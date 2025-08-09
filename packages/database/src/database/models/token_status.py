"""
TokenStatus model for tracking Tiger API token refresh operations.
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

from sqlalchemy import (
    CheckConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel


class TokenRefreshStatus(str, Enum):
    """Status of token refresh operations."""

    PENDING = "pending"  # Refresh scheduled but not started
    IN_PROGRESS = "in_progress"  # Refresh currently running
    SUCCESS = "success"  # Refresh completed successfully
    FAILED = "failed"  # Refresh failed
    EXPIRED = "expired"  # Token expired before refresh
    CANCELLED = "cancelled"  # Refresh was cancelled


class RefreshTrigger(str, Enum):
    """What triggered the token refresh."""

    SCHEDULED = "scheduled"  # Automatic scheduled refresh
    MANUAL = "manual"  # Manually triggered refresh
    ON_DEMAND = "on_demand"  # Triggered by API call needing fresh token
    EXPIRY_SOON = "expiry_soon"  # Triggered because token expires soon
    EXPIRED = "expired"  # Triggered because token already expired
    ERROR = "error"  # Triggered by authentication error


class TokenStatus(BaseModel):
    """
    Track Tiger API token refresh operations and status.

    This model maintains a history of token refresh attempts,
    success/failure rates, and helps with automatic token management.
    """

    __tablename__ = "token_statuses"

    # Account relationship
    tiger_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tiger_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tiger account this token status belongs to",
    )

    # Refresh operation details
    status: Mapped[TokenRefreshStatus] = mapped_column(
        SQLEnum(TokenRefreshStatus),
        nullable=False,
        default=TokenRefreshStatus.PENDING,
        index=True,
        comment="Current status of the token refresh",
    )

    trigger: Mapped[RefreshTrigger] = mapped_column(
        SQLEnum(RefreshTrigger),
        nullable=False,
        index=True,
        comment="What triggered this refresh operation",
    )

    # Token information (before refresh)
    old_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="When the old token was set to expire"
    )

    old_token_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="SHA-256 hash of the old access token"
    )

    # Token information (after refresh)
    new_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="When the new token expires"
    )

    new_token_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="SHA-256 hash of the new access token"
    )

    # Timing information
    started_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, index=True, comment="When the refresh operation started"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, index=True, comment="When the refresh operation completed"
    )

    duration_ms: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Duration of the refresh operation in milliseconds"
    )

    # Next scheduled refresh
    next_refresh_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, index=True, comment="When the next refresh is scheduled"
    )

    # Error information
    error_code: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="Error code if refresh failed"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Detailed error message if refresh failed"
    )

    retry_count: Mapped[int] = mapped_column(
        default=0, comment="Number of retry attempts made"
    )

    max_retries: Mapped[int] = mapped_column(
        default=3, comment="Maximum number of retries allowed"
    )

    # API response details
    api_response_code: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="HTTP response code from Tiger API"
    )

    api_response_time_ms: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="API response time in milliseconds"
    )

    # Additional metadata
    details: Mapped[Dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Additional details about the refresh operation",
    )

    # Environment and context
    environment: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Environment where refresh occurred (sandbox/production)",
    )

    server_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Version of the MCP server performing the refresh",
    )

    # Relationship
    tiger_account: Mapped["TigerAccount"] = relationship(
        "TigerAccount", back_populates="token_statuses", lazy="selectin"
    )

    # Table constraints
    __table_args__ = (
        # Check constraints
        CheckConstraint(
            "retry_count >= 0", name="ck_token_status_retry_count_positive"
        ),
        CheckConstraint(
            "max_retries >= 0", name="ck_token_status_max_retries_positive"
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_token_status_duration_positive",
        ),
        CheckConstraint(
            "api_response_time_ms IS NULL OR api_response_time_ms >= 0",
            name="ck_token_status_api_time_positive",
        ),
        CheckConstraint(
            "started_at IS NULL OR completed_at IS NULL OR completed_at >= started_at",
            name="ck_token_status_completed_after_started",
        ),
        # Composite indexes
        Index("ix_token_status_account_status", "tiger_account_id", "status"),
        Index("ix_token_status_trigger_created", "trigger", "created_at"),
        Index("ix_token_status_next_refresh", "next_refresh_at"),
        Index(
            "ix_token_status_account_next_refresh",
            "tiger_account_id",
            "next_refresh_at",
        ),
        # Index for failed operations
        Index(
            "ix_token_status_failures",
            "tiger_account_id",
            "status",
            "created_at",
            postgresql_where="status = 'failed'",
        ),
        # Index for success rate analysis
        Index(
            "ix_token_status_completed_operations",
            "tiger_account_id",
            "status",
            "completed_at",
        ),
    )

    def __str__(self) -> str:
        """String representation."""
        account_name = (
            self.tiger_account.account_name if self.tiger_account else "Unknown"
        )
        return f"TokenStatus({account_name}:{self.status.value}:{self.trigger.value})"

    @property
    def is_in_progress(self) -> bool:
        """Check if refresh is currently in progress."""
        return self.status == TokenRefreshStatus.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        """Check if refresh operation is completed (success or failure)."""
        return self.status in [
            TokenRefreshStatus.SUCCESS,
            TokenRefreshStatus.FAILED,
            TokenRefreshStatus.EXPIRED,
            TokenRefreshStatus.CANCELLED,
        ]

    @property
    def is_successful(self) -> bool:
        """Check if refresh was successful."""
        return self.status == TokenRefreshStatus.SUCCESS

    @property
    def can_retry(self) -> bool:
        """Check if refresh can be retried."""
        return (
            self.status == TokenRefreshStatus.FAILED
            and self.retry_count < self.max_retries
        )

    @property
    def total_duration_seconds(self) -> Optional[float]:
        """Get total duration in seconds."""
        if self.duration_ms is not None:
            return self.duration_ms / 1000.0
        return None

    def start_refresh(self) -> None:
        """Mark refresh operation as started."""
        self.status = TokenRefreshStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()

    def complete_refresh(
        self,
        success: bool,
        new_token_expires_at: Optional[datetime] = None,
        new_token_hash: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        api_response_code: Optional[int] = None,
        api_response_time_ms: Optional[int] = None,
    ) -> None:
        """Complete the refresh operation."""
        now = datetime.utcnow()
        self.completed_at = now

        if self.started_at:
            self.duration_ms = int((now - self.started_at).total_seconds() * 1000)

        if success:
            self.status = TokenRefreshStatus.SUCCESS
            self.new_token_expires_at = new_token_expires_at
            self.new_token_hash = new_token_hash

            # Schedule next refresh (refresh 1 hour before expiry)
            if new_token_expires_at:
                self.next_refresh_at = new_token_expires_at - timedelta(hours=1)
        else:
            self.status = TokenRefreshStatus.FAILED
            self.error_code = error_code
            self.error_message = error_message

        self.api_response_code = api_response_code
        self.api_response_time_ms = api_response_time_ms

    def cancel_refresh(self, reason: str) -> None:
        """Cancel the refresh operation."""
        self.status = TokenRefreshStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.details["cancellation_reason"] = reason

    def retry_refresh(self) -> None:
        """Prepare for retry attempt."""
        if not self.can_retry:
            raise ValueError("Refresh cannot be retried")

        self.retry_count += 1
        self.status = TokenRefreshStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.duration_ms = None
        self.error_code = None
        self.error_message = None

    def add_detail(self, key: str, value) -> None:
        """Add detail information."""
        self.details[key] = value

    def get_detail(self, key: str, default=None):
        """Get detail information."""
        return self.details.get(key, default)

    @classmethod
    def create_scheduled_refresh(
        cls,
        tiger_account_id: uuid.UUID,
        next_refresh_at: datetime,
        current_token_expires_at: Optional[datetime] = None,
        current_token_hash: Optional[str] = None,
    ) -> "TokenStatus":
        """Create a new scheduled token refresh."""
        return cls(
            tiger_account_id=tiger_account_id,
            status=TokenRefreshStatus.PENDING,
            trigger=RefreshTrigger.SCHEDULED,
            old_token_expires_at=current_token_expires_at,
            old_token_hash=current_token_hash,
            next_refresh_at=next_refresh_at,
        )

    @classmethod
    def create_manual_refresh(
        cls,
        tiger_account_id: uuid.UUID,
        current_token_expires_at: Optional[datetime] = None,
        current_token_hash: Optional[str] = None,
    ) -> "TokenStatus":
        """Create a new manual token refresh."""
        return cls(
            tiger_account_id=tiger_account_id,
            status=TokenRefreshStatus.PENDING,
            trigger=RefreshTrigger.MANUAL,
            old_token_expires_at=current_token_expires_at,
            old_token_hash=current_token_hash,
        )

    @classmethod
    def create_on_demand_refresh(
        cls,
        tiger_account_id: uuid.UUID,
        trigger: RefreshTrigger = RefreshTrigger.ON_DEMAND,
        current_token_expires_at: Optional[datetime] = None,
        current_token_hash: Optional[str] = None,
    ) -> "TokenStatus":
        """Create a new on-demand token refresh."""
        return cls(
            tiger_account_id=tiger_account_id,
            status=TokenRefreshStatus.PENDING,
            trigger=trigger,
            old_token_expires_at=current_token_expires_at,
            old_token_hash=current_token_hash,
        )
