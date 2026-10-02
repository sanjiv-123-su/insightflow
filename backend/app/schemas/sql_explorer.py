from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class SqlQueryRequest(BaseModel):
    """Request payload for executing a read-only SQL query on a dataset."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Analytical SELECT query to execute against the dataset",
        examples=["SELECT * FROM dataset LIMIT 10"],
    )
    limit: Optional[int] = Field(
        default=500,
        ge=1,
        le=1000,
        description="Maximum number of rows to return (capped at 1000)",
    )


class SqlQueryResponse(BaseModel):
    """Standardized table-friendly response for SQL query execution."""

    dataset_id: uuid.UUID = Field(..., description="Target dataset UUID")
    table_name: str = Field(default="dataset", description="Primary SQL table alias for dataset")
    columns: List[str] = Field(..., description="List of column names in query projection")
    column_types: Dict[str, str] = Field(
        default_factory=dict,
        description="Inferred data types for each returned column",
    )
    rows: List[Dict[str, Any]] = Field(..., description="Table rows formatted as JSON records")
    row_count: int = Field(..., description="Number of rows returned in current response")
    truncated: bool = Field(
        default=False,
        description="Whether query results were capped by the row limit",
    )
    execution_time_ms: float = Field(..., description="Query execution duration in milliseconds")


class SavedQueryCreate(BaseModel):
    """Payload to save a new analytical SQL query."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Friendly name for the saved query",
        examples=["Top 10 High Value Customers"],
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Read-only SELECT query string",
        examples=["SELECT customer_id, SUM(amount) AS total FROM dataset GROUP BY customer_id ORDER BY total DESC LIMIT 10"],
    )


class SavedQueryUpdate(BaseModel):
    """Payload to update an existing saved query."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    query: Optional[str] = Field(None, min_length=1, max_length=10000)


class SavedQueryResponse(BaseModel):
    """Saved query entity metadata and SQL text."""

    id: uuid.UUID = Field(..., description="Unique saved query UUID")
    dataset_id: uuid.UUID = Field(..., description="Associated dataset UUID")
    user_id: uuid.UUID = Field(..., description="Owner user UUID")
    name: str = Field(..., description="Saved query display name")
    query: str = Field(..., description="SQL query string")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)
