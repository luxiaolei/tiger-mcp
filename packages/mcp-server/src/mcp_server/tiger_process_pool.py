"""
Tiger Process Pool Manager.

Manages isolated worker processes for Tiger SDK single-account limitation.
Each process handles one Tiger account with SDK loaded at fixed path.
"""

import asyncio
import multiprocessing as mp
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

# Import shared components
from shared.account_manager import get_account_manager
from shared.config import get_config


class ProcessStatus(Enum):
    """Process status enumeration."""

    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class ProcessInfo:
    """Information about a worker process."""

    process_id: str
    account_id: str
    account_number: str
    pid: Optional[int] = None
    status: ProcessStatus = ProcessStatus.STARTING
    created_at: datetime = None
    last_heartbeat: datetime = None
    error_count: int = 0
    current_task: Optional[str] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.utcnow()


@dataclass
class TaskRequest:
    """Task request for worker process."""

    task_id: str
    method: str
    args: List[Any] = None
    kwargs: Dict[str, Any] = None
    timeout: float = 30.0

    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.kwargs is None:
            self.kwargs = {}


@dataclass
class TaskResponse:
    """Task response from worker process."""

    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class TigerProcessPool:
    """
    Process pool manager for Tiger SDK single-account limitation.

    Manages isolated worker processes where each process handles one Tiger account
    with SDK loaded at startup. Provides process lifecycle management, health monitoring,
    and automatic recovery.
    """

    def __init__(
        self,
        max_processes: int = None,
        process_timeout: float = 300.0,
        heartbeat_interval: float = 10.0,
        max_restarts: int = 3,
        restart_cooldown: float = 60.0,
    ):
        """
        Initialize the Tiger process pool.

        Args:
            max_processes: Maximum number of worker processes (default: CPU count)
            process_timeout: Process timeout in seconds
            heartbeat_interval: Heartbeat check interval
            max_restarts: Maximum restart attempts per process
            restart_cooldown: Cooldown between restart attempts
        """
        self.config = get_config()
        self.account_manager = get_account_manager()

        # Process management
        self.max_processes = max_processes or mp.cpu_count()
        self.process_timeout = process_timeout
        self.heartbeat_interval = heartbeat_interval
        self.max_restarts = max_restarts
        self.restart_cooldown = restart_cooldown

        # Process tracking
        self.processes: Dict[str, ProcessInfo] = {}  # process_id -> ProcessInfo
        self.account_to_process: Dict[str, str] = {}  # account_id -> process_id
        self.process_pool: Dict[str, mp.Process] = {}  # process_id -> Process
        self.task_queues: Dict[str, mp.Queue] = {}  # process_id -> Queue
        self.result_queues: Dict[str, mp.Queue] = {}  # process_id -> Queue

        # Threading for async operations
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_processes)
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None

        # Shutdown flag
        self._shutdown = False

        logger.info(
            f"TigerProcessPool initialized with max_processes={self.max_processes}"
        )

    async def start(self) -> None:
        """Start the process pool and monitoring."""
        try:
            logger.info("Starting Tiger process pool...")

            # Start process monitoring
            self._monitoring_active = True
            self._monitoring_task = asyncio.create_task(self._monitor_processes())

            logger.info("Tiger process pool started successfully")

        except Exception as e:
            logger.error(f"Failed to start process pool: {e}")
            raise

    async def stop(self) -> None:
        """Stop all processes and clean up resources."""
        try:
            logger.info("Stopping Tiger process pool...")
            self._shutdown = True

            # Stop monitoring
            if self._monitoring_task:
                self._monitoring_active = False
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass

            # Stop all processes
            await self._stop_all_processes()

            # Clean up thread pool
            self.thread_pool.shutdown(wait=True)

            logger.info("Tiger process pool stopped")

        except Exception as e:
            logger.error(f"Error stopping process pool: {e}")
            raise

    async def get_or_create_process(self, account_id: str) -> str:
        """
        Get existing process for account or create a new one.

        Args:
            account_id: Tiger account ID

        Returns:
            Process ID

        Raises:
            RuntimeError: If process creation fails
        """
        try:
            # Check if process already exists for this account
            if account_id in self.account_to_process:
                process_id = self.account_to_process[account_id]
                process_info = self.processes.get(process_id)

                if process_info and process_info.status in [
                    ProcessStatus.READY,
                    ProcessStatus.BUSY,
                ]:
                    return process_id
                else:
                    # Process is not healthy, remove and recreate
                    await self._remove_process(process_id)

            # Check process limit
            active_processes = sum(
                1
                for p in self.processes.values()
                if p.status not in [ProcessStatus.STOPPED, ProcessStatus.ERROR]
            )

            if active_processes >= self.max_processes:
                raise RuntimeError(f"Maximum processes ({self.max_processes}) reached")

            # Create new process
            process_id = str(uuid.uuid4())
            return await self._create_process(process_id, account_id)

        except Exception as e:
            logger.error(f"Failed to get/create process for account {account_id}: {e}")
            raise

    async def execute_task(
        self,
        account_id: str,
        method: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        timeout: float = 30.0,
    ) -> Any:
        """
        Execute a task on the worker process for the specified account.

        Args:
            account_id: Tiger account ID
            method: Method name to execute
            args: Method arguments
            kwargs: Method keyword arguments
            timeout: Task timeout in seconds

        Returns:
            Task result

        Raises:
            TimeoutError: If task times out
            RuntimeError: If task execution fails
        """
        try:
            # Get or create process for account
            process_id = await self.get_or_create_process(account_id)
            process_info = self.processes[process_id]

            # Mark process as busy
            process_info.status = ProcessStatus.BUSY
            task_id = str(uuid.uuid4())
            process_info.current_task = task_id

            # Create task request
            task_request = TaskRequest(
                task_id=task_id,
                method=method,
                args=args or [],
                kwargs=kwargs or {},
                timeout=timeout,
            )

            # Submit task to worker process
            task_queue = self.task_queues[process_id]
            result_queue = self.result_queues[process_id]

            # Send task request
            await self._put_queue_async(task_queue, asdict(task_request), timeout=5.0)

            # Wait for result
            start_time = time.time()
            try:
                result_data = await self._get_queue_async(result_queue, timeout=timeout)
                execution_time = time.time() - start_time

                # Parse response
                task_response = TaskResponse(**result_data)

                # Update process status
                process_info.status = ProcessStatus.READY
                process_info.current_task = None
                process_info.last_heartbeat = datetime.utcnow()

                if task_response.success:
                    logger.debug(f"Task {task_id} completed in {execution_time:.2f}s")
                    return task_response.result
                else:
                    # Task failed
                    error_msg = task_response.error or "Unknown error"
                    logger.error(f"Task {task_id} failed: {error_msg}")

                    # Increment error count
                    process_info.error_count += 1
                    if process_info.error_count >= 3:
                        # Too many errors, restart process
                        logger.warning(
                            f"Process {process_id} has too many errors, restarting..."
                        )
                        await self._restart_process(process_id)

                    raise RuntimeError(f"Task execution failed: {error_msg}")

            except TimeoutError:
                # Task timed out
                process_info.status = ProcessStatus.ERROR
                process_info.current_task = None
                logger.error(f"Task {task_id} timed out after {timeout}s")

                # Consider restarting process after timeout
                await self._restart_process(process_id)
                raise TimeoutError(f"Task execution timed out after {timeout}s")

        except Exception as e:
            logger.error(
                f"Failed to execute task {method} on account {account_id}: {e}"
            )
            raise

    async def get_process_status(self, account_id: str) -> Optional[ProcessInfo]:
        """Get status of process handling the specified account."""
        process_id = self.account_to_process.get(account_id)
        if process_id:
            return self.processes.get(process_id)
        return None

    async def get_all_processes(self) -> List[ProcessInfo]:
        """Get status of all processes."""
        return list(self.processes.values())

    async def restart_process(self, account_id: str) -> bool:
        """
        Restart process for the specified account.

        Args:
            account_id: Tiger account ID

        Returns:
            True if restart was successful
        """
        process_id = self.account_to_process.get(account_id)
        if process_id:
            return await self._restart_process(process_id)
        return False

    async def remove_process(self, account_id: str) -> bool:
        """
        Remove process for the specified account.

        Args:
            account_id: Tiger account ID

        Returns:
            True if removal was successful
        """
        process_id = self.account_to_process.get(account_id)
        if process_id:
            return await self._remove_process(process_id)
        return False

    # Private methods

    async def _create_process(self, process_id: str, account_id: str) -> str:
        """Create a new worker process."""
        try:
            # Get account details
            account = await self.account_manager.get_account_by_id(
                uuid.UUID(account_id)
            )
            if not account:
                raise RuntimeError(f"Account {account_id} not found")

            # Create process info
            process_info = ProcessInfo(
                process_id=process_id,
                account_id=account_id,
                account_number=account.account_number,
                status=ProcessStatus.STARTING,
            )

            # Create communication queues
            task_queue = mp.Queue()
            result_queue = mp.Queue()

            # Start worker process
            from .tiger_worker import tiger_worker_main

            process = mp.Process(
                target=tiger_worker_main,
                args=(process_id, account_id, task_queue, result_queue),
                name=f"tiger_worker_{account.account_number}",
            )
            process.start()

            # Update tracking
            process_info.pid = process.pid
            self.processes[process_id] = process_info
            self.account_to_process[account_id] = process_id
            self.process_pool[process_id] = process
            self.task_queues[process_id] = task_queue
            self.result_queues[process_id] = result_queue

            # Wait for process to be ready
            ready_timeout = 30.0
            start_time = time.time()

            while time.time() - start_time < ready_timeout:
                # Check if process is still alive
                if not process.is_alive():
                    raise RuntimeError("Worker process died during startup")

                # Check for ready signal
                try:
                    if not result_queue.empty():
                        ready_msg = result_queue.get_nowait()
                        if ready_msg.get("type") == "ready":
                            process_info.status = ProcessStatus.READY
                            process_info.last_heartbeat = datetime.utcnow()
                            logger.info(
                                f"Worker process {process_id} is ready for account {account.account_number}"
                            )
                            return process_id
                except:
                    pass

                await asyncio.sleep(0.5)

            # Timeout waiting for ready signal
            await self._remove_process(process_id)
            raise RuntimeError("Worker process failed to start within timeout")

        except Exception as e:
            logger.error(f"Failed to create process {process_id}: {e}")
            await self._remove_process(process_id)
            raise

    async def _restart_process(self, process_id: str) -> bool:
        """Restart a worker process."""
        try:
            process_info = self.processes.get(process_id)
            if not process_info:
                return False

            account_id = process_info.account_id
            logger.info(f"Restarting process {process_id} for account {account_id}")

            # Remove old process
            await self._remove_process(process_id)

            # Create new process with same ID
            await self._create_process(process_id, account_id)

            return True

        except Exception as e:
            logger.error(f"Failed to restart process {process_id}: {e}")
            return False

    async def _remove_process(self, process_id: str) -> bool:
        """Remove a worker process."""
        try:
            process_info = self.processes.get(process_id)
            if not process_info:
                return True

            logger.info(f"Removing process {process_id}")

            # Update status
            process_info.status = ProcessStatus.STOPPING

            # Stop the process
            process = self.process_pool.get(process_id)
            if process and process.is_alive():
                # Try graceful shutdown first
                task_queue = self.task_queues.get(process_id)
                if task_queue:
                    try:
                        shutdown_task = {"type": "shutdown"}
                        task_queue.put_nowait(shutdown_task)
                        process.join(timeout=5.0)
                    except:
                        pass

                # Force terminate if still alive
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5.0)

                # Kill if still alive
                if process.is_alive():
                    process.kill()
                    process.join()

            # Clean up tracking
            account_id = process_info.account_id
            if account_id in self.account_to_process:
                del self.account_to_process[account_id]

            if process_id in self.processes:
                del self.processes[process_id]

            if process_id in self.process_pool:
                del self.process_pool[process_id]

            if process_id in self.task_queues:
                del self.task_queues[process_id]

            if process_id in self.result_queues:
                del self.result_queues[process_id]

            process_info.status = ProcessStatus.STOPPED
            logger.info(f"Process {process_id} removed successfully")

            return True

        except Exception as e:
            logger.error(f"Failed to remove process {process_id}: {e}")
            return False

    async def _stop_all_processes(self) -> None:
        """Stop all worker processes."""
        process_ids = list(self.processes.keys())

        for process_id in process_ids:
            try:
                await self._remove_process(process_id)
            except Exception as e:
                logger.error(f"Error stopping process {process_id}: {e}")

    async def _monitor_processes(self) -> None:
        """Monitor process health and perform maintenance."""
        logger.info("Process monitoring started")

        while self._monitoring_active and not self._shutdown:
            try:
                current_time = datetime.utcnow()

                # Check each process
                for process_id, process_info in list(self.processes.items()):
                    try:
                        # Check if process is still alive
                        process = self.process_pool.get(process_id)
                        if process and not process.is_alive():
                            logger.warning(f"Process {process_id} died unexpectedly")
                            await self._restart_process(process_id)
                            continue

                        # Check heartbeat timeout
                        if process_info.last_heartbeat:
                            heartbeat_age = (
                                current_time - process_info.last_heartbeat
                            ).total_seconds()
                            if heartbeat_age > self.process_timeout:
                                logger.warning(
                                    f"Process {process_id} heartbeat timeout ({heartbeat_age:.1f}s)"
                                )
                                await self._restart_process(process_id)
                                continue

                        # Send heartbeat check if ready
                        if process_info.status == ProcessStatus.READY:
                            try:
                                task_queue = self.task_queues.get(process_id)
                                if task_queue:
                                    heartbeat_task = {
                                        "type": "heartbeat",
                                        "timestamp": current_time.isoformat(),
                                    }
                                    task_queue.put_nowait(heartbeat_task)
                            except:
                                pass

                    except Exception as e:
                        logger.error(f"Error monitoring process {process_id}: {e}")

                # Wait before next check
                await asyncio.sleep(self.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in process monitoring: {e}")
                await asyncio.sleep(self.heartbeat_interval)

        logger.info("Process monitoring stopped")

    async def _put_queue_async(
        self, queue: mp.Queue, item: Any, timeout: float = None
    ) -> None:
        """Put item in queue asynchronously."""
        loop = asyncio.get_event_loop()

        def _put():
            if timeout:
                # Use timeout for blocking put
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        queue.put_nowait(item)
                        return True
                    except:
                        time.sleep(0.1)
                raise TimeoutError("Queue put timeout")
            else:
                queue.put(item)
                return True

        try:
            await loop.run_in_executor(self.thread_pool, _put)
        except Exception as e:
            raise TimeoutError(f"Failed to put item in queue: {e}")

    async def _get_queue_async(self, queue: mp.Queue, timeout: float = None) -> Any:
        """Get item from queue asynchronously."""
        loop = asyncio.get_event_loop()

        def _get():
            if timeout:
                # Use timeout for blocking get
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        return queue.get_nowait()
                    except:
                        time.sleep(0.1)
                raise TimeoutError("Queue get timeout")
            else:
                return queue.get()

        try:
            return await loop.run_in_executor(self.thread_pool, _get)
        except Exception as e:
            raise TimeoutError(f"Failed to get item from queue: {e}")


# Global process pool instance
_process_pool: Optional[TigerProcessPool] = None


def get_process_pool() -> TigerProcessPool:
    """Get global process pool instance."""
    global _process_pool
    if _process_pool is None:
        _process_pool = TigerProcessPool()
    return _process_pool
