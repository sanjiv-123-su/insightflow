import logging
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.ai_insights import AiInsightsResponse
from app.services.ai_insights import AiInsightsService
from app.services.auth import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["AI Insights"])


@router.get(
    "/{dataset_id}/ai-insights",
    response_model=AiInsightsResponse,
    summary="Get AI natural language explanation grounded in verified metrics",
    responses={
        200: {"description": "Grounded natural language insights explaining analytical metrics"},
        400: {"description": "Normal analytics failed or missing required numeric columns"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
    },
)
def get_ai_insights(
    dataset_id: uuid.UUID,
    use_cache: bool = Query(True, description="Whether to return cached insights if available"),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Generate or retrieve natural language business insights explaining verified analytics.

    Architecture pipeline:
    Database -> SQL/Pandas -> Verified Metrics -> AI Explanation Layer

    - AI explains existing analytical results.
    - AI does NOT calculate fundamental metrics.
    - Grounded in verified revenue, category, and regional drivers.
    """
    return AiInsightsService.get_or_generate_insights(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
        use_cache=use_cache,
    )


@router.post(
    "/{dataset_id}/ai-insights/regenerate",
    response_model=AiInsightsResponse,
    summary="Force regenerate AI natural language explanation",
    responses={
        200: {"description": "Freshly regenerated AI insights"},
        400: {"description": "Normal analytics failed or missing required numeric columns"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
    },
)
def regenerate_ai_insights(
    dataset_id: uuid.UUID,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Force re-run AI explanation generation against the latest verified analytics."""
    return AiInsightsService.get_or_generate_insights(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
        use_cache=False,
    )
