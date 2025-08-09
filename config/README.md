# Configuration Files

This directory contains configuration files for the Tiger MCP system.

## Files

### Claude MCP Configuration
- **`claude_mcp.json`** - Configuration for Claude Desktop MCP server integration
- **`mcp_test.json`** - Test configuration for MCP server

### Environment Templates
Environment template files are located in the project root:
- **`../.env.template`** - Main environment template for development
- **`../.env.prod.template`** - Production environment template
- **`../.env.test`** - Test environment configuration

## Setup Instructions

1. **Development Setup:**
   ```bash
   cp .env.template .env
   # Edit .env with your configuration
   ```

2. **Production Setup:**
   ```bash
   cp .env.prod.template .env.prod
   # Edit .env.prod with your production configuration
   ```

3. **Claude Desktop Integration:**
   - Use `claude_mcp.json` as reference for Claude Desktop configuration
   - Update paths to match your installation directory

## Security Notes

- Never commit actual `.env` files to version control
- Use secure secrets management in production
- Store Tiger API private keys in the `secrets/` directory for production deployments