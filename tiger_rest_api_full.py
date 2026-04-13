#!/usr/bin/env python3
"""
Tiger MCP REST API Server - Full Version with Token Refresh
支持完整的22个Tiger API工具 + 自动Token刷新
"""

import asyncio
import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger
from pydantic import BaseModel, Field

# 延迟导入Tiger SDK，避免启动时配置问题
app = FastAPI(
    title="Tiger MCP REST API - Full Edition",
    version="2.0.0",
    description="完整的Tiger Brokers REST API，包含22个工具端点和自动Token刷新"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ============================================================================
# Configuration
# ============================================================================

def _to_namespace(item: Any) -> Any:
    """Convert dictionaries to SimpleNamespace for attribute-style access."""
    if isinstance(item, dict):
        return SimpleNamespace(**item)
    return item


def _coerce_iterable(obj: Any) -> List[Any]:
    """Ensure arbitrary objects become list-like without triggering truthiness checks."""
    if obj is None:
        return []

    if isinstance(obj, list):
        return obj

    if isinstance(obj, tuple):
        return list(obj)

    if isinstance(obj, dict):
        return [obj]

    if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
        try:
            return list(obj)
        except TypeError:
            return [obj]

    return [obj]


def _normalize_payload(payload: Any) -> List[Any]:
    """Normalize Tiger SDK responses into iterable collections we can inspect safely."""
    if payload is None:
        return []

    if isinstance(payload, (list, tuple)):
        return [_to_namespace(obj) for obj in payload]

    if isinstance(payload, dict):
        return [_to_namespace(payload)]

    # Handle pandas DataFrames or other objects exposing to_dict()
    to_dict = getattr(payload, "to_dict", None)
    if callable(to_dict):
        try:
            records = to_dict(orient="records")  # pandas.DataFrame signature
        except TypeError:
            records = to_dict()

        except ValueError as exc:
            if "truth value of a DataFrame is ambiguous" in str(exc):
                records = to_dict(orient="records")
            else:
                raise

        return [_to_namespace(record) for record in _coerce_iterable(records)]

    if isinstance(payload, Iterable) and not isinstance(payload, (str, bytes)):
        return [_to_namespace(item) for item in _coerce_iterable(payload)]

    return [_to_namespace(payload)]


def _to_plain_dict(item: Any) -> Dict[str, Any]:
    """Convert normalized objects into serializable dictionaries."""
    if isinstance(item, SimpleNamespace):
        return vars(item).copy()

    if isinstance(item, dict):
        return dict(item)

    if hasattr(item, "__dict__") and item.__dict__:
        return {
            key: value
            for key, value in vars(item).items()
            if not key.startswith("_") and not callable(value)
        }

    attributes: Dict[str, Any] = {}
    for attr in dir(item):
        if attr.startswith("_"):
            continue
        value = getattr(item, attr)
        if callable(value):
            continue
        attributes[attr] = value

    return attributes if attributes else {"value": item}


def _clean_numeric(value: Any) -> Any:
    """Return ints for whole numbers, floats for fractional numeric values."""
    if value is None or isinstance(value, bool):
        return value

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return value

    if numeric.is_integer():
        return int(numeric)

    return numeric


def _normalize_position_quantity(position: Any) -> Any:
    """Prefer Tiger's decoded position quantity for fractional-share holdings."""
    position_qty = getattr(position, "position_qty", None)
    if position_qty is not None:
        return _clean_numeric(position_qty)

    raw_quantity = getattr(position, "quantity", 0)
    position_scale = getattr(position, "position_scale", None)

    if position_scale not in (None, 0):
        try:
            return _clean_numeric(raw_quantity / (10 ** int(position_scale)))
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    return _clean_numeric(raw_quantity)


def _structure_option_chain(chain_payload: Any) -> Dict[str, Any]:
    """Split option chain payload into calls, puts, and miscellaneous contracts."""
    records = _normalize_payload(chain_payload)

    calls: List[Dict[str, Any]] = []
    puts: List[Dict[str, Any]] = []
    other: List[Dict[str, Any]] = []

    for entry in records:
        contract = _to_plain_dict(entry)
        side = str(
            contract.get("put_call")
            or contract.get("direction")
            or contract.get("type")
            or ""
        ).upper()

        if side == "CALL":
            calls.append(contract)
        elif side == "PUT":
            puts.append(contract)
        else:
            other.append(contract)

    return {
        "total": len(records),
        "calls": calls,
        "puts": puts,
        "other": other,
    }

API_KEYS = {
    "client_key_001": {
        "name": "Full Access Client",
        "allowed_accounts": ["67686635", "66804149", "20240830213609658"],
        "permissions": ["read", "trade", "admin"]
    },
    "client_key_demo": {
        "name": "Demo Only Client",
        "allowed_accounts": ["20240830213609658"],
        "permissions": ["read", "trade"]
    }
}

ACCOUNT_MAPPING = {
    "67686635": {"tiger_id": "20154747", "type": "live", "license": "TBHK"},
    "66804149": {"tiger_id": "20153921", "type": "live", "license": "TBHK"},
    "20240830213609658": {"tiger_id": "20153921", "type": "demo", "license": "TBHK"}
}

# Token refresh configuration
TOKEN_REFRESH_INTERVAL = 12 * 3600  # 12 hours (Tiger tokens expire in 15 days)
TOKEN_REFRESH_RETRY_INTERVAL = 3600  # 1 hour on error

# ============================================================================
# Models
# ============================================================================

class APIResponse(BaseModel):
    """Standard API response"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    account: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class QuoteRequest(BaseModel):
    """Get quote request"""
    account: str
    symbol: str

class KlineRequest(BaseModel):
    """Get K-line data request"""
    account: str
    symbol: str
    period: str = "day"  # day, week, month, year, 1min, 5min, 15min, 30min, 60min
    begin_time: Optional[str] = None  # YYYY-MM-DD HH:MM:SS
    end_time: Optional[str] = None
    limit: int = 100

class MarketDataRequest(BaseModel):
    """Batch market data request"""
    account: str
    symbols: List[str]
    fields: Optional[List[str]] = None  # latest_price, volume, open, high, low, close, etc.

class SymbolSearchRequest(BaseModel):
    """Symbol search request"""
    account: str
    keyword: str
    market: str = "US"  # US, HK, CN

class OptionChainRequest(BaseModel):
    """Option chain request"""
    account: str
    symbol: str
    expiry: Optional[str] = None  # YYYYMMDD

class MarketStatusRequest(BaseModel):
    """Market status request"""
    account: str
    market: str = "US"  # US, HK, CN

class ContractsRequest(BaseModel):
    """Get contracts request"""
    account: str
    symbols: List[str]
    sec_type: str = "STK"  # STK, OPT, FUT, CASH, FOP, WAR, IOPT

class FinancialsRequest(BaseModel):
    """Get financials request"""
    account: str
    symbols: List[str]
    fields: Optional[List[str]] = None

class CorporateActionsRequest(BaseModel):
    """Corporate actions request"""
    account: str
    symbols: List[str]
    action_type: Optional[str] = None  # dividend, split, merge

class EarningsRequest(BaseModel):
    """Earnings request"""
    account: str
    symbols: List[str]
    begin_date: Optional[str] = None
    end_date: Optional[str] = None

class PositionsRequest(BaseModel):
    """Get positions request"""
    account: str

class AccountInfoRequest(BaseModel):
    """Get account info request"""
    account: str

class OrdersRequest(BaseModel):
    """Get orders request"""
    account: str
    status: Optional[str] = None  # Initial, Submitted, Filled, Cancelled, PendingCancel
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class PlaceOrderRequest(BaseModel):
    """Place order request"""
    account: str
    symbol: str
    action: str  # BUY, SELL
    order_type: str  # MKT, LMT, STP, STP_LMT
    quantity: int
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "DAY"  # DAY, GTC, IOC, FOK
    outside_rth: Optional[bool] = Field(
        default=None,
        description="Allow execution outside regular trading hours; defaults to True for market orders when omitted."
    )

class ModifyOrderRequest(BaseModel):
    """Modify order request"""
    account: str
    order_id: str
    quantity: Optional[int] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

class CancelOrderRequest(BaseModel):
    """Cancel order request"""
    account: str
    order_id: str

# ============================================================================
# Authentication & Authorization
# ============================================================================

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """验证API Key"""
    api_key = credentials.credentials

    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    return api_key

def verify_account_access(api_key: str, account: str, permission: str = "read") -> bool:
    """验证账户访问权限"""
    if api_key not in API_KEYS:
        return False

    api_info = API_KEYS[api_key]

    # Check account access
    if account not in api_info["allowed_accounts"]:
        return False

    # Check permission
    if permission not in api_info["permissions"]:
        return False

    return True

def get_tiger_client(account: str):
    """获取Tiger客户端（延迟导入）"""
    if account not in ACCOUNT_MAPPING:
        raise HTTPException(status_code=404, detail=f"Account {account} not found")

    from tigeropen.tiger_open_config import TigerOpenClientConfig
    from tigeropen.trade.trade_client import TradeClient
    from tigeropen.quote.quote_client import QuoteClient

    config = TigerOpenClientConfig()
    return {
        "config": config,
        "trade": TradeClient(config),
        "quote": QuoteClient(config)
    }


def _extract_order_summary(order_obj: Any) -> Optional[Dict[str, Any]]:
    """Convert Tiger SDK Order objects to a serializable summary."""
    if not order_obj:
        return None

    try:
        contract = getattr(order_obj, "contract", None)
        contract_symbol = getattr(contract, "symbol", None) if contract else None
        raw_sub_orders = getattr(order_obj, "orders", None)
        sub_orders = None
        if raw_sub_orders:
            sub_orders = []
            for sub_order in raw_sub_orders:
                sub_summary = _extract_order_summary(sub_order)
                if sub_summary:
                    sub_orders.append(sub_summary)

        return {
            "global_order_id": getattr(order_obj, "id", None),
            "account_order_id": getattr(order_obj, "order_id", None),
            "symbol": getattr(order_obj, "symbol", None) or contract_symbol,
            "action": getattr(order_obj, "action", None),
            "order_type": getattr(order_obj, "order_type", None),
            "quantity": getattr(order_obj, "quantity", None),
            "filled": getattr(order_obj, "filled", None),
            "remaining": getattr(order_obj, "remaining", None),
            "avg_fill_price": getattr(order_obj, "avg_fill_price", None),
            "limit_price": getattr(order_obj, "limit_price", None),
            "stop_price": getattr(order_obj, "aux_price", None),
            "time_in_force": getattr(order_obj, "time_in_force", None),
            "outside_rth": getattr(order_obj, "outside_rth", None),
            "status": getattr(order_obj, "status", None),
            "order_time": getattr(order_obj, "order_time", None),
            "update_time": getattr(order_obj, "update_time", None),
            "filled_cash_amount": getattr(order_obj, "filled_cash_amount", None),
            "commission": getattr(order_obj, "commission", None),
            "realized_pnl": getattr(order_obj, "realized_pnl", None),
            "sub_orders": sub_orders,
        }
    except Exception as exc:
        logger.warning(f"Failed to serialize order object: {exc}")
        return None


def _fetch_order_details(
    trade_client: Any,
    account: str,
    identifier: Optional[Union[str, int]],
    fallback_global_id: Optional[int] = None,
):
    """
    Retrieve order details by trying both global and account-specific identifiers.

    Args:
        trade_client: Tiger trade client
        account: Account number string
        identifier: ID supplied by caller (global or account-specific)
        fallback_global_id: Optional integer ID already known (e.g., from SDK response)
    """
    candidate_ids = []

    if fallback_global_id:
        candidate_ids.append(("id", fallback_global_id))

    if identifier:
        numeric_id = None
        try:
            numeric_id = int(identifier)
            candidate_ids.append(("id", numeric_id))
        except (TypeError, ValueError):
            numeric_id = None

        candidate_ids.append(("order_id", str(identifier)))

    attempted = []
    for key, value in candidate_ids:
        if value is None:
            continue
        try:
            if key == "id":
                order_result = trade_client.get_order(account=account, id=value)
            else:
                order_result = trade_client.get_order(account=account, order_id=value)

            if order_result:
                return order_result

            attempted.append(f"{key}={value} (empty)")
        except Exception as exc:
            attempted.append(f"{key}={value} ({exc})")

    # Fallback: scan recent orders when direct lookup fails (handles account-level IDs)
    try:
        orders = trade_client.get_orders(account=account)
        if orders:
            identifier_str = str(identifier) if identifier is not None else None
            fallback_global_str = (
                str(fallback_global_id) if fallback_global_id is not None else None
            )

            for order_obj in orders:
                order_id_value = getattr(order_obj, "order_id", None)
                global_id_value = getattr(order_obj, "id", None)

                if identifier_str and str(order_id_value) == identifier_str:
                    return order_obj

                if identifier_str and str(global_id_value) == identifier_str:
                    return order_obj

                if fallback_global_str and str(global_id_value) == fallback_global_str:
                    return order_obj
    except Exception as exc:
        attempted.append(f"orders_scan ({exc})")

    if attempted:
        logger.warning(
            "Unable to fetch order details for account %s using identifiers: %s",
            account,
            "; ".join(attempted),
        )
    return None


# ============================================================================
# Health & System Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "Tiger MCP REST API - Full Edition",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "22 Tiger API endpoints",
            "Automatic token refresh (12h interval)",
            "Multi-account support",
            "API key authentication"
        ]
    }

@app.get("/api/endpoints")
async def list_endpoints():
    """列出所有可用的API端点"""
    return {
        "success": True,
        "data": {
            "health": ["GET /health", "GET /api/endpoints"],
            "account_management": [
                "GET /api/accounts",
                "POST /api/token/refresh"
            ],
            "market_data": [
                "POST /api/market/quote",
                "POST /api/market/kline",
                "POST /api/market/batch",
                "POST /api/market/search",
                "POST /api/market/option-chain",
                "POST /api/market/status"
            ],
            "company_info": [
                "POST /api/info/contracts",
                "POST /api/info/financials",
                "POST /api/info/corporate-actions",
                "POST /api/info/earnings"
            ],
            "trading": [
                "POST /api/trade/positions",
                "POST /api/trade/account-info",
                "POST /api/trade/orders",
                "POST /api/trade/place-order",
                "POST /api/trade/modify-order",
                "POST /api/trade/cancel-order"
            ]
        }
    }

# ============================================================================
# Account Management Endpoints
# ============================================================================

@app.get("/api/accounts")
async def list_accounts(api_key: str = Depends(verify_api_key)):
    """列出可访问的账户"""
    api_key_info = API_KEYS[api_key]
    allowed_accounts = api_key_info["allowed_accounts"]

    accounts_info = []
    for account in allowed_accounts:
        if account in ACCOUNT_MAPPING:
            account_info = ACCOUNT_MAPPING[account]
            accounts_info.append({
                "account": account,
                "tiger_id": account_info["tiger_id"],
                "account_type": account_info["type"],
                "license": account_info["license"]
            })

    return APIResponse(
        success=True,
        data={
            "accounts": accounts_info,
            "permissions": api_key_info["permissions"],
            "api_key_name": api_key_info["name"]
        },
        account="system"
    )

@app.post("/api/token/refresh")
async def manual_token_refresh(
    account: str,
    api_key: str = Depends(verify_api_key)
):
    """手动触发Token刷新"""
    if not verify_account_access(api_key, account, "admin"):
        raise HTTPException(status_code=403, detail="Admin permission required")

    try:
        result = await refresh_token_for_account(account)
        return APIResponse(
            success=True,
            data=result,
            account=account
        )
    except Exception as e:
        logger.error(f"Manual token refresh failed: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=account
        )

# ============================================================================
# Market Data Endpoints (6 endpoints)
# ============================================================================

@app.post("/api/market/quote")
async def get_quote(
    request: QuoteRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取实时行情"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        quote_client = clients["quote"]

        # Get quote
        quote_data = _normalize_payload(quote_client.get_stock_briefs([request.symbol]))

        if not quote_data:
            return APIResponse(
                success=False,
                error="No quote data available",
                account=request.account
            )

        quote = quote_data[0]
        return APIResponse(
            success=True,
            data={
                "symbol": request.symbol,
                "latest_price": getattr(quote, 'latest_price', None),
                "pre_close": getattr(quote, 'pre_close', None),
                "open": getattr(quote, 'open', None),
                "high": getattr(quote, 'high', None),
                "low": getattr(quote, 'low', None),
                "volume": getattr(quote, 'volume', None),
                "timestamp": getattr(quote, 'latest_time', None)
            },
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get quote error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/market/kline")
async def get_kline(
    request: KlineRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取K线历史数据"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        quote_client = clients["quote"]

        # Get K-line data
        kline_data = quote_client.get_bars(
            symbols=[request.symbol],
            period=request.period,
            begin_time=request.begin_time,
            end_time=request.end_time,
            limit=request.limit
        )

        normalized_bars = _normalize_payload(kline_data)

        if normalized_bars:
            bars = []
            for item in normalized_bars:
                bars.append({
                    "time": getattr(item, 'time', None),
                    "open": getattr(item, 'open', None),
                    "high": getattr(item, 'high', None),
                    "low": getattr(item, 'low', None),
                    "close": getattr(item, 'close', None),
                    "volume": getattr(item, 'volume', None)
                })

            return APIResponse(
                success=True,
                data={
                    "symbol": request.symbol,
                    "period": request.period,
                    "count": len(bars),
                    "bars": bars
                },
                account=request.account
            )
        else:
            return APIResponse(
                success=True,
                data={"symbol": request.symbol, "bars": []},
                account=request.account
            )
    except Exception as e:
        logger.error(f"Get kline error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/market/batch")
async def get_market_data_batch(
    request: MarketDataRequest,
    api_key: str = Depends(verify_api_key)
):
    """批量获取市场数据"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        quote_client = clients["quote"]

        # Get batch quotes
        quotes = _normalize_payload(quote_client.get_stock_briefs(request.symbols))

        result = {}
        for quote in quotes:
            symbol = getattr(quote, 'symbol', None)
            if symbol:
                result[symbol] = {
                    "latest_price": getattr(quote, 'latest_price', None),
                    "volume": getattr(quote, 'volume', None),
                    "open": getattr(quote, 'open', None),
                    "high": getattr(quote, 'high', None),
                    "low": getattr(quote, 'low', None),
                    "pre_close": getattr(quote, 'pre_close', None)
                }

        return APIResponse(
            success=True,
            data={
                "symbols": request.symbols,
                "count": len(result),
                "quotes": result
            },
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get batch market data error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/market/search")
async def search_symbols(
    request: SymbolSearchRequest,
    api_key: str = Depends(verify_api_key)
):
    """搜索股票代码"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        quote_client = clients["quote"]

        # Search symbols
        results = _normalize_payload(
            quote_client.get_symbol_names(request.keyword, market=request.market)
        )

        symbols_list = []
        for result in results:
            symbols_list.append({
                "symbol": getattr(result, 'symbol', None),
                "name": getattr(result, 'name', None),
                "market": getattr(result, 'market', None)
            })

        return APIResponse(
            success=True,
            data={
                "keyword": request.keyword,
                "market": request.market,
                "results": symbols_list
            },
            account=request.account
        )
    except Exception as e:
        logger.error(f"Search symbols error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/market/option-chain")
async def get_option_chain(
    request: OptionChainRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取期权链"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        quote_client = clients["quote"]

        # Tiger SDK expects a sequence of symbols; wrap the incoming symbol
        symbols = [request.symbol]

        # Get option chain expirations for the requested symbol
        option_data = quote_client.get_option_expirations(symbols)
        normalized_expirations = _normalize_payload(option_data)

        expirations: List[Any] = []
        for entry in normalized_expirations:
            if isinstance(entry, SimpleNamespace):
                value = next(
                    (
                        getattr(entry, attr)
                        for attr in ("expiration", "expiry", "expire_date", "date")
                        if getattr(entry, attr, None)
                    ),
                    None,
                )
                if value is not None:
                    expirations.append(value)
                else:
                    expirations.append(entry.__dict__.copy())
            else:
                expirations.append(entry)

        chain_details: Optional[Dict[str, Any]] = None
        if request.expiry:
            option_chain = quote_client.get_option_chain(
                request.symbol,
                request.expiry,
            )
            structured_chain = _structure_option_chain(option_chain)

            chain_details = {
                "expiry": request.expiry,
                "total": structured_chain["total"],
                "calls": structured_chain["calls"],
                "puts": structured_chain["puts"],
            }

            if structured_chain["other"]:
                chain_details["other"] = structured_chain["other"]

        response_payload: Dict[str, Any] = {
            "symbol": request.symbol,
            "expirations": expirations,
        }

        if chain_details:
            response_payload["chain"] = chain_details

        return APIResponse(
            success=True,
            data=response_payload,
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get option chain error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/market/status")
async def get_market_status(
    request: MarketStatusRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取市场状态"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        quote_client = clients["quote"]

        # Get market status (Tiger SDK returns a domain object that is not JSON serializable)
        status = quote_client.get_market_status(market=request.market)

        normalized_status = _normalize_payload(status)

        if not normalized_status:
            status_payload: Any = {"market": request.market, "status": "Unknown"}
        elif len(normalized_status) == 1:
            status_payload = {
                "market": request.market,
                **_to_plain_dict(normalized_status[0])
            }
        else:
            status_payload = {
                "market": request.market,
                "statuses": [_to_plain_dict(item) for item in normalized_status]
            }

        return APIResponse(
            success=True,
            data=status_payload,
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get market status error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

# ============================================================================
# Company Info Endpoints (4 endpoints)
# ============================================================================

@app.post("/api/info/contracts")
async def get_contracts(
    request: ContractsRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取合约信息"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        quote_client = clients["quote"]

        # Get contract details
        from tigeropen.common.util.contract_utils import stock_contract

        contracts_data = []
        for symbol in request.symbols:
            contract = stock_contract(symbol=symbol)
            contracts_data.append({
                "symbol": symbol,
                "sec_type": request.sec_type,
                "currency": getattr(contract, 'currency', 'USD'),
                "exchange": getattr(contract, 'exchange', None)
            })

        return APIResponse(
            success=True,
            data={"contracts": contracts_data},
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get contracts error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/info/financials")
async def get_financials(
    request: FinancialsRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取财务数据"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        quote_client = clients["quote"]

        # Get financial data
        financials = quote_client.get_financial_daily(request.symbols, fields=request.fields)

        return APIResponse(
            success=True,
            data={"financials": financials if financials else []},
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get financials error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/info/corporate-actions")
async def get_corporate_actions(
    request: CorporateActionsRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取公司行动（分红、拆股等）"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        quote_client = clients["quote"]

        # Get corporate actions
        actions = quote_client.get_corporate_actions(
            request.symbols,
            action_type=request.action_type
        )

        return APIResponse(
            success=True,
            data={"corporate_actions": actions if actions else []},
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get corporate actions error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/info/earnings")
async def get_earnings(
    request: EarningsRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取财报数据"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        quote_client = clients["quote"]

        # Get earnings calendar
        earnings = quote_client.get_earnings_calendar(
            symbols=request.symbols,
            begin_date=request.begin_date,
            end_date=request.end_date
        )

        return APIResponse(
            success=True,
            data={"earnings": earnings if earnings else []},
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get earnings error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

# ============================================================================
# Trading Endpoints (6 endpoints)
# ============================================================================

@app.post("/api/trade/positions")
async def get_positions(
    request: PositionsRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取持仓"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        trade_client = clients["trade"]

        positions = trade_client.get_positions()

        positions_data = []
        if positions:
            for pos in positions:
                normalized_quantity = _normalize_position_quantity(pos)
                positions_data.append({
                    "symbol": getattr(pos.contract, 'symbol', 'Unknown') if hasattr(pos, 'contract') else 'Unknown',
                    "quantity": normalized_quantity,
                    "quantity_raw": getattr(pos, 'quantity', 0),
                    "quantity_scale": getattr(pos, 'position_scale', 0),
                    "average_cost": getattr(pos, 'average_cost', 0),
                    "market_price": getattr(pos, 'market_price', 0),
                    "market_value": getattr(pos, 'market_value', 0),
                    "unrealized_pnl": getattr(pos, 'unrealized_pnl', 0) if hasattr(pos, 'unrealized_pnl') else
                                     (getattr(pos, 'market_price', 0) - getattr(pos, 'average_cost', 0)) * normalized_quantity
                })

        return APIResponse(
            success=True,
            data={"positions": positions_data, "count": len(positions_data)},
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get positions error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/trade/account-info")
async def get_account_info(
    request: AccountInfoRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取账户信息"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        trade_client = clients["trade"]
        config = clients["config"]

        # Get assets
        assets = trade_client.get_prime_assets()

        account_data = {
            "account_id": assets.account if hasattr(assets, 'account') else request.account,
            "tiger_id": config.tiger_id,
            "update_timestamp": getattr(assets, 'update_timestamp', None)
        }

        if hasattr(assets, 'segments') and 'S' in assets.segments:
            s_segment = assets.segments['S']
            account_data.update({
                "net_liquidation": getattr(s_segment, 'net_liquidation', 0),
                "cash_balance": getattr(s_segment, 'cash_balance', 0),
                "buying_power": getattr(s_segment, 'buying_power', 0),
                "gross_position_value": getattr(s_segment, 'gross_position_value', 0),
                "unrealized_pnl": getattr(s_segment, 'unrealized_pl', 0),
                "realized_pnl": getattr(s_segment, 'realized_pl', 0)
            })

        return APIResponse(
            success=True,
            data=account_data,
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get account info error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/trade/orders")
async def get_orders(
    request: OrdersRequest,
    api_key: str = Depends(verify_api_key)
):
    """获取订单列表"""
    if not verify_account_access(api_key, request.account):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        clients = get_tiger_client(request.account)
        trade_client = clients["trade"]

        # Get orders with optional filters
        orders = trade_client.get_orders(
            account=request.account,
            start_time=request.start_date,
            end_time=request.end_date
        )

        orders_data = []
        if orders:
            for order in orders:
                order_dict = {
                    "order_id": getattr(order, 'order_id', None),
                    "symbol": getattr(order.contract, 'symbol', None) if hasattr(order, 'contract') else None,
                    "action": getattr(order, 'action', None),
                    "order_type": getattr(order, 'order_type', None),
                    "quantity": getattr(order, 'quantity', 0),
                    "limit_price": getattr(order, 'limit_price', None),
                    "status": getattr(order, 'status', None),
                    "filled": getattr(order, 'filled', 0),
                    "avg_fill_price": getattr(order, 'avg_fill_price', None),
                    "order_time": getattr(order, 'order_time', None)
                }

                # Filter by status if specified
                if request.status:
                    if order_dict["status"] == request.status:
                        orders_data.append(order_dict)
                else:
                    orders_data.append(order_dict)

        return APIResponse(
            success=True,
            data={"orders": orders_data, "count": len(orders_data)},
            account=request.account
        )
    except Exception as e:
        logger.error(f"Get orders error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/trade/place-order")
async def place_order(
    request: PlaceOrderRequest,
    api_key: str = Depends(verify_api_key)
):
    """下单"""
    if not verify_account_access(api_key, request.account, "trade"):
        raise HTTPException(status_code=403, detail="Trading permission required")

    try:
        clients = get_tiger_client(request.account)
        trade_client = clients["trade"]

        from tigeropen.common.util.contract_utils import stock_contract
        from tigeropen.common.util.order_utils import (
            market_order, limit_order, stop_order, stop_limit_order
        )

        contract = stock_contract(symbol=request.symbol, currency='USD')

        # Create order based on type
        if request.order_type == "MKT":
            order = market_order(
                account=request.account,
                contract=contract,
                action=request.action,
                quantity=request.quantity
            )
        elif request.order_type == "LMT":
            if not request.limit_price:
                raise HTTPException(status_code=400, detail="Limit price required for limit order")
            order = limit_order(
                account=request.account,
                contract=contract,
                action=request.action,
                quantity=request.quantity,
                limit_price=request.limit_price
            )
        elif request.order_type == "STP":
            if not request.stop_price:
                raise HTTPException(status_code=400, detail="Stop price required for stop order")
            order = stop_order(
                account=request.account,
                contract=contract,
                action=request.action,
                quantity=request.quantity,
                stop_price=request.stop_price
            )
        elif request.order_type == "STP_LMT":
            if not request.limit_price or not request.stop_price:
                raise HTTPException(status_code=400, detail="Both limit and stop price required")
            order = stop_limit_order(
                account=request.account,
                contract=contract,
                action=request.action,
                quantity=request.quantity,
                limit_price=request.limit_price,
                stop_price=request.stop_price
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported order type: {request.order_type}")

        # Set time in force
        order.time_in_force = request.time_in_force
        outside_rth = request.outside_rth
        if outside_rth is None:
            outside_rth = request.order_type == "MKT"
        order.outside_rth = bool(outside_rth)

        # Place order
        order_id = trade_client.place_order(order)

        # Attempt to include enriched order metadata
        order_summary = _extract_order_summary(order) or {}

        if not order_summary.get("status") or order_summary.get("status") == "NEW":
            fetched_order = _fetch_order_details(
                trade_client,
                request.account,
                identifier=order_summary.get("account_order_id"),
                fallback_global_id=order_id,
            )
            if fetched_order:
                fetched_summary = _extract_order_summary(fetched_order)
                if fetched_summary:
                    order_summary = fetched_summary

        outside_rth_value = order_summary.get("outside_rth")
        if outside_rth_value is None:
            outside_rth_value = bool(outside_rth)

        response_payload = {
            "order_id": order_id,
            "account_order_id": order_summary.get("account_order_id"),
            "symbol": order_summary.get("symbol") or request.symbol,
            "action": order_summary.get("action") or request.action,
            "order_type": order_summary.get("order_type") or request.order_type,
            "quantity": order_summary.get("quantity") or request.quantity,
            "status": order_summary.get("status"),
            "filled": order_summary.get("filled"),
            "remaining": order_summary.get("remaining"),
            "avg_fill_price": order_summary.get("avg_fill_price"),
            "limit_price": order_summary.get("limit_price") or request.limit_price,
            "stop_price": order_summary.get("stop_price") or request.stop_price,
            "time_in_force": order_summary.get("time_in_force") or request.time_in_force,
            "outside_rth": outside_rth_value,
            "order_time": order_summary.get("order_time"),
            "update_time": order_summary.get("update_time"),
            "commission": order_summary.get("commission"),
            "realized_pnl": order_summary.get("realized_pnl"),
            "filled_cash_amount": order_summary.get("filled_cash_amount"),
            "status_details": order_summary.get("sub_orders"),
        }

        return APIResponse(
            success=True,
            data=response_payload,
            account=request.account
        )
    except Exception as e:
        logger.error(f"Place order error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/trade/modify-order")
async def modify_order(
    request: ModifyOrderRequest,
    api_key: str = Depends(verify_api_key)
):
    """修改订单"""
    if not verify_account_access(api_key, request.account, "trade"):
        raise HTTPException(status_code=403, detail="Trading permission required")

    try:
        clients = get_tiger_client(request.account)
        trade_client = clients["trade"]

        if all(
            value is None
            for value in (request.quantity, request.limit_price, request.stop_price)
        ):
            raise HTTPException(
                status_code=400,
                detail="At least one of quantity, limit_price, or stop_price must be provided",
            )

        # Fetch existing order details
        existing_order = _fetch_order_details(
            trade_client,
            request.account,
            identifier=request.order_id,
        )

        if not existing_order:
            raise HTTPException(
                status_code=404,
                detail=f"Order {request.order_id} not found for account {request.account}",
            )

        modify_kwargs: Dict[str, Any] = {}
        if request.quantity is not None:
            modify_kwargs["quantity"] = request.quantity
        if request.limit_price is not None:
            modify_kwargs["limit_price"] = request.limit_price
        if request.stop_price is not None:
            modify_kwargs["aux_price"] = request.stop_price

        # Modify order with correct Tiger SDK signature
        modify_result = trade_client.modify_order(
            existing_order,
            **modify_kwargs,
        )

        updated_order = _fetch_order_details(
            trade_client,
            request.account,
            identifier=request.order_id,
            fallback_global_id=modify_result or getattr(existing_order, "id", None),
        )

        if not updated_order:
            updated_order = existing_order

        order_summary = _extract_order_summary(updated_order) or {}
        modified_fields = {
            key: value
            for key, value in (
                ("quantity", request.quantity),
                ("limit_price", request.limit_price),
                ("stop_price", request.stop_price),
            )
            if value is not None
        }

        response_payload = {
            "order_id": order_summary.get("global_order_id")
            or modify_result
            or getattr(existing_order, "id", None),
            "account_order_id": order_summary.get("account_order_id"),
            "requested_order_id": request.order_id,
            "status": order_summary.get("status"),
            "symbol": order_summary.get("symbol"),
            "action": order_summary.get("action"),
            "order_type": order_summary.get("order_type"),
            "quantity": order_summary.get("quantity"),
            "filled": order_summary.get("filled"),
            "remaining": order_summary.get("remaining"),
            "avg_fill_price": order_summary.get("avg_fill_price"),
            "limit_price": order_summary.get("limit_price"),
            "stop_price": order_summary.get("stop_price"),
            "time_in_force": order_summary.get("time_in_force"),
            "outside_rth": order_summary.get("outside_rth"),
            "order_time": order_summary.get("order_time"),
            "update_time": order_summary.get("update_time"),
            "commission": order_summary.get("commission"),
            "realized_pnl": order_summary.get("realized_pnl"),
            "filled_cash_amount": order_summary.get("filled_cash_amount"),
            "status_details": order_summary.get("sub_orders"),
            "modified_fields": modified_fields,
            "modify_reference_id": modify_result,
        }

        if modify_result is not None:
            response_payload["result"] = modify_result

        return APIResponse(
            success=True,
            data=response_payload,
            account=request.account
        )
    except Exception as e:
        logger.error(f"Modify order error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

@app.post("/api/trade/cancel-order")
async def cancel_order(
    request: CancelOrderRequest,
    api_key: str = Depends(verify_api_key)
):
    """取消订单"""
    if not verify_account_access(api_key, request.account, "trade"):
        raise HTTPException(status_code=403, detail="Trading permission required")

    try:
        clients = get_tiger_client(request.account)
        trade_client = clients["trade"]

        # Cancel order
        existing_order = _fetch_order_details(
            trade_client,
            request.account,
            identifier=request.order_id,
        )

        if not existing_order:
            raise HTTPException(
                status_code=404,
                detail=f"Order {request.order_id} not found for account {request.account}",
            )

        order_summary = _extract_order_summary(existing_order) or {}

        # Prepare cancel parameters supporting both global and account-level IDs
        cancel_kwargs: Dict[str, Any] = {"account": request.account}

        global_order_id = order_summary.get("global_order_id")
        account_order_id = order_summary.get("account_order_id")

        provided_numeric_id: Optional[int] = None
        try:
            provided_numeric_id = int(request.order_id)
        except (TypeError, ValueError):
            provided_numeric_id = None

        if global_order_id:
            try:
                cancel_kwargs["id"] = int(global_order_id)
            except (TypeError, ValueError):
                pass

        if account_order_id not in (None, ""):
            try:
                cancel_kwargs["order_id"] = int(account_order_id)
            except (TypeError, ValueError):
                cancel_kwargs["order_id"] = str(account_order_id)

        # If we still don't have an identifier, fall back to caller-provided numeric
        if "id" not in cancel_kwargs and provided_numeric_id is not None:
            cancel_kwargs["id"] = provided_numeric_id

        cancel_result = trade_client.cancel_order(**cancel_kwargs)

        cancel_reference_id: Optional[int] = None
        if isinstance(cancel_result, bool):
            cancel_reference_id = None
        elif isinstance(cancel_result, int):
            cancel_reference_id = cancel_result
        elif isinstance(cancel_result, str) and cancel_result.isdigit():
            cancel_reference_id = int(cancel_result)

        # Refresh order status after cancellation
        refreshed_order = _fetch_order_details(
            trade_client,
            request.account,
            identifier=account_order_id or request.order_id,
            fallback_global_id=cancel_reference_id or global_order_id,
        )

        if refreshed_order:
            order_summary = _extract_order_summary(refreshed_order) or order_summary

        response_payload = {
            "order_id": order_summary.get("global_order_id")
            or cancel_result
            or global_order_id
            or request.order_id,
            "account_order_id": order_summary.get("account_order_id") or account_order_id,
            "requested_order_id": request.order_id,
            "status": order_summary.get("status"),
            "symbol": order_summary.get("symbol"),
            "action": order_summary.get("action"),
            "order_type": order_summary.get("order_type"),
            "quantity": order_summary.get("quantity"),
            "filled": order_summary.get("filled"),
            "remaining": order_summary.get("remaining"),
            "avg_fill_price": order_summary.get("avg_fill_price"),
            "limit_price": order_summary.get("limit_price"),
            "stop_price": order_summary.get("stop_price"),
            "time_in_force": order_summary.get("time_in_force"),
            "outside_rth": order_summary.get("outside_rth"),
            "order_time": order_summary.get("order_time"),
            "update_time": order_summary.get("update_time"),
            "commission": order_summary.get("commission"),
            "realized_pnl": order_summary.get("realized_pnl"),
            "filled_cash_amount": order_summary.get("filled_cash_amount"),
            "status_details": order_summary.get("sub_orders"),
            "cancel_reference_id": cancel_reference_id or global_order_id,
        }

        return APIResponse(
            success=True,
            data=response_payload,
            account=request.account
        )
    except Exception as e:
        logger.error(f"Cancel order error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            account=request.account
        )

# ============================================================================
# Token Refresh Background Task
# ============================================================================

async def refresh_token_for_account(account: str) -> Dict[str, Any]:
    """
    为指定账户刷新Token

    Tiger SDK会自动更新token文件，我们只需要触发一次API调用即可
    """
    try:
        from tigeropen.tiger_open_config import TigerOpenClientConfig
        from tigeropen.trade.trade_client import TradeClient

        # Create client - this will trigger token validation
        config = TigerOpenClientConfig()
        client = TradeClient(config)

        # Make a lightweight API call to trigger refresh
        managed_accounts = client.get_managed_accounts()

        logger.info(f"✅ Token refresh successful for account {account}, tiger_id: {config.tiger_id}")

        return {
            "refreshed": True,
            "tiger_id": config.tiger_id,
            "account": account,
            "managed_accounts": managed_accounts if managed_accounts else []
        }

    except Exception as e:
        logger.error(f"❌ Token refresh failed for account {account}: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """启动时执行的任务"""
    logger.info("🚀 Tiger MCP REST API Server starting...")
    logger.info(f"📋 Registered {len(ACCOUNT_MAPPING)} accounts")
    logger.info(f"🔑 Configured {len(API_KEYS)} API keys")
    logger.info(f"🔄 Token refresh interval: {TOKEN_REFRESH_INTERVAL / 3600}h")

    # Start background token refresh task
    asyncio.create_task(token_refresh_background_task())
    logger.info("✅ Background token refresh scheduler started")

async def token_refresh_background_task():
    """
    后台Token刷新任务

    Tiger token有效期15天，SDK默认24小时刷新
    我们设置12小时刷新一次以保证安全
    """
    # Wait a bit before first refresh to let server fully start
    await asyncio.sleep(60)  # Wait 1 minute

    while True:
        try:
            logger.info("🔄 Starting scheduled token refresh for all accounts...")

            refresh_results = []
            for account in ACCOUNT_MAPPING.keys():
                try:
                    result = await refresh_token_for_account(account)
                    refresh_results.append({
                        "account": account,
                        "success": True,
                        "result": result
                    })
                except Exception as e:
                    refresh_results.append({
                        "account": account,
                        "success": False,
                        "error": str(e)
                    })

            # Log summary
            success_count = sum(1 for r in refresh_results if r["success"])
            logger.info(f"✅ Token refresh completed: {success_count}/{len(refresh_results)} successful")

            # Wait for next refresh cycle
            logger.info(f"⏰ Next token refresh in {TOKEN_REFRESH_INTERVAL / 3600}h")
            await asyncio.sleep(TOKEN_REFRESH_INTERVAL)

        except Exception as e:
            logger.error(f"❌ Token refresh task error: {e}")
            # On error, retry sooner
            logger.info(f"⏰ Retrying token refresh in {TOKEN_REFRESH_RETRY_INTERVAL / 3600}h")
            await asyncio.sleep(TOKEN_REFRESH_RETRY_INTERVAL)

@app.on_event("shutdown")
async def shutdown_event():
    """关闭时执行的清理"""
    logger.info("🛑 Tiger MCP REST API Server shutting down...")

# ============================================================================
# Main Entry Point
# ============================================================================

def run(host: str = "0.0.0.0", port: int = 9000, log_level: str = "info") -> None:
    """Launch the FastAPI server."""
    logger.info("=" * 80)
    logger.info("Tiger MCP REST API Server - Full Edition v2.0.0")
    logger.info("=" * 80)
    logger.info("Features:")
    logger.info("  ✅ 22 Complete Tiger API Endpoints")
    logger.info("  ✅ Automatic Token Refresh (12h interval)")
    logger.info("  ✅ Multi-Account Support")
    logger.info("  ✅ API Key Authentication")
    logger.info("  ✅ CORS Enabled")
    logger.info("=" * 80)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level
    )


if __name__ == "__main__":
    run()
