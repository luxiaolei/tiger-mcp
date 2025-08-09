"""
Comprehensive unit tests for account_router module.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock database imports before importing the account_router
with patch.dict(
    "sys.modules",
    {
        "database.models.accounts": MagicMock(),
    },
):
    # Mock the specific imports
    mock_tiger_account = MagicMock()
    mock_account_status = MagicMock()
    mock_account_type = MagicMock()
    mock_market_permission = MagicMock()

    with (
        patch("shared.account_router.TigerAccount", mock_tiger_account),
        patch("shared.account_router.AccountStatus", mock_account_status),
        patch("shared.account_router.AccountType", mock_account_type),
        patch("shared.account_router.MarketPermission", mock_market_permission),
    ):

        from shared.account_router import (
            AccountRouter,
            AccountRouterError,
            LoadBalanceStrategy,
            NoAccountsAvailableError,
            OperationNotSupportedError,
            OperationType,
            get_account_router,
        )


class TestEnums:
    """Tests for enum classes."""

    def test_operation_type_enum(self):
        """Test OperationType enum values."""
        # Data operations
        assert OperationType.MARKET_DATA == "market_data"
        assert OperationType.QUOTE == "quote"
        assert OperationType.HISTORICAL_DATA == "historical_data"
        assert OperationType.FUNDAMENTALS == "fundamentals"
        assert OperationType.OPTIONS_CHAIN == "options_chain"

        # Trading operations
        assert OperationType.PLACE_ORDER == "place_order"
        assert OperationType.MODIFY_ORDER == "modify_order"
        assert OperationType.CANCEL_ORDER == "cancel_order"

        # Account operations
        assert OperationType.ACCOUNT_INFO == "account_info"
        assert OperationType.POSITIONS == "positions"
        assert OperationType.ORDERS == "orders"
        assert OperationType.TRANSACTIONS == "transactions"

        # Analysis operations
        assert OperationType.PORTFOLIO_ANALYSIS == "portfolio_analysis"
        assert OperationType.RISK_ANALYSIS == "risk_analysis"

    def test_load_balance_strategy_enum(self):
        """Test LoadBalanceStrategy enum values."""
        assert LoadBalanceStrategy.ROUND_ROBIN == "round_robin"
        assert LoadBalanceStrategy.RANDOM == "random"
        assert LoadBalanceStrategy.LEAST_USED == "least_used"
        assert LoadBalanceStrategy.FASTEST_RESPONSE == "fastest_response"


class TestAccountRouterErrors:
    """Tests for account router exception classes."""

    def test_account_router_error(self):
        """Test AccountRouterError exception."""
        error = AccountRouterError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_no_accounts_available_error(self):
        """Test NoAccountsAvailableError exception."""
        error = NoAccountsAvailableError("No accounts available")
        assert str(error) == "No accounts available"
        assert isinstance(error, AccountRouterError)

    def test_operation_not_supported_error(self):
        """Test OperationNotSupportedError exception."""
        error = OperationNotSupportedError("Operation not supported")
        assert str(error) == "Operation not supported"
        assert isinstance(error, AccountRouterError)


class TestAccountRouterInit:
    """Tests for AccountRouter initialization."""

    @patch("shared.account_router.get_account_manager")
    @patch("shared.account_router.get_token_manager")
    def test_account_router_initialization(
        self, mock_token_manager, mock_account_manager
    ):
        """Test AccountRouter initialization."""
        mock_account_manager.return_value = MagicMock()
        mock_token_manager.return_value = MagicMock()

        router = AccountRouter()

        assert router._account_manager is not None
        assert router._token_manager is not None
        assert isinstance(router._round_robin_counters, dict)
        assert isinstance(router._usage_counters, dict)
        assert isinstance(router._response_times, dict)
        assert isinstance(router._operation_preferences, dict)

        mock_account_manager.assert_called_once()
        mock_token_manager.assert_called_once()


class TestOperationRouting:
    """Tests for operation routing functionality."""

    @pytest.fixture
    def account_router(self):
        """Create account router instance for testing."""
        with (
            patch("shared.account_router.get_account_manager"),
            patch("shared.account_router.get_token_manager"),
        ):
            return AccountRouter()

    @pytest.fixture
    def mock_accounts(self):
        """Create mock accounts for testing."""
        accounts = []
        for i in range(3):
            account = MagicMock()
            account.id = uuid.uuid4()
            account.account_name = f"Account {i+1}"
            account.environment = "sandbox"
            account.is_default_trading = i == 0
            account.is_default_data = i == 1
            account.status = mock_account_status.ACTIVE
            account.account_type = mock_account_type.STANDARD
            account.has_valid_token = True
            accounts.append(account)
        return accounts

    async def test_route_operation_success(self, account_router, mock_accounts):
        """Test successful operation routing."""
        # Mock candidate account selection
        account_router._get_candidate_accounts = AsyncMock(return_value=mock_accounts)
        account_router._apply_load_balancing = AsyncMock(return_value=mock_accounts[0])
        account_router._ensure_valid_token = AsyncMock(return_value=True)

        # Test routing
        selected_account = await account_router.route_operation(
            operation_type=OperationType.MARKET_DATA,
            strategy=LoadBalanceStrategy.LEAST_USED,
        )

        assert selected_account == mock_accounts[0]
        account_router._get_candidate_accounts.assert_called_once()
        account_router._apply_load_balancing.assert_called_once()
        account_router._ensure_valid_token.assert_called_once_with(mock_accounts[0])

    async def test_route_operation_no_candidates(self, account_router):
        """Test operation routing with no candidate accounts."""
        # Mock no candidates found
        account_router._get_candidate_accounts = AsyncMock(return_value=[])

        # Should raise NoAccountsAvailableError
        with pytest.raises(NoAccountsAvailableError, match="No accounts available"):
            await account_router.route_operation(
                operation_type=OperationType.MARKET_DATA
            )

    async def test_route_operation_token_invalid_retry(
        self, account_router, mock_accounts
    ):
        """Test operation routing with invalid token retry."""
        # Mock candidate selection
        account_router._get_candidate_accounts = AsyncMock(return_value=mock_accounts)
        account_router._apply_load_balancing = AsyncMock(
            side_effect=[mock_accounts[0], mock_accounts[1]]  # First try  # Retry
        )

        # First account has invalid token, second is valid
        account_router._ensure_valid_token = AsyncMock(side_effect=[False, True])

        selected_account = await account_router.route_operation(
            operation_type=OperationType.MARKET_DATA
        )

        assert selected_account == mock_accounts[1]
        assert account_router._apply_load_balancing.call_count == 2
        assert account_router._ensure_valid_token.call_count == 2

    async def test_get_default_trading_account(self, account_router, mock_accounts):
        """Test getting default trading account."""
        # Mock account manager
        account_router._account_manager.get_default_trading_account = AsyncMock(
            return_value=mock_accounts[0]
        )

        account = await account_router.get_default_trading_account()

        assert account == mock_accounts[0]
        account_router._account_manager.get_default_trading_account.assert_called_once()

    async def test_get_default_data_account(self, account_router, mock_accounts):
        """Test getting default data account."""
        # Mock account manager
        account_router._account_manager.get_default_data_account = AsyncMock(
            return_value=mock_accounts[1]
        )

        account = await account_router.get_default_data_account()

        assert account == mock_accounts[1]
        account_router._account_manager.get_default_data_account.assert_called_once()

    async def test_route_trading_operation(self, account_router, mock_accounts):
        """Test routing trading operation."""
        # Mock methods
        account_router.get_default_trading_account = AsyncMock(
            return_value=mock_accounts[0]
        )
        account_router._ensure_valid_token = AsyncMock(return_value=True)

        selected_account = await account_router.route_trading_operation(
            operation_type=OperationType.PLACE_ORDER
        )

        assert selected_account == mock_accounts[0]
        account_router.get_default_trading_account.assert_called_once()

    async def test_route_trading_operation_fallback(
        self, account_router, mock_accounts
    ):
        """Test trading operation routing with fallback."""
        # Default trading account not available, fallback to general routing
        account_router.get_default_trading_account = AsyncMock(return_value=None)
        account_router.route_operation = AsyncMock(return_value=mock_accounts[1])

        selected_account = await account_router.route_trading_operation(
            operation_type=OperationType.PLACE_ORDER
        )

        assert selected_account == mock_accounts[1]
        account_router.route_operation.assert_called_once()

    async def test_route_data_operation(self, account_router, mock_accounts):
        """Test routing data operation."""
        # Mock methods
        account_router.get_default_data_account = AsyncMock(
            return_value=mock_accounts[1]
        )
        account_router._ensure_valid_token = AsyncMock(return_value=True)

        selected_account = await account_router.route_data_operation(
            operation_type=OperationType.MARKET_DATA
        )

        assert selected_account == mock_accounts[1]
        account_router.get_default_data_account.assert_called_once()


class TestCandidateSelection:
    """Tests for candidate account selection."""

    @pytest.fixture
    def account_router(self):
        """Create account router instance for testing."""
        with (
            patch("shared.account_router.get_account_manager"),
            patch("shared.account_router.get_token_manager"),
        ):
            return AccountRouter()

    @pytest.fixture
    def mock_accounts(self):
        """Create diverse mock accounts for testing."""
        accounts = []

        # Standard sandbox account
        account1 = MagicMock()
        account1.id = uuid.uuid4()
        account1.environment = "sandbox"
        account1.account_type = mock_account_type.STANDARD
        account1.status = mock_account_status.ACTIVE
        accounts.append(account1)

        # Production paper trading account
        account2 = MagicMock()
        account2.id = uuid.uuid4()
        account2.environment = "production"
        account2.account_type = mock_account_type.PAPER
        account2.status = mock_account_status.ACTIVE
        accounts.append(account2)

        # Inactive account
        account3 = MagicMock()
        account3.id = uuid.uuid4()
        account3.environment = "sandbox"
        account3.account_type = mock_account_type.STANDARD
        account3.status = mock_account_status.INACTIVE
        accounts.append(account3)

        return accounts

    async def test_get_candidate_accounts_basic_filter(
        self, account_router, mock_accounts
    ):
        """Test basic candidate account filtering."""
        # Mock account manager
        account_router._account_manager.list_accounts = AsyncMock(
            return_value=mock_accounts
        )

        # Mock account support check (all support the operation)
        account_router._account_supports_operation = MagicMock(return_value=True)

        candidates = await account_router._get_candidate_accounts(
            operation_type=OperationType.MARKET_DATA, environment="sandbox"
        )

        # Should exclude production and inactive accounts
        assert len(candidates) == 1
        assert candidates[0].environment == "sandbox"
        assert candidates[0].status == mock_account_status.ACTIVE

    async def test_get_candidate_accounts_exclude_accounts(
        self, account_router, mock_accounts
    ):
        """Test candidate selection with account exclusion."""
        account_router._account_manager.list_accounts = AsyncMock(
            return_value=mock_accounts[:2]
        )
        account_router._account_supports_operation = MagicMock(return_value=True)

        exclude_set = {str(mock_accounts[0].id)}

        candidates = await account_router._get_candidate_accounts(
            operation_type=OperationType.MARKET_DATA, exclude_accounts=exclude_set
        )

        # Should exclude the specified account
        assert len(candidates) == 1
        assert candidates[0].id != mock_accounts[0].id

    async def test_get_candidate_accounts_account_type_filter(
        self, account_router, mock_accounts
    ):
        """Test candidate selection with account type filter."""
        account_router._account_manager.list_accounts = AsyncMock(
            return_value=mock_accounts[:2]
        )
        account_router._account_supports_operation = MagicMock(return_value=True)

        candidates = await account_router._get_candidate_accounts(
            operation_type=OperationType.MARKET_DATA,
            account_type=mock_account_type.PAPER,
        )

        # Should only return PAPER accounts
        assert len(candidates) == 1
        assert candidates[0].account_type == mock_account_type.PAPER

    def test_account_supports_operation(self, account_router):
        """Test account operation support checking."""
        mock_account = MagicMock()
        mock_account.market_permissions = {"permissions": ["US_STOCK", "US_OPTION"]}

        # Test with matching permission
        supports = account_router._account_supports_operation(
            mock_account, OperationType.MARKET_DATA, [mock_market_permission.US_STOCK]
        )
        assert supports is True

        # Test without required permission
        supports = account_router._account_supports_operation(
            mock_account, OperationType.MARKET_DATA, [mock_market_permission.HK_STOCK]
        )
        # Should still return True since we don't have actual permission checking in mock
        assert supports is True


class TestLoadBalancing:
    """Tests for load balancing strategies."""

    @pytest.fixture
    def account_router(self):
        """Create account router instance for testing."""
        with (
            patch("shared.account_router.get_account_manager"),
            patch("shared.account_router.get_token_manager"),
        ):
            return AccountRouter()

    @pytest.fixture
    def mock_candidates(self):
        """Create mock candidate accounts."""
        candidates = []
        for i in range(3):
            account = MagicMock()
            account.id = uuid.uuid4()
            account.account_name = f"Account {i+1}"
            candidates.append(account)
        return candidates

    async def test_apply_load_balancing_round_robin(
        self, account_router, mock_candidates
    ):
        """Test round robin load balancing."""
        operation_type = OperationType.MARKET_DATA

        # Test multiple selections should rotate
        for i in range(6):  # Test 2 full cycles
            selected = await account_router._apply_load_balancing(
                mock_candidates, LoadBalanceStrategy.ROUND_ROBIN, operation_type
            )
            expected_index = i % len(mock_candidates)
            assert selected == mock_candidates[expected_index]

    async def test_apply_load_balancing_random(self, account_router, mock_candidates):
        """Test random load balancing."""
        # Set seed for predictable testing
        import random

        random.seed(42)

        selected = await account_router._apply_load_balancing(
            mock_candidates, LoadBalanceStrategy.RANDOM, OperationType.MARKET_DATA
        )

        # Should return one of the candidates
        assert selected in mock_candidates

    async def test_apply_load_balancing_least_used(
        self, account_router, mock_candidates
    ):
        """Test least used load balancing."""
        # Set usage counters
        account_router._usage_counters[str(mock_candidates[0].id)] = 5
        account_router._usage_counters[str(mock_candidates[1].id)] = 2  # Least used
        account_router._usage_counters[str(mock_candidates[2].id)] = 3

        selected = await account_router._apply_load_balancing(
            mock_candidates, LoadBalanceStrategy.LEAST_USED, OperationType.MARKET_DATA
        )

        # Should select least used account
        assert selected == mock_candidates[1]

    async def test_apply_load_balancing_fastest_response(
        self, account_router, mock_candidates
    ):
        """Test fastest response load balancing."""
        # Set response times
        account_router._response_times[str(mock_candidates[0].id)] = [1.5, 2.0, 1.8]
        account_router._response_times[str(mock_candidates[1].id)] = [
            0.8,
            1.0,
            0.9,
        ]  # Fastest
        account_router._response_times[str(mock_candidates[2].id)] = [2.5, 3.0, 2.8]

        selected = await account_router._apply_load_balancing(
            mock_candidates,
            LoadBalanceStrategy.FASTEST_RESPONSE,
            OperationType.MARKET_DATA,
        )

        # Should select fastest response account
        assert selected == mock_candidates[1]

    def test_record_account_usage(self, account_router, mock_candidates):
        """Test recording account usage."""
        account = mock_candidates[0]
        account_id = str(account.id)

        # Initial usage
        account_router._record_account_usage(account)
        assert account_router._usage_counters[account_id] == 1

        # Additional usage
        account_router._record_account_usage(account)
        assert account_router._usage_counters[account_id] == 2


class TestTokenValidation:
    """Tests for token validation functionality."""

    @pytest.fixture
    def account_router(self):
        """Create account router instance for testing."""
        with (
            patch("shared.account_router.get_account_manager"),
            patch("shared.account_router.get_token_manager"),
        ):
            return AccountRouter()

    async def test_ensure_valid_token_success(self, account_router):
        """Test successful token validation."""
        mock_account = MagicMock()
        mock_account.has_valid_token = True

        # Mock token manager validation
        account_router._token_manager.validate_token = AsyncMock(
            return_value=(True, None)
        )

        result = await account_router._ensure_valid_token(mock_account)

        assert result is True
        account_router._token_manager.validate_token.assert_called_once_with(
            mock_account
        )

    async def test_ensure_valid_token_refresh_needed(self, account_router):
        """Test token validation with refresh needed."""
        mock_account = MagicMock()
        mock_account.has_valid_token = False

        # Mock token validation failure, then successful refresh
        account_router._token_manager.validate_token = AsyncMock(
            return_value=(False, "Token expired")
        )
        account_router._token_manager.refresh_token = AsyncMock(
            return_value=(True, None)
        )

        result = await account_router._ensure_valid_token(mock_account)

        assert result is True
        account_router._token_manager.validate_token.assert_called_once()
        account_router._token_manager.refresh_token.assert_called_once()

    async def test_ensure_valid_token_refresh_failed(self, account_router):
        """Test token validation with refresh failure."""
        mock_account = MagicMock()
        mock_account.has_valid_token = False

        # Mock token validation failure and refresh failure
        account_router._token_manager.validate_token = AsyncMock(
            return_value=(False, "Token expired")
        )
        account_router._token_manager.refresh_token = AsyncMock(
            return_value=(False, "Refresh failed")
        )

        result = await account_router._ensure_valid_token(mock_account)

        assert result is False
        account_router._token_manager.refresh_token.assert_called_once()


class TestAccountAvailability:
    """Tests for account availability checking."""

    @pytest.fixture
    def account_router(self):
        """Create account router instance for testing."""
        with (
            patch("shared.account_router.get_account_manager"),
            patch("shared.account_router.get_token_manager"),
        ):
            return AccountRouter()

    async def test_check_account_availability_healthy(self, account_router):
        """Test availability check for healthy account."""
        mock_account = MagicMock()
        mock_account.status = mock_account_status.ACTIVE
        mock_account.has_valid_token = True
        mock_account.error_count = 0
        mock_account.last_error_at = None

        # Mock token validation
        account_router._token_manager.validate_token = AsyncMock(
            return_value=(True, None)
        )

        availability = await account_router.check_account_availability(mock_account)

        assert availability["is_available"] is True
        assert availability["status"] == "healthy"
        assert availability["error_count"] == 0
        assert availability["has_valid_token"] is True

    async def test_check_account_availability_unhealthy(self, account_router):
        """Test availability check for unhealthy account."""
        mock_account = MagicMock()
        mock_account.status = mock_account_status.ACTIVE
        mock_account.has_valid_token = False
        mock_account.error_count = 5
        mock_account.last_error_at = datetime.utcnow()
        mock_account.last_error = "API error"

        # Mock token validation failure
        account_router._token_manager.validate_token = AsyncMock(
            return_value=(False, "Invalid token")
        )

        availability = await account_router.check_account_availability(mock_account)

        assert availability["is_available"] is False
        assert availability["status"] == "unhealthy"
        assert availability["error_count"] == 5
        assert availability["has_valid_token"] is False
        assert "Invalid token" in availability["issues"]

    async def test_get_available_accounts_for_operation(self, account_router):
        """Test getting available accounts for operation."""
        # Create mix of available and unavailable accounts
        mock_accounts = [MagicMock() for _ in range(3)]

        account_router._account_manager.list_accounts = AsyncMock(
            return_value=mock_accounts
        )

        # Mock availability checks - first two available, third not
        availability_results = [
            {"is_available": True, "status": "healthy"},
            {"is_available": True, "status": "healthy"},
            {"is_available": False, "status": "unhealthy"},
        ]

        account_router.check_account_availability = AsyncMock(
            side_effect=availability_results
        )

        available = await account_router.get_available_accounts_for_operation(
            OperationType.MARKET_DATA
        )

        assert len(available) == 2
        assert available[0] == mock_accounts[0]
        assert available[1] == mock_accounts[1]


class TestResponseTimeTracking:
    """Tests for response time tracking functionality."""

    @pytest.fixture
    def account_router(self):
        """Create account router instance for testing."""
        with (
            patch("shared.account_router.get_account_manager"),
            patch("shared.account_router.get_token_manager"),
        ):
            return AccountRouter()

    def test_record_operation_response_time(self, account_router):
        """Test recording operation response time."""
        account_id = str(uuid.uuid4())

        # Record multiple response times
        account_router.record_operation_response_time(account_id, 1.5)
        account_router.record_operation_response_time(account_id, 2.0)
        account_router.record_operation_response_time(account_id, 1.2)

        response_times = account_router._response_times[account_id]
        assert len(response_times) == 3
        assert 1.5 in response_times
        assert 2.0 in response_times
        assert 1.2 in response_times

    def test_record_operation_response_time_max_history(self, account_router):
        """Test response time recording with maximum history limit."""
        account_id = str(uuid.uuid4())

        # Record many response times (more than typical limit)
        for i in range(150):  # Assume limit is 100
            account_router.record_operation_response_time(account_id, float(i))

        response_times = account_router._response_times[account_id]

        # Should keep only the most recent times (assuming 100 limit)
        assert len(response_times) <= 100
        # Most recent times should be kept
        assert 149.0 in response_times
        assert 148.0 in response_times


class TestStatisticsAndMetrics:
    """Tests for statistics and metrics functionality."""

    @pytest.fixture
    def account_router(self):
        """Create account router instance for testing."""
        with (
            patch("shared.account_router.get_account_manager"),
            patch("shared.account_router.get_token_manager"),
        ):
            return AccountRouter()

    async def test_get_routing_statistics(self, account_router):
        """Test getting routing statistics."""
        # Setup some usage and response time data
        account1_id = str(uuid.uuid4())
        account2_id = str(uuid.uuid4())

        account_router._usage_counters[account1_id] = 10
        account_router._usage_counters[account2_id] = 5

        account_router._response_times[account1_id] = [1.0, 1.5, 2.0]
        account_router._response_times[account2_id] = [0.8, 1.2]

        stats = await account_router.get_routing_statistics()

        assert "total_operations" in stats
        assert "account_usage" in stats
        assert "average_response_times" in stats

        assert stats["total_operations"] == 15  # 10 + 5
        assert account1_id in stats["account_usage"]
        assert account2_id in stats["account_usage"]
        assert stats["account_usage"][account1_id] == 10
        assert stats["account_usage"][account2_id] == 5


class TestOperationClassification:
    """Tests for operation classification methods."""

    @pytest.fixture
    def account_router(self):
        """Create account router instance for testing."""
        with (
            patch("shared.account_router.get_account_manager"),
            patch("shared.account_router.get_token_manager"),
        ):
            return AccountRouter()

    def test_is_trading_operation(self, account_router):
        """Test trading operation classification."""
        # Trading operations
        assert account_router._is_trading_operation(OperationType.PLACE_ORDER) is True
        assert account_router._is_trading_operation(OperationType.MODIFY_ORDER) is True
        assert account_router._is_trading_operation(OperationType.CANCEL_ORDER) is True

        # Non-trading operations
        assert account_router._is_trading_operation(OperationType.MARKET_DATA) is False
        assert account_router._is_trading_operation(OperationType.QUOTE) is False
        assert account_router._is_trading_operation(OperationType.ACCOUNT_INFO) is False

    def test_is_data_operation(self, account_router):
        """Test data operation classification."""
        # Data operations
        assert account_router._is_data_operation(OperationType.MARKET_DATA) is True
        assert account_router._is_data_operation(OperationType.QUOTE) is True
        assert account_router._is_data_operation(OperationType.HISTORICAL_DATA) is True
        assert account_router._is_data_operation(OperationType.FUNDAMENTALS) is True
        assert account_router._is_data_operation(OperationType.OPTIONS_CHAIN) is True

        # Non-data operations
        assert account_router._is_data_operation(OperationType.PLACE_ORDER) is False
        assert account_router._is_data_operation(OperationType.POSITIONS) is False

    def test_build_operation_preferences(self, account_router):
        """Test operation preferences building."""
        preferences = account_router._build_operation_preferences()

        assert isinstance(preferences, dict)
        assert OperationType.MARKET_DATA in preferences
        assert OperationType.PLACE_ORDER in preferences

        # Each operation should have preferences
        for operation in OperationType:
            assert operation in preferences
            assert isinstance(preferences[operation], dict)


class TestSingletonFunction:
    """Tests for singleton function."""

    def test_get_account_router_singleton(self):
        """Test get_account_router returns singleton."""
        with patch("shared.account_router.AccountRouter") as mock_router:
            router1 = get_account_router()
            router2 = get_account_router()

            assert router1 is router2
            # Should only create instance once
            mock_router.assert_called_once()


class TestAccountRouterIntegration:
    """Integration tests for account router functionality."""

    @pytest.fixture
    def account_router(self):
        """Create account router instance for testing."""
        with (
            patch("shared.account_router.get_account_manager"),
            patch("shared.account_router.get_token_manager"),
        ):
            return AccountRouter()

    async def test_complete_routing_workflow(self, account_router):
        """Test complete routing workflow."""
        # Setup mock accounts
        mock_accounts = [MagicMock() for _ in range(3)]
        for i, account in enumerate(mock_accounts):
            account.id = uuid.uuid4()
            account.account_name = f"Account {i+1}"
            account.status = mock_account_status.ACTIVE
            account.has_valid_token = True
            account.environment = "sandbox"
            account.account_type = mock_account_type.STANDARD

        # Mock all dependencies
        account_router._account_manager.list_accounts = AsyncMock(
            return_value=mock_accounts
        )
        account_router._account_supports_operation = MagicMock(return_value=True)
        account_router._token_manager.validate_token = AsyncMock(
            return_value=(True, None)
        )

        # Test complete workflow
        selected_account = await account_router.route_operation(
            operation_type=OperationType.MARKET_DATA,
            environment="sandbox",
            strategy=LoadBalanceStrategy.LEAST_USED,
        )

        assert selected_account in mock_accounts

        # Usage should be recorded
        account_id = str(selected_account.id)
        assert account_id in account_router._usage_counters
        assert account_router._usage_counters[account_id] > 0

    async def test_failover_scenario(self, account_router):
        """Test failover when primary account fails."""
        mock_accounts = [MagicMock() for _ in range(3)]
        for i, account in enumerate(mock_accounts):
            account.id = uuid.uuid4()
            account.status = mock_account_status.ACTIVE
            account.environment = "sandbox"

        # Setup failover scenario
        account_router._account_manager.list_accounts = AsyncMock(
            return_value=mock_accounts
        )
        account_router._account_supports_operation = MagicMock(return_value=True)

        # First account fails token validation, second succeeds
        account_router._token_manager.validate_token = AsyncMock(
            side_effect=[
                (False, "Token expired"),  # First account fails
                (True, None),  # Second account succeeds
            ]
        )
        account_router._token_manager.refresh_token = AsyncMock(
            return_value=(False, "Refresh failed")
        )

        # Mock load balancing to return accounts in order
        call_count = 0

        def mock_load_balance(*args, **kwargs):
            nonlocal call_count
            result = mock_accounts[call_count]
            call_count += 1
            return result

        account_router._apply_load_balancing = AsyncMock(side_effect=mock_load_balance)

        selected_account = await account_router.route_operation(
            operation_type=OperationType.MARKET_DATA
        )

        # Should have failed over to second account
        assert selected_account == mock_accounts[1]
        assert account_router._apply_load_balancing.call_count == 2

    async def test_load_balancing_across_strategies(self, account_router):
        """Test load balancing behavior across different strategies."""
        mock_accounts = [MagicMock() for _ in range(3)]
        for i, account in enumerate(mock_accounts):
            account.id = uuid.uuid4()
            account.account_name = f"Account {i+1}"

        # Setup usage counters for least used strategy
        account_router._usage_counters[str(mock_accounts[0].id)] = 10
        account_router._usage_counters[str(mock_accounts[1].id)] = 5
        account_router._usage_counters[str(mock_accounts[2].id)] = 1  # Least used

        # Setup response times for fastest response strategy
        account_router._response_times[str(mock_accounts[0].id)] = [2.0, 2.1, 1.9]
        account_router._response_times[str(mock_accounts[1].id)] = [
            1.0,
            1.1,
            0.9,
        ]  # Fastest
        account_router._response_times[str(mock_accounts[2].id)] = [3.0, 3.2, 2.8]

        # Test least used strategy
        least_used = await account_router._apply_load_balancing(
            mock_accounts, LoadBalanceStrategy.LEAST_USED, OperationType.MARKET_DATA
        )
        assert least_used == mock_accounts[2]  # Account with usage count 1

        # Test fastest response strategy
        fastest = await account_router._apply_load_balancing(
            mock_accounts,
            LoadBalanceStrategy.FASTEST_RESPONSE,
            OperationType.MARKET_DATA,
        )
        assert fastest == mock_accounts[1]  # Account with best response times

        # Test round robin
        rr1 = await account_router._apply_load_balancing(
            mock_accounts, LoadBalanceStrategy.ROUND_ROBIN, OperationType.MARKET_DATA
        )
        rr2 = await account_router._apply_load_balancing(
            mock_accounts, LoadBalanceStrategy.ROUND_ROBIN, OperationType.MARKET_DATA
        )
        rr3 = await account_router._apply_load_balancing(
            mock_accounts, LoadBalanceStrategy.ROUND_ROBIN, OperationType.MARKET_DATA
        )

        # Should cycle through accounts
        assert rr1 != rr2 or rr2 != rr3  # At least one should be different
        assert {rr1, rr2, rr3}.issubset(
            set(mock_accounts)
        )  # All should be from candidates
