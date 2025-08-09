"""
Market Data MCP Tools for Tiger Brokers API.

Provides MCP tools for retrieving market data, quotes, historical data,
and other market-related information through the Tiger API process pool.
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

# Initialize FastMCP instance for data tools
mcp = FastMCP("Tiger Data Tools")


class QuoteResponse(BaseModel):
    """Quote response model."""

    success: bool
    symbol: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    account_id: Optional[str] = None


class KlineResponse(BaseModel):
    """K-line historical data response model."""

    success: bool
    symbol: str = ""
    period: str = ""
    count: int = 0
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    account_id: Optional[str] = None


class MarketDataResponse(BaseModel):
    """Batch market data response model."""

    success: bool
    symbols: List[str] = Field(default_factory=list)
    fields: List[str] = Field(default_factory=list)
    data: Optional[Dict[str, Dict[str, Any]]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    account_id: Optional[str] = None


class SymbolSearchResponse(BaseModel):
    """Symbol search response model."""

    success: bool
    keyword: str = ""
    market: str = ""
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    account_id: Optional[str] = None


class OptionChainResponse(BaseModel):
    """Option chain response model."""

    success: bool
    symbol: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    account_id: Optional[str] = None


class MarketStatusResponse(BaseModel):
    """Market status response model."""

    success: bool
    market: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    account_id: Optional[str] = None


# Service instance for account routing
class DataToolsService:
    """Service class for data tools with account routing."""

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
_data_service = DataToolsService()


@mcp.tool()
async def tiger_get_quote(
    symbol: str, data_account_id: Optional[str] = None
) -> QuoteResponse:
    """
    Get real-time quote for a symbol.

    Retrieves current market data including bid/ask prices, last trade,
    volume, and other real-time market information for a specified symbol.

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA', 'SPY')
        data_account_id: Optional specific data account ID to use.
                        If not provided, uses default data account or router.

    Returns:
        QuoteResponse containing quote data with fields like:
        - latest_price: Current trading price
        - bid_price: Best bid price
        - ask_price: Best ask price
        - bid_size: Size at bid
        - ask_size: Size at ask
        - volume: Trading volume
        - prev_close: Previous close price
        - change: Price change from previous close
        - change_rate: Percentage change rate

    Example:
        ```python
        response = await tiger_get_quote("AAPL")
        if response.success:
            price = response.data["latest_price"]
            print(f"AAPL current price: ${price}")
        ```
    """
    try:
        await _data_service.ensure_started()

        # Route to appropriate account
        target_account_id = await _data_service._route_account(
            data_account_id, True, "data"
        )

        # Execute API call
        result = await _data_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="quote.get_stock_brief",
            kwargs={"symbols": [symbol]},
            timeout=10.0,
        )

        # Process single symbol result
        quote_data = None
        if result and len(result) > 0:
            brief = result[0]
            quote_data = {
                "symbol": brief.symbol if hasattr(brief, "symbol") else symbol,
                "latest_price": (
                    brief.latest_price if hasattr(brief, "latest_price") else 0
                ),
                "bid_price": brief.bid_price if hasattr(brief, "bid_price") else 0,
                "ask_price": brief.ask_price if hasattr(brief, "ask_price") else 0,
                "bid_size": brief.bid_size if hasattr(brief, "bid_size") else 0,
                "ask_size": brief.ask_size if hasattr(brief, "ask_size") else 0,
                "volume": brief.volume if hasattr(brief, "volume") else 0,
                "prev_close": brief.prev_close if hasattr(brief, "prev_close") else 0,
                "open": brief.open if hasattr(brief, "open") else 0,
                "high": brief.high if hasattr(brief, "high") else 0,
                "low": brief.low if hasattr(brief, "low") else 0,
                "change": brief.change if hasattr(brief, "change") else 0,
                "change_rate": (
                    brief.change_rate if hasattr(brief, "change_rate") else 0
                ),
                "latest_time": (
                    brief.latest_time if hasattr(brief, "latest_time") else None
                ),
            }

        return QuoteResponse(
            success=True, symbol=symbol, data=quote_data, account_id=target_account_id
        )

    except Exception as e:
        logger.error(f"Failed to get quote for {symbol}: {e}")
        return QuoteResponse(success=False, symbol=symbol, error=str(e))


@mcp.tool()
async def tiger_get_kline(
    symbol: str,
    period: str = "1d",
    count: int = 100,
    data_account_id: Optional[str] = None,
) -> KlineResponse:
    """
    Get historical K-line (candlestick) data for a symbol.

    Retrieves historical price data including OHLCV (Open, High, Low, Close, Volume)
    for technical analysis and charting purposes.

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA', 'SPY')
        period: Time period for each candlestick. Options:
                - '1m', '5m', '15m', '30m' (minutes)
                - '1h', '2h', '4h' (hours)
                - '1d', '1w' (days/weeks)
                - '1M' (months)
        count: Number of data points to retrieve (max 300)
        data_account_id: Optional specific data account ID to use.
                        If not provided, uses default data account or router.

    Returns:
        KlineResponse containing historical data with each bar containing:
        - time: Timestamp of the bar
        - open: Opening price
        - high: Highest price
        - low: Lowest price
        - close: Closing price
        - volume: Trading volume

    Example:
        ```python
        # Get daily data for last 30 days
        response = await tiger_get_kline("AAPL", "1d", 30)
        if response.success:
            for bar in response.data:
                print(f"{bar['time']}: O={bar['open']} H={bar['high']} L={bar['low']} C={bar['close']}")
        ```
    """
    try:
        await _data_service.ensure_started()

        # Validate count limit
        count = min(count, 300)

        # Route to appropriate account
        target_account_id = await _data_service._route_account(
            data_account_id, True, "data"
        )

        # Execute API call
        result = await _data_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="quote.get_bars",
            kwargs={"symbol": symbol, "period": period, "limit": count},
            timeout=15.0,
        )

        # Process k-line data
        kline_data = []
        if result:
            for bar in result:
                bar_data = {
                    "time": bar.time if hasattr(bar, "time") else None,
                    "open": bar.open if hasattr(bar, "open") else 0,
                    "high": bar.high if hasattr(bar, "high") else 0,
                    "low": bar.low if hasattr(bar, "low") else 0,
                    "close": bar.close if hasattr(bar, "close") else 0,
                    "volume": bar.volume if hasattr(bar, "volume") else 0,
                }
                kline_data.append(bar_data)

        return KlineResponse(
            success=True,
            symbol=symbol,
            period=period,
            count=len(kline_data),
            data=kline_data,
            account_id=target_account_id,
        )

    except Exception as e:
        logger.error(f"Failed to get k-line data for {symbol}: {e}")
        return KlineResponse(
            success=False, symbol=symbol, period=period, count=count, error=str(e)
        )


@mcp.tool()
async def tiger_get_market_data(
    symbols: List[str],
    fields: Optional[List[str]] = None,
    data_account_id: Optional[str] = None,
) -> MarketDataResponse:
    """
    Get batch market data for multiple symbols.

    Efficiently retrieves market data for multiple symbols in a single request,
    useful for portfolio monitoring or market scanning applications.

    Args:
        symbols: List of stock symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        fields: Optional list of specific fields to retrieve. If not provided,
               returns all available fields. Common fields include:
               - 'latest_price', 'volume', 'change', 'change_rate'
               - 'bid_price', 'ask_price', 'high', 'low', 'open'
        data_account_id: Optional specific data account ID to use.
                        If not provided, uses default data account or router.

    Returns:
        MarketDataResponse containing market data organized by symbol.
        Each symbol entry contains the requested fields with current values.

    Example:
        ```python
        # Get basic data for tech stocks
        response = await tiger_get_market_data(['AAPL', 'MSFT', 'GOOGL'])
        if response.success:
            for symbol, data in response.data.items():
                print(f"{symbol}: ${data['latest_price']} ({data['change_rate']:.2f}%)")
        ```
    """
    try:
        await _data_service.ensure_started()

        # Limit symbols for performance
        symbols = symbols[:50]  # Limit to 50 symbols

        # Route to appropriate account
        target_account_id = await _data_service._route_account(
            data_account_id, True, "data"
        )

        # Execute API call for stock briefs
        result = await _data_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="quote.get_stock_briefs",
            kwargs={"symbols": symbols},
            timeout=15.0,
        )

        # Process batch market data
        market_data = {}
        if result:
            for brief in result:
                symbol = brief.symbol if hasattr(brief, "symbol") else ""

                # Extract all available fields
                symbol_data = {
                    "symbol": symbol,
                    "latest_price": (
                        brief.latest_price if hasattr(brief, "latest_price") else 0
                    ),
                    "bid_price": brief.bid_price if hasattr(brief, "bid_price") else 0,
                    "ask_price": brief.ask_price if hasattr(brief, "ask_price") else 0,
                    "volume": brief.volume if hasattr(brief, "volume") else 0,
                    "prev_close": (
                        brief.prev_close if hasattr(brief, "prev_close") else 0
                    ),
                    "open": brief.open if hasattr(brief, "open") else 0,
                    "high": brief.high if hasattr(brief, "high") else 0,
                    "low": brief.low if hasattr(brief, "low") else 0,
                    "change": brief.change if hasattr(brief, "change") else 0,
                    "change_rate": (
                        brief.change_rate if hasattr(brief, "change_rate") else 0
                    ),
                    "latest_time": (
                        brief.latest_time if hasattr(brief, "latest_time") else None
                    ),
                }

                # Filter fields if specified
                if fields:
                    symbol_data = {
                        field: symbol_data.get(field)
                        for field in fields
                        if field in symbol_data
                    }

                market_data[symbol] = symbol_data

        return MarketDataResponse(
            success=True,
            symbols=symbols,
            fields=fields or [],
            data=market_data,
            account_id=target_account_id,
        )

    except Exception as e:
        logger.error(f"Failed to get batch market data: {e}")
        return MarketDataResponse(
            success=False, symbols=symbols, fields=fields or [], error=str(e)
        )


@mcp.tool()
async def tiger_search_symbols(
    keyword: str, market: str = "US", data_account_id: Optional[str] = None
) -> SymbolSearchResponse:
    """
    Search for symbols by keyword.

    Find stock symbols matching a keyword, useful for symbol discovery
    and autocomplete functionality. Searches company names, symbols,
    and other identifying information.

    Args:
        keyword: Search term (company name, symbol, or partial match)
                Examples: 'Apple', 'AAPL', 'tesla', 'tech'
        market: Market to search in. Options:
               - 'US': United States markets (NYSE, NASDAQ)
               - 'HK': Hong Kong market
               - 'SG': Singapore market
               - 'CN': China markets (A-shares)
        data_account_id: Optional specific data account ID to use.
                        If not provided, uses default data account or router.

    Returns:
        SymbolSearchResponse containing matching symbols with details:
        - symbol: Trading symbol
        - name: Company/security name
        - market: Market exchange
        - sec_type: Security type (STK, ETF, etc.)
        - currency: Trading currency

    Example:
        ```python
        # Search for Apple-related symbols
        response = await tiger_search_symbols("apple", "US")
        if response.success:
            for result in response.data:
                print(f"{result['symbol']}: {result['name']} ({result['market']})")
        ```
    """
    try:
        await _data_service.ensure_started()

        # Route to appropriate account
        target_account_id = await _data_service._route_account(
            data_account_id, True, "data"
        )

        # Execute symbol search API call
        result = await _data_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="quote.search_symbols",
            kwargs={"keyword": keyword, "market": market},
            timeout=10.0,
        )

        # Process search results
        search_results = []
        if result:
            for item in result:
                result_data = {
                    "symbol": item.symbol if hasattr(item, "symbol") else "",
                    "name": item.name if hasattr(item, "name") else "",
                    "market": item.market if hasattr(item, "market") else market,
                    "sec_type": item.sec_type if hasattr(item, "sec_type") else "STK",
                    "currency": item.currency if hasattr(item, "currency") else "USD",
                    "exchange": item.exchange if hasattr(item, "exchange") else "",
                    "exp_date": item.exp_date if hasattr(item, "exp_date") else None,
                }
                search_results.append(result_data)

        return SymbolSearchResponse(
            success=True,
            keyword=keyword,
            market=market,
            data=search_results,
            account_id=target_account_id,
        )

    except Exception as e:
        logger.error(f"Failed to search symbols for keyword '{keyword}': {e}")
        return SymbolSearchResponse(
            success=False, keyword=keyword, market=market, error=str(e)
        )


@mcp.tool()
async def tiger_get_option_chain(
    symbol: str, data_account_id: Optional[str] = None
) -> OptionChainResponse:
    """
    Get option chain data for a symbol.

    Retrieves option contracts available for a given underlying symbol,
    including calls and puts with various expiration dates and strike prices.

    Args:
        symbol: Underlying stock symbol (e.g., 'AAPL', 'SPY', 'QQQ')
        data_account_id: Optional specific data account ID to use.
                        If not provided, uses default data account or router.

    Returns:
        OptionChainResponse containing option chain data:
        - calls: List of call options with strike, expiry, bid, ask, etc.
        - puts: List of put options with strike, expiry, bid, ask, etc.
        - underlying_price: Current price of underlying stock
        - expiration_dates: Available expiration dates

    Example:
        ```python
        # Get AAPL option chain
        response = await tiger_get_option_chain("AAPL")
        if response.success:
            calls = response.data["calls"]
            puts = response.data["puts"]
            print(f"Found {len(calls)} calls and {len(puts)} puts")
        ```
    """
    try:
        await _data_service.ensure_started()

        # Route to appropriate account
        target_account_id = await _data_service._route_account(
            data_account_id, True, "data"
        )

        # Execute option chain API call
        result = await _data_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="quote.get_option_chain",
            kwargs={"symbol": symbol},
            timeout=15.0,
        )

        # Process option chain data
        option_data = None
        if result:
            option_data = {
                "underlying_symbol": symbol,
                "underlying_price": (
                    result.underlying_price
                    if hasattr(result, "underlying_price")
                    else 0
                ),
                "calls": [],
                "puts": [],
                "expiration_dates": [],
            }

            # Process calls
            if hasattr(result, "calls") and result.calls:
                for call in result.calls:
                    call_data = {
                        "symbol": call.symbol if hasattr(call, "symbol") else "",
                        "strike": call.strike if hasattr(call, "strike") else 0,
                        "expiry": call.expiry if hasattr(call, "expiry") else None,
                        "bid": call.bid if hasattr(call, "bid") else 0,
                        "ask": call.ask if hasattr(call, "ask") else 0,
                        "last_price": (
                            call.last_price if hasattr(call, "last_price") else 0
                        ),
                        "volume": call.volume if hasattr(call, "volume") else 0,
                        "open_interest": (
                            call.open_interest if hasattr(call, "open_interest") else 0
                        ),
                        "implied_volatility": (
                            call.implied_volatility
                            if hasattr(call, "implied_volatility")
                            else 0
                        ),
                    }
                    option_data["calls"].append(call_data)

            # Process puts
            if hasattr(result, "puts") and result.puts:
                for put in result.puts:
                    put_data = {
                        "symbol": put.symbol if hasattr(put, "symbol") else "",
                        "strike": put.strike if hasattr(put, "strike") else 0,
                        "expiry": put.expiry if hasattr(put, "expiry") else None,
                        "bid": put.bid if hasattr(put, "bid") else 0,
                        "ask": put.ask if hasattr(put, "ask") else 0,
                        "last_price": (
                            put.last_price if hasattr(put, "last_price") else 0
                        ),
                        "volume": put.volume if hasattr(put, "volume") else 0,
                        "open_interest": (
                            put.open_interest if hasattr(put, "open_interest") else 0
                        ),
                        "implied_volatility": (
                            put.implied_volatility
                            if hasattr(put, "implied_volatility")
                            else 0
                        ),
                    }
                    option_data["puts"].append(put_data)

            # Extract unique expiration dates
            all_options = option_data["calls"] + option_data["puts"]
            expiry_dates = list(
                set([opt["expiry"] for opt in all_options if opt["expiry"]])
            )
            option_data["expiration_dates"] = sorted(expiry_dates)

        return OptionChainResponse(
            success=True, symbol=symbol, data=option_data, account_id=target_account_id
        )

    except Exception as e:
        logger.error(f"Failed to get option chain for {symbol}: {e}")
        return OptionChainResponse(success=False, symbol=symbol, error=str(e))


@mcp.tool()
async def tiger_get_market_status(
    market: str = "US", data_account_id: Optional[str] = None
) -> MarketStatusResponse:
    """
    Get current market status and trading hours.

    Retrieves information about whether markets are open, closed, or in
    pre/post market trading, along with trading session times.

    Args:
        market: Market to check status for. Options:
               - 'US': United States markets (NYSE, NASDAQ)
               - 'HK': Hong Kong market
               - 'SG': Singapore market
               - 'CN': China markets (A-shares)
        data_account_id: Optional specific data account ID to use.
                        If not provided, uses default data account or router.

    Returns:
        MarketStatusResponse containing market status information:
        - status: Current market status (OPEN, CLOSED, PRE_MARKET, POST_MARKET)
        - trading_date: Current trading date
        - open_time: Regular trading session open time
        - close_time: Regular trading session close time
        - timezone: Market timezone
        - is_trading_day: Whether today is a trading day

    Example:
        ```python
        # Check if US market is open
        response = await tiger_get_market_status("US")
        if response.success:
            status = response.data["status"]
            print(f"US Market Status: {status}")
            if status == "OPEN":
                print("Market is currently open for trading")
        ```
    """
    try:
        await _data_service.ensure_started()

        # Route to appropriate account
        target_account_id = await _data_service._route_account(
            data_account_id, True, "data"
        )

        # Execute market status API call
        result = await _data_service.process_manager.execute_api_call(
            account_id=target_account_id,
            method="quote.get_market_status",
            kwargs={"market": market},
            timeout=10.0,
        )

        # Process market status data
        status_data = None
        if result:
            status_data = {
                "market": market,
                "status": result.status if hasattr(result, "status") else "UNKNOWN",
                "trading_date": (
                    result.trading_date if hasattr(result, "trading_date") else None
                ),
                "open_time": result.open_time if hasattr(result, "open_time") else None,
                "close_time": (
                    result.close_time if hasattr(result, "close_time") else None
                ),
                "timezone": result.timezone if hasattr(result, "timezone") else "UTC",
                "is_trading_day": (
                    result.is_trading_day
                    if hasattr(result, "is_trading_day")
                    else False
                ),
                "pre_market_open": (
                    result.pre_market_open
                    if hasattr(result, "pre_market_open")
                    else None
                ),
                "post_market_close": (
                    result.post_market_close
                    if hasattr(result, "post_market_close")
                    else None
                ),
                "next_trading_day": (
                    result.next_trading_day
                    if hasattr(result, "next_trading_day")
                    else None
                ),
            }

        return MarketStatusResponse(
            success=True, market=market, data=status_data, account_id=target_account_id
        )

    except Exception as e:
        logger.error(f"Failed to get market status for {market}: {e}")
        return MarketStatusResponse(success=False, market=market, error=str(e))
