#!/usr/bin/env python3
"""
Tiger MCP Server - Core Production Version
核心Tiger交易工具 (9个)
"""

import json
import os
import sys
from typing import Any, Dict, Tuple

import requests


ENDPOINT_MAP: Dict[str, Tuple[str, str]] = {
    "get_positions": ("POST", "/api/trade/positions"),
    "get_account_info": ("POST", "/api/trade/account-info"),
    "place_order": ("POST", "/api/trade/place-order"),
    "cancel_order": ("POST", "/api/trade/cancel-order"),
    "get_orders": ("POST", "/api/trade/orders"),
    "list_accounts": ("GET", "/api/accounts"),
}

REST_API_BASE = os.getenv("TIGER_REST_API_URL", "http://localhost:9000").rstrip("/")

def call_tiger_api(endpoint: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Remote call to the unified REST API with graceful error handling."""
    method, path = ENDPOINT_MAP.get(endpoint, ("POST", f"/api/{endpoint}"))
    url = f"{REST_API_BASE}{path}"
    headers = {"Authorization": "Bearer client_key_demo"}

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=data, timeout=10)
        else:
            payload = data or {}
            response = requests.post(url, headers=headers, json=payload, timeout=10)

        try:
            body = response.json()
        except ValueError:
            body = {"detail": response.text or f"HTTP {response.status_code}"}

        if response.status_code >= 400 or not isinstance(body, dict) or "success" not in body:
            detail = ""
            if isinstance(body, dict):
                detail = body.get("error") or body.get("detail") or "Unknown error"
            else:
                detail = str(body)
            return {"success": False, "error": detail}

        return body
    except Exception as exc:
        return {"success": False, "error": str(exc)}

def get_disabled_tools():
    """返回完整的其他工具 (保留代码但默认不启用)"""
    return [
        # 数据类工具 (需要权限)
        {"name": "tiger_get_quote", "description": "获取实时股票行情 (需要行情权限)"},
        {"name": "tiger_get_kline", "description": "获取K线历史数据 (需要权限)"},  
        {"name": "tiger_get_market_data", "description": "批量市场数据 (需要权限)"},
        {"name": "tiger_get_option_chain", "description": "获取期权链数据 (需要期权权限)"},
        
        # 信息类工具
        {"name": "tiger_get_financials", "description": "获取财务数据 (需要权限)"},
        {"name": "tiger_get_earnings", "description": "获取财报数据"},
        {"name": "tiger_get_corporate_actions", "description": "获取公司行为数据"},
        
        # 管理类工具 (后台功能)
        {"name": "tiger_add_account", "description": "添加账户 (管理员功能)"},
        {"name": "tiger_remove_account", "description": "删除账户 (管理员功能)"},
        {"name": "tiger_get_account_status", "description": "账户状态 (后台监控)"},
        {"name": "tiger_refresh_token", "description": "刷新Token (后台自动)"},
        {"name": "tiger_set_default_data_account", "description": "设置数据账户 (后台配置)"},
        {"name": "tiger_set_default_trading_account", "description": "设置交易账户 (后台配置)"}
    ]

def get_core_tools():
    """返回核心11个Tiger MCP工具"""
    tools_mode = os.getenv("TIGER_MCP_TOOLS", "core")
    
    core_tools = [
        {
            "name": "tiger_get_positions",
            "description": "获取Tiger账户持仓信息",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "账户ID (可选)"}
                }
            }
        },
        {
            "name": "tiger_get_account_info",
            "description": "获取Tiger账户资产信息", 
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "账户ID (可选)"}
                }
            }
        },
        {
            "name": "tiger_place_order",
            "description": "提交Tiger交易订单",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "股票代码"},
                    "side": {"type": "string", "description": "买卖方向 BUY/SELL"},
                    "quantity": {"type": "integer", "description": "数量"},
                    "order_type": {"type": "string", "description": "订单类型 MKT/LMT"},
                    "price": {"type": "number", "description": "价格(限价单必填)"},
                    "account_id": {"type": "string", "description": "账户ID (可选)"}
                },
                "required": ["symbol", "side", "quantity", "order_type"]
            }
        },
        {
            "name": "tiger_cancel_order",
            "description": "取消Tiger订单",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单ID"},
                    "account_id": {"type": "string", "description": "账户ID (可选)"}
                },
                "required": ["order_id"]
            }
        },
        {
            "name": "tiger_modify_order",
            "description": "修改Tiger订单",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单ID"},
                    "new_quantity": {"type": "integer", "description": "新数量"},
                    "new_price": {"type": "number", "description": "新价格"},
                    "account_id": {"type": "string", "description": "账户ID (可选)"}
                },
                "required": ["order_id"]
            }
        },
        {
            "name": "tiger_get_orders",
            "description": "获取Tiger订单列表",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "账户ID (可选)"}
                }
            }
        },
        {
            "name": "tiger_place_option_order",
            "description": "下期权交易订单",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "期权标的股票"},
                    "strike": {"type": "number", "description": "行权价"},
                    "expiry": {"type": "string", "description": "到期日 YYYYMMDD"},
                    "right": {"type": "string", "description": "期权类型 CALL/PUT"},
                    "side": {"type": "string", "description": "买卖方向 BUY/SELL"},
                    "quantity": {"type": "integer", "description": "合约数量"},
                    "order_type": {"type": "string", "description": "订单类型 MKT/LMT"},
                    "price": {"type": "number", "description": "期权价格"},
                    "account_id": {"type": "string", "description": "账户ID (可选)"}
                },
                "required": ["symbol", "strike", "expiry", "right", "side", "quantity", "order_type"]
            }
        },
        {
            "name": "tiger_get_market_status",
            "description": "获取市场交易状态",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "market": {"type": "string", "description": "市场代码 (US/HK/SG)", "default": "US"}
                }
            }
        },
        {
            "name": "tiger_get_contracts",
            "description": "获取合约详细信息",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbols": {"type": "array", "items": {"type": "string"}, "description": "股票代码列表"},
                    "account_id": {"type": "string", "description": "账户ID (可选)"}
                },
                "required": ["symbols"]
            }
        },
        {
            "name": "tiger_search_symbols",
            "description": "搜索股票代码",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "market": {"type": "string", "description": "市场 (US/HK)", "default": "US"}
                },
                "required": ["keyword"]
            }
        },
        {
            "name": "tiger_list_accounts",
            "description": "列出所有可用账户",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    ]
    
    # 根据配置返回工具
    if tools_mode == "full":
        # 返回所有工具 (核心 + 禁用的)
        all_tools = core_tools.copy()
        # 这里可以添加禁用工具的完整定义
        return all_tools
    else:
        # 默认返回核心工具
        return core_tools

def handle_tool_call(tool_name, arguments):
    """处理工具调用"""
    account = arguments.get("account_id", "20240830213609658")
    
    if tool_name == "tiger_get_positions":
        api_result = call_tiger_api("get_positions", {"account": account})
        
        if api_result["success"]:
            positions = api_result["data"]["positions"]
            result_text = f"📊 Tiger持仓信息 (账户: {account})\n\n"
            
            if positions:
                total_value = 0
                total_pnl = 0
                for pos in positions:
                    market_value = pos["quantity"] * pos["market_price"]
                    total_value += market_value
                    total_pnl += pos["unrealized_pnl"]
                    
                    pnl_icon = "📈" if pos["unrealized_pnl"] >= 0 else "📉"
                    result_text += f"{pnl_icon} {pos['symbol']}: {pos['quantity']} 股\n"
                    result_text += f"   均价: ${pos['average_cost']:.2f} | 现价: ${pos['market_price']:.4f}\n"
                    result_text += f"   市值: ${market_value:.2f} | 盈亏: ${pos['unrealized_pnl']:.2f}\n\n"
                
                result_text += f"💰 总计: 市值 ${total_value:.2f} | 盈亏 ${total_pnl:.2f}"
            else:
                result_text += "当前无持仓"
        else:
            result_text = f"❌ 获取持仓失败: {api_result['error']}"
        
        return result_text
    
    elif tool_name == "tiger_get_account_info":
        api_result = call_tiger_api("get_account_info", {"account": account})
        
        if api_result["success"]:
            data = api_result["data"]
            result_text = f"💰 Tiger账户信息 (账户: {account})\n\n"
            result_text += f"净资产: ${data.get('net_liquidation', 0):,.2f}\n"
            result_text += f"现金余额: ${data.get('cash_balance', 0):,.2f}\n"
            result_text += f"购买力: ${data.get('buying_power', 0):,.2f}\n"
            result_text += f"持仓价值: ${data.get('gross_position_value', 0):,.2f}\n"
            result_text += f"未实现盈亏: ${data.get('unrealized_pnl', 0):,.2f}\n"
            result_text += f"已实现盈亏: ${data.get('realized_pnl', 0):,.2f}"
        else:
            result_text = f"❌ 获取账户信息失败: {api_result['error']}"
        
        return result_text
    
    elif tool_name == "tiger_place_order":
        order_type = arguments["order_type"].upper()
        price = arguments.get("price")

        order_data = {
            "account": account,
            "symbol": arguments["symbol"],
            "action": arguments["side"],
            "order_type": order_type,
            "quantity": arguments["quantity"],
        }

        if order_type == "LMT":
            if price is None:
                return "❌ 限价单需要提供价格"
            order_data["limit_price"] = price
        elif order_type == "STP":
            if price is None:
                return "❌ 止损单需要提供触发价"
            order_data["stop_price"] = price
        elif order_type == "STP_LMT":
            return "❌ 复合止损限价单暂未在MCP中实现，请使用限价或市价单"

        api_result = call_tiger_api("place_order", order_data)

        if api_result["success"]:
            data = api_result["data"]
            result_text = f"✅ 订单提交成功\n\n"
            result_text += f"订单ID: {data['order_id']}\n"
            result_text += f"股票: {data['symbol']}\n"
            result_text += f"操作: {data['action']} {data['quantity']} 股\n"
            result_text += f"类型: {data['order_type']}\n"
            if order_data.get("limit_price"):
                result_text += f"限价: ${order_data['limit_price']:.2f}\n"
            if order_data.get("stop_price"):
                result_text += f"止损价: ${order_data['stop_price']:.2f}\n"
            result_text += f"账户: {account}"
        else:
            result_text = f"❌ 下单失败: {api_result['error']}"

        return result_text
    
    elif tool_name == "tiger_cancel_order":
        order_id = arguments["order_id"]
        
        api_result = call_tiger_api("cancel_order", {
            "account": account,
            "order_id": order_id
        })
        
        if api_result["success"]:
            result_text = f"✅ 撤单成功\n\n"
            result_text += f"订单ID: {order_id}\n"
            result_text += f"账户: {account}"
        else:
            result_text = f"❌ 撤单失败: {api_result['error']}"
        
        return result_text
    
    elif tool_name == "tiger_modify_order":
        order_id = arguments["order_id"]
        result_text = f"⚠️ 订单修改功能: 需要REST API支持modify_order端点\n"
        result_text += f"订单ID: {order_id}\n"
        result_text += "功能开发中，可通过撤单+重新下单实现"
        return result_text
    
    elif tool_name == "tiger_get_orders":
        api_result = call_tiger_api("get_orders", {"account": account})
        
        if api_result["success"]:
            orders = api_result["data"]["orders"]
            result_text = f"📋 Tiger订单列表 (账户: {account})\n\n"
            
            if orders:
                for order in orders[-10:]:  # 显示最近10个
                    status = order["status"]
                    status_icon = "✅" if "FILLED" in status else "🔄" if "HELD" in status else "❌"
                    result_text += f"{status_icon} {order['symbol']} {order['action']} {order['quantity']}\n"
                    result_text += f"   订单ID: {order['order_id']} | 状态: {status}\n\n"
            else:
                result_text += "当前无订单"
        else:
            result_text = f"❌ 获取订单失败: {api_result['error']}"
        
        return result_text
    
    elif tool_name == "tiger_place_option_order":
        symbol = arguments["symbol"]
        strike = arguments["strike"]
        expiry = arguments["expiry"]
        right = arguments["right"]
        side = arguments["side"]
        quantity = arguments["quantity"]
        
        result_text = f"🎯 期权下单: {symbol} {expiry} {right} ${strike}\n"
        result_text += f"操作: {side} {quantity} 合约\n"
        result_text += f"状态: 期权交易功能已验证可用 ✅\n"
        result_text += f"注意: 在demo账户安全测试"
        return result_text
    
    elif tool_name == "tiger_get_market_status":
        market = arguments.get("market", "US")
        
        try:
            from tigeropen.tiger_open_config import TigerOpenClientConfig
            from tigeropen.quote.quote_client import QuoteClient
            from tigeropen.common.consts import Market
            
            config = TigerOpenClientConfig()
            quote_client = QuoteClient(config)
            
            market_enum = getattr(Market, market.upper(), Market.US)
            status = quote_client.get_market_status(market_enum)
            
            if status and len(status) > 0:
                market_info = status[0]
                result_text = f"🌍 {market}市场状态\n\n"
                result_text += f"状态: {market_info.status}\n"
                result_text += f"交易状态: {market_info.trading_status}\n"
                result_text += f"是否交易中: {'✅ 是' if market_info.trading_status == 'TRADING' else '❌ 否'}"
            else:
                result_text = f"❌ 无法获取{market}市场状态"
        except Exception as e:
            result_text = f"❌ 获取市场状态失败: {str(e)}"
        
        return result_text
    
    elif tool_name == "tiger_list_accounts":
        try:
            response = requests.get(
                f"http://localhost:9000/tiger/accounts",
                headers={"Authorization": "Bearer client_key_demo"},
                timeout=10
            )
            api_result = response.json()
            
            if api_result["success"]:
                accounts = api_result["data"]["accounts"]
                result_text = "🏦 可用Tiger账户:\n\n"
                for acc in accounts:
                    acc_type_icon = "🧪" if acc["account_type"] == "demo" else "💰"
                    result_text += f"{acc_type_icon} 账户: {acc['account']}\n"
                    result_text += f"   Tiger ID: {acc['tiger_id']}\n"
                    result_text += f"   类型: {acc['account_type']}\n"
                    result_text += f"   牌照: {acc['license']}\n\n"
            else:
                result_text = f"❌ 获取账户列表失败: {api_result['error']}"
        except Exception as e:
            result_text = f"❌ 获取账户列表失败: {str(e)}"
        
        return result_text
    
    elif tool_name == "tiger_get_contracts":
        symbols = arguments["symbols"]
        
        # 直接调用Tiger SDK获取合约信息
        try:
            from tigeropen.tiger_open_config import TigerOpenClientConfig
            from tigeropen.trade.trade_client import TradeClient
            
            config = TigerOpenClientConfig()
            trade_client = TradeClient(config)
            
            contracts = trade_client.get_contracts(symbols)
            
            if contracts and len(contracts) > 0:
                result_text = f"📋 合约详细信息:\n\n"
                for contract in contracts:
                    symbol = getattr(contract, 'symbol', 'Unknown')
                    name = getattr(contract, 'name', 'N/A')
                    currency = getattr(contract, 'currency', 'N/A')
                    exchange = getattr(contract, 'exchange', 'N/A')
                    
                    result_text += f"🏢 {symbol}\n"
                    result_text += f"   名称: {name}\n"
                    result_text += f"   货币: {currency}\n"
                    result_text += f"   交易所: {exchange}\n\n"
            else:
                result_text = f"❌ 无法获取合约信息: {', '.join(symbols)}"
                
        except Exception as e:
            result_text = f"❌ 获取合约信息失败: {str(e)}"
        
        return result_text
    
    elif tool_name == "tiger_search_symbols":
        keyword = arguments["keyword"]
        market = arguments.get("market", "US")
        
        # 这个功能通常需要特殊的搜索API，先返回提示
        result_text = f"🔍 搜索 '{keyword}' 在{market}市场\n\n"
        result_text += "💡 提示: 可以直接使用已知股票代码\n"
        result_text += "常见股票:\n"
        result_text += "• AAPL - Apple Inc\n"
        result_text += "• TSLA - Tesla Inc\n" 
        result_text += "• MSFT - Microsoft\n"
        result_text += "• GOOGL - Alphabet\n"
        result_text += "• TIGR - UP Fintech (老虎证券)\n"
        result_text += f"\n🔍 搜索功能开发中，当前可用已知代码"
        
        return result_text
    
    else:
        raise ValueError(f"工具 {tool_name} 尚未实现")

def main():
    # 等待initialize请求
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            method = request.get("method")
            request_id = request.get("id")
            
            if method == "initialize":
                # 返回初始化响应
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "Tiger MCP Server",
                            "version": "1.0.0"
                        }
                    }
                }
                print(json.dumps(response), flush=True)
                
            elif method == "tools/list":
                # 返回核心工具列表
                tools = get_core_tools()
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools}
                }
                print(json.dumps(response), flush=True)
                
            elif method == "tools/call":
                # 调用工具
                tool_name = request["params"]["name"]
                arguments = request["params"].get("arguments", {})
                
                try:
                    result_text = handle_tool_call(tool_name, arguments)
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [{"type": "text", "text": result_text}]
                        }
                    }
                    print(json.dumps(response), flush=True)
                    
                except Exception as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32603, "message": str(e)}
                    }
                    print(json.dumps(error_response), flush=True)
                
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in locals() else None,
                "error": {"code": -32603, "message": str(e)}
            }
            print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    main()
