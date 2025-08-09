"""
Tiger MCP Tools module.

Contains MCP tool implementations for Tiger Brokers API integration.
"""

from .account_tools import (
    tiger_add_account,
    tiger_get_account_status,
    tiger_list_accounts,
    tiger_refresh_token,
    tiger_remove_account,
    tiger_set_default_data_account,
    tiger_set_default_trading_account,
)
from .data_tools import (
    tiger_get_kline,
    tiger_get_market_data,
    tiger_get_market_status,
    tiger_get_option_chain,
    tiger_get_quote,
    tiger_search_symbols,
)
from .info_tools import (
    tiger_get_contracts,
    tiger_get_corporate_actions,
    tiger_get_earnings,
    tiger_get_financials,
)
from .trading_tools import (
    tiger_cancel_order,
    tiger_get_account_info,
    tiger_get_orders,
    tiger_get_positions,
    tiger_modify_order,
    tiger_place_order,
)

__all__ = [
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
