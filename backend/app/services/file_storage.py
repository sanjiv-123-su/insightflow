import logging
from pathlib import Path
import re
from typing import Optional, Tuple
import uuid
import zipfile

from fastapi import HTTPException, UploadFile, status
import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)

# Supported extensions
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}

# Allowed MIME types per extension
ALLOWED_MIME_TYPES = {
    ".csv": {
        "text/csv",
        "text/plain",
        "application/csv",
        "application/x-csv",
        "text/x-csv",
        "text/comma-separated-values",
        "application/vnd.ms-excel",
        "application/octet-stream",
    },
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/zip",
        "application/x-zip-compressed",
        "application/octet-stream",
    },
}

# Magic bytes signature for ZIP/XLSX
ZIP_MAGIC_BYTES = b"PK\x03\x04"


class FileStorageService:
    """Service handling file validation, storage, and Pandas structural verification."""

    @staticmethod
    def validate_file_metadata(filename: Optional[str], content_type: Optional[str]) -> str:
        """Validate filename, extension, and MIME type.

        Returns normalized extension without leading dot (e.g. 'csv', 'xlsx').
        """
        if not filename or not filename.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid filename must be provided.",
            )

        # Extract and normalize extension
        ext = Path(filename.strip()).suffix.lower()
        if not ext or ext not in ALLOWED_EXTENSIONS:
            allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension '{ext}'. InsightFlow currently supports: {allowed_list}.",
            )

        # Validate MIME type where practical
        if content_type:
            normalized_mime = content_type.split(";")[0].strip().lower()
            allowed_mimes = ALLOWED_MIME_TYPES.get(ext, set())
            if normalized_mime and normalized_mime not in allowed_mimes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid MIME type '{content_type}' for {ext} file.",
                )

        return ext.lstrip(".")

    @staticmethod
    def generate_safe_filename(original_filename: str, dataset_id: uuid.UUID) -> str:
        """Generate a safe stored filename immune to path traversal or collisions."""
        ext = Path(original_filename).suffix.lower()
        base_stem = Path(original_filename).stem
        # Keep only alphanumeric characters, hyphens, and underscores
        clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", base_stem).strip("._")
        if not clean_stem:
            clean_stem = "dataset"
        clean_stem = clean_stem[:50]
        return f"{dataset_id}_{clean_stem}{ext}"

    @classmethod
    async def save_upload_file(
        cls,
        upload_file: UploadFile,
        dataset_id: uuid.UUID,
    ) -> Tuple[Path, int, str]:
        """Stream an uploaded file to storage outside source directory with size limits.

        Returns:
            Tuple of (saved_file_path, file_size_in_bytes, safe_stored_filename)
        """
        ext = Path(upload_file.filename or "").suffix.lower()
        safe_filename = cls.generate_safe_filename(upload_file.filename or "dataset", dataset_id)
        storage_dir = settings.upload_path
        target_path = storage_dir / safe_filename

        max_size = settings.MAX_UPLOAD_SIZE_BYTES
        max_mb = max_size // (1024 * 1024)

        total_bytes = 0
        chunk_size = 1024 * 1024  # 1MB chunks

        try:
            with open(target_path, "wb") as buffer:
                while True:
                    chunk = await upload_file.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_size:
                        buffer.close()
                        cls.delete_file(target_path)
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail=f"File size exceeds maximum allowed limit of {max_mb} MB.",
                        )
                    buffer.write(chunk)

            if total_bytes == 0:
                cls.delete_file(target_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded file is empty (0 bytes).",
                )

            return target_path, total_bytes, safe_filename

        except HTTPException:
            cls.delete_file(target_path)
            raise
        except Exception as exc:
            cls.delete_file(target_path)
            logger.error("Failed to stream upload file '%s': %s", upload_file.filename, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while saving the uploaded file.",
            )

    @classmethod
    def validate_file_content(cls, file_path: Path, file_type: str) -> Tuple[Optional[int], Optional[int]]:
        """Validate file structure using Pandas without executing arbitrary code.

        Returns:
            Tuple of (row_count, column_count)
        """
        if file_type == "xlsx":
            return cls._validate_xlsx(file_path)
        elif file_type == "csv":
            return cls._validate_csv(file_path)
        else:
            cls.delete_file(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{file_type}'.",
            )

    @classmethod
    def _validate_xlsx(cls, file_path: Path) -> Tuple[Optional[int], Optional[int]]:
        """Verify XLSX signature and basic sheet parseability via openpyxl/Pandas."""
        # 1. Verify ZIP magic bytes
        try:
            with open(file_path, "rb") as f:
                header = f.read(4)
                if header != ZIP_MAGIC_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid XLSX file: file header does not match Excel OpenXML format.",
                    )
        except OSError as exc:
            cls.delete_file(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to read uploaded file: {exc}",
            )

        # 2. Check ZIP container integrity
        if not zipfile.is_zipfile(file_path):
            cls.delete_file(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid XLSX file: damaged or corrupt ZIP structure.",
            )

        # 3. Read first few rows with Pandas openpyxl engine (does NOT execute VBA macros)
        try:
            df = pd.read_excel(file_path, nrows=5, engine="openpyxl")
            if df.columns.empty or len(df.columns) == 0:
                cls.delete_file(file_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Excel file contains no valid columns or headers.",
                )
            column_count = int(len(df.columns))

            # Attempt to determine row count quickly
            try:
                full_df = pd.read_excel(file_path, engine="openpyxl")
                row_count = int(len(full_df))
            except Exception:
                row_count = None

            return row_count, column_count

        except HTTPException:
            cls.delete_file(file_path)
            raise
        except Exception as exc:
            cls.delete_file(file_path)
            logger.warning("XLSX parsing failed for '%s': %s", file_path.name, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupt Excel spreadsheet. Please verify file integrity.",
            )

    @classmethod
    def _validate_csv(cls, file_path: Path) -> Tuple[Optional[int], Optional[int]]:
        """Verify CSV encoding, absence of binary/null bytes, and basic structure via Pandas."""
        # 1. Check for null bytes to reject binary files masquerading as CSV
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                if b"\x00" in chunk:
                    cls.delete_file(file_path)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid CSV file: binary data or null bytes detected.",
                    )
        except OSError as exc:
            cls.delete_file(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to read uploaded file: {exc}",
            )

        # 2. Parse sample with Pandas
        df = None
        for encoding in ["utf-8", "latin-1"]:
            try:
                df = pd.read_csv(file_path, nrows=5, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except pd.errors.EmptyDataError:
                cls.delete_file(file_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CSV file is empty or contains no readable columns.",
                )
            except Exception as exc:
                cls.delete_file(file_path)
                logger.warning("CSV read error with encoding %s: %s", encoding, exc)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Malformed CSV file: unable to parse row and column structure.",
                )

        if df is None:
            cls.delete_file(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to decode CSV file with supported encodings (UTF-8, Latin-1).",
            )

        if df.columns.empty or len(df.columns) == 0:
            cls.delete_file(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file contains no valid columns.",
            )

        column_count = int(len(df.columns))

        # Accurate row count for CSV
        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                total_lines = sum(1 for _ in f)
                row_count = max(0, total_lines - 1) if total_lines > 0 else 0
        except Exception:
            row_count = None

        return row_count, column_count

    @staticmethod
    def delete_file(file_path: Path) -> None:
        """Safely delete file if it exists."""
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError as exc:
            logger.warning("Failed to delete file '%s': %s", file_path, exc)

    @classmethod
    def get_stored_file_path(cls, dataset_id: uuid.UUID) -> Optional[Path]:
        """Locate stored file on disk matching dataset UUID prefix."""
        upload_dir = settings.upload_path
        matches = list(upload_dir.glob(f"{dataset_id}_*"))
        if matches and matches[0].exists():
            return matches[0]
        return None
