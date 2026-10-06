from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
import httpx
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analytics_result import AnalyticsResult
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.ai_insights import AiInsightsResponse
from app.schemas.analytics import DatasetAnalyticsResponse
from app.services.analytics import AnalyticsService
from app.services.dataset import DatasetService
from app.services.file_storage import FileStorageService
from app.services.profiler import DataProfilerService

logger = logging.getLogger(__name__)


class AiInsightsService:
    """AI natural language insights engine grounded strictly in verified analytics."""

    @classmethod
    def get_or_generate_insights(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
        use_cache: bool = True,
    ) -> AiInsightsResponse:
        """Generate or retrieve cached natural language AI insights.

        Guaranteed:
        1. Only runs AFTER normal analytics successfully computes verified metrics.
        2. AI only explains existing analytical results, never calculating fundamental metrics.
        3. Persists reusable results in Neon PostgreSQL.
        """
        # 1. Verify dataset access and ownership
        dataset = DatasetService.get_dataset(db=db, user=user, dataset_id=dataset_id)

        # 2. Check for cached AI insights
        if use_cache:
            cached = (
                db.query(AnalyticsResult)
                .filter(
                    AnalyticsResult.dataset_id == dataset.id,
                    AnalyticsResult.analysis_type == "ai_insights",
                )
                .first()
            )
            if cached and isinstance(cached.result, dict):
                try:
                    return AiInsightsResponse(
                        dataset_id=dataset.id,
                        headline=cached.result["headline"],
                        summary=cached.result["summary"],
                        key_drivers=cached.result.get("key_drivers", []),
                        category_insight=cached.result.get("category_insight"),
                        regional_insight=cached.result.get("regional_insight"),
                        recommendations=cached.result.get("recommendations", []),
                        verified_facts=cached.result.get("verified_facts", {}),
                        provider=cached.result.get("provider", "grounded_engine"),
                        created_at=cached.created_at,
                    )
                except Exception as exc:
                    logger.warning("Failed to deserialize cached AI insights: %s", exc)

        # 3. Step 1 of Pipeline: Normal Analytics must execute first (SQL/Pandas)
        try:
            analytics = AnalyticsService.get_or_compute_analytics(
                db=db,
                user=user,
                dataset_id=dataset.id,
                use_cache=use_cache,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Failed running normal analytics prior to AI insights: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI Insights requires normal analytics to be calculated first. Ensure dataset contains valid numeric data.",
            )

        if not analytics or analytics.kpis.total_revenue <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI Insights requires valid revenue and business metrics. No revenue was detected in this dataset.",
            )

        # 4. Step 2 of Pipeline: Extract Verified Period, Category & Region Drivers
        verified_facts = cls._extract_verified_drivers(dataset, analytics)

        # 5. Step 3 of Pipeline: Generate Natural Language Explanation
        insights_data, provider = cls._generate_explanation(verified_facts)

        now = datetime.now(timezone.utc)
        result_payload = {
            "headline": insights_data["headline"],
            "summary": insights_data["summary"],
            "key_drivers": insights_data["key_drivers"],
            "category_insight": insights_data.get("category_insight"),
            "regional_insight": insights_data.get("regional_insight"),
            "recommendations": insights_data.get("recommendations", []),
            "verified_facts": verified_facts,
            "provider": provider,
        }

        # 6. Store in Neon PostgreSQL (analytics_results)
        cached_record = (
            db.query(AnalyticsResult)
            .filter(
                AnalyticsResult.dataset_id == dataset.id,
                AnalyticsResult.analysis_type == "ai_insights",
            )
            .first()
        )
        if cached_record:
            cached_record.result = result_payload
            cached_record.created_at = now
        else:
            cached_record = AnalyticsResult(
                id=uuid.uuid4(),
                dataset_id=dataset.id,
                analysis_type="ai_insights",
                result=result_payload,
                created_at=now,
            )
            db.add(cached_record)

        try:
            db.commit()
            db.refresh(cached_record)
        except Exception as exc:
            db.rollback()
            logger.warning("Could not persist AI insights record: %s", exc)

        return AiInsightsResponse(
            dataset_id=dataset.id,
            headline=result_payload["headline"],
            summary=result_payload["summary"],
            key_drivers=result_payload["key_drivers"],
            category_insight=result_payload["category_insight"],
            regional_insight=result_payload["regional_insight"],
            recommendations=result_payload["recommendations"],
            verified_facts=verified_facts,
            provider=provider,
            created_at=now,
        )

    @classmethod
    def _extract_verified_drivers(
        cls,
        dataset: Dataset,
        analytics: DatasetAnalyticsResponse,
    ) -> Dict[str, Any]:
        """Compute verified period-over-period category and regional breakdowns with Pandas."""
        kpis = analytics.kpis
        months = analytics.revenue_by_month
        categories = analytics.revenue_by_category
        regions = analytics.revenue_by_region
        growth_summary = analytics.growth_summary
        mapping = analytics.column_mapping

        facts: Dict[str, Any] = {
            "dataset_name": dataset.name,
            "total_revenue": kpis.total_revenue,
            "total_orders": kpis.total_orders,
            "average_order_value": kpis.average_order_value,
            "unique_customers": kpis.unique_customers,
            "overall_growth_percentage": kpis.growth_percentage,
            "has_date_trend": len(months) >= 2,
            "period_trend": None,
            "category_driver": None,
            "region_driver": None,
            "top_categories": [
                {"name": c.category, "revenue": c.revenue, "percentage": c.percentage}
                for c in categories[:3]
            ],
            "top_regions": [
                {"name": r.region, "revenue": r.revenue, "percentage": r.percentage}
                for r in regions[:3]
            ],
            "top_product": analytics.top_products[0].product if analytics.top_products else None,
            "top_customer": analytics.top_customers[0].customer if analytics.top_customers else None,
        }

        # 1. Period comparison trend
        if len(months) >= 2:
            latest = months[-1]
            prior = months[-2]
            growth_pct = latest.growth_percentage or 0.0
            direction = "decreased" if growth_pct < 0 else ("increased" if growth_pct > 0 else "remained flat")

            facts["period_trend"] = {
                "current_period": latest.period,
                "previous_period": prior.period,
                "current_revenue": latest.revenue,
                "previous_revenue": prior.revenue,
                "revenue_change": round(latest.revenue - prior.revenue, 2),
                "growth_percentage": growth_pct,
                "direction": direction,
            }

            # 2. Extract Category and Regional Contributors using Pandas if columns exist
            file_path = FileStorageService.get_stored_file_path(dataset.id)
            if file_path and file_path.exists():
                try:
                    df = DataProfilerService.load_dataframe(file_path, dataset.file_type)
                    cls._compute_period_breakdown(df, mapping, latest.period, prior.period, facts)
                except Exception as exc:
                    logger.warning("Could not compute detailed period breakdown: %s", exc)

        # 3. Fallback / General category and region drivers if no date or breakdown
        if not facts.get("category_driver") and categories:
            top_cat = categories[0]
            facts["category_driver"] = {
                "name": top_cat.category,
                "share_percentage": top_cat.percentage,
                "revenue": top_cat.revenue,
                "orders": top_cat.orders,
                "is_dominant": top_cat.percentage >= 30.0,
            }

        if not facts.get("region_driver") and regions:
            top_reg = regions[0]
            facts["region_driver"] = {
                "name": top_reg.region,
                "share_percentage": top_reg.percentage,
                "revenue": top_reg.revenue,
                "orders": top_reg.orders,
                "is_dominant": top_reg.percentage >= 30.0,
            }

        return facts

    @classmethod
    def _compute_period_breakdown(
        cls,
        df: pd.DataFrame,
        mapping: Any,
        current_period: str,
        prior_period: str,
        facts: Dict[str, Any],
    ) -> None:
        """Inspect latest vs prior period subsets to identify exact contributor categories & regions."""
        date_col = getattr(mapping, "date_column", None)
        rev_col = getattr(mapping, "revenue_column", None)
        cat_col = getattr(mapping, "category_column", None)
        reg_col = getattr(mapping, "region_column", None)

        if not (date_col and rev_col and date_col in df.columns and rev_col in df.columns):
            return

        # Prepare date series and periods
        parsed_dates = pd.to_datetime(df[date_col], errors="coerce")
        df_copy = df.copy()
        df_copy["_date"] = parsed_dates
        df_copy["_rev"] = pd.to_numeric(df[rev_col], errors="coerce").fillna(0)
        df_copy["_period"] = df_copy["_date"].dt.to_period("M").astype(str)

        curr_df = df_copy[df_copy["_period"] == current_period]
        prior_df = df_copy[df_copy["_period"] == prior_period]

        if curr_df.empty or prior_df.empty:
            return

        is_decline = facts["period_trend"]["growth_percentage"] < 0

        # Category Breakdown
        if cat_col and cat_col in df_copy.columns:
            curr_cat = curr_df.groupby(cat_col)["_rev"].sum()
            prior_cat = prior_df.groupby(cat_col)["_rev"].sum()

            cat_diffs = []
            for cat in set(curr_cat.index).union(prior_cat.index):
                c_curr = curr_cat.get(cat, 0.0)
                c_prev = prior_cat.get(cat, 0.0)
                diff = c_curr - c_prev
                pct = ((c_curr - c_prev) / c_prev * 100.0) if c_prev > 0 else (100.0 if c_curr > 0 else 0.0)
                cat_diffs.append({
                    "name": str(cat),
                    "current": round(float(c_curr), 2),
                    "prior": round(float(c_prev), 2),
                    "diff": round(float(diff), 2),
                    "pct_change": round(float(pct), 1),
                })

            if cat_diffs:
                if is_decline:
                    # Contributed most to decline (most negative diff)
                    target = min(cat_diffs, key=lambda x: x["diff"])
                    facts["category_driver"] = {
                        "name": target["name"],
                        "change_direction": "declined",
                        "percentage": abs(target["pct_change"]),
                        "diff": target["diff"],
                        "is_largest_contributor": True,
                    }
                else:
                    # Contributed most to growth (most positive diff)
                    target = max(cat_diffs, key=lambda x: x["diff"])
                    facts["category_driver"] = {
                        "name": target["name"],
                        "change_direction": "increased",
                        "percentage": target["pct_change"],
                        "diff": target["diff"],
                        "is_largest_contributor": True,
                    }

        # Region Breakdown
        if reg_col and reg_col in df_copy.columns:
            curr_reg = curr_df.groupby(reg_col)["_rev"].sum()
            prior_reg = prior_df.groupby(reg_col)["_rev"].sum()

            reg_diffs = []
            for reg in set(curr_reg.index).union(prior_reg.index):
                r_curr = curr_reg.get(reg, 0.0)
                r_prev = prior_reg.get(reg, 0.0)
                diff = r_curr - r_prev
                pct = ((r_curr - r_prev) / r_prev * 100.0) if r_prev > 0 else (100.0 if r_curr > 0 else 0.0)
                reg_diffs.append({
                    "name": str(reg),
                    "current": round(float(r_curr), 2),
                    "prior": round(float(r_prev), 2),
                    "diff": round(float(diff), 2),
                    "pct_change": round(float(pct), 1),
                })

            if reg_diffs:
                if is_decline:
                    target = min(reg_diffs, key=lambda x: x["diff"])
                    facts["region_driver"] = {
                        "name": target["name"],
                        "change_direction": "declined",
                        "diff": target["diff"],
                        "is_largest_portion": True,
                    }
                else:
                    target = max(reg_diffs, key=lambda x: x["diff"])
                    facts["region_driver"] = {
                        "name": target["name"],
                        "change_direction": "increased",
                        "diff": target["diff"],
                        "is_largest_portion": True,
                    }

    @classmethod
    def _generate_explanation(cls, facts: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Generate structured business natural language explanations.

        Uses LLM (Gemini/OpenAI) if API key is provided; otherwise seamlessly uses
        the verified Grounded Narrative Engine.
        """
        # Try external LLM if API key configured
        if settings.GEMINI_API_KEY:
            try:
                llm_res = cls._call_gemini_api(facts, settings.GEMINI_API_KEY)
                if llm_res:
                    return llm_res, "gemini"
            except Exception as exc:
                logger.warning("Gemini API call failed; falling back to grounded narrative engine: %s", exc)

        elif settings.OPENAI_API_KEY:
            try:
                llm_res = cls._call_openai_api(facts, settings.OPENAI_API_KEY)
                if llm_res:
                    return llm_res, "openai"
            except Exception as exc:
                logger.warning("OpenAI API call failed; falling back to grounded narrative engine: %s", exc)

        # Grounded Narrative Engine (deterministic, verified, 100% grounded in facts)
        return cls._build_grounded_narrative(facts), "grounded_engine"

    @classmethod
    def _build_grounded_narrative(cls, facts: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize natural language explanations matching exact user business expectations."""
        period_trend = facts.get("period_trend")
        cat_driver = facts.get("category_driver")
        reg_driver = facts.get("region_driver")
        total_rev = facts["total_revenue"]
        total_orders = facts["total_orders"]
        aov = facts["average_order_value"]
        top_product = facts.get("top_product")
        top_customer = facts.get("top_customer")

        # 1. Headline
        if period_trend:
            pct = abs(period_trend["growth_percentage"])
            direction = period_trend["direction"]
            period = period_trend["current_period"]
            headline = f"Revenue {direction} {pct:.1f}% in {period}."
        else:
            headline = f"Total revenue reached ${total_rev:,.2f} across {total_orders:,} transactions."

        # 2. Category Insight
        category_insight = None
        if cat_driver:
            cat_name = cat_driver["name"]
            if "percentage" in cat_driver:
                pct = cat_driver["percentage"]
                direction = cat_driver.get("change_direction", "changed")
                category_insight = f"The largest contribution came from the {cat_name} category, which {direction} {pct:.1f}%."
            elif "share_percentage" in cat_driver:
                share = cat_driver["share_percentage"]
                category_insight = f"The largest contribution came from the {cat_name} category, representing {share:.1f}% of overall sales."

        # 3. Regional Insight
        regional_insight = None
        if reg_driver:
            reg_name = reg_driver["name"]
            if "change_direction" in reg_driver:
                direction_noun = "decline" if reg_driver["change_direction"] == "declined" else "growth"
                regional_insight = f"The {reg_name} region accounted for the largest portion of the {direction_noun}."
            elif "share_percentage" in reg_driver:
                share = reg_driver["share_percentage"]
                regional_insight = f"The {reg_name} region accounted for the largest portion of sales at {share:.1f}%."

        # 4. Summary Narrative (Cohesive Executive Explanation)
        summary_sentences = [headline]
        if category_insight:
            summary_sentences.append(category_insight)
        if regional_insight:
            summary_sentences.append(regional_insight)

        summary_sentences.append(
            f"Overall transaction volume reflects {total_orders:,} total orders with an average order value of ${aov:,.2f}."
        )
        summary = " ".join(summary_sentences)

        # 5. Key Drivers (Bulleted facts)
        key_drivers = []
        if period_trend:
            key_drivers.append(
                f"Period Revenue: ${period_trend['current_revenue']:,.2f} vs ${period_trend['previous_revenue']:,.2f} previously ({period_trend['revenue_change']:+,.2f})."
            )
        if category_insight:
            key_drivers.append(category_insight)
        if regional_insight:
            key_drivers.append(regional_insight)
        if top_product:
            key_drivers.append(f"Top performing product by volume and sales: {top_product}.")
        if top_customer:
            key_drivers.append(f"Primary account contributor: {top_customer}.")

        # 6. Actionable Data-Grounded Recommendations
        recommendations = []
        if period_trend and period_trend["growth_percentage"] < 0:
            if cat_driver:
                recommendations.append(
                    f"Initiate promotional campaign and inventory review for '{cat_driver['name']}' to mitigate the recent {cat_driver.get('percentage', 0):.1f}% contraction."
                )
            if reg_driver:
                recommendations.append(
                    f"Perform regional audit in the '{reg_driver['name']}' territory to identify distribution or competitive pressures."
                )
            recommendations.append(
                f"Target high-value repeat buyers to protect the current ${aov:,.2f} average order value baseline."
            )
        else:
            if cat_driver:
                recommendations.append(
                    f"Allocate increased marketing budget to expand market share in '{cat_driver['name']}'."
                )
            if reg_driver:
                recommendations.append(
                    f"Replicate successful sales methodologies from the '{reg_driver['name']}' region into secondary regions."
                )
            recommendations.append(
                f"Implement cross-selling bundles to boost the current average order value above ${aov:,.2f}."
            )

        return {
            "headline": headline,
            "summary": summary,
            "category_insight": category_insight,
            "regional_insight": regional_insight,
            "key_drivers": key_drivers,
            "recommendations": recommendations,
        }

    @classmethod
    def _call_gemini_api(cls, facts: Dict[str, Any], api_key: str) -> Optional[Dict[str, Any]]:
        """Call Google Gemini to generate natural language explanations grounded strictly in facts."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={api_key}"

        prompt = f"""
You are the Chief Analytics Officer for InsightFlow.
Explain these VERIFIED analytical results to executive stakeholders in clear, natural language.

CRITICAL RULES:
1. Explain ONLY the verified analytical results provided below.
2. NEVER calculate or guess fundamental metrics; all numbers are already verified by Pandas/SQL.
3. Be concise, direct, and authoritative (like Linear or Stripe executive reports).

VERIFIED METRICS:
{json.dumps(facts, indent=2)}

Respond with a JSON object conforming exactly to this schema:
{{
  "headline": "Short single sentence headline (e.g. Revenue decreased 12.4% in March.)",
  "category_insight": "The largest contribution came from...",
  "regional_insight": "The West region accounted for...",
  "summary": "Full cohesive 2-3 sentence executive paragraph.",
  "key_drivers": ["bullet 1", "bullet 2", "bullet 3"],
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"]
}}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        with httpx.Client(timeout=10.0) as client:
            res = client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
        return None

    @classmethod
    def _call_openai_api(cls, facts: Dict[str, Any], api_key: str) -> Optional[Dict[str, Any]]:
        """Call OpenAI to generate natural language explanations grounded strictly in facts."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        prompt = f"""
You are the Chief Analytics Officer for InsightFlow.
Explain these VERIFIED analytical results to executive stakeholders in clear, natural language.
Explain existing results. Do not calculate fundamental metrics.

VERIFIED METRICS:
{json.dumps(facts, indent=2)}

Return JSON:
{{
  "headline": "Short single sentence headline",
  "category_insight": "Category explanation",
  "regional_insight": "Regional explanation",
  "summary": "Full cohesive executive paragraph.",
  "key_drivers": ["bullet 1", "bullet 2"],
  "recommendations": ["action 1", "action 2"]
}}
"""
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        with httpx.Client(timeout=10.0) as client:
            res = client.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        return None
