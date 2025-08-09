# Tiger MCP + Claude Code: Quick Start Guide

Get up and running with Tiger MCP server and Claude Code in under 15 minutes.

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] Claude Code installed (`npm install -g @anthropic-ai/claude-code`)
- [ ] Tiger Brokers account with API access
- [ ] Tiger API credentials ready

## 🚀 Quick Setup (15 minutes)

### Step 1: Clone and Install (3 minutes)

```bash
# Clone repository
git clone <your-repository-url>
cd tiger-mcp

# Install UV package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Step 2: Configure Credentials (5 minutes)

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your Tiger credentials
nano .env  # or use your preferred editor
```

**Required .env settings:**
```bash
TIGER_CLIENT_ID=your_client_id_here
TIGER_PRIVATE_KEY=your_private_key_content_here
TIGER_ACCOUNT=your_account_number_here
TIGER_SANDBOX=true  # IMPORTANT: Start with sandbox!
TIGER_LICENSE=TBHK
LOG_LEVEL=INFO
```

### Step 3: Add to Claude Code (2 minutes)

```bash
# Navigate to your project directory (where you want to use Tiger MCP)
cd /path/to/your/project

# Add Tiger MCP server to Claude Code
claude mcp add tiger-trading \
  --env TIGER_CLIENT_ID="$(grep TIGER_CLIENT_ID /path/to/tiger-mcp/.env | cut -d'=' -f2)" \
  --env TIGER_PRIVATE_KEY="$(grep TIGER_PRIVATE_KEY /path/to/tiger-mcp/.env | cut -d'=' -f2)" \
  --env TIGER_ACCOUNT="$(grep TIGER_ACCOUNT /path/to/tiger-mcp/.env | cut -d'=' -f2)" \
  --env TIGER_SANDBOX="true" \
  --env LOG_LEVEL="INFO" \
  -- uv run --package mcp-server python /path/to/tiger-mcp/mcp-server/server.py
```

### Step 4: Test Connection (2 minutes)

```bash
# Start Claude Code
claude

# Test the connection
```

In Claude Code, run:
```
> Test my Tiger MCP connection and show available tools
```

### Step 5: First Trading Query (3 minutes)

Try these example queries:

```bash
# Get account information
> Show my Tiger trading account information

# Get market data
> Get current market data for AAPL and MSFT

# Check portfolio (if you have positions)
> Show my current portfolio positions

# Market analysis
> Scan the market for today's top 5 gainers
```

## ✅ Verification Checklist

After setup, verify these work:

- [ ] `> Get Tiger account info` - Shows your account details
- [ ] `> Get market data for AAPL` - Returns current AAPL price
- [ ] `> List available Tiger MCP tools` - Shows all trading tools
- [ ] `> Validate Tiger connection` - Reports successful connection

## 🛠️ Quick Troubleshooting

**Connection Failed?**
```bash
# Check credentials
> Use mcp__tiger-trading__get_tiger_config

# Test connection manually
> Use mcp__tiger-trading__validate_tiger_connection
```

**Tools Not Found?**
```bash
# List MCP servers
claude mcp list

# Check specific server
claude mcp get tiger-trading
```

**Authentication Issues?**
1. Verify Tiger Brokers account has API enabled
2. Check private key format (should include `-----BEGIN` and `-----END`)
3. Ensure TIGER_SANDBOX=true for testing

## 📋 Essential Commands

```bash
# Claude Code MCP Management
claude mcp list                    # List all servers
claude mcp get tiger-trading       # Check Tiger server details
claude mcp remove tiger-trading    # Remove server (if needed)

# In Claude Code Session
> Get account info                 # Account details
> Get market data for [SYMBOL]     # Real-time quotes
> Show portfolio                   # Current positions
> Scan market for top gainers      # Market screening
```

## 🔄 Next Steps

1. **Explore Examples**: See [CLAUDE_CODE_INTEGRATION.md](CLAUDE_CODE_INTEGRATION.md) for detailed usage examples
2. **Advanced Setup**: Configure multi-account support, Docker deployment
3. **Production Ready**: Switch to production environment (TIGER_SANDBOX=false)
4. **Security**: Review security best practices in the full guide

## 🆘 Need Help?

- **Full Documentation**: [CLAUDE_CODE_INTEGRATION.md](CLAUDE_CODE_INTEGRATION.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **API Reference**: [API_REFERENCE.md](API_REFERENCE.md)
- **Issues**: GitHub Issues page

---

**🚨 Safety Reminder**: Always start with `TIGER_SANDBOX=true` and test thoroughly before switching to production trading!