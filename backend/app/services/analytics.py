from datetime import datetime, timezone
import logging
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
    BusinessAnalyticsResponse,
    CategoryRevenueItem,
    ColumnMappingConfig,
    DetectedColumnMapping,
    KPIMetrics,
    MonthlyRevenueItem,
    RegionRevenueItem,
    TopCustomerItem,
    TopProductItem,
)
from app.services.file_storage import FileStorageService
from app.services.profiler import DataProfilerService

logger = logging.getLogger(__name__)

# Heuristic regex patterns for common business dimensions
PATTERNS = {
    "revenue": re.compile(
        r"(total[\s_]?)?(rev(enue)?|sales?|amount|price|subtotal|spend|turnover|gmv|val(ue)?|cost)",
        re.IGNORECASE,
    ),
    "date": re.compile(
        r"(order[\s_]?date|invoice[\s_]?date|sale[\s_]?date|trans(action)?[\s_]?date|date|created[\s_]?at|timestamp|period|time)",
        re.IGNORECASE,
    ),
    "order_id": re.compile(
        r"(order[\s_]?id|order[\s_]?no|order[\s_]?number|invoice[\s_]?(no|id|num)?|transaction[\s_]?id|receipt|txn[\s_]?id)",
        re.IGNORECASE,
    ),
    "customer_id": re.compile(
        r"(cust(omer)?[\s_]?(id|no|num|code|name)?|client[\s_]?(id|name)?|user[\s_]?(id|name)?|buyer|account[\s_]?id|email)",
        re.IGNORECASE,
    ),
    "category": re.compile(
        r"(cat(egory)?|department|dept|segment|type|class|group|sector|line)",
        re.IGNORECASE,
    ),
    "product": re.compile(
        r"(prod(uct)?[\s_]?(name|id|title|desc)?|item[\s_]?(name|id|title|desc)?|sku|description|title)",
        re.IGNORECASE,
    ),
    "region": re.compile(
        r"(region|territory|country|state|city|market|zone|area|location|province|continent)",
        re.IGNORECASE,
    ),
}


class ColumnDetector:
    """Intelligently detects business semantic roles from DataFrame columns."""

    @staticmethod
    def clean_numeric_series(series: pd.Series) -> pd.Series:
        """Strip currency symbols, commas, and whitespace, converting to clean numeric float."""
        if pd.api.types.is_numeric_dtype(series):
            return pd.to_numeric(series, errors="coerce")
        # Strip currency symbols and commas from strings
        cleaned = (
            series.dropna()
            .astype(str)
            .str.replace(r"[$€£¥₹,\s]", "", regex=True)
            .str.strip()
        )
        return pd.to_numeric(cleaned, errors="coerce")

    @classmethod
    def detect_revenue_column(cls, df: pd.DataFrame, explicit: Optional[str] = None) -> Optional[str]:
        """Detect the primary revenue or sales metric column."""
        if explicit and explicit in df.columns:
            cleaned = cls.clean_numeric_series(df[explicit])
            if cleaned.notna().sum() > 0:
                return explicit

        # 1. Look for columns matching revenue regex keywords
        candidates = []
        for col in df.columns:
            col_str = str(col).strip()
            if PATTERNS["revenue"].search(col_str):
                cleaned = cls.clean_numeric_series(df[col])
                valid_count = cleaned.notna().sum()
                if valid_count > 0:
                    score = 10
                    # Prioritize exact names like "revenue", "sales", "total_amount"
                    lower_name = col_str.lower()
                    if "revenue" in lower_name:
                        score += 5
                    elif "sales" in lower_name:
                        score += 4
                    elif "amount" in lower_name:
                        score += 3
                    elif "total" in lower_name:
                        score += 2
                    candidates.append((col_str, score, float(cleaned.sum(skipna=True))))

        if candidates:
            # Sort by score descending, then by sum descending
            candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
            return candidates[0][0]

        # 2. Fallback: find any numeric column that is not an ID or index
        fallback_candidates = []
        for col in df.columns:
            col_str = str(col).strip()
            if not re.search(r"(id|code|no|num|index|year|month|day)$", col_str, re.IGNORECASE):
                cleaned = cls.clean_numeric_series(df[col])
                if cleaned.notna().sum() / max(len(df), 1) >= 0.5:
                    fallback_candidates.append((col_str, float(cleaned.sum(skipna=True))))

        if fallback_candidates:
            fallback_candidates.sort(key=lambda x: x[1], reverse=True)
            return fallback_candidates[0][0]

        return None

    @classmethod
    def detect_date_column(cls, df: pd.DataFrame, explicit: Optional[str] = None) -> Optional[str]:
        """Detect the transaction date or timestamp column."""
        if explicit and explicit in df.columns:
            return explicit

        # 1. Match regex pattern on column name
        for col in df.columns:
            col_str = str(col).strip()
            if PATTERNS["date"].search(col_str):
                parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
                if parsed.notna().sum() / max(len(df), 1) >= 0.5:
                    return col_str

        # 2. Check if any column is datetime dtype
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return str(col)

        # 3. Sample check for date-like strings
        for col in df.columns:
            if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                sample = df[col].dropna().head(30)
                if len(sample) > 0 and sample.astype(str).str.contains(r"[-/:\sT]").any():
                    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
                    if parsed.notna().sum() / len(sample) >= 0.8:
                        return str(col)

        return None

    @classmethod
    def detect_categorical_role(
        cls,
        df: pd.DataFrame,
        role: str,
        explicit: Optional[str] = None,
        exclude_cols: Optional[set] = None,
    ) -> Optional[str]:
        """Detect categorical or entity columns (order_id, customer, category, product, region)."""
        exclude = exclude_cols or set()
        if explicit and explicit in df.columns:
            return explicit

        pattern = PATTERNS.get(role)
        if not pattern:
            return None

        candidates = []
        for col in df.columns:
            col_str = str(col).strip()
            if col_str in exclude:
                continue

            if pattern.search(col_str):
                unique_cnt = df[col].nunique(dropna=True)
                candidates.append((col_str, unique_cnt))

        if candidates:
            # For categories and regions, lower cardinality is preferred
            if role in ("category", "region"):
                candidates.sort(key=lambda x: x[1])
            else:
                # For IDs, higher cardinality is preferred
                candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    @classmethod
    def resolve_mapping(
        cls,
        df: pd.DataFrame,
        custom: Optional[ColumnMappingConfig] = None,
    ) -> Tuple[DetectedColumnMapping, set]:
        """Resolve all column mappings using user configuration and heuristics."""
        cfg = custom or ColumnMappingConfig()
        detected_roles = {}
        assigned_cols = set()

        # 1. Revenue
        rev_col = cls.detect_revenue_column(df, explicit=cfg.revenue_column)
        if rev_col:
            detected_roles["revenue"] = rev_col
            assigned_cols.add(rev_col)

        # 2. Date
        date_col = cls.detect_date_column(df, explicit=cfg.date_column)
        if date_col:
            detected_roles["date"] = date_col
            assigned_cols.add(date_col)

        # 3. Order ID
        order_col = cls.detect_categorical_role(
            df, "order_id", explicit=cfg.order_id_column, exclude_cols=assigned_cols
        )
        if order_col:
            detected_roles["order_id"] = order_col
            assigned_cols.add(order_col)

        # 4. Customer ID
        cust_col = cls.detect_categorical_role(
            df, "customer_id", explicit=cfg.customer_id_column, exclude_cols=assigned_cols
        )
        if cust_col:
            detected_roles["customer_id"] = cust_col
            assigned_cols.add(cust_col)

        # 5. Category
        cat_col = cls.detect_categorical_role(
            df, "category", explicit=cfg.category_column, exclude_cols=assigned_cols
        )
        if cat_col:
            detected_roles["category"] = cat_col
            assigned_cols.add(cat_col)

        # 6. Product
        prod_col = cls.detect_categorical_role(
            df, "product", explicit=cfg.product_column, exclude_cols=assigned_cols
        )
        if prod_col:
            detected_roles["product"] = prod_col
            assigned_cols.add(prod_col)

        # 7. Region
        region_col = cls.detect_categorical_role(
            df, "region", explicit=cfg.region_column, exclude_cols=assigned_cols
        )
        if region_col:
            detected_roles["region"] = region_col
            assigned_cols.add(region_col)

        mapping = DetectedColumnMapping(
            revenue_column=rev_col,
            date_column=date_col,
            order_id_column=order_col,
            customer_id_column=cust_col,
            category_column=cat_col,
            product_column=prod_col,
            region_column=region_col,
            auto_detected=custom is None or all(v is None for v in cfg.model_dump().values()),
            detected_roles=detected_roles,
        )
        return mapping, assigned_cols


class AnalyticsEngine:
    """Core computational engine for common business metrics and React chart payloads."""

    @classmethod
    def validate_and_prepare_df(
        cls,
        df: pd.DataFrame,
        mapping: DetectedColumnMapping,
    ) -> Tuple[pd.DataFrame, str]:
        """Validate mapped columns and prepare numeric and date representations.

        Raises:
            HTTPException(400): If dataset has no valid revenue column or required columns missing.
        """
        if df.empty or len(df.columns) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot perform business analytics: dataset is empty.",
            )

        rev_col = mapping.revenue_column
        if not rev_col or rev_col not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Could not detect a revenue, sales, or numeric metric column in this dataset. "
                    "Please provide explicit column mappings or upload a dataset with financial/order values."
                ),
            )

        # Clean revenue column
        df = df.copy()
        df["__clean_revenue__"] = ColumnDetector.clean_numeric_series(df[rev_col])
        if df["__clean_revenue__"].notna().sum() == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mapped revenue column '{rev_col}' contains no valid numeric values.",
            )

        # Parse date column if mapped
        if mapping.date_column and mapping.date_column in df.columns:
            df["__clean_date__"] = pd.to_datetime(
                df[mapping.date_column], errors="coerce", format="mixed"
            )
        else:
            df["__clean_date__"] = pd.NaT

        return df, rev_col

    @classmethod
    def compute_kpis(
        cls,
        df: pd.DataFrame,
        mapping: DetectedColumnMapping,
        monthly_growth: Optional[float] = None,
    ) -> KPIMetrics:
        """Compute high-level summary KPIs (total revenue, total orders, customers, AOV, growth)."""
        rev_series = df["__clean_revenue__"].dropna()
        total_revenue = round(float(rev_series.sum()), 2)

        # Total orders
        if mapping.order_id_column and mapping.order_id_column in df.columns:
            total_orders = int(df[mapping.order_id_column].nunique(dropna=True))
        else:
            total_orders = int(len(df))

        # Unique customers
        if mapping.customer_id_column and mapping.customer_id_column in df.columns:
            unique_customers = int(df[mapping.customer_id_column].nunique(dropna=True))
        else:
            unique_customers = total_orders

        # Average Order Value (AOV)
        if total_orders > 0:
            aov = round(total_revenue / total_orders, 2)
        else:
            aov = 0.0

        return KPIMetrics(
            total_revenue=total_revenue,
            total_orders=total_orders,
            unique_customers=unique_customers,
            average_order_value=aov,
            overall_growth_percentage=monthly_growth,
        )

    @classmethod
    def compute_revenue_by_month(
        cls,
        df: pd.DataFrame,
        mapping: DetectedColumnMapping,
    ) -> Tuple[List[MonthlyRevenueItem], Optional[float]]:
        """Calculate monthly revenue trends and month-over-month growth percentages."""
        if "__clean_date__" not in df.columns or df["__clean_date__"].isna().all():
            return [], None

        valid_df = df.dropna(subset=["__clean_date__"]).copy()
        if valid_df.empty:
            return [], None

        valid_df["__month__"] = valid_df["__clean_date__"].dt.strftime("%Y-%m")

        # Group by month
        grouped = (
            valid_df.groupby("__month__")
            .agg(
                revenue=("__clean_revenue__", "sum"),
                orders=(
                    mapping.order_id_column
                    if mapping.order_id_column and mapping.order_id_column in valid_df.columns
                    else "__clean_revenue__",
                    "nunique"
                    if mapping.order_id_column and mapping.order_id_column in valid_df.columns
                    else "count",
                ),
            )
            .reset_index()
            .sort_values("__month__")
        )

        monthly_items: List[MonthlyRevenueItem] = []
        prev_rev: Optional[float] = None
        latest_growth: Optional[float] = None

        for _, row in grouped.iterrows():
            month_str = str(row["__month__"])
            curr_rev = round(float(row["revenue"]), 2)
            orders_count = int(row["orders"])

            growth_pct: Optional[float] = None
            if prev_rev is not None and prev_rev > 0:
                growth_pct = round(((curr_rev - prev_rev) / prev_rev) * 100.0, 2)
                latest_growth = growth_pct

            monthly_items.append(
                MonthlyRevenueItem(
                    month=month_str,
                    revenue=curr_rev,
                    orders=orders_count,
                    growth_percentage=growth_pct,
                )
            )
            prev_rev = curr_rev

        return monthly_items, latest_growth

    @classmethod
    def compute_revenue_by_category(
        cls,
        df: pd.DataFrame,
        mapping: DetectedColumnMapping,
        total_revenue: float,
        top_n: int = 10,
    ) -> List[CategoryRevenueItem]:
        """Aggregate revenue by product category with share percentage."""
        cat_col = mapping.category_column
        if not cat_col or cat_col not in df.columns:
            return []

        valid_df = df.dropna(subset=[cat_col, "__clean_revenue__"])
        if valid_df.empty:
            return []

        grouped = (
            valid_df.groupby(cat_col)["__clean_revenue__"]
            .sum()
            .reset_index()
            .sort_values("__clean_revenue__", ascending=False)
        )

        items: List[CategoryRevenueItem] = []
        for _, row in grouped.head(top_n).iterrows():
            rev = round(float(row["__clean_revenue__"]), 2)
            pct = round((rev / total_revenue * 100.0), 2) if total_revenue > 0 else 0.0
            items.append(
                CategoryRevenueItem(
                    category=str(row[cat_col]),
                    revenue=rev,
                    percentage=pct,
                )
            )

        return items

    @classmethod
    def compute_revenue_by_region(
        cls,
        df: pd.DataFrame,
        mapping: DetectedColumnMapping,
        total_revenue: float,
        top_n: int = 10,
    ) -> List[RegionRevenueItem]:
        """Aggregate revenue by geographical region with share percentage."""
        region_col = mapping.region_column
        if not region_col or region_col not in df.columns:
            return []

        valid_df = df.dropna(subset=[region_col, "__clean_revenue__"])
        if valid_df.empty:
            return []

        grouped = (
            valid_df.groupby(region_col)["__clean_revenue__"]
            .sum()
            .reset_index()
            .sort_values("__clean_revenue__", ascending=False)
        )

        items: List[RegionRevenueItem] = []
        for _, row in grouped.head(top_n).iterrows():
            rev = round(float(row["__clean_revenue__"]), 2)
            pct = round((rev / total_revenue * 100.0), 2) if total_revenue > 0 else 0.0
            items.append(
                RegionRevenueItem(
                    region=str(row[region_col]),
                    revenue=rev,
                    percentage=pct,
                )
            )

        return items

    @classmethod
    def compute_top_products(
        cls,
        df: pd.DataFrame,
        mapping: DetectedColumnMapping,
        top_n: int = 10,
    ) -> List[TopProductItem]:
        """Identify top-performing products by sales revenue and frequency."""
        prod_col = mapping.product_column
        if not prod_col or prod_col not in df.columns:
            return []

        valid_df = df.dropna(subset=[prod_col, "__clean_revenue__"])
        if valid_df.empty:
            return []

        grouped = (
            valid_df.groupby(prod_col)
            .agg(
                revenue=("__clean_revenue__", "sum"),
                orders=(
                    mapping.order_id_column
                    if mapping.order_id_column and mapping.order_id_column in valid_df.columns
                    else "__clean_revenue__",
                    "nunique"
                    if mapping.order_id_column and mapping.order_id_column in valid_df.columns
                    else "count",
                ),
            )
            .reset_index()
            .sort_values("revenue", ascending=False)
        )

        items: List[TopProductItem] = []
        for _, row in grouped.head(top_n).iterrows():
            items.append(
                TopProductItem(
                    product=str(row[prod_col]),
                    revenue=round(float(row["revenue"]), 2),
                    orders=int(row["orders"]),
                )
            )

        return items

    @classmethod
    def compute_top_customers(
        cls,
        df: pd.DataFrame,
        mapping: DetectedColumnMapping,
        top_n: int = 10,
    ) -> List[TopCustomerItem]:
        """Identify top revenue-generating customers."""
        cust_col = mapping.customer_id_column
        if not cust_col or cust_col not in df.columns:
            return []

        valid_df = df.dropna(subset=[cust_col, "__clean_revenue__"])
        if valid_df.empty:
            return []

        grouped = (
            valid_df.groupby(cust_col)
            .agg(
                revenue=("__clean_revenue__", "sum"),
                orders=(
                    mapping.order_id_column
                    if mapping.order_id_column and mapping.order_id_column in valid_df.columns
                    else "__clean_revenue__",
                    "nunique"
                    if mapping.order_id_column and mapping.order_id_column in valid_df.columns
                    else "count",
                ),
            )
            .reset_index()
            .sort_values("revenue", ascending=False)
        )

        items: List[TopCustomerItem] = []
        for _, row in grouped.head(top_n).iterrows():
            items.append(
                TopCustomerItem(
                    customer=str(row[cust_col]),
                    revenue=round(float(row["revenue"]), 2),
                    orders=int(row["orders"]),
                )
            )

        return items

    @classmethod
    def generate_analytics(
        cls,
        df: pd.DataFrame,
        custom_mapping: Optional[ColumnMappingConfig] = None,
        dataset_id: Optional[uuid.UUID] = None,
    ) -> BusinessAnalyticsResponse:
        """Run full analytics pipeline on DataFrame with resolved column mappings."""
        # 1. Resolve column mappings
        mapping, _ = ColumnDetector.resolve_mapping(df, custom=custom_mapping)

        # 2. Validate and prepare DataFrame
        prepared_df, rev_col = cls.validate_and_prepare_df(df, mapping)

        # 3. Monthly revenue & growth
        revenue_by_month, latest_growth = cls.compute_revenue_by_month(prepared_df, mapping)

        # 4. High-level KPIs
        kpis = cls.compute_kpis(prepared_df, mapping, monthly_growth=latest_growth)

        # 5. Categorical & Regional breakdowns
        revenue_by_cat = cls.compute_revenue_by_category(
            prepared_df, mapping, total_revenue=kpis.total_revenue
        )
        revenue_by_reg = cls.compute_revenue_by_region(
            prepared_df, mapping, total_revenue=kpis.total_revenue
        )

        # 6. Top Products & Top Customers
        top_products = cls.compute_top_products(prepared_df, mapping)
        top_customers = cls.compute_top_customers(prepared_df, mapping)

        # List of supported metrics derived
        supported = ["total_revenue", "total_orders", "average_order_value"]
        if mapping.customer_id_column:
            supported.append("unique_customers")
        if mapping.date_column and revenue_by_month:
            supported.append("revenue_by_month")
            if latest_growth is not None:
                supported.append("growth_percentage")
        if mapping.category_column and revenue_by_cat:
            supported.append("revenue_by_category")
        if mapping.region_column and revenue_by_reg:
            supported.append("revenue_by_region")
        if mapping.product_column and top_products:
            supported.append("top_products")
        if mapping.customer_id_column and top_customers:
            supported.append("top_customers")

        return BusinessAnalyticsResponse(
            dataset_id=dataset_id or uuid.uuid4(),
            mapping=mapping,
            kpis=kpis,
            revenue_by_month=revenue_by_month,
            revenue_by_category=revenue_by_cat,
            revenue_by_region=revenue_by_reg,
            top_products=top_products,
            top_customers=top_customers,
            supported_metrics=supported,
            created_at=datetime.now(timezone.utc),
        )


class AnalyticsService:
    """Service handling dataset analytics orchestration, database caching, and access control."""

    @classmethod
    def get_or_compute_analytics(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
        custom_mapping: Optional[ColumnMappingConfig] = None,
    ) -> BusinessAnalyticsResponse:
        """Fetch cached analytics from Neon or compute on-demand and persist.

        Raises:
            HTTPException(404): If dataset does not exist or user lacks permission.
            HTTPException(400): If dataset is unsupported or invalid.
        """
        # 1. Enforce user access control
        dataset = (
            db.query(Dataset)
            .filter(Dataset.id == dataset_id, Dataset.user_id == user.id)
            .first()
        )
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset with ID '{dataset_id}' not found.",
            )

        # 2. Check if reusable cached result exists when no custom mapping is provided
        is_custom = custom_mapping is not None and any(
            v is not None for v in custom_mapping.model_dump().values()
        )

        if not is_custom:
            cached_result = (
                db.query(AnalyticsResult)
                .filter(
                    AnalyticsResult.dataset_id == dataset.id,
                    AnalyticsResult.analysis_type == "business_analytics",
                )
                .order_by(AnalyticsResult.created_at.desc())
                .first()
            )
            if cached_result and cached_result.result:
                try:
                    return BusinessAnalyticsResponse.model_validate(cached_result.result)
                except Exception as exc:
                    logger.warning("Failed to deserialize cached analytics for %s: %s", dataset.id, exc)

        # 3. Compute analytics on-demand from stored file
        file_path = FileStorageService.get_stored_file_path(dataset.id)
        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset source file is not available on disk for analytics.",
            )

        df = DataProfilerService.load_dataframe(file_path, dataset.file_type)
        analytics_response = AnalyticsEngine.generate_analytics(
            df=df,
            custom_mapping=custom_mapping,
            dataset_id=dataset.id,
        )

        # 4. Cache / persist reusable result in Neon PostgreSQL
        if not is_custom:
            analytics_record = (
                db.query(AnalyticsResult)
                .filter(
                    AnalyticsResult.dataset_id == dataset.id,
                    AnalyticsResult.analysis_type == "business_analytics",
                )
                .first()
            )
            if not analytics_record:
                analytics_record = AnalyticsResult(
                    id=uuid.uuid4(),
                    dataset_id=dataset.id,
                    analysis_type="business_analytics",
                    result=analytics_response.model_dump(mode="json"),
                )
                db.add(analytics_record)
            else:
                analytics_record.result = analytics_response.model_dump(mode="json")
                analytics_record.created_at = datetime.now(timezone.utc)

            try:
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.warning("Failed to cache analytics result in DB: %s", exc)

        return analytics_response
