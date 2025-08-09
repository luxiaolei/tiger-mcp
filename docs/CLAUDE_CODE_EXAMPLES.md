# Tiger MCP + Claude Code: Usage Examples & Workflows

Practical examples and workflows for using Tiger MCP server with Claude Code for trading, analysis, and portfolio management.

## Table of Contents

1. [Getting Started Examples](#getting-started-examples)
2. [Market Analysis Workflows](#market-analysis-workflows)
3. [Portfolio Management](#portfolio-management)
4. [Trading Operations](#trading-operations)
5. [Risk Management](#risk-management)
6. [Research & Analysis](#research--analysis)
7. [Automated Workflows](#automated-workflows)
8. [Advanced Use Cases](#advanced-use-cases)

## Getting Started Examples

### Basic Connection and Setup

#### Example 1: First Connection Test

```bash
# Start Claude Code
claude

# In Claude Code, test the connection
> Test my Tiger MCP connection and show me what's available
```

**Expected Response**:
```
✅ Tiger MCP Connection Test Results:

📊 Server Status: Connected
🔑 Authentication: Valid 
🏦 Account: SANDBOX-12345 (TBHK)
💰 Environment: Sandbox Mode

🛠️ Available Tools:
- get_account_info: Account details and balances
- get_portfolio: Portfolio positions and P&L
- get_market_data: Real-time market quotes  
- place_order: Execute trading orders
- get_order_status: Check order status
- scan_market: Market screening and scanning
- get_historical_data: Historical price data
- validate_tiger_connection: Connection diagnostics

✅ Connection test successful! Ready for trading operations.
```

#### Example 2: Account Overview

```bash
> Show me a comprehensive overview of my Tiger trading account
```

**Sample Query Response**:
```
🏦 Tiger Trading Account Overview

Account Details:
- Account ID: SANDBOX-12345
- License: TBHK (Hong Kong)
- Environment: Sandbox
- Currency: USD

💰 Account Balances:
- Total Cash: $50,000.00
- Buying Power: $100,000.00 (2:1 leverage)
- Net Liquidation Value: $52,450.00
- Equity Value: $52,450.00

📊 Today's Performance:
- Daily P&L: +$245.00 (+0.48%)
- Unrealized P&L: +$2,450.00
- Realized P&L: $0.00

🔄 Recent Activity: 3 trades this week
```

### Basic Market Data Queries

#### Example 3: Real-time Quotes

```bash
# Single stock quote
> Get the current market data for Apple (AAPL)

# Multiple stocks
> Get market data for AAPL, MSFT, GOOGL, AMZN and TSLA

# With analysis
> Get market data for the FAANG stocks and analyze which ones are performing best today
```

#### Example 4: Market Overview

```bash
> Give me a market overview: show me the top 5 gainers, top 5 losers, and most active stocks today
```

## Market Analysis Workflows

### Technical Analysis Workflow

#### Example 5: Comprehensive Stock Analysis

```bash
> Perform a comprehensive analysis of NVIDIA (NVDA):
1. Get current market data and today's performance
2. Fetch 30 days of historical data
3. Analyze the trend and key support/resistance levels  
4. Check recent volume patterns
5. Provide a technical outlook and key levels to watch
```

**Expected Analysis Output**:
```
📊 NVIDIA (NVDA) - Comprehensive Technical Analysis

Current Market Data:
- Price: $485.50 (+$12.30, +2.60%)
- Volume: 45.2M (Above average)
- Day Range: $472.00 - $487.90
- Previous Close: $473.20

📈 30-Day Technical Analysis:
- Trend: Strong Uptrend (+18.5% over 30 days)
- Support Levels: $460, $445, $420
- Resistance Levels: $490, $510, $525
- Moving Averages: Above 20-day ($465) and 50-day ($440)

📊 Volume Analysis:
- Average Volume: 32M
- Recent Volume Surge: +41% above average
- Volume-Price Correlation: Positive (bullish sign)

🎯 Technical Outlook:
- Short-term: Bullish momentum with potential test of $490 resistance
- Key Levels: Watch for breakout above $490 or support at $460
- Volume Pattern: Strong institutional interest evident
```

#### Example 6: Sector Comparison

```bash
> Compare the tech giants AAPL, MSFT, GOOGL, AMZN, and META:
1. Get current market data for all
2. Calculate their 30-day performance  
3. Compare their relative strength
4. Identify the best and worst performers
5. Suggest which might be good investment opportunities
```

### Market Screening Workflows

#### Example 7: Finding Trading Opportunities

```bash
> Help me find potential trading opportunities:
1. Scan for today's top 10 gainers in the US market
2. Filter for stocks with volume > 1M shares
3. Get detailed data for the most interesting candidates
4. Analyze which ones have sustainable momentum vs. one-day spikes
```

#### Example 8: Value Screening

```bash
> Screen the market for undervalued opportunities:
1. Find stocks that are down >5% this week but up >10% this month
2. Check their recent volume to ensure liquidity
3. Get fundamental data for the top candidates
4. Identify potential value plays vs. falling knives
```

## Portfolio Management

### Portfolio Analysis and Monitoring

#### Example 9: Portfolio Health Check

```bash
> Perform a complete portfolio health check:
1. Show my current positions with market values
2. Calculate my sector allocation and concentration risk
3. Identify my best and worst performing positions
4. Analyze my portfolio's correlation to major indices
5. Suggest any rebalancing needs
```

#### Example 10: Performance Tracking

```bash
> Analyze my portfolio performance:
1. Show my positions with entry dates and costs
2. Calculate unrealized gains/losses for each position
3. Compare my performance to SPY benchmark
4. Identify which positions are helping vs. hurting performance
5. Suggest position sizing adjustments
```

#### Example 11: Risk Assessment

```bash
> Assess my portfolio risk profile:
1. Show my current position sizes as % of portfolio
2. Identify any over-concentrated positions (>10% of portfolio)
3. Analyze sector/geographic diversification
4. Calculate portfolio beta and volatility metrics
5. Recommend risk management adjustments
```

### Rebalancing Workflows

#### Example 12: Portfolio Rebalancing

```bash
> Help me rebalance my portfolio to target allocation:
- Tech: 40% (currently 55%)
- Healthcare: 20% (currently 15%)  
- Finance: 20% (currently 20%)
- Consumer: 15% (currently 10%)
- Cash: 5% (currently 0%)

Show me specific buy/sell recommendations to achieve these targets.
```

## Trading Operations

⚠️ **IMPORTANT**: All trading examples assume SANDBOX mode. Never execute real trades without thorough testing!

### Order Placement Workflows

#### Example 13: Basic Order Entry

```bash
# Market order (sandbox only!)
> Place a market buy order for 100 shares of AAPL in sandbox mode

# Limit order
> Place a limit buy order for 50 shares of MSFT at $420.00 in sandbox mode

# Stop-loss order
> Place a stop-loss sell order for my 200 shares of TSLA at $240.00
```

#### Example 14: Strategic Order Placement

```bash
> I want to build a position in Microsoft (MSFT):
1. Current price is $425, I want to buy 300 shares total
2. Place 100 shares at market to start the position  
3. Place limit orders for 100 shares at $420 and 100 shares at $415
4. Set a stop-loss at $400 for the entire planned position
5. Show me the risk/reward profile of this strategy
```

#### Example 15: Options-Style Bracket Orders

```bash
> Create a bracket order strategy for AAPL:
1. Buy 200 shares at current market price
2. Set a profit target at +5% from entry
3. Set a stop-loss at -3% from entry  
4. Calculate the risk/reward ratio
5. Show me the exact order prices and expected outcomes
```

### Order Management

#### Example 16: Order Status Monitoring

```bash
# Check all orders
> Show me all my pending orders with their current status

# Check specific order
> Check the status of my AAPL buy order placed this morning

# Order history
> Show me all my orders from the past week with fill status
```

#### Example 17: Order Modification

```bash
> I have a pending limit buy order for GOOGL at $140. The stock is now at $142.50:
1. Show me the current order status
2. Recommend whether to cancel, modify, or keep the order
3. If modifying, suggest a new price based on current market conditions
4. Explain the reasoning behind your recommendation
```

## Risk Management

### Position Monitoring

#### Example 18: Stop-Loss Management

```bash
> Review my positions for stop-loss protection:
1. Show positions without stop-losses
2. Suggest appropriate stop-loss levels for each (based on volatility)
3. Calculate the maximum risk per position
4. Recommend position sizes based on 2% portfolio risk rule
5. Show me how to place the protective orders
```

#### Example 19: Position Size Optimization

```bash
> Help me optimize position sizes based on risk management:
1. Show my current positions as % of total portfolio
2. Identify positions that exceed 5% concentration limit
3. Calculate optimal position sizes using 1% risk per trade rule
4. Suggest specific buy/sell actions to optimize sizing
5. Show the before/after portfolio allocation
```

### Risk Monitoring Alerts

#### Example 20: Daily Risk Check

```bash
> Perform my daily risk management check:
1. Show any positions down >10% from entry
2. Calculate my portfolio's beta and volatility  
3. Check for any over-concentrated sectors (>25%)
4. Identify positions approaching stop-loss levels
5. Alert me to any unusual market movements affecting my holdings
6. Recommend any protective actions needed
```

## Research & Analysis

### Fundamental Analysis Integration

#### Example 21: Stock Research Workflow

```bash
> Research Tesla (TSLA) as a potential investment:
1. Get current market data and valuation metrics
2. Analyze recent price action and technical setup
3. Check for any recent news or events affecting the stock
4. Compare valuation to industry peers (Ford, GM)
5. Assess the risk/reward profile for a new position
6. Recommend position size if bullish, or reasons to avoid if bearish
```

#### Example 22: Earnings Season Preparation

```bash
> Prepare for earnings season - analyze my holdings:
1. Show which of my positions have earnings coming up this week
2. Get historical earnings reaction data for each
3. Assess current option implied volatility vs. historical moves
4. Recommend protective strategies (hedge, trim, or hold through)
5. Calculate potential impact on portfolio if positions move ±10%
```

### Market Intelligence

#### Example 23: Market Regime Analysis

```bash
> Analyze the current market environment and its impact on my strategy:
1. Get market data for major indices (SPY, QQQ, IWM)
2. Analyze sector rotation patterns
3. Check VIX levels and market sentiment indicators
4. Compare current levels to 3-month and 1-year ranges
5. Recommend portfolio positioning for current market regime
6. Suggest any tactical adjustments to my holdings
```

## Automated Workflows

### Daily Routines

#### Example 24: Morning Market Briefing

```bash
> Give me my daily morning trading briefing:
1. Market futures and overnight developments
2. My portfolio performance since yesterday's close
3. Any earnings or news affecting my positions
4. Top market movers and unusual volume
5. Economic calendar events for today
6. My watchlist stocks with any significant moves
7. Any pending orders needing attention
```

#### Example 25: End-of-Day Review

```bash
> Perform my end-of-day portfolio review:
1. Show today's portfolio performance vs. market
2. Highlight best and worst performing positions today
3. Check if any positions hit technical levels I'm watching
4. Review any orders that filled today
5. Identify tomorrow's key levels and potential opportunities
6. Update my trading journal with today's key observations
```

### Weekly Analysis Routines

#### Example 26: Weekly Portfolio Review

```bash
> Conduct my weekly portfolio review and planning:
1. Calculate week's performance vs. benchmarks (SPY, QQQ)
2. Review position changes and new positions added
3. Analyze which sectors/stocks contributed most to performance
4. Check portfolio allocation vs. target weights
5. Identify any positions needing attention or review
6. Plan next week's potential trades and watchlist updates
7. Update risk management rules based on recent performance
```

## Advanced Use Cases

### Multi-Timeframe Analysis

#### Example 27: Swing Trading Setup

```bash
> Help me identify a swing trading setup for next week:
1. Scan for stocks breaking out of consolidation patterns
2. Filter for stocks with strong fundamentals and momentum
3. Analyze daily and weekly charts for best entries
4. Calculate risk/reward for top 3 candidates
5. Suggest entry, target, and stop-loss levels
6. Recommend position sizing for 2% portfolio risk per trade
```

### Integration with External Analysis

#### Example 28: News-Driven Trading

```bash
> A major tech company just announced strong earnings. Help me capitalize:
1. Get market data for the company and sector peers
2. Analyze the immediate market reaction and volume
3. Compare the move to historical earnings reactions
4. Identify related stocks that might benefit (suppliers, competitors)
5. Suggest trading strategies: momentum plays vs. contrarian bets
6. Calculate appropriate position sizes and risk management
```

### Advanced Risk Management

#### Example 29: Portfolio Hedging Strategy

```bash
> The market seems vulnerable to a correction. Help me hedge my portfolio:
1. Calculate my portfolio's beta to major indices
2. Identify my highest-risk positions (growth, high-beta stocks)
3. Suggest hedging strategies: index puts, VIX calls, or inverse ETFs
4. Calculate hedge ratios to protect 80% of my downside
5. Show the cost of hedging vs. potential protection
6. Recommend the most cost-effective hedging approach
```

#### Example 30: Stress Testing

```bash
> Stress test my portfolio for various market scenarios:
1. Calculate impact of -20% market correction
2. Model sector rotation from growth to value
3. Analyze impact of rising interest rates on my holdings
4. Show how my portfolio would perform in different market regimes
5. Identify most vulnerable positions in each scenario
6. Recommend portfolio adjustments to improve resilience
```

## Pro Tips for Effective Usage

### Best Practices

1. **Always Start with Questions**: Frame your requests as questions to get analytical responses
2. **Be Specific**: Provide specific symbols, timeframes, and criteria
3. **Chain Operations**: Use numbered lists for multi-step workflows
4. **Sandbox First**: Always test trading operations in sandbox mode
5. **Risk Management**: Include risk parameters in all trading requests

### Power User Commands

```bash
# Quick portfolio snapshot
> Quick status: portfolio value, day's P&L, and any positions needing attention

# Market pulse check
> Market pulse: indices, VIX, sector leaders, and my watchlist status

# Risk check
> Risk alert: show any positions down >5%, approaching stops, or over-concentrated

# Opportunity scanner  
> Opportunities: scan for setups matching my trading criteria and risk tolerance

# Performance summary
> Performance: my return vs. SPY this month, best/worst picks, lessons learned
```

### Keyboard Shortcuts for Claude Code

```bash
# Quick access to common queries
alias mkt="claude -p 'Market overview: indices, top movers, my watchlist'"
alias port="claude -p 'Portfolio summary: value, P&L, and attention needed'"
alias risk="claude -p 'Risk check: stops, concentration, and alerts'"
alias news="claude -p 'Market news affecting my positions and watchlist'"
```

## Sample Trading Session

Here's a complete example of a morning trading session workflow:

```bash
# 1. Morning briefing
> Good morning! Give me my daily trading briefing: market futures, my portfolio overnight performance, any news affecting my positions, and today's economic calendar.

# 2. Position review
> Review my current positions: show any that moved >3% overnight, check if any are approaching technical levels I'm watching, and flag any needing attention.

# 3. Opportunity scanning  
> Scan for today's opportunities: look for stocks with unusual volume, momentum breakouts, and any that fit my swing trading criteria.

# 4. Risk management
> Daily risk check: verify all positions have appropriate stops, check portfolio concentration, and alert me to any risk management issues.

# 5. Order management
> Review my pending orders: check status, recommend any modifications based on current market conditions, and suggest new limit orders for stocks on my watchlist.

# Throughout the day...
> Update me on AAPL - it's moving unusually high on volume
> Check if my MSFT limit order at $420 should be adjusted
> Quick portfolio pulse: how am I doing vs. the market today?

# End of day
> End-of-day summary: today's performance, any trades executed, tomorrow's key levels to watch, and weekend homework assignments.
```

---

## Getting the Most from Tiger MCP

### Optimization Tips

1. **Use Natural Language**: Write queries as you would ask a human analyst
2. **Be Comprehensive**: Ask for analysis, not just data
3. **Include Context**: Mention your investment style, risk tolerance, and goals
4. **Think Multi-Step**: Chain related queries for comprehensive analysis
5. **Verify Important Decisions**: Always double-check before executing real trades

### Advanced Features

- **Portfolio Analytics**: Deep performance attribution analysis
- **Risk Management**: Automated stop-loss and position sizing
- **Market Intelligence**: Sector rotation and regime analysis  
- **Trade Journal**: Automated trade documentation and analysis
- **Backtesting**: Historical performance analysis of strategies

Remember: These examples show the power of combining AI analysis with professional trading tools. Always verify important information and never risk more than you can afford to lose!