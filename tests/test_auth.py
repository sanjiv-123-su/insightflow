import uuid
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import User

# Configure an isolated in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


client = TestClient(app)


def test_register_user_success():
    """Test successful user registration returns 201 and public profile."""
    payload = {
        "email": "analyst@insightflow.io",
        "password": "StrongPassword123!",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "analyst@insightflow.io"
    assert "id" in data
    assert "created_at" in data
    # Ensure password and hash are NEVER exposed
    assert "password" not in data
    assert "password_hash" not in data

    # Verify password was hashed in the database
    with TestingSessionLocal() as db:
        user = db.query(User).filter(User.email == "analyst@insightflow.io").first()
        assert user is not None
        assert user.password_hash != "StrongPassword123!"
        assert user.password_hash.startswith("$2b$")


def test_register_duplicate_email_conflict():
    """Test registering an existing email returns 409 Conflict."""
    payload = {
        "email": "duplicate@insightflow.io",
        "password": "StrongPassword123!",
    }
    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with case-insensitive variation
    payload_variant = {
        "email": "DUPLICATE@insightflow.io",
        "password": "DifferentPassword456!",
    }
    res2 = client.post("/auth/register", json=payload_variant)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


def test_register_validation_failures():
    """Test registration validation errors for short passwords and malformed emails."""
    # Password too short (< 8 chars)
    res_short = client.post(
        "/auth/register",
        json={"email": "valid@example.com", "password": "short"},
    )
    assert res_short.status_code == 422

    # Malformed email
    res_bad_email = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "ValidPassword123!"},
    )
    assert res_bad_email.status_code == 422


def test_login_success_json():
    """Test login via JSON payload returns 200 and valid JWT token."""
    client.post(
        "/auth/register",
        json={"email": "jsonuser@insightflow.io", "password": "UserPass123!"},
    )

    response = client.post(
        "/auth/login",
        json={"email": "jsonuser@insightflow.io", "password": "UserPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_success_oauth2_form():
    """Test login via standard OAuth2 Password form data (username=email)."""
    client.post(
        "/auth/register",
        json={"email": "formuser@insightflow.io", "password": "FormPass123!"},
    )

    response = client.post(
        "/auth/login",
        data={"username": "formuser@insightflow.io", "password": "FormPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials():
    """Test login fails with 401 for incorrect password and non-existent user."""
    client.post(
        "/auth/register",
        json={"email": "realuser@insightflow.io", "password": "CorrectPassword123!"},
    )

    # Wrong password
    res_wrong_pw = client.post(
        "/auth/login",
        json={"email": "realuser@insightflow.io", "password": "WrongPassword123!"},
    )
    assert res_wrong_pw.status_code == 401

    # Non-existent user
    res_no_user = client.post(
        "/auth/login",
        json={"email": "nobody@insightflow.io", "password": "Password123!"},
    )
    assert res_no_user.status_code == 401


def test_get_current_user_me_protected():
    """Test protected /auth/me endpoint."""
    reg_res = client.post(
        "/auth/register",
        json={"email": "me@insightflow.io", "password": "MySecretPass123!"},
    )
    user_id = reg_res.json()["id"]

    login_res = client.post(
        "/auth/login",
        json={"email": "me@insightflow.io", "password": "MySecretPass123!"},
    )
    token = login_res.json()["access_token"]

    # Valid token
    me_res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == user_id
    assert me_data["email"] == "me@insightflow.io"

    # Missing token -> 401
    res_no_token = client.get("/auth/me")
    assert res_no_token.status_code == 401

    # Invalid / garbage token -> 401
    res_bad_token = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.garbage.token"},
    )
    assert res_bad_token.status_code == 401


def test_get_me_expired_token():
    """Test accessing /auth/me with an expired JWT token returns 401."""
    # Create an expired token
    expired_token = create_access_token(
        subject=str(uuid.uuid4()),
        expires_delta=timedelta(seconds=-10),
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()
