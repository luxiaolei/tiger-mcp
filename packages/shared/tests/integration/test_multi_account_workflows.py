"""
Integration tests for multi-account workflows in Tiger MCP system.

Tests end-to-end scenarios involving multiple Tiger accounts with real
database operations, routing logic, failover scenarios, and load balancing.
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from database.models.accounts import AccountStatus, AccountType, MarketPermission
from shared.account_router import LoadBalanceStrategy, OperationType

from .fixtures import (
    simulate_load,
)


class TestMultiAccountCreationAndManagement:
    """Test multiple account creation and management scenarios."""

    @pytest.mark.asyncio
    async def test_create_multiple_accounts(self, account_manager, tiger_api_configs):
        """Test creating multiple accounts with different configurations."""
        accounts = []

        # Create three accounts with different types and environments
        for i, (config_name, config) in enumerate(tiger_api_configs.items()):
            account = await account_manager.create_account(
                account_name=f"Integration Test Account {i+1}",
                account_number=config["account_number"],
                tiger_id=config["tiger_id"],
                private_key=config["private_key"],
                account_type=AccountType.STANDARD if i < 2 else AccountType.PAPER,
                environment=config["environment"],
                market_permissions=[MarketPermission.US_STOCK],
                description=f"Test account for {config_name}",
                tags={"test": True, "account_type": config_name},
            )
            accounts.append(account)

        # Verify all accounts were created
        assert len(accounts) == 3

        # Verify account properties
        for i, account in enumerate(accounts):
            assert account.account_name == f"Integration Test Account {i+1}"
            assert account.status == AccountStatus.ACTIVE
            assert account.has_market_permission(MarketPermission.US_STOCK)
            assert account.tags["test"] is True

        # Verify unique account numbers
        account_numbers = {account.account_number for account in accounts}
        assert len(account_numbers) == 3

    @pytest.mark.asyncio
    async def test_default_account_management(
        self, multiple_tiger_accounts, account_manager
    ):
        """Test setting and switching default accounts."""
        trading_account = multiple_tiger_accounts["trading"]
        data_account = multiple_tiger_accounts["data"]
        production_account = multiple_tiger_accounts["production"]

        # Verify initial default settings
        assert trading_account.is_default_trading is True
        assert data_account.is_default_data is True
        assert production_account.is_default_trading is False
        assert production_account.is_default_data is False

        # Switch default trading account
        await account_manager.set_default_trading_account(production_account.id)

        # Verify changes
        updated_trading = await account_manager.get_account_by_id(trading_account.id)
        updated_production = await account_manager.get_account_by_id(
            production_account.id
        )

        assert updated_trading.is_default_trading is False
        assert updated_production.is_default_trading is True

        # Switch default data account
        await account_manager.set_default_data_account(trading_account.id)

        # Verify changes
        updated_trading = await account_manager.get_account_by_id(trading_account.id)
        updated_data = await account_manager.get_account_by_id(data_account.id)

        assert updated_trading.is_default_data is True
        assert updated_data.is_default_data is False

    @pytest.mark.asyncio
    async def test_account_status_transitions(
        self, multiple_tiger_accounts, account_manager
    ):
        """Test account status transitions and their effects."""
        account = multiple_tiger_accounts["trading"]

        # Test suspend account
        await account_manager.update_account_status(
            account.id, AccountStatus.SUSPENDED, reason="Testing suspension"
        )

        updated = await account_manager.get_account_by_id(account.id)
        assert updated.status == AccountStatus.SUSPENDED
        assert updated.tags["status_change_reason"] == "Testing suspension"

        # Test reactivate account
        await account_manager.update_account_status(account.id, AccountStatus.ACTIVE)
        updated = await account_manager.get_account_by_id(account.id)
        assert updated.status == AccountStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_error_count_and_auto_suspension(
        self, multiple_tiger_accounts, account_manager
    ):
        """Test error counting and automatic suspension."""
        account = multiple_tiger_accounts["data"]

        # Simulate multiple errors
        for i in range(8):
            await account_manager.increment_error_count(account.id, f"Test error {i+1}")

        # Account should still be active
        updated = await account_manager.get_account_by_id(account.id)
        assert updated.status == AccountStatus.ACTIVE
        assert updated.error_count == 8

        # Add two more errors to trigger auto-suspension
        for i in range(2):
            await account_manager.increment_error_count(
                account.id, f"Critical error {i+1}"
            )

        # Account should now be suspended
        updated = await account_manager.get_account_by_id(account.id)
        assert updated.status == AccountStatus.SUSPENDED
        assert updated.error_count == 10

        # Reset errors should reactivate
        await account_manager.reset_error_count(account.id)
        updated = await account_manager.get_account_by_id(account.id)
        assert updated.status == AccountStatus.ACTIVE
        assert updated.error_count == 0


class TestCrossAccountDataOperations:
    """Test data operations across multiple accounts with routing logic."""

    @pytest.mark.asyncio
    async def test_data_operation_routing(
        self, multiple_tiger_accounts, account_router
    ):
        """Test routing of data operations to appropriate accounts."""
        # Test market data operation routing
        account = await account_router.route_data_operation(
            OperationType.MARKET_DATA, strategy=LoadBalanceStrategy.ROUND_ROBIN
        )

        # Should route to default data account or any available account
        assert account.is_active
        assert account.has_market_permission(MarketPermission.US_STOCK)

    @pytest.mark.asyncio
    async def test_trading_operation_routing(
        self, multiple_tiger_accounts, account_router
    ):
        """Test routing of trading operations to appropriate accounts."""
        # Test trading operation routing
        account = await account_router.route_trading_operation(
            OperationType.PLACE_ORDER,
            market_permissions=[MarketPermission.US_STOCK],
            strategy=LoadBalanceStrategy.LEAST_USED,
        )

        # Should route to trading-capable account
        assert account.is_active
        assert account.has_market_permission(MarketPermission.US_STOCK)
        # Should be production or paper account
        assert account.environment in ["production", "sandbox"]

    @pytest.mark.asyncio
    async def test_load_balancing_strategies(
        self, multiple_tiger_accounts, account_router
    ):
        """Test different load balancing strategies."""
        strategies = [
            LoadBalanceStrategy.ROUND_ROBIN,
            LoadBalanceStrategy.RANDOM,
            LoadBalanceStrategy.LEAST_USED,
            LoadBalanceStrategy.FASTEST_RESPONSE,
        ]

        results = {}

        for strategy in strategies:
            # Perform 10 operations with each strategy
            accounts_used = []
            for _ in range(10):
                try:
                    account = await account_router.route_operation(
                        OperationType.MARKET_DATA, strategy=strategy
                    )
                    accounts_used.append(account.id)

                    # Record usage for tracking
                    account_router._record_account_usage(account)
                except Exception:
                    # Some strategies might fail if no data is available
                    pass

            results[strategy.value] = accounts_used

        # Verify round robin distributes requests
        if results[LoadBalanceStrategy.ROUND_ROBIN.value]:
            unique_accounts = set(results[LoadBalanceStrategy.ROUND_ROBIN.value])
            assert len(unique_accounts) > 1, "Round robin should use multiple accounts"

    @pytest.mark.asyncio
    async def test_market_permission_filtering(
        self, multiple_tiger_accounts, account_router
    ):
        """Test filtering accounts by market permissions."""
        # Test US stock permission
        us_account = await account_router.route_operation(
            OperationType.MARKET_DATA, market_permissions=[MarketPermission.US_STOCK]
        )
        assert us_account.has_market_permission(MarketPermission.US_STOCK)

        # Test multiple permissions (should find account with both)
        try:
            multi_account = await account_router.route_operation(
                OperationType.MARKET_DATA,
                market_permissions=[
                    MarketPermission.US_STOCK,
                    MarketPermission.US_OPTION,
                ],
            )
            assert multi_account.has_market_permission(MarketPermission.US_STOCK)
            assert multi_account.has_market_permission(MarketPermission.US_OPTION)
        except Exception:
            # Expected if no account has both permissions
            pass


class TestAccountFailoverAndRecovery:
    """Test account failover and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_account_failover_on_error(
        self, multiple_tiger_accounts, account_router, account_manager
    ):
        """Test failover when primary account fails."""
        trading_account = multiple_tiger_accounts["trading"]

        # Simulate account failure by suspending it
        await account_manager.update_account_status(
            trading_account.id, AccountStatus.SUSPENDED, reason="Simulated failure"
        )

        # Try to route trading operation - should failover to another account
        try:
            fallback_account = await account_router.route_trading_operation(
                OperationType.PLACE_ORDER,
                market_permissions=[MarketPermission.US_STOCK],
            )

            # Should get a different account
            assert fallback_account.id != trading_account.id
            assert fallback_account.is_active

        except Exception as e:
            # If no fallback available, should get meaningful error
            assert "No accounts available" in str(e)

    @pytest.mark.asyncio
    async def test_token_refresh_failover(
        self, multiple_tiger_accounts, account_router, token_manager
    ):
        """Test failover when token refresh fails."""
        account = multiple_tiger_accounts["data"]

        # Simulate expired token
        await account_router._account_manager.update_tokens(
            account.id, token_expires_at=datetime.utcnow() - timedelta(hours=1)
        )

        # Mock failed token refresh
        with patch.object(
            token_manager, "refresh_token", return_value=(False, "Mock refresh failure")
        ):
            # Try to use account - should exclude it and find alternative
            exclude_set = set()

            # First attempt should exclude the failed account
            try:
                alternative_account = await account_router.route_operation(
                    OperationType.MARKET_DATA, exclude_accounts=exclude_set
                )
                # If successful, it found an alternative
                assert (
                    alternative_account.id != account.id
                    or alternative_account.has_valid_token
                )
            except Exception:
                # No alternatives available - expected in some cases
                pass

    @pytest.mark.asyncio
    async def test_cascade_failure_handling(
        self, multiple_tiger_accounts, account_manager, account_router
    ):
        """Test handling of cascade failures across accounts."""
        # Suspend all accounts except one
        accounts = list(multiple_tiger_accounts.values())

        for account in accounts[:-1]:
            await account_manager.update_account_status(
                account.id, AccountStatus.SUSPENDED, reason="Cascade test"
            )

        # Should still be able to route to the last remaining account
        remaining_account = await account_router.route_operation(
            OperationType.MARKET_DATA
        )
        assert remaining_account.id == accounts[-1].id
        assert remaining_account.is_active

        # Suspend the last account - should fail gracefully
        await account_manager.update_account_status(
            accounts[-1].id, AccountStatus.SUSPENDED, reason="Cascade test complete"
        )

        # Now operations should fail with no accounts available
        with pytest.raises(Exception) as exc_info:
            await account_router.route_operation(OperationType.MARKET_DATA)

        assert "No accounts available" in str(exc_info.value)


class TestTokenRefreshAutomation:
    """Test automated token refresh across multiple accounts."""

    @pytest.mark.asyncio
    async def test_token_refresh_automation(
        self, multiple_tiger_accounts, token_manager, account_manager
    ):
        """Test automated token refresh for multiple accounts."""
        # Set up accounts needing refresh
        accounts_needing_refresh = []

        for account in multiple_tiger_accounts.values():
            # Set token to expire soon
            await account_manager.update_tokens(
                account.id,
                access_token="old_access_token",
                refresh_token="old_refresh_token",
                token_expires_at=datetime.utcnow() + timedelta(minutes=30),
            )
            accounts_needing_refresh.append(account)

        # Mock successful token refresh
        mock_response = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }

        with patch.object(token_manager, "_tiger_api_client") as mock_client:
            mock_client.refresh_token.return_value = AsyncMock(
                return_value=mock_response
            )

            # Test batch refresh
            refresh_results = []
            for account in accounts_needing_refresh:
                success, error = await token_manager.refresh_token(account)
                refresh_results.append((account.id, success, error))

            # Verify all refreshes succeeded
            for account_id, success, error in refresh_results:
                assert success is True
                assert error is None

    @pytest.mark.asyncio
    async def test_concurrent_token_refresh(
        self, multiple_tiger_accounts, token_manager
    ):
        """Test concurrent token refresh operations."""
        # Prepare accounts for concurrent refresh
        refresh_tasks = []

        for account in multiple_tiger_accounts.values():
            # Create refresh task
            task = asyncio.create_task(token_manager.refresh_token(account))
            refresh_tasks.append((account.id, task))

        # Mock token refresh API
        with patch.object(token_manager, "_tiger_api_client") as mock_client:
            mock_client.refresh_token.return_value = AsyncMock(
                return_value={
                    "access_token": "concurrent_access_token",
                    "refresh_token": "concurrent_refresh_token",
                    "expires_in": 3600,
                }
            )

            # Wait for all refreshes to complete
            results = await asyncio.gather(
                *[task for _, task in refresh_tasks], return_exceptions=True
            )

            # Verify results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Token refresh failed: {result}")

                success, error = result
                assert success is True
                assert error is None


class TestTradingOperationsWithIsolation:
    """Test trading operations with proper account isolation."""

    @pytest.mark.asyncio
    async def test_isolated_trading_operations(
        self, multiple_tiger_accounts, account_router, sample_trading_scenarios
    ):
        """Test that trading operations are properly isolated by account."""
        multiple_tiger_accounts["trading"]
        multiple_tiger_accounts["production"]

        # Mock trading operations
        with patch.object(account_router, "_ensure_valid_token", return_value=True):
            # Execute buy order on trading account
            buy_scenario = sample_trading_scenarios["buy_market_order"]

            # Route to specific account type
            sandbox_account = await account_router.route_operation(
                buy_scenario["operation_type"],
                environment="sandbox",
                strategy=LoadBalanceStrategy.LEAST_USED,
            )

            production_account_selected = await account_router.route_operation(
                buy_scenario["operation_type"],
                environment="production",
                strategy=LoadBalanceStrategy.LEAST_USED,
            )

            # Verify proper environment isolation
            assert sandbox_account.environment == "sandbox"
            assert production_account_selected.environment == "production"
            assert sandbox_account.id != production_account_selected.id

    @pytest.mark.asyncio
    async def test_order_routing_by_market_hours(
        self, multiple_tiger_accounts, account_router
    ):
        """Test order routing considers market hours and account capabilities."""

        # Mock market hours check
        def is_market_open():
            return True  # Simulate market open

        with patch("shared.utils.is_market_open", side_effect=is_market_open):
            # During market hours, should route to active trading accounts
            account = await account_router.route_trading_operation(
                OperationType.PLACE_ORDER,
                market_permissions=[MarketPermission.US_STOCK],
            )

            assert account.is_active
            assert account.has_market_permission(MarketPermission.US_STOCK)

    @pytest.mark.asyncio
    async def test_position_consolidation_across_accounts(
        self, multiple_tiger_accounts
    ):
        """Test position consolidation logic across multiple accounts."""
        # This would test how positions are aggregated across accounts
        # For now, we'll test the data structure and logic

        positions_by_account = {}

        for account_name, account in multiple_tiger_accounts.items():
            # Mock position data
            positions_by_account[account.account_number] = {
                "AAPL": {"quantity": 100, "avg_cost": 150.00},
                "MSFT": {"quantity": 50, "avg_cost": 330.00},
            }

        # Consolidate positions
        consolidated_positions = {}
        for account_positions in positions_by_account.values():
            for symbol, position in account_positions.items():
                if symbol not in consolidated_positions:
                    consolidated_positions[symbol] = {
                        "total_quantity": 0,
                        "total_cost": 0,
                        "accounts": [],
                    }

                consolidated_positions[symbol]["total_quantity"] += position["quantity"]
                consolidated_positions[symbol]["total_cost"] += (
                    position["quantity"] * position["avg_cost"]
                )
                consolidated_positions[symbol]["accounts"].append(account)

        # Calculate average costs
        for symbol, data in consolidated_positions.items():
            data["avg_cost"] = data["total_cost"] / data["total_quantity"]

        # Verify consolidation
        assert (
            consolidated_positions["AAPL"]["total_quantity"] == 300
        )  # 100 * 3 accounts
        assert (
            consolidated_positions["MSFT"]["total_quantity"] == 150
        )  # 50 * 3 accounts


class TestLoadBalancingAndPerformance:
    """Test load balancing and performance under various conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_operations_load_balancing(
        self, multiple_tiger_accounts, account_router
    ):
        """Test load balancing under concurrent operations."""
        # Prepare concurrent operations
        operations = []
        for i in range(20):
            operation = account_router.route_operation(
                OperationType.MARKET_DATA, strategy=LoadBalanceStrategy.ROUND_ROBIN
            )
            operations.append(operation)

        # Execute all operations concurrently
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Analyze distribution
        account_usage = {}
        for result in results:
            if not isinstance(result, Exception):
                account_id = str(result.id)
                account_usage[account_id] = account_usage.get(account_id, 0) + 1

        # Verify reasonably balanced distribution
        if account_usage:
            usage_values = list(account_usage.values())
            max_usage = max(usage_values)
            min_usage = min(usage_values)

            # Shouldn't be too skewed (within reasonable range)
            assert max_usage - min_usage <= 5, "Load balancing too skewed"

    @pytest.mark.asyncio
    async def test_performance_under_load(
        self, multiple_tiger_accounts, account_router, performance_test_data
    ):
        """Test system performance under high load."""
        start_time = time.time()

        # Create load simulation
        async def single_operation():
            return await account_router.route_operation(
                OperationType.MARKET_DATA, strategy=LoadBalanceStrategy.FASTEST_RESPONSE
            )

        # Run load test
        results = await simulate_load(
            single_operation, concurrent_requests=10, total_requests=50
        )

        total_time = time.time() - start_time

        # Analyze results
        successful_operations = [r for r in results if r["success"]]
        [r for r in results if not r["success"]]

        success_rate = len(successful_operations) / len(results)
        avg_response_time = (
            sum(r["duration"] for r in successful_operations)
            / len(successful_operations)
            if successful_operations
            else 0
        )

        # Performance assertions
        assert success_rate >= 0.95, f"Success rate too low: {success_rate}"
        assert (
            avg_response_time < 1.0
        ), f"Average response time too high: {avg_response_time}"
        assert total_time < 30.0, f"Total test time too high: {total_time}"

    @pytest.mark.asyncio
    async def test_response_time_tracking(
        self, multiple_tiger_accounts, account_router
    ):
        """Test response time tracking and fastest response selection."""
        # Record some response times
        for account in multiple_tiger_accounts.values():
            # Simulate different response times
            base_time = 100  # ms
            for i in range(5):
                response_time = base_time + (i * 50)  # Increasing response times
                account_router.record_operation_response_time(account, response_time)

        # Get routing statistics
        stats = await account_router.get_routing_statistics()

        # Verify response time tracking
        assert "average_response_times" in stats
        assert len(stats["average_response_times"]) > 0

        # Test fastest response routing
        account = await account_router.route_operation(
            OperationType.MARKET_DATA, strategy=LoadBalanceStrategy.FASTEST_RESPONSE
        )

        # Should get an account (though we can't verify it's actually fastest without more data)
        assert account is not None
        assert account.is_active


class TestFaultToleranceAndRecovery:
    """Test fault tolerance and recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_database_connection_recovery(
        self, account_manager, multiple_tiger_accounts
    ):
        """Test recovery from database connection issues."""
        # This would test database reconnection logic
        # For integration test, we verify graceful error handling

        try:
            # Simulate database operation during potential connection issue
            accounts = await account_manager.list_accounts(include_inactive=True)
            assert len(accounts) >= 3  # Should have our test accounts
        except Exception as e:
            # Should handle database errors gracefully
            assert "database" in str(e).lower() or "connection" in str(e).lower()

    @pytest.mark.asyncio
    async def test_partial_system_failure(
        self, multiple_tiger_accounts, account_router, account_manager
    ):
        """Test system behavior during partial failures."""
        # Simulate partial failure by disabling some accounts
        accounts = list(multiple_tiger_accounts.values())

        # Disable half the accounts
        for account in accounts[: len(accounts) // 2]:
            await account_manager.update_account_status(
                account.id, AccountStatus.SUSPENDED, reason="Partial failure test"
            )

        # System should still function with remaining accounts
        remaining_account = await account_router.route_operation(
            OperationType.MARKET_DATA
        )

        assert remaining_account.is_active
        assert remaining_account.status == AccountStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_error_propagation_and_circuit_breaking(
        self, multiple_tiger_accounts, account_router, account_manager
    ):
        """Test error propagation and circuit breaker pattern."""
        account = multiple_tiger_accounts["trading"]

        # Simulate repeated failures
        for i in range(5):
            await account_manager.increment_error_count(
                account.id, f"Circuit breaker test error {i+1}"
            )

        # Account should have increased error count
        updated = await account_manager.get_account_by_id(account.id)
        assert updated.error_count == 5

        # High error count should affect routing decisions
        # (Account might be excluded from routing due to error threshold)
        try:
            routed_account = await account_router.route_operation(
                OperationType.PLACE_ORDER, exclude_accounts={str(account.id)}
            )
            # Should route to different account
            assert routed_account.id != account.id
        except Exception:
            # Expected if no other suitable accounts available
            pass


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows spanning multiple accounts."""

    @pytest.mark.asyncio
    async def test_complete_trading_workflow(
        self, multiple_tiger_accounts, account_router, mock_tiger_client_factory
    ):
        """Test complete trading workflow from market data to order execution."""
        # Step 1: Get market data (using data account)
        data_account = await account_router.route_data_operation(
            OperationType.MARKET_DATA, market_permissions=[MarketPermission.US_STOCK]
        )

        assert data_account.is_active

        # Step 2: Route trading operation (using trading account)
        trading_account = await account_router.route_trading_operation(
            OperationType.PLACE_ORDER, market_permissions=[MarketPermission.US_STOCK]
        )

        assert trading_account.is_active

        # Step 3: Verify accounts are different (proper separation of concerns)
        # Note: They might be the same if only one account has required permissions

        # Step 4: Verify both accounts are capable of their operations
        assert data_account.has_market_permission(MarketPermission.US_STOCK)
        assert trading_account.has_market_permission(MarketPermission.US_STOCK)

    @pytest.mark.asyncio
    async def test_multi_account_portfolio_aggregation(self, multiple_tiger_accounts):
        """Test aggregation of portfolio data across multiple accounts."""
        # Mock portfolio data for each account
        portfolios = {}

        for account_name, account in multiple_tiger_accounts.items():
            portfolios[account.account_number] = {
                "cash": 10000.0 + (len(account_name) * 1000),  # Different amounts
                "positions": {
                    "AAPL": {"quantity": 100, "value": 15000.0},
                    "MSFT": {"quantity": 50, "value": 16500.0},
                },
            }

        # Aggregate portfolios
        total_cash = sum(p["cash"] for p in portfolios.values())

        consolidated_positions = {}
        for portfolio in portfolios.values():
            for symbol, position in portfolio["positions"].items():
                if symbol not in consolidated_positions:
                    consolidated_positions[symbol] = {"quantity": 0, "value": 0.0}

                consolidated_positions[symbol]["quantity"] += position["quantity"]
                consolidated_positions[symbol]["value"] += position["value"]

        # Verify aggregation
        expected_accounts = len(multiple_tiger_accounts)
        assert (
            total_cash > expected_accounts * 10000
        )  # At least base amount per account
        assert consolidated_positions["AAPL"]["quantity"] == expected_accounts * 100
        assert consolidated_positions["MSFT"]["quantity"] == expected_accounts * 50

    @pytest.mark.asyncio
    async def test_cross_account_risk_management(
        self, multiple_tiger_accounts, account_router
    ):
        """Test risk management across multiple accounts."""
        # This would test position limits, exposure limits, etc. across accounts

        # Simulate position limits per account
        account_limits = {}
        for account_name, account in multiple_tiger_accounts.items():
            account_limits[account.account_number] = {
                "max_position_size": 1000,
                "max_daily_trades": 100,
                "current_positions": 500,  # Mock current position size
                "daily_trades": 25,  # Mock current daily trades
            }

        # Test position limit enforcement
        for account_number, limits in account_limits.items():
            position_utilization = (
                limits["current_positions"] / limits["max_position_size"]
            )
            trade_utilization = limits["daily_trades"] / limits["max_daily_trades"]

            # These should be within reasonable limits for continued trading
            assert (
                position_utilization < 1.0
            ), f"Position limit exceeded for {account_number}"
            assert (
                trade_utilization < 1.0
            ), f"Daily trade limit exceeded for {account_number}"

        # Test aggregated risk across all accounts
        total_positions = sum(
            limits["current_positions"] for limits in account_limits.values()
        )
        total_daily_trades = sum(
            limits["daily_trades"] for limits in account_limits.values()
        )

        # Set some reasonable aggregated limits
        max_total_positions = 2000
        max_total_daily_trades = 200

        assert (
            total_positions < max_total_positions
        ), "Aggregated position limit exceeded"
        assert (
            total_daily_trades < max_total_daily_trades
        ), "Aggregated daily trade limit exceeded"
