"""
Integration test script for Tiger MCP tools.

Tests the basic functionality and integration of account and trading tools
without requiring actual Tiger API credentials or live connections.
"""

import asyncio
import sys
from typing import List

# Add paths for imports
sys.path.insert(
    0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/shared/src"
)

# Import tool functions to test
from account_tools import (
    tiger_add_account,
    tiger_get_account_status,
    tiger_list_accounts,
    tiger_remove_account,
)
from loguru import logger
from trading_tools import (
    tiger_cancel_order,
    tiger_get_positions,
    tiger_modify_order,
    tiger_place_order,
)


class MockTest:
    """Mock test class to validate tool structure and error handling."""

    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results: List[str] = []

    def log_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "PASS" if success else "FAIL"
        message = f"{test_name}: {status}"
        if details:
            message += f" - {details}"

        self.test_results.append(message)

        if success:
            self.passed_tests += 1
            logger.info(message)
        else:
            self.failed_tests += 1
            logger.error(message)

    async def test_account_tools_structure(self):
        """Test that account tools have proper structure and error handling."""
        print("\n=== Testing Account Tools Structure ===")

        # Test tiger_list_accounts with invalid parameters
        try:
            response = await tiger_list_accounts(account_type="invalid_type")
            if not response.success and "Invalid account_type" in response.error:
                self.log_result("list_accounts_invalid_type", True, "Proper validation")
            else:
                self.log_result(
                    "list_accounts_invalid_type", False, f"Response: {response}"
                )
        except Exception as e:
            self.log_result("list_accounts_invalid_type", False, f"Exception: {e}")

        # Test tiger_add_account with missing required fields
        try:
            response = await tiger_add_account(
                name="", api_key="test", secret_key="test"
            )
            if not response.success and "name is required" in response.error:
                self.log_result("add_account_empty_name", True, "Proper validation")
            else:
                self.log_result(
                    "add_account_empty_name", False, f"Response: {response}"
                )
        except Exception as e:
            self.log_result("add_account_empty_name", False, f"Exception: {e}")

        # Test tiger_remove_account with invalid UUID
        try:
            response = await tiger_remove_account("invalid-uuid")
            if not response.success and "Invalid account ID format" in response.error:
                self.log_result(
                    "remove_account_invalid_uuid", True, "Proper validation"
                )
            else:
                self.log_result(
                    "remove_account_invalid_uuid", False, f"Response: {response}"
                )
        except Exception as e:
            self.log_result("remove_account_invalid_uuid", False, f"Exception: {e}")

        # Test tiger_get_account_status with invalid UUID
        try:
            response = await tiger_get_account_status("invalid-uuid")
            if not response.success and "Invalid account ID format" in response.error:
                self.log_result(
                    "get_account_status_invalid_uuid", True, "Proper validation"
                )
            else:
                self.log_result(
                    "get_account_status_invalid_uuid", False, f"Response: {response}"
                )
        except Exception as e:
            self.log_result("get_account_status_invalid_uuid", False, f"Exception: {e}")

    async def test_trading_tools_structure(self):
        """Test that trading tools have proper structure and error handling."""
        print("\n=== Testing Trading Tools Structure ===")

        # Test tiger_place_order with invalid inputs
        try:
            response = await tiger_place_order(
                symbol="", side="BUY", quantity=100, order_type="MARKET"
            )
            if not response.success and "Symbol is required" in response.error:
                self.log_result("place_order_empty_symbol", True, "Proper validation")
            else:
                self.log_result(
                    "place_order_empty_symbol", False, f"Response: {response}"
                )
        except Exception as e:
            self.log_result("place_order_empty_symbol", False, f"Exception: {e}")

        # Test tiger_place_order with invalid side
        try:
            response = await tiger_place_order(
                symbol="AAPL", side="INVALID", quantity=100, order_type="MARKET"
            )
            if not response.success and "Side must be" in response.error:
                self.log_result("place_order_invalid_side", True, "Proper validation")
            else:
                self.log_result(
                    "place_order_invalid_side", False, f"Response: {response}"
                )
        except Exception as e:
            self.log_result("place_order_invalid_side", False, f"Exception: {e}")

        # Test tiger_place_order with negative quantity
        try:
            response = await tiger_place_order(
                symbol="AAPL", side="BUY", quantity=-10, order_type="MARKET"
            )
            if not response.success and "Quantity must be positive" in response.error:
                self.log_result(
                    "place_order_negative_quantity", True, "Proper validation"
                )
            else:
                self.log_result(
                    "place_order_negative_quantity", False, f"Response: {response}"
                )
        except Exception as e:
            self.log_result("place_order_negative_quantity", False, f"Exception: {e}")

        # Test tiger_place_order LIMIT order without price
        try:
            response = await tiger_place_order(
                symbol="AAPL", side="BUY", quantity=100, order_type="LIMIT"
            )
            if not response.success and "requires a price" in response.error:
                self.log_result("place_order_limit_no_price", True, "Proper validation")
            else:
                self.log_result(
                    "place_order_limit_no_price", False, f"Response: {response}"
                )
        except Exception as e:
            self.log_result("place_order_limit_no_price", False, f"Exception: {e}")

        # Test tiger_cancel_order with empty order ID
        try:
            response = await tiger_cancel_order("")
            if not response.success and "Order ID is required" in response.error:
                self.log_result("cancel_order_empty_id", True, "Proper validation")
            else:
                self.log_result("cancel_order_empty_id", False, f"Response: {response}")
        except Exception as e:
            self.log_result("cancel_order_empty_id", False, f"Exception: {e}")

        # Test tiger_modify_order with no modifications
        try:
            response = await tiger_modify_order("test-order-id")
            if (
                not response.success
                and "At least one modification parameter" in response.error
            ):
                self.log_result("modify_order_no_params", True, "Proper validation")
            else:
                self.log_result(
                    "modify_order_no_params", False, f"Response: {response}"
                )
        except Exception as e:
            self.log_result("modify_order_no_params", False, f"Exception: {e}")

    async def test_tool_response_structure(self):
        """Test that all tools return properly structured responses."""
        print("\n=== Testing Response Structure ===")

        # All responses should have success field and timestamp
        try:
            response = await tiger_list_accounts()
            if hasattr(response, "success") and hasattr(response, "timestamp"):
                self.log_result(
                    "response_structure_list_accounts", True, "Has required fields"
                )
            else:
                self.log_result(
                    "response_structure_list_accounts", False, "Missing required fields"
                )
        except Exception as e:
            self.log_result(
                "response_structure_list_accounts", False, f"Exception: {e}"
            )

        try:
            response = await tiger_get_positions()
            if hasattr(response, "success") and hasattr(response, "timestamp"):
                self.log_result(
                    "response_structure_get_positions", True, "Has required fields"
                )
            else:
                self.log_result(
                    "response_structure_get_positions", False, "Missing required fields"
                )
        except Exception as e:
            self.log_result(
                "response_structure_get_positions", False, f"Exception: {e}"
            )

    async def run_all_tests(self):
        """Run all tests."""
        print("Starting Tiger MCP Tools Integration Tests...")

        await self.test_account_tools_structure()
        await self.test_trading_tools_structure()
        await self.test_tool_response_structure()

        print(f"\n=== Test Results Summary ===")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Total: {self.passed_tests + self.failed_tests}")

        print(f"\n=== Detailed Results ===")
        for result in self.test_results:
            print(result)

        return self.failed_tests == 0


async def main():
    """Main test function."""
    test_runner = MockTest()
    success = await test_runner.run_all_tests()

    if success:
        print("\nAll tests passed! ✅")
        return 0
    else:
        print(f"\n{test_runner.failed_tests} test(s) failed! ❌")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest runner failed: {e}")
        sys.exit(1)
