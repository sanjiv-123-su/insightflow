from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class DatasetBase(BaseModel):
    name: str = Field(..., description="Dataset display name")
    original_filename: str = Field(..., description="Original filename uploaded by the user")
    file_type: str = Field(..., description="Normalized file format type (csv, xlsx)")
    file_size: int = Field(..., description="File size in bytes", ge=0)
    status: str = Field(default="pending", description="Processing status of the dataset")
    row_count: Optional[int] = Field(default=None, description="Number of rows detected")
    column_count: Optional[int] = Field(default=None, description="Number of columns detected")


class DatasetResponse(DatasetBase):
    id: uuid.UUID = Field(..., description="Unique dataset UUID")
    user_id: uuid.UUID = Field(..., description="Owner user UUID")
    created_at: datetime = Field(..., description="Upload timestamp")

    model_config = ConfigDict(from_attributes=True)


class DatasetUploadResponse(DatasetResponse):
    message: str = Field(default="Dataset uploaded successfully", description="Status message")

    model_config = ConfigDict(from_attributes=True)
