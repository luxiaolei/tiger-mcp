# Tiger MCP + Claude Code: Troubleshooting Guide

Comprehensive troubleshooting guide for resolving common issues when integrating Tiger MCP server with Claude Code.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Connection Issues](#connection-issues)
3. [Authentication Problems](#authentication-problems)
4. [Tool Access Issues](#tool-access-issues)
5. [Performance Problems](#performance-problems)
6. [Trading Operation Issues](#trading-operation-issues)
7. [Configuration Problems](#configuration-problems)
8. [Environment Issues](#environment-issues)
9. [Advanced Debugging](#advanced-debugging)
10. [Support Resources](#support-resources)

## Quick Diagnostics

### 30-Second Health Check

Run these commands to quickly identify the most common issues:

```bash
# 1. Check Claude Code installation
claude --version

# 2. List MCP servers
claude mcp list

# 3. Check Tiger MCP server status
claude mcp get tiger-trading

# 4. Test basic connection
claude -p "Test Tiger MCP connection and show me the current status"
```

### Diagnostic Output Interpretation

**✅ Healthy System**:
```
Claude Code version: 1.x.x
MCP Servers: tiger-trading (active)
Tiger MCP: Connected, API: Operational, Account: Active
```

**❌ Problem Indicators**:
```
Error: MCP server not found
Error: Connection timeout
Error: Authentication failed
Error: Tool not available
```

## Connection Issues

### Issue: "MCP Server Not Found"

**Symptoms**:
```
Error: No MCP server named 'tiger-trading'
Error: MCP server tiger-trading is not configured
```

**Diagnosis**:
```bash
# Check if server exists
claude mcp list | grep tiger

# Check server configuration
claude mcp get tiger-trading
```

**Solutions**:

#### Solution 1: Re-add MCP Server
```bash
# Remove existing server
claude mcp remove tiger-trading

# Re-add with correct configuration
claude mcp add tiger-trading \
  --env TIGER_CLIENT_ID="your_client_id" \
  --env TIGER_PRIVATE_KEY="your_private_key" \
  --env TIGER_ACCOUNT="your_account" \
  --env TIGER_SANDBOX="true" \
  -- uv run --package mcp-server python /path/to/tiger-mcp/mcp-server/server.py
```

#### Solution 2: Check Path Configuration
```bash
# Verify the server path exists
ls -la /path/to/tiger-mcp/mcp-server/server.py

# Check if UV is available
which uv

# Test server manually
cd /path/to/tiger-mcp
uv run --package mcp-server python mcp-server/server.py
```

### Issue: "Connection Timeout"

**Symptoms**:
```
Error: Connection timeout after 30 seconds
Error: Failed to start MCP server
Error: Server process died unexpectedly
```

**Diagnosis**:
```bash
# Check server startup
tail -f /var/log/claude/mcp-servers.log

# Monitor server process
ps aux | grep "tiger-mcp\|server.py"

# Check port conflicts
lsof -i :8080  # If using HTTP transport
```

**Solutions**:

#### Solution 1: Increase Timeout
```bash
# Set longer timeout in Claude Code config
claude config set mcp.timeout 60

# Or specify timeout in server addition
claude mcp add tiger-trading --timeout 60 ...
```

#### Solution 2: Check Dependencies
```bash
# Verify Python environment
cd /path/to/tiger-mcp
uv run python --version
uv run pip list | grep fastmcp

# Install missing dependencies
uv sync --all-extras
```

#### Solution 3: Debug Server Startup
```bash
# Run server with debug logging
export LOG_LEVEL=DEBUG
cd /path/to/tiger-mcp
uv run --package mcp-server python mcp-server/server.py

# Check for startup errors
tail -n 50 logs/mcp-server.log
```

### Issue: "Server Process Crashes"

**Symptoms**:
```
Error: Server process exited with code 1
Error: Broken pipe
Error: Connection reset by peer
```

**Diagnosis**:
```bash
# Check server logs
tail -n 100 logs/mcp-server.log

# Check system resources
free -h
df -h
ps aux | head -20
```

**Solutions**:

#### Solution 1: Memory Issues
```bash
# Check memory usage
ps aux --sort=-%mem | head -10

# Increase available memory or reduce usage
export TIGER_CACHE_SIZE=100  # Reduce cache size
export TIGER_MAX_CONNECTIONS=5  # Limit connections
```

#### Solution 2: Permission Issues
```bash
# Check file permissions
ls -la /path/to/tiger-mcp/mcp-server/
chmod +x /path/to/tiger-mcp/mcp-server/server.py

# Check directory permissions
chmod 755 /path/to/tiger-mcp/
```

## Authentication Problems

### Issue: "Invalid Tiger API Credentials"

**Symptoms**:
```
Error: Authentication failed with Tiger Brokers API
Error: Invalid client ID or private key
Error: Account access denied
```

**Diagnosis**:
```bash
# Test credentials directly
claude -p "Use mcp__tiger-trading__get_tiger_config to show current configuration"
claude -p "Use mcp__tiger-trading__validate_tiger_connection to test authentication"
```

**Solutions**:

#### Solution 1: Verify Credentials
```bash
# Check environment variables
env | grep TIGER

# Verify client ID format (should be numeric)
echo $TIGER_CLIENT_ID | grep -E '^[0-9]+$'

# Check private key format
echo "$TIGER_PRIVATE_KEY" | head -1 | grep -E 'BEGIN (RSA )?PRIVATE KEY'
```

#### Solution 2: Private Key Format Issues
```bash
# Convert PK8 to PK1 if needed
openssl rsa -in private_key_pk8.pem -out private_key_pk1.pem

# Verify key validity
openssl rsa -in private_key.pem -check -noout

# Check key matches client ID
# (Manual verification in Tiger Brokers console required)
```

#### Solution 3: Account Status Check
1. **Log into Tiger Brokers**: Verify account is active
2. **Check API Access**: Ensure API access is enabled
3. **Verify Account Number**: Confirm account number matches TIGER_ACCOUNT
4. **Check Permissions**: Ensure account has necessary trading permissions

### Issue: "Sandbox vs Production Mismatch"

**Symptoms**:
```
Error: Account not found in production
Error: Invalid account for sandbox environment
```

**Solutions**:
```bash
# For sandbox testing
export TIGER_SANDBOX=true
export TIGER_ACCOUNT="your_sandbox_account"

# For production use
export TIGER_SANDBOX=false  
export TIGER_ACCOUNT="your_production_account"

# Verify environment
claude -p "Show me which Tiger environment I'm connected to"
```

## Tool Access Issues

### Issue: "MCP Tool Not Available"

**Symptoms**:
```
Error: Tool mcp__tiger-trading__get_account_info not found
Error: Tool access denied
Error: Unknown tool requested
```

**Diagnosis**:
```bash
# List available tools
claude -p "What MCP tools are available from tiger-trading server?"

# Check tool permissions
claude config get permissions
```

**Solutions**:

#### Solution 1: Enable Tool Access
```bash
# Allow all Tiger MCP tools
claude config add permissions.allow "mcp__tiger-trading__*"

# Or allow specific tools only
claude config add permissions.allow "mcp__tiger-trading__get_account_info"
claude config add permissions.allow "mcp__tiger-trading__get_market_data"
```

#### Solution 2: Use Explicit Tool Allowlist
```bash
# Specify allowed tools when running Claude
claude -p "Get my account info" \
  --allowedTools "mcp__tiger-trading__get_account_info"
```

#### Solution 3: Check Tool Implementation
```bash
# Verify tools are properly exposed in server
cd /path/to/tiger-mcp
grep -n "@mcp.tool" mcp-server/server.py
```

### Issue: "Permission Denied for Tool"

**Symptoms**:
```
Error: Permission denied for tool execution
Error: Tool blocked by security policy
```

**Solutions**:
```bash
# Check current permissions
claude config list | grep permissions

# Reset permissions to allow MCP tools
claude config set permissions.allow '["mcp__*"]'

# Remove conflicting deny rules
claude config remove permissions.deny "mcp__tiger-trading__*"
```

## Performance Problems

### Issue: "Slow Response Times"

**Symptoms**:
```
Tool calls taking > 30 seconds
Timeout errors intermittently
Claude appears to hang on Tiger MCP calls
```

**Diagnosis**:
```bash
# Monitor API response times
time claude -p "Get market data for AAPL"

# Check network latency
ping api.tiger.com
traceroute api.tiger.com

# Monitor server resources
top -p $(pgrep -f "tiger-mcp")
```

**Solutions**:

#### Solution 1: Optimize Configuration
```bash
# Enable caching
export TIGER_CACHE_ENABLED=true
export TIGER_CACHE_TTL=60

# Reduce connection timeout
export TIGER_API_TIMEOUT=15

# Limit concurrent requests
export TIGER_MAX_CONCURRENT=3
```

#### Solution 2: Network Optimization
```bash
# Use persistent connections
export TIGER_KEEP_ALIVE=true

# Enable compression
export TIGER_COMPRESSION=gzip

# Configure connection pooling
export TIGER_POOL_SIZE=5
```

### Issue: "Memory Usage Growing"

**Symptoms**:
```
Server memory usage continuously increasing
System becomes sluggish over time
Out of memory errors
```

**Solutions**:
```bash
# Monitor memory usage
watch -n 5 'ps aux | grep tiger-mcp | grep -v grep'

# Configure memory limits
export TIGER_MAX_MEMORY=512M  # Limit server memory

# Enable periodic garbage collection
export TIGER_GC_FREQUENCY=300  # Every 5 minutes

# Restart server periodically
crontab -e
# Add: 0 2 * * * claude mcp restart tiger-trading
```

## Trading Operation Issues

### Issue: "Orders Not Placing"

**Symptoms**:
```
Error: Failed to place order
Error: Order rejected by Tiger Brokers
Error: Invalid order parameters
```

**Diagnosis**:
```bash
# Test order placement in sandbox
claude -p "Place a test order for 1 share of AAPL at market price in sandbox mode"

# Check account status
claude -p "Show my account information and trading permissions"

# Verify market hours
claude -p "Check if the market is currently open for trading"
```

**Solutions**:

#### Solution 1: Order Parameter Validation
```bash
# Verify order parameters
claude -p "Validate these order parameters: 
- Symbol: AAPL
- Action: BUY  
- Quantity: 100
- Order Type: LIMIT
- Price: $150.00"
```

#### Solution 2: Account Permissions
```bash
# Check trading permissions
claude -p "Check my account trading permissions and any restrictions"

# Verify buying power
claude -p "Show my current buying power and available cash"
```

#### Solution 3: Market Status
```bash
# Check market status
claude -p "Check current market status and trading hours"

# Verify symbol validity
claude -p "Verify that AAPL is a valid tradable symbol"
```

### Issue: "Market Data Not Updating"

**Symptoms**:
```
Stale market data (timestamps > 15 minutes old)
No real-time quotes
Empty market data responses
```

**Solutions**:
```bash
# Check market data subscription
claude -p "Test market data access for major symbols like AAPL, MSFT, GOOGL"

# Verify market hours
claude -p "Check current market status and data availability"

# Test with different symbols
claude -p "Get market data for both US and international symbols to test coverage"
```

## Configuration Problems

### Issue: "Environment Variables Not Loading"

**Symptoms**:
```
Server uses default values instead of configured settings
Configuration appears to be ignored
Credentials not found despite being set
```

**Diagnosis**:
```bash
# Check if variables are set
env | grep TIGER | sort

# Test variable access in server
cd /path/to/tiger-mcp
uv run python -c "import os; print('TIGER_CLIENT_ID:', os.getenv('TIGER_CLIENT_ID'))"
```

**Solutions**:
```bash
# Ensure variables are exported
export TIGER_CLIENT_ID="your_client_id"
export TIGER_PRIVATE_KEY="$(cat your_key.pem)"

# Or use .env file
echo "TIGER_CLIENT_ID=your_client_id" > .env
echo "TIGER_PRIVATE_KEY=$(cat your_key.pem)" >> .env

# Add to MCP server configuration
claude mcp add tiger-trading \
  --env TIGER_CLIENT_ID="$TIGER_CLIENT_ID" \
  --env TIGER_PRIVATE_KEY="$TIGER_PRIVATE_KEY" \
  -- uv run --package mcp-server python mcp-server/server.py
```

### Issue: "Multiple Account Configuration"

**Symptoms**:
```
Wrong account being used
Cannot switch between accounts
Account ID not recognized
```

**Solutions**:
```bash
# Set default account
export TIGER_DEFAULT_ACCOUNT_ID="account-uuid-from-database"

# Or configure specific account in server startup
claude mcp add tiger-trading-main \
  --env TIGER_ACCOUNT="primary_account" \
  -- uv run --package mcp-server python mcp-server/server.py

claude mcp add tiger-trading-backup \
  --env TIGER_ACCOUNT="backup_account" \
  -- uv run --package mcp-server python mcp-server/server.py
```

## Environment Issues

### Issue: "Python Version Compatibility"

**Symptoms**:
```
ImportError: cannot import name 'Protocol' from 'typing'
SyntaxError: invalid syntax (async def)
ModuleNotFoundError: No module named 'asyncio'
```

**Solutions**:
```bash
# Check Python version
python --version  # Should be 3.11+

# Update Python if needed
brew install python@3.11  # macOS
sudo apt update && sudo apt install python3.11  # Ubuntu

# Update UV and dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
cd /path/to/tiger-mcp
uv sync --python 3.11
```

### Issue: "Dependency Conflicts"

**Symptoms**:
```
ERROR: Cannot install packages due to conflicting dependencies
ImportError: No module named 'fastmcp'
Version conflict between packages
```

**Solutions**:
```bash
# Clean and reinstall dependencies
cd /path/to/tiger-mcp
rm -rf .venv
uv sync --reinstall

# Check for conflicts
uv pip list --outdated
uv pip check

# Update specific packages
uv add fastmcp@latest
uv add anthropic@latest
```

### Issue: "Claude Code Version Incompatibility"

**Symptoms**:
```
MCP protocol version mismatch
Unsupported MCP server configuration
Claude Code features not available
```

**Solutions**:
```bash
# Update Claude Code
npm update -g @anthropic-ai/claude-code

# Check version compatibility
claude --version
node --version  # Should be 18+

# Reinstall if needed
npm uninstall -g @anthropic-ai/claude-code
npm install -g @anthropic-ai/claude-code@latest
```

## Advanced Debugging

### Comprehensive Debug Mode

```bash
#!/bin/bash
# debug-tiger-mcp.sh - Comprehensive debugging script

echo "🔍 Starting Tiger MCP Debug Session"
echo "=================================="

# 1. Environment Check
echo "Environment Variables:"
env | grep TIGER | sort
echo ""

# 2. System Resources
echo "System Resources:"
echo "Memory: $(free -h | grep Mem)"
echo "Disk: $(df -h / | tail -1)"
echo "Load: $(uptime)"
echo ""

# 3. Network Connectivity
echo "Network Connectivity:"
ping -c 3 api.tiger.com 2>/dev/null && echo "✅ Tiger API reachable" || echo "❌ Tiger API unreachable"
echo ""

# 4. Process Status
echo "Related Processes:"
ps aux | grep -E "(claude|tiger|mcp)" | grep -v grep
echo ""

# 5. Log Analysis
echo "Recent Log Entries:"
tail -20 /var/log/tiger-mcp/audit.log 2>/dev/null || echo "No audit log found"
tail -20 ~/.claude/logs/claude.log 2>/dev/null || echo "No Claude log found"
echo ""

# 6. MCP Configuration
echo "MCP Server Configuration:"
claude mcp list 2>/dev/null || echo "Claude MCP not configured"
echo ""

# 7. Test Connection
echo "Connection Test:"
timeout 30 claude -p "Test Tiger MCP connection" 2>&1 | head -10
echo ""

echo "🏁 Debug session complete"
```

### Log Analysis Tools

```bash
# Analyze Tiger MCP logs for patterns
#!/bin/bash
# analyze-logs.sh

LOG_FILE="/var/log/tiger-mcp/audit.log"

echo "📊 Log Analysis Report"
echo "===================="

# Error frequency
echo "Top Errors:"
grep -i error $LOG_FILE | cut -d' ' -f4- | sort | uniq -c | sort -nr | head -10
echo ""

# API call patterns  
echo "API Call Distribution:"
grep "api_call" $LOG_FILE | awk '{print $5}' | sort | uniq -c | sort -nr
echo ""

# Performance metrics
echo "Response Time Analysis:"
grep "response_time" $LOG_FILE | awk '{sum+=$6; count++} END {print "Average:", sum/count "ms"}'
echo ""

# Security events
echo "Security Events:"
grep -i "unauthorized\|failed\|denied" $LOG_FILE | wc -l
echo ""
```

### Network Debugging

```bash
# Monitor Tiger MCP network traffic
#!/bin/bash
# network-debug.sh

echo "🌐 Network Debug Session"
echo "======================"

# Capture Tiger API traffic
echo "Capturing Tiger API traffic (30 seconds)..."
timeout 30 tcpdump -i any -w tiger-api-capture.pcap host api.tiger.com &
TCPDUMP_PID=$!

# Test API calls during capture
sleep 5
claude -p "Get market data for AAPL to generate API traffic" &

# Wait for capture to complete
wait $TCPDUMP_PID

# Analyze capture
echo "Traffic Analysis:"
tcpdump -r tiger-api-capture.pcap -n | head -20

# Check SSL/TLS details
echo "SSL/TLS Analysis:"
echo | openssl s_client -connect api.tiger.com:443 -servername api.tiger.com 2>/dev/null | \
grep -E "(subject=|issuer=|Verify return code)"
```

## Support Resources

### Self-Service Resources

1. **Documentation Links**:
   - [Full Integration Guide](CLAUDE_CODE_INTEGRATION.md)
   - [Security Best Practices](CLAUDE_CODE_SECURITY.md)
   - [API Reference](API_REFERENCE.md)
   - [Tiger Brokers API Docs](https://www.itiger.com/openapi)

2. **Diagnostic Commands**:
   ```bash
   # Generate comprehensive system report
   ./scripts/generate-system-report.sh > system-report-$(date +%Y%m%d).txt
   
   # Run automated diagnostics
   ./scripts/run-diagnostics.sh
   
   # Test all major functions
   ./scripts/integration-test.sh
   ```

### Getting Help

#### Before Requesting Support

- [ ] Run the comprehensive debug script above
- [ ] Collect relevant log files
- [ ] Document exact error messages
- [ ] Note your system configuration (OS, Python version, Claude Code version)
- [ ] Try the solutions in this guide

#### Support Channels

1. **GitHub Issues**: 
   - Bug reports with full debug information
   - Feature requests and enhancements
   - Community discussions

2. **Documentation Updates**:
   - Submit PRs for documentation improvements
   - Report missing or unclear information

3. **Emergency Support**:
   - Critical security issues
   - Trading system outages
   - Data integrity problems

#### Issue Report Template

```markdown
## Issue Description
Brief description of the problem

## Environment
- OS: 
- Python Version: 
- Claude Code Version: 
- Tiger MCP Version: 
- Tiger Account Type: (Sandbox/Production)

## Error Messages
```
Exact error messages here
```

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen

## Actual Behavior
What actually happened

## Debug Information
- Environment variables (redacted): 
- MCP server status: 
- Log excerpts: 
- Network connectivity: 

## Attempted Solutions
- [ ] Checked documentation
- [ ] Ran debug scripts
- [ ] Verified credentials
- [ ] Tested in sandbox
```

### Emergency Procedures

#### Trading System Outage

```bash
# Immediate steps if trading system is down
echo "🚨 Trading System Emergency Procedure"

# 1. Stop all automated trading
export TIGER_TRADING_HALTED=true
pkill -f "tiger-mcp"

# 2. Document the outage
echo "$(date): Trading system halted due to emergency" >> /var/log/emergency.log

# 3. Switch to manual Tiger Brokers interface
echo "Use Tiger Brokers web/mobile app for manual trading"

# 4. Notify stakeholders
echo "Trading system outage at $(date)" | mail -s "URGENT: Trading System Down" alerts@company.com
```

#### Security Incident

```bash
# If security breach is suspected
echo "🔒 Security Incident Response"

# 1. Immediate isolation
claude mcp remove tiger-trading
export TIGER_API_DISABLED=true

# 2. Preserve evidence
cp -r /var/log/tiger-mcp /tmp/incident-evidence-$(date +%Y%m%d)

# 3. Contact security team
echo "Suspected security incident in Tiger MCP at $(date)" | \
mail -s "CRITICAL: Security Incident" security@company.com
```

---

## Quick Reference

### Most Common Issues (80% of problems)

1. **Credentials incorrect** → Verify in Tiger Brokers console
2. **MCP server not added** → Run `claude mcp add tiger-trading ...`
3. **Tool permissions denied** → Set `claude config add permissions.allow "mcp__*"`
4. **Sandbox/production mismatch** → Check `TIGER_SANDBOX` setting
5. **Server process died** → Check logs and restart with debug mode

### Emergency Commands

```bash
# Reset everything
claude mcp remove tiger-trading
rm -rf ~/.claude/mcp-servers/tiger-trading
# Then re-add from scratch

# Debug mode
export LOG_LEVEL=DEBUG
export TIGER_DEBUG=true

# Safe mode (read-only)
export TIGER_READ_ONLY=true
export TIGER_TRADING_DISABLED=true
```

Remember: When in doubt, start with the sandbox environment and verify each component step by step!