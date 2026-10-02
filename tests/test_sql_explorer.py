import io
from pathlib import Path
import time
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
from app.models.dataset import Dataset
from app.models.saved_query import SavedQuery
from app.models.user import User

# Isolated in-memory SQLite database for tests
sql_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SqlTestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sql_engine)


def override_sql_get_db():
    db = SqlTestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_sql_test(tmp_path, monkeypatch):
    """Setup isolated database and temporary uploads directory for each test."""
    Base.metadata.create_all(bind=sql_engine)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    app.dependency_overrides[get_db] = override_sql_get_db
    yield
    Base.metadata.drop_all(bind=sql_engine)
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


def upload_sample_dataset(auth_headers: dict) -> str:
    """Upload a clean test dataset and return its dataset_id."""
    df = pd.DataFrame({
        "order_id": [101, 102, 103, 104, 105],
        "customer": ["Alice", "Bob", "Charlie", "Alice", "Diana"],
        "category": ["Electronics", "Furniture", "Electronics", "Groceries", "Furniture"],
        "amount": [299.99, 149.50, 89.00, 45.20, 520.00],
        "quantity": [2, 1, 1, 4, 3],
    })
    csv_buf = io.BytesIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    res = client.post(
        "/datasets/upload",
        files={"file": ("sales_records.csv", csv_buf, "text/csv")},
        headers=auth_headers,
    )
    assert res.status_code == 201
    return res.json()["id"]


# =========================================================================
# Authentication and Access Control Tests
# =========================================================================

def test_sql_query_requires_authentication():
    """Verify unauthenticated requests cannot execute SQL queries."""
    fake_id = uuid.uuid4()
    res = client.post(
        f"/datasets/{fake_id}/query",
        json={"query": "SELECT * FROM dataset"},
    )
    assert res.status_code == 401


def test_sql_query_dataset_isolation():
    """Verify User B cannot query User A's dataset."""
    user_a = register_and_login("usera@insightflow.io")
    user_b = register_and_login("userb@insightflow.io")

    dataset_id = upload_sample_dataset(user_a["headers"])

    # User B attempts to query User A's dataset
    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": "SELECT * FROM dataset"},
        headers=user_b["headers"],
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_sql_query_nonexistent_dataset():
    """Verify querying a non-existent dataset returns 404."""
    user = register_and_login()
    fake_id = uuid.uuid4()
    res = client.post(
        f"/datasets/{fake_id}/query",
        json={"query": "SELECT * FROM dataset"},
        headers=user["headers"],
    )
    assert res.status_code == 404


# =========================================================================
# Valid Analytical SELECT Queries
# =========================================================================

def test_sql_query_select_all():
    """Verify basic SELECT * queries return structured rows and columns."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": "SELECT * FROM dataset"},
        headers=user["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == dataset_id
    assert set(data["columns"]) == {"order_id", "customer", "category", "amount", "quantity"}
    assert data["row_count"] == 5
    assert not data["truncated"]
    assert data["execution_time_ms"] >= 0
    assert len(data["rows"]) == 5
    assert data["rows"][0]["customer"] == "Alice"


def test_sql_query_with_aggregations_and_grouping():
    """Verify analytical GROUP BY, SUM, and COUNT queries work as expected."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    query = """
        SELECT
            category,
            COUNT(*) AS total_orders,
            ROUND(SUM(amount), 2) AS total_revenue
        FROM dataset
        GROUP BY category
        ORDER BY total_revenue DESC
    """
    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": query},
        headers=user["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["columns"] == ["category", "total_orders", "total_revenue"]
    assert data["row_count"] == 3
    # Top revenue should be Furniture (149.50 + 520.00 = 669.50)
    assert data["rows"][0]["category"] == "Furniture"
    assert data["rows"][0]["total_orders"] == 2
    assert data["rows"][0]["total_revenue"] == 669.50


def test_sql_query_cte_support():
    """Verify Common Table Expressions (WITH ... SELECT) are supported."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    query = """
        WITH customer_totals AS (
            SELECT customer, SUM(amount) AS spent
            FROM dataset
            GROUP BY customer
        )
        SELECT customer, spent
        FROM customer_totals
        WHERE spent > 100
        ORDER BY spent DESC
    """
    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": query},
        headers=user["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["row_count"] >= 1
    for r in data["rows"]:
        assert r["spent"] > 100


def test_sql_query_data_alias_and_trailing_semicolon():
    """Verify queries against 'data' alias and queries with trailing semicolon succeed."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": "SELECT order_id, amount FROM data WHERE amount > 200;"},
        headers=user["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["row_count"] == 2


def test_sql_query_string_literal_with_keyword():
    """Verify queries containing dangerous keywords INSIDE string literals are allowed."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    # Query with 'DELETE' inside a string literal
    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": "SELECT * FROM dataset WHERE customer = 'DELETE'"},
        headers=user["headers"],
    )
    assert res.status_code == 200
    assert res.json()["row_count"] == 0


# =========================================================================
# Dangerous Mutation and SQL Injection Tests
# =========================================================================

@pytest.mark.parametrize(
    "dangerous_query",
    [
        "DROP TABLE dataset",
        "DROP VIEW data",
        "DELETE FROM dataset WHERE order_id = 101",
        "UPDATE dataset SET amount = 0",
        "INSERT INTO dataset VALUES (999, 'Hacker', 'None', 0, 0)",
        "ALTER TABLE dataset ADD COLUMN backdoor TEXT",
        "TRUNCATE TABLE dataset",
        "CREATE TABLE backdoor (id INT)",
        "CREATE VIEW backdoor AS SELECT * FROM dataset",
        "PRAGMA table_info(dataset)",
        "ATTACH DATABASE ':memory:' AS evil",
        "VACUUM",
        "EXEC sp_help",
        "SELECT * FROM dataset INTO OUTFILE '/tmp/leak.csv'",
        "BEGIN TRANSACTION",
    ],
)
def test_block_dangerous_mutation_queries(dangerous_query):
    """Verify all mutation, schema modification, and administrative queries are blocked."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": dangerous_query},
        headers=user["headers"],
    )
    assert res.status_code == 400
    error_detail = res.json()["detail"].lower()
    assert any(w in error_detail for w in ["only read-only", "disallowed", "strictly blocked", "mutation", "syntax"])


def test_block_stacked_queries_injection():
    """Verify stacked queries attempting to run mutations are rejected."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    stacked_query = "SELECT * FROM dataset; DROP TABLE dataset;"
    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": stacked_query},
        headers=user["headers"],
    )
    assert res.status_code == 400
    assert "multiple" in res.json()["detail"].lower() or "stacked" in res.json()["detail"].lower()


def test_block_comment_hidden_mutation():
    """Verify mutations hidden behind comments or line breaks are caught."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    query = "SELECT * FROM dataset; -- comment \n DROP TABLE dataset;"
    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": query},
        headers=user["headers"],
    )
    assert res.status_code == 400


def test_block_empty_or_whitespace_query():
    """Verify empty queries are rejected."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": "   \n\t   "},
        headers=user["headers"],
    )
    assert res.status_code == 400


# =========================================================================
# Limits, Timeouts, and Safe Error Handling
# =========================================================================

def test_sql_row_limit_enforced():
    """Verify output rows are capped when limit is specified."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    # Request with limit=2 on a 5-row dataset
    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": "SELECT * FROM dataset", "limit": 2},
        headers=user["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["row_count"] == 2
    assert len(data["rows"]) == 2
    assert data["truncated"] is True


def test_sql_query_timeout_enforced():
    """Verify runaway recursive queries hit the timeout limit safely."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    # Infinite recursive CTE requiring full computation in SQLite
    runaway_query = "WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt) SELECT COUNT(*) FROM cnt"
    start = time.monotonic()
    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": runaway_query},
        headers=user["headers"],
    )
    duration = time.monotonic() - start
    assert res.status_code in (400, 408)
    assert "timeout" in res.json()["detail"].lower() or "timed out" in res.json()["detail"].lower()
    # Should terminate within ~6 seconds, never hang indefinitely
    assert duration < 7.0


def test_safe_syntax_error_display():
    """Verify syntax errors return clean error messages without leaking server secrets."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    res = client.post(
        f"/datasets/{dataset_id}/query",
        json={"query": "SELECT nonexistent_col FROM dataset"},
        headers=user["headers"],
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "no such column" in detail.lower()
    # Ensure no file path or credentials leaked
    assert "password" not in detail.lower()
    assert "postgresql://" not in detail.lower()


# =========================================================================
# Saved Queries CRUD Tests
# =========================================================================

def test_saved_queries_crud_lifecycle():
    """Verify complete lifecycle of saved queries: create, list, get, update, delete."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    # 1. Create saved query
    create_res = client.post(
        f"/datasets/{dataset_id}/saved-queries",
        json={
            "name": "High Value Orders",
            "query": "SELECT * FROM dataset WHERE amount > 200 ORDER BY amount DESC",
        },
        headers=user["headers"],
    )
    assert create_res.status_code == 201
    saved_data = create_res.json()
    query_id = saved_data["id"]
    assert saved_data["name"] == "High Value Orders"
    assert "WHERE amount > 200" in saved_data["query"]

    # 2. List saved queries
    list_res = client.get(
        f"/datasets/{dataset_id}/saved-queries",
        headers=user["headers"],
    )
    assert list_res.status_code == 200
    queries = list_res.json()
    assert len(queries) == 1
    assert queries[0]["id"] == query_id

    # 3. Get single saved query
    get_res = client.get(
        f"/datasets/{dataset_id}/saved-queries/{query_id}",
        headers=user["headers"],
    )
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "High Value Orders"

    # 4. Update saved query
    patch_res = client.patch(
        f"/datasets/{dataset_id}/saved-queries/{query_id}",
        json={"name": "Top Value Orders (Renamed)"},
        headers=user["headers"],
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Top Value Orders (Renamed)"

    # 5. Delete saved query
    del_res = client.delete(
        f"/datasets/{dataset_id}/saved-queries/{query_id}",
        headers=user["headers"],
    )
    assert del_res.status_code == 204

    # 6. Verify query no longer exists
    get_after_del = client.get(
        f"/datasets/{dataset_id}/saved-queries/{query_id}",
        headers=user["headers"],
    )
    assert get_after_del.status_code == 404


def test_saved_query_mutation_rejected():
    """Verify attempting to save a dangerous mutation query is rejected."""
    user = register_and_login()
    dataset_id = upload_sample_dataset(user["headers"])

    res = client.post(
        f"/datasets/{dataset_id}/saved-queries",
        json={
            "name": "Malicious Query",
            "query": "DROP TABLE dataset",
        },
        headers=user["headers"],
    )
    assert res.status_code == 400


def test_saved_query_isolation_between_users():
    """Verify User B cannot access or delete User A's saved query."""
    user_a = register_and_login("alice_saved@insightflow.io")
    user_b = register_and_login("bob_saved@insightflow.io")

    dataset_id = upload_sample_dataset(user_a["headers"])

    # User A creates a saved query
    create_res = client.post(
        f"/datasets/{dataset_id}/saved-queries",
        json={"name": "Alice Query", "query": "SELECT * FROM dataset"},
        headers=user_a["headers"],
    )
    query_id = create_res.json()["id"]

    # User B tries to view it
    get_res = client.get(
        f"/datasets/{dataset_id}/saved-queries/{query_id}",
        headers=user_b["headers"],
    )
    assert get_res.status_code == 404

    # User B tries to delete it
    del_res = client.delete(
        f"/datasets/{dataset_id}/saved-queries/{query_id}",
        headers=user_b["headers"],
    )
    assert del_res.status_code == 404
