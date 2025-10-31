#!/usr/bin/env python3
"""
Tiger MCP Server Module
Professional Tiger Brokers MCP integration
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

REST_API_BASE = os.environ.get("TIGER_REST_API_URL", "http://localhost:9000").rstrip("/")

def mcp_response(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}

def mcp_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

def call_tiger_api(endpoint: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Call the unified REST API and normalize responses."""
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

def main():
    """MCP服务器主函数"""
    # 初始化响应
    init_response = mcp_response(None, {
        "protocolVersion": "1.0.0", 
        "serverInfo": {"name": "Tiger MCP Server", "version": "1.0.0"},
        "capabilities": {"tools": {}}
    })
    print(json.dumps(init_response), flush=True)
    
    # 请求处理循环
    for line in sys.stdin:
        try:
            line = line.strip()
            if not line:
                continue
                
            request = json.loads(line)
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id")
            
            if method == "tools/list":
                tools = [
                    {
                        "name": "tiger_get_positions",
                        "description": "获取Tiger账户持仓信息",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"account_id": {"type": "string", "description": "账户ID"}}
                        }
                    },
                    {
                        "name": "tiger_get_account_info", 
                        "description": "获取Tiger账户资产信息",
                        "inputSchema": {
                            "type": "object", 
                            "properties": {"account_id": {"type": "string", "description": "账户ID"}}
                        }
                    }
                ]
                
                response = mcp_response(request_id, {"tools": tools})
                print(json.dumps(response), flush=True)
                
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "tiger_get_positions":
                    account = arguments.get("account_id", "20240830213609658")
                    api_result = call_tiger_api("get_positions", {"account": account})
                    
                    if api_result["success"]:
                        positions = api_result["data"]["positions"]
                        result_text = f"📊 Tiger持仓 (账户: {account})\\n\\n"
                        
                        if positions:
                            for pos in positions:
                                pnl_icon = "📈" if pos["unrealized_pnl"] >= 0 else "📉"
                                result_text += f"{pnl_icon} {pos['symbol']}: {pos['quantity']} 股\\n"
                                result_text += f"   ${pos['average_cost']:.2f} → ${pos['market_price']:.4f} (盈亏: ${pos['unrealized_pnl']:.2f})\\n\\n"
                        else:
                            result_text += "当前无持仓"
                    else:
                        result_text = f"❌ 错误: {api_result['error']}"
                    
                    response = mcp_response(request_id, {"content": [{"type": "text", "text": result_text}]})
                    
                elif tool_name == "tiger_get_account_info":
                    account = arguments.get("account_id", "20240830213609658")
                    api_result = call_tiger_api("get_account_info", {"account": account})
                    
                    if api_result["success"]:
                        data = api_result["data"]
                        result_text = f"💰 Tiger账户 (账户: {account})\\n\\n"
                        result_text += f"净资产: ${data.get('net_liquidation', 0):,.2f}\\n"
                        result_text += f"现金: ${data.get('cash_balance', 0):,.2f}\\n"
                        result_text += f"购买力: ${data.get('buying_power', 0):,.2f}\\n"
                        result_text += f"持仓价值: ${data.get('gross_position_value', 0):,.2f}\\n"
                        result_text += f"未实现盈亏: ${data.get('unrealized_pnl', 0):,.2f}\\n"
                        result_text += f"已实现盈亏: ${data.get('realized_pnl', 0):,.2f}"
                    else:
                        result_text = f"❌ 错误: {api_result['error']}"
                    
                    response = mcp_response(request_id, {"content": [{"type": "text", "text": result_text}]})
                    
                else:
                    response = mcp_error(request_id, -32601, f"工具 {tool_name} 不存在")
                
                print(json.dumps(response), flush=True)
                
            else:
                response = mcp_error(request_id, -32601, f"未知方法: {method}")
                print(json.dumps(response), flush=True)
                
        except Exception as e:
            error_response = mcp_error(request.get("id") if 'request' in locals() else None, -32603, str(e))
            print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    main()
