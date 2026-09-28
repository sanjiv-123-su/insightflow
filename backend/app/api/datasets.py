import logging
from typing import List
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.dataset import DatasetResponse, DatasetUploadResponse
from app.services.auth import AuthService
from app.services.dataset import DatasetService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new dataset (CSV or XLSX)",
    responses={
        201: {"description": "Dataset uploaded and registered successfully"},
        400: {"description": "Invalid file format, empty file, or validation failure"},
        401: {"description": "Authentication required"},
        413: {"description": "File size exceeds maximum allowed threshold"},
        500: {"description": "Internal database or server error"},
    },
)
async def upload_dataset(
    file: UploadFile = File(..., description="Dataset file (CSV or XLSX)"),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Upload and validate a new dataset file.

    - Supported file formats: `.csv`, `.xlsx`
    - Maximum file size: Configured via `MAX_UPLOAD_SIZE_BYTES`
    - Only authenticated users can upload datasets.
    - Files are stored safely outside source code.
    - Dataset record is persisted in Neon PostgreSQL.
    """
    dataset = await DatasetService.upload_dataset(db=db, user=current_user, file=file)
    return dataset


@router.get(
    "",
    response_model=List[DatasetResponse],
    summary="List all datasets for current user",
    responses={
        200: {"description": "List of user-owned datasets"},
        401: {"description": "Authentication required"},
    },
)
def list_datasets(
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all datasets belonging to the authenticated user.

    Users cannot see datasets uploaded by other users.
    """
    return DatasetService.list_datasets(db=db, user=current_user)


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Get details of a specific dataset",
    responses={
        200: {"description": "Dataset metadata"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
    },
)
def get_dataset(
    dataset_id: uuid.UUID,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details for a single dataset by ID.

    Users can only access their own datasets. Non-existent datasets or datasets owned
    by other users return 404 Not Found.
    """
    return DatasetService.get_dataset(db=db, user=current_user, dataset_id=dataset_id)
