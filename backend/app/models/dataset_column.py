import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "column_name",
            name="uq_dataset_columns_dataset_colname",
        ),
        CheckConstraint(
            "null_count >= 0",
            name="ck_dataset_columns_null_count_positive",
        ),
        CheckConstraint(
            "unique_count >= 0",
            name="ck_dataset_columns_unique_count_positive",
        ),
        Index("ix_dataset_columns_dataset_id", "dataset_id"),
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
    )
    column_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    data_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    nullable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    null_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    unique_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="columns")

    def __repr__(self) -> str:
        return f"<DatasetColumn(id={self.id}, dataset_id={self.dataset_id}, column_name={self.column_name!r})>"
