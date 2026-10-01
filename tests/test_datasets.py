import io
from pathlib import Path
import uuid
import openpyxl
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
from app.models.user import User

# Isolated in-memory SQLite database for datasets tests
dataset_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
DatasetTestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=dataset_engine)


def override_dataset_get_db():
    db = DatasetTestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_dataset_test(tmp_path, monkeypatch):
    """Setup isolated database and temporary uploads directory for each test."""
    Base.metadata.create_all(bind=dataset_engine)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    app.dependency_overrides[get_db] = override_dataset_get_db
    yield
    Base.metadata.drop_all(bind=dataset_engine)
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


def create_sample_csv(rows: int = 5) -> io.BytesIO:
    """Generate in-memory CSV file bytes."""
    lines = ["id,feature_a,feature_b,target"]
    for i in range(1, rows + 1):
        lines.append(f"{i},value_a_{i},{i * 10.5},{i % 2}")
    content = "\n".join(lines).encode("utf-8")
    return io.BytesIO(content)


def create_sample_xlsx(rows: int = 5) -> io.BytesIO:
    """Generate in-memory XLSX file bytes."""
    buf = io.BytesIO()
    df = pd.DataFrame({
        "customer_id": [f"C{i:03d}" for i in range(1, rows + 1)],
        "revenue": [i * 150.25 for i in range(1, rows + 1)],
        "region": ["North" if i % 2 == 0 else "South" for i in range(1, rows + 1)],
    })
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buf.seek(0)
    return buf


# =========================================================================
# Upload Authentication Tests
# =========================================================================

def test_upload_requires_authentication():
    """Verify unauthenticated requests cannot upload datasets."""
    csv_file = create_sample_csv()
    files = {"file": ("test.csv", csv_file, "text/csv")}
    response = client.post("/datasets/upload", files=files)
    assert response.status_code == 401


def test_upload_invalid_token_rejected():
    """Verify invalid JWT tokens are rejected on upload."""
    csv_file = create_sample_csv()
    files = {"file": ("test.csv", csv_file, "text/csv")}
    response = client.post(
        "/datasets/upload",
        files=files,
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401


# =========================================================================
# CSV Upload Tests
# =========================================================================

def test_upload_valid_csv_success():
    """Verify successful CSV upload, metadata persistence, and file storage."""
    auth = register_and_login("csv_user@insightflow.io")
    csv_file = create_sample_csv(rows=10)

    files = {"file": ("sales_q3.csv", csv_file, "text/csv")}
    response = client.post("/datasets/upload", files=files, headers=auth["headers"])

    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    dataset_id = data["id"]
    assert data["name"] == "Sales Q3"
    assert data["original_filename"] == "sales_q3.csv"
    assert data["file_type"] == "csv"
    assert data["file_size"] > 0
    assert data["status"] in ("completed", "pending")
    assert data["column_count"] == 4
    assert data["row_count"] == 10
    assert "created_at" in data

    # Verify database record
    with DatasetTestingSessionLocal() as db:
        record = db.query(Dataset).filter(Dataset.id == uuid.UUID(dataset_id)).first()
        assert record is not None
        assert record.original_filename == "sales_q3.csv"
        assert record.file_type == "csv"
        assert record.status in ("completed", "pending")

    # Verify file stored on disk
    upload_dir = settings.upload_path
    stored_files = list(upload_dir.glob(f"{dataset_id}_*"))
    assert len(stored_files) == 1
    assert stored_files[0].exists()
    assert stored_files[0].stat().st_size == data["file_size"]


# =========================================================================
# XLSX Upload Tests
# =========================================================================

def test_upload_valid_xlsx_success():
    """Verify successful XLSX upload and basic Excel parsing."""
    auth = register_and_login("xlsx_user@insightflow.io")
    xlsx_file = create_sample_xlsx(rows=8)

    files = {
        "file": (
            "metrics.xlsx",
            xlsx_file,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    response = client.post("/datasets/upload", files=files, headers=auth["headers"])

    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    dataset_id = data["id"]
    assert data["original_filename"] == "metrics.xlsx"
    assert data["file_type"] == "xlsx"
    assert data["column_count"] == 3
    assert data["row_count"] == 8
    assert data["status"] in ("completed", "pending")

    upload_dir = settings.upload_path
    stored_files = list(upload_dir.glob(f"{dataset_id}_*"))
    assert len(stored_files) == 1
    assert stored_files[0].exists()


# =========================================================================
# Validation and Error Handling Tests
# =========================================================================

def test_upload_unsupported_extension_rejected():
    """Verify files with unsupported extensions are rejected."""
    auth = register_and_login("ext_user@insightflow.io")

    # .txt
    res_txt = client.post(
        "/datasets/upload",
        files={"file": ("data.txt", io.BytesIO(b"some,data\n1,2"), "text/plain")},
        headers=auth["headers"],
    )
    assert res_txt.status_code == 400
    assert "unsupported file extension" in res_txt.json()["detail"].lower()

    # .exe
    res_exe = client.post(
        "/datasets/upload",
        files={"file": ("payload.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
        headers=auth["headers"],
    )
    assert res_exe.status_code == 400
    assert "unsupported file extension" in res_exe.json()["detail"].lower()


def test_upload_invalid_mime_type_rejected():
    """Verify files with conflicting/dangerous MIME types are rejected."""
    auth = register_and_login("mime_user@insightflow.io")
    csv_file = create_sample_csv()

    # CSV with image/png MIME type
    response = client.post(
        "/datasets/upload",
        files={"file": ("data.csv", csv_file, "image/png")},
        headers=auth["headers"],
    )
    assert response.status_code == 400
    assert "invalid mime type" in response.json()["detail"].lower()


def test_upload_empty_file_rejected():
    """Verify empty 0-byte files are rejected."""
    auth = register_and_login("empty_user@insightflow.io")

    response = client.post(
        "/datasets/upload",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        headers=auth["headers"],
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_exceeds_max_file_size_rejected(monkeypatch):
    """Verify files exceeding configured MAX_UPLOAD_SIZE_BYTES are rejected with 413."""
    auth = register_and_login("size_user@insightflow.io")
    # Set limit to 100 bytes for test
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 100)

    oversized_content = b"col1,col2,col3\n" + (b"1,2,3\n" * 50)  # > 300 bytes
    response = client.post(
        "/datasets/upload",
        files={"file": ("oversized.csv", io.BytesIO(oversized_content), "text/csv")},
        headers=auth["headers"],
    )
    assert response.status_code == 413
    assert "exceeds maximum allowed limit" in response.json()["detail"].lower()

    # Verify no orphan file was left on disk
    upload_dir = settings.upload_path
    assert len(list(upload_dir.glob("*oversized*"))) == 0


def test_upload_corrupt_xlsx_rejected():
    """Verify non-Excel content masquerading as .xlsx is rejected."""
    auth = register_and_login("corrupt_user@insightflow.io")

    # Plain text with .xlsx extension (missing ZIP magic bytes)
    response = client.post(
        "/datasets/upload",
        files={
            "file": (
                "fake.xlsx",
                io.BytesIO(b"This is just plain text masquerading as xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=auth["headers"],
    )
    assert response.status_code == 400
    assert "xlsx" in response.json()["detail"].lower() or "header" in response.json()["detail"].lower()


def test_upload_csv_with_binary_null_bytes_rejected():
    """Verify CSV with embedded binary null bytes is rejected."""
    auth = register_and_login("nullbyte_user@insightflow.io")
    corrupt_content = b"col1,col2\nval1,val\x002\n"

    response = client.post(
        "/datasets/upload",
        files={"file": ("corrupt.csv", io.BytesIO(corrupt_content), "text/csv")},
        headers=auth["headers"],
    )
    assert response.status_code == 400
    assert "binary data or null bytes" in response.json()["detail"].lower()


# =========================================================================
# Dataset Listing and User Isolation Tests
# =========================================================================

def test_list_datasets_isolated_per_user():
    """Verify users can only see datasets they own."""
    user1 = register_and_login("user1@insightflow.io")
    user2 = register_and_login("user2@insightflow.io")

    # User 1 uploads 2 datasets
    client.post(
        "/datasets/upload",
        files={"file": ("u1_dataset1.csv", create_sample_csv(rows=3), "text/csv")},
        headers=user1["headers"],
    )
    client.post(
        "/datasets/upload",
        files={"file": ("u1_dataset2.csv", create_sample_csv(rows=4), "text/csv")},
        headers=user1["headers"],
    )

    # User 2 uploads 1 dataset
    client.post(
        "/datasets/upload",
        files={"file": ("u2_dataset1.csv", create_sample_csv(rows=5), "text/csv")},
        headers=user2["headers"],
    )

    # User 1 lists datasets
    res1 = client.get("/datasets", headers=user1["headers"])
    assert res1.status_code == 200
    datasets1 = res1.json()
    assert len(datasets1) == 2
    filenames1 = {d["original_filename"] for d in datasets1}
    assert filenames1 == {"u1_dataset1.csv", "u1_dataset2.csv"}

    # User 2 lists datasets
    res2 = client.get("/datasets", headers=user2["headers"])
    assert res2.status_code == 200
    datasets2 = res2.json()
    assert len(datasets2) == 1
    assert datasets2[0]["original_filename"] == "u2_dataset1.csv"


# =========================================================================
# Single Dataset Retrieval Tests
# =========================================================================

def test_get_dataset_by_id_success():
    """Verify owner can retrieve specific dataset details."""
    auth = register_and_login("owner@insightflow.io")
    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("analysis.csv", create_sample_csv(rows=7), "text/csv")},
        headers=auth["headers"],
    )
    dataset_id = upload_res.json()["id"]

    get_res = client.get(f"/datasets/{dataset_id}", headers=auth["headers"])
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == dataset_id
    assert data["original_filename"] == "analysis.csv"
    assert data["file_type"] == "csv"
    assert data["column_count"] == 4
    assert data["row_count"] == 7


def test_get_dataset_other_user_denied():
    """Verify a user cannot retrieve another user's dataset (returns 404)."""
    user_a = register_and_login("alice@insightflow.io")
    user_b = register_and_login("bob@insightflow.io")

    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("alice_secret.csv", create_sample_csv(), "text/csv")},
        headers=user_a["headers"],
    )
    dataset_id = upload_res.json()["id"]

    # Bob tries to access Alice's dataset
    bob_res = client.get(f"/datasets/{dataset_id}", headers=user_b["headers"])
    assert bob_res.status_code == 404
    assert "not found" in bob_res.json()["detail"].lower()


def test_get_dataset_not_found():
    """Verify non-existent dataset UUID returns 404."""
    auth = register_and_login("seeker@insightflow.io")
    random_id = str(uuid.uuid4())
    res = client.get(f"/datasets/{random_id}", headers=auth["headers"])
    assert res.status_code == 404


# =========================================================================
# Profiling Endpoint Tests
# =========================================================================

def test_get_dataset_profile_success():
    """Verify GET /datasets/{id}/profile returns comprehensive column & dataset stats."""
    auth = register_and_login("profile_user@insightflow.io")
    csv_file = create_sample_csv(rows=10)

    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("profile_data.csv", csv_file, "text/csv")},
        headers=auth["headers"],
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["id"]

    profile_res = client.get(f"/datasets/{dataset_id}/profile", headers=auth["headers"])
    assert profile_res.status_code == 200
    data = profile_res.json()

    assert data["dataset_id"] == dataset_id
    assert "summary" in data
    summary = data["summary"]
    assert summary["row_count"] == 10
    assert summary["column_count"] == 4
    assert summary["duplicate_rows"] == 0
    assert summary["total_missing_values"] == 0
    assert 0.0 <= summary["overall_data_quality_score"] <= 100.0

    assert "columns" in data
    assert len(data["columns"]) == 4
    col_names = {c["column_name"] for c in data["columns"]}
    assert col_names == {"id", "feature_a", "feature_b", "target"}

    # Check a numeric column profile
    feature_b_col = next(c for c in data["columns"] if c["column_name"] == "feature_b")
    assert feature_b_col["detected_data_type"] in ("float", "numeric")
    assert feature_b_col["null_count"] == 0
    assert feature_b_col["null_percentage"] == 0.0
    assert feature_b_col["unique_count"] == 10
    assert feature_b_col["minimum"] is not None
    assert feature_b_col["maximum"] is not None
    assert feature_b_col["mean"] is not None
    assert feature_b_col["median"] is not None
    assert len(feature_b_col["sample_values"]) > 0

    assert "warnings" in data
    assert "completely_empty_columns" in data["warnings"]
    assert "high_null_columns" in data["warnings"]


def test_get_dataset_profile_auth_and_isolation():
    """Verify profile access requires authentication and respects user isolation."""
    user_a = register_and_login("alice_p@insightflow.io")
    user_b = register_and_login("bob_p@insightflow.io")

    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("secret.csv", create_sample_csv(rows=5), "text/csv")},
        headers=user_a["headers"],
    )
    dataset_id = upload_res.json()["id"]

    # 1. Unauthenticated -> 401
    res_unauth = client.get(f"/datasets/{dataset_id}/profile")
    assert res_unauth.status_code == 401

    # 2. Other user -> 404
    res_forbidden = client.get(f"/datasets/{dataset_id}/profile", headers=user_b["headers"])
    assert res_forbidden.status_code == 404

    # 3. Nonexistent -> 404
    res_not_found = client.get(f"/datasets/{uuid.uuid4()}/profile", headers=user_a["headers"])
    assert res_not_found.status_code == 404


# =========================================================================
# Quality Report Endpoint Tests
# =========================================================================

def test_get_dataset_quality_success():
    """Verify GET /datasets/{id}/quality returns score and metric breakdown."""
    auth = register_and_login("quality_user@insightflow.io")
    csv_file = create_sample_csv(rows=12)

    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("quality_data.csv", csv_file, "text/csv")},
        headers=auth["headers"],
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["id"]

    quality_res = client.get(f"/datasets/{dataset_id}/quality", headers=auth["headers"])
    assert quality_res.status_code == 200
    data = quality_res.json()

    assert data["dataset_id"] == dataset_id
    assert 0.0 <= data["quality_score"] <= 100.0
    assert data["missing_values"] == 0
    assert data["duplicate_rows"] == 0
    assert data["invalid_values"] == 0
    assert "metrics" in data
    assert data["metrics"]["completeness_score"] == 100.0
    assert data["metrics"]["uniqueness_score"] == 100.0


def test_get_dataset_quality_auth_and_isolation():
    """Verify quality report requires authentication and isolates users."""
    user_a = register_and_login("alice_q@insightflow.io")
    user_b = register_and_login("bob_q@insightflow.io")

    upload_res = client.post(
        "/datasets/upload",
        files={"file": ("isolated.csv", create_sample_csv(), "text/csv")},
        headers=user_a["headers"],
    )
    dataset_id = upload_res.json()["id"]

    # 1. Unauthenticated -> 401
    res_unauth = client.get(f"/datasets/{dataset_id}/quality")
    assert res_unauth.status_code == 401

    # 2. Other user -> 404
    res_other = client.get(f"/datasets/{dataset_id}/quality", headers=user_b["headers"])
    assert res_other.status_code == 404
