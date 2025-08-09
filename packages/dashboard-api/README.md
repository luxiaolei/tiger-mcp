# Dashboard API

FastAPI backend providing REST API for the Tiger MCP dashboard.

## Features

- Portfolio and account management endpoints
- Market data and trading APIs
- Authentication and authorization
- Real-time WebSocket connections

## Development

```bash
# Install dependencies
uv sync

# Run API server
uv run --package dashboard-api uvicorn dashboard_api.main:app --reload
```