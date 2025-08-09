"""
Database package for Tiger MCP system.

This package provides:
- SQLAlchemy models for all database entities
- Alembic migrations for schema management
- Database configuration and engine setup
- Utility functions for common operations
"""

# Core components
from .base import Base, BaseModel, TimestampMixin, UUIDMixin
from .config import DatabaseConfig, db_config
from .engine import (
    check_database_connection,
    close_engine,
    create_engine,
    get_engine,
    get_session,
    get_session_factory,
    get_transaction,
)

# Models
from .models import APIKey, AuditLog, TigerAccount, TokenStatus

# Model enums
from .models.accounts import AccountStatus, AccountType, MarketPermission
from .models.api_keys import APIKeyScope, APIKeyStatus
from .models.audit_logs import AuditAction, AuditResult, AuditSeverity
from .models.token_status import RefreshTrigger, TokenRefreshStatus

# Utilities
from .utils import (
    APIKeyUtils,
    AuditLogUtils,
    DatabaseUtils,
    TigerAccountUtils,
    TokenStatusUtils,
    create_utils,
)

__all__ = [
    # Core components
    "Base",
    "BaseModel",
    "UUIDMixin",
    "TimestampMixin",
    "DatabaseConfig",
    "db_config",
    "create_engine",
    "get_engine",
    "get_session_factory",
    "get_session",
    "get_transaction",
    "close_engine",
    "check_database_connection",
    # Models
    "TigerAccount",
    "APIKey",
    "AuditLog",
    "TokenStatus",
    # Model enums
    "AccountType",
    "AccountStatus",
    "MarketPermission",
    "APIKeyScope",
    "APIKeyStatus",
    "AuditAction",
    "AuditResult",
    "AuditSeverity",
    "TokenRefreshStatus",
    "RefreshTrigger",
    # Utilities
    "DatabaseUtils",
    "TigerAccountUtils",
    "APIKeyUtils",
    "AuditLogUtils",
    "TokenStatusUtils",
    "create_utils",
]

# Package metadata
__version__ = "0.1.0"
__description__ = "Database models and migrations for Tiger MCP system"
