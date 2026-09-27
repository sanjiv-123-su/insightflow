import uuid
from datetime import datetime
from typing import Any, Dict, TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset


class AnalyticsResult(Base):
    __tablename__ = "analytics_results"
    __table_args__ = (
        Index("ix_analytics_results_dataset_id_analysis_type", "dataset_id", "analysis_type"),
        Index("ix_analytics_results_dataset_id_created_at", "dataset_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    result: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="analytics_results")

    def __repr__(self) -> str:
        return f"<AnalyticsResult(id={self.id}, dataset_id={self.dataset_id}, analysis_type={self.analysis_type!r})>"
