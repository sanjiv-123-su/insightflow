from fastapi import APIRouter

from app.schemas.health import HealthResponse, RootResponse
from app.services.health import HealthService

router = APIRouter()


@router.get("/", response_model=RootResponse, summary="Root status")
def root():
    return HealthService.get_root_message()


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health():
    return HealthService.get_health_status()
