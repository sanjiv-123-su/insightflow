from datetime import datetime, timezone
import logging
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from fastapi import HTTPException, status
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.analytics_result import AnalyticsResult
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.analytics import (
    CategoryRevenuePoint,
    ColumnMappingInput,
    DatasetAnalyticsResponse,
    DetectedColumnMapping,
    GrowthSummary,
    KpiMetrics,
    MonthlyRevenuePoint,
    RegionRevenuePoint,
    TopCustomerPoint,
    TopProductPoint,
)
from app.services.file_storage import FileStorageService
from app.services.profiler import DataProfilerService

logger = logging.getLogger(__name__)

# Heuristic keyword matchers for column auto-detection
KEYWORD_CANDIDATES = {
    "revenue": [
        "revenue", "sales", "amount", "total_amount", "price", "total",
        "order_total", "line_total", "net_sales", "subtotal", "cost",
        "turnover", "gross_sales", "payment", "value", "spent", "grand_total"
    ],
    "order_id": [
        "order_id", "order_number", "order_no", "invoice_id", "invoice_no",
        "invoice", "transaction_id", "trans_id", "receipt_id", "order", "id"
    ],
    "customer": [
        "customer_id", "customer_name", "customer", "client_id", "client_name",
        "client", "user_id", "username", "buyer_id", "buyer", "account_id",
        "account_name", "email", "customer_email"
    ],
    "date": [
        "date", "order_date", "created_at", "timestamp", "invoice_date",
        "transaction_date", "purchase_date", "sale_date", "time", "day",
        "order_timestamp", "period"
    ],
    "category": [
        "category", "product_category", "item_category", "department", "type",
        "segment", "group", "genre", "class", "family", "product_type"
    ],
    "region": [
        "region", "country", "state", "city", "territory", "zone",
        "location", "market", "area", "province", "continent", "store_location"
    ],
    "product": [
        "product", "product_name", "item", "item_name", "sku", "product_id",
        "item_id", "description", "title", "goods", "service"
    ],
    "quantity": [
        "quantity", "qty", "units", "count", "items", "volume", "number_of_items"
    ],
}


def normalize_col_name(name: str) -> str:
    """Normalize a column name for comparison (lowercased, spaces/hyphens to underscores)."""
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


class AnalyticsEngine:
    """Core computational analytics engine for business datasets."""

    @classmethod
    def detect_columns(
        cls,
        df: pd.DataFrame,
        overrides: Optional[ColumnMappingInput] = None,
    ) -> DetectedColumnMapping:
        """Identify revenue, order, customer, date, category, region, and product columns."""
        cols = list(df.columns)
        norm_map = {normalize_col_name(c): c for c in cols}

        # 1. Identify available data types
        numeric_cols: List[str] = []
        date_cols: List[str] = []
        categorical_cols: List[str] = []

        for c in cols:
            series = df[c]
            non_null = series.dropna()
            if len(non_null) == 0:
                continue

            # Check numeric
            if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
                numeric_cols.append(c)
            else:
                converted = pd.to_numeric(non_null, errors="coerce")
                if converted.notna().sum() / len(non_null) >= 0.80:
                    numeric_cols.append(c)

            # Check datetime
            if pd.api.types.is_datetime64_any_dtype(series):
                date_cols.append(c)
            elif str(c).lower().find("date") != -1 or str(c).lower().find("time") != -1:
                try:
                    dt_sample = pd.to_datetime(non_null.head(30), errors="coerce")
                    if dt_sample.notna().sum() / min(len(non_null), 30) >= 0.70:
                        date_cols.append(c)
                except Exception:
                    pass

            # Check categorical
            if series.nunique() <= 100 and c not in numeric_cols:
                categorical_cols.append(c)

        # 2. Heuristic scoring for each role
        detected: Dict[str, Optional[str]] = {
            "revenue_column": None,
            "order_id_column": None,
            "customer_column": None,
            "date_column": None,
            "category_column": None,
            "region_column": None,
            "product_column": None,
            "quantity_column": None,
        }

        for role, candidates in KEYWORD_CANDIDATES.items():
            best_col = None
            best_score = -1

            for c in cols:
                norm_c = normalize_col_name(c)
                score = 0

                # Keyword matching
                for cand in candidates:
                    if norm_c == cand:
                        score = max(score, 100)
                    elif norm_c.startswith(f"{cand}_") or norm_c.endswith(f"_{cand}"):
                        score = max(score, 85)
                    elif cand in norm_c:
                        score = max(score, 65)

                # Type suitability penalties/bonuses
                if role == "revenue":
                    if c in numeric_cols:
                        score += 30
                        # Penalize ID-like columns (integer IDs with high cardinality)
                        if norm_c.endswith("_id") or norm_c == "id":
                            score -= 80
                    else:
                        score = -1  # Disqualify non-numeric
                elif role == "date":
                    if c in date_cols:
                        score += 40
                    else:
                        score -= 50
                elif role == "quantity":
                    if c in numeric_cols:
                        score += 20
                    else:
                        score = -1
                elif role in ("category", "region"):
                    if c in categorical_cols:
                        score += 20
                    if c in numeric_cols and role != "order_id":
                        score -= 40

                if score > best_score and score > 40:
                    best_score = score
                    best_col = c

            key = f"{role}_column" if not role.endswith("_column") else role
            detected[key] = best_col

        # Fallback for revenue if no keyword matched
        if not detected["revenue_column"] and numeric_cols:
            # Pick first numeric column that is not an ID
            for nc in numeric_cols:
                norm_nc = normalize_col_name(nc)
                if not norm_nc.endswith("_id") and norm_nc != "id" and nc != detected["quantity_column"]:
                    detected["revenue_column"] = nc
                    break
            if not detected["revenue_column"]:
                detected["revenue_column"] = numeric_cols[0]

        # 3. Apply user overrides if provided
        auto_detected = True
        if overrides:
            override_dict = overrides.model_dump(exclude_unset=True)
            for k, val in override_dict.items():
                if val:
                    auto_detected = False
                    detected[k] = val

        return DetectedColumnMapping(
            revenue_column=detected["revenue_column"],
            order_id_column=detected["order_id_column"],
            customer_column=detected["customer_column"],
            date_column=detected["date_column"],
            category_column=detected["category_column"],
            region_column=detected["region_column"],
            product_column=detected["product_column"],
            quantity_column=detected["quantity_column"],
            detected_automatically=auto_detected,
            available_numeric_columns=numeric_cols,
            available_categorical_columns=categorical_cols,
            available_date_columns=date_cols,
        )

    @classmethod
    def validate_mapping(cls, df: pd.DataFrame, mapping: DetectedColumnMapping) -> None:
        """Validate mapped columns exist and contain valid data types before analysis.

        Raises:
            HTTPException(400): If mapping validation fails or dataset is unsupported.
        """
        cols = list(df.columns)
        col_lookup = {normalize_col_name(c): c for c in cols}

        # 1. Revenue column validation (Mandatory)
        rev_col = mapping.revenue_column
        if not rev_col:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Unsupported dataset: No revenue, sales, or numeric metric column could be identified. "
                    "Please provide an explicit column mapping."
                ),
            )

        if rev_col not in cols:
            norm_rev = normalize_col_name(rev_col)
            if norm_rev in col_lookup:
                mapping.revenue_column = col_lookup[norm_rev]
                rev_col = mapping.revenue_column
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Specified revenue column '{rev_col}' does not exist in dataset. Available columns: {cols}",
                )

        # Ensure revenue contains parseable numeric values
        num_series = pd.to_numeric(df[rev_col], errors="coerce")
        if num_series.notna().sum() == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Revenue column '{rev_col}' contains no valid numeric values for analysis.",
            )

        # 2. Date column validation
        if mapping.date_column:
            d_col = mapping.date_column
            if d_col not in cols:
                norm_d = normalize_col_name(d_col)
                if norm_d in col_lookup:
                    mapping.date_column = col_lookup[norm_d]
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Specified date column '{d_col}' does not exist in dataset. Available columns: {cols}",
                    )
            # Verify date parseability
            parsed_dates = pd.to_datetime(df[mapping.date_column].dropna().head(50), errors="coerce")
            if parsed_dates.notna().sum() == 0:
                logger.warning("Configured date column '%s' has 0 parseable dates; disabling date analysis", mapping.date_column)
                mapping.date_column = None

        # 3. Validate existence of other optional columns
        for field_name in ["order_id_column", "customer_column", "category_column", "region_column", "product_column", "quantity_column"]:
            val = getattr(mapping, field_name, None)
            if val and val not in cols:
                norm_v = normalize_col_name(val)
                if norm_v in col_lookup:
                    setattr(mapping, field_name, col_lookup[norm_v])
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Specified {field_name} '{val}' does not exist in dataset. Available columns: {cols}",
                    )

    @classmethod
    def calculate_analytics(
        cls,
        df: pd.DataFrame,
        mapping: DetectedColumnMapping,
    ) -> Dict[str, Any]:
        """Perform comprehensive business analytics and structure for React visualizations."""
        cls.validate_mapping(df, mapping)

        rev_col = mapping.revenue_column
        assert rev_col is not None

        # Prepare clean numeric revenue series
        clean_df = df.copy()
        clean_df["_revenue"] = pd.to_numeric(clean_df[rev_col], errors="coerce").fillna(0.0)

        # 1. Total Revenue
        total_revenue = round(float(clean_df["_revenue"].sum()), 2)

        # 2. Total Orders
        order_col = mapping.order_id_column
        if order_col and order_col in clean_df.columns:
            total_orders = int(clean_df[order_col].dropna().nunique())
        else:
            total_orders = int(len(clean_df))
        total_orders = max(total_orders, 1) if len(clean_df) > 0 else 0

        # 3. Unique Customers
        cust_col = mapping.customer_column
        unique_customers = None
        if cust_col and cust_col in clean_df.columns:
            unique_customers = int(clean_df[cust_col].dropna().nunique())

        # 4. Average Order Value (AOV)
        aov = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0

        # 5. Revenue by Month & Growth Percentage
        revenue_by_month: List[Dict[str, Any]] = []
        growth_summary: Optional[Dict[str, Any]] = None
        overall_growth_pct: Optional[float] = None

        date_col = mapping.date_column
        if date_col and date_col in clean_df.columns:
            clean_df["_date"] = pd.to_datetime(clean_df[date_col], errors="coerce")
            dated_df = clean_df.dropna(subset=["_date"]).copy()

            if len(dated_df) > 0:
                dated_df["_period"] = dated_df["_date"].dt.strftime("%Y-%m")
                
                # Group by month
                if order_col and order_col in dated_df.columns:
                    monthly_agg = dated_df.groupby("_period").agg(
                        revenue=("_revenue", "sum"),
                        orders=(order_col, "nunique"),
                    ).reset_index()
                else:
                    monthly_agg = dated_df.groupby("_period").agg(
                        revenue=("_revenue", "sum"),
                        orders=("_revenue", "count"),
                    ).reset_index()

                monthly_agg = monthly_agg.sort_values("_period")

                # Calculate Month-over-Month Growth
                prev_rev = None
                for _, row in monthly_agg.iterrows():
                    period = str(row["_period"])
                    m_rev = round(float(row["revenue"]), 2)
                    m_orders = int(row["orders"])

                    growth_pct = None
                    if prev_rev is not None and prev_rev > 0:
                        growth_pct = round(((m_rev - prev_rev) / prev_rev) * 100.0, 2)

                    revenue_by_month.append({
                        "period": period,
                        "revenue": m_rev,
                        "orders": m_orders,
                        "growth_percentage": growth_pct,
                    })
                    prev_rev = m_rev

                # Overall / latest growth summary
                if len(revenue_by_month) >= 2:
                    latest = revenue_by_month[-1]
                    prior = revenue_by_month[-2]
                    l_growth = latest["growth_percentage"]
                    if l_growth is not None:
                        overall_growth_pct = l_growth
                        trend = "positive" if l_growth > 0 else ("negative" if l_growth < 0 else "neutral")
                        growth_summary = {
                            "current_period": latest["period"],
                            "previous_period": prior["period"],
                            "growth_percentage": l_growth,
                            "trend": trend,
                        }

        # 6. Revenue by Category
        revenue_by_category: List[Dict[str, Any]] = []
        cat_col = mapping.category_column
        if cat_col and cat_col in clean_df.columns:
            cat_series = clean_df[cat_col].fillna("Uncategorized").astype(str).str.strip()
            clean_df["_cat"] = cat_series

            if order_col and order_col in clean_df.columns:
                cat_agg = clean_df.groupby("_cat").agg(
                    revenue=("_revenue", "sum"),
                    orders=(order_col, "nunique"),
                ).reset_index()
            else:
                cat_agg = clean_df.groupby("_cat").agg(
                    revenue=("_revenue", "sum"),
                    orders=("_revenue", "count"),
                ).reset_index()

            cat_agg = cat_agg.sort_values("revenue", ascending=False)
            for _, r in cat_agg.head(10).iterrows():
                c_rev = round(float(r["revenue"]), 2)
                pct = round((c_rev / total_revenue * 100.0), 2) if total_revenue > 0 else 0.0
                revenue_by_category.append({
                    "category": str(r["_cat"]),
                    "revenue": c_rev,
                    "orders": int(r["orders"]),
                    "percentage": pct,
                })

        # 7. Revenue by Region
        revenue_by_region: List[Dict[str, Any]] = []
        reg_col = mapping.region_column
        if reg_col and reg_col in clean_df.columns:
            reg_series = clean_df[reg_col].fillna("Unknown Region").astype(str).str.strip()
            clean_df["_reg"] = reg_series

            if order_col and order_col in clean_df.columns:
                reg_agg = clean_df.groupby("_reg").agg(
                    revenue=("_revenue", "sum"),
                    orders=(order_col, "nunique"),
                ).reset_index()
            else:
                reg_agg = clean_df.groupby("_reg").agg(
                    revenue=("_revenue", "sum"),
                    orders=("_revenue", "count"),
                ).reset_index()

            reg_agg = reg_agg.sort_values("revenue", ascending=False)
            for _, r in reg_agg.head(10).iterrows():
                r_rev = round(float(r["revenue"]), 2)
                pct = round((r_rev / total_revenue * 100.0), 2) if total_revenue > 0 else 0.0
                revenue_by_region.append({
                    "region": str(r["_reg"]),
                    "revenue": r_rev,
                    "orders": int(r["orders"]),
                    "percentage": pct,
                })

        # 8. Top Products
        top_products: List[Dict[str, Any]] = []
        prod_col = mapping.product_column
        qty_col = mapping.quantity_column
        if prod_col and prod_col in clean_df.columns:
            clean_df["_prod"] = clean_df[prod_col].fillna("Unknown Product").astype(str).str.strip()

            agg_dict: Dict[str, Any] = {
                "revenue": ("_revenue", "sum"),
            }
            if order_col and order_col in clean_df.columns:
                agg_dict["orders"] = (order_col, "nunique")
            else:
                agg_dict["orders"] = ("_revenue", "count")

            has_qty = qty_col and qty_col in clean_df.columns
            if has_qty:
                clean_df["_qty"] = pd.to_numeric(clean_df[qty_col], errors="coerce").fillna(0)
                agg_dict["units_sold"] = ("_qty", "sum")

            prod_agg = clean_df.groupby("_prod").agg(**agg_dict).reset_index()
            prod_agg = prod_agg.sort_values("revenue", ascending=False)

            for _, r in prod_agg.head(10).iterrows():
                p_item: Dict[str, Any] = {
                    "product": str(r["_prod"]),
                    "revenue": round(float(r["revenue"]), 2),
                    "orders": int(r["orders"]),
                    "units_sold": int(r["units_sold"]) if has_qty else None,
                }
                top_products.append(p_item)

        # 9. Top Customers
        top_customers: List[Dict[str, Any]] = []
        if cust_col and cust_col in clean_df.columns:
            clean_df["_cust"] = clean_df[cust_col].fillna("Guest").astype(str).str.strip()

            if order_col and order_col in clean_df.columns:
                cust_agg = clean_df.groupby("_cust").agg(
                    revenue=("_revenue", "sum"),
                    orders=(order_col, "nunique"),
                ).reset_index()
            else:
                cust_agg = clean_df.groupby("_cust").agg(
                    revenue=("_revenue", "sum"),
                    orders=("_revenue", "count"),
                ).reset_index()

            cust_agg = cust_agg.sort_values("revenue", ascending=False)
            for _, r in cust_agg.head(10).iterrows():
                c_rev = round(float(r["revenue"]), 2)
                c_ord = max(int(r["orders"]), 1)
                c_avg = round(c_rev / c_ord, 2)
                top_customers.append({
                    "customer": str(r["_cust"]),
                    "revenue": c_rev,
                    "orders": c_ord,
                    "average_spend": c_avg,
                })

        return {
            "kpis": {
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "unique_customers": unique_customers,
                "average_order_value": aov,
                "growth_percentage": overall_growth_pct,
            },
            "revenue_by_month": revenue_by_month,
            "revenue_by_category": revenue_by_category,
            "revenue_by_region": revenue_by_region,
            "top_products": top_products,
            "top_customers": top_customers,
            "growth_summary": growth_summary,
            "column_mapping": mapping.model_dump(),
        }


class AnalyticsService:
    """Service handling business analytics execution, caching, and mapping retrieval."""

    @classmethod
    def get_detected_mapping(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
    ) -> DetectedColumnMapping:
        """Inspect dataset and return detected column mappings without running full analysis."""
        from app.services.dataset import DatasetService
        dataset = DatasetService.get_dataset(db, user, dataset_id)

        file_path = FileStorageService.get_stored_file_path(dataset.id)
        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset source file is not available on storage.",
            )

        df = DataProfilerService.load_dataframe(file_path, dataset.file_type)
        return AnalyticsEngine.detect_columns(df)

    @classmethod
    def get_or_compute_analytics(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
        mapping_override: Optional[ColumnMappingInput] = None,
        use_cache: bool = True,
    ) -> DatasetAnalyticsResponse:
        """Compute business analytics, utilizing cached AnalyticsResult when appropriate.

        Raises:
            HTTPException(400): If dataset lacks required numeric/business columns.
            HTTPException(404): If dataset does not exist or user lacks permission.
        """
        from app.services.dataset import DatasetService
        dataset = DatasetService.get_dataset(db, user, dataset_id)

        # 1. Check cache if no custom overrides provided and use_cache is True
        if use_cache and not mapping_override:
            cached_result = (
                db.query(AnalyticsResult)
                .filter(
                    AnalyticsResult.dataset_id == dataset.id,
                    AnalyticsResult.analysis_type == "business_overview",
                )
                .first()
            )
            if cached_result and isinstance(cached_result.result, dict):
                res = cached_result.result
                return DatasetAnalyticsResponse(
                    dataset_id=dataset.id,
                    kpis=KpiMetrics(**res["kpis"]),
                    revenue_by_month=[MonthlyRevenuePoint(**m) for m in res.get("revenue_by_month", [])],
                    revenue_by_category=[CategoryRevenuePoint(**c) for c in res.get("revenue_by_category", [])],
                    revenue_by_region=[RegionRevenuePoint(**r) for r in res.get("revenue_by_region", [])],
                    top_products=[TopProductPoint(**p) for p in res.get("top_products", [])],
                    top_customers=[TopCustomerPoint(**u) for u in res.get("top_customers", [])],
                    growth_summary=GrowthSummary(**res["growth_summary"]) if res.get("growth_summary") else None,
                    column_mapping=DetectedColumnMapping(**res["column_mapping"]),
                    created_at=cached_result.created_at,
                )

        # 2. Load file and perform analysis
        file_path = FileStorageService.get_stored_file_path(dataset.id)
        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset source file is not available on storage.",
            )

        df = DataProfilerService.load_dataframe(file_path, dataset.file_type)

        # Detect columns with optional overrides
        mapping = AnalyticsEngine.detect_columns(df, overrides=mapping_override)

        # Run analytics calculations
        analytics_dict = AnalyticsEngine.calculate_analytics(df, mapping)

        # 3. Store/update reusable analysis results in Neon PostgreSQL
        cached_result = (
            db.query(AnalyticsResult)
            .filter(
                AnalyticsResult.dataset_id == dataset.id,
                AnalyticsResult.analysis_type == "business_overview",
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        if cached_result:
            cached_result.result = analytics_dict
            cached_result.created_at = now
        else:
            cached_result = AnalyticsResult(
                id=uuid.uuid4(),
                dataset_id=dataset.id,
                analysis_type="business_overview",
                result=analytics_dict,
                created_at=now,
            )
            db.add(cached_result)

        try:
            db.commit()
            db.refresh(cached_result)
        except Exception as exc:
            db.rollback()
            logger.warning("Could not persist cached analytics result: %s", exc)

        return DatasetAnalyticsResponse(
            dataset_id=dataset.id,
            kpis=KpiMetrics(**analytics_dict["kpis"]),
            revenue_by_month=[MonthlyRevenuePoint(**m) for m in analytics_dict.get("revenue_by_month", [])],
            revenue_by_category=[CategoryRevenuePoint(**c) for c in analytics_dict.get("revenue_by_category", [])],
            revenue_by_region=[RegionRevenuePoint(**r) for r in analytics_dict.get("revenue_by_region", [])],
            top_products=[TopProductPoint(**p) for p in analytics_dict.get("top_products", [])],
            top_customers=[TopCustomerPoint(**u) for u in analytics_dict.get("top_customers", [])],
            growth_summary=GrowthSummary(**analytics_dict["growth_summary"]) if analytics_dict.get("growth_summary") else None,
            column_mapping=mapping,
            created_at=cached_result.created_at,
        )
