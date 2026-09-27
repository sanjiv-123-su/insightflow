from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.health import DatabaseHealthResponse, HealthResponse, RootResponse
from app.services.health import HealthService

router = APIRouter()


@router.get("/", response_model=RootResponse, summary="Root status")
def root():
    return HealthService.get_root_message()


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health():
    return HealthService.get_health_status()


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    summary="Neon database connection health",
    responses={
        200: {"description": "Database connection successful"},
        503: {"description": "Database disconnected or connection error"},
    },
)
def health_database(response: Response, db: Session = Depends(get_db)):
    """Test connection to Neon PostgreSQL using the FastAPI database dependency."""
    result, is_healthy = HealthService.test_database_connection(db)
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get(
    "/db-test",
    response_model=DatabaseHealthResponse,
    summary="Database connection test endpoint",
    responses={
        200: {"description": "Database connection successful"},
        503: {"description": "Database disconnected or connection error"},
    },
)
def db_test(response: Response, db: Session = Depends(get_db)):
    """Convenience endpoint for testing database connectivity directly."""
    result, is_healthy = HealthService.test_database_connection(db)
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
