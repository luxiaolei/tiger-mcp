"""
Tiger MCP Server - Main orchestration class.

Orchestrates all components including database, account services, process pool,
and MCP tools with proper initialization order and lifecycle management.
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .config_manager import TigerMCPConfig, get_config_manager

# Add paths for shared and database imports
_SHARED_PATH = Path(__file__).parent.parent.parent.parent / "shared" / "src"
_DATABASE_PATH = Path(__file__).parent.parent.parent.parent / "database" / "src"

if str(_SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(_SHARED_PATH))
if str(_DATABASE_PATH) not in sys.path:
    sys.path.insert(0, str(_DATABASE_PATH))


class TigerMCPServer:
    """
    Main Tiger MCP Server class.

    Orchestrates all components including:
    - Configuration management
    - Database initialization
    - Account management services
    - Process pool management
    - Background task scheduling
    - Graceful shutdown handling
    """

    def __init__(
        self, config_file: Optional[str] = None, environment: Optional[str] = None
    ):
        """
        Initialize Tiger MCP Server.

        Args:
            config_file: Optional configuration file path
            environment: Environment name (development, testing, production)
        """
        self.config_manager = get_config_manager(
            config_file=config_file, environment=environment
        )
        self.config: Optional[TigerMCPConfig] = None

        # Service components
        self.account_manager = None
        self.account_router = None
        self.process_manager = None
        self.tiger_service = None

        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()
        self._started = False

        # Setup signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        if sys.platform != "win32":
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()

    async def initialize(self) -> None:
        """
        Initialize all server components.

        Components are initialized in dependency order:
        1. Configuration loading and validation
        2. Logging configuration
        3. Database initialization
        4. Account management services
        5. Process pool initialization
        6. Tiger API service
        7. Background task startup

        Raises:
            Exception: If any component fails to initialize
        """
        try:
            logger.info("Initializing Tiger MCP Server...")

            # 1. Load and validate configuration
            logger.info("Loading configuration...")
            self.config = self.config_manager.load_config()

            # 2. Configure logging
            self._configure_logging()

            # 3. Initialize database
            logger.info("Initializing database...")
            await self._initialize_database()

            # 4. Initialize account management
            logger.info("Initializing account management...")
            await self._initialize_account_services()

            # 5. Initialize process pool
            logger.info("Initializing process pool...")
            await self._initialize_process_pool()

            # 6. Initialize Tiger API service
            logger.info("Initializing Tiger API service...")
            await self._initialize_tiger_service()

            # 7. Start background tasks
            logger.info("Starting background tasks...")
            await self._start_background_tasks()

            self._started = True
            logger.success("Tiger MCP Server initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Tiger MCP Server: {e}")
            await self.cleanup()
            raise

    def _configure_logging(self) -> None:
        """Configure logging based on configuration."""
        # Remove default logger
        logger.remove()

        # Configure console logging
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

        logger.add(
            sys.stdout,
            format=log_format,
            level=self.config.server.log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

        # Add file logging in production
        if self.config.environment == "production":
            logger.add(
                "logs/tiger_mcp_server.log",
                format=log_format,
                level=self.config.server.log_level,
                rotation="1 day",
                retention="30 days",
                compression="gz",
            )

        logger.info(f"Logging configured for {self.config.environment} environment")

    async def _initialize_database(self) -> None:
        """Initialize database connection and migrations."""
        try:
            from database import get_db_manager

            db_manager = get_db_manager()
            await db_manager.initialize(
                database_url=self.config.database.url, echo=self.config.database.echo
            )
            logger.info("Database initialized successfully")

        except ImportError:
            logger.warning(
                "Database package not available, running without persistent storage"
            )
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def _initialize_account_services(self) -> None:
        """Initialize account management services."""
        try:
            from shared.account_manager import get_account_manager
            from shared.account_router import get_account_router

            # Initialize account manager
            self.account_manager = get_account_manager()
            await self.account_manager.initialize()

            # Initialize account router
            self.account_router = get_account_router()

            logger.info("Account services initialized successfully")

        except ImportError as e:
            logger.warning(f"Account services not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize account services: {e}")
            raise

    async def _initialize_process_pool(self) -> None:
        """Initialize Tiger process pool."""
        try:
            from .process_manager import get_process_manager

            self.process_manager = get_process_manager()

            # Configure process manager with settings
            await self.process_manager.configure(
                min_workers=self.config.process.min_workers,
                max_workers=self.config.process.max_workers,
                target_workers=self.config.process.target_workers,
                startup_timeout=self.config.process.startup_timeout,
                shutdown_timeout=self.config.process.shutdown_timeout,
                health_check_interval=self.config.process.health_check_interval,
                worker_restart_threshold=self.config.process.worker_restart_threshold,
                load_balance_strategy=self.config.process.load_balance_strategy,
            )

            # Start process pool
            await self.process_manager.start()

            logger.info("Process pool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize process pool: {e}")
            raise

    async def _initialize_tiger_service(self) -> None:
        """Initialize Tiger API service."""
        try:
            from .example_usage import TigerAPIService

            self.tiger_service = TigerAPIService()
            await self.tiger_service.start()

            logger.info("Tiger API service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Tiger API service: {e}")
            raise

    async def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        # Token refresh task
        if self.config.security.enable_token_validation and self.account_manager:
            task = asyncio.create_task(self._token_refresh_task())
            self.background_tasks.append(task)
            logger.info("Token refresh task started")

        # Health monitoring task
        if self.process_manager:
            task = asyncio.create_task(self._health_monitor_task())
            self.background_tasks.append(task)
            logger.info("Health monitoring task started")

        # Cleanup task
        task = asyncio.create_task(self._cleanup_task())
        self.background_tasks.append(task)
        logger.info("Cleanup task started")

    async def _token_refresh_task(self) -> None:
        """Background task for token refresh."""
        try:
            while not self.shutdown_event.is_set():
                try:
                    if self.account_manager:
                        await self.account_manager.refresh_expiring_tokens(
                            threshold=self.config.security.token_refresh_threshold
                        )
                except Exception as e:
                    logger.error(f"Error in token refresh task: {e}")

                # Wait for next check (with early exit on shutdown)
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(),
                        timeout=self.config.security.token_refresh_threshold / 2,
                    )
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue loop
                else:
                    break  # Shutdown event was set

        except asyncio.CancelledError:
            logger.info("Token refresh task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in token refresh task: {e}")

    async def _health_monitor_task(self) -> None:
        """Background task for health monitoring."""
        try:
            while not self.shutdown_event.is_set():
                try:
                    if self.process_manager:
                        # Perform health checks
                        unhealthy_workers = (
                            await self.process_manager.check_worker_health()
                        )
                        if unhealthy_workers:
                            logger.warning(
                                f"Found {len(unhealthy_workers)} unhealthy workers"
                            )

                        # Check if we need to scale workers
                        await self.process_manager.auto_scale()

                except Exception as e:
                    logger.error(f"Error in health monitoring task: {e}")

                # Wait for next check
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(),
                        timeout=self.config.process.health_check_interval,
                    )
                except asyncio.TimeoutError:
                    continue
                else:
                    break

        except asyncio.CancelledError:
            logger.info("Health monitoring task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in health monitoring task: {e}")

    async def _cleanup_task(self) -> None:
        """Background task for periodic cleanup."""
        try:
            while not self.shutdown_event.is_set():
                try:
                    # Cleanup expired sessions, logs, etc.
                    if self.account_manager:
                        await self.account_manager.cleanup_expired_sessions()

                    # Cleanup process metrics
                    if self.process_manager:
                        await self.process_manager.cleanup_old_metrics()

                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")

                # Wait for next cleanup (every hour)
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(), timeout=3600  # 1 hour
                    )
                except asyncio.TimeoutError:
                    continue
                else:
                    break

        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in cleanup task: {e}")

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()
        logger.info("Shutdown signal received")

    async def cleanup(self) -> None:
        """
        Cleanup all server components.

        Components are cleaned up in reverse dependency order:
        1. Stop background tasks
        2. Stop Tiger API service
        3. Stop process pool
        4. Stop account services
        5. Close database connections
        """
        logger.info("Starting server cleanup...")

        # Cancel background tasks
        if self.background_tasks:
            logger.info("Stopping background tasks...")
            for task in self.background_tasks:
                task.cancel()

            # Wait for tasks to complete with timeout
            if self.background_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self.background_tasks, return_exceptions=True),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Some background tasks did not complete within timeout"
                    )

            self.background_tasks.clear()

        # Stop Tiger API service
        if self.tiger_service:
            try:
                logger.info("Stopping Tiger API service...")
                await self.tiger_service.stop()
            except Exception as e:
                logger.error(f"Error stopping Tiger API service: {e}")

        # Stop process pool
        if self.process_manager:
            try:
                logger.info("Stopping process pool...")
                await self.process_manager.stop()
            except Exception as e:
                logger.error(f"Error stopping process pool: {e}")

        # Cleanup account services
        if self.account_manager:
            try:
                logger.info("Stopping account services...")
                await self.account_manager.cleanup()
            except Exception as e:
                logger.error(f"Error stopping account services: {e}")

        # Close database connections
        try:
            from database import get_db_manager

            db_manager = get_db_manager()
            await db_manager.cleanup()
            logger.info("Database connections closed")
        except ImportError:
            pass  # Database package not available
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

        self._started = False
        logger.info("Server cleanup completed")

    async def start(self) -> None:
        """
        Start the Tiger MCP Server.

        Raises:
            RuntimeError: If server is already started
            Exception: If initialization fails
        """
        if self._started:
            raise RuntimeError("Server is already started")

        await self.initialize()

    async def stop(self) -> None:
        """
        Stop the Tiger MCP Server.

        Raises:
            RuntimeError: If server is not started
        """
        if not self._started:
            raise RuntimeError("Server is not started")

        self.shutdown_event.set()
        await self.cleanup()

    @property
    def is_started(self) -> bool:
        """Check if server is started."""
        return self._started

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current server health status.

        Returns:
            Dictionary containing health information
        """
        status = {
            "server": {
                "started": self._started,
                "environment": self.config.environment if self.config else None,
                "background_tasks": len(self.background_tasks),
            }
        }

        # Add process pool status
        if self.process_manager:
            try:
                status["process_pool"] = {
                    "active_workers": len(self.process_manager.workers),
                    "total_requests": sum(
                        w.request_count for w in self.process_manager.workers.values()
                    ),
                    "failed_requests": sum(
                        w.error_count for w in self.process_manager.workers.values()
                    ),
                }
            except Exception:
                status["process_pool"] = {"error": "Unable to get process pool status"}

        # Add account manager status
        if self.account_manager:
            try:
                status["accounts"] = {
                    "total_accounts": len(self.account_manager.accounts),
                    "active_accounts": len(
                        [
                            acc
                            for acc in self.account_manager.accounts.values()
                            if acc.status.value == "active"
                        ]
                    ),
                }
            except Exception:
                status["accounts"] = {"error": "Unable to get account status"}

        return status


async def main():
    """Main entry point for the server."""
    server = None
    try:
        # Create and start server
        server = TigerMCPServer()
        await server.start()

        logger.success("Tiger MCP Server started successfully")

        # Wait for shutdown signal
        await server.wait_for_shutdown()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        if server and server.is_started:
            await server.stop()
        logger.info("Tiger MCP Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
