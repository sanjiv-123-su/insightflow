from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class RootResponse(BaseModel):
    message: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str
    message: str
    current_database: Optional[str] = None
    server_version: Optional[str] = None
    detail: Optional[str] = None
