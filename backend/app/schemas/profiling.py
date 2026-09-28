from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ColumnProfile(BaseModel):
    column_name: str = Field(..., description="Name of the column")
    detected_data_type: str = Field(..., description="Inferred data type (e.g. integer, float, string, boolean, datetime)")
    null_count: int = Field(..., ge=0, description="Count of missing/null values")
    null_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of missing values")
    unique_count: int = Field(..., ge=0, description="Count of distinct non-null values")
    minimum: Optional[Any] = Field(default=None, description="Minimum value if applicable")
    maximum: Optional[Any] = Field(default=None, description="Maximum value if applicable")
    mean: Optional[float] = Field(default=None, description="Mean value if numeric")
    median: Optional[float] = Field(default=None, description="Median value if numeric")
    sample_values: List[Any] = Field(default_factory=list, description="Sample of representative non-null values")


class DatasetProfileSummary(BaseModel):
    row_count: int = Field(..., ge=0, description="Total number of rows")
    column_count: int = Field(..., ge=0, description="Total number of columns")
    duplicate_rows: int = Field(..., ge=0, description="Number of duplicate rows")
    total_missing_values: int = Field(..., ge=0, description="Total missing cells across all columns")
    overall_data_quality_score: float = Field(..., ge=0.0, le=100.0, description="Overall quality score (0-100)")


class ProfileWarnings(BaseModel):
    duplicate_rows_count: int = Field(default=0, ge=0)
    completely_empty_columns: List[str] = Field(default_factory=list)
    high_null_columns: List[str] = Field(default_factory=list)
    invalid_values_count: int = Field(default=0, ge=0)


class DatasetProfileResponse(BaseModel):
    dataset_id: uuid.UUID
    summary: DatasetProfileSummary
    columns: List[ColumnProfile]
    warnings: ProfileWarnings
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DataQualityBreakdown(BaseModel):
    completeness_score: float = Field(..., ge=0.0, le=100.0)
    uniqueness_score: float = Field(..., ge=0.0, le=100.0)
    validity_score: float = Field(..., ge=0.0, le=100.0)
    completely_empty_columns: List[str] = Field(default_factory=list)
    high_null_columns: List[str] = Field(default_factory=list)


class DataQualityResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    quality_score: float = Field(..., ge=0.0, le=100.0)
    missing_values: int = Field(..., ge=0)
    duplicate_rows: int = Field(..., ge=0)
    invalid_values: int = Field(..., ge=0)
    created_at: datetime
    metrics: Optional[DataQualityBreakdown] = None

    model_config = ConfigDict(from_attributes=True)
