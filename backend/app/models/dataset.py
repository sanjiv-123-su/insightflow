import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.analytics_result import AnalyticsResult
    from app.models.dataset_column import DatasetColumn
    from app.models.quality_report import DataQualityReport
    from app.models.saved_query import SavedQuery
    from app.models.user import User


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        CheckConstraint("file_size >= 0", name="ck_datasets_file_size_positive"),
        CheckConstraint(
            "row_count IS NULL OR row_count >= 0",
            name="ck_datasets_row_count_positive",
        ),
        CheckConstraint(
            "column_count IS NULL OR column_count >= 0",
            name="ck_datasets_column_count_positive",
        ),
        Index("ix_datasets_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    row_count: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    column_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="datasets")
    columns: Mapped[List["DatasetColumn"]] = relationship(
        "DatasetColumn",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    quality_reports: Mapped[List["DataQualityReport"]] = relationship(
        "DataQualityReport",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    saved_queries: Mapped[List["SavedQuery"]] = relationship(
        "SavedQuery",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    analytics_results: Mapped[List["AnalyticsResult"]] = relationship(
        "AnalyticsResult",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Dataset(id={self.id}, name={self.name!r}, status={self.status!r})>"
