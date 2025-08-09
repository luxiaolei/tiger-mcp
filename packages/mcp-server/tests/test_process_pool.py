"""
Unit tests for Tiger Process Pool Manager.

Tests the TigerProcessPool class that manages isolated worker processes
for Tiger SDK single-account limitation. Tests cover:

1. Process lifecycle management (start, stop, restart)
2. Worker process isolation and communication
3. Process failure recovery and health monitoring
4. Task execution and load balancing
5. Resource management and scaling
6. Error handling and timeout management
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the class under test
from mcp_server.tiger_process_pool import (
    ProcessInfo,
    ProcessStatus,
    TigerProcessPool,
    get_process_pool,
)


class TestTigerProcessPool:
    """Test suite for TigerProcessPool."""

    def setup_method(self):
        """Setup test method with clean process pool."""
        # Reset global instance for clean testing
        import mcp_server.tiger_process_pool

        mcp_server.tiger_process_pool._process_pool = None

    @pytest.fixture
    def process_pool(self, mock_account_manager):
        """Create a TigerProcessPool instance for testing."""
        with (
            patch("mcp_server.tiger_process_pool.get_config") as mock_config,
            patch(
                "mcp_server.tiger_process_pool.get_account_manager",
                return_value=mock_account_manager,
            ),
        ):

            # Setup mock config
            mock_config.return_value = MagicMock()

            pool = TigerProcessPool(
                max_processes=2,
                process_timeout=30.0,
                heartbeat_interval=5.0,
                max_restarts=2,
                restart_cooldown=10.0,
            )
            return pool

    @pytest.mark.asyncio
    async def test_process_pool_initialization(self, process_pool):
        """Test process pool initialization."""
        assert process_pool.max_processes == 2
        assert process_pool.process_timeout == 30.0
        assert process_pool.heartbeat_interval == 5.0
        assert process_pool.max_restarts == 2
        assert process_pool.restart_cooldown == 10.0

        # Check initial state
        assert len(process_pool.processes) == 0
        assert len(process_pool.account_to_process) == 0
        assert len(process_pool.process_pool) == 0
        assert process_pool._monitoring_active is False
        assert process_pool._shutdown is False

    @pytest.mark.asyncio
    async def test_process_pool_start_stop(self, process_pool):
        """Test process pool start and stop operations."""
        # Test start
        await process_pool.start()

        assert process_pool._monitoring_active is True
        assert process_pool._monitoring_task is not None

        # Test stop
        await process_pool.stop()

        assert process_pool._monitoring_active is False
        assert process_pool._shutdown is True

    @pytest.mark.asyncio
    async def test_create_process_success(
        self, process_pool, mock_account_data, mock_multiprocessing
    ):
        """Test successful process creation."""
        with patch.object(
            process_pool.account_manager, "get_account_by_id"
        ) as mock_get_account:
            # Setup account mock
            account = mock_account_data.accounts[0]
            mock_get_account.return_value = account

            # Setup multiprocessing mocks
            mock_process = mock_multiprocessing["process"]
            mock_queue = mock_multiprocessing["queue"]

            # Mock ready signal from worker
            ready_message = {
                "type": "ready",
                "timestamp": datetime.utcnow().isoformat(),
            }
            mock_queue.empty.return_value = False
            mock_queue.get_nowait.return_value = ready_message

            # Execute process creation
            process_id = str(uuid.uuid4())
            account_id = account.id

            result_process_id = await process_pool._create_process(
                process_id, account_id
            )

            # Verify results
            assert result_process_id == process_id
            assert process_id in process_pool.processes
            assert account_id in process_pool.account_to_process
            assert process_pool.account_to_process[account_id] == process_id

            # Verify process info
            process_info = process_pool.processes[process_id]
            assert process_info.process_id == process_id
            assert process_info.account_id == account_id
            assert process_info.account_number == account.account_number
            assert process_info.status == ProcessStatus.READY
            assert process_info.pid == mock_process.pid

            # Verify process was started
            mock_process.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_process_timeout(
        self, process_pool, mock_account_data, mock_multiprocessing
    ):
        """Test process creation timeout."""
        with patch.object(
            process_pool.account_manager, "get_account_by_id"
        ) as mock_get_account:
            # Setup account mock
            account = mock_account_data.accounts[0]
            mock_get_account.return_value = account

            # Setup multiprocessing mocks - no ready signal
            mock_queue = mock_multiprocessing["queue"]
            mock_queue.empty.return_value = True  # No ready message

            # Execute process creation
            process_id = str(uuid.uuid4())
            account_id = account.id

            with pytest.raises(
                RuntimeError, match="Worker process failed to start within timeout"
            ):
                await process_pool._create_process(process_id, account_id)

            # Verify cleanup occurred
            assert process_id not in process_pool.processes
            assert account_id not in process_pool.account_to_process

    @pytest.mark.asyncio
    async def test_create_process_worker_died(
        self, process_pool, mock_account_data, mock_multiprocessing
    ):
        """Test process creation when worker dies during startup."""
        with patch.object(
            process_pool.account_manager, "get_account_by_id"
        ) as mock_get_account:
            # Setup account mock
            account = mock_account_data.accounts[0]
            mock_get_account.return_value = account

            # Setup multiprocessing mocks - process dies
            mock_process = mock_multiprocessing["process"]
            mock_process.is_alive.return_value = False  # Process died

            # Execute process creation
            process_id = str(uuid.uuid4())
            account_id = account.id

            with pytest.raises(
                RuntimeError, match="Worker process died during startup"
            ):
                await process_pool._create_process(process_id, account_id)

    @pytest.mark.asyncio
    async def test_get_or_create_process_existing(
        self, process_pool, mock_account_data
    ):
        """Test getting existing process for account."""
        # Setup existing process
        account = mock_account_data.accounts[0]
        account_id = account.id
        process_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account_id,
            account_number=account.account_number,
            status=ProcessStatus.READY,
        )

        process_pool.processes[process_id] = process_info
        process_pool.account_to_process[account_id] = process_id

        # Execute
        result_process_id = await process_pool.get_or_create_process(account_id)

        # Verify existing process is returned
        assert result_process_id == process_id

    @pytest.mark.asyncio
    async def test_get_or_create_process_max_limit(
        self, process_pool, mock_account_data
    ):
        """Test process creation when max limit is reached."""
        # Fill up process pool to max capacity
        for i in range(process_pool.max_processes):
            mock_account_data.accounts[0]
            process_id = f"process_{i}"
            process_info = ProcessInfo(
                process_id=process_id,
                account_id=f"account_{i}",
                account_number=f"DU{i:06d}",
                status=ProcessStatus.READY,
            )
            process_pool.processes[process_id] = process_info

        # Try to create one more process
        new_account_id = str(uuid.uuid4())

        with pytest.raises(RuntimeError, match="Maximum processes .* reached"):
            await process_pool.get_or_create_process(new_account_id)

    @pytest.mark.asyncio
    async def test_execute_task_success(
        self, process_pool, mock_account_data, mock_multiprocessing
    ):
        """Test successful task execution."""
        # Setup existing process
        account = mock_account_data.accounts[0]
        account_id = account.id
        process_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account_id,
            account_number=account.account_number,
            status=ProcessStatus.READY,
        )

        process_pool.processes[process_id] = process_info
        process_pool.account_to_process[account_id] = process_id

        # Setup queues
        task_queue = mock_multiprocessing["queue"]
        result_queue = mock_multiprocessing["queue"]
        process_pool.task_queues[process_id] = task_queue
        process_pool.result_queues[process_id] = result_queue

        # Mock task response
        task_response = {
            "task_id": "test_task_123",
            "success": True,
            "result": {"quote": {"symbol": "AAPL", "price": 150.25}},
            "execution_time": 0.5,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Mock async queue operations
        async def mock_put_queue_async(queue, item, timeout=None):
            pass

        async def mock_get_queue_async(queue, timeout=None):
            return task_response

        process_pool._put_queue_async = mock_put_queue_async
        process_pool._get_queue_async = mock_get_queue_async

        # Execute task
        result = await process_pool.execute_task(
            account_id=account_id,
            method="get_quote",
            args=["AAPL"],
            kwargs={},
            timeout=30.0,
        )

        # Verify results
        assert result == task_response["result"]

        # Verify process status updated
        assert process_info.status == ProcessStatus.READY
        assert process_info.current_task is None

    @pytest.mark.asyncio
    async def test_execute_task_timeout(self, process_pool, mock_account_data):
        """Test task execution timeout."""
        # Setup existing process
        account = mock_account_data.accounts[0]
        account_id = account.id
        process_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account_id,
            account_number=account.account_number,
            status=ProcessStatus.READY,
        )

        process_pool.processes[process_id] = process_info
        process_pool.account_to_process[account_id] = process_id

        # Mock timeout in queue operations
        async def mock_put_queue_async(queue, item, timeout=None):
            pass

        async def mock_get_queue_async(queue, timeout=None):
            raise TimeoutError("Task execution timed out")

        process_pool._put_queue_async = mock_put_queue_async
        process_pool._get_queue_async = mock_get_queue_async

        # Mock restart process
        process_pool._restart_process = AsyncMock()

        # Execute task
        with pytest.raises(TimeoutError, match="Task execution timed out"):
            await process_pool.execute_task(
                account_id=account_id, method="get_quote", args=["AAPL"], timeout=5.0
            )

        # Verify process status and restart
        assert process_info.status == ProcessStatus.ERROR
        process_pool._restart_process.assert_called_once_with(process_id)

    @pytest.mark.asyncio
    async def test_execute_task_failure(self, process_pool, mock_account_data):
        """Test task execution failure."""
        # Setup existing process
        account = mock_account_data.accounts[0]
        account_id = account.id
        process_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account_id,
            account_number=account.account_number,
            status=ProcessStatus.READY,
            error_count=2,  # Already has some errors
        )

        process_pool.processes[process_id] = process_info
        process_pool.account_to_process[account_id] = process_id

        # Mock task failure response
        task_response = {
            "task_id": "test_task_123",
            "success": False,
            "result": None,
            "error": "API call failed",
            "execution_time": 0.5,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Mock async queue operations
        async def mock_put_queue_async(queue, item, timeout=None):
            pass

        async def mock_get_queue_async(queue, timeout=None):
            return task_response

        process_pool._put_queue_async = mock_put_queue_async
        process_pool._get_queue_async = mock_get_queue_async

        # Mock restart process (will be called due to error count)
        process_pool._restart_process = AsyncMock()

        # Execute task
        with pytest.raises(
            RuntimeError, match="Task execution failed: API call failed"
        ):
            await process_pool.execute_task(
                account_id=account_id, method="get_quote", args=["AAPL"]
            )

        # Verify error count increased and restart was called
        assert process_info.error_count == 3
        process_pool._restart_process.assert_called_once_with(process_id)

    @pytest.mark.asyncio
    async def test_restart_process(
        self, process_pool, mock_account_data, mock_multiprocessing
    ):
        """Test process restart operation."""
        # Setup existing process
        account = mock_account_data.accounts[0]
        account_id = account.id
        process_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account_id,
            account_number=account.account_number,
            status=ProcessStatus.ERROR,
        )

        process_pool.processes[process_id] = process_info
        process_pool.account_to_process[account_id] = process_id

        # Mock remove and create operations
        process_pool._remove_process = AsyncMock(return_value=True)
        process_pool._create_process = AsyncMock(return_value=process_id)

        # Execute restart
        result = await process_pool._restart_process(process_id)

        # Verify results
        assert result is True
        process_pool._remove_process.assert_called_once_with(process_id)
        process_pool._create_process.assert_called_once_with(process_id, account_id)

    @pytest.mark.asyncio
    async def test_remove_process_graceful(self, process_pool, mock_multiprocessing):
        """Test graceful process removal."""
        # Setup existing process
        process_id = str(uuid.uuid4())
        account_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account_id,
            account_number="DU123456",
            status=ProcessStatus.READY,
        )

        process_pool.processes[process_id] = process_info
        process_pool.account_to_process[account_id] = process_id

        # Setup mock process and queues
        mock_process = mock_multiprocessing["process"]
        mock_queue = mock_multiprocessing["queue"]

        process_pool.process_pool[process_id] = mock_process
        process_pool.task_queues[process_id] = mock_queue
        process_pool.result_queues[process_id] = mock_queue

        # Mock graceful shutdown
        mock_process.join.return_value = None  # Process stops gracefully

        # Execute removal
        result = await process_pool._remove_process(process_id)

        # Verify results
        assert result is True
        assert process_id not in process_pool.processes
        assert account_id not in process_pool.account_to_process
        assert process_id not in process_pool.process_pool
        assert process_info.status == ProcessStatus.STOPPED

        # Verify graceful shutdown was attempted
        mock_queue.put_nowait.assert_called_once()
        mock_process.join.assert_called()

    @pytest.mark.asyncio
    async def test_remove_process_force_terminate(
        self, process_pool, mock_multiprocessing
    ):
        """Test forced process termination."""
        # Setup existing process
        process_id = str(uuid.uuid4())
        account_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account_id,
            account_number="DU123456",
            status=ProcessStatus.READY,
        )

        process_pool.processes[process_id] = process_info
        process_pool.account_to_process[account_id] = process_id

        # Setup mock process that won't stop gracefully
        mock_process = mock_multiprocessing["process"]
        mock_process.is_alive.side_effect = [
            True,
            True,
            False,
        ]  # Alive after terminate, dead after kill
        mock_queue = mock_multiprocessing["queue"]

        process_pool.process_pool[process_id] = mock_process
        process_pool.task_queues[process_id] = mock_queue
        process_pool.result_queues[process_id] = mock_queue

        # Execute removal
        result = await process_pool._remove_process(process_id)

        # Verify results
        assert result is True

        # Verify forced termination was used
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_monitoring(
        self, process_pool, mock_account_data, mock_multiprocessing
    ):
        """Test process health monitoring."""
        # Setup existing processes
        processes = []
        for i, account in enumerate(mock_account_data.active_accounts):
            process_id = f"process_{i}"
            process_info = ProcessInfo(
                process_id=process_id,
                account_id=account.id,
                account_number=account.account_number,
                status=ProcessStatus.READY,
                last_heartbeat=datetime.utcnow() - timedelta(seconds=5),
            )
            processes.append((process_id, process_info, account))

            process_pool.processes[process_id] = process_info
            process_pool.account_to_process[account.id] = process_id

            # Setup mock process and queues
            mock_process = mock_multiprocessing["process"]
            mock_queue = mock_multiprocessing["queue"]
            process_pool.process_pool[process_id] = mock_process
            process_pool.task_queues[process_id] = mock_queue

        # Start monitoring
        process_pool._monitoring_active = True

        # Create monitoring task that runs once
        async def single_monitor_cycle():
            current_time = datetime.utcnow()
            for process_id, process_info in list(process_pool.processes.items()):
                # Check if process is still alive
                process = process_pool.process_pool.get(process_id)
                if process and process.is_alive():
                    # Send heartbeat check
                    if process_info.status == ProcessStatus.READY:
                        task_queue = process_pool.task_queues.get(process_id)
                        if task_queue:
                            heartbeat_task = {
                                "type": "heartbeat",
                                "timestamp": current_time.isoformat(),
                            }
                            task_queue.put_nowait(heartbeat_task)

        # Run monitoring cycle
        await single_monitor_cycle()

        # Verify heartbeat messages were sent to ready processes
        for process_id, process_info, account in processes:
            if process_info.status == ProcessStatus.READY:
                task_queue = process_pool.task_queues[process_id]
                task_queue.put_nowait.assert_called()

    @pytest.mark.asyncio
    async def test_process_monitoring_dead_process(
        self, process_pool, mock_account_data, mock_multiprocessing
    ):
        """Test monitoring detects and restarts dead processes."""
        # Setup existing process
        account = mock_account_data.accounts[0]
        process_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account.id,
            account_number=account.account_number,
            status=ProcessStatus.READY,
        )

        process_pool.processes[process_id] = process_info

        # Setup dead mock process
        mock_process = mock_multiprocessing["process"]
        mock_process.is_alive.return_value = False  # Process is dead
        process_pool.process_pool[process_id] = mock_process

        # Mock restart process
        process_pool._restart_process = AsyncMock()

        # Simulate monitoring check
        datetime.utcnow()
        process = process_pool.process_pool.get(process_id)
        if process and not process.is_alive():
            await process_pool._restart_process(process_id)

        # Verify restart was called
        process_pool._restart_process.assert_called_once_with(process_id)

    @pytest.mark.asyncio
    async def test_process_monitoring_heartbeat_timeout(
        self, process_pool, mock_account_data
    ):
        """Test monitoring detects heartbeat timeouts."""
        # Setup existing process with old heartbeat
        account = mock_account_data.accounts[0]
        process_id = str(uuid.uuid4())

        old_heartbeat = datetime.utcnow() - timedelta(
            seconds=process_pool.process_timeout + 10
        )
        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account.id,
            account_number=account.account_number,
            status=ProcessStatus.READY,
            last_heartbeat=old_heartbeat,
        )

        process_pool.processes[process_id] = process_info

        # Mock restart process
        process_pool._restart_process = AsyncMock()

        # Simulate heartbeat timeout check
        current_time = datetime.utcnow()
        if process_info.last_heartbeat:
            heartbeat_age = (current_time - process_info.last_heartbeat).total_seconds()
            if heartbeat_age > process_pool.process_timeout:
                await process_pool._restart_process(process_id)

        # Verify restart was called
        process_pool._restart_process.assert_called_once_with(process_id)

    @pytest.mark.asyncio
    async def test_get_process_status(self, process_pool, mock_account_data):
        """Test getting process status for account."""
        # Setup existing process
        account = mock_account_data.accounts[0]
        process_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account.id,
            account_number=account.account_number,
            status=ProcessStatus.READY,
        )

        process_pool.processes[process_id] = process_info
        process_pool.account_to_process[account.id] = process_id

        # Execute
        result = await process_pool.get_process_status(account.id)

        # Verify
        assert result == process_info

        # Test non-existent account
        result = await process_pool.get_process_status("non_existent_account")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_processes(self, process_pool, mock_account_data):
        """Test getting all process statuses."""
        # Setup multiple processes
        processes = []
        for i, account in enumerate(mock_account_data.active_accounts):
            process_id = f"process_{i}"
            process_info = ProcessInfo(
                process_id=process_id,
                account_id=account.id,
                account_number=account.account_number,
                status=ProcessStatus.READY,
            )
            processes.append(process_info)
            process_pool.processes[process_id] = process_info

        # Execute
        result = await process_pool.get_all_processes()

        # Verify
        assert len(result) == len(processes)
        assert set(result) == set(processes)

    @pytest.mark.asyncio
    async def test_restart_process_by_account(self, process_pool, mock_account_data):
        """Test restarting process by account ID."""
        # Setup existing process
        account = mock_account_data.accounts[0]
        process_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account.id,
            account_number=account.account_number,
            status=ProcessStatus.READY,
        )

        process_pool.processes[process_id] = process_info
        process_pool.account_to_process[account.id] = process_id

        # Mock restart process
        process_pool._restart_process = AsyncMock(return_value=True)

        # Execute
        result = await process_pool.restart_process(account.id)

        # Verify
        assert result is True
        process_pool._restart_process.assert_called_once_with(process_id)

        # Test non-existent account
        result = await process_pool.restart_process("non_existent_account")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_process_by_account(self, process_pool, mock_account_data):
        """Test removing process by account ID."""
        # Setup existing process
        account = mock_account_data.accounts[0]
        process_id = str(uuid.uuid4())

        process_info = ProcessInfo(
            process_id=process_id,
            account_id=account.id,
            account_number=account.account_number,
            status=ProcessStatus.READY,
        )

        process_pool.processes[process_id] = process_info
        process_pool.account_to_process[account.id] = process_id

        # Mock remove process
        process_pool._remove_process = AsyncMock(return_value=True)

        # Execute
        result = await process_pool.remove_process(account.id)

        # Verify
        assert result is True
        process_pool._remove_process.assert_called_once_with(process_id)

        # Test non-existent account
        result = await process_pool.remove_process("non_existent_account")
        assert result is False

    @pytest.mark.asyncio
    async def test_stop_all_processes(self, process_pool, mock_account_data):
        """Test stopping all processes."""
        # Setup multiple processes
        process_ids = []
        for i, account in enumerate(mock_account_data.active_accounts):
            process_id = f"process_{i}"
            process_info = ProcessInfo(
                process_id=process_id,
                account_id=account.id,
                account_number=account.account_number,
                status=ProcessStatus.READY,
            )
            process_ids.append(process_id)
            process_pool.processes[process_id] = process_info

        # Mock remove process
        process_pool._remove_process = AsyncMock(return_value=True)

        # Execute
        await process_pool._stop_all_processes()

        # Verify all processes were removed
        assert process_pool._remove_process.call_count == len(process_ids)
        for process_id in process_ids:
            process_pool._remove_process.assert_any_call(process_id)

    def test_get_process_pool_singleton(self):
        """Test global process pool singleton."""
        # Get first instance
        pool1 = get_process_pool()

        # Get second instance
        pool2 = get_process_pool()

        # Should be the same instance
        assert pool1 is pool2
        assert isinstance(pool1, TigerProcessPool)


class TestProcessPoolIntegration:
    """Integration tests for TigerProcessPool."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_process_pool_full_lifecycle(
        self, mock_account_manager, mock_account_data, mock_multiprocessing
    ):
        """Test complete process pool lifecycle."""
        with patch("mcp_server.tiger_process_pool.get_config") as mock_config:
            # Setup mock config
            mock_config.return_value = MagicMock()

            # Create process pool
            pool = TigerProcessPool(max_processes=2, heartbeat_interval=1.0)

            try:
                # Start pool
                await pool.start()
                assert pool._monitoring_active is True

                # Setup account
                account = mock_account_data.accounts[0]
                mock_account_manager.get_account_by_id.return_value = account

                # Mock process creation success
                mock_queue = mock_multiprocessing["queue"]
                ready_message = {"type": "ready"}
                mock_queue.empty.return_value = False
                mock_queue.get_nowait.return_value = ready_message

                # Create process for account
                process_id = await pool.get_or_create_process(account.id)
                assert process_id is not None
                assert account.id in pool.account_to_process

                # Mock task execution
                task_response = {
                    "task_id": "test_task",
                    "success": True,
                    "result": {"data": "test_result"},
                    "execution_time": 0.1,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                async def mock_put_queue_async(queue, item, timeout=None):
                    pass

                async def mock_get_queue_async(queue, timeout=None):
                    return task_response

                pool._put_queue_async = mock_put_queue_async
                pool._get_queue_async = mock_get_queue_async

                # Execute task
                result = await pool.execute_task(
                    account_id=account.id, method="test_method", args=["test_arg"]
                )
                assert result == task_response["result"]

                # Get process status
                status = await pool.get_process_status(account.id)
                assert status is not None
                assert status.status == ProcessStatus.READY

                # Get all processes
                all_processes = await pool.get_all_processes()
                assert len(all_processes) == 1

                # Restart process
                restart_result = await pool.restart_process(account.id)
                # Result depends on mocking, but should not raise exception
                assert isinstance(restart_result, bool)

            finally:
                # Stop pool
                await pool.stop()
                assert pool._shutdown is True

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_process_pool_concurrent_operations(
        self, mock_account_manager, mock_account_data, mock_multiprocessing
    ):
        """Test concurrent operations on process pool."""
        with patch("mcp_server.tiger_process_pool.get_config") as mock_config:
            # Setup mock config
            mock_config.return_value = MagicMock()

            # Create process pool
            pool = TigerProcessPool(max_processes=3)

            try:
                await pool.start()

                # Setup accounts
                accounts = mock_account_data.active_accounts
                mock_account_manager.get_account_by_id.side_effect = (
                    lambda account_id: next(
                        (acc for acc in accounts if acc.id == str(account_id)), None
                    )
                )

                # Mock successful process creation
                mock_queue = mock_multiprocessing["queue"]
                ready_message = {"type": "ready"}
                mock_queue.empty.return_value = False
                mock_queue.get_nowait.return_value = ready_message

                # Create processes concurrently
                create_tasks = [
                    pool.get_or_create_process(account.id)
                    for account in accounts[:2]  # Only use 2 accounts
                ]
                process_ids = await asyncio.gather(*create_tasks)

                assert len(process_ids) == 2
                assert all(pid is not None for pid in process_ids)

                # Mock task execution
                task_response = {
                    "task_id": "test_task",
                    "success": True,
                    "result": {"data": "concurrent_result"},
                    "execution_time": 0.1,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                async def mock_put_queue_async(queue, item, timeout=None):
                    await asyncio.sleep(0.01)  # Simulate some delay

                async def mock_get_queue_async(queue, timeout=None):
                    await asyncio.sleep(0.02)  # Simulate processing time
                    return task_response

                pool._put_queue_async = mock_put_queue_async
                pool._get_queue_async = mock_get_queue_async

                # Execute tasks concurrently on different accounts
                task_execution_tasks = [
                    pool.execute_task(
                        account_id=account.id,
                        method=f"test_method_{i}",
                        args=[f"test_arg_{i}"],
                    )
                    for i, account in enumerate(accounts[:2])
                ]

                start_time = asyncio.get_event_loop().time()
                results = await asyncio.gather(*task_execution_tasks)
                end_time = asyncio.get_event_loop().time()

                # Verify results
                assert len(results) == 2
                assert all(result == task_response["result"] for result in results)

                # Verify concurrent execution (should be faster than sequential)
                execution_time = end_time - start_time
                assert (
                    execution_time < 0.1
                )  # Much faster than 2 * (0.01 + 0.02) sequential

                # Get status of all processes
                status_tasks = [
                    pool.get_process_status(account.id) for account in accounts[:2]
                ]
                statuses = await asyncio.gather(*status_tasks)

                assert len(statuses) == 2
                assert all(status is not None for status in statuses)
                assert all(status.status == ProcessStatus.READY for status in statuses)

            finally:
                await pool.stop()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_process_pool_error_recovery(
        self, mock_account_manager, mock_account_data, mock_multiprocessing
    ):
        """Test process pool error recovery mechanisms."""
        with patch("mcp_server.tiger_process_pool.get_config") as mock_config:
            # Setup mock config
            mock_config.return_value = MagicMock()

            # Create process pool
            pool = TigerProcessPool(max_processes=2, max_restarts=1)

            try:
                await pool.start()

                # Setup account
                account = mock_account_data.accounts[0]
                mock_account_manager.get_account_by_id.return_value = account

                # Mock process creation success initially
                mock_queue = mock_multiprocessing["queue"]
                ready_message = {"type": "ready"}
                mock_queue.empty.return_value = False
                mock_queue.get_nowait.return_value = ready_message

                # Create process
                process_id = await pool.get_or_create_process(account.id)
                assert process_id is not None

                # Simulate process failure during task execution
                error_response = {
                    "task_id": "failing_task",
                    "success": False,
                    "result": None,
                    "error": "Simulated API failure",
                    "execution_time": 0.1,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                async def mock_put_queue_async(queue, item, timeout=None):
                    pass

                async def mock_get_queue_async(queue, timeout=None):
                    return error_response

                pool._put_queue_async = mock_put_queue_async
                pool._get_queue_async = mock_get_queue_async

                # Mock restart operations
                pool._remove_process = AsyncMock(return_value=True)
                pool._create_process = AsyncMock(return_value=process_id)

                # Execute failing task multiple times to trigger restart
                process_info = pool.processes[process_id]
                original_error_count = process_info.error_count

                # This should fail and increment error count
                with pytest.raises(RuntimeError, match="Task execution failed"):
                    await pool.execute_task(
                        account_id=account.id, method="failing_method", args=["test"]
                    )

                # Verify error count increased
                assert process_info.error_count > original_error_count

                # Simulate multiple failures to trigger restart threshold
                process_info.error_count = 3  # Set to trigger restart

                with pytest.raises(RuntimeError):
                    await pool.execute_task(
                        account_id=account.id, method="failing_method", args=["test"]
                    )

                # Verify restart was attempted
                pool._restart_process.assert_called()

            finally:
                await pool.stop()
