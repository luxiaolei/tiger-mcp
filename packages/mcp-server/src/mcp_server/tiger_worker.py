"""
Tiger Worker Process.

Isolated worker process that loads Tiger SDK for one specific account.
Handles API calls from the main process via queue communication.
"""

import json
import multiprocessing as mp
import sys
import time
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, List

# Set up logging for worker process
from loguru import logger

# Add the Tiger SDK path to sys.path
TIGER_SDK_PATH = (
    "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/references/openapi-python-sdk"
)
if TIGER_SDK_PATH not in sys.path:
    sys.path.insert(0, TIGER_SDK_PATH)

try:
    # Import Tiger SDK components
    from tigeropen.push.push_client import PushClient
    from tigeropen.quote.quote_client import QuoteClient
    from tigeropen.tiger_open_client import TigerOpenClient
    from tigeropen.tiger_open_config import TigerOpenClientConfig
    from tigeropen.trade.trade_client import TradeClient
except ImportError as e:
    logger.error(f"Failed to import Tiger SDK: {e}")
    raise


class TigerWorker:
    """
    Tiger worker process that handles one specific account.

    Loads Tiger SDK credentials at startup and processes API calls
    from the main process via queue communication.
    """

    def __init__(self, process_id: str, account_id: str):
        """
        Initialize Tiger worker.

        Args:
            process_id: Unique process identifier
            account_id: Tiger account ID
        """
        self.process_id = process_id
        self.account_id = account_id
        self.account = None
        self.credentials = None

        # Tiger SDK clients
        self.config = None
        self.client = None
        self.trade_client = None
        self.quote_client = None
        self.push_client = None

        # State management
        self.is_initialized = False
        self.last_heartbeat = datetime.utcnow()
        self.task_count = 0

        logger.info(f"TigerWorker {process_id} initialized for account {account_id}")

    async def initialize(self) -> bool:
        """
        Initialize Tiger SDK with account credentials.

        Returns:
            True if initialization successful
        """
        try:
            logger.info(f"Initializing Tiger SDK for account {self.account_id}")

            # Load account and credentials
            await self._load_account_credentials()

            # Configure Tiger SDK
            await self._configure_tiger_sdk()

            # Initialize clients
            await self._initialize_clients()

            self.is_initialized = True
            logger.info(
                f"Tiger SDK initialized successfully for account {self.account.account_number}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to initialize Tiger SDK: {e}")
            logger.error(traceback.format_exc())
            return False

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task request.

        Args:
            task_data: Task request data

        Returns:
            Task response data
        """
        task_id = task_data.get("task_id")
        method = task_data.get("method")
        args = task_data.get("args", [])
        kwargs = task_data.get("kwargs", {})

        start_time = time.time()

        try:
            logger.debug(f"Processing task {task_id}: {method}")

            # Check initialization
            if not self.is_initialized:
                raise RuntimeError("Worker not initialized")

            # Route method call
            if method.startswith("trade."):
                result = await self._execute_trade_method(method[6:], args, kwargs)
            elif method.startswith("quote."):
                result = await self._execute_quote_method(method[6:], args, kwargs)
            elif method.startswith("push."):
                result = await self._execute_push_method(method[5:], args, kwargs)
            elif method == "health_check":
                result = await self._health_check()
            else:
                raise ValueError(f"Unknown method: {method}")

            execution_time = time.time() - start_time
            self.task_count += 1

            logger.debug(f"Task {task_id} completed in {execution_time:.2f}s")

            return {
                "task_id": task_id,
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)

            logger.error(f"Task {task_id} failed: {error_msg}")
            logger.error(traceback.format_exc())

            return {
                "task_id": task_id,
                "success": False,
                "error": error_msg,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def heartbeat(self) -> Dict[str, Any]:
        """
        Respond to heartbeat check.

        Returns:
            Heartbeat response
        """
        self.last_heartbeat = datetime.utcnow()

        return {
            "type": "heartbeat_response",
            "process_id": self.process_id,
            "account_id": self.account_id,
            "timestamp": self.last_heartbeat.isoformat(),
            "task_count": self.task_count,
            "is_initialized": self.is_initialized,
        }

    async def shutdown(self) -> None:
        """Graceful shutdown of the worker."""
        try:
            logger.info(f"Shutting down TigerWorker {self.process_id}")

            # Close Tiger SDK clients
            if self.push_client:
                try:
                    self.push_client.disconnect()
                except:
                    pass

            # Clean up resources
            self.is_initialized = False

            logger.info(f"TigerWorker {self.process_id} shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    # Private methods

    async def _load_account_credentials(self) -> None:
        """Load account and decrypt credentials."""
        # Import account manager in worker process
        sys.path.insert(
            0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/shared/src"
        )
        sys.path.insert(
            0, "/Volumes/extdisk/MyRepos/cctrading-ws/tiger-mcp/packages/database/src"
        )

        from shared.account_manager import get_account_manager

        account_manager = get_account_manager()

        # Get account by ID
        self.account = await account_manager.get_account_by_id(
            uuid.UUID(self.account_id)
        )
        if not self.account:
            raise RuntimeError(f"Account {self.account_id} not found")

        # Decrypt credentials
        self.credentials = await account_manager.decrypt_credentials(self.account)
        if not self.credentials.get("tiger_id") or not self.credentials.get(
            "private_key"
        ):
            raise RuntimeError("Missing or invalid credentials")

        logger.info(f"Loaded credentials for account {self.account.account_number}")

    async def _configure_tiger_sdk(self) -> None:
        """Configure Tiger SDK with account credentials."""
        try:
            # Determine server URL
            if self.account.environment == "production":
                server_url = (
                    self.account.server_url or "https://openapi.tigerfintech.com"
                )
            else:
                server_url = (
                    self.account.server_url
                    or "https://openapi-sandbox.tigerfintech.com"
                )

            # Create Tiger configuration
            self.config = TigerOpenClientConfig(
                tiger_id=self.credentials["tiger_id"],
                private_key=self.credentials["private_key"],
                account=self.account.account_number,
                server_url=server_url,
                env=self.account.environment,
            )

            logger.info(
                f"Tiger SDK configured for {self.account.environment} environment"
            )

        except Exception as e:
            logger.error(f"Failed to configure Tiger SDK: {e}")
            raise

    async def _initialize_clients(self) -> None:
        """Initialize Tiger SDK clients."""
        try:
            # Create main client
            self.client = TigerOpenClient(self.config)

            # Create specialized clients
            self.trade_client = TradeClient(self.config)
            self.quote_client = QuoteClient(self.config)
            self.push_client = PushClient(self.config)

            logger.info("Tiger SDK clients initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Tiger clients: {e}")
            raise

    async def _execute_trade_method(
        self, method: str, args: List[Any], kwargs: Dict[str, Any]
    ) -> Any:
        """Execute trade client method."""
        if not self.trade_client:
            raise RuntimeError("Trade client not initialized")

        if not hasattr(self.trade_client, method):
            raise AttributeError(f"Trade client has no method '{method}'")

        # Get method and execute
        trade_method = getattr(self.trade_client, method)
        result = trade_method(*args, **kwargs)

        # Convert response to serializable format
        return self._serialize_response(result)

    async def _execute_quote_method(
        self, method: str, args: List[Any], kwargs: Dict[str, Any]
    ) -> Any:
        """Execute quote client method."""
        if not self.quote_client:
            raise RuntimeError("Quote client not initialized")

        if not hasattr(self.quote_client, method):
            raise AttributeError(f"Quote client has no method '{method}'")

        # Get method and execute
        quote_method = getattr(self.quote_client, method)
        result = quote_method(*args, **kwargs)

        # Convert response to serializable format
        return self._serialize_response(result)

    async def _execute_push_method(
        self, method: str, args: List[Any], kwargs: Dict[str, Any]
    ) -> Any:
        """Execute push client method."""
        if not self.push_client:
            raise RuntimeError("Push client not initialized")

        if not hasattr(self.push_client, method):
            raise AttributeError(f"Push client has no method '{method}'")

        # Get method and execute
        push_method = getattr(self.push_client, method)
        result = push_method(*args, **kwargs)

        # Convert response to serializable format
        return self._serialize_response(result)

    async def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test trade client connection
            trade_health = False
            if self.trade_client:
                try:
                    # Try to get account info
                    account_info = self.trade_client.get_account()
                    trade_health = bool(account_info)
                except:
                    pass

            # Test quote client connection
            quote_health = False
            if self.quote_client:
                try:
                    # Try to get market status
                    market_status = self.quote_client.get_market_status()
                    quote_health = bool(market_status)
                except:
                    pass

            return {
                "process_id": self.process_id,
                "account_id": self.account_id,
                "account_number": self.account.account_number,
                "environment": self.account.environment,
                "is_initialized": self.is_initialized,
                "trade_client_healthy": trade_health,
                "quote_client_healthy": quote_health,
                "task_count": self.task_count,
                "last_heartbeat": self.last_heartbeat.isoformat(),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "process_id": self.process_id,
                "account_id": self.account_id,
                "is_initialized": self.is_initialized,
                "health_error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _serialize_response(self, response) -> Any:
        """
        Serialize Tiger API response to JSON-compatible format.

        Args:
            response: Tiger API response object

        Returns:
            Serializable representation
        """
        try:
            # Handle different response types
            if hasattr(response, "to_dict"):
                return response.to_dict()
            elif hasattr(response, "__dict__"):
                # Convert object attributes to dict
                result = {}
                for key, value in response.__dict__.items():
                    if not key.startswith("_"):
                        try:
                            # Try to serialize the value
                            json.dumps(value)
                            result[key] = value
                        except (TypeError, ValueError):
                            # Convert non-serializable values to string
                            result[key] = str(value)
                return result
            elif isinstance(response, (list, tuple)):
                return [self._serialize_response(item) for item in response]
            elif isinstance(response, dict):
                return {k: self._serialize_response(v) for k, v in response.items()}
            else:
                # Try direct serialization
                try:
                    json.dumps(response)
                    return response
                except (TypeError, ValueError):
                    return str(response)

        except Exception as e:
            logger.warning(f"Failed to serialize response: {e}")
            return {"serialization_error": str(e), "response_type": str(type(response))}


def tiger_worker_main(
    process_id: str, account_id: str, task_queue: mp.Queue, result_queue: mp.Queue
) -> None:
    """
    Main entry point for Tiger worker process.

    Args:
        process_id: Unique process identifier
        account_id: Tiger account ID
        task_queue: Queue for receiving tasks
        result_queue: Queue for sending results
    """
    # Set up process-specific logging
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        f"<cyan>worker-{process_id[:8]}</cyan> | <level>{{message}}</level>",
        level="DEBUG",
    )

    logger.info(f"Starting Tiger worker process {process_id} for account {account_id}")

    worker = None

    try:
        # Create worker instance
        worker = TigerWorker(process_id, account_id)

        # Initialize worker (this is synchronous in the worker process)
        import asyncio

        async def async_main():
            # Initialize worker
            if not await worker.initialize():
                logger.error("Failed to initialize worker")
                return

            # Send ready signal
            ready_msg = {
                "type": "ready",
                "process_id": process_id,
                "account_id": account_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            result_queue.put(ready_msg)

            logger.info(f"Worker {process_id} ready and waiting for tasks")

            # Main processing loop
            while True:
                try:
                    # Get task from queue (with timeout)
                    try:
                        task_data = task_queue.get(timeout=1.0)
                    except:
                        # No task, continue loop
                        continue

                    # Handle special messages
                    if isinstance(task_data, dict):
                        msg_type = task_data.get("type")

                        if msg_type == "shutdown":
                            logger.info("Received shutdown signal")
                            await worker.shutdown()
                            break

                        elif msg_type == "heartbeat":
                            heartbeat_response = await worker.heartbeat()
                            result_queue.put(heartbeat_response)
                            continue

                    # Process regular task
                    if isinstance(task_data, dict) and "task_id" in task_data:
                        response = await worker.process_task(task_data)
                        result_queue.put(response)
                    else:
                        logger.warning(f"Invalid task data: {task_data}")

                except KeyboardInterrupt:
                    logger.info("Received interrupt signal")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    logger.error(traceback.format_exc())

        # Run async main
        asyncio.run(async_main())

    except Exception as e:
        logger.error(f"Fatal error in worker process: {e}")
        logger.error(traceback.format_exc())

    finally:
        if worker:
            try:
                asyncio.run(worker.shutdown())
            except:
                pass

        logger.info(f"Tiger worker process {process_id} exiting")


if __name__ == "__main__":
    # This allows the worker to be run standalone for testing
    if len(sys.argv) >= 3:
        process_id = sys.argv[1]
        account_id = sys.argv[2]

        # Create dummy queues for testing
        task_queue = mp.Queue()
        result_queue = mp.Queue()

        tiger_worker_main(process_id, account_id, task_queue, result_queue)
    else:
        print("Usage: python tiger_worker.py <process_id> <account_id>")
        sys.exit(1)
