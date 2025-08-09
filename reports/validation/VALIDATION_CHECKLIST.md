# Tiger MCP Server Validation Checklist

Use this checklist to validate your Tiger MCP server setup before using with Claude Code.

## Prerequisites ✅

- [ ] Python 3.11+ installed
- [ ] Claude Code installed (`claude --version` works)
- [ ] UV package manager installed
- [ ] Tiger Brokers account with API access
- [ ] Tiger API credentials (Client ID, Private Key, Account)

## Environment Setup ✅

- [ ] Project cloned and UV sync completed
- [ ] `.env` file created with Tiger credentials
- [ ] Environment variables properly set:
  ```bash
  TIGER_CLIENT_ID=your_client_id
  TIGER_PRIVATE_KEY=your_private_key_content  
  TIGER_ACCOUNT=your_account_number
  TIGER_SANDBOX=true  # Start with sandbox
  TIGER_LICENSE=TBHK  # or TBNZ, TBSG
  ```

## Server Validation ✅

- [ ] MCP server modules import successfully:
  ```bash
  uv run --package mcp-server python -c "import mcp_server; print('OK')"
  ```

- [ ] Tiger SDK dependencies available:
  ```bash
  uv run --package mcp-server python -c "import simplejson, delorean; print('OK')"
  ```

- [ ] Configuration loads without errors:
  ```bash
  uv run --package mcp-server python -c "from mcp_server.config_manager import get_config; get_config(); print('OK')"
  ```

## Claude Code Integration ✅

- [ ] Add MCP server to Claude Code:
  ```bash
  claude mcp add tiger-mcp \
    --env TIGER_CLIENT_ID=your_client_id \
    --env TIGER_PRIVATE_KEY="$(cat your_private_key.pem)" \
    --env TIGER_ACCOUNT=your_account \
    --env TIGER_SANDBOX=true \
    --env TIGER_LICENSE=TBHK \
    --env TIGER_USE_DATABASE=false \
    -- uv run --package mcp-server python -m mcp_server.main
  ```

- [ ] Verify server appears in list:
  ```bash
  claude mcp list
  ```

- [ ] Test basic connection:
  ```bash
  claude -p "What Tiger MCP tools are available?"
  ```

## Tool Functionality ✅

Expected MCP tools should be available:
- [ ] `mcp__tiger-mcp__tiger_get_quote` - Market quotes
- [ ] `mcp__tiger-mcp__tiger_get_account_info` - Account information  
- [ ] `mcp__tiger-mcp__tiger_list_accounts` - Account listing
- [ ] `mcp__tiger-mcp__tiger_get_positions` - Portfolio positions
- [ ] `mcp__tiger-mcp__tiger_get_market_data` - Market data
- [ ] `mcp__tiger-mcp__tiger_place_order` - Order placement (sandbox only!)

## Basic Testing ✅

- [ ] Test account info retrieval:
  ```bash
  claude -p "Use tiger MCP tools to get my account information"
  ```

- [ ] Test market data (sandbox):
  ```bash
  claude -p "Get current market data for AAPL using Tiger MCP"
  ```

- [ ] Test portfolio access:
  ```bash
  claude -p "Show my current portfolio positions using Tiger MCP"
  ```

## Security Validation ✅

- [ ] Sandbox mode enabled (`TIGER_SANDBOX=true`)
- [ ] Private key file has proper permissions (600)
- [ ] No credentials visible in logs
- [ ] Environment variables not committed to git
- [ ] API access restricted to sandbox initially

## Troubleshooting ✅

If tests fail, check:

### Configuration Issues
- [ ] All required environment variables set
- [ ] Private key format is correct (PK1 or PK8)
- [ ] Tiger license matches your account region
- [ ] Account number is correct

### Connection Issues  
- [ ] Internet connectivity working
- [ ] Tiger API endpoints accessible
- [ ] No proxy/firewall blocking connections
- [ ] API credentials are valid and active

### MCP Server Issues
- [ ] UV virtual environment properly set up
- [ ] All dependencies installed (`uv sync` completed)
- [ ] No Python version conflicts
- [ ] Sufficient disk space and memory

## Next Steps After Validation ✅

### Development Use
- [ ] Create test trading scenarios (sandbox only)
- [ ] Test error handling with invalid inputs
- [ ] Validate multi-symbol market data requests
- [ ] Test order placement and cancellation (sandbox)

### Production Preparation  
- [ ] Switch to production credentials
- [ ] Set `TIGER_SANDBOX=false`  
- [ ] Implement position limits and safeguards
- [ ] Set up monitoring and logging
- [ ] Create backup of working configuration

## Common Issues and Solutions

### ❌ "MCP server failed to connect"
**Solution**: Check environment variables and ensure UV environment is properly activated

### ❌ "Configuration validation errors"  
**Solution**: Set `TIGER_USE_DATABASE=false` for simple setup, or adjust Pydantic config schema

### ❌ "Tiger API authentication failed"
**Solution**: Verify credentials, check private key format, ensure API access is enabled

### ❌ "Protobuf version warnings"
**Solution**: These are warnings only and don't affect functionality - can be ignored for now

### ❌ "Account manager initialization failed"
**Solution**: Use environment variable configuration instead of database mode

## Support Resources

- **Integration Guide**: [CLAUDE_CODE_INTEGRATION.md](docs/CLAUDE_CODE_INTEGRATION.md)
- **Test Report**: [TIGER_MCP_INTEGRATION_TEST_REPORT.md](TIGER_MCP_INTEGRATION_TEST_REPORT.md) 
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Tiger API Docs**: [Tiger Brokers API Documentation](https://www.itiger.com/openapi)

---

**✅ Validation Complete**: If all items are checked, your Tiger MCP server should be ready for use with Claude Code!

**⚠️ Issues Found**: Review the troubleshooting section and test report for specific guidance on resolving any problems.