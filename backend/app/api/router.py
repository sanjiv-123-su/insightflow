from fastapi import APIRouter

from app.api.ai_insights import router as ai_insights_router
from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.health import router as health_router
from app.api.sql_explorer import router as sql_explorer_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(datasets_router)
api_router.include_router(sql_explorer_router)
api_router.include_router(ai_insights_router)
