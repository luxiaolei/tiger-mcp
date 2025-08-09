"""
AuditLog model for tracking system operations and changes.
"""

import uuid
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import CheckConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel


class AuditAction(str, Enum):
    """Types of actions that can be audited."""

    # Account operations
    ACCOUNT_CREATE = "account_create"
    ACCOUNT_UPDATE = "account_update"
    ACCOUNT_DELETE = "account_delete"
    ACCOUNT_LOGIN = "account_login"
    ACCOUNT_LOGOUT = "account_logout"
    ACCOUNT_TOKEN_REFRESH = "account_token_refresh"

    # API key operations
    API_KEY_CREATE = "api_key_create"
    API_KEY_UPDATE = "api_key_update"
    API_KEY_DELETE = "api_key_delete"
    API_KEY_REVOKE = "api_key_revoke"
    API_KEY_USE = "api_key_use"

    # Trading operations
    TRADE_PLACE_ORDER = "trade_place_order"
    TRADE_CANCEL_ORDER = "trade_cancel_order"
    TRADE_MODIFY_ORDER = "trade_modify_order"
    TRADE_ORDER_FILLED = "trade_order_filled"
    TRADE_POSITION_UPDATE = "trade_position_update"

    # Data operations
    DATA_FETCH_QUOTES = "data_fetch_quotes"
    DATA_FETCH_HISTORICAL = "data_fetch_historical"
    DATA_FETCH_POSITIONS = "data_fetch_positions"
    DATA_FETCH_ORDERS = "data_fetch_orders"
    DATA_FETCH_ACCOUNT_INFO = "data_fetch_account_info"

    # System operations
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_CONFIG_UPDATE = "system_config_update"
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"

    # MCP operations
    MCP_CONNECT = "mcp_connect"
    MCP_DISCONNECT = "mcp_disconnect"
    MCP_TOOL_CALL = "mcp_tool_call"
    MCP_ERROR = "mcp_error"

    # Dashboard operations
    DASHBOARD_LOGIN = "dashboard_login"
    DASHBOARD_LOGOUT = "dashboard_logout"
    DASHBOARD_VIEW = "dashboard_view"
    DASHBOARD_CONFIG_UPDATE = "dashboard_config_update"

    # Security operations
    SECURITY_AUTH_FAIL = "security_auth_fail"
    SECURITY_ACCESS_DENIED = "security_access_denied"
    SECURITY_BREACH_DETECTED = "security_breach_detected"

    # Error operations
    ERROR_API_LIMIT = "error_api_limit"
    ERROR_NETWORK = "error_network"
    ERROR_AUTH = "error_auth"
    ERROR_SYSTEM = "error_system"


class AuditResult(str, Enum):
    """Result of the audited action."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    ERROR = "error"


class AuditSeverity(str, Enum):
    """Severity level of the audit event."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLog(BaseModel):
    """
    Comprehensive audit trail for all system operations.

    Tracks user actions, system events, API calls, trading operations,
    and security events for compliance and debugging purposes.
    """

    __tablename__ = "audit_logs"

    # Action details
    action: Mapped[AuditAction] = mapped_column(
        SQLEnum(AuditAction),
        nullable=False,
        index=True,
        comment="Type of action performed",
    )

    result: Mapped[AuditResult] = mapped_column(
        SQLEnum(AuditResult), nullable=False, index=True, comment="Result of the action"
    )

    severity: Mapped[AuditSeverity] = mapped_column(
        SQLEnum(AuditSeverity),
        nullable=False,
        default=AuditSeverity.LOW,
        index=True,
        comment="Severity level of the event",
    )

    # Resource identification
    resource_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Type of resource affected (account, order, etc.)",
    )

    resource_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Identifier of the affected resource",
    )

    # User/system identification
    user_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="User who performed the action"
    )

    user_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Type of user (human, system, api)"
    )

    session_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True, comment="Session identifier"
    )

    # Network information
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET, nullable=True, index=True, comment="IP address of the request"
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="User agent string"
    )

    # Request details
    request_method: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, comment="HTTP method or operation type"
    )

    request_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Request path or operation name"
    )

    request_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True, comment="Unique request identifier"
    )

    # Related entities
    tiger_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tiger_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Related Tiger account",
    )

    api_key_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="API key used for the action",
    )

    # Event data
    details: Mapped[Dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Detailed information about the event",
    )

    # Before/after states for changes
    old_values: Mapped[Optional[Dict]] = mapped_column(
        JSONB, nullable=True, comment="Values before the change (for updates/deletes)"
    )

    new_values: Mapped[Optional[Dict]] = mapped_column(
        JSONB, nullable=True, comment="Values after the change (for creates/updates)"
    )

    # Error information
    error_code: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="Error code if action failed"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Error message if action failed"
    )

    # Performance metrics
    duration_ms: Mapped[Optional[int]] = mapped_column(
        nullable=True, comment="Duration of the operation in milliseconds"
    )

    # Tags and categorization
    tags: Mapped[Dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Flexible tags for categorization and filtering",
    )

    # Relationships
    tiger_account: Mapped[Optional["TigerAccount"]] = relationship(
        "TigerAccount", back_populates="audit_logs", lazy="selectin"
    )

    api_key: Mapped[Optional["APIKey"]] = relationship(
        "APIKey", back_populates="audit_logs", lazy="selectin"
    )

    # Table constraints
    __table_args__ = (
        # Check constraints
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_audit_logs_duration_positive",
        ),
        # Composite indexes for common queries
        Index("ix_audit_logs_action_result", "action", "result"),
        Index("ix_audit_logs_severity_created", "severity", "created_at"),
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_account_action", "tiger_account_id", "action"),
        Index("ix_audit_logs_ip_created", "ip_address", "created_at"),
        Index("ix_audit_logs_session_created", "session_id", "created_at"),
        # Partial indexes for errors
        Index(
            "ix_audit_logs_errors",
            "result",
            "severity",
            "created_at",
            postgresql_where="result IN ('failure', 'error')",
        ),
        # Time-based partitioning support
        Index("ix_audit_logs_created_at_action", "created_at", "action"),
    )

    def __str__(self) -> str:
        """String representation."""
        return (
            f"AuditLog({self.action.value}:{self.result.value}:"
            f"{self.user_id or 'system'})"
        )

    @property
    def is_success(self) -> bool:
        """Check if action was successful."""
        return self.result == AuditResult.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Check if action failed."""
        return self.result in [AuditResult.FAILURE, AuditResult.ERROR]

    @property
    def is_critical(self) -> bool:
        """Check if event is critical severity."""
        return self.severity == AuditSeverity.CRITICAL

    @property
    def is_security_event(self) -> bool:
        """Check if this is a security-related event."""
        security_actions = [
            AuditAction.SECURITY_AUTH_FAIL,
            AuditAction.SECURITY_ACCESS_DENIED,
            AuditAction.SECURITY_BREACH_DETECTED,
            AuditAction.API_KEY_CREATE,
            AuditAction.API_KEY_REVOKE,
            AuditAction.ACCOUNT_LOGIN,
            AuditAction.ACCOUNT_LOGOUT,
        ]
        return self.action in security_actions

    @property
    def is_trading_event(self) -> bool:
        """Check if this is a trading-related event."""
        return self.action.value.startswith("trade_")

    def add_tag(self, key: str, value: Any) -> None:
        """Add a tag to the audit log."""
        self.tags[key] = value

    def get_tag(self, key: str, default: Any = None) -> Any:
        """Get a tag value from the audit log."""
        return self.tags.get(key, default)

    def has_tag(self, key: str) -> bool:
        """Check if audit log has a specific tag."""
        return key in self.tags

    def set_error(self, error_code: str, error_message: str) -> None:
        """Set error information for the audit log."""
        self.result = AuditResult.ERROR
        self.error_code = error_code
        self.error_message = error_message

    def set_duration(self, start_time: float, end_time: float) -> None:
        """Set the duration of the operation."""
        self.duration_ms = int((end_time - start_time) * 1000)

    @classmethod
    def create_login_event(
        cls,
        user_id: str,
        ip_address: Optional[str] = None,
        success: bool = True,
        tiger_account_id: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> "AuditLog":
        """Create a login audit event."""
        return cls(
            action=AuditAction.ACCOUNT_LOGIN,
            result=AuditResult.SUCCESS if success else AuditResult.FAILURE,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            user_type="human",
            ip_address=ip_address,
            tiger_account_id=tiger_account_id,
            resource_type="account",
            resource_id=str(tiger_account_id) if tiger_account_id else None,
            **kwargs,
        )

    @classmethod
    def create_trade_event(
        cls,
        action: AuditAction,
        tiger_account_id: uuid.UUID,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        **kwargs,
    ) -> "AuditLog":
        """Create a trading audit event."""
        details = kwargs.pop("details", {})
        if symbol:
            details["symbol"] = symbol
        if quantity:
            details["quantity"] = quantity
        if price:
            details["price"] = price

        return cls(
            action=action,
            result=kwargs.pop("result", AuditResult.SUCCESS),
            severity=kwargs.pop("severity", AuditSeverity.MEDIUM),
            tiger_account_id=tiger_account_id,
            resource_type="order",
            resource_id=order_id,
            details=details,
            **kwargs,
        )

    @classmethod
    def create_api_event(
        cls,
        action: AuditAction,
        api_key_id: Optional[uuid.UUID] = None,
        request_path: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs,
    ) -> "AuditLog":
        """Create an API usage audit event."""
        return cls(
            action=action,
            result=kwargs.pop("result", AuditResult.SUCCESS),
            severity=kwargs.pop("severity", AuditSeverity.LOW),
            api_key_id=api_key_id,
            user_type="api",
            request_path=request_path,
            ip_address=ip_address,
            resource_type="api_key",
            resource_id=str(api_key_id) if api_key_id else None,
            **kwargs,
        )
