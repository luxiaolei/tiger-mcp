"""Initial schema with all Tiger MCP tables

Revision ID: 001
Revises:
Create Date: 2025-01-08 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Create ENUM types
    accounttype_enum = postgresql.ENUM("standard", "paper", "prime", name="accounttype")
    accounttype_enum.create(op.get_bind())

    accountstatus_enum = postgresql.ENUM(
        "active", "inactive", "suspended", "pending_verification", name="accountstatus"
    )
    accountstatus_enum.create(op.get_bind())

    apikeyscope_enum = postgresql.ENUM(
        "mcp:read",
        "mcp:write",
        "mcp:admin",
        "dashboard:read",
        "dashboard:write",
        "dashboard:admin",
        "trade:read",
        "trade:write",
        "trade:admin",
        "account:read",
        "account:write",
        "account:admin",
        "system:read",
        "system:write",
        "system:admin",
        name="apikeyscope",
    )
    apikeyscope_enum.create(op.get_bind())

    apikeystatus_enum = postgresql.ENUM(
        "active", "inactive", "revoked", "expired", name="apikeystatus"
    )
    apikeystatus_enum.create(op.get_bind())

    auditaction_enum = postgresql.ENUM(
        "account_create",
        "account_update",
        "account_delete",
        "account_login",
        "account_logout",
        "account_token_refresh",
        "api_key_create",
        "api_key_update",
        "api_key_delete",
        "api_key_revoke",
        "api_key_use",
        "trade_place_order",
        "trade_cancel_order",
        "trade_modify_order",
        "trade_order_filled",
        "trade_position_update",
        "data_fetch_quotes",
        "data_fetch_historical",
        "data_fetch_positions",
        "data_fetch_orders",
        "data_fetch_account_info",
        "system_start",
        "system_stop",
        "system_config_update",
        "system_backup",
        "system_restore",
        "mcp_connect",
        "mcp_disconnect",
        "mcp_tool_call",
        "mcp_error",
        "dashboard_login",
        "dashboard_logout",
        "dashboard_view",
        "dashboard_config_update",
        "security_auth_fail",
        "security_access_denied",
        "security_breach_detected",
        "error_api_limit",
        "error_network",
        "error_auth",
        "error_system",
        name="auditaction",
    )
    auditaction_enum.create(op.get_bind())

    auditresult_enum = postgresql.ENUM(
        "success", "failure", "partial", "error", name="auditresult"
    )
    auditresult_enum.create(op.get_bind())

    auditseverity_enum = postgresql.ENUM(
        "low", "medium", "high", "critical", name="auditseverity"
    )
    auditseverity_enum.create(op.get_bind())

    tokenrefreshstatus_enum = postgresql.ENUM(
        "pending",
        "in_progress",
        "success",
        "failed",
        "expired",
        "cancelled",
        name="tokenrefreshstatus",
    )
    tokenrefreshstatus_enum.create(op.get_bind())

    refreshtrigger_enum = postgresql.ENUM(
        "scheduled",
        "manual",
        "on_demand",
        "expiry_soon",
        "expired",
        "error",
        name="refreshtrigger",
    )
    refreshtrigger_enum.create(op.get_bind())

    # Create tiger_accounts table
    op.create_table(
        "tiger_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column(
            "account_name",
            sa.String(length=100),
            nullable=False,
            comment="User-friendly account name",
        ),
        sa.Column(
            "account_number",
            sa.String(length=50),
            nullable=False,
            comment="Tiger account number",
        ),
        sa.Column(
            "account_type",
            accounttype_enum,
            nullable=False,
            default="standard",
            comment="Type of Tiger account",
        ),
        sa.Column(
            "status",
            accountstatus_enum,
            nullable=False,
            default="active",
            comment="Current account status",
        ),
        sa.Column(
            "tiger_id",
            sa.String(length=255),
            nullable=False,
            comment="Encrypted Tiger ID",
        ),
        sa.Column(
            "private_key",
            sa.Text(),
            nullable=False,
            comment="Encrypted private key for Tiger API",
        ),
        sa.Column(
            "access_token",
            sa.Text(),
            nullable=True,
            comment="Encrypted current access token",
        ),
        sa.Column(
            "refresh_token", sa.Text(), nullable=True, comment="Encrypted refresh token"
        ),
        sa.Column(
            "token_expires_at",
            sa.DateTime(),
            nullable=True,
            comment="When the access token expires",
        ),
        sa.Column(
            "is_default_trading",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="Default account for trading operations",
        ),
        sa.Column(
            "is_default_data",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="Default account for data fetching operations",
        ),
        sa.Column(
            "market_permissions",
            postgresql.JSONB(),
            nullable=False,
            default={},
            comment="Market access permissions as JSON",
        ),
        sa.Column(
            "environment",
            sa.String(length=20),
            nullable=False,
            default="sandbox",
            comment="API environment (sandbox/production)",
        ),
        sa.Column(
            "server_url",
            sa.String(length=255),
            nullable=True,
            comment="Custom server URL if different from default",
        ),
        sa.Column(
            "daily_api_calls",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Number of API calls made today",
        ),
        sa.Column(
            "rate_limit_reset",
            sa.DateTime(),
            nullable=True,
            comment="When the rate limit counter resets",
        ),
        sa.Column(
            "description",
            sa.String(length=500),
            nullable=True,
            comment="Optional account description",
        ),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=False,
            default={},
            comment="Flexible tags for categorization",
        ),
        sa.Column(
            "last_error", sa.Text(), nullable=True, comment="Last API error encountered"
        ),
        sa.Column(
            "last_error_at",
            sa.DateTime(),
            nullable=True,
            comment="When the last error occurred",
        ),
        sa.Column(
            "error_count",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Number of consecutive errors",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_number"),
        sa.CheckConstraint(
            "environment IN ('sandbox', 'production')",
            name="ck_tiger_accounts_environment",
        ),
        sa.CheckConstraint(
            "daily_api_calls >= 0", name="ck_tiger_accounts_api_calls_positive"
        ),
        sa.CheckConstraint(
            "error_count >= 0", name="ck_tiger_accounts_error_count_positive"
        ),
        comment="Tiger Broker account information with encrypted credentials",
    )

    # Create indexes for tiger_accounts
    op.create_index(
        "ix_tiger_accounts_account_name", "tiger_accounts", ["account_name"]
    )
    op.create_index(
        "ix_tiger_accounts_account_number", "tiger_accounts", ["account_number"]
    )
    op.create_index(
        "ix_tiger_accounts_account_type", "tiger_accounts", ["account_type"]
    )
    op.create_index("ix_tiger_accounts_status", "tiger_accounts", ["status"])
    op.create_index(
        "ix_tiger_accounts_is_default_trading", "tiger_accounts", ["is_default_trading"]
    )
    op.create_index(
        "ix_tiger_accounts_is_default_data", "tiger_accounts", ["is_default_data"]
    )
    op.create_index(
        "ix_tiger_accounts_type_status", "tiger_accounts", ["account_type", "status"]
    )
    op.create_index(
        "ix_tiger_accounts_environment_status",
        "tiger_accounts",
        ["environment", "status"],
    )

    # Create unique partial indexes for default accounts
    op.create_index(
        "ix_tiger_accounts_default_trading_unique",
        "tiger_accounts",
        ["is_default_trading"],
        unique=True,
        postgresql_where=sa.text("is_default_trading = true"),
    )
    op.create_index(
        "ix_tiger_accounts_default_data_unique",
        "tiger_accounts",
        ["is_default_data"],
        unique=True,
        postgresql_where=sa.text("is_default_data = true"),
    )

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
            comment="Human-readable key name",
        ),
        sa.Column(
            "key_hash",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 hash of the API key",
        ),
        sa.Column(
            "key_prefix",
            sa.String(length=8),
            nullable=False,
            comment="First 8 characters of key for identification",
        ),
        sa.Column(
            "status",
            apikeystatus_enum,
            nullable=False,
            default="active",
            comment="Current key status",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(),
            nullable=True,
            comment="When the key expires (null = no expiration)",
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(),
            nullable=True,
            comment="When the key was last used",
        ),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.String(length=50)),
            nullable=False,
            default=[],
            comment="List of access scopes for this key",
        ),
        sa.Column(
            "tiger_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Tiger account this key is bound to (if any)",
        ),
        sa.Column(
            "usage_count",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Number of times this key has been used",
        ),
        sa.Column(
            "rate_limit_per_hour",
            sa.Integer(),
            nullable=True,
            comment="Rate limit per hour (null = no limit)",
        ),
        sa.Column(
            "rate_limit_per_day",
            sa.Integer(),
            nullable=True,
            comment="Rate limit per day (null = no limit)",
        ),
        sa.Column(
            "allowed_ips",
            postgresql.ARRAY(sa.String(length=45)),
            nullable=False,
            default=[],
            comment="List of allowed IP addresses (empty = no restriction)",
        ),
        sa.Column(
            "allowed_user_agents",
            postgresql.ARRAY(sa.String(length=255)),
            nullable=False,
            default=[],
            comment="List of allowed user agents (empty = no restriction)",
        ),
        sa.Column(
            "description",
            sa.String(length=500),
            nullable=True,
            comment="Optional key description",
        ),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=False,
            default={},
            comment="Flexible tags for categorization",
        ),
        sa.Column(
            "created_by",
            sa.String(length=100),
            nullable=True,
            comment="Who created this API key",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tiger_account_id"], ["tiger_accounts.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("key_hash"),
        sa.CheckConstraint("usage_count >= 0", name="ck_api_keys_usage_count_positive"),
        sa.CheckConstraint(
            "rate_limit_per_hour IS NULL OR rate_limit_per_hour > 0",
            name="ck_api_keys_rate_limit_hour_positive",
        ),
        sa.CheckConstraint(
            "rate_limit_per_day IS NULL OR rate_limit_per_day > 0",
            name="ck_api_keys_rate_limit_day_positive",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at",
            name="ck_api_keys_expires_after_created",
        ),
        comment="API keys for authenticating MCP server and dashboard access",
    )

    # Create indexes for api_keys
    op.create_index("ix_api_keys_name", "api_keys", ["name"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_keys_status", "api_keys", ["status"])
    op.create_index("ix_api_keys_expires_at", "api_keys", ["expires_at"])
    op.create_index("ix_api_keys_last_used_at", "api_keys", ["last_used_at"])
    op.create_index("ix_api_keys_tiger_account_id", "api_keys", ["tiger_account_id"])
    op.create_index("ix_api_keys_created_by", "api_keys", ["created_by"])
    op.create_index("ix_api_keys_status_expires", "api_keys", ["status", "expires_at"])
    op.create_index(
        "ix_api_keys_account_status", "api_keys", ["tiger_account_id", "status"]
    )

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column(
            "action",
            auditaction_enum,
            nullable=False,
            comment="Type of action performed",
        ),
        sa.Column(
            "result", auditresult_enum, nullable=False, comment="Result of the action"
        ),
        sa.Column(
            "severity",
            auditseverity_enum,
            nullable=False,
            default="low",
            comment="Severity level of the event",
        ),
        sa.Column(
            "resource_type",
            sa.String(length=50),
            nullable=True,
            comment="Type of resource affected (account, order, etc.)",
        ),
        sa.Column(
            "resource_id",
            sa.String(length=255),
            nullable=True,
            comment="Identifier of the affected resource",
        ),
        sa.Column(
            "user_id",
            sa.String(length=100),
            nullable=True,
            comment="User who performed the action",
        ),
        sa.Column(
            "user_type",
            sa.String(length=50),
            nullable=True,
            comment="Type of user (human, system, api)",
        ),
        sa.Column(
            "session_id",
            sa.String(length=255),
            nullable=True,
            comment="Session identifier",
        ),
        sa.Column(
            "ip_address",
            postgresql.INET(),
            nullable=True,
            comment="IP address of the request",
        ),
        sa.Column(
            "user_agent",
            sa.String(length=500),
            nullable=True,
            comment="User agent string",
        ),
        sa.Column(
            "request_method",
            sa.String(length=10),
            nullable=True,
            comment="HTTP method or operation type",
        ),
        sa.Column(
            "request_path",
            sa.String(length=500),
            nullable=True,
            comment="Request path or operation name",
        ),
        sa.Column(
            "request_id",
            sa.String(length=255),
            nullable=True,
            comment="Unique request identifier",
        ),
        sa.Column(
            "tiger_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Related Tiger account",
        ),
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="API key used for the action",
        ),
        sa.Column(
            "details",
            postgresql.JSONB(),
            nullable=False,
            default={},
            comment="Detailed information about the event",
        ),
        sa.Column(
            "old_values",
            postgresql.JSONB(),
            nullable=True,
            comment="Values before the change (for updates/deletes)",
        ),
        sa.Column(
            "new_values",
            postgresql.JSONB(),
            nullable=True,
            comment="Values after the change (for creates/updates)",
        ),
        sa.Column(
            "error_code",
            sa.String(length=100),
            nullable=True,
            comment="Error code if action failed",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error message if action failed",
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=True,
            comment="Duration of the operation in milliseconds",
        ),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=False,
            default={},
            comment="Flexible tags for categorization and filtering",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tiger_account_id"], ["tiger_accounts.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_audit_logs_duration_positive",
        ),
        comment="Comprehensive audit trail for all system operations",
    )

    # Create indexes for audit_logs
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_result", "audit_logs", ["result"])
    op.create_index("ix_audit_logs_severity", "audit_logs", ["severity"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_session_id", "audit_logs", ["session_id"])
    op.create_index("ix_audit_logs_ip_address", "audit_logs", ["ip_address"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index(
        "ix_audit_logs_tiger_account_id", "audit_logs", ["tiger_account_id"]
    )
    op.create_index("ix_audit_logs_api_key_id", "audit_logs", ["api_key_id"])
    op.create_index("ix_audit_logs_error_code", "audit_logs", ["error_code"])
    op.create_index("ix_audit_logs_action_result", "audit_logs", ["action", "result"])
    op.create_index(
        "ix_audit_logs_severity_created", "audit_logs", ["severity", "created_at"]
    )
    op.create_index("ix_audit_logs_user_action", "audit_logs", ["user_id", "action"])
    op.create_index(
        "ix_audit_logs_account_action", "audit_logs", ["tiger_account_id", "action"]
    )
    op.create_index(
        "ix_audit_logs_ip_created", "audit_logs", ["ip_address", "created_at"]
    )
    op.create_index(
        "ix_audit_logs_session_created", "audit_logs", ["session_id", "created_at"]
    )
    op.create_index(
        "ix_audit_logs_created_at_action", "audit_logs", ["created_at", "action"]
    )

    # Create partial index for errors
    op.create_index(
        "ix_audit_logs_errors",
        "audit_logs",
        ["result", "severity", "created_at"],
        postgresql_where=sa.text("result IN ('failure', 'error')"),
    )

    # Create token_statuses table
    op.create_table(
        "token_statuses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column(
            "tiger_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tiger account this token status belongs to",
        ),
        sa.Column(
            "status",
            tokenrefreshstatus_enum,
            nullable=False,
            default="pending",
            comment="Current status of the token refresh",
        ),
        sa.Column(
            "trigger",
            refreshtrigger_enum,
            nullable=False,
            comment="What triggered this refresh operation",
        ),
        sa.Column(
            "old_token_expires_at",
            sa.DateTime(),
            nullable=True,
            comment="When the old token was set to expire",
        ),
        sa.Column(
            "old_token_hash",
            sa.String(length=64),
            nullable=True,
            comment="SHA-256 hash of the old access token",
        ),
        sa.Column(
            "new_token_expires_at",
            sa.DateTime(),
            nullable=True,
            comment="When the new token expires",
        ),
        sa.Column(
            "new_token_hash",
            sa.String(length=64),
            nullable=True,
            comment="SHA-256 hash of the new access token",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=True,
            comment="When the refresh operation started",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(),
            nullable=True,
            comment="When the refresh operation completed",
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=True,
            comment="Duration of the refresh operation in milliseconds",
        ),
        sa.Column(
            "next_refresh_at",
            sa.DateTime(),
            nullable=True,
            comment="When the next refresh is scheduled",
        ),
        sa.Column(
            "error_code",
            sa.String(length=100),
            nullable=True,
            comment="Error code if refresh failed",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Detailed error message if refresh failed",
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Number of retry attempts made",
        ),
        sa.Column(
            "max_retries",
            sa.Integer(),
            nullable=False,
            default=3,
            comment="Maximum number of retries allowed",
        ),
        sa.Column(
            "api_response_code",
            sa.Integer(),
            nullable=True,
            comment="HTTP response code from Tiger API",
        ),
        sa.Column(
            "api_response_time_ms",
            sa.Integer(),
            nullable=True,
            comment="API response time in milliseconds",
        ),
        sa.Column(
            "details",
            postgresql.JSONB(),
            nullable=False,
            default={},
            comment="Additional details about the refresh operation",
        ),
        sa.Column(
            "environment",
            sa.String(length=20),
            nullable=True,
            comment="Environment where refresh occurred (sandbox/production)",
        ),
        sa.Column(
            "server_version",
            sa.String(length=50),
            nullable=True,
            comment="Version of the MCP server performing the refresh",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tiger_account_id"], ["tiger_accounts.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "retry_count >= 0", name="ck_token_status_retry_count_positive"
        ),
        sa.CheckConstraint(
            "max_retries >= 0", name="ck_token_status_max_retries_positive"
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_token_status_duration_positive",
        ),
        sa.CheckConstraint(
            "api_response_time_ms IS NULL OR api_response_time_ms >= 0",
            name="ck_token_status_api_time_positive",
        ),
        sa.CheckConstraint(
            "started_at IS NULL OR completed_at IS NULL OR completed_at >= started_at",
            name="ck_token_status_completed_after_started",
        ),
        comment="Track Tiger API token refresh operations and status",
    )

    # Create indexes for token_statuses
    op.create_index(
        "ix_token_statuses_tiger_account_id", "token_statuses", ["tiger_account_id"]
    )
    op.create_index("ix_token_statuses_status", "token_statuses", ["status"])
    op.create_index("ix_token_statuses_trigger", "token_statuses", ["trigger"])
    op.create_index("ix_token_statuses_started_at", "token_statuses", ["started_at"])
    op.create_index(
        "ix_token_statuses_completed_at", "token_statuses", ["completed_at"]
    )
    op.create_index(
        "ix_token_statuses_next_refresh_at", "token_statuses", ["next_refresh_at"]
    )
    op.create_index("ix_token_statuses_error_code", "token_statuses", ["error_code"])
    op.create_index(
        "ix_token_status_account_status",
        "token_statuses",
        ["tiger_account_id", "status"],
    )
    op.create_index(
        "ix_token_status_trigger_created", "token_statuses", ["trigger", "created_at"]
    )
    op.create_index(
        "ix_token_status_account_next_refresh",
        "token_statuses",
        ["tiger_account_id", "next_refresh_at"],
    )
    op.create_index(
        "ix_token_status_completed_operations",
        "token_statuses",
        ["tiger_account_id", "status", "completed_at"],
    )

    # Create partial index for failures
    op.create_index(
        "ix_token_status_failures",
        "token_statuses",
        ["tiger_account_id", "status", "created_at"],
        postgresql_where=sa.text("status = 'failed'"),
    )


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop tables in reverse order (to handle foreign key constraints)
    op.drop_table("token_statuses")
    op.drop_table("audit_logs")
    op.drop_table("api_keys")
    op.drop_table("tiger_accounts")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS refreshtrigger")
    op.execute("DROP TYPE IF EXISTS tokenrefreshstatus")
    op.execute("DROP TYPE IF EXISTS auditseverity")
    op.execute("DROP TYPE IF EXISTS auditresult")
    op.execute("DROP TYPE IF EXISTS auditaction")
    op.execute("DROP TYPE IF EXISTS apikeystatus")
    op.execute("DROP TYPE IF EXISTS apikeyscope")
    op.execute("DROP TYPE IF EXISTS accountstatus")
    op.execute("DROP TYPE IF EXISTS accounttype")
