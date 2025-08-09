"""
TigerAccount model for storing Tiger Broker account information.
"""

# import uuid  # Unused - UUIDs handled by UUIDMixin
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel


class AccountType(str, Enum):
    """Tiger account types."""

    STANDARD = "standard"
    PAPER = "paper"  # Paper trading account
    PRIME = "prime"  # Prime account


class AccountStatus(str, Enum):
    """Account status options."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class MarketPermission(str, Enum):
    """Market access permissions."""

    US_STOCK = "us_stock"
    HK_STOCK = "hk_stock"
    CN_STOCK = "cn_stock"
    US_OPTION = "us_option"
    HK_OPTION = "hk_option"
    FUTURES = "futures"
    FOREX = "forex"


class TigerLicense(str, Enum):
    """Tiger broker license types."""
    
    TBHK = "TBHK"  # Tiger Brokers Hong Kong
    TBSG = "TBSG"  # Tiger Brokers Singapore
    TBNZ = "TBNZ"  # Tiger Brokers New Zealand
    TBAU = "TBAU"  # Tiger Brokers Australia
    TBUK = "TBUK"  # Tiger Brokers UK


class TigerEnvironment(str, Enum):
    """Tiger API environment types."""
    
    PROD = "PROD"      # Production environment
    SANDBOX = "SANDBOX"  # Sandbox/testing environment


class TigerAccount(BaseModel):
    """
    Tiger Broker account information with encrypted credentials.

    This model stores account configuration, credentials, and permissions
    for Tiger Broker API access. Sensitive data is encrypted at rest.
    
    Tiger Authentication requires:
    - tiger_id: Developer application ID
    - account: Account number (can be paper or real trading account)
    - license: Broker license (TBHK, TBSG, TBNZ, etc.)
    - private_key: RSA private key (supports both PK1 and PK8 formats)
    - environment: PROD or SANDBOX
    """

    __tablename__ = "tiger_accounts"

    # Basic account information
    account_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="User-friendly account name"
    )

    account_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Tiger account number",
    )

    account_type: Mapped[AccountType] = mapped_column(
        SQLEnum(AccountType),
        nullable=False,
        default=AccountType.STANDARD,
        index=True,
        comment="Type of Tiger account",
    )

    status: Mapped[AccountStatus] = mapped_column(
        SQLEnum(AccountStatus),
        nullable=False,
        default=AccountStatus.ACTIVE,
        index=True,
        comment="Current account status",
    )

    # Tiger-specific authentication fields
    tiger_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Encrypted Tiger developer ID"
    )

    license: Mapped[TigerLicense] = mapped_column(
        SQLEnum(TigerLicense),
        nullable=False,
        index=True,
        comment="Tiger broker license (TBHK, TBSG, TBNZ, etc.)",
    )

    private_key: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Encrypted RSA private key (PK1 or PK8 format)"
    )
    
    private_key_format: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="PK1",
        comment="Private key format: PK1 or PK8",
    )

    # Authentication tokens (encrypted)
    access_token: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Encrypted current access token"
    )

    refresh_token: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Encrypted refresh token"
    )

    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="When the access token expires"
    )

    # Account configuration
    is_default_trading: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        comment="Default account for trading operations",
    )

    is_default_data: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        comment="Default account for data fetching operations",
    )

    # Market permissions
    market_permissions: Mapped[Dict] = mapped_column(
        JSONB, nullable=False, default=dict, comment="Market access permissions as JSON"
    )

    # Connection settings
    environment: Mapped[TigerEnvironment] = mapped_column(
        SQLEnum(TigerEnvironment),
        nullable=False,
        default=TigerEnvironment.SANDBOX,
        index=True,
        comment="Tiger API environment (PROD/SANDBOX)",
    )

    server_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Custom server URL if different from default",
    )

    # Rate limiting and usage
    daily_api_calls: Mapped[int] = mapped_column(
        default=0, comment="Number of API calls made today"
    )

    rate_limit_reset: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="When the rate limit counter resets"
    )

    # Account metadata
    description: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Optional account description"
    )

    tags: Mapped[Dict] = mapped_column(
        JSONB, nullable=False, default=dict, comment="Flexible tags for categorization"
    )

    # Error tracking
    last_error: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Last API error encountered"
    )

    last_error_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="When the last error occurred"
    )

    error_count: Mapped[int] = mapped_column(
        default=0, comment="Number of consecutive errors"
    )

    # Relationships
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="tiger_account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    token_statuses: Mapped[list["TokenStatus"]] = relationship(
        "TokenStatus",
        back_populates="tiger_account",
        cascade="all, delete-orphan",
        order_by="desc(TokenStatus.created_at)",
        lazy="selectin",
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="tiger_account",
        cascade="all, delete-orphan",
        order_by="desc(AuditLog.created_at)",
    )

    # Table constraints
    __table_args__ = (
        # Ensure only one default trading account
        Index(
            "ix_tiger_accounts_default_trading_unique",
            "is_default_trading",
            unique=True,
            postgresql_where="is_default_trading = true",
        ),
        # Ensure only one default data account
        Index(
            "ix_tiger_accounts_default_data_unique",
            "is_default_data",
            unique=True,
            postgresql_where="is_default_data = true",
        ),
        # Check constraints
        CheckConstraint(
            "private_key_format IN ('PK1', 'PK8')",
            name="ck_tiger_accounts_private_key_format",
        ),
        CheckConstraint(
            "daily_api_calls >= 0", name="ck_tiger_accounts_api_calls_positive"
        ),
        CheckConstraint(
            "error_count >= 0", name="ck_tiger_accounts_error_count_positive"
        ),
        # Composite indexes
        Index("ix_tiger_accounts_type_status", "account_type", "status"),
        Index("ix_tiger_accounts_environment_status", "environment", "status"),
        Index("ix_tiger_accounts_license_env", "license", "environment"),
        Index("ix_tiger_accounts_tiger_id", "tiger_id"),
    )

    def __str__(self) -> str:
        """String representation."""
        return f"TigerAccount({self.account_name}:{self.account_number}@{self.license.value})"

    @property
    def is_active(self) -> bool:
        """Check if account is active."""
        return self.status == AccountStatus.ACTIVE

    @property
    def is_production(self) -> bool:
        """Check if account is configured for production."""
        return self.environment == TigerEnvironment.PROD
    
    @property
    def is_sandbox(self) -> bool:
        """Check if account is configured for sandbox."""
        return self.environment == TigerEnvironment.SANDBOX
        
    @property
    def is_paper_account(self) -> bool:
        """Check if this is a paper trading account based on account number."""
        # Tiger paper accounts typically start with specific prefixes
        # This is a heuristic and may need adjustment based on actual patterns
        return str(self.account_number).startswith(('P', '9'))

    @property
    def has_valid_token(self) -> bool:
        """Check if account has a valid access token."""
        if not self.access_token or not self.token_expires_at:
            return False
        return self.token_expires_at > datetime.utcnow()

    @property
    def needs_token_refresh(self) -> bool:
        """Check if token needs to be refreshed soon (within 1 hour)."""
        if not self.token_expires_at:
            return True
        # Refresh if expires within 1 hour
        return (self.token_expires_at - datetime.utcnow()).total_seconds() < 3600

    def has_market_permission(self, permission: MarketPermission) -> bool:
        """Check if account has specific market permission."""
        return permission.value in self.market_permissions.get("permissions", [])

    def add_market_permission(self, permission: MarketPermission) -> None:
        """Add market permission to account."""
        if "permissions" not in self.market_permissions:
            self.market_permissions["permissions"] = []
        if permission.value not in self.market_permissions["permissions"]:
            self.market_permissions["permissions"].append(permission.value)

    def remove_market_permission(self, permission: MarketPermission) -> None:
        """Remove market permission from account."""
        if "permissions" in self.market_permissions:
            self.market_permissions["permissions"] = [
                p
                for p in self.market_permissions["permissions"]
                if p != permission.value
            ]

    def increment_error_count(self, error_message: str) -> None:
        """Increment error count and update error details."""
        self.error_count += 1
        self.last_error = error_message
        self.last_error_at = datetime.utcnow()

    def reset_error_count(self) -> None:
        """Reset error tracking after successful operation."""
        self.error_count = 0
        self.last_error = None
        self.last_error_at = None

    def to_dict_safe(self) -> Dict:
        """Convert to dictionary without sensitive data."""
        data = self.to_dict()
        # Remove sensitive fields
        for field in ["tiger_id", "private_key", "access_token", "refresh_token"]:
            data.pop(field, None)
        # Convert enums to string values for JSON serialization
        if "license" in data:
            data["license"] = data["license"].value if hasattr(data["license"], 'value') else str(data["license"])
        if "environment" in data:
            data["environment"] = data["environment"].value if hasattr(data["environment"], 'value') else str(data["environment"])
        return data
        
    def get_tiger_config_dict(self) -> Dict[str, str]:
        """Get Tiger configuration as dictionary for .properties file format."""
        return {
            "tiger_id": str(self.tiger_id),  # Will be decrypted when used
            "account": str(self.account_number),
            "license": self.license.value,
            "env": self.environment.value,
            "private_key_pk1": self.private_key if self.private_key_format == "PK1" else "",
            "private_key_pk8": self.private_key if self.private_key_format == "PK8" else "",
        }
