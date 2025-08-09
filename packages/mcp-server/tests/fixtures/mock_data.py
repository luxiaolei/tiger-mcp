"""
Mock data fixtures for Tiger MCP Server tests.

Provides realistic Tiger API response fixtures, account data samples,
market data examples, and error patterns for comprehensive testing.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class MockProcessStatus(Enum):
    """Mock process status for testing."""

    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class MockProcessInfo:
    """Mock process information for testing."""

    process_id: str
    account_id: str
    account_number: str
    pid: Optional[int] = None
    status: MockProcessStatus = MockProcessStatus.READY
    created_at: datetime = None
    last_heartbeat: datetime = None
    error_count: int = 0
    current_task: Optional[str] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.utcnow()


@dataclass
class MockAccount:
    """Mock account for testing."""

    id: str
    account_number: str
    account_name: str
    account_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    encrypted_credentials: bytes


class MockTigerAPIData:
    """Mock Tiger API response data for testing."""

    def __init__(self):
        self.base_timestamp = datetime.utcnow()

    @property
    def quote_response(self) -> Dict[str, Any]:
        """Mock quote response."""
        return {
            "success": True,
            "symbol": "AAPL",
            "data": {
                "symbol": "AAPL",
                "latest_price": 150.25,
                "pre_close": 149.50,
                "change": 0.75,
                "change_rate": 0.005016,
                "volume": 45678900,
                "amount": 6850234500.0,
                "high": 151.20,
                "low": 149.10,
                "open": 149.80,
                "timestamp": int(self.base_timestamp.timestamp()),
                "market_status": "TRADING",
            },
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def quote_error_response(self) -> Dict[str, Any]:
        """Mock quote error response."""
        return {
            "success": False,
            "symbol": "INVALID",
            "data": None,
            "error": "Symbol not found: INVALID",
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def kline_response(self) -> Dict[str, Any]:
        """Mock k-line historical data response."""
        base_time = int(self.base_timestamp.timestamp())
        kline_data = []

        for i in range(10):
            timestamp = base_time - (i * 3600)  # Hourly data
            price_base = 150.0 + (i * 0.5)
            kline_data.append(
                {
                    "time": timestamp,
                    "open": price_base,
                    "high": price_base + 1.5,
                    "low": price_base - 1.2,
                    "close": price_base + 0.3,
                    "volume": 1000000 + (i * 10000),
                }
            )

        return {
            "success": True,
            "symbol": "AAPL",
            "period": "1h",
            "count": len(kline_data),
            "data": kline_data,
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def market_data_response(self) -> Dict[str, Any]:
        """Mock comprehensive market data response."""
        return {
            "success": True,
            "data": {
                "quotes": [
                    {
                        "symbol": "AAPL",
                        "latest_price": 150.25,
                        "change": 0.75,
                        "change_rate": 0.005016,
                        "volume": 45678900,
                    },
                    {
                        "symbol": "GOOGL",
                        "latest_price": 2650.80,
                        "change": -15.40,
                        "change_rate": -0.005778,
                        "volume": 1234567,
                    },
                ],
                "market_status": "TRADING",
                "timestamp": int(self.base_timestamp.timestamp()),
            },
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def symbol_search_response(self) -> Dict[str, Any]:
        """Mock symbol search response."""
        return {
            "success": True,
            "query": "AAPL",
            "data": {
                "symbols": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "market": "US",
                        "currency": "USD",
                        "type": "STOCK",
                        "exchange": "NASDAQ",
                    },
                    {
                        "symbol": "AAPL.O",
                        "name": "Apple Inc. Options",
                        "market": "US",
                        "currency": "USD",
                        "type": "OPTION",
                        "exchange": "NASDAQ",
                    },
                ]
            },
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def option_chain_response(self) -> Dict[str, Any]:
        """Mock option chain response."""
        expiry_date = (self.base_timestamp + timedelta(days=30)).strftime("%Y-%m-%d")

        return {
            "success": True,
            "symbol": "AAPL",
            "data": {
                "expiry_dates": [expiry_date],
                "strikes": [145, 150, 155],
                "options": [
                    {
                        "symbol": "AAPL240215C00150000",
                        "strike": 150.0,
                        "expiry": expiry_date,
                        "type": "CALL",
                        "bid": 2.50,
                        "ask": 2.75,
                        "last": 2.60,
                        "volume": 1500,
                        "open_interest": 45000,
                    },
                    {
                        "symbol": "AAPL240215P00150000",
                        "strike": 150.0,
                        "expiry": expiry_date,
                        "type": "PUT",
                        "bid": 1.80,
                        "ask": 2.05,
                        "last": 1.95,
                        "volume": 800,
                        "open_interest": 35000,
                    },
                ],
            },
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def market_status_response(self) -> Dict[str, Any]:
        """Mock market status response."""
        return {
            "success": True,
            "data": {
                "market": "US",
                "status": "TRADING",
                "open_time": "09:30:00",
                "close_time": "16:00:00",
                "timezone": "America/New_York",
                "next_trading_day": (self.base_timestamp + timedelta(days=1)).strftime(
                    "%Y-%m-%d"
                ),
                "is_trading_day": True,
                "pre_market": {
                    "status": "CLOSED",
                    "open_time": "04:00:00",
                    "close_time": "09:30:00",
                },
                "after_hours": {
                    "status": "PENDING",
                    "open_time": "16:00:00",
                    "close_time": "20:00:00",
                },
            },
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def contracts_response(self) -> Dict[str, Any]:
        """Mock contracts/instruments response."""
        return {
            "success": True,
            "symbol": "AAPL",
            "data": {
                "contracts": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "currency": "USD",
                        "exchange": "NASDAQ",
                        "market": "US",
                        "type": "STOCK",
                        "lot_size": 1,
                        "tick_size": 0.01,
                        "multiplier": 1,
                        "expiry": None,
                        "strike": None,
                        "right": None,
                    }
                ]
            },
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def financials_response(self) -> Dict[str, Any]:
        """Mock financial data response."""
        return {
            "success": True,
            "symbol": "AAPL",
            "data": {
                "financial_data": {
                    "quarter": "Q1 2024",
                    "year": 2024,
                    "revenue": 119575000000,  # $119.57B
                    "net_income": 33916000000,  # $33.92B
                    "eps": 2.18,
                    "pe_ratio": 25.5,
                    "market_cap": 2400000000000,  # $2.4T
                    "debt_to_equity": 1.73,
                    "roe": 0.56,
                    "gross_margin": 0.44,
                },
                "fiscal_period": "quarterly",
            },
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def corporate_actions_response(self) -> Dict[str, Any]:
        """Mock corporate actions response."""
        return {
            "success": True,
            "symbol": "AAPL",
            "data": {
                "corporate_actions": [
                    {
                        "type": "DIVIDEND",
                        "ex_date": "2024-02-09",
                        "pay_date": "2024-02-16",
                        "record_date": "2024-02-12",
                        "amount": 0.24,
                        "currency": "USD",
                        "status": "ANNOUNCED",
                    },
                    {
                        "type": "SPLIT",
                        "ex_date": "2020-08-31",
                        "ratio": "4:1",
                        "status": "EXECUTED",
                    },
                ]
            },
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def earnings_response(self) -> Dict[str, Any]:
        """Mock earnings data response."""
        return {
            "success": True,
            "symbol": "AAPL",
            "data": {
                "earnings": [
                    {
                        "quarter": "Q1 2024",
                        "year": 2024,
                        "announce_date": "2024-02-01",
                        "eps_estimate": 2.10,
                        "eps_actual": 2.18,
                        "eps_surprise": 0.08,
                        "revenue_estimate": 117800000000,
                        "revenue_actual": 119575000000,
                        "status": "ANNOUNCED",
                    },
                    {
                        "quarter": "Q4 2023",
                        "year": 2023,
                        "announce_date": "2023-11-02",
                        "eps_estimate": 1.39,
                        "eps_actual": 1.46,
                        "eps_surprise": 0.07,
                        "revenue_estimate": 89280000000,
                        "revenue_actual": 89498000000,
                        "status": "ANNOUNCED",
                    },
                ]
            },
            "timestamp": self.base_timestamp.isoformat(),
            "account_id": "test_account_123",
        }

    @property
    def positions_response(self) -> Dict[str, Any]:
        """Mock positions response."""
        return {
            "success": True,
            "account_id": "test_account_123",
            "data": {
                "positions": [
                    {
                        "symbol": "AAPL",
                        "quantity": 100,
                        "average_cost": 148.50,
                        "market_value": 15025.00,
                        "unrealized_pnl": 175.00,
                        "realized_pnl": 0.00,
                        "currency": "USD",
                        "position_side": "LONG",
                    },
                    {
                        "symbol": "GOOGL",
                        "quantity": 10,
                        "average_cost": 2680.00,
                        "market_value": 26508.00,
                        "unrealized_pnl": -172.00,
                        "realized_pnl": 0.00,
                        "currency": "USD",
                        "position_side": "LONG",
                    },
                ],
                "total_market_value": 41533.00,
                "total_unrealized_pnl": 3.00,
            },
            "timestamp": self.base_timestamp.isoformat(),
        }

    @property
    def account_info_response(self) -> Dict[str, Any]:
        """Mock account information response."""
        return {
            "success": True,
            "account_id": "test_account_123",
            "data": {
                "account": {
                    "account_number": "DU123456",
                    "account_type": "MARGIN",
                    "currency": "USD",
                    "buying_power": 50000.00,
                    "cash_balance": 25000.00,
                    "market_value": 41533.00,
                    "total_equity": 66533.00,
                    "margin_used": 0.00,
                    "margin_available": 50000.00,
                    "day_trading_buying_power": 100000.00,
                    "maintenance_margin": 0.00,
                }
            },
            "timestamp": self.base_timestamp.isoformat(),
        }

    @property
    def orders_response(self) -> Dict[str, Any]:
        """Mock orders response."""
        return {
            "success": True,
            "account_id": "test_account_123",
            "data": {
                "orders": [
                    {
                        "order_id": "ORD_123456789",
                        "symbol": "AAPL",
                        "action": "BUY",
                        "quantity": 100,
                        "order_type": "LMT",
                        "limit_price": 149.00,
                        "status": "FILLED",
                        "filled_quantity": 100,
                        "avg_fill_price": 149.25,
                        "created_at": self.base_timestamp.isoformat(),
                        "updated_at": self.base_timestamp.isoformat(),
                        "currency": "USD",
                    },
                    {
                        "order_id": "ORD_123456790",
                        "symbol": "MSFT",
                        "action": "BUY",
                        "quantity": 50,
                        "order_type": "MKT",
                        "status": "PENDING_SUBMIT",
                        "filled_quantity": 0,
                        "avg_fill_price": 0.00,
                        "created_at": self.base_timestamp.isoformat(),
                        "updated_at": self.base_timestamp.isoformat(),
                        "currency": "USD",
                    },
                ]
            },
            "timestamp": self.base_timestamp.isoformat(),
        }

    @property
    def place_order_response(self) -> Dict[str, Any]:
        """Mock place order response."""
        return {
            "success": True,
            "account_id": "test_account_123",
            "data": {
                "order": {
                    "order_id": "ORD_"
                    + str(uuid.uuid4()).replace("-", "").upper()[:12],
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "order_type": "LMT",
                    "limit_price": 150.00,
                    "status": "PENDING_SUBMIT",
                    "created_at": self.base_timestamp.isoformat(),
                    "currency": "USD",
                }
            },
            "timestamp": self.base_timestamp.isoformat(),
        }

    @property
    def cancel_order_response(self) -> Dict[str, Any]:
        """Mock cancel order response."""
        return {
            "success": True,
            "account_id": "test_account_123",
            "data": {
                "order_id": "ORD_123456789",
                "status": "CANCELLED",
                "cancelled_at": self.base_timestamp.isoformat(),
            },
            "timestamp": self.base_timestamp.isoformat(),
        }

    @property
    def modify_order_response(self) -> Dict[str, Any]:
        """Mock modify order response."""
        return {
            "success": True,
            "account_id": "test_account_123",
            "data": {
                "order": {
                    "order_id": "ORD_123456789",
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 150,  # Modified quantity
                    "order_type": "LMT",
                    "limit_price": 148.50,  # Modified price
                    "status": "PENDING_SUBMIT",
                    "updated_at": self.base_timestamp.isoformat(),
                    "currency": "USD",
                }
            },
            "timestamp": self.base_timestamp.isoformat(),
        }

    def get_error_response(self, error_type: str = "general") -> Dict[str, Any]:
        """Generate error responses for testing."""
        error_responses = {
            "network": {
                "success": False,
                "error": "Network connection failed",
                "error_code": "NETWORK_ERROR",
                "timestamp": self.base_timestamp.isoformat(),
            },
            "authentication": {
                "success": False,
                "error": "Authentication failed: Invalid token",
                "error_code": "AUTH_ERROR",
                "timestamp": self.base_timestamp.isoformat(),
            },
            "rate_limit": {
                "success": False,
                "error": "Rate limit exceeded",
                "error_code": "RATE_LIMIT",
                "timestamp": self.base_timestamp.isoformat(),
                "retry_after": 60,
            },
            "invalid_symbol": {
                "success": False,
                "error": "Symbol not found",
                "error_code": "INVALID_SYMBOL",
                "timestamp": self.base_timestamp.isoformat(),
            },
            "insufficient_funds": {
                "success": False,
                "error": "Insufficient buying power",
                "error_code": "INSUFFICIENT_FUNDS",
                "timestamp": self.base_timestamp.isoformat(),
            },
            "market_closed": {
                "success": False,
                "error": "Market is closed",
                "error_code": "MARKET_CLOSED",
                "timestamp": self.base_timestamp.isoformat(),
            },
            "general": {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "timestamp": self.base_timestamp.isoformat(),
            },
        }

        return error_responses.get(error_type, error_responses["general"])


class MockAccountData:
    """Mock account data for testing."""

    def __init__(self):
        self.base_time = datetime.utcnow()
        self._accounts = self._create_mock_accounts()

    def _create_mock_accounts(self) -> List[MockAccount]:
        """Create mock account data."""
        accounts = []

        # Main trading account
        accounts.append(
            MockAccount(
                id=str(uuid.uuid4()),
                account_number="DU123456",
                account_name="Main Trading Account",
                account_type="MARGIN",
                status="active",
                created_at=self.base_time - timedelta(days=30),
                updated_at=self.base_time,
                encrypted_credentials=b"encrypted_creds_main",
            )
        )

        # Paper trading account
        accounts.append(
            MockAccount(
                id=str(uuid.uuid4()),
                account_number="DU789012",
                account_name="Paper Trading Account",
                account_type="PAPER",
                status="active",
                created_at=self.base_time - timedelta(days=15),
                updated_at=self.base_time,
                encrypted_credentials=b"encrypted_creds_paper",
            )
        )

        # Inactive account
        accounts.append(
            MockAccount(
                id=str(uuid.uuid4()),
                account_number="DU345678",
                account_name="Inactive Account",
                account_type="CASH",
                status="inactive",
                created_at=self.base_time - timedelta(days=60),
                updated_at=self.base_time - timedelta(days=30),
                encrypted_credentials=b"encrypted_creds_inactive",
            )
        )

        return accounts

    @property
    def accounts(self) -> List[MockAccount]:
        """Get mock accounts."""
        return self._accounts

    @property
    def active_accounts(self) -> List[MockAccount]:
        """Get active mock accounts."""
        return [acc for acc in self._accounts if acc.status == "active"]

    def get_account_by_number(self, account_number: str) -> Optional[MockAccount]:
        """Get account by account number."""
        for account in self._accounts:
            if account.account_number == account_number:
                return account
        return None

    def get_account_by_id(self, account_id: str) -> Optional[MockAccount]:
        """Get account by ID."""
        for account in self._accounts:
            if account.id == account_id:
                return account
        return None


class MockProcessData:
    """Mock process data for testing."""

    def __init__(self):
        self.base_time = datetime.utcnow()
        self.account_data = MockAccountData()
        self._processes = self._create_mock_processes()

    def _create_mock_processes(self) -> List[MockProcessInfo]:
        """Create mock process data."""
        processes = []

        for i, account in enumerate(self.account_data.active_accounts):
            processes.append(
                MockProcessInfo(
                    process_id=f"proc_{i+1}_{str(uuid.uuid4())[:8]}",
                    account_id=account.id,
                    account_number=account.account_number,
                    pid=12345 + i,
                    status=MockProcessStatus.READY,
                    created_at=self.base_time - timedelta(minutes=30 - i * 5),
                    last_heartbeat=self.base_time - timedelta(seconds=i * 10),
                    error_count=i % 2,  # Some with errors
                    memory_usage=45.5 + i * 5.0,
                    cpu_usage=12.3 + i * 2.1,
                )
            )

        return processes

    @property
    def processes(self) -> List[MockProcessInfo]:
        """Get mock processes."""
        return self._processes

    @property
    def healthy_processes(self) -> List[MockProcessInfo]:
        """Get healthy mock processes."""
        return [p for p in self._processes if p.status == MockProcessStatus.READY]

    def get_process_by_account(self, account_id: str) -> Optional[MockProcessInfo]:
        """Get process by account ID."""
        for process in self._processes:
            if process.account_id == account_id:
                return process
        return None


class MockServerData:
    """Mock server data for testing."""

    def __init__(self):
        self.base_time = datetime.utcnow()

    @property
    def health_status(self) -> Dict[str, Any]:
        """Mock server health status."""
        return {
            "server": {
                "started": True,
                "environment": "testing",
                "background_tasks": 3,
                "uptime_seconds": 1800,
            },
            "process_pool": {
                "active_workers": 2,
                "total_requests": 150,
                "failed_requests": 2,
                "success_rate": 0.9867,
            },
            "accounts": {"total_accounts": 3, "active_accounts": 2},
            "database": {
                "status": "connected",
                "pool_size": 5,
                "active_connections": 2,
            },
            "timestamp": self.base_time.isoformat(),
        }

    @property
    def server_info(self) -> Dict[str, Any]:
        """Mock server information."""
        return {
            "name": "Tiger MCP Server",
            "version": "0.1.0",
            "description": "FastMCP server for Tiger Brokers API integration",
            "author": "Tiger MCP Team",
            "license": "MIT",
            "api_version": "1.0",
            "supported_tools": 22,
            "environment": "testing",
            "started_at": (self.base_time - timedelta(minutes=30)).isoformat(),
            "timestamp": self.base_time.isoformat(),
        }

    def get_configuration(self) -> Dict[str, Any]:
        """Mock server configuration."""
        return {
            "server": {"environment": "testing", "log_level": "DEBUG", "port": 8000},
            "database": {"url": "sqlite:///:memory:", "echo": False},
            "process": {
                "min_workers": 1,
                "max_workers": 4,
                "target_workers": 2,
                "startup_timeout": 30.0,
                "shutdown_timeout": 10.0,
                "health_check_interval": 10.0,
            },
            "security": {
                "enable_token_validation": True,
                "token_refresh_threshold": 3600,
                "max_token_age": 86400,
            },
        }
