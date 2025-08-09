#!/usr/bin/env python3
"""
Example usage of the Tiger Account Management Service.

This script demonstrates how to use the account management, token management,
and account routing services for Tiger MCP operations.
"""

import logging
from datetime import datetime, timedelta

from database.models.accounts import MarketPermission
from shared import (
    AccountType,
    LoadBalanceStrategy,
    MarketPermission,
    OperationType,
    get_account_manager,
    get_account_router,
    get_token_manager,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_account_management():
    """Demonstrate account management operations."""
    print("\n=== Account Management Example ===")

    account_manager = get_account_manager()

    try:
        # Create a new account
        print("1. Creating a new Tiger account...")
        account = await account_manager.create_account(
            account_name="Demo Trading Account",
            account_number="DU123456",
            tiger_id="demo_tiger_id",
            private_key="demo_private_key_placeholder",
            account_type=AccountType.PAPER,
            environment="sandbox",
            market_permissions=[MarketPermission.US_STOCK, MarketPermission.US_OPTION],
            description="Demo account for testing",
            is_default_trading=True,
        )
        print(f"   Created account: {account.account_name} (ID: {account.id})")

        # List all accounts
        print("\n2. Listing all accounts...")
        accounts = await account_manager.list_accounts()
        for acc in accounts:
            print(
                f"   - {acc.account_name} ({acc.account_number}) - Status: {acc.status.value}"
            )

        # Update account
        print("\n3. Updating account description...")
        updated_account = await account_manager.update_account(
            account.id,
            {"description": "Updated demo account for comprehensive testing"},
        )
        print(f"   Updated description: {updated_account.description}")

        # Get default accounts
        print("\n4. Getting default accounts...")
        default_trading = await account_manager.get_default_trading_account()
        if default_trading:
            print(f"   Default trading account: {default_trading.account_name}")

        default_data = await account_manager.get_default_data_account()
        if default_data:
            print(f"   Default data account: {default_data.account_name}")
        else:
            print("   No default data account set")

        return account

    except Exception as e:
        logger.error(f"Account management error: {e}")
        return None


async def example_token_management(account):
    """Demonstrate token management operations."""
    print("\n=== Token Management Example ===")

    if not account:
        print("No account available for token management demo")
        return

    token_manager = get_token_manager()

    try:
        # Check token status
        print("1. Checking token validity...")
        is_valid, error = await token_manager.validate_token(account)
        print(f"   Token valid: {is_valid}")
        if error:
            print(f"   Error: {error}")

        # Schedule token refresh
        print("\n2. Scheduling token refresh...")
        refresh_time = datetime.utcnow() + timedelta(minutes=5)
        token_status = await token_manager.schedule_token_refresh(account, refresh_time)
        print(f"   Scheduled refresh at: {token_status.next_refresh_at}")

        # Get token statistics
        print("\n3. Getting refresh statistics...")
        stats = await token_manager.get_refresh_statistics(days=7)
        print(f"   Total refreshes (7 days): {stats['total_refreshes']}")
        print(f"   Success rate: {stats['success_rate']}%")

        # Demonstrate token refresh
        print("\n4. Performing manual token refresh...")
        success, error = await token_manager.refresh_token(account)
        print(f"   Refresh successful: {success}")
        if error:
            print(f"   Error: {error}")

    except Exception as e:
        logger.error(f"Token management error: {e}")


async def example_account_routing(account):
    """Demonstrate account routing operations."""
    print("\n=== Account Routing Example ===")

    if not account:
        print("No account available for routing demo")
        return

    account_router = get_account_router()

    try:
        # Route different types of operations
        operations_to_test = [
            (OperationType.MARKET_DATA, "Market data fetch"),
            (OperationType.QUOTE, "Stock quote"),
            (OperationType.ACCOUNT_INFO, "Account information"),
            (OperationType.POSITIONS, "Portfolio positions"),
        ]

        print("1. Routing different operation types...")
        for op_type, description in operations_to_test:
            try:
                selected_account = await account_router.route_operation(
                    operation_type=op_type, strategy=LoadBalanceStrategy.LEAST_USED
                )
                print(f"   {description} -> {selected_account.account_name}")
            except Exception as e:
                print(f"   {description} -> Error: {e}")

        # Check account availability
        print("\n2. Checking account availability...")
        availability = await account_router.check_account_availability(account)
        print(f"   Account: {availability['account_name']}")
        print(f"   Active: {availability['is_active']}")
        print(f"   Can trade: {availability['can_trade']}")
        print(f"   Can fetch data: {availability['can_fetch_data']}")
        print(f"   Token valid: {availability['token_valid']}")

        # Get available accounts for specific operation
        print("\n3. Finding accounts for trading operations...")
        available_accounts = await account_router.get_available_accounts_for_operation(
            OperationType.PLACE_ORDER
        )
        if available_accounts:
            print(f"   Found {len(available_accounts)} accounts for trading:")
            for acc in available_accounts:
                print(f"     - {acc.account_name} ({acc.environment})")
        else:
            print("   No accounts available for trading operations")

        # Get routing statistics
        print("\n4. Getting routing statistics...")
        stats = await account_router.get_routing_statistics()
        print(f"   Total accounts: {stats['total_accounts']}")
        print(f"   Active accounts: {stats['active_accounts']}")
        print(f"   Accounts with errors: {stats['accounts_with_errors']}")

    except Exception as e:
        logger.error(f"Account routing error: {e}")


async def example_integrated_workflow():
    """Demonstrate integrated workflow using all services."""
    print("\n=== Integrated Workflow Example ===")

    account_manager = get_account_manager()
    token_manager = get_token_manager()
    account_router = get_account_router()

    try:
        # 1. Route a data operation
        print("1. Routing market data operation...")
        data_account = await account_router.route_data_operation(
            OperationType.MARKET_DATA, strategy=LoadBalanceStrategy.FASTEST_RESPONSE
        )
        print(f"   Selected data account: {data_account.account_name}")

        # 2. Ensure token is valid
        print("2. Ensuring valid token...")
        if data_account.needs_token_refresh:
            print("   Token needs refresh, refreshing...")
            success, error = await token_manager.refresh_token(data_account)
            if success:
                print("   Token refreshed successfully")
            else:
                print(f"   Token refresh failed: {error}")
        else:
            print("   Token is valid")

        # 3. Record operation response time (simulated)
        print("3. Recording operation metrics...")
        import random

        simulated_response_time = random.uniform(50, 500)  # 50-500ms
        account_router.record_operation_response_time(
            data_account, simulated_response_time
        )
        print(f"   Recorded response time: {simulated_response_time:.1f}ms")

        # 4. Get accounts needing refresh
        print("4. Checking for accounts needing token refresh...")
        accounts_needing_refresh = (
            await account_manager.get_accounts_needing_token_refresh()
        )
        print(f"   Found {len(accounts_needing_refresh)} accounts needing refresh")

        print("\n✅ Integrated workflow completed successfully!")

    except Exception as e:
        logger.error(f"Integrated workflow error: {e}")


async def cleanup_demo_data():
    """Clean up demo data created during the example."""
    print("\n=== Cleanup ===")

    account_manager = get_account_manager()

    try:
        # Find and delete demo accounts
        accounts = await account_manager.list_accounts()
        for account in accounts:
            if account.account_name.startswith(
                "Demo"
            ) or account.account_number.startswith("DU"):
                print(f"Deleting demo account: {account.account_name}")
                await account_manager.delete_account(account.id, force=True)

        print("✅ Cleanup completed")

    except Exception as e:
        logger.error(f"Cleanup error: {e}")


async def main():
    """Main example function."""
    print("🚀 Tiger Account Management Service Examples")
    print("=" * 50)

    try:
        # Run examples
        account = await example_account_management()
        await example_token_management(account)
        await example_account_routing(account)
        await example_integrated_workflow()

        # Ask user if they want to keep demo data
        print("\n" + "=" * 50)
        keep_data = input("Keep demo data? (y/N): ").lower().strip()
        if keep_data != "y":
            await cleanup_demo_data()

        print("\n🎉 All examples completed successfully!")

    except Exception as e:
        logger.error(f"Example execution error: {e}")
        print(f"\n❌ Examples failed: {e}")


if __name__ == "__main__":
    # Note: In a real application, you would need to set up the database
    # connection and ensure all required environment variables are set
    print("⚠️  Note: This example requires a properly configured database")
    print("⚠️  and environment variables. See documentation for setup.")
    print("\nTo run this example:")
    print("1. Set up database with: python -m database.manage_db migrate")
    print("2. Configure environment variables")
    print("3. Run: python example_usage.py")

    # Uncomment the following line to run the examples (after proper setup)
    # asyncio.run(main())
