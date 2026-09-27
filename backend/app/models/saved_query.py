import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.user import User


class SavedQuery(Base):
    __tablename__ = "saved_queries"
    __table_args__ = (
        Index("ix_saved_queries_user_id_dataset_id", "user_id", "dataset_id"),
        Index("ix_saved_queries_dataset_id", "dataset_id"),
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
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="saved_queries")
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="saved_queries")

    def __repr__(self) -> str:
        return f"<SavedQuery(id={self.id}, name={self.name!r}, user_id={self.user_id})>"
