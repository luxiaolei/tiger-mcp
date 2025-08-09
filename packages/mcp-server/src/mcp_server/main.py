"""
Tiger MCP Server - FastMCP Integration.

Main entry point that integrates Tiger MCP Server with FastMCP framework,
registering all MCP tools and handling server lifecycle.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP
from loguru import logger

from .config_manager import get_config
from .server import TigerMCPServer

# Add paths for tool imports
_TOOLS_PATH = Path(__file__).parent / "tools"
if str(_TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(_TOOLS_PATH))


class TigerFastMCPServer:
    """
    Tiger FastMCP Server integration.

    Combines the Tiger MCP Server with FastMCP framework to provide
    a complete MCP server with all Tiger Brokers API tools.
    """

    def __init__(
        self, config_file: Optional[str] = None, environment: Optional[str] = None
    ):
        """
        Initialize Tiger FastMCP Server.

        Args:
            config_file: Optional configuration file path
            environment: Environment name (development, testing, production)
        """
        self.tiger_server = TigerMCPServer(
            config_file=config_file, environment=environment
        )
        self.mcp_server: Optional[FastMCP] = None
        self._started = False

    async def initialize(self) -> None:
        """Initialize the combined server."""
        # Initialize Tiger MCP Server first
        await self.tiger_server.initialize()

        # Create FastMCP server instance
        get_config()
        self.mcp_server = FastMCP("Tiger MCP Server")

        # Register all MCP tools
        await self._register_tools()

        logger.info("Tiger FastMCP Server initialized successfully")

    async def _register_tools(self) -> None:
        """Register all MCP tools with FastMCP server."""
        # Import all tools
        from .tools import (  # Data tools; Info tools; Account tools; Trading tools
            tiger_add_account,
            tiger_cancel_order,
            tiger_get_account_info,
            tiger_get_account_status,
            tiger_get_contracts,
            tiger_get_corporate_actions,
            tiger_get_earnings,
            tiger_get_financials,
            tiger_get_kline,
            tiger_get_market_data,
            tiger_get_market_status,
            tiger_get_option_chain,
            tiger_get_orders,
            tiger_get_positions,
            tiger_get_quote,
            tiger_list_accounts,
            tiger_modify_order,
            tiger_place_order,
            tiger_refresh_token,
            tiger_remove_account,
            tiger_search_symbols,
            tiger_set_default_data_account,
            tiger_set_default_trading_account,
        )

        # Register data tools
        logger.info("Registering data tools...")
        self.mcp_server.add_tool(tiger_get_quote)
        self.mcp_server.add_tool(tiger_get_kline)
        self.mcp_server.add_tool(tiger_get_market_data)
        self.mcp_server.add_tool(tiger_search_symbols)
        self.mcp_server.add_tool(tiger_get_option_chain)
        self.mcp_server.add_tool(tiger_get_market_status)

        # Register info tools
        logger.info("Registering info tools...")
        self.mcp_server.add_tool(tiger_get_contracts)
        self.mcp_server.add_tool(tiger_get_financials)
        self.mcp_server.add_tool(tiger_get_corporate_actions)
        self.mcp_server.add_tool(tiger_get_earnings)

        # Register account tools
        logger.info("Registering account tools...")
        self.mcp_server.add_tool(tiger_list_accounts)
        self.mcp_server.add_tool(tiger_add_account)
        self.mcp_server.add_tool(tiger_remove_account)
        self.mcp_server.add_tool(tiger_get_account_status)
        self.mcp_server.add_tool(tiger_refresh_token)
        self.mcp_server.add_tool(tiger_set_default_data_account)
        self.mcp_server.add_tool(tiger_set_default_trading_account)

        # Register trading tools
        logger.info("Registering trading tools...")
        self.mcp_server.add_tool(tiger_get_positions)
        self.mcp_server.add_tool(tiger_get_account_info)
        self.mcp_server.add_tool(tiger_get_orders)
        self.mcp_server.add_tool(tiger_place_order)
        self.mcp_server.add_tool(tiger_cancel_order)
        self.mcp_server.add_tool(tiger_modify_order)

        logger.success("All MCP tools registered successfully")

        # Add health check endpoint
        @self.mcp_server.add_resource("tiger://health")
        async def health_status() -> str:
            """Get server health status."""
            try:
                health = self.tiger_server.get_health_status()
                return f"Tiger MCP Server Health Status:\n{health}"
            except Exception as e:
                return f"Error getting health status: {e}"

        # Add server info endpoint
        @self.mcp_server.add_resource("tiger://info")
        async def server_info() -> str:
            """Get server information."""
            config = get_config()
            return f"""Tiger MCP Server Information:
Environment: {config.environment}
Process Pool Workers: {config.process.target_workers}
Security Enabled: {config.security.enable_token_validation}
Tiger Sandbox Mode: {config.tiger.sandbox_mode}
"""

    async def start(self) -> None:
        """Start the combined server."""
        if self._started:
            raise RuntimeError("Server is already started")

        await self.initialize()
        self._started = True

        logger.success("Tiger FastMCP Server started and ready to handle requests")

    async def stop(self) -> None:
        """Stop the combined server."""
        if not self._started:
            raise RuntimeError("Server is not started")

        logger.info("Stopping Tiger FastMCP Server...")

        # Stop Tiger MCP Server
        await self.tiger_server.stop()

        self._started = False
        logger.info("Tiger FastMCP Server stopped")

    async def run_stdio(self) -> None:
        """Run the FastMCP server with stdio transport."""
        if not self._started:
            await self.start()

        logger.info("Starting FastMCP server with stdio transport...")
        await self.mcp_server.run(transport="stdio")

    async def run_sse(self, host: str = "localhost", port: int = 8000) -> None:
        """
        Run the FastMCP server with SSE transport.

        Args:
            host: Server host
            port: Server port
        """
        if not self._started:
            await self.start()

        logger.info(f"Starting FastMCP server with SSE transport on {host}:{port}...")
        await self.mcp_server.run(transport="sse", host=host, port=port)

    @property
    def is_started(self) -> bool:
        """Check if server is started."""
        return self._started


async def run_stdio_server(
    config_file: Optional[str] = None, environment: Optional[str] = None
) -> None:
    """
    Run Tiger MCP server with stdio transport.

    Args:
        config_file: Optional configuration file path
        environment: Environment name
    """
    server = TigerFastMCPServer(config_file=config_file, environment=environment)

    try:
        await server.run_stdio()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        if server.is_started:
            await server.stop()


async def run_sse_server(
    host: str = "localhost",
    port: int = 8000,
    config_file: Optional[str] = None,
    environment: Optional[str] = None,
) -> None:
    """
    Run Tiger MCP server with SSE transport.

    Args:
        host: Server host
        port: Server port
        config_file: Optional configuration file path
        environment: Environment name
    """
    server = TigerFastMCPServer(config_file=config_file, environment=environment)

    try:
        await server.run_sse(host=host, port=port)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        if server.is_started:
            await server.stop()


def main() -> None:
    """Main entry point for stdio server."""
    try:
        asyncio.run(run_stdio_server())
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


def main_sse() -> None:
    """Main entry point for SSE server."""
    try:
        asyncio.run(run_sse_server())
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
