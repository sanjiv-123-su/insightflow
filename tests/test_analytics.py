import io
from pathlib import Path
import uuid
import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.analytics_result import AnalyticsResult
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.analytics import ColumnMappingInput, DetectedColumnMapping
from app.services.analytics import AnalyticsEngine, AnalyticsService

# Isolated in-memory SQLite database for analytics tests
analytics_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
AnalyticsTestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=analytics_engine)


def override_analytics_get_db():
    db = AnalyticsTestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_analytics_test(tmp_path, monkeypatch):
    """Setup isolated database and temporary uploads directory for each test."""
    Base.metadata.create_all(bind=analytics_engine)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    app.dependency_overrides[get_db] = override_analytics_get_db
    yield
    Base.metadata.drop_all(bind=analytics_engine)
    app.dependency_overrides.pop(get_db, None)


def register_and_login(email: str = "analyst@insightflow.io", password: str = "StrongPassword123!") -> dict:
    """Helper to register and login a user, returning auth headers and user info."""
    client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "email": email,
    }


def create_business_csv() -> io.BytesIO:
    """Generate in-memory CSV with common e-commerce business data."""
    data = [
        "order_id,customer_id,order_date,amount,category,region,product_name,quantity",
        "ORD-001,CUST-A,2026-01-10,120.00,Electronics,North,Wireless Mouse,2",
        "ORD-002,CUST-B,2026-01-15,450.00,Electronics,West,Mechanical Keyboard,1",
        "ORD-003,CUST-A,2026-02-05,200.00,Office,North,Ergonomic Chair,1",
        "ORD-004,CUST-C,2026-02-18,150.00,Furniture,South,Desk Lamp,3",
        "ORD-005,CUST-B,2026-03-01,800.00,Electronics,West,4K Monitor,1",
        "ORD-006,CUST-D,2026-03-12,300.00,Office,East,Standing Desk,1",
    ]
    return io.BytesIO("\n".join(data).encode("utf-8"))


# =========================================================================
# Unit Tests: Column Detection
# =========================================================================

def test_detect_columns_standard_names():
    """Verify detection with standard column naming conventions."""
    df = pd.DataFrame({
        "order_id": [1, 2],
        "customer_id": ["C1", "C2"],
        "order_date": ["2026-01-01", "2026-01-02"],
        "sales_amount": [100.5, 200.0],
        "product_category": ["Tech", "Home"],
        "region": ["East", "West"],
        "product_name": ["Widget A", "Widget B"],
        "quantity": [2, 1],
    })

    mapping = AnalyticsEngine.detect_columns(df)
    assert mapping.revenue_column == "sales_amount"
    assert mapping.order_id_column == "order_id"
    assert mapping.customer_column == "customer_id"
    assert mapping.date_column == "order_date"
    assert mapping.category_column == "product_category"
    assert mapping.region_column == "region"
    assert mapping.product_column == "product_name"
    assert mapping.quantity_column == "quantity"
    assert mapping.detected_automatically is True


def test_detect_columns_alternative_names():
    """Verify detection with alternative names like invoice, client, price, department, etc."""
    df = pd.DataFrame({
        "invoice_no": [101, 102],
        "client_email": ["a@test.com", "b@test.com"],
        "timestamp": ["2026-02-01", "2026-02-02"],
        "price": [45.0, 90.0],
        "department": ["Shoes", "Apparel"],
        "country": ["USA", "Canada"],
        "item_title": ["Sneakers", "Jacket"],
        "qty": [1, 3],
    })

    mapping = AnalyticsEngine.detect_columns(df)
    assert mapping.revenue_column == "price"
    assert mapping.order_id_column == "invoice_no"
    assert mapping.customer_column == "client_email"
    assert mapping.date_column == "timestamp"
    assert mapping.category_column == "department"
    assert mapping.region_column == "country"
    assert mapping.product_column == "item_title"
    assert mapping.quantity_column == "qty"


def test_detect_columns_user_overrides():
    """Verify user overrides take precedence over heuristic detection."""
    df = pd.DataFrame({
        "col_a": [10.0, 20.0],
        "col_b": [100.0, 200.0],
        "col_c": ["2026-01-01", "2026-01-02"],
    })

    overrides = ColumnMappingInput(
        revenue_column="col_b",
        date_column="col_c",
    )
    mapping = AnalyticsEngine.detect_columns(df, overrides=overrides)
    assert mapping.revenue_column == "col_b"
    assert mapping.date_column == "col_c"
    assert mapping.detected_automatically is False


# =========================================================================
# Unit Tests: Column Validation
# =========================================================================

def test_validate_mapping_missing_revenue_column():
    """Verify validation fails if no revenue column could be identified."""
    df = pd.DataFrame({
        "text_1": ["foo", "bar"],
        "text_2": ["baz", "qux"],
    })
    mapping = DetectedColumnMapping(revenue_column=None)

    with pytest.raises(HTTPException) as exc:
        AnalyticsEngine.validate_mapping(df, mapping)
    assert exc.value.status_code == 400
    assert "no revenue" in exc.value.detail.lower()


def test_validate_mapping_nonexistent_column_override():
    """Verify validation fails if user specifies a non-existent column."""
    df = pd.DataFrame({"sales": [10, 20]})
    mapping = DetectedColumnMapping(revenue_column="non_existent")

    with pytest.raises(HTTPException) as exc:
        AnalyticsEngine.validate_mapping(df, mapping)
    assert exc.value.status_code == 400
    assert "does not exist" in exc.value.detail.lower()


def test_validate_mapping_non_numeric_revenue_column():
    """Verify validation fails if mapped revenue column is non-numeric."""
    df = pd.DataFrame({"description": ["apple", "banana", "orange"]})
    mapping = DetectedColumnMapping(revenue_column="description")

    with pytest.raises(HTTPException) as exc:
        AnalyticsEngine.validate_mapping(df, mapping)
    assert exc.value.status_code == 400
    assert "no valid numeric values" in exc.value.detail.lower()


# =========================================================================
# Unit Tests: Analytics Calculations
# =========================================================================

def test_calculate_analytics_full_metrics():
    """Verify complete business metrics calculations, groupings, and growth rates."""
    df = pd.DataFrame({
        "order_id": ["O1", "O2", "O3", "O4"],
        "customer": ["Alice", "Bob", "Alice", "Charlie"],
        "date": ["2026-01-10", "2026-01-20", "2026-02-15", "2026-02-25"],
        "revenue": [100.0, 200.0, 300.0, 400.0],
        "category": ["Electronics", "Books", "Electronics", "Books"],
        "region": ["North", "North", "South", "South"],
        "product": ["Phone", "Novel", "Laptop", "Textbook"],
        "qty": [1, 2, 1, 4],
    })

    mapping = AnalyticsEngine.detect_columns(df)
    results = AnalyticsEngine.calculate_analytics(df, mapping)

    # 1. KPIs
    kpis = results["kpis"]
    assert kpis["total_revenue"] == 1000.0
    assert kpis["total_orders"] == 4
    assert kpis["unique_customers"] == 3
    assert kpis["average_order_value"] == 250.0
    assert kpis["growth_percentage"] == 133.33  # Jan: 300, Feb: 700 -> (700-300)/300 = 133.33%

    # 2. Revenue by month
    monthly = results["revenue_by_month"]
    assert len(monthly) == 2
    assert monthly[0]["period"] == "2026-01"
    assert monthly[0]["revenue"] == 300.0
    assert monthly[0]["orders"] == 2
    assert monthly[0]["growth_percentage"] is None

    assert monthly[1]["period"] == "2026-02"
    assert monthly[1]["revenue"] == 700.0
    assert monthly[1]["orders"] == 2
    assert monthly[1]["growth_percentage"] == 133.33

    # 3. Growth summary
    growth = results["growth_summary"]
    assert growth is not None
    assert growth["current_period"] == "2026-02"
    assert growth["previous_period"] == "2026-01"
    assert growth["growth_percentage"] == 133.33
    assert growth["trend"] == "positive"

    # 4. Revenue by category
    cats = results["revenue_by_category"]
    assert len(cats) == 2
    assert cats[0]["category"] == "Books"  # 200 + 400 = 600
    assert cats[0]["revenue"] == 600.0
    assert cats[0]["percentage"] == 60.0

    assert cats[1]["category"] == "Electronics"  # 100 + 300 = 400
    assert cats[1]["revenue"] == 400.0
    assert cats[1]["percentage"] == 40.0

    # 5. Revenue by region
    regs = results["revenue_by_region"]
    assert len(regs) == 2
    assert regs[0]["region"] == "South"
    assert regs[0]["revenue"] == 700.0
    assert regs[0]["percentage"] == 70.0

    # 6. Top products
    prods = results["top_products"]
    assert len(prods) == 4
    assert prods[0]["product"] == "Textbook"
    assert prods[0]["revenue"] == 400.0
    assert prods[0]["units_sold"] == 4

    # 7. Top customers
    custs = results["top_customers"]
    assert len(custs) == 3
    # Alice and Charlie both have 400
    assert custs[0]["revenue"] == 400.0


def test_calculate_analytics_single_month():
    """Verify single month data does not crash and handles growth gracefully."""
    df = pd.DataFrame({
        "date": ["2026-03-01", "2026-03-15"],
        "sales": [50.0, 150.0],
    })
    mapping = AnalyticsEngine.detect_columns(df)
    results = AnalyticsEngine.calculate_analytics(df, mapping)

    assert results["kpis"]["total_revenue"] == 200.0
    assert results["kpis"]["growth_percentage"] is None
    assert results["growth_summary"] is None
    assert len(results["revenue_by_month"]) == 1
    assert results["revenue_by_month"][0]["growth_percentage"] is None


# =========================================================================
# Integration Tests: API Endpoints
# =========================================================================

def test_get_dataset_analytics_success():
    """Verify GET /datasets/{id}/analytics auto-detects and returns full business data."""
    auth = register_and_login("analytics_user@insightflow.io")
    csv_file = create_business_csv()

    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("ecommerce.csv", csv_file, "text/csv")},
        headers=auth["headers"],
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["id"]

    res = client.get(f"/datasets/{dataset_id}/analytics", headers=auth["headers"])
    assert res.status_code == 200
    data = res.json()

    assert data["dataset_id"] == dataset_id
    assert "kpis" in data
    assert data["kpis"]["total_revenue"] == 2020.0
    assert data["kpis"]["total_orders"] == 6
    assert data["kpis"]["unique_customers"] == 4
    assert data["kpis"]["average_order_value"] == 336.67

    assert len(data["revenue_by_month"]) == 3  # Jan, Feb, Mar
    assert len(data["revenue_by_category"]) >= 3
    assert len(data["revenue_by_region"]) >= 3
    assert len(data["top_products"]) >= 4
    assert len(data["top_customers"]) == 4

    assert data["column_mapping"]["revenue_column"] == "amount"
    assert data["column_mapping"]["date_column"] == "order_date"

    # Verify cached in database
    with AnalyticsTestingSessionLocal() as db:
        cached = (
            db.query(AnalyticsResult)
            .filter(
                AnalyticsResult.dataset_id == uuid.UUID(dataset_id),
                AnalyticsResult.analysis_type == "business_overview",
            )
            .first()
        )
        assert cached is not None
        assert cached.result["kpis"]["total_revenue"] == 2020.0


def test_post_dataset_analytics_with_mapping_override():
    """Verify POST /datasets/{id}/analytics recalculates with custom column mapping."""
    auth = register_and_login("override_user@insightflow.io")
    # Dataset with 2 numeric columns: price and shipping_cost
    csv_data = (
        "order_num,price,shipping_cost,tag\n"
        "101,100,10,A\n"
        "102,200,20,B\n"
    )
    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("fees.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
        headers=auth["headers"],
    )
    dataset_id = upload_res.json()["id"]

    # 1. Default should pick price (higher revenue keyword match)
    default_res = client.get(f"/datasets/{dataset_id}/analytics", headers=auth["headers"])
    assert default_res.status_code == 200
    assert default_res.json()["kpis"]["total_revenue"] == 300.0

    # 2. Override revenue to shipping_cost via POST
    override_payload = {
        "revenue_column": "shipping_cost",
        "order_id_column": "order_num",
        "category_column": "tag",
    }
    post_res = client.post(
        f"/datasets/{dataset_id}/analytics",
        json=override_payload,
        headers=auth["headers"],
    )
    assert post_res.status_code == 200
    overridden_data = post_res.json()
    assert overridden_data["kpis"]["total_revenue"] == 30.0  # 10 + 20
    assert overridden_data["column_mapping"]["revenue_column"] == "shipping_cost"
    assert overridden_data["column_mapping"]["detected_automatically"] is False


def test_get_dataset_analytics_mapping_preview():
    """Verify GET /datasets/{id}/analytics/mapping returns detected candidate mapping."""
    auth = register_and_login("mapping_preview@insightflow.io")
    csv_file = create_business_csv()

    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("preview.csv", csv_file, "text/csv")},
        headers=auth["headers"],
    )
    dataset_id = upload_res.json()["id"]

    res = client.get(f"/datasets/{dataset_id}/analytics/mapping", headers=auth["headers"])
    assert res.status_code == 200
    data = res.json()

    assert data["revenue_column"] == "amount"
    assert data["date_column"] == "order_date"
    assert data["order_id_column"] == "order_id"
    assert data["customer_column"] == "customer_id"
    assert "amount" in data["available_numeric_columns"]
    assert "order_date" in data["available_date_columns"]


def test_analytics_auth_and_isolation():
    """Verify analytics endpoints require auth and protect cross-user data."""
    user_a = register_and_login("alice_ana@insightflow.io")
    user_b = register_and_login("bob_ana@insightflow.io")

    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("biz.csv", create_business_csv(), "text/csv")},
        headers=user_a["headers"],
    )
    dataset_id = upload_res.json()["id"]

    # 1. Unauthenticated -> 401
    assert client.get(f"/datasets/{dataset_id}/analytics").status_code == 401
    assert client.post(f"/datasets/{dataset_id}/analytics").status_code == 401
    assert client.get(f"/datasets/{dataset_id}/analytics/mapping").status_code == 401

    # 2. Other user -> 404
    assert client.get(f"/datasets/{dataset_id}/analytics", headers=user_b["headers"]).status_code == 404
    assert client.post(f"/datasets/{dataset_id}/analytics", json={}, headers=user_b["headers"]).status_code == 404
    assert client.get(f"/datasets/{dataset_id}/analytics/mapping", headers=user_b["headers"]).status_code == 404


def test_analytics_unsupported_dataset():
    """Verify non-business dataset without numeric columns returns 400 Bad Request."""
    auth = register_and_login("unsupported@insightflow.io")
    text_only_csv = "first_name,last_name,city\nJohn,Doe,Seattle\nJane,Smith,Boston\n"

    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("names.csv", io.BytesIO(text_only_csv.encode("utf-8")), "text/csv")},
        headers=auth["headers"],
    )
    dataset_id = upload_res.json()["id"]

    res = client.get(f"/datasets/{dataset_id}/analytics", headers=auth["headers"])
    assert res.status_code == 400
    assert "unsupported dataset" in res.json()["detail"].lower()
