#!/usr/bin/env python3
"""
Database management script for Tiger MCP system.

This script provides utilities for database operations including:
- Running migrations
- Creating/dropping database
- Seeding test data
- Database health checks
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from alembic import command
from alembic.config import Config
from sqlalchemy import text
# from sqlalchemy.ext.asyncio import create_async_engine  # Unused

# Add src directory to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from database.base import Base
from database.config import db_config
from database.engine import check_database_connection, close_engine, get_engine
from database.models import TigerAccount  # APIKey, AuditLog, TokenStatus unused in main script
from database.utils import create_utils

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_config.sync_database_url)
    return alembic_cfg


@click.group()
def cli():
    """Tiger MCP Database Management CLI."""


@cli.command()
def init():
    """Initialize database with initial migration."""
    try:
        logger.info("Initializing database...")
        alembic_cfg = get_alembic_config()

        # Create initial migration if needed
        logger.info("Checking for existing migrations...")
        try:
            command.current(alembic_cfg)
        except Exception:
            logger.info("No existing migrations found, creating initial migration...")
            # The migration already exists, so just stamp it
            command.stamp(alembic_cfg, "head")

        logger.info("Database initialization completed successfully!")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


@cli.command()
def migrate():
    """Run pending migrations."""
    try:
        logger.info("Running database migrations...")
        alembic_cfg = get_alembic_config()
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--message", "-m", required=True, help="Migration message")
def revision(message: str):
    """Create a new migration revision."""
    try:
        logger.info(f"Creating new migration: {message}")
        alembic_cfg = get_alembic_config()
        command.revision(alembic_cfg, message=message, autogenerate=True)
        logger.info("Migration revision created successfully!")

    except Exception as e:
        logger.error(f"Creating revision failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--steps", "-n", default=1, help="Number of steps to rollback")
def rollback(steps: int):
    """Rollback database migrations."""
    try:
        logger.info(f"Rolling back {steps} migration(s)...")
        alembic_cfg = get_alembic_config()
        command.downgrade(alembic_cfg, f"-{steps}")
        logger.info("Rollback completed successfully!")

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        sys.exit(1)


@cli.command()
@click.confirmation_option(prompt="Are you sure you want to drop all database tables?")
async def drop_all():
    """Drop all database tables."""
    try:
        logger.info("Dropping all database tables...")
        engine = get_engine()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        await close_engine()
        logger.info("All tables dropped successfully!")

    except Exception as e:
        logger.error(f"Dropping tables failed: {e}")
        sys.exit(1)


@cli.command()
async def create_tables():
    """Create all database tables."""
    try:
        logger.info("Creating database tables...")
        engine = get_engine()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        await close_engine()
        logger.info("Tables created successfully!")

    except Exception as e:
        logger.error(f"Creating tables failed: {e}")
        sys.exit(1)


@cli.command()
async def health_check():
    """Check database connection health."""
    try:
        logger.info("Checking database connection...")

        if await check_database_connection():
            logger.info("✅ Database connection is healthy!")

            # Additional checks
            engine = get_engine()
            async with engine.begin() as conn:
                # Check if tables exist
                result = await conn.execute(
                    text(
                        """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_name IN ('tiger_accounts', 'api_keys', 'audit_logs', 'token_statuses')
                """
                    )
                )
                tables = [row[0] for row in result]

                logger.info(f"Found {len(tables)} core tables: {', '.join(tables)}")

                # Check record counts
                for table in tables:
                    count_result = await conn.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    )
                    count = count_result.scalar()
                    logger.info(f"  {table}: {count} records")

            await close_engine()

        else:
            logger.error("❌ Database connection failed!")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--account-name", required=True, help="Account name")
@click.option("--account-number", required=True, help="Tiger account number")
@click.option("--tiger-id", required=True, help="Tiger ID")
@click.option("--private-key", required=True, help="Private key (will be encrypted)")
@click.option(
    "--environment", default="sandbox", help="Environment (sandbox/production)"
)
async def create_account(
    account_name: str,
    account_number: str,
    tiger_id: str,
    private_key: str,
    environment: str,
):
    """Create a new Tiger account (for testing)."""
    try:
        logger.info(f"Creating Tiger account: {account_name}")

        from database.engine import get_session
        from database.models.accounts import AccountStatus, AccountType

        async with get_session() as session:
            utils = create_utils(session)

            # TODO: In production, encrypt the credentials
            account = await utils["accounts"].create(
                TigerAccount,
                account_name=account_name,
                account_number=account_number,
                tiger_id=tiger_id,  # Should be encrypted
                private_key=private_key,  # Should be encrypted
                account_type=AccountType.STANDARD,
                status=AccountStatus.ACTIVE,
                environment=environment,
                market_permissions={"permissions": ["us_stock", "hk_stock"]},
                is_default_trading=False,
                is_default_data=False,
            )

            logger.info(f"✅ Created account: {account.account_name} ({account.id})")

    except Exception as e:
        logger.error(f"Creating account failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--name", required=True, help="API key name")
@click.option("--scopes", required=True, help="Comma-separated scopes")
@click.option("--account-id", help="Tiger account ID to bind to")
async def create_api_key(name: str, scopes: str, account_id: Optional[str]):
    """Create a new API key (for testing)."""
    try:
        logger.info(f"Creating API key: {name}")

        import uuid

        from database.engine import get_session
        from database.models.api_keys import APIKeyScope

        # Parse scopes
        scope_list = []
        for scope_str in scopes.split(","):
            scope_str = scope_str.strip()
            try:
                scope_list.append(APIKeyScope(scope_str))
            except ValueError:
                logger.error(f"Invalid scope: {scope_str}")
                sys.exit(1)

        async with get_session() as session:
            utils = create_utils(session)

            tiger_account_id = None
            if account_id:
                try:
                    tiger_account_id = uuid.UUID(account_id)
                except ValueError:
                    logger.error(f"Invalid account ID: {account_id}")
                    sys.exit(1)

            api_key, raw_key = await utils["api_keys"].create_api_key(
                name=name, scopes=scope_list, tiger_account_id=tiger_account_id
            )

            logger.info(f"✅ Created API key: {api_key.name} ({api_key.id})")
            logger.info(f"🔑 API Key: {raw_key}")
            logger.info("⚠️  Save this key securely - it won't be shown again!")

    except Exception as e:
        logger.error(f"Creating API key failed: {e}")
        sys.exit(1)


@cli.command()
async def list_accounts():
    """List all Tiger accounts."""
    try:
        from database.engine import get_session

        async with get_session() as session:
            utils = create_utils(session)

            accounts = await utils["accounts"].get_active_accounts()

            if not accounts:
                logger.info("No accounts found.")
                return

            logger.info(f"Found {len(accounts)} accounts:")
            for account in accounts:
                logger.info(f"  • {account.account_name} ({account.account_number})")
                logger.info(f"    ID: {account.id}")
                logger.info(f"    Type: {account.account_type.value}")
                logger.info(f"    Environment: {account.environment}")
                logger.info(f"    Default Trading: {account.is_default_trading}")
                logger.info(f"    Default Data: {account.is_default_data}")
                logger.info(f"    API Keys: {len(account.api_keys)}")
                logger.info("")

    except Exception as e:
        logger.error(f"Listing accounts failed: {e}")
        sys.exit(1)


@cli.command()
async def list_api_keys():
    """List all API keys."""
    try:
        from database.engine import get_session

        async with get_session() as session:
            utils = create_utils(session)

            keys = await utils["api_keys"].get_active_keys()

            if not keys:
                logger.info("No API keys found.")
                return

            logger.info(f"Found {len(keys)} API keys:")
            for key in keys:
                logger.info(f"  • {key.name} ({key.key_prefix}...)")
                logger.info(f"    ID: {key.id}")
                logger.info(f"    Status: {key.status.value}")
                logger.info(f"    Scopes: {', '.join(key.scopes)}")
                logger.info(
                    f"    Account: {key.tiger_account.account_name if key.tiger_account else 'None'}"
                )
                logger.info(f"    Usage Count: {key.usage_count}")
                logger.info(f"    Last Used: {key.last_used_at or 'Never'}")
                logger.info("")

    except Exception as e:
        logger.error(f"Listing API keys failed: {e}")
        sys.exit(1)


def run_async_command(func):
    """Decorator to run async commands."""
    return lambda *args, **kwargs: asyncio.run(func(*args, **kwargs))


# Apply async decorator to commands that need it
for cmd_name in [
    "drop_all",
    "create_tables",
    "health_check",
    "create_account",
    "create_api_key",
    "list_accounts",
    "list_api_keys",
]:
    if hasattr(cli.commands[cmd_name], "callback"):
        cli.commands[cmd_name].callback = run_async_command(
            cli.commands[cmd_name].callback
        )


if __name__ == "__main__":
    cli()
