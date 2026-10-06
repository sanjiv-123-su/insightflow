import io
from pathlib import Path
import uuid
import pandas as pd
import pytest
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

# Isolated in-memory SQLite database for AI Insights tests
ai_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
AiTestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ai_engine)


def override_ai_get_db():
    db = AiTestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_ai_test(tmp_path, monkeypatch):
    """Setup isolated database and temporary uploads directory for each test."""
    Base.metadata.create_all(bind=ai_engine)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    app.dependency_overrides[get_db] = override_ai_get_db
    yield
    Base.metadata.drop_all(bind=ai_engine)
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


def upload_period_business_dataset(auth_headers: dict) -> str:
    """Upload dataset with February and March data where Electronics and West region decline."""
    # February:
    # Electronics: West $5000, East $3000 -> Total $8000
    # Furniture: West $2000, East $2000 -> Total $4000
    # Total Feb = $12000
    #
    # March:
    # Electronics: West $2500, East $3000 -> Total $5500 (Declined $2500, -31.25%)
    # Furniture: West $2000, East $2500 -> Total $4500 (Increased $500)
    # Total March = $10000 (Declined $2000, -16.67%)
    # West Region change: Feb $7000 -> March $4500 (Declined $2500)
    # East Region change: Feb $5000 -> March $5500 (Increased $500)
    records = [
        # Feb
        {"date": "2024-02-05", "revenue": 5000.0, "category": "Electronics", "region": "West", "order_id": "O1"},
        {"date": "2024-02-12", "revenue": 3000.0, "category": "Electronics", "region": "East", "order_id": "O2"},
        {"date": "2024-02-18", "revenue": 2000.0, "category": "Furniture", "region": "West", "order_id": "O3"},
        {"date": "2024-02-25", "revenue": 2000.0, "category": "Furniture", "region": "East", "order_id": "O4"},
        # March
        {"date": "2024-03-05", "revenue": 2500.0, "category": "Electronics", "region": "West", "order_id": "O5"},
        {"date": "2024-03-12", "revenue": 3000.0, "category": "Electronics", "region": "East", "order_id": "O6"},
        {"date": "2024-03-18", "revenue": 2000.0, "category": "Furniture", "region": "West", "order_id": "O7"},
        {"date": "2024-03-25", "revenue": 2500.0, "category": "Furniture", "region": "East", "order_id": "O8"},
    ]
    df = pd.DataFrame(records)
    csv_buf = io.BytesIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    res = client.post(
        "/datasets/upload",
        files={"file": ("monthly_sales.csv", csv_buf, "text/csv")},
        headers=auth_headers,
    )
    assert res.status_code == 201
    return res.json()["id"]


# =========================================================================
# Authentication & Isolation Tests
# =========================================================================

def test_ai_insights_requires_authentication():
    """Verify unauthenticated requests cannot access AI insights."""
    fake_id = uuid.uuid4()
    res = client.get(f"/datasets/{fake_id}/ai-insights")
    assert res.status_code == 401


def test_ai_insights_dataset_isolation():
    """Verify User B cannot view User A's AI insights."""
    user_a = register_and_login("alice_ai@insightflow.io")
    user_b = register_and_login("bob_ai@insightflow.io")

    dataset_id = upload_period_business_dataset(user_a["headers"])

    # User B requests User A's insights
    res = client.get(
        f"/datasets/{dataset_id}/ai-insights",
        headers=user_b["headers"],
    )
    assert res.status_code == 404


# =========================================================================
# Dependency on Normal Analytics ("Only after normal analytics works")
# =========================================================================

def test_ai_insights_fails_if_normal_analytics_cannot_run():
    """Verify AI insights cannot run on datasets lacking numeric revenue columns."""
    user = register_and_login()
    # Upload text-only dataset with no numbers
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "city": ["New York", "Chicago", "Boston"],
    })
    csv_buf = io.BytesIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("text_only.csv", csv_buf, "text/csv")},
        headers=user["headers"],
    )
    dataset_id = upload_res.json()["id"]

    # AI insights request should fail with 400 because normal analytics cannot run
    res = client.get(
        f"/datasets/{dataset_id}/ai-insights",
        headers=user["headers"],
    )
    assert res.status_code == 400
    assert "analytics" in res.json()["detail"].lower() or "numeric" in res.json()["detail"].lower()


# =========================================================================
# Grounded Explanation of Analytical Results
# =========================================================================

def test_ai_insights_explains_verified_results_accurately():
    """Verify AI explains the verified metrics: headline, category contribution, and regional portion."""
    user = register_and_login()
    dataset_id = upload_period_business_dataset(user["headers"])

    res = client.get(
        f"/datasets/{dataset_id}/ai-insights",
        headers=user["headers"],
    )
    assert res.status_code == 200
    data = res.json()

    assert data["dataset_id"] == dataset_id
    assert "headline" in data
    assert "summary" in data
    assert "category_insight" in data
    assert "regional_insight" in data
    assert len(data["key_drivers"]) >= 2
    assert len(data["recommendations"]) >= 1

    # 1. Headline should reflect the revenue decrease in March
    # March decreased -16.7% vs Feb ($10000 vs $12000)
    headline_lower = data["headline"].lower()
    assert "decreased" in headline_lower or "declined" in headline_lower or "revenue" in headline_lower
    assert "2024-03" in data["headline"] or "march" in headline_lower

    # 2. Category insight should identify Electronics as the largest contributor to the decline
    cat_insight = data["category_insight"]
    assert cat_insight is not None
    assert "electronics" in cat_insight.lower()
    assert "largest contribution" in cat_insight.lower()
    assert "declined" in cat_insight.lower()

    # 3. Regional insight should identify West as accounting for largest portion of decline
    reg_insight = data["regional_insight"]
    assert reg_insight is not None
    assert "west" in reg_insight.lower()
    assert "largest portion" in reg_insight.lower()

    # 4. Verified facts must be attached and match calculation
    facts = data["verified_facts"]
    assert facts["total_revenue"] == 22000.0  # 12000 + 10000
    assert facts["total_orders"] == 8
    assert facts["period_trend"]["growth_percentage"] == -16.67
    assert facts["category_driver"]["name"] == "Electronics"
    assert facts["region_driver"]["name"] == "West"


def test_ai_insights_caching_and_regeneration():
    """Verify AI insights are cached and can be explicitly regenerated."""
    user = register_and_login()
    dataset_id = upload_period_business_dataset(user["headers"])

    # First fetch generates and caches
    res1 = client.get(
        f"/datasets/{dataset_id}/ai-insights",
        headers=user["headers"],
    )
    assert res1.status_code == 200
    time1 = res1.json()["created_at"]

    # Second fetch returns cached version
    res2 = client.get(
        f"/datasets/{dataset_id}/ai-insights",
        headers=user["headers"],
    )
    assert res2.status_code == 200
    assert res2.json()["headline"] == res1.json()["headline"]

    # Explicit regeneration forces fresh computation
    res_regen = client.post(
        f"/datasets/{dataset_id}/ai-insights/regenerate",
        headers=user["headers"],
    )
    assert res_regen.status_code == 200
    assert res_regen.json()["headline"] == res1.json()["headline"]
