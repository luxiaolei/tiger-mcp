#!/usr/bin/env python3
"""
Simple startup script for Tiger MCP Server.

This script provides a simple way to start the server for development
and testing purposes.
"""

import asyncio
import sys
from pathlib import Path

# Add the source directory to Python path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from mcp_server.main import run_sse_server, run_stdio_server


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Start Tiger MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host for SSE transport (default: localhost)",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port for SSE transport (default: 8000)"
    )
    parser.add_argument(
        "--environment",
        choices=["development", "testing", "production"],
        default="development",
        help="Environment (default: development)",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        print("Starting Tiger MCP Server with stdio transport...")
        await run_stdio_server(environment=args.environment)
    else:
        print(
            f"Starting Tiger MCP Server with SSE transport on {args.host}:{args.port}..."
        )
        await run_sse_server(
            host=args.host, port=args.port, environment=args.environment
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
