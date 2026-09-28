from datetime import datetime
import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException

from app.schemas.analytics import ColumnMappingConfig
from app.services.analytics import AnalyticsEngine, ColumnDetector


# =========================================================================
# Unit Tests: ColumnDetector
# =========================================================================

def test_detect_revenue_column_various_names():
    """Verify revenue column is detected across various synonyms and formats."""
    # 1. "sales"
    df1 = pd.DataFrame({"sales": [100.5, 200.0, 300.0], "item": ["A", "B", "C"]})
    assert ColumnDetector.detect_revenue_column(df1) == "sales"

    # 2. "amount"
    df2 = pd.DataFrame({"amount": [50, 75, 125], "customer": ["C1", "C2", "C3"]})
    assert ColumnDetector.detect_revenue_column(df2) == "amount"

    # 3. Currency strings: "$1,500.00"
    df3 = pd.DataFrame({"total_price": ["$1,500.00", "$250.50", "$3,100.25"]})
    assert ColumnDetector.detect_revenue_column(df3) == "total_price"

    # 4. Explicit override takes precedence
    assert ColumnDetector.detect_revenue_column(df1, explicit="sales") == "sales"


def test_detect_date_column_various_names():
    """Verify transaction date column is detected across common naming conventions."""
    df1 = pd.DataFrame({
        "order_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "sales": [10, 20, 30],
    })
    assert ColumnDetector.detect_date_column(df1) == "order_date"

    df2 = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=3),
        "val": [1, 2, 3],
    })
    assert ColumnDetector.detect_date_column(df2) == "timestamp"


def test_detect_categorical_roles():
    """Verify order, customer, category, product, and region columns are identified."""
    df = pd.DataFrame({
        "invoice_no": ["INV-001", "INV-002", "INV-003"],
        "client_name": ["Acme Corp", "Beta LLC", "Gamma Inc"],
        "dept": ["Hardware", "Software", "Hardware"],
        "item_title": ["Laptop Pro", "Cloud License", "Docking Station"],
        "territory": ["EMEA", "APAC", "Americas"],
        "sales_amount": [1200.0, 500.0, 250.0],
    })

    assert ColumnDetector.detect_categorical_role(df, "order_id") == "invoice_no"
    assert ColumnDetector.detect_categorical_role(df, "customer_id") == "client_name"
    assert ColumnDetector.detect_categorical_role(df, "category") == "dept"
    assert ColumnDetector.detect_categorical_role(df, "product") == "item_title"
    assert ColumnDetector.detect_categorical_role(df, "region") == "territory"


def test_resolve_mapping_with_custom_overrides():
    """Verify custom column mappings override auto-detection."""
    df = pd.DataFrame({
        "col_a": [10, 20, 30],
        "col_b": ["2026-01-01", "2026-02-01", "2026-03-01"],
        "col_c": ["Prod1", "Prod2", "Prod3"],
    })

    custom = ColumnMappingConfig(
        revenue_column="col_a",
        date_column="col_b",
        product_column="col_c",
    )
    mapping, _ = ColumnDetector.resolve_mapping(df, custom)

    assert mapping.revenue_column == "col_a"
    assert mapping.date_column == "col_b"
    assert mapping.product_column == "col_c"
    assert mapping.auto_detected is False


# =========================================================================
# Unit Tests: AnalyticsEngine Calculations
# =========================================================================

@pytest.fixture
def sample_business_df():
    """Create a realistic business transaction dataset."""
    return pd.DataFrame({
        "order_id": ["ORD-1", "ORD-2", "ORD-3", "ORD-4", "ORD-5", "ORD-6"],
        "order_date": [
            "2026-01-10",
            "2026-01-20",
            "2026-02-05",
            "2026-02-15",
            "2026-03-01",
            "2026-03-25",
        ],
        "customer": ["Cust_A", "Cust_B", "Cust_A", "Cust_C", "Cust_B", "Cust_A"],
        "product": ["Widget Pro", "Gadget Max", "Widget Pro", "Super Sensor", "Gadget Max", "Widget Pro"],
        "category": ["Electronics", "Electronics", "Electronics", "Hardware", "Electronics", "Electronics"],
        "region": ["North", "South", "North", "East", "South", "North"],
        "sales": [100.0, 200.0, 150.0, 300.0, 250.0, 100.0],
    })


def test_compute_kpis(sample_business_df):
    """Verify calculation of high-level KPIs."""
    df, rev_col = AnalyticsEngine.validate_and_prepare_df(
        sample_business_df,
        ColumnDetector.resolve_mapping(sample_business_df)[0],
    )
    mapping, _ = ColumnDetector.resolve_mapping(sample_business_df)

    kpis = AnalyticsEngine.compute_kpis(df, mapping, monthly_growth=15.5)

    assert kpis.total_revenue == 1100.0  # 100 + 200 + 150 + 300 + 250 + 100
    assert kpis.total_orders == 6
    assert kpis.unique_customers == 3  # Cust_A, Cust_B, Cust_C
    assert kpis.average_order_value == round(1100.0 / 6, 2)
    assert kpis.overall_growth_percentage == 15.5


def test_compute_revenue_by_month_and_growth(sample_business_df):
    """Verify monthly aggregation and month-over-month growth calculations."""
    df, _ = AnalyticsEngine.validate_and_prepare_df(
        sample_business_df,
        ColumnDetector.resolve_mapping(sample_business_df)[0],
    )
    mapping, _ = ColumnDetector.resolve_mapping(sample_business_df)

    monthly_items, latest_growth = AnalyticsEngine.compute_revenue_by_month(df, mapping)

    assert len(monthly_items) == 3
    assert [m.month for m in monthly_items] == ["2026-01", "2026-02", "2026-03"]

    # Jan: 100 + 200 = 300, growth = None
    assert monthly_items[0].revenue == 300.0
    assert monthly_items[0].growth_percentage is None

    # Feb: 150 + 300 = 450, growth = ((450 - 300) / 300) * 100 = 50.0%
    assert monthly_items[1].revenue == 450.0
    assert monthly_items[1].growth_percentage == 50.0

    # Mar: 250 + 100 = 350, growth = ((350 - 450) / 450) * 100 = -22.22%
    assert monthly_items[2].revenue == 350.0
    assert monthly_items[2].growth_percentage == round(((350.0 - 450.0) / 450.0) * 100.0, 2)

    assert latest_growth == monthly_items[2].growth_percentage


def test_compute_revenue_by_category(sample_business_df):
    """Verify category revenue distribution and percentage shares."""
    df, _ = AnalyticsEngine.validate_and_prepare_df(
        sample_business_df,
        ColumnDetector.resolve_mapping(sample_business_df)[0],
    )
    mapping, _ = ColumnDetector.resolve_mapping(sample_business_df)

    cat_items = AnalyticsEngine.compute_revenue_by_category(df, mapping, total_revenue=1100.0)

    assert len(cat_items) == 2
    # Electronics: 100+200+150+250+100 = 800 (72.73%)
    assert cat_items[0].category == "Electronics"
    assert cat_items[0].revenue == 800.0
    assert cat_items[0].percentage == round((800.0 / 1100.0) * 100.0, 2)

    # Hardware: 300 (27.27%)
    assert cat_items[1].category == "Hardware"
    assert cat_items[1].revenue == 300.0
    assert cat_items[1].percentage == round((300.0 / 1100.0) * 100.0, 2)


def test_compute_revenue_by_region(sample_business_df):
    """Verify regional revenue distribution."""
    df, _ = AnalyticsEngine.validate_and_prepare_df(
        sample_business_df,
        ColumnDetector.resolve_mapping(sample_business_df)[0],
    )
    mapping, _ = ColumnDetector.resolve_mapping(sample_business_df)

    reg_items = AnalyticsEngine.compute_revenue_by_region(df, mapping, total_revenue=1100.0)

    assert len(reg_items) == 3
    # South: 200 + 250 = 450
    # North: 100 + 150 + 100 = 350
    # East: 300
    regions = {r.region: r.revenue for r in reg_items}
    assert regions["South"] == 450.0
    assert regions["North"] == 350.0
    assert regions["East"] == 300.0


def test_compute_top_products_and_customers(sample_business_df):
    """Verify product and customer leaderboards."""
    df, _ = AnalyticsEngine.validate_and_prepare_df(
        sample_business_df,
        ColumnDetector.resolve_mapping(sample_business_df)[0],
    )
    mapping, _ = ColumnDetector.resolve_mapping(sample_business_df)

    # Top products
    top_prods = AnalyticsEngine.compute_top_products(df, mapping)
    assert top_prods[0].product == "Gadget Max"
    assert top_prods[0].revenue == 450.0  # 200 + 250
    assert top_prods[1].product == "Widget Pro"
    assert top_prods[1].revenue == 350.0  # 100 + 150 + 100

    # Top customers
    top_custs = AnalyticsEngine.compute_top_customers(df, mapping)
    assert top_custs[0].customer == "Cust_B"
    assert top_custs[0].revenue == 450.0  # 200 + 250
    assert top_custs[1].customer == "Cust_A"
    assert top_custs[1].revenue == 350.0  # 100 + 150 + 100


def test_generate_analytics_full_pipeline(sample_business_df):
    """Verify full end-to-end analytics generation returning React chart payloads."""
    result = AnalyticsEngine.generate_analytics(sample_business_df)

    assert result.kpis.total_revenue == 1100.0
    assert len(result.revenue_by_month) == 3
    assert len(result.revenue_by_category) == 2
    assert len(result.revenue_by_region) == 3
    assert len(result.top_products) == 3
    assert len(result.top_customers) == 3
    assert "revenue_by_month" in result.supported_metrics
    assert "revenue_by_category" in result.supported_metrics


# =========================================================================
# Unit Tests: Error Handling & Unsupported Datasets
# =========================================================================

def test_empty_dataframe_rejected():
    """Verify empty DataFrame raises 400 error."""
    df = pd.DataFrame()
    with pytest.raises(HTTPException) as exc:
        AnalyticsEngine.generate_analytics(df)
    assert exc.value.status_code == 400
    assert "empty" in exc.value.detail.lower()


def test_no_numeric_revenue_column_rejected():
    """Verify dataset with purely text columns raises 400 error."""
    df = pd.DataFrame({
        "name": ["Alice", "Bob"],
        "city": ["New York", "London"],
        "comments": ["Good", "Great"],
    })
    with pytest.raises(HTTPException) as exc:
        AnalyticsEngine.generate_analytics(df)
    assert exc.value.status_code == 400
    assert "could not detect a revenue" in exc.value.detail.lower()


def test_dataset_with_only_revenue_column_succeeds():
    """Verify dataset with only revenue column calculates KPIs without crashing."""
    df = pd.DataFrame({"sales": [50.0, 150.0, 200.0]})
    result = AnalyticsEngine.generate_analytics(df)

    assert result.kpis.total_revenue == 400.0
    assert result.kpis.total_orders == 3
    assert result.revenue_by_month == []
    assert result.revenue_by_category == []
    assert result.revenue_by_region == []
