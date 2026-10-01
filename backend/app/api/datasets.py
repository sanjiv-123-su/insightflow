import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    ColumnMappingInput,
    DatasetAnalyticsResponse,
    DetectedColumnMapping,
)
from app.schemas.dataset import DatasetResponse, DatasetUploadResponse
from app.schemas.profiling import DataQualityResponse, DatasetProfileResponse
from app.services.analytics import AnalyticsService
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
        201: {"description": "Dataset uploaded, profiled, and registered successfully"},
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
    """Upload, validate, and automatically profile a new dataset file.

    - Supported file formats: `.csv`, `.xlsx`
    - Maximum file size: Configured via `MAX_UPLOAD_SIZE_BYTES`
    - Only authenticated users can upload datasets.
    - Files are stored safely outside source code.
    - Dataset and profiling records are persisted in Neon PostgreSQL.
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


@router.get(
    "/{dataset_id}/profile",
    response_model=DatasetProfileResponse,
    summary="Get complete automated profile for a dataset",
    responses={
        200: {"description": "Dataset profile including column-level statistics and warnings"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
    },
)
def get_dataset_profile(
    dataset_id: uuid.UUID,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve complete automated profiling results for a dataset.

    Calculates and returns:
    - Dataset-level summary (row count, column count, duplicate rows, missing values, quality score)
    - Column-level metrics (detected type, null count/percentage, unique count, min, max, mean, median, sample values)
    - Warning detections (completely empty columns, high-null columns, duplicate rows)
    """
    return DatasetService.get_dataset_profile(db=db, user=current_user, dataset_id=dataset_id)


@router.get(
    "/{dataset_id}/quality",
    response_model=DataQualityResponse,
    summary="Get data quality report for a dataset",
    responses={
        200: {"description": "Data quality score and breakdown metrics"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
    },
)
def get_dataset_quality(
    dataset_id: uuid.UUID,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the data quality report and metrics breakdown for a dataset.

    Returns:
    - Overall data quality score (0.0 to 100.0)
    - Total missing values
    - Duplicate rows count
    - Invalid values count
    - Detailed quality metric scores (completeness, uniqueness, validity)
    """
    return DatasetService.get_dataset_quality(db=db, user=current_user, dataset_id=dataset_id)


@router.get(
    "/{dataset_id}/analytics",
    response_model=DatasetAnalyticsResponse,
    summary="Get business analytics and metrics for React charts",
    responses={
        200: {"description": "Structured business analytics for dashboard charts and KPIs"},
        400: {"description": "Unsupported dataset or missing required numeric column"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
    },
)
def get_dataset_analytics(
    dataset_id: uuid.UUID,
    use_cache: bool = Query(True, description="Whether to return cached analysis if available"),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Calculate or retrieve business analytics for an uploaded dataset.

    Calculates:
    - Total Revenue, Total Orders, Unique Customers, Average Order Value
    - Revenue by Month (with Month-over-Month growth rates)
    - Revenue by Category & Revenue by Region
    - Top Products & Top Customers
    - Growth trends and summary
    """
    return AnalyticsService.get_or_compute_analytics(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
        mapping_override=None,
        use_cache=use_cache,
    )


@router.post(
    "/{dataset_id}/analytics",
    response_model=DatasetAnalyticsResponse,
    summary="Calculate business analytics with custom column mapping",
    responses={
        200: {"description": "Recalculated analytics based on custom column mapping"},
        400: {"description": "Invalid column mapping or unsupported columns"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
    },
)
def calculate_dataset_analytics_with_mapping(
    dataset_id: uuid.UUID,
    mapping_override: Optional[ColumnMappingInput] = Body(None, description="Custom column mapping overrides"),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Recompute business analytics for a dataset with user-configured column mapping overrides."""
    return AnalyticsService.get_or_compute_analytics(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
        mapping_override=mapping_override,
        use_cache=False,
    )


@router.get(
    "/{dataset_id}/analytics/mapping",
    response_model=DetectedColumnMapping,
    summary="Inspect and detect candidate columns for analytics",
    responses={
        200: {"description": "Detected column roles and available candidates"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
    },
)
def get_analytics_column_mapping(
    dataset_id: uuid.UUID,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Inspect dataset and detect candidate columns for revenue, date, customer, product, category, etc."""
    return AnalyticsService.get_detected_mapping(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
    )
