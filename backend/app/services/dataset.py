import logging
from pathlib import Path
from typing import List, Optional
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.user import User
from app.services.file_storage import FileStorageService

logger = logging.getLogger(__name__)


class DatasetService:
    """Service handling dataset uploads, validation, and user-scoped queries."""

    @classmethod
    async def upload_dataset(
        cls,
        db: Session,
        user: User,
        file: UploadFile,
    ) -> Dataset:
        """Process, validate, store an uploaded dataset, and persist record in Neon DB.

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

        # 3. Validate file content with Pandas (without executing arbitrary code)
        try:
            row_count, column_count = FileStorageService.validate_file_content(file_path, file_type)
        except Exception:
            # FileStorageService already cleaned up target file on exception
            raise

        # 4. Create and persist the Dataset record in Neon
        dataset = Dataset(
            id=dataset_id,
            user_id=user.id,
            name=display_name,
            original_filename=original_name,
            file_type=file_type,
            file_size=file_size,
            row_count=row_count,
            column_count=column_count,
            status="pending",
        )

        try:
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            logger.info(
                "Dataset %s successfully created for user %s (file: %s, size: %d bytes)",
                dataset.id,
                user.id,
                original_name,
                file_size,
            )
            return dataset
        except SQLAlchemyError as exc:
            db.rollback()
            FileStorageService.delete_file(file_path)
            logger.error("Failed to commit dataset record %s to database: %s", dataset_id, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while recording dataset.",
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
