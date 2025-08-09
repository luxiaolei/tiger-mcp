"""
SQLAlchemy base configuration and declarative base.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import DateTime, String, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    # Type annotation for registry
    type_annotation_map = {
        str: String(255),
        uuid.UUID: UUID(as_uuid=True),
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class UUIDMixin:
    """Mixin for UUID primary key."""

    @declared_attr
    def id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
        )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID primary key and timestamps."""

    __abstract__ = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.key: getattr(self, column.key) for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """String representation of model."""
        class_name = self.__class__.__name__
        attrs = []
        for key, value in self.to_dict().items():
            if key in ["id", "created_at", "updated_at"]:
                continue
            if isinstance(value, str) and len(value) > 50:
                value = f"{value[:47]}..."
            attrs.append(f"{key}={value!r}")
        return f"{class_name}({', '.join(attrs)})"


# Event listener to automatically update updated_at timestamp
@event.listens_for(BaseModel, "before_update", propagate=True)
def update_timestamp(mapper, connection, target):
    """Update the updated_at timestamp before updates."""
    target.updated_at = datetime.now(timezone.utc)
