"""
Tests for Alembic migration operations.

This module tests:
- Alembic migration operations
- Schema creation and upgrades
- Data migration scenarios
- Rollback operations
- Use temporary database for migration testing
"""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError


class TestAlembicConfiguration:
    """Test Alembic configuration and setup."""

    def test_alembic_config_exists(self):
        """Test that alembic.ini configuration file exists."""
        # Get path to alembic.ini
        db_package_path = Path(__file__).parent.parent.parent
        alembic_ini_path = db_package_path / "alembic.ini"

        assert alembic_ini_path.exists(), "alembic.ini configuration file not found"

    def test_alembic_config_valid(self):
        """Test that alembic configuration is valid."""
        db_package_path = Path(__file__).parent.parent.parent
        alembic_ini_path = str(db_package_path / "alembic.ini")

        # Create Alembic config
        alembic_cfg = Config(alembic_ini_path)

        # Test that essential configuration is present
        assert alembic_cfg.get_main_option("script_location") is not None
        assert (
            alembic_cfg.get_main_option("sqlalchemy.url") is not None
            or alembic_cfg.get_main_option("url") is not None
        )

    def test_migrations_directory_exists(self):
        """Test that migrations directory and files exist."""
        db_package_path = Path(__file__).parent.parent / "src" / "database"
        migrations_path = db_package_path / "migrations"

        assert migrations_path.exists(), "Migrations directory not found"
        assert (migrations_path / "env.py").exists(), "env.py not found"
        assert (migrations_path / "script.py.mako").exists(), "script.py.mako not found"

        versions_path = migrations_path / "versions"
        assert versions_path.exists(), "Versions directory not found"


@pytest.fixture
def temp_sqlite_db() -> Generator[str, None, None]:
    """Create temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield f"sqlite:///{db_path}"

    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def alembic_config(temp_sqlite_db) -> Config:
    """Create Alembic configuration for testing."""
    db_package_path = Path(__file__).parent.parent.parent
    alembic_ini_path = str(db_package_path / "alembic.ini")

    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("sqlalchemy.url", temp_sqlite_db)

    return alembic_cfg


@pytest.fixture
def test_engine(temp_sqlite_db) -> Engine:
    """Create test SQLite engine."""
    return create_engine(temp_sqlite_db, echo=False)


class TestMigrationOperations:
    """Test basic migration operations."""

    def test_get_current_revision(self, alembic_config):
        """Test getting current revision."""
        # For a fresh database, current revision should be None
        try:
            ScriptDirectory.from_config(alembic_config)
            with create_engine(
                alembic_config.get_main_option("sqlalchemy.url")
            ).connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()
                # Should be None for fresh database
                assert current_rev is None
        except OperationalError:
            # Expected for fresh database without alembic_version table
            pass

    def test_get_migration_history(self, alembic_config):
        """Test getting migration history."""
        script = ScriptDirectory.from_config(alembic_config)

        # Get all revisions
        revisions = list(script.walk_revisions())

        # Should have at least the initial migration
        assert len(revisions) >= 1

        # Check that initial migration exists
        initial_rev = None
        for rev in revisions:
            if rev.down_revision is None:
                initial_rev = rev
                break

        assert initial_rev is not None, "Initial migration not found"
        assert initial_rev.revision == "001"

    def test_upgrade_to_head(self, alembic_config, test_engine):
        """Test upgrading to head revision."""
        # Run upgrade to head
        command.upgrade(alembic_config, "head")

        # Check that alembic_version table exists
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "alembic_version" in tables

        # Check current revision
        with test_engine.connect() as connection:
            result = connection.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar()
            assert current_version is not None

    def test_downgrade_to_base(self, alembic_config, test_engine):
        """Test downgrading to base."""
        # First upgrade to head
        command.upgrade(alembic_config, "head")

        # Then downgrade to base
        command.downgrade(alembic_config, "base")

        # Check that main tables are removed
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()

        main_tables = ["tiger_accounts", "api_keys", "audit_logs", "token_statuses"]
        for table in main_tables:
            assert (
                table not in tables
            ), f"Table {table} should be removed after downgrade"

    def test_revision_idempotent(self, alembic_config):
        """Test that migrations are idempotent."""
        # Upgrade to head twice - should not fail
        command.upgrade(alembic_config, "head")
        command.upgrade(alembic_config, "head")  # Second time should be idempotent

        # No exception should be raised


class TestSchemaValidation:
    """Test schema validation after migrations."""

    def test_schema_matches_models(self, alembic_config, test_engine):
        """Test that migrated schema matches SQLAlchemy models."""
        # Upgrade to head
        command.upgrade(alembic_config, "head")

        # Get database schema
        inspector = inspect(test_engine)

        # Test that all expected tables exist
        expected_tables = ["tiger_accounts", "api_keys", "audit_logs", "token_statuses"]
        actual_tables = inspector.get_table_names()

        for table in expected_tables:
            assert table in actual_tables, f"Table {table} missing from migrated schema"

    def test_tiger_accounts_table_structure(self, alembic_config, test_engine):
        """Test tiger_accounts table structure."""
        command.upgrade(alembic_config, "head")

        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("tiger_accounts")}

        # Test essential columns exist
        essential_columns = [
            "id",
            "created_at",
            "updated_at",
            "account_name",
            "account_number",
            "account_type",
            "status",
            "tiger_id",
            "private_key",
        ]

        for col_name in essential_columns:
            assert col_name in columns, f"Column {col_name} missing from tiger_accounts"

        # Test constraints
        inspector.get_check_constraints("tiger_accounts")
        pk_constraint = inspector.get_pk_constraint("tiger_accounts")
        unique_constraints = inspector.get_unique_constraints("tiger_accounts")

        assert pk_constraint["constrained_columns"] == ["id"]

        # Check for account_number unique constraint
        account_number_unique = any(
            "account_number" in constraint["column_names"]
            for constraint in unique_constraints
        )
        assert account_number_unique, "account_number unique constraint missing"

    def test_api_keys_table_structure(self, alembic_config, test_engine):
        """Test api_keys table structure."""
        command.upgrade(alembic_config, "head")

        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("api_keys")}

        # Test essential columns exist
        essential_columns = [
            "id",
            "created_at",
            "updated_at",
            "name",
            "key_hash",
            "key_prefix",
            "status",
            "scopes",
            "tiger_account_id",
        ]

        for col_name in essential_columns:
            assert col_name in columns, f"Column {col_name} missing from api_keys"

        # Test foreign key constraints
        fk_constraints = inspector.get_foreign_keys("api_keys")

        tiger_account_fk = any(
            fk["constrained_columns"] == ["tiger_account_id"]
            and fk["referred_table"] == "tiger_accounts"
            for fk in fk_constraints
        )
        assert tiger_account_fk, "Foreign key to tiger_accounts missing"

    def test_audit_logs_table_structure(self, alembic_config, test_engine):
        """Test audit_logs table structure."""
        command.upgrade(alembic_config, "head")

        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("audit_logs")}

        # Test essential columns exist
        essential_columns = [
            "id",
            "created_at",
            "updated_at",
            "action",
            "result",
            "severity",
            "tiger_account_id",
            "api_key_id",
            "details",
        ]

        for col_name in essential_columns:
            assert col_name in columns, f"Column {col_name} missing from audit_logs"

    def test_token_statuses_table_structure(self, alembic_config, test_engine):
        """Test token_statuses table structure."""
        command.upgrade(alembic_config, "head")

        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("token_statuses")}

        # Test essential columns exist
        essential_columns = [
            "id",
            "created_at",
            "updated_at",
            "tiger_account_id",
            "status",
            "trigger",
            "retry_count",
            "max_retries",
        ]

        for col_name in essential_columns:
            assert col_name in columns, f"Column {col_name} missing from token_statuses"


class TestIndexCreation:
    """Test that proper indexes are created."""

    def test_essential_indexes_created(self, alembic_config, test_engine):
        """Test that essential indexes are created."""
        command.upgrade(alembic_config, "head")

        inspector = inspect(test_engine)

        # Test tiger_accounts indexes
        tiger_accounts_indexes = inspector.get_indexes("tiger_accounts")
        index_names = [idx["name"] for idx in tiger_accounts_indexes]

        # Should have indexes on frequently queried columns
        essential_tiger_indexes = [
            "ix_tiger_accounts_account_number",
            "ix_tiger_accounts_status",
        ]

        for idx_name in essential_tiger_indexes:
            assert idx_name in index_names, f"Index {idx_name} missing"

        # Test api_keys indexes
        api_keys_indexes = inspector.get_indexes("api_keys")
        api_index_names = [idx["name"] for idx in api_keys_indexes]

        essential_api_indexes = [
            "ix_api_keys_key_hash",
            "ix_api_keys_status",
        ]

        for idx_name in essential_api_indexes:
            assert idx_name in api_index_names, f"Index {idx_name} missing"


class TestDataMigration:
    """Test data migration scenarios."""

    def test_preserve_data_during_migration(self, alembic_config, test_engine):
        """Test that data is preserved during migrations."""
        # Upgrade to head
        command.upgrade(alembic_config, "head")

        # Insert test data
        with test_engine.connect() as connection:
            # Insert test account
            connection.execute(
                text(
                    """
                INSERT INTO tiger_accounts (
                    id, created_at, updated_at, account_name, account_number,
                    account_type, status, tiger_id, private_key
                ) VALUES (
                    'a1a1a1a1-b2b2-c3c3-d4d4-e5e5e5e5e5e5',
                    '2023-01-01 00:00:00',
                    '2023-01-01 00:00:00',
                    'Test Account',
                    'TEST123456',
                    'standard',
                    'active',
                    'encrypted_tiger_id',
                    'encrypted_private_key'
                )
            """
                )
            )
            connection.commit()

        # Run migration again (should be idempotent)
        command.upgrade(alembic_config, "head")

        # Verify data still exists
        with test_engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT account_name FROM tiger_accounts WHERE account_number = 'TEST123456'"
                )
            )
            account_name = result.scalar()
            assert account_name == "Test Account"


class TestMigrationErrors:
    """Test migration error handling."""

    def test_invalid_revision(self, alembic_config):
        """Test handling of invalid revision."""
        with pytest.raises((ValueError, KeyError)):
            command.upgrade(alembic_config, "invalid_revision")

    def test_downgrade_beyond_base(self, alembic_config):
        """Test downgrading beyond base revision."""
        # Upgrade first
        command.upgrade(alembic_config, "head")

        # Downgrade to base should work
        command.downgrade(alembic_config, "base")

        # Trying to downgrade further should handle gracefully
        command.downgrade(alembic_config, "base")  # Should not error

    @patch("alembic.command.upgrade")
    def test_migration_failure_handling(self, mock_upgrade, alembic_config):
        """Test handling of migration failures."""
        # Mock a migration failure
        mock_upgrade.side_effect = OperationalError("Migration failed", None, None)

        with pytest.raises(OperationalError):
            command.upgrade(alembic_config, "head")


class TestPostgreSQLMigrations:
    """Test PostgreSQL-specific migration features."""

    @pytest.mark.skipif(
        "postgresql" not in os.environ.get("DB_TEST_URL", ""),
        reason="PostgreSQL not available for testing",
    )
    def test_postgresql_enum_creation(self):
        """Test that PostgreSQL ENUMs are created properly."""
        # This test would run only when PostgreSQL is available
        test_db_url = os.environ.get("DB_TEST_URL")
        if not test_db_url or "postgresql" not in test_db_url:
            pytest.skip("PostgreSQL test URL not configured")

        # Create config for PostgreSQL
        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

        try:
            # Run migration
            command.upgrade(alembic_cfg, "head")

            # Verify ENUMs exist
            engine = create_engine(test_db_url)
            with engine.connect() as connection:
                result = connection.execute(
                    text(
                        """
                    SELECT typname FROM pg_type 
                    WHERE typname IN ('accounttype', 'accountstatus', 'apikeystatus')
                """
                    )
                )
                enum_types = [row[0] for row in result.fetchall()]

                assert "accounttype" in enum_types
                assert "accountstatus" in enum_types
                assert "apikeystatus" in enum_types

        finally:
            # Cleanup
            try:
                command.downgrade(alembic_cfg, "base")
            except:
                pass

    @pytest.mark.skipif(
        "postgresql" not in os.environ.get("DB_TEST_URL", ""),
        reason="PostgreSQL not available for testing",
    )
    def test_postgresql_partial_indexes(self):
        """Test PostgreSQL partial index creation."""
        test_db_url = os.environ.get("DB_TEST_URL")
        if not test_db_url or "postgresql" not in test_db_url:
            pytest.skip("PostgreSQL test URL not configured")

        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

        try:
            command.upgrade(alembic_cfg, "head")

            engine = create_engine(test_db_url)
            with engine.connect() as connection:
                # Check for partial indexes
                result = connection.execute(
                    text(
                        """
                    SELECT indexname FROM pg_indexes 
                    WHERE indexname LIKE '%_default_%_unique'
                """
                    )
                )
                partial_indexes = [row[0] for row in result.fetchall()]

                assert "ix_tiger_accounts_default_trading_unique" in partial_indexes
                assert "ix_tiger_accounts_default_data_unique" in partial_indexes

        finally:
            try:
                command.downgrade(alembic_cfg, "base")
            except:
                pass


class TestMigrationRevisioning:
    """Test migration revision management."""

    def test_revision_numbering(self, alembic_config):
        """Test that revision numbers are properly formatted."""
        script = ScriptDirectory.from_config(alembic_config)

        for revision in script.walk_revisions():
            # Revision should be non-empty string
            assert revision.revision
            assert isinstance(revision.revision, str)
            assert len(revision.revision) > 0

            # Down revision should be None or valid string
            if revision.down_revision is not None:
                assert isinstance(revision.down_revision, str)
                assert len(revision.down_revision) > 0

    def test_migration_docstrings(self, alembic_config):
        """Test that migrations have proper docstrings."""
        script = ScriptDirectory.from_config(alembic_config)

        for revision in script.walk_revisions():
            assert (
                revision.doc is not None
            ), f"Migration {revision.revision} missing docstring"
            assert (
                len(revision.doc.strip()) > 0
            ), f"Migration {revision.revision} has empty docstring"

    def test_circular_dependencies(self, alembic_config):
        """Test that there are no circular dependencies in migrations."""
        script = ScriptDirectory.from_config(alembic_config)

        # Build dependency graph
        revisions = {}
        for revision in script.walk_revisions():
            revisions[revision.revision] = revision.down_revision

        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(revision):
            if revision in rec_stack:
                return True
            if revision in visited:
                return False

            visited.add(revision)
            rec_stack.add(revision)

            down_rev = revisions.get(revision)
            if down_rev and has_cycle(down_rev):
                return True

            rec_stack.remove(revision)
            return False

        for revision in revisions:
            if has_cycle(revision):
                pytest.fail(
                    f"Circular dependency detected involving revision {revision}"
                )


class TestMigrationTesting:
    """Test migration testing utilities."""

    def test_fresh_database_state(self, temp_sqlite_db):
        """Test starting from fresh database state."""
        engine = create_engine(temp_sqlite_db)

        # Fresh database should have no tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # Should be empty or only have sqlite internal tables
        main_tables = ["tiger_accounts", "api_keys", "audit_logs", "token_statuses"]
        for table in main_tables:
            assert table not in tables

    def test_migration_rollback_scenario(self, alembic_config, test_engine):
        """Test a complete migration rollback scenario."""
        # Start from base
        command.downgrade(alembic_config, "base")

        # Upgrade to head
        command.upgrade(alembic_config, "head")

        # Verify tables exist
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "tiger_accounts" in tables

        # Rollback to base
        command.downgrade(alembic_config, "base")

        # Verify tables are gone
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "tiger_accounts" not in tables

    def test_multiple_upgrade_downgrade_cycles(self, alembic_config, test_engine):
        """Test multiple upgrade/downgrade cycles."""
        for _ in range(3):
            # Upgrade
            command.upgrade(alembic_config, "head")

            # Verify upgrade successful
            inspector = inspect(test_engine)
            tables = inspector.get_table_names()
            assert "tiger_accounts" in tables

            # Downgrade
            command.downgrade(alembic_config, "base")

            # Verify downgrade successful
            inspector = inspect(test_engine)
            tables = inspector.get_table_names()
            assert "tiger_accounts" not in tables
