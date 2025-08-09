"""
Informational Data MCP Tools for Tiger Brokers API.

Provides MCP tools for retrieving contract information, financial data,
corporate actions, and other informational data through the Tiger API process pool.
"""

import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add paths for imports
sys.path.insert(
    0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/shared/src"
)

from fastmcp import FastMCP
from loguru import logger
from pydantic import BaseModel, Field
from shared.account_manager import get_account_manager
from shared.account_router import get_account_router

from ..process_manager import get_process_manager

# Initialize FastMCP instance for info tools
mcp = FastMCP("Tiger Info Tools")


class ContractResponse(BaseModel):
    """Contract details response model."""

    success: bool
    symbols: List[str] = Field(default_factory=list)
    data: Optional[Dict[str, Dict[str, Any]]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    account_id: Optional[str] = None


class FinancialResponse(BaseModel):
    """Financial data response model."""

    success: bool
    symbol: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    account_id: Optional[str] = None


class CorporateActionsResponse(BaseModel):
    """Corporate actions response model."""

    success: bool
    symbol: str = ""
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    account_id: Optional[str] = None


class EarningsResponse(BaseModel):
    """Earnings data response model."""

    success: bool
    symbol: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    account_id: Optional[str] = None


# Service instance for account routing
class InfoToolsService:
    """Service class for info tools with account routing."""

    def __init__(self):
        self.process_manager = get_process_manager()
        self.account_manager = get_account_manager()
        self.account_router = get_account_router()

    async def _route_account(
        self,
        account_id: Optional[str],
        use_default: bool = True,
        operation_type: str = "data",
    ) -> str:
        """Route request to appropriate account."""
        if account_id:
            # Use specified account
            return account_id
        elif use_default:
            # Use default data account
            default_account = await self.account_manager.get_default_account("data")
            if default_account:
                return default_account.account_number
            else:
                # Fallback to account router
                return await self.account_router.get_account_for_operation(
                    operation_type
                )
        else:
            # Use account router
            return await self.account_router.get_account_for_operation(operation_type)

    async def ensure_started(self):
        """Ensure the process manager is started."""
        if (
            not hasattr(self.process_manager, "_started")
            or not self.process_manager._started
        ):
            await self.process_manager.start()


# Global service instance
_info_service = InfoToolsService()


@mcp.tool()
async def tiger_get_contracts(
    symbols: List[str], data_account_id: Optional[str] = None
) -> ContractResponse:
    """
    Get detailed contract information for symbols.

    Retrieves comprehensive contract details including security type,
    exchange, currency, lot size, and other trading specifications
    needed for order placement and analysis.

    Args:
        symbols: List of symbols to get contract details for
                (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        data_account_id: Optional specific data account ID to use.
                        If not provided, uses default data account or router.

    Returns:
        ContractResponse containing contract details for each symbol:
        - symbol: Trading symbol
        - sec_type: Security type (STK, ETF, OPT, FUT, etc.)
        - exchange: Primary exchange
        - currency: Trading currency
        - lot_size: Minimum lot size for trading
        - multiplier: Contract multiplier (for derivatives)
        - tick_size: Minimum price increment
        - name: Full security name
        - local_symbol: Local exchange symbol (if different)

    Example:
        ```python
        # Get contract details for major stocks
        response = await tiger_get_contracts(['AAPL', 'TSLA', 'SPY'])
        if response.success:
            for symbol, contract in response.data.items():
                print(f"{symbol}: {contract['sec_type']} on {contract['exchange']}")
                print(f"  Lot Size: {contract['lot_size']}, Currency: {contract['currency']}")
        ```
    """
    try:
        await _info_service.ensure_started()

        # Limit symbols for performance
        symbols = symbols[:20]  # Limit to 20 symbols

        # Route to appropriate account
        target_account_id = await _info_service._route_account(
            data_account_id, True, "data"
        )

        # Execute contract details API call
        result = await _info_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="quote.get_contract_details",
            kwargs={"symbols": symbols},
            timeout=15.0,
        )

        # Process contract details
        contract_data = {}
        if result:
            for contract in result:
                symbol = contract.symbol if hasattr(contract, "symbol") else ""

                contract_info = {
                    "symbol": symbol,
                    "sec_type": (
                        contract.sec_type if hasattr(contract, "sec_type") else "STK"
                    ),
                    "exchange": (
                        contract.exchange if hasattr(contract, "exchange") else ""
                    ),
                    "currency": (
                        contract.currency if hasattr(contract, "currency") else "USD"
                    ),
                    "name": contract.name if hasattr(contract, "name") else "",
                    "local_symbol": (
                        contract.local_symbol
                        if hasattr(contract, "local_symbol")
                        else symbol
                    ),
                    "lot_size": (
                        contract.lot_size if hasattr(contract, "lot_size") else 1
                    ),
                    "multiplier": (
                        contract.multiplier if hasattr(contract, "multiplier") else 1
                    ),
                    "tick_size": (
                        contract.tick_size if hasattr(contract, "tick_size") else 0.01
                    ),
                    "market": contract.market if hasattr(contract, "market") else "",
                    "expiry": contract.expiry if hasattr(contract, "expiry") else None,
                    "strike": contract.strike if hasattr(contract, "strike") else None,
                    "right": contract.right if hasattr(contract, "right") else None,
                }

                contract_data[symbol] = contract_info

        return ContractResponse(
            success=True,
            symbols=symbols,
            data=contract_data,
            account_id=target_account_id,
        )

    except Exception as e:
        logger.error(f"Failed to get contract details for {symbols}: {e}")
        return ContractResponse(success=False, symbols=symbols, error=str(e))


@mcp.tool()
async def tiger_get_financials(
    symbol: str, data_account_id: Optional[str] = None
) -> FinancialResponse:
    """
    Get financial data and key metrics for a symbol.

    Retrieves fundamental financial information including balance sheet,
    income statement, cash flow data, and key financial ratios useful
    for investment analysis and valuation.

    Args:
        symbol: Stock symbol to get financial data for (e.g., 'AAPL', 'MSFT')
        data_account_id: Optional specific data account ID to use.
                        If not provided, uses default data account or router.

    Returns:
        FinancialResponse containing financial data:
        - market_cap: Market capitalization
        - pe_ratio: Price-to-earnings ratio
        - pb_ratio: Price-to-book ratio
        - dividend_yield: Annual dividend yield percentage
        - revenue: Latest annual revenue
        - net_income: Latest annual net income
        - total_assets: Total assets from balance sheet
        - total_debt: Total debt outstanding
        - cash_and_equivalents: Cash and short-term investments
        - shares_outstanding: Total shares outstanding
        - eps: Earnings per share
        - book_value_per_share: Book value per share

    Example:
        ```python
        # Get Apple's financial metrics
        response = await tiger_get_financials("AAPL")
        if response.success:
            financials = response.data
            print(f"Market Cap: ${financials['market_cap']:,.0f}")
            print(f"P/E Ratio: {financials['pe_ratio']:.2f}")
            print(f"Dividend Yield: {financials['dividend_yield']:.2f}%")
        ```
    """
    try:
        await _info_service.ensure_started()

        # Route to appropriate account
        target_account_id = await _info_service._route_account(
            data_account_id, True, "data"
        )

        # Execute financial data API call
        result = await _info_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="quote.get_financial_data",
            kwargs={"symbol": symbol},
            timeout=10.0,
        )

        # Process financial data
        financial_data = None
        if result:
            financial_data = {
                "symbol": symbol,
                "market_cap": result.market_cap if hasattr(result, "market_cap") else 0,
                "pe_ratio": result.pe_ratio if hasattr(result, "pe_ratio") else 0,
                "pb_ratio": result.pb_ratio if hasattr(result, "pb_ratio") else 0,
                "ps_ratio": result.ps_ratio if hasattr(result, "ps_ratio") else 0,
                "dividend_yield": (
                    result.dividend_yield if hasattr(result, "dividend_yield") else 0
                ),
                "dividend_per_share": (
                    result.dividend_per_share
                    if hasattr(result, "dividend_per_share")
                    else 0
                ),
                "revenue": result.revenue if hasattr(result, "revenue") else 0,
                "net_income": result.net_income if hasattr(result, "net_income") else 0,
                "total_assets": (
                    result.total_assets if hasattr(result, "total_assets") else 0
                ),
                "total_debt": result.total_debt if hasattr(result, "total_debt") else 0,
                "cash_and_equivalents": (
                    result.cash_and_equivalents
                    if hasattr(result, "cash_and_equivalents")
                    else 0
                ),
                "shares_outstanding": (
                    result.shares_outstanding
                    if hasattr(result, "shares_outstanding")
                    else 0
                ),
                "eps": result.eps if hasattr(result, "eps") else 0,
                "book_value_per_share": (
                    result.book_value_per_share
                    if hasattr(result, "book_value_per_share")
                    else 0
                ),
                "return_on_equity": (
                    result.return_on_equity
                    if hasattr(result, "return_on_equity")
                    else 0
                ),
                "return_on_assets": (
                    result.return_on_assets
                    if hasattr(result, "return_on_assets")
                    else 0
                ),
                "profit_margin": (
                    result.profit_margin if hasattr(result, "profit_margin") else 0
                ),
                "operating_margin": (
                    result.operating_margin
                    if hasattr(result, "operating_margin")
                    else 0
                ),
                "gross_margin": (
                    result.gross_margin if hasattr(result, "gross_margin") else 0
                ),
                "debt_to_equity": (
                    result.debt_to_equity if hasattr(result, "debt_to_equity") else 0
                ),
                "current_ratio": (
                    result.current_ratio if hasattr(result, "current_ratio") else 0
                ),
                "quick_ratio": (
                    result.quick_ratio if hasattr(result, "quick_ratio") else 0
                ),
                "beta": result.beta if hasattr(result, "beta") else 0,
                "52_week_high": (
                    result.high_52_week if hasattr(result, "high_52_week") else 0
                ),
                "52_week_low": (
                    result.low_52_week if hasattr(result, "low_52_week") else 0
                ),
            }

        return FinancialResponse(
            success=True,
            symbol=symbol,
            data=financial_data,
            account_id=target_account_id,
        )

    except Exception as e:
        logger.error(f"Failed to get financial data for {symbol}: {e}")
        return FinancialResponse(success=False, symbol=symbol, error=str(e))


@mcp.tool()
async def tiger_get_corporate_actions(
    symbol: str, data_account_id: Optional[str] = None
) -> CorporateActionsResponse:
    """
    Get corporate actions data for a symbol.

    Retrieves information about corporate events that affect shareholders
    such as dividends, stock splits, mergers, spin-offs, and other
    corporate actions that may impact trading and valuation.

    Args:
        symbol: Stock symbol to get corporate actions for (e.g., 'AAPL', 'MSFT')
        data_account_id: Optional specific data account ID to use.
                        If not provided, uses default data account or router.

    Returns:
        CorporateActionsResponse containing list of corporate actions:
        Each action includes:
        - action_type: Type of corporate action (DIVIDEND, SPLIT, MERGER, etc.)
        - ex_date: Ex-dividend or ex-action date
        - record_date: Record date for shareholder eligibility
        - payment_date: Payment or effective date
        - amount: Dividend amount or split ratio
        - currency: Currency of the action
        - description: Human-readable description
        - status: Status of the corporate action

    Example:
        ```python
        # Get Apple's recent corporate actions
        response = await tiger_get_corporate_actions("AAPL")
        if response.success:
            for action in response.data:
                if action['action_type'] == 'DIVIDEND':
                    print(f"Dividend: ${action['amount']} ex-date: {action['ex_date']}")
                elif action['action_type'] == 'SPLIT':
                    print(f"Stock Split: {action['amount']} effective: {action['ex_date']}")
        ```
    """
    try:
        await _info_service.ensure_started()

        # Route to appropriate account
        target_account_id = await _info_service._route_account(
            data_account_id, True, "data"
        )

        # Execute corporate actions API call
        result = await _info_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="quote.get_corporate_actions",
            kwargs={"symbol": symbol},
            timeout=10.0,
        )

        # Process corporate actions data
        actions_data = []
        if result:
            for action in result:
                action_info = {
                    "symbol": symbol,
                    "action_type": (
                        action.action_type if hasattr(action, "action_type") else ""
                    ),
                    "ex_date": action.ex_date if hasattr(action, "ex_date") else None,
                    "record_date": (
                        action.record_date if hasattr(action, "record_date") else None
                    ),
                    "payment_date": (
                        action.payment_date if hasattr(action, "payment_date") else None
                    ),
                    "effective_date": (
                        action.effective_date
                        if hasattr(action, "effective_date")
                        else None
                    ),
                    "amount": action.amount if hasattr(action, "amount") else 0,
                    "currency": (
                        action.currency if hasattr(action, "currency") else "USD"
                    ),
                    "description": (
                        action.description if hasattr(action, "description") else ""
                    ),
                    "status": action.status if hasattr(action, "status") else "UNKNOWN",
                    "ratio_from": (
                        action.ratio_from if hasattr(action, "ratio_from") else None
                    ),
                    "ratio_to": (
                        action.ratio_to if hasattr(action, "ratio_to") else None
                    ),
                    "announcement_date": (
                        action.announcement_date
                        if hasattr(action, "announcement_date")
                        else None
                    ),
                }
                actions_data.append(action_info)

        return CorporateActionsResponse(
            success=True, symbol=symbol, data=actions_data, account_id=target_account_id
        )

    except Exception as e:
        logger.error(f"Failed to get corporate actions for {symbol}: {e}")
        return CorporateActionsResponse(success=False, symbol=symbol, error=str(e))


@mcp.tool()
async def tiger_get_earnings(
    symbol: str, data_account_id: Optional[str] = None
) -> EarningsResponse:
    """
    Get earnings data and estimates for a symbol.

    Retrieves earnings reports, analyst estimates, and earnings-related
    information useful for investment analysis and earnings season tracking.

    Args:
        symbol: Stock symbol to get earnings data for (e.g., 'AAPL', 'MSFT')
        data_account_id: Optional specific data account ID to use.
                        If not provided, uses default data account or router.

    Returns:
        EarningsResponse containing earnings information:
        - last_reported_eps: Most recent reported earnings per share
        - last_report_date: Date of last earnings report
        - next_report_date: Expected date of next earnings report
        - estimated_eps: Analyst consensus EPS estimate for next quarter
        - revenue_estimate: Analyst consensus revenue estimate
        - earnings_surprise: Last quarter's earnings surprise (actual vs estimate)
        - revenue_surprise: Last quarter's revenue surprise
        - annual_eps: Annual earnings per share (trailing twelve months)
        - quarterly_growth: Quarterly earnings growth rate
        - annual_growth: Annual earnings growth rate

    Example:
        ```python
        # Get Apple's earnings information
        response = await tiger_get_earnings("AAPL")
        if response.success:
            earnings = response.data
            print(f"Last EPS: ${earnings['last_reported_eps']:.2f}")
            print(f"Next Report: {earnings['next_report_date']}")
            print(f"Estimated EPS: ${earnings['estimated_eps']:.2f}")
            if earnings['earnings_surprise'] > 0:
                print(f"Beat estimates by ${earnings['earnings_surprise']:.2f}")
        ```
    """
    try:
        await _info_service.ensure_started()

        # Route to appropriate account
        target_account_id = await _info_service._route_account(
            data_account_id, True, "data"
        )

        # Execute earnings data API call
        result = await _info_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="quote.get_earnings_data",
            kwargs={"symbol": symbol},
            timeout=10.0,
        )

        # Process earnings data
        earnings_data = None
        if result:
            earnings_data = {
                "symbol": symbol,
                "last_reported_eps": (
                    result.last_reported_eps
                    if hasattr(result, "last_reported_eps")
                    else 0
                ),
                "last_report_date": (
                    result.last_report_date
                    if hasattr(result, "last_report_date")
                    else None
                ),
                "next_report_date": (
                    result.next_report_date
                    if hasattr(result, "next_report_date")
                    else None
                ),
                "estimated_eps": (
                    result.estimated_eps if hasattr(result, "estimated_eps") else 0
                ),
                "revenue_estimate": (
                    result.revenue_estimate
                    if hasattr(result, "revenue_estimate")
                    else 0
                ),
                "earnings_surprise": (
                    result.earnings_surprise
                    if hasattr(result, "earnings_surprise")
                    else 0
                ),
                "revenue_surprise": (
                    result.revenue_surprise
                    if hasattr(result, "revenue_surprise")
                    else 0
                ),
                "surprise_percentage": (
                    result.surprise_percentage
                    if hasattr(result, "surprise_percentage")
                    else 0
                ),
                "annual_eps": result.annual_eps if hasattr(result, "annual_eps") else 0,
                "quarterly_growth": (
                    result.quarterly_growth
                    if hasattr(result, "quarterly_growth")
                    else 0
                ),
                "annual_growth": (
                    result.annual_growth if hasattr(result, "annual_growth") else 0
                ),
                "consensus_rating": (
                    result.consensus_rating
                    if hasattr(result, "consensus_rating")
                    else ""
                ),
                "analyst_count": (
                    result.analyst_count if hasattr(result, "analyst_count") else 0
                ),
                "eps_revisions_up": (
                    result.eps_revisions_up
                    if hasattr(result, "eps_revisions_up")
                    else 0
                ),
                "eps_revisions_down": (
                    result.eps_revisions_down
                    if hasattr(result, "eps_revisions_down")
                    else 0
                ),
                "high_estimate": (
                    result.high_estimate if hasattr(result, "high_estimate") else 0
                ),
                "low_estimate": (
                    result.low_estimate if hasattr(result, "low_estimate") else 0
                ),
                "fiscal_year_end": (
                    result.fiscal_year_end
                    if hasattr(result, "fiscal_year_end")
                    else None
                ),
                "earnings_time": (
                    result.earnings_time if hasattr(result, "earnings_time") else ""
                ),  # BMO, AMC, etc.
            }

        return EarningsResponse(
            success=True,
            symbol=symbol,
            data=earnings_data,
            account_id=target_account_id,
        )

    except Exception as e:
        logger.error(f"Failed to get earnings data for {symbol}: {e}")
        return EarningsResponse(success=False, symbol=symbol, error=str(e))
