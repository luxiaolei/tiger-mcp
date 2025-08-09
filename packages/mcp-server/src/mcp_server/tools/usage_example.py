"""
Example usage of Tiger MCP Data and Info tools.

Demonstrates how to use the MCP tools for various data retrieval operations.
"""

import asyncio
import sys
from datetime import datetime

# Add paths for imports
sys.path.insert(
    0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/shared/src"
)

from loguru import logger

# Import MCP tools
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


async def demonstrate_data_tools():
    """Demonstrate usage of data tools."""
    print("\n" + "=" * 60)
    print("TIGER MCP DATA TOOLS DEMONSTRATION")
    print("=" * 60)

    # 1. Get real-time quote
    print("\n1. Getting real-time quote for AAPL...")
    quote_response = await tiger_get_quote("AAPL")
    if quote_response.success:
        data = quote_response.data
        print(f"   AAPL Quote: ${data['latest_price']:.2f}")
        print(f"   Change: {data['change']:.2f} ({data['change_rate']:.2f}%)")
        print(f"   Volume: {data['volume']:,}")
    else:
        print(f"   Error: {quote_response.error}")

    # 2. Get historical data
    print("\n2. Getting historical daily data for TSLA (last 10 days)...")
    kline_response = await tiger_get_kline("TSLA", "1d", 10)
    if kline_response.success:
        print(f"   Retrieved {len(kline_response.data)} bars")
        if kline_response.data:
            latest = kline_response.data[-1]
            print(
                f"   Latest bar: O=${latest['open']:.2f} H=${latest['high']:.2f} L=${latest['low']:.2f} C=${latest['close']:.2f}"
            )
    else:
        print(f"   Error: {kline_response.error}")

    # 3. Get batch market data
    print("\n3. Getting batch market data for tech stocks...")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    market_response = await tiger_get_market_data(symbols)
    if market_response.success:
        for symbol, data in market_response.data.items():
            print(
                f"   {symbol}: ${data['latest_price']:.2f} ({data['change_rate']:+.2f}%)"
            )
    else:
        print(f"   Error: {market_response.error}")

    # 4. Search symbols
    print("\n4. Searching for 'tesla' symbols...")
    search_response = await tiger_search_symbols("tesla", "US")
    if search_response.success:
        print(f"   Found {len(search_response.data)} results:")
        for result in search_response.data[:3]:  # Show first 3 results
            print(f"   - {result['symbol']}: {result['name']} ({result['market']})")
    else:
        print(f"   Error: {search_response.error}")

    # 5. Get option chain
    print("\n5. Getting option chain for SPY...")
    option_response = await tiger_get_option_chain("SPY")
    if option_response.success:
        calls = option_response.data.get("calls", [])
        puts = option_response.data.get("puts", [])
        print(f"   Found {len(calls)} calls and {len(puts)} puts")
        print(
            f"   Underlying price: ${option_response.data.get('underlying_price', 0):.2f}"
        )
    else:
        print(f"   Error: {option_response.error}")

    # 6. Get market status
    print("\n6. Getting US market status...")
    status_response = await tiger_get_market_status("US")
    if status_response.success:
        status = status_response.data["status"]
        print(f"   Market Status: {status}")
        print(f"   Trading Day: {status_response.data['is_trading_day']}")
    else:
        print(f"   Error: {status_response.error}")


async def demonstrate_info_tools():
    """Demonstrate usage of info tools."""
    print("\n" + "=" * 60)
    print("TIGER MCP INFO TOOLS DEMONSTRATION")
    print("=" * 60)

    # 1. Get contract details
    print("\n1. Getting contract details for major stocks...")
    contract_response = await tiger_get_contracts(["AAPL", "TSLA", "SPY"])
    if contract_response.success:
        for symbol, contract in contract_response.data.items():
            print(f"   {symbol}:")
            print(f"     Type: {contract['sec_type']}")
            print(f"     Exchange: {contract['exchange']}")
            print(f"     Currency: {contract['currency']}")
            print(f"     Lot Size: {contract['lot_size']}")
    else:
        print(f"   Error: {contract_response.error}")

    # 2. Get financial data
    print("\n2. Getting financial data for AAPL...")
    financial_response = await tiger_get_financials("AAPL")
    if financial_response.success:
        data = financial_response.data
        print(f"   Market Cap: ${data['market_cap']:,.0f}")
        print(f"   P/E Ratio: {data['pe_ratio']:.2f}")
        print(f"   Dividend Yield: {data['dividend_yield']:.2f}%")
        print(f"   EPS: ${data['eps']:.2f}")
        print(f"   Revenue: ${data['revenue']:,.0f}")
    else:
        print(f"   Error: {financial_response.error}")

    # 3. Get corporate actions
    print("\n3. Getting corporate actions for MSFT...")
    actions_response = await tiger_get_corporate_actions("MSFT")
    if actions_response.success:
        actions = actions_response.data
        print(f"   Found {len(actions)} corporate actions:")
        for action in actions[:3]:  # Show first 3 actions
            print(f"   - {action['action_type']}: {action['description']}")
            if action["ex_date"]:
                print(f"     Ex-Date: {action['ex_date']}")
    else:
        print(f"   Error: {actions_response.error}")

    # 4. Get earnings data
    print("\n4. Getting earnings data for GOOGL...")
    earnings_response = await tiger_get_earnings("GOOGL")
    if earnings_response.success:
        data = earnings_response.data
        print(f"   Last EPS: ${data['last_reported_eps']:.2f}")
        print(f"   Estimated EPS: ${data['estimated_eps']:.2f}")
        print(f"   Last Report: {data['last_report_date']}")
        print(f"   Next Report: {data['next_report_date']}")
        print(f"   Annual Growth: {data['annual_growth']:.2f}%")
    else:
        print(f"   Error: {earnings_response.error}")


async def main():
    """Main demonstration function."""
    try:
        print("Tiger MCP Tools Usage Examples")
        print("=" * 40)
        print(f"Started at: {datetime.now()}")

        # Demonstrate data tools
        await demonstrate_data_tools()

        # Demonstrate info tools
        await demonstrate_info_tools()

        print("\n" + "=" * 60)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        print(f"\nDemonstration failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
