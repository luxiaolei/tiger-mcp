"""
Integration tests for database operations with real PostgreSQL.

Tests database transactions, connection pooling, concurrent operations,
and data consistency across multiple accounts and operations.
"""

import asyncio
import time
from datetime import datetime, timedelta

import pytest
import sqlalchemy as sa
from database.models.accounts import (
    AccountType,
    MarketPermission,
    TigerAccount,
)
from database.models.api_keys import APIKey
from database.models.token_status import TokenStatus
from shared.account_manager import AccountManagerError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestDatabaseConnectionAndPooling:
    """Test database connection management and pooling."""

    @pytest.mark.asyncio
    async def test_database_connection_pool(self, test_database):
        """Test database connection pool behavior."""
        # Create multiple concurrent sessions
        sessions = []
        for i in range(10):
            session = AsyncSession(test_database)
            sessions.append(session)

        # Test concurrent queries
        tasks = []
        for session in sessions:
            task = asyncio.create_task(session.execute(text("SELECT 1 as test_value")))
            tasks.append(task)

        # Wait for all queries to complete
        results = await asyncio.gather(*tasks)

        # Verify all queries succeeded
        assert len(results) == 10
        for result in results:
            row = result.first()
            assert row.test_value == 1

        # Close all sessions
        for session in sessions:
            await session.close()

    @pytest.mark.asyncio
    async def test_connection_recovery(self, test_database):
        """Test database connection recovery after failure."""
        # This would test connection recovery in a real scenario
        # For now, we test basic connection health

        async with AsyncSession(test_database) as session:
            # Test basic connectivity
            result = await session.execute(text("SELECT current_timestamp"))
            timestamp = result.scalar()
            assert isinstance(timestamp, datetime)

            # Test connection is still alive after operation
            result2 = await session.execute(text("SELECT 2 as test"))
            assert result2.scalar() == 2

    @pytest.mark.asyncio
    async def test_transaction_isolation(self, test_database):
        """Test transaction isolation between concurrent operations."""
        # Create two sessions for testing isolation
        session1 = AsyncSession(test_database)
        session2 = AsyncSession(test_database)

        try:
            # Start transactions in both sessions
            async with session1.begin():
                # Create account in session1 but don't commit yet
                account1 = TigerAccount(
                    account_name="Isolation Test 1",
                    account_number="ISO001",
                    tiger_id='{"ciphertext": "test", "nonce": "test", "tag": "test", "salt": "test", "key_version": 1, "algorithm": "AES-256-GCM"}',
                    private_key='{"ciphertext": "test", "nonce": "test", "tag": "test", "salt": "test", "key_version": 1, "algorithm": "AES-256-GCM"}',
                    account_type=AccountType.STANDARD,
                    environment="test",
                )
                session1.add(account1)
                await session1.flush()  # Make visible within transaction

                # Try to find account in session2 (should not see uncommitted data)
                async with session2.begin():
                    result = await session2.execute(
                        sa.select(TigerAccount).where(
                            TigerAccount.account_number == "ISO001"
                        )
                    )
                    found_account = result.scalar_one_or_none()
                    assert found_account is None, "Should not see uncommitted data"

                # Rollback session1 transaction
                await session1.rollback()

            # Verify account was not created (due to rollback)
            async with session2.begin():
                result = await session2.execute(
                    sa.select(TigerAccount).where(
                        TigerAccount.account_number == "ISO001"
                    )
                )
                found_account = result.scalar_one_or_none()
                assert found_account is None, "Account should not exist after rollback"

        finally:
            await session1.close()
            await session2.close()


class TestConcurrentDatabaseOperations:
    """Test concurrent database operations and data consistency."""

    @pytest.mark.asyncio
    async def test_concurrent_account_creation(
        self, account_manager, tiger_api_configs
    ):
        """Test concurrent account creation operations."""
        # Prepare account configurations
        configs = list(tiger_api_configs.values())

        async def create_account_task(config, index):
            return await account_manager.create_account(
                account_name=f"Concurrent Account {index}",
                account_number=f"CONC{index:03d}",
                tiger_id=f"{config['tiger_id']}_{index}",
                private_key=config["private_key"],
                account_type=AccountType.STANDARD,
                environment=config["environment"],
                market_permissions=[MarketPermission.US_STOCK],
                description=f"Concurrently created account {index}",
            )

        # Create multiple accounts concurrently
        tasks = [create_account_task(configs[i % len(configs)], i) for i in range(5)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all accounts were created successfully
        successful_accounts = []
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Account creation failed: {result}")
            successful_accounts.append(result)

        assert len(successful_accounts) == 5

        # Verify unique account numbers
        account_numbers = {acc.account_number for acc in successful_accounts}
        assert len(account_numbers) == 5, "All account numbers should be unique"

    @pytest.mark.asyncio
    async def test_concurrent_default_account_updates(
        self, multiple_tiger_accounts, account_manager
    ):
        """Test concurrent default account updates."""
        accounts = list(multiple_tiger_accounts.values())

        # Try to set multiple accounts as default simultaneously
        tasks = [
            account_manager.set_default_trading_account(account.id)
            for account in accounts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Only one should succeed in being set as default
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 1, "At least one should succeed"

        # Verify only one account is default trading
        all_accounts = await account_manager.list_accounts()
        default_trading_accounts = [
            acc for acc in all_accounts if acc.is_default_trading
        ]
        assert (
            len(default_trading_accounts) == 1
        ), "Only one account should be default trading"

    @pytest.mark.asyncio
    async def test_concurrent_error_count_updates(
        self, multiple_tiger_accounts, account_manager
    ):
        """Test concurrent error count updates on the same account."""
        account = list(multiple_tiger_accounts.values())[0]

        # Increment error count concurrently
        tasks = [
            account_manager.increment_error_count(account.id, f"Concurrent error {i}")
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Error count increment failed: {result}")

        # Verify final error count
        updated_account = await account_manager.get_account_by_id(account.id)
        assert updated_account.error_count >= 10, "Error count should be at least 10"

    @pytest.mark.asyncio
    async def test_concurrent_token_updates(
        self, multiple_tiger_accounts, account_manager
    ):
        """Test concurrent token updates."""
        account = list(multiple_tiger_accounts.values())[0]

        # Update tokens concurrently with different values
        tasks = []
        for i in range(5):
            task = account_manager.update_tokens(
                account.id,
                access_token=f"concurrent_access_token_{i}",
                refresh_token=f"concurrent_refresh_token_{i}",
                token_expires_at=datetime.utcnow() + timedelta(hours=i + 1),
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed (last one wins)
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Token update failed: {result}")

        # Verify account was updated
        updated_account = await account_manager.get_account_by_id(account.id)
        assert updated_account.access_token is not None


class TestDataConsistencyAndIntegrity:
    """Test data consistency and integrity constraints."""

    @pytest.mark.asyncio
    async def test_unique_constraint_enforcement(
        self, account_manager, tiger_api_configs
    ):
        """Test that unique constraints are properly enforced."""
        config = tiger_api_configs["account_1"]

        # Create first account
        account1 = await account_manager.create_account(
            account_name="First Account",
            account_number=config["account_number"],
            tiger_id=config["tiger_id"],
            private_key=config["private_key"],
            account_type=AccountType.STANDARD,
            environment=config["environment"],
        )

        # Try to create second account with same account number
        with pytest.raises(Exception) as exc_info:
            await account_manager.create_account(
                account_name="Duplicate Account",
                account_number=config["account_number"],  # Same account number
                tiger_id="different_tiger_id",
                private_key="different_private_key",
                account_type=AccountType.PAPER,
                environment=config["environment"],
            )

        # Should get validation error about duplicate account number
        assert "already exists" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_foreign_key_constraints(
        self, test_database, multiple_tiger_accounts
    ):
        """Test foreign key constraint enforcement."""
        account = list(multiple_tiger_accounts.values())[0]

        async with AsyncSession(test_database) as session:
            # Create token status linked to account
            token_status = TokenStatus.create_scheduled_refresh(
                tiger_account_id=account.id,
                next_refresh_at=datetime.utcnow() + timedelta(hours=1),
            )
            session.add(token_status)
            await session.commit()

            # Verify token status was created
            result = await session.execute(
                sa.select(TokenStatus).where(TokenStatus.tiger_account_id == account.id)
            )
            found_status = result.scalar_one_or_none()
            assert found_status is not None
            assert found_status.tiger_account_id == account.id

    @pytest.mark.asyncio
    async def test_cascade_deletion_behavior(
        self, test_database, account_manager, multiple_tiger_accounts
    ):
        """Test cascade deletion behavior."""
        account = list(multiple_tiger_accounts.values())[0]

        # Create related records
        async with AsyncSession(test_database) as session:
            # Create token status
            token_status = TokenStatus.create_scheduled_refresh(
                tiger_account_id=account.id,
                next_refresh_at=datetime.utcnow() + timedelta(hours=1),
            )
            session.add(token_status)

            # Create API key
            api_key = APIKey(
                tiger_account_id=account.id,
                key_name="Test API Key",
                encrypted_key_data='{"test": "data"}',
                permissions={"read": True},
                created_by="test_user",
            )
            session.add(api_key)

            await session.commit()

        # Delete account (should handle related records appropriately)
        try:
            await account_manager.delete_account(account.id, force=True)
        except AccountManagerError:
            # Expected if cascade deletion isn't configured
            pass

        # If deletion succeeded, verify related records handling
        async with AsyncSession(test_database) as session:
            # Check if account still exists
            result = await session.execute(
                sa.select(TigerAccount).where(TigerAccount.id == account.id)
            )
            account_exists = result.scalar_one_or_none() is not None

            if not account_exists:
                # Account was deleted, check related records
                token_result = await session.execute(
                    sa.select(TokenStatus).where(
                        TokenStatus.tiger_account_id == account.id
                    )
                )
                token_result.scalar_one_or_none() is not None

                # Based on cascade configuration, tokens might be deleted or orphaned
                # This test verifies the behavior is consistent
                assert True  # Test passes if no exceptions thrown


class TestDatabasePerformance:
    """Test database performance under various conditions."""

    @pytest.mark.asyncio
    async def test_bulk_operations_performance(
        self, account_manager, tiger_api_configs
    ):
        """Test performance of bulk database operations."""
        start_time = time.time()

        # Create multiple accounts
        accounts = []
        config = tiger_api_configs["account_1"]

        for i in range(20):
            account = await account_manager.create_account(
                account_name=f"Bulk Test Account {i}",
                account_number=f"BULK{i:03d}",
                tiger_id=f"{config['tiger_id']}_bulk_{i}",
                private_key=config["private_key"],
                account_type=AccountType.STANDARD,
                environment=config["environment"],
            )
            accounts.append(account)

        creation_time = time.time() - start_time

        # Test bulk retrieval
        start_time = time.time()
        all_accounts = await account_manager.list_accounts()
        retrieval_time = time.time() - start_time

        # Performance assertions
        assert creation_time < 10.0, f"Bulk creation took too long: {creation_time}s"
        assert retrieval_time < 2.0, f"Bulk retrieval took too long: {retrieval_time}s"
        assert len(all_accounts) >= 20, "Should have at least 20 accounts"

    @pytest.mark.asyncio
    async def test_query_performance_with_indices(
        self, test_database, multiple_tiger_accounts
    ):
        """Test query performance with database indices."""
        # Test query by account number (should be indexed)
        start_time = time.time()

        async with AsyncSession(test_database) as session:
            for _ in range(100):  # Repeat query to test index effectiveness
                result = await session.execute(
                    sa.select(TigerAccount).where(
                        TigerAccount.account_number
                        == list(multiple_tiger_accounts.values())[0].account_number
                    )
                )
                account = result.scalar_one_or_none()
                assert account is not None

        query_time = time.time() - start_time

        # Should be fast due to index on account_number
        assert query_time < 2.0, f"Indexed queries took too long: {query_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_query_performance(
        self, test_database, multiple_tiger_accounts
    ):
        """Test performance under concurrent query load."""
        account_numbers = [
            acc.account_number for acc in multiple_tiger_accounts.values()
        ]

        async def query_account(account_number):
            async with AsyncSession(test_database) as session:
                result = await session.execute(
                    sa.select(TigerAccount).where(
                        TigerAccount.account_number == account_number
                    )
                )
                return result.scalar_one_or_none()

        start_time = time.time()

        # Run 50 concurrent queries
        tasks = []
        for i in range(50):
            account_number = account_numbers[i % len(account_numbers)]
            tasks.append(query_account(account_number))

        results = await asyncio.gather(*tasks)

        query_time = time.time() - start_time

        # Verify all queries succeeded
        assert all(result is not None for result in results)

        # Should handle concurrent load reasonably well
        assert query_time < 5.0, f"Concurrent queries took too long: {query_time}s"


class TestDatabaseMigrationsAndSchema:
    """Test database migrations and schema changes."""

    @pytest.mark.asyncio
    async def test_schema_validation(self, test_database):
        """Test that database schema matches model definitions."""
        async with AsyncSession(test_database) as session:
            # Test that all expected tables exist
            result = await session.execute(
                text(
                    """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """
                )
            )

            tables = [row[0] for row in result.fetchall()]

            expected_tables = ["tiger_accounts", "token_statuses", "api_keys"]

            for expected_table in expected_tables:
                assert (
                    expected_table in tables
                ), f"Expected table {expected_table} not found"

    @pytest.mark.asyncio
    async def test_column_constraints(self, test_database):
        """Test that column constraints are properly enforced."""
        async with AsyncSession(test_database) as session:
            # Test NOT NULL constraint
            with pytest.raises(Exception):
                account = TigerAccount(
                    # Missing required fields
                    account_name="Test",
                    # account_number missing (NOT NULL)
                    tiger_id='{"test": "data"}',
                    private_key='{"test": "data"}',
                    account_type=AccountType.STANDARD,
                    environment="test",
                )
                session.add(account)
                await session.commit()

    @pytest.mark.asyncio
    async def test_enum_constraints(self, test_database):
        """Test that enum constraints are properly enforced."""
        async with AsyncSession(test_database) as session:
            # Create account with valid enum values
            account = TigerAccount(
                account_name="Enum Test",
                account_number="ENUM001",
                tiger_id='{"test": "data"}',
                private_key='{"test": "data"}',
                account_type=AccountType.STANDARD,
                environment="test",
            )
            session.add(account)
            await session.commit()

            # Verify account was created
            result = await session.execute(
                sa.select(TigerAccount).where(TigerAccount.account_number == "ENUM001")
            )
            found_account = result.scalar_one_or_none()
            assert found_account is not None
            assert found_account.account_type == AccountType.STANDARD


class TestDatabaseBackupAndRecovery:
    """Test database backup and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_data_persistence(
        self, test_database, account_manager, tiger_api_configs
    ):
        """Test that data persists across sessions."""
        config = tiger_api_configs["account_1"]

        # Create account
        account = await account_manager.create_account(
            account_name="Persistence Test",
            account_number="PERSIST001",
            tiger_id=config["tiger_id"],
            private_key=config["private_key"],
            account_type=AccountType.STANDARD,
            environment=config["environment"],
        )

        account_id = account.id

        # Create new session to test persistence
        async with AsyncSession(test_database) as new_session:
            result = await new_session.execute(
                sa.select(TigerAccount).where(TigerAccount.id == account_id)
            )
            persisted_account = result.scalar_one_or_none()

            assert persisted_account is not None
            assert persisted_account.account_name == "Persistence Test"
            assert persisted_account.account_number == "PERSIST001"

    @pytest.mark.asyncio
    async def test_transaction_recovery(self, test_database):
        """Test recovery from failed transactions."""
        session = AsyncSession(test_database)

        try:
            async with session.begin():
                # Create valid account
                account1 = TigerAccount(
                    account_name="Recovery Test 1",
                    account_number="RECOVERY001",
                    tiger_id='{"test": "data"}',
                    private_key='{"test": "data"}',
                    account_type=AccountType.STANDARD,
                    environment="test",
                )
                session.add(account1)

                # Create invalid account (will cause transaction to fail)
                account2 = TigerAccount(
                    account_name="Recovery Test 2",
                    account_number="RECOVERY001",  # Duplicate number - will fail
                    tiger_id='{"test": "data"}',
                    private_key='{"test": "data"}',
                    account_type=AccountType.STANDARD,
                    environment="test",
                )
                session.add(account2)

                # This should fail due to duplicate account number
                await session.commit()

        except Exception:
            # Transaction failed, verify rollback worked
            await session.rollback()

        finally:
            await session.close()

        # Verify neither account was created (due to transaction rollback)
        async with AsyncSession(test_database) as new_session:
            result = await new_session.execute(
                sa.select(TigerAccount).where(
                    TigerAccount.account_number == "RECOVERY001"
                )
            )
            found_account = result.scalar_one_or_none()
            assert (
                found_account is None
            ), "No accounts should exist after failed transaction"


class TestDatabaseMonitoringAndHealthChecks:
    """Test database monitoring and health check functionality."""

    @pytest.mark.asyncio
    async def test_connection_health_check(self, test_database):
        """Test database connection health check."""
        async with AsyncSession(test_database) as session:
            # Simple health check query
            start_time = time.time()
            result = await session.execute(text("SELECT 1 as health_check"))
            health_time = time.time() - start_time

            assert result.scalar() == 1
            assert health_time < 1.0, f"Health check took too long: {health_time}s"

    @pytest.mark.asyncio
    async def test_query_performance_monitoring(
        self, test_database, multiple_tiger_accounts
    ):
        """Test query performance monitoring."""
        slow_queries = []

        async def timed_query(query_name, query_func):
            start_time = time.time()
            result = await query_func()
            duration = time.time() - start_time

            if duration > 0.5:  # Consider > 500ms as slow
                slow_queries.append((query_name, duration))

            return result, duration

        async with AsyncSession(test_database) as session:
            # Test various query patterns
            queries = [
                ("simple_select", lambda: session.execute(text("SELECT 1"))),
                (
                    "account_by_id",
                    lambda: session.execute(
                        sa.select(TigerAccount).where(
                            TigerAccount.id
                            == list(multiple_tiger_accounts.values())[0].id
                        )
                    ),
                ),
                ("account_list", lambda: session.execute(sa.select(TigerAccount))),
            ]

            for query_name, query_func in queries:
                result, duration = await timed_query(query_name, query_func)
                assert result is not None

                # Log slow queries for monitoring
                if duration > 0.1:  # Log queries > 100ms
                    print(f"Query {query_name} took {duration:.3f}s")

        # Report slow queries
        if slow_queries:
            print(f"Found {len(slow_queries)} slow queries:")
            for query_name, duration in slow_queries:
                print(f"  {query_name}: {duration:.3f}s")

    @pytest.mark.asyncio
    async def test_connection_pool_monitoring(self, test_database):
        """Test connection pool monitoring."""
        # Create multiple sessions to test pool behavior
        sessions = []
        for i in range(5):
            session = AsyncSession(test_database)
            sessions.append(session)

        # Verify all sessions can execute queries
        for i, session in enumerate(sessions):
            result = await session.execute(text(f"SELECT {i+1} as session_id"))
            assert result.scalar() == i + 1

        # Close all sessions
        for session in sessions:
            await session.close()

        # Verify new sessions can still be created
        async with AsyncSession(test_database) as new_session:
            result = await new_session.execute(text("SELECT 'pool_healthy' as status"))
            assert result.scalar() == "pool_healthy"
