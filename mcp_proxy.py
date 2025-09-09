#!/usr/bin/env python3
"""
简单的MCP代理服务器
通过MCP协议提供Tiger MCP工具，内部调用REST API
"""

import json
import sys
import requests
from typing import Any, Dict, List, Optional, Union

# 简化的MCP实现 - 避免FastMCP的异步冲突
class SimpleMCPServer:
    def __init__(self):
        self.tools = {}
        self.rest_api_url = "http://localhost:9000"
        self.api_key = "client_key_demo"
        self.default_account = "20240830213609658"
    
    def tool(self, name: str, description: str):
        """注册工具装饰器"""
        def decorator(func):
            self.tools[name] = {
                "function": func,
                "description": description,
                "schema": self._generate_schema(func)
            }
            return func
        return decorator
    
    def _generate_schema(self, func):
        """生成工具的简单schema"""
        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": func.__doc__ or "Tiger MCP tool"
            }
        }
    
    def _call_rest_api(self, endpoint: str, data: dict) -> dict:
        """调用REST API"""
        try:
            response = requests.post(
                f"{self.rest_api_url}/tiger/{endpoint}",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=data,
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_stdio(self):
        """运行STDIO MCP服务器"""
        print('{"jsonrpc": "2.0", "method": "initialize", "result": {"protocolVersion": "1.0.0", "serverInfo": {"name": "Tiger MCP Server", "version": "1.0.0"}}}', flush=True)
        
        # 简单的请求处理循环
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                method = request.get("method")
                params = request.get("params", {})
                request_id = request.get("id")
                
                if method == "tools/list":
                    # 返回可用工具列表
                    tools_list = []
                    for tool_name, tool_info in self.tools.items():
                        tools_list.append({
                            "name": tool_name,
                            "description": tool_info["description"],
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        })
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"tools": tools_list}
                    }
                    print(json.dumps(response), flush=True)
                
                elif method == "tools/call":
                    # 调用工具
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})
                    
                    if tool_name in self.tools:
                        try:
                            result = self.tools[tool_name]["function"](**tool_args)
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
                            }
                        except Exception as e:
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {"code": -32603, "message": str(e)}
                            }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32601, "message": f"Tool {tool_name} not found"}
                        }
                    
                    print(json.dumps(response), flush=True)
                
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if 'request' in locals() else None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                print(json.dumps(error_response), flush=True)

# 创建MCP服务器实例
mcp = SimpleMCPServer()

@mcp.tool("tiger_get_positions", "获取Tiger账户持仓信息")
def tiger_get_positions(account_id: Optional[str] = None) -> Dict[str, Any]:
    """获取当前持仓信息"""
    account = account_id or mcp.default_account
    result = mcp._call_rest_api("get_positions", {"account": account})
    
    if result["success"]:
        positions = result["data"]["positions"]
        formatted_positions = []
        total_value = 0
        total_pnl = 0
        
        for pos in positions:
            market_value = pos["quantity"] * pos["market_price"]
            total_value += market_value
            total_pnl += pos["unrealized_pnl"]
            
            formatted_positions.append({
                "股票": pos["symbol"],
                "数量": pos["quantity"],
                "均价": f"${pos['average_cost']:.2f}",
                "现价": f"${pos['market_price']:.4f}",
                "市值": f"${market_value:.2f}",
                "盈亏": f"${pos['unrealized_pnl']:.2f}"
            })
        
        return {
            "账户": account,
            "持仓列表": formatted_positions,
            "总市值": f"${total_value:.2f}",
            "总盈亏": f"${total_pnl:.2f}",
            "持仓数量": len(formatted_positions)
        }
    else:
        return {"错误": result["error"]}

@mcp.tool("tiger_get_account_info", "获取Tiger账户资产信息")
def tiger_get_account_info(account_id: Optional[str] = None) -> Dict[str, Any]:
    """获取账户资产详情"""
    account = account_id or mcp.default_account
    result = mcp._call_rest_api("get_account_info", {"account": account})
    
    if result["success"]:
        data = result["data"]
        return {
            "账户号": data["account_id"],
            "总资产": f"${data.get('total_assets', 0):,.2f}",
            "现金余额": f"${data.get('cash_balance', 0):,.2f}",
            "购买力": f"${data.get('buying_power', 0):,.2f}",
            "持仓价值": f"${data.get('gross_position_value', 0):,.2f}",
            "未实现盈亏": f"${data.get('unrealized_pnl', 0):,.2f}",
            "当日盈亏": f"${data.get('today_pnl', 0):,.2f}"
        }
    else:
        return {"错误": result["error"]}

@mcp.tool("tiger_place_order", "提交Tiger交易订单")
def tiger_place_order(
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "MKT",
    price: Optional[float] = None,
    account_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    下交易订单
    
    Args:
        symbol: 股票代码 (如 AAPL)
        side: 买卖方向 (BUY/SELL)
        quantity: 数量
        order_type: 订单类型 (MKT/LMT)
        price: 限价单价格
        account_id: 账户ID
    """
    account = account_id or mcp.default_account
    
    order_data = {
        "account": account,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "order_type": order_type
    }
    
    if price:
        order_data["price"] = price
    
    result = mcp._call_rest_api("place_order", order_data)
    
    if result["success"]:
        data = result["data"]
        return {
            "订单状态": "提交成功",
            "订单ID": data["order_id"],
            "股票": data["symbol"],
            "操作": data["side"],
            "数量": data["quantity"],
            "类型": data["order_type"],
            "价格": f"${data.get('price', 0):.2f}" if data.get("price") else "市价",
            "账户": account
        }
    else:
        return {"错误": result["error"]}

@mcp.tool("tiger_cancel_order", "取消Tiger订单")
def tiger_cancel_order(order_id: str, account_id: Optional[str] = None) -> Dict[str, Any]:
    """取消指定订单"""
    account = account_id or mcp.default_account
    
    result = mcp._call_rest_api("cancel_order", {
        "account": account,
        "order_id": order_id
    })
    
    if result["success"]:
        return {
            "撤单状态": "成功",
            "订单ID": order_id,
            "账户": account
        }
    else:
        return {"错误": result["error"]}

@mcp.tool("tiger_get_market_status", "获取市场交易状态")
def tiger_get_market_status(market: str = "US") -> Dict[str, Any]:
    """获取指定市场的交易状态"""
    # 这个直接调用Tiger SDK，因为不需要特殊权限
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
            return {
                "市场": market,
                "状态": market_info.status,
                "交易状态": market_info.trading_status,
                "是否交易中": market_info.trading_status == "TRADING",
                "开盘时间": str(market_info.open_time) if hasattr(market_info, 'open_time') else "N/A"
            }
        else:
            return {"错误": "无法获取市场状态"}
            
    except Exception as e:
        return {"错误": str(e)}

if __name__ == "__main__":
    print(f"🚀 启动Tiger MCP代理服务器...", file=sys.stderr)
    print(f"📡 REST API: {mcp.rest_api_url}", file=sys.stderr)
    print(f"🔑 API Key: {mcp.api_key}", file=sys.stderr)
    print(f"🏦 默认账户: {mcp.default_account}", file=sys.stderr)
    
    mcp.run_stdio()