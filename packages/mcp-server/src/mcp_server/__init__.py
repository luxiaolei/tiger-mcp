"""FastMCP server for Tiger Brokers API integration."""

__version__ = "0.1.0"

from .cli import main as cli_main
from .config_manager import (
    ConfigManager,
    DatabaseConfig,
    ProcessConfig,
    SecurityConfig,
    ServerConfig,
    TigerConfig,
    TigerMCPConfig,
    get_config,
    get_config_manager,
)

# Import example service
from .example_usage import TigerAPIService
from .main import TigerFastMCPServer, run_sse_server, run_stdio_server
from .process_manager import (
    LoadBalanceStrategy,
    ProcessManager,
    ProcessMetrics,
    get_process_manager,
)

# Import main server components
from .server import TigerMCPServer

# Import process pool components
from .tiger_process_pool import (
    ProcessInfo,
    ProcessStatus,
    TigerProcessPool,
    get_process_pool,
)
from .tiger_worker import TigerWorker

# Import all MCP tools
from .tools import (  # Data tools; Info tools; Account tools; Trading tools
    tiger_add_account,
    tiger_cancel_order,
    tiger_get_account_info,
    tiger_get_account_status,
    tiger_get_contracts,
    tiger_get_corporate_actions,
    tiger_get_earnings,
    tiger_get_financials,
    tiger_get_kline,
    tiger_get_market_data,
    tiger_get_market_status,
    tiger_get_option_chain,
    tiger_get_orders,
    tiger_get_positions,
    tiger_get_quote,
    tiger_list_accounts,
    tiger_modify_order,
    tiger_place_order,
    tiger_refresh_token,
    tiger_remove_account,
    tiger_search_symbols,
    tiger_set_default_data_account,
    tiger_set_default_trading_account,
)

__all__ = [
    # Main server components
    "TigerMCPServer",
    "TigerFastMCPServer",
    "run_stdio_server",
    "run_sse_server",
    "cli_main",
    # Configuration
    "ConfigManager",
    "get_config_manager",
    "get_config",
    "TigerMCPConfig",
    "DatabaseConfig",
    "ProcessConfig",
    "SecurityConfig",
    "ServerConfig",
    "TigerConfig",
    # Process pool components
    "TigerProcessPool",
    "get_process_pool",
    "ProcessStatus",
    "ProcessInfo",
    "ProcessManager",
    "get_process_manager",
    "LoadBalanceStrategy",
    "ProcessMetrics",
    "TigerWorker",
    "TigerAPIService",
    # Data tools
    "tiger_get_quote",
    "tiger_get_kline",
    "tiger_get_market_data",
    "tiger_search_symbols",
    "tiger_get_option_chain",
    "tiger_get_market_status",
    # Info tools
    "tiger_get_contracts",
    "tiger_get_financials",
    "tiger_get_corporate_actions",
    "tiger_get_earnings",
    # Account tools
    "tiger_list_accounts",
    "tiger_add_account",
    "tiger_remove_account",
    "tiger_get_account_status",
    "tiger_refresh_token",
    "tiger_set_default_data_account",
    "tiger_set_default_trading_account",
    # Trading tools
    "tiger_get_positions",
    "tiger_get_account_info",
    "tiger_get_orders",
    "tiger_place_order",
    "tiger_cancel_order",
    "tiger_modify_order",
]
