import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"
    __table_args__ = (
        CheckConstraint(
            "missing_values >= 0",
            name="ck_data_quality_missing_values_positive",
        ),
        CheckConstraint(
            "duplicate_rows >= 0",
            name="ck_data_quality_duplicate_rows_positive",
        ),
        CheckConstraint(
            "invalid_values >= 0",
            name="ck_data_quality_invalid_values_positive",
        ),
        CheckConstraint(
            "quality_score >= 0.0 AND quality_score <= 100.0",
            name="ck_data_quality_score_range",
        ),
        Index("ix_data_quality_reports_dataset_id_created_at", "dataset_id", "created_at"),
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
    missing_values: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    duplicate_rows: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    invalid_values: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="quality_reports")

    def __repr__(self) -> str:
        return f"<DataQualityReport(id={self.id}, dataset_id={self.dataset_id}, score={self.quality_score})>"
