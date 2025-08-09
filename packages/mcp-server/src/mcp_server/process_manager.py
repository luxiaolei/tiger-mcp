"""
Process Manager for Tiger API Process Pool.

Coordinates the process pool, manages account-to-process mapping,
monitors process health, and handles resource management.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger
from shared.account_manager import (
    AccountStatus,
    get_account_manager,
)

# Import components
from .tiger_process_pool import (
    ProcessInfo,
    ProcessStatus,
    get_process_pool,
)


class LoadBalanceStrategy(Enum):
    """Load balancing strategy for process allocation."""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    STICKY = "sticky"  # Always use same process for same account


@dataclass
class ProcessMetrics:
    """Metrics for process performance monitoring."""

    process_id: str
    account_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    average_response_time: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    uptime_seconds: float = 0.0
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tasks == 0:
            return 100.0
        return (self.successful_tasks / self.total_tasks) * 100.0

    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.failed_tasks / self.total_tasks) * 100.0


class ProcessManager:
    """
    Process manager for coordinating Tiger API process pool.

    Provides high-level interface for managing worker processes,
    load balancing, health monitoring, and resource management.
    """

    def __init__(
        self,
        load_balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy.STICKY,
        max_concurrent_tasks: int = 10,
        health_check_interval: float = 30.0,
        metrics_retention_hours: int = 24,
        auto_scale_enabled: bool = True,
        min_processes: int = 1,
        max_processes_per_account: int = 1,
    ):
        """
        Initialize process manager.

        Args:
            load_balance_strategy: Strategy for load balancing
            max_concurrent_tasks: Maximum concurrent tasks per process
            health_check_interval: Health check interval in seconds
            metrics_retention_hours: How long to retain metrics
            auto_scale_enabled: Enable automatic scaling
            min_processes: Minimum number of processes to maintain
            max_processes_per_account: Maximum processes per account
        """
        self.load_balance_strategy = load_balance_strategy
        self.max_concurrent_tasks = max_concurrent_tasks
        self.health_check_interval = health_check_interval
        self.metrics_retention_hours = metrics_retention_hours
        self.auto_scale_enabled = auto_scale_enabled
        self.min_processes = min_processes
        self.max_processes_per_account = max_processes_per_account

        # Components
        self.process_pool = get_process_pool()
        self.account_manager = get_account_manager()

        # State tracking
        self.process_metrics: Dict[str, ProcessMetrics] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.round_robin_index = 0

        # Background tasks
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._metrics_cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(
            f"ProcessManager initialized with strategy={load_balance_strategy.value}"
        )

    async def start(self) -> None:
        """Start the process manager and background tasks."""
        try:
            logger.info("Starting ProcessManager...")

            # Start process pool
            await self.process_pool.start()

            # Start background tasks
            self._running = True
            self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
            self._metrics_cleanup_task = asyncio.create_task(
                self._metrics_cleanup_loop()
            )

            logger.info("ProcessManager started successfully")

        except Exception as e:
            logger.error(f"Failed to start ProcessManager: {e}")
            raise

    async def stop(self) -> None:
        """Stop the process manager and clean up resources."""
        try:
            logger.info("Stopping ProcessManager...")
            self._running = False

            # Cancel background tasks
            if self._health_monitor_task:
                self._health_monitor_task.cancel()
                try:
                    await self._health_monitor_task
                except asyncio.CancelledError:
                    pass

            if self._metrics_cleanup_task:
                self._metrics_cleanup_task.cancel()
                try:
                    await self._metrics_cleanup_task
                except asyncio.CancelledError:
                    pass

            # Stop process pool
            await self.process_pool.stop()

            logger.info("ProcessManager stopped")

        except Exception as e:
            logger.error(f"Error stopping ProcessManager: {e}")
            raise

    async def execute_api_call(
        self,
        account_id: str,
        method: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        timeout: float = 30.0,
    ) -> Any:
        """
        Execute API call on appropriate worker process.

        Args:
            account_id: Tiger account ID
            method: API method to execute
            args: Method arguments
            kwargs: Method keyword arguments
            timeout: Call timeout in seconds

        Returns:
            API call result

        Raises:
            RuntimeError: If execution fails
        """
        start_time = datetime.utcnow()
        task_id = str(uuid.uuid4())

        try:
            logger.debug(f"Executing API call {method} for account {account_id}")

            # Validate account
            account = await self.account_manager.get_account_by_id(
                uuid.UUID(account_id)
            )
            if not account:
                raise RuntimeError(f"Account {account_id} not found")

            if account.status != AccountStatus.ACTIVE:
                raise RuntimeError(f"Account {account.account_number} is not active")

            # Execute on process pool
            result = await self.process_pool.execute_task(
                account_id=account_id,
                method=method,
                args=args,
                kwargs=kwargs,
                timeout=timeout,
            )

            # Record success
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            await self._record_task_completion(
                task_id, account_id, method, True, execution_time
            )

            logger.debug(
                f"API call {method} completed successfully in {execution_time:.2f}s"
            )
            return result

        except Exception as e:
            # Record failure
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            await self._record_task_completion(
                task_id, account_id, method, False, execution_time, str(e)
            )

            logger.error(f"API call {method} failed: {e}")
            raise

    async def get_account_process_status(
        self, account_id: str
    ) -> Optional[ProcessInfo]:
        """Get status of process handling the specified account."""
        return await self.process_pool.get_process_status(account_id)

    async def get_all_process_status(self) -> List[ProcessInfo]:
        """Get status of all processes."""
        return await self.process_pool.get_all_processes()

    async def get_process_metrics(
        self, process_id: str = None
    ) -> Dict[str, ProcessMetrics]:
        """
        Get process performance metrics.

        Args:
            process_id: Specific process ID, or None for all processes

        Returns:
            Dictionary of process metrics
        """
        if process_id:
            return {process_id: self.process_metrics.get(process_id)}
        else:
            return self.process_metrics.copy()

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get overall system metrics."""
        try:
            processes = await self.get_all_process_status()

            # Count by status
            status_counts = {}
            for process in processes:
                status = process.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            # Calculate aggregate metrics
            total_tasks = sum(m.total_tasks for m in self.process_metrics.values())
            total_successful = sum(
                m.successful_tasks for m in self.process_metrics.values()
            )
            total_failed = sum(m.failed_tasks for m in self.process_metrics.values())

            avg_response_time = 0.0
            if self.process_metrics:
                avg_response_time = sum(
                    m.average_response_time for m in self.process_metrics.values()
                ) / len(self.process_metrics)

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "total_processes": len(processes),
                "status_counts": status_counts,
                "total_tasks": total_tasks,
                "successful_tasks": total_successful,
                "failed_tasks": total_failed,
                "success_rate": (total_successful / max(total_tasks, 1)) * 100,
                "average_response_time": avg_response_time,
                "load_balance_strategy": self.load_balance_strategy.value,
                "auto_scale_enabled": self.auto_scale_enabled,
            }

        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"error": str(e)}

    async def restart_account_process(self, account_id: str) -> bool:
        """
        Restart process for specific account.

        Args:
            account_id: Account ID

        Returns:
            True if restart was successful
        """
        try:
            logger.info(f"Restarting process for account {account_id}")

            success = await self.process_pool.restart_process(account_id)

            if success:
                # Reset metrics for the restarted process
                processes = await self.get_all_process_status()
                for process in processes:
                    if process.account_id == account_id:
                        self._reset_process_metrics(process.process_id, account_id)
                        break

            return success

        except Exception as e:
            logger.error(f"Failed to restart process for account {account_id}: {e}")
            return False

    async def health_check_account(self, account_id: str) -> Dict[str, Any]:
        """
        Perform health check for specific account.

        Args:
            account_id: Account ID

        Returns:
            Health check results
        """
        try:
            result = await self.execute_api_call(
                account_id=account_id, method="health_check", timeout=10.0
            )

            return {
                "account_id": account_id,
                "healthy": True,
                "details": result,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed for account {account_id}: {e}")
            return {
                "account_id": account_id,
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def health_check_all_accounts(self) -> List[Dict[str, Any]]:
        """Perform health check for all active accounts."""
        try:
            # Get all active accounts
            accounts = await self.account_manager.list_accounts(
                status=AccountStatus.ACTIVE, include_inactive=False
            )

            # Run health checks concurrently
            tasks = [self.health_check_account(str(account.id)) for account in accounts]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and convert to results
            health_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    health_results.append(
                        {
                            "account_id": str(accounts[i].id),
                            "healthy": False,
                            "error": str(result),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                else:
                    health_results.append(result)

            return health_results

        except Exception as e:
            logger.error(f"Failed to run health checks: {e}")
            return []

    # Private methods

    async def _record_task_completion(
        self,
        task_id: str,
        account_id: str,
        method: str,
        success: bool,
        execution_time: float,
        error: str = None,
    ) -> None:
        """Record task completion for metrics."""
        try:
            # Find process handling this account
            processes = await self.get_all_process_status()
            process_id = None

            for process in processes:
                if process.account_id == account_id:
                    process_id = process.process_id
                    break

            if not process_id:
                return

            # Initialize metrics if not exists
            if process_id not in self.process_metrics:
                self._reset_process_metrics(process_id, account_id)

            metrics = self.process_metrics[process_id]

            # Update metrics
            metrics.total_tasks += 1
            if success:
                metrics.successful_tasks += 1
            else:
                metrics.failed_tasks += 1
                metrics.last_error = error
                metrics.last_error_time = datetime.utcnow()

            # Update average response time
            if metrics.total_tasks == 1:
                metrics.average_response_time = execution_time
            else:
                # Exponential moving average
                alpha = 0.1
                metrics.average_response_time = (
                    alpha * execution_time + (1 - alpha) * metrics.average_response_time
                )

            # Add to history
            self.task_history.append(
                {
                    "task_id": task_id,
                    "process_id": process_id,
                    "account_id": account_id,
                    "method": method,
                    "success": success,
                    "execution_time": execution_time,
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        except Exception as e:
            logger.error(f"Failed to record task completion: {e}")

    def _reset_process_metrics(self, process_id: str, account_id: str) -> None:
        """Reset metrics for a process."""
        self.process_metrics[process_id] = ProcessMetrics(
            process_id=process_id, account_id=account_id
        )

    async def _health_monitor_loop(self) -> None:
        """Background task for health monitoring."""
        logger.info("Health monitor started")

        while self._running:
            try:
                # Update process metrics
                await self._update_process_metrics()

                # Check for unhealthy processes
                await self._check_process_health()

                # Auto-scale if enabled
                if self.auto_scale_enabled:
                    await self._auto_scale_processes()

                await asyncio.sleep(self.health_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(self.health_check_interval)

        logger.info("Health monitor stopped")

    async def _metrics_cleanup_loop(self) -> None:
        """Background task for cleaning up old metrics."""
        logger.info("Metrics cleanup started")

        while self._running:
            try:
                # Clean up old task history
                cutoff_time = datetime.utcnow() - timedelta(
                    hours=self.metrics_retention_hours
                )

                old_count = len(self.task_history)
                self.task_history = [
                    task
                    for task in self.task_history
                    if datetime.fromisoformat(task["timestamp"]) > cutoff_time
                ]
                new_count = len(self.task_history)

                if old_count > new_count:
                    logger.debug(f"Cleaned up {old_count - new_count} old task records")

                # Sleep for an hour before next cleanup
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics cleanup: {e}")
                await asyncio.sleep(3600)

        logger.info("Metrics cleanup stopped")

    async def _update_process_metrics(self) -> None:
        """Update process metrics with current information."""
        try:
            processes = await self.get_all_process_status()

            for process in processes:
                # Initialize metrics if not exists
                if process.process_id not in self.process_metrics:
                    self._reset_process_metrics(process.process_id, process.account_id)

                metrics = self.process_metrics[process.process_id]

                # Update uptime
                if process.created_at:
                    metrics.uptime_seconds = (
                        datetime.utcnow() - process.created_at
                    ).total_seconds()

                # Update system metrics (would need process monitoring)
                # metrics.memory_usage_mb = get_process_memory(process.pid)
                # metrics.cpu_usage_percent = get_process_cpu(process.pid)

        except Exception as e:
            logger.error(f"Failed to update process metrics: {e}")

    async def _check_process_health(self) -> None:
        """Check process health and restart unhealthy processes."""
        try:
            processes = await self.get_all_process_status()

            for process in processes:
                metrics = self.process_metrics.get(process.process_id)
                if not metrics:
                    continue

                # Check error rate
                if metrics.total_tasks > 10 and metrics.error_rate > 50:
                    logger.warning(
                        f"Process {process.process_id} has high error rate: {metrics.error_rate:.1f}%"
                    )
                    await self.restart_account_process(process.account_id)
                    continue

                # Check if process is stuck
                if (
                    process.status == ProcessStatus.BUSY
                    and process.last_heartbeat
                    and (datetime.utcnow() - process.last_heartbeat).total_seconds()
                    > 300
                ):
                    logger.warning(
                        f"Process {process.process_id} appears stuck, restarting"
                    )
                    await self.restart_account_process(process.account_id)
                    continue

        except Exception as e:
            logger.error(f"Failed to check process health: {e}")

    async def _auto_scale_processes(self) -> None:
        """Auto-scale processes based on load."""
        try:
            # Get current process count and load
            processes = await self.get_all_process_status()
            active_processes = [
                p
                for p in processes
                if p.status in [ProcessStatus.READY, ProcessStatus.BUSY]
            ]

            # Simple auto-scaling logic - this could be enhanced
            if len(active_processes) < self.min_processes:
                logger.info("Process count below minimum, considering scaling up")
                # Would implement scaling logic here

        except Exception as e:
            logger.error(f"Failed to auto-scale processes: {e}")


# Global process manager instance
_process_manager: Optional[ProcessManager] = None


def get_process_manager() -> ProcessManager:
    """Get global process manager instance."""
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager
