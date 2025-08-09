"""
APIKey model for authentication and authorization.
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from sqlalchemy import (
    CheckConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel


class APIKeyScope(str, Enum):
    """API key access scopes."""

    # MCP Server access
    MCP_READ = "mcp:read"  # Read-only MCP operations
    MCP_WRITE = "mcp:write"  # Full MCP operations
    MCP_ADMIN = "mcp:admin"  # MCP server administration

    # Dashboard access
    DASHBOARD_READ = "dashboard:read"  # View dashboard data
    DASHBOARD_WRITE = "dashboard:write"  # Modify dashboard settings
    DASHBOARD_ADMIN = "dashboard:admin"  # Full dashboard administration

    # Trading operations (bound to specific account)
    TRADE_READ = "trade:read"  # View trading data
    TRADE_WRITE = "trade:write"  # Execute trades
    TRADE_ADMIN = "trade:admin"  # Full trading administration

    # Account management
    ACCOUNT_READ = "account:read"  # View account info
    ACCOUNT_WRITE = "account:write"  # Modify account settings
    ACCOUNT_ADMIN = "account:admin"  # Full account management

    # System administration
    SYSTEM_READ = "system:read"  # View system status
    SYSTEM_WRITE = "system:write"  # Modify system settings
    SYSTEM_ADMIN = "system:admin"  # Full system administration


class APIKeyStatus(str, Enum):
    """API key status options."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    EXPIRED = "expired"


class APIKey(BaseModel):
    """
    API keys for authenticating MCP server and dashboard access.

    API keys can be scoped to specific operations and optionally bound
    to specific Tiger accounts for trading operations.
    """

    __tablename__ = "api_keys"

    # Key identification
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="Human-readable key name"
    )

    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="SHA-256 hash of the API key",
    )

    key_prefix: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        index=True,
        comment="First 8 characters of key for identification",
    )

    # Status and lifecycle
    status: Mapped[APIKeyStatus] = mapped_column(
        SQLEnum(APIKeyStatus),
        nullable=False,
        default=APIKeyStatus.ACTIVE,
        index=True,
        comment="Current key status",
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, index=True, comment="When the key expires (null = no expiration)"
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, index=True, comment="When the key was last used"
    )

    # Access control
    scopes: Mapped[List[str]] = mapped_column(
        ARRAY(String(50)),
        nullable=False,
        default=list,
        comment="List of access scopes for this key",
    )

    # Optional account binding (for trading operations)
    tiger_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tiger_accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Tiger account this key is bound to (if any)",
    )

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(
        default=0, comment="Number of times this key has been used"
    )

    rate_limit_per_hour: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Rate limit per hour (null = no limit)"
    )

    rate_limit_per_day: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Rate limit per day (null = no limit)"
    )

    # IP restrictions
    allowed_ips: Mapped[List[str]] = mapped_column(
        ARRAY(String(45)),  # IPv6 max length
        nullable=False,
        default=list,
        comment="List of allowed IP addresses (empty = no restriction)",
    )

    # User agent restrictions
    allowed_user_agents: Mapped[List[str]] = mapped_column(
        ARRAY(String(255)),
        nullable=False,
        default=list,
        comment="List of allowed user agents (empty = no restriction)",
    )

    # Additional metadata
    description: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Optional key description"
    )

    tags: Mapped[Dict] = mapped_column(
        JSONB, nullable=False, default=dict, comment="Flexible tags for categorization"
    )

    # Creator information
    created_by: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Who created this API key"
    )

    # Relationships
    tiger_account: Mapped[Optional["TigerAccount"]] = relationship(
        "TigerAccount", back_populates="api_keys", lazy="selectin"
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="api_key",
        cascade="all, delete-orphan",
        order_by="desc(AuditLog.created_at)",
    )

    # Table constraints
    __table_args__ = (
        # Check constraints
        CheckConstraint("usage_count >= 0", name="ck_api_keys_usage_count_positive"),
        CheckConstraint(
            "rate_limit_per_hour IS NULL OR rate_limit_per_hour > 0",
            name="ck_api_keys_rate_limit_hour_positive",
        ),
        CheckConstraint(
            "rate_limit_per_day IS NULL OR rate_limit_per_day > 0",
            name="ck_api_keys_rate_limit_day_positive",
        ),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at",
            name="ck_api_keys_expires_after_created",
        ),
        # Composite indexes
        Index("ix_api_keys_status_expires", "status", "expires_at"),
        Index("ix_api_keys_account_status", "tiger_account_id", "status"),
        Index("ix_api_keys_created_by", "created_by"),
    )

    def __str__(self) -> str:
        """String representation."""
        return f"APIKey({self.name}:{self.key_prefix}...)"

    @property
    def is_active(self) -> bool:
        """Check if API key is active and not expired."""
        if self.status != APIKeyStatus.ACTIVE:
            return False
        if self.expires_at and self.expires_at <= datetime.utcnow():
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if API key has expired."""
        return self.expires_at is not None and self.expires_at <= datetime.utcnow()

    @property
    def expires_in_days(self) -> Optional[int]:
        """Get number of days until expiration."""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    def has_scope(self, scope: APIKeyScope) -> bool:
        """Check if key has specific scope."""
        return scope.value in self.scopes

    def has_any_scope(self, scopes: List[APIKeyScope]) -> bool:
        """Check if key has any of the specified scopes."""
        return any(scope.value in self.scopes for scope in scopes)

    def has_all_scopes(self, scopes: List[APIKeyScope]) -> bool:
        """Check if key has all specified scopes."""
        return all(scope.value in self.scopes for scope in scopes)

    def add_scope(self, scope: APIKeyScope) -> None:
        """Add scope to API key."""
        if scope.value not in self.scopes:
            self.scopes.append(scope.value)

    def remove_scope(self, scope: APIKeyScope) -> None:
        """Remove scope from API key."""
        if scope.value in self.scopes:
            self.scopes.remove(scope.value)

    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed."""
        if not self.allowed_ips:  # Empty list means no restriction
            return True
        return ip_address in self.allowed_ips

    def is_user_agent_allowed(self, user_agent: str) -> bool:
        """Check if user agent is allowed."""
        if not self.allowed_user_agents:  # Empty list means no restriction
            return True
        return any(allowed_ua in user_agent for allowed_ua in self.allowed_user_agents)

    def can_access_account(self, account_id: uuid.UUID) -> bool:
        """Check if key can access specific Tiger account."""
        # If key is not bound to any account, it can access any account
        # (assuming it has the right scopes)
        if not self.tiger_account_id:
            return True
        # If key is bound to an account, it can only access that account
        return self.tiger_account_id == account_id

    def record_usage(self, ip_address: Optional[str] = None) -> None:
        """Record API key usage."""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()

    def revoke(self, reason: Optional[str] = None) -> None:
        """Revoke the API key."""
        self.status = APIKeyStatus.REVOKED
        if reason:
            self.tags["revocation_reason"] = reason
            self.tags["revoked_at"] = datetime.utcnow().isoformat()

    def extend_expiration(self, days: int) -> None:
        """Extend expiration by specified days."""
        if self.expires_at:
            self.expires_at += timedelta(days=days)
        else:
            self.expires_at = datetime.utcnow() + timedelta(days=days)

    def to_dict_safe(self) -> Dict:
        """Convert to dictionary without sensitive data."""
        data = self.to_dict()
        # Remove the hash but keep prefix for identification
        data.pop("key_hash", None)
        return data

    @classmethod
    def get_trading_scopes(cls) -> List[APIKeyScope]:
        """Get all trading-related scopes."""
        return [
            APIKeyScope.TRADE_READ,
            APIKeyScope.TRADE_WRITE,
            APIKeyScope.TRADE_ADMIN,
        ]

    @classmethod
    def get_dashboard_scopes(cls) -> List[APIKeyScope]:
        """Get all dashboard-related scopes."""
        return [
            APIKeyScope.DASHBOARD_READ,
            APIKeyScope.DASHBOARD_WRITE,
            APIKeyScope.DASHBOARD_ADMIN,
        ]

    @classmethod
    def get_mcp_scopes(cls) -> List[APIKeyScope]:
        """Get all MCP-related scopes."""
        return [APIKeyScope.MCP_READ, APIKeyScope.MCP_WRITE, APIKeyScope.MCP_ADMIN]
