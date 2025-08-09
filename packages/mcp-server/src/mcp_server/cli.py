"""
Tiger MCP Server CLI.

Command-line interface for running and managing the Tiger MCP server
with various modes and configuration options.
"""

import argparse
import asyncio
import sys
from typing import Optional

from loguru import logger

from .config_manager import get_config_manager
from .main import run_sse_server, run_stdio_server
from .server import TigerMCPServer


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Setup logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    # Remove default logger
    logger.remove()

    # Console logging format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # Add console handler
    logger.add(sys.stdout, format=log_format, level=log_level, colorize=True)

    # Add file handler if specified
    if log_file:
        logger.add(
            log_file,
            format=log_format,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
        )


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="tiger-mcp-server",
        description="Tiger MCP Server - FastMCP integration for Tiger Brokers API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with stdio transport (default)
  tiger-mcp-server

  # Run with SSE transport
  tiger-mcp-server --transport sse --host 0.0.0.0 --port 8000

  # Run in development mode with debug logging
  tiger-mcp-server --environment development --log-level DEBUG

  # Run with custom configuration
  tiger-mcp-server --config config.yaml --environment production

  # Check server health
  tiger-mcp-server health

  # Validate configuration
  tiger-mcp-server validate-config --environment production
        """,
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command (default)
    run_parser = subparsers.add_parser("run", help="Run the MCP server")
    run_parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    run_parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to for SSE transport (default: localhost)",
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to for SSE transport (default: 8000)",
    )

    # Health command
    subparsers.add_parser("health", help="Check server health status")

    # Validate config command
    validate_parser = subparsers.add_parser(
        "validate-config", help="Validate configuration"
    )
    validate_parser.add_argument(
        "--show-config", action="store_true", help="Show resolved configuration values"
    )

    # Common options
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument(
        "--environment",
        choices=["development", "testing", "production"],
        help="Environment name",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    parser.add_argument("--log-file", help="Log file path")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    return parser


async def run_command(args) -> int:
    """
    Run the MCP server.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    try:
        if args.transport == "stdio":
            logger.info("Starting Tiger MCP Server with stdio transport...")
            await run_stdio_server(
                config_file=args.config, environment=args.environment
            )
        elif args.transport == "sse":
            logger.info(
                f"Starting Tiger MCP Server with SSE transport on {args.host}:{args.port}..."
            )
            await run_sse_server(
                host=args.host,
                port=args.port,
                config_file=args.config,
                environment=args.environment,
            )

        return 0

    except Exception as e:
        logger.error(f"Failed to run server: {e}")
        return 1


async def health_command(args) -> int:
    """
    Check server health status.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    try:
        # Create a temporary server instance to check health
        server = TigerMCPServer(config_file=args.config, environment=args.environment)

        # Initialize to get configuration and basic components
        await server.initialize()

        # Get health status
        health = server.get_health_status()

        # Display health information
        print("Tiger MCP Server Health Status:")
        print("=" * 40)

        # Server status
        server_status = health.get("server", {})
        print(f"Server Started: {server_status.get('started', False)}")
        print(f"Environment: {server_status.get('environment', 'unknown')}")
        print(f"Background Tasks: {server_status.get('background_tasks', 0)}")

        # Process pool status
        if "process_pool" in health:
            pool_status = health["process_pool"]
            if "error" in pool_status:
                print(f"Process Pool: ERROR - {pool_status['error']}")
            else:
                print(f"Active Workers: {pool_status.get('active_workers', 0)}")
                print(f"Total Requests: {pool_status.get('total_requests', 0)}")
                print(f"Failed Requests: {pool_status.get('failed_requests', 0)}")

        # Account status
        if "accounts" in health:
            account_status = health["accounts"]
            if "error" in account_status:
                print(f"Accounts: ERROR - {account_status['error']}")
            else:
                print(f"Total Accounts: {account_status.get('total_accounts', 0)}")
                print(f"Active Accounts: {account_status.get('active_accounts', 0)}")

        # Cleanup
        await server.cleanup()

        # Determine exit code based on health
        if server_status.get("started", False):
            print("\nStatus: HEALTHY")
            return 0
        else:
            print("\nStatus: UNHEALTHY")
            return 1

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        print(f"Status: ERROR - {e}")
        return 1


async def validate_config_command(args) -> int:
    """
    Validate configuration.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    try:
        # Load configuration
        config_manager = get_config_manager(
            config_file=args.config, environment=args.environment
        )

        config = config_manager.load_config()

        print("Configuration Validation: PASSED")
        print(f"Environment: {config.environment}")

        if args.show_config:
            print("\nResolved Configuration:")
            print("=" * 40)

            # Database config
            print(f"Database URL: {config.database.url}")
            print(f"Database Echo: {config.database.echo}")
            print(f"Database Pool Size: {config.database.pool_size}")

            # Server config
            print(f"Server Host: {config.server.host}")
            print(f"Server Port: {config.server.port}")
            print(f"Server Debug: {config.server.debug}")
            print(f"Server Log Level: {config.server.log_level}")

            # Process config
            print(f"Process Min Workers: {config.process.min_workers}")
            print(f"Process Max Workers: {config.process.max_workers}")
            print(f"Process Target Workers: {config.process.target_workers}")

            # Security config
            print(
                f"Token Validation Enabled: {config.security.enable_token_validation}"
            )
            print(
                f"Token Refresh Threshold: {config.security.token_refresh_threshold}s"
            )
            print(f"API Rate Limit: {config.security.api_rate_limit}")

            # Tiger config
            print(f"Tiger Sandbox Mode: {config.tiger.sandbox_mode}")
            print(f"Tiger Default Market: {config.tiger.default_market}")
            print(f"Tiger Request Timeout: {config.tiger.request_timeout}s")

        return 0

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        print(f"Configuration Validation: FAILED - {e}")
        return 1


async def async_main() -> int:
    """Async main function."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    setup_logging(log_level=args.log_level, log_file=args.log_file)

    # Handle commands
    command = args.command or "run"

    if command == "run":
        return await run_command(args)
    elif command == "health":
        return await health_command(args)
    elif command == "validate-config":
        return await validate_config_command(args)
    else:
        logger.error(f"Unknown command: {command}")
        return 1


def main() -> None:
    """Main CLI entry point."""
    try:
        exit_code = asyncio.run(async_main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
