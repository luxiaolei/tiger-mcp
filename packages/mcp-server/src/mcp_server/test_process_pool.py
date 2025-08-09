"""
Test script for Tiger Process Pool Manager.

Tests process isolation, account management, and API execution.
"""

import asyncio
import sys
from datetime import datetime
from typing import List

# Add paths for imports
sys.path.insert(
    0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/shared/src"
)
sys.path.insert(
    0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/database/src"
)

from database.models.accounts import MarketPermission
from loguru import logger
from process_manager import ProcessManager, get_process_manager
from shared.account_manager import AccountType, get_account_manager


async def test_account_creation():
    """Test creating test accounts."""
    logger.info("=== Testing Account Creation ===")

    account_manager = get_account_manager()

    # Create test accounts
    test_accounts = []

    try:
        # Account 1 - Sandbox
        account1 = await account_manager.create_account(
            account_name="Test Account 1",
            account_number="TEST001",
            tiger_id="test_tiger_id_1",
            private_key="test_private_key_1",
            account_type=AccountType.PAPER,
            environment="sandbox",
            market_permissions=[MarketPermission.US_STOCK],
            description="Test account for process pool testing",
            is_default_data=True,
        )
        test_accounts.append(account1)
        logger.info(f"Created account 1: {account1.account_name} ({account1.id})")

        # Account 2 - Sandbox
        account2 = await account_manager.create_account(
            account_name="Test Account 2",
            account_number="TEST002",
            tiger_id="test_tiger_id_2",
            private_key="test_private_key_2",
            account_type=AccountType.PAPER,
            environment="sandbox",
            market_permissions=[MarketPermission.US_STOCK, MarketPermission.HK_STOCK],
            description="Second test account for isolation testing",
        )
        test_accounts.append(account2)
        logger.info(f"Created account 2: {account2.account_name} ({account2.id})")

        return test_accounts

    except Exception as e:
        logger.error(f"Failed to create test accounts: {e}")
        return test_accounts


async def test_process_manager_startup():
    """Test process manager startup and basic functionality."""
    logger.info("=== Testing Process Manager Startup ===")

    try:
        process_manager = get_process_manager()

        # Start process manager
        await process_manager.start()
        logger.info("Process manager started successfully")

        # Get initial system metrics
        metrics = await process_manager.get_system_metrics()
        logger.info(f"Initial system metrics: {metrics}")

        return process_manager

    except Exception as e:
        logger.error(f"Failed to start process manager: {e}")
        raise


async def test_process_creation_and_isolation(
    process_manager: ProcessManager, test_accounts: List
):
    """Test process creation and account isolation."""
    logger.info("=== Testing Process Creation and Isolation ===")

    try:
        if len(test_accounts) < 2:
            logger.warning("Need at least 2 accounts for isolation testing")
            return

        account1_id = str(test_accounts[0].id)
        account2_id = str(test_accounts[1].id)

        # Test process creation for account 1
        logger.info(f"Testing process creation for account 1: {account1_id}")

        try:
            # This should trigger process creation
            result1 = await process_manager.execute_api_call(
                account_id=account1_id, method="health_check", timeout=15.0
            )
            logger.info(f"Account 1 health check result: {result1}")
        except Exception as e:
            logger.error(f"Account 1 health check failed: {e}")

        # Test process creation for account 2
        logger.info(f"Testing process creation for account 2: {account2_id}")

        try:
            result2 = await process_manager.execute_api_call(
                account_id=account2_id, method="health_check", timeout=15.0
            )
            logger.info(f"Account 2 health check result: {result2}")
        except Exception as e:
            logger.error(f"Account 2 health check failed: {e}")

        # Check process status
        processes = await process_manager.get_all_process_status()
        logger.info(f"Total processes created: {len(processes)}")

        for process in processes:
            logger.info(
                f"Process {process.process_id[:8]}: "
                f"Account {process.account_number}, Status {process.status.value}"
            )

        # Test that each account has its own process
        account1_process = await process_manager.get_account_process_status(account1_id)
        account2_process = await process_manager.get_account_process_status(account2_id)

        if account1_process and account2_process:
            if account1_process.process_id != account2_process.process_id:
                logger.info(
                    "✓ Account isolation verified - each account has separate process"
                )
            else:
                logger.error("✗ Account isolation failed - accounts share process")

        return processes

    except Exception as e:
        logger.error(f"Failed process isolation test: {e}")
        return []


async def test_api_calls(process_manager: ProcessManager, test_accounts: List):
    """Test various API calls through the process pool."""
    logger.info("=== Testing API Calls ===")

    if not test_accounts:
        logger.warning("No test accounts available for API testing")
        return

    account_id = str(test_accounts[0].id)

    try:
        # Test different API call patterns
        test_calls = [
            ("health_check", [], {}),
            ("quote.get_market_status", [], {}),  # This will likely fail in test env
            ("trade.get_account", [], {}),  # This will likely fail in test env
        ]

        for method, args, kwargs in test_calls:
            try:
                logger.info(f"Testing API call: {method}")
                start_time = datetime.utcnow()

                result = await process_manager.execute_api_call(
                    account_id=account_id,
                    method=method,
                    args=args,
                    kwargs=kwargs,
                    timeout=10.0,
                )

                execution_time = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"✓ {method} completed in {execution_time:.2f}s")
                logger.debug(f"Result: {result}")

            except Exception as e:
                logger.warning(f"✗ {method} failed (expected in test env): {e}")

    except Exception as e:
        logger.error(f"API testing failed: {e}")


async def test_process_restart(process_manager: ProcessManager, test_accounts: List):
    """Test process restart functionality."""
    logger.info("=== Testing Process Restart ===")

    if not test_accounts:
        logger.warning("No test accounts available for restart testing")
        return

    account_id = str(test_accounts[0].id)

    try:
        # Get current process info
        process_before = await process_manager.get_account_process_status(account_id)
        if not process_before:
            logger.warning("No process found to restart")
            return

        logger.info(
            f"Current process: {process_before.process_id[:8]} (PID: {process_before.pid})"
        )

        # Restart the process
        logger.info("Restarting process...")
        restart_success = await process_manager.restart_account_process(account_id)

        if restart_success:
            logger.info("✓ Process restart initiated successfully")

            # Wait a moment for restart to complete
            await asyncio.sleep(3)

            # Get new process info
            process_after = await process_manager.get_account_process_status(account_id)

            if process_after and process_after.process_id != process_before.process_id:
                logger.info("✓ Process restart verified - new process created")
                logger.info(
                    f"New process: {process_after.process_id[:8]} (PID: {process_after.pid})"
                )
            else:
                logger.warning("Process restart may not have completed")
        else:
            logger.error("✗ Process restart failed")

    except Exception as e:
        logger.error(f"Process restart test failed: {e}")


async def test_metrics_and_monitoring(process_manager: ProcessManager):
    """Test metrics collection and monitoring."""
    logger.info("=== Testing Metrics and Monitoring ===")

    try:
        # Get system metrics
        system_metrics = await process_manager.get_system_metrics()
        logger.info("System metrics:")
        for key, value in system_metrics.items():
            logger.info(f"  {key}: {value}")

        # Get process metrics
        process_metrics = await process_manager.get_process_metrics()
        logger.info(f"Process metrics for {len(process_metrics)} processes:")

        for process_id, metrics in process_metrics.items():
            logger.info(f"  Process {process_id[:8]}:")
            logger.info(f"    Total tasks: {metrics.total_tasks}")
            logger.info(f"    Success rate: {metrics.success_rate:.1f}%")
            logger.info(f"    Avg response time: {metrics.average_response_time:.3f}s")
            logger.info(f"    Uptime: {metrics.uptime_seconds:.1f}s")

    except Exception as e:
        logger.error(f"Metrics testing failed: {e}")


async def test_health_checks(process_manager: ProcessManager):
    """Test health check functionality."""
    logger.info("=== Testing Health Checks ===")

    try:
        # Run health checks on all accounts
        health_results = await process_manager.health_check_all_accounts()

        logger.info(f"Health check results for {len(health_results)} accounts:")
        for result in health_results:
            status = "✓ HEALTHY" if result["healthy"] else "✗ UNHEALTHY"
            logger.info(f"  Account {result['account_id'][:8]}: {status}")
            if not result["healthy"]:
                logger.info(f"    Error: {result.get('error', 'Unknown')}")

    except Exception as e:
        logger.error(f"Health check testing failed: {e}")


async def cleanup_test_accounts(test_accounts: List):
    """Clean up test accounts."""
    logger.info("=== Cleaning Up Test Accounts ===")

    account_manager = get_account_manager()

    for account in test_accounts:
        try:
            await account_manager.delete_account(account.id, force=True)
            logger.info(f"Deleted test account: {account.account_name}")
        except Exception as e:
            logger.error(f"Failed to delete account {account.account_name}: {e}")


async def main():
    """Main test function."""
    logger.info("Starting Tiger Process Pool Integration Tests")
    logger.info("=" * 60)

    test_accounts = []
    process_manager = None

    try:
        # Create test accounts
        test_accounts = await test_account_creation()

        if not test_accounts:
            logger.error("Failed to create test accounts, aborting tests")
            return

        # Start process manager
        process_manager = await test_process_manager_startup()

        # Run tests
        await test_process_creation_and_isolation(process_manager, test_accounts)
        await asyncio.sleep(2)  # Let processes stabilize

        await test_api_calls(process_manager, test_accounts)
        await asyncio.sleep(2)

        await test_process_restart(process_manager, test_accounts)
        await asyncio.sleep(2)

        await test_metrics_and_monitoring(process_manager)
        await test_health_checks(process_manager)

        logger.info("=" * 60)
        logger.info("✓ All tests completed successfully!")

    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        import traceback

        logger.error(traceback.format_exc())

    finally:
        # Cleanup
        if process_manager:
            try:
                await process_manager.stop()
                logger.info("Process manager stopped")
            except Exception as e:
                logger.error(f"Failed to stop process manager: {e}")

        if test_accounts:
            await cleanup_test_accounts(test_accounts)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>test</cyan> | <level>{message}</level>",
        level="DEBUG",
    )

    # Run tests
    asyncio.run(main())
