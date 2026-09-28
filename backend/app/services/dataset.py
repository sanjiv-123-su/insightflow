from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.analytics_result import AnalyticsResult
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.quality_report import DataQualityReport
from app.models.user import User
from app.schemas.profiling import (
    ColumnProfile,
    DataQualityBreakdown,
    DataQualityResponse,
    DatasetProfileResponse,
    DatasetProfileSummary,
    ProfileWarnings,
)
from app.services.file_storage import FileStorageService
from app.services.profiler import DataProfilerService, ProfileResult

logger = logging.getLogger(__name__)


class DatasetService:
    """Service handling dataset uploads, validation, profiling, and user-scoped queries."""

    @classmethod
    async def upload_dataset(
        cls,
        db: Session,
        user: User,
        file: UploadFile,
    ) -> Dataset:
        """Process, validate, store an uploaded dataset, run automated profiling, and persist in Neon.

        Raises:
            HTTPException(400): If file metadata or contents fail validation.
            HTTPException(413): If file size exceeds maximum configured threshold.
            HTTPException(500): If database persistence fails.
        """
        # 1. Validate file extension and MIME type where practical
        file_type = FileStorageService.validate_file_metadata(file.filename, file.content_type)

        dataset_id = uuid.uuid4()
        original_name = file.filename or f"dataset_{dataset_id.hex[:8]}.{file_type}"
        display_name = Path(original_name).stem.replace("_", " ").title() or original_name

        # 2. Stream and store file safely outside source code
        file_path, file_size, safe_filename = await FileStorageService.save_upload_file(file, dataset_id)

        # 3. Basic file integrity validation (magic bytes, binary null-byte check)
        FileStorageService.validate_file_content(file_path, file_type)

        # 4. Run automated profiling engine using Pandas
        try:
            profile_result = DataProfilerService.profile_file(file_path, file_type)
        except Exception:
            FileStorageService.delete_file(file_path)
            raise

        # 4. Create Dataset entity
        dataset = Dataset(
            id=dataset_id,
            user_id=user.id,
            name=display_name,
            original_filename=original_name,
            file_type=file_type,
            file_size=file_size,
            row_count=profile_result.row_count,
            column_count=profile_result.column_count,
            status="completed",
        )

        try:
            db.add(dataset)

            # 5. Persist column-level records in Neon
            for col in profile_result.columns:
                db_col = DatasetColumn(
                    id=uuid.uuid4(),
                    dataset_id=dataset_id,
                    column_name=col.column_name,
                    data_type=col.detected_data_type,
                    nullable=col.null_count > 0,
                    null_count=col.null_count,
                    unique_count=col.unique_count,
                )
                db.add(db_col)

            # 6. Persist DataQualityReport in Neon
            quality_report = DataQualityReport(
                id=uuid.uuid4(),
                dataset_id=dataset_id,
                missing_values=profile_result.total_missing_values,
                duplicate_rows=profile_result.duplicate_rows,
                invalid_values=profile_result.invalid_values_count,
                quality_score=profile_result.overall_data_quality_score,
            )
            db.add(quality_report)

            # 7. Persist comprehensive profiling JSON in AnalyticsResult
            profile_analytics = AnalyticsResult(
                id=uuid.uuid4(),
                dataset_id=dataset_id,
                analysis_type="profile",
                result=profile_result.to_dict(),
            )
            db.add(profile_analytics)

            db.commit()
            db.refresh(dataset)
            logger.info(
                "Dataset %s successfully profiled and created for user %s (rows: %d, cols: %d)",
                dataset.id,
                user.id,
                profile_result.row_count,
                profile_result.column_count,
            )
            return dataset

        except SQLAlchemyError as exc:
            db.rollback()
            FileStorageService.delete_file(file_path)
            logger.error("Failed to commit dataset record %s to database: %s", dataset_id, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while recording dataset profiling results.",
            )

    @classmethod
    def list_datasets(
        cls,
        db: Session,
        user: User,
    ) -> List[Dataset]:
        """Retrieve all datasets belonging exclusively to the authenticated user."""
        return (
            db.query(Dataset)
            .filter(Dataset.user_id == user.id)
            .order_by(Dataset.created_at.desc())
            .all()
        )

    @classmethod
    def get_dataset(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
    ) -> Dataset:
        """Retrieve a specific dataset by ID, ensuring user ownership.

        Raises:
            HTTPException(404): If dataset does not exist or does not belong to the user.
        """
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

        return dataset

    @classmethod
    def _ensure_dataset_profiled(cls, db: Session, dataset: Dataset) -> Tuple[Dict[str, Any], DataQualityReport]:
        """Check if profiling results exist; if not, generate them on-demand and persist."""
        analytics = (
            db.query(AnalyticsResult)
            .filter(
                AnalyticsResult.dataset_id == dataset.id,
                AnalyticsResult.analysis_type == "profile",
            )
            .first()
        )

        quality_report = (
            db.query(DataQualityReport)
            .filter(DataQualityReport.dataset_id == dataset.id)
            .order_by(DataQualityReport.created_at.desc())
            .first()
        )

        if analytics and quality_report:
            return analytics.result, quality_report

        # Run profiling if not yet performed
        file_path = FileStorageService.get_stored_file_path(dataset.id)
        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset source file is not available for profiling.",
            )

        profile_result = DataProfilerService.profile_file(file_path, dataset.file_type)

        # Update dataset row & column count
        dataset.row_count = profile_result.row_count
        dataset.column_count = profile_result.column_count
        dataset.status = "completed"

        # Remove any existing columns to prevent duplicate key errors
        db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset.id).delete()
        for col in profile_result.columns:
            db_col = DatasetColumn(
                id=uuid.uuid4(),
                dataset_id=dataset.id,
                column_name=col.column_name,
                data_type=col.detected_data_type,
                nullable=col.null_count > 0,
                null_count=col.null_count,
                unique_count=col.unique_count,
            )
            db.add(db_col)

        if not quality_report:
            quality_report = DataQualityReport(
                id=uuid.uuid4(),
                dataset_id=dataset.id,
                missing_values=profile_result.total_missing_values,
                duplicate_rows=profile_result.duplicate_rows,
                invalid_values=profile_result.invalid_values_count,
                quality_score=profile_result.overall_data_quality_score,
            )
            db.add(quality_report)

        if not analytics:
            analytics = AnalyticsResult(
                id=uuid.uuid4(),
                dataset_id=dataset.id,
                analysis_type="profile",
                result=profile_result.to_dict(),
            )
            db.add(analytics)

        try:
            db.commit()
            db.refresh(analytics)
            db.refresh(quality_report)
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error("Failed to persist on-demand profiling: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save profiling results.",
            )

        return analytics.result, quality_report

    @classmethod
    def get_dataset_profile(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
    ) -> DatasetProfileResponse:
        """Retrieve full profiling results for a dataset owned by the user.

        Raises:
            HTTPException(404): If dataset does not exist or user lacks permission.
        """
        dataset = cls.get_dataset(db, user, dataset_id)
        profile_data, _ = cls._ensure_dataset_profiled(db, dataset)

        summary_data = profile_data.get("summary", {})
        warnings_data = profile_data.get("warnings", {})
        columns_data = profile_data.get("columns", [])

        columns = [
            ColumnProfile(
                column_name=c["column_name"],
                detected_data_type=c["detected_data_type"],
                null_count=c["null_count"],
                null_percentage=c["null_percentage"],
                unique_count=c["unique_count"],
                minimum=c.get("minimum"),
                maximum=c.get("maximum"),
                mean=c.get("mean"),
                median=c.get("median"),
                sample_values=c.get("sample_values", []),
            )
            for c in columns_data
        ]

        summary = DatasetProfileSummary(
            row_count=summary_data.get("row_count", dataset.row_count or 0),
            column_count=summary_data.get("column_count", dataset.column_count or 0),
            duplicate_rows=summary_data.get("duplicate_rows", 0),
            total_missing_values=summary_data.get("total_missing_values", 0),
            overall_data_quality_score=summary_data.get("overall_data_quality_score", 0.0),
        )

        warnings = ProfileWarnings(
            duplicate_rows_count=warnings_data.get("duplicate_rows_count", 0),
            completely_empty_columns=warnings_data.get("completely_empty_columns", []),
            high_null_columns=warnings_data.get("high_null_columns", []),
            invalid_values_count=warnings_data.get("invalid_values_count", 0),
        )

        return DatasetProfileResponse(
            dataset_id=dataset.id,
            summary=summary,
            columns=columns,
            warnings=warnings,
            created_at=dataset.created_at,
        )

    @classmethod
    def get_dataset_quality(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
    ) -> DataQualityResponse:
        """Retrieve data quality report for a dataset owned by the user.

        Raises:
            HTTPException(404): If dataset does not exist or user lacks permission.
        """
        dataset = cls.get_dataset(db, user, dataset_id)
        profile_data, quality_report = cls._ensure_dataset_profiled(db, dataset)

        quality_metrics_data = profile_data.get("quality_metrics", {})
        metrics = None
        if quality_metrics_data:
            metrics = DataQualityBreakdown(
                completeness_score=quality_metrics_data.get("completeness_score", 0.0),
                uniqueness_score=quality_metrics_data.get("uniqueness_score", 0.0),
                validity_score=quality_metrics_data.get("validity_score", 0.0),
                completely_empty_columns=quality_metrics_data.get("completely_empty_columns", []),
                high_null_columns=quality_metrics_data.get("high_null_columns", []),
            )

        return DataQualityResponse(
            id=quality_report.id,
            dataset_id=dataset.id,
            quality_score=quality_report.quality_score,
            missing_values=quality_report.missing_values,
            duplicate_rows=quality_report.duplicate_rows,
            invalid_values=quality_report.invalid_values,
            created_at=quality_report.created_at,
            metrics=metrics,
        )
