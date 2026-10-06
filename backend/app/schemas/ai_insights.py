from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class AiInsightsResponse(BaseModel):
    """Structured response containing AI natural language explanation grounded in verified metrics."""

    dataset_id: uuid.UUID = Field(..., description="Target dataset UUID")
    headline: str = Field(..., description="Concise, high-impact headline summarizing performance")
    summary: str = Field(..., description="Comprehensive natural language business narrative")
    key_drivers: List[str] = Field(
        default_factory=list,
        description="Key contributing drivers extracted from verified data",
    )
    category_insight: Optional[str] = Field(
        default=None,
        description="Natural language explanation of category performance and contributions",
    )
    regional_insight: Optional[str] = Field(
        default=None,
        description="Natural language explanation of regional and geographic contributions",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Data-grounded strategic recommendations",
    )
    verified_facts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Underlying verified metrics passed as grounding facts to the AI",
    )
    provider: str = Field(
        default="grounded_engine",
        description="Generation engine used: 'gemini', 'openai', or 'grounded_engine'",
    )
    created_at: datetime = Field(..., description="Timestamp when insights were generated")

    model_config = ConfigDict(from_attributes=True)
