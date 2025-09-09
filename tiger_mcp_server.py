#!/usr/bin/env python3
"""
Tiger MCP Server
Professional Tiger Brokers MCP integration
"""

import json
import sys
import requests

def mcp_response(request_id, result):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }

def mcp_error(request_id, code, message):
    return {
        "jsonrpc": "2.0", 
        "id": request_id,
        "error": {"code": code, "message": message}
    }

def call_tiger_api(endpoint, data):
    """调用Tiger REST API"""
    try:
        response = requests.post(
            f"http://localhost:9000/tiger/{endpoint}",
            headers={"Authorization": "Bearer client_key_demo", "Content-Type": "application/json"},
            json=data,
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    # 发送初始化响应
    init_response = mcp_response(None, {
        "protocolVersion": "1.0.0",
        "serverInfo": {
            "name": "Tiger MCP Server",
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {}
        }
    })
    print(json.dumps(init_response), flush=True)
    
    # 处理请求
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
                            "properties": {
                                "account_id": {"type": "string", "description": "账户ID"}
                            }
                        }
                    },
                    {
                        "name": "tiger_get_account_info", 
                        "description": "获取Tiger账户资产信息",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "account_id": {"type": "string", "description": "账户ID"}
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
                                "price": {"type": "number", "description": "价格"}
                            },
                            "required": ["symbol", "side", "quantity", "order_type"]
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
                    
                    response = mcp_response(request_id, {
                        "content": [{"type": "text", "text": result_text}]
                    })
                    
                elif tool_name == "tiger_get_account_info":
                    account = arguments.get("account_id", "20240830213609658")
                    api_result = call_tiger_api("get_account_info", {"account": account})
                    
                    if api_result["success"]:
                        data = api_result["data"]
                        result_text = f"💰 Tiger账户信息 (账户: {account})\n\n"
                        result_text += f"总资产: ${data.get('total_assets', 0):,.2f}\n"
                        result_text += f"现金余额: ${data.get('cash_balance', 0):,.2f}\n"
                        result_text += f"购买力: ${data.get('buying_power', 0):,.2f}\n"
                        result_text += f"持仓价值: ${data.get('gross_position_value', 0):,.2f}\n"
                        result_text += f"未实现盈亏: ${data.get('unrealized_pnl', 0):,.2f}\n"
                        result_text += f"当日盈亏: ${data.get('today_pnl', 0):,.2f}"
                    else:
                        result_text = f"❌ 获取账户信息失败: {api_result['error']}"
                    
                    response = mcp_response(request_id, {
                        "content": [{"type": "text", "text": result_text}]
                    })
                    
                elif tool_name == "tiger_place_order":
                    account = arguments.get("account_id", "20240830213609658")
                    
                    order_data = {
                        "account": account,
                        "symbol": arguments["symbol"],
                        "side": arguments["side"], 
                        "quantity": arguments["quantity"],
                        "order_type": arguments["order_type"]
                    }
                    
                    if arguments.get("price"):
                        order_data["price"] = arguments["price"]
                    
                    api_result = call_tiger_api("place_order", order_data)
                    
                    if api_result["success"]:
                        data = api_result["data"]
                        result_text = f"✅ 订单提交成功\n\n"
                        result_text += f"订单ID: {data['order_id']}\n"
                        result_text += f"股票: {data['symbol']}\n"
                        result_text += f"操作: {data['side']} {data['quantity']} 股\n"
                        result_text += f"类型: {data['order_type']}\n"
                        if data.get('price'):
                            result_text += f"价格: ${data['price']:.2f}\n"
                        result_text += f"账户: {account}"
                    else:
                        result_text = f"❌ 下单失败: {api_result['error']}"
                    
                    response = mcp_response(request_id, {
                        "content": [{"type": "text", "text": result_text}]
                    })
                    
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