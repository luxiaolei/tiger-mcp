"""
Integration tests for process pool operations with real multiprocessing.

Tests concurrent processing, task distribution, error handling, and
resource management across multiple processes.
"""

import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Dict

import pytest
from shared.account_router import OperationType


# Worker functions for process pool testing
def cpu_intensive_task(task_id: int, duration: float = 1.0) -> Dict[str, Any]:
    """CPU-intensive task for testing process pool."""
    start_time = time.time()

    # Simulate CPU-intensive work
    result = 0
    iterations = int(duration * 1000000)  # Scale iterations based on duration

    for i in range(iterations):
        result += i**0.5

    end_time = time.time()

    return {
        "task_id": task_id,
        "result": result,
        "duration": end_time - start_time,
        "process_id": mp.current_process().pid,
        "process_name": mp.current_process().name,
    }


def io_simulation_task(task_id: int, io_duration: float = 0.5) -> Dict[str, Any]:
    """I/O simulation task for testing."""
    start_time = time.time()

    # Simulate I/O wait
    time.sleep(io_duration)

    end_time = time.time()

    return {
        "task_id": task_id,
        "duration": end_time - start_time,
        "process_id": mp.current_process().pid,
        "simulated_data": f"data_from_task_{task_id}",
    }


def account_validation_task(account_data: Dict[str, Any]) -> Dict[str, Any]:
    """Account validation task for multiprocessing."""
    start_time = time.time()

    # Simulate account validation logic
    account_id = account_data.get("account_id", "unknown")
    tiger_id = account_data.get("tiger_id", "")
    private_key = account_data.get("private_key", "")

    # Basic validation
    is_valid = len(tiger_id) > 10 and len(private_key) > 20

    # Simulate some processing time
    time.sleep(0.1)

    end_time = time.time()

    return {
        "account_id": account_id,
        "is_valid": is_valid,
        "validation_time": end_time - start_time,
        "process_id": mp.current_process().pid,
        "validated_at": time.time(),
    }


def market_data_processing_task(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Market data processing task."""
    start_time = time.time()

    symbol = market_data.get("symbol", "UNKNOWN")
    price = market_data.get("latest_price", 0.0)
    volume = market_data.get("volume", 0)

    # Simulate technical analysis calculations
    sma_5 = price * 0.98  # Simplified moving average
    rsi = 50.0 + (hash(symbol) % 50)  # Mock RSI calculation

    # Calculate volatility estimate
    volatility = abs(hash(symbol + str(price)) % 100) / 1000.0

    end_time = time.time()

    return {
        "symbol": symbol,
        "processed_price": price,
        "sma_5": sma_5,
        "rsi": rsi,
        "volatility": volatility,
        "volume": volume,
        "processing_time": end_time - start_time,
        "process_id": mp.current_process().pid,
    }


def error_prone_task(task_id: int, error_probability: float = 0.2) -> Dict[str, Any]:
    """Task that may fail to test error handling."""
    import random

    if random.random() < error_probability:
        raise ValueError(f"Simulated error in task {task_id}")

    # Simulate some work
    time.sleep(0.1)

    return {"task_id": task_id, "success": True, "process_id": mp.current_process().pid}


class TestBasicProcessPoolOperations:
    """Test basic process pool functionality."""

    def test_process_pool_creation_and_cleanup(self, process_pool):
        """Test process pool creation and proper cleanup."""
        # Verify process pool is created
        assert process_pool is not None
        assert hasattr(process_pool, "submit")

        # Submit a simple task
        future = process_pool.submit(cpu_intensive_task, 1, 0.1)
        result = future.result(timeout=5.0)

        # Verify task executed
        assert result["task_id"] == 1
        assert result["process_id"] is not None
        assert result["duration"] > 0

    def test_multiple_concurrent_tasks(self, process_pool):
        """Test multiple concurrent tasks in process pool."""
        num_tasks = 8

        # Submit multiple tasks
        futures = []
        for i in range(num_tasks):
            future = process_pool.submit(cpu_intensive_task, i, 0.2)
            futures.append(future)

        # Collect results
        results = []
        for future in as_completed(futures, timeout=10.0):
            result = future.result()
            results.append(result)

        # Verify all tasks completed
        assert len(results) == num_tasks

        # Verify tasks ran on different processes
        process_ids = {result["process_id"] for result in results}
        assert len(process_ids) > 1, "Tasks should run on multiple processes"

        # Verify task IDs are correct
        task_ids = {result["task_id"] for result in results}
        assert task_ids == set(range(num_tasks))

    def test_process_pool_with_io_tasks(self, process_pool):
        """Test process pool with I/O simulation tasks."""
        num_tasks = 6
        io_duration = 0.3

        start_time = time.time()

        # Submit I/O tasks
        futures = [
            process_pool.submit(io_simulation_task, i, io_duration)
            for i in range(num_tasks)
        ]

        # Wait for completion
        results = [future.result(timeout=5.0) for future in futures]

        total_time = time.time() - start_time

        # Verify results
        assert len(results) == num_tasks

        # With multiprocessing, total time should be less than sequential
        sequential_time = num_tasks * io_duration
        assert (
            total_time < sequential_time * 0.8
        ), "Multiprocessing should provide speedup"

        # Verify all tasks completed
        for result in results:
            assert result["duration"] >= io_duration * 0.9  # Allow some variance
            assert "simulated_data" in result


class TestAccountValidationWithProcessPool:
    """Test account validation operations using process pool."""

    def test_parallel_account_validation(self, process_pool, tiger_api_configs):
        """Test parallel validation of multiple accounts."""
        # Prepare account data for validation
        account_data_list = []
        for i, (name, config) in enumerate(tiger_api_configs.items()):
            account_data_list.append(
                {
                    "account_id": f"test_account_{i}",
                    "tiger_id": config["tiger_id"],
                    "private_key": config["private_key"],
                    "environment": config["environment"],
                }
            )

        # Submit validation tasks
        futures = [
            process_pool.submit(account_validation_task, account_data)
            for account_data in account_data_list
        ]

        # Collect results
        results = [future.result(timeout=10.0) for future in futures]

        # Verify validation results
        assert len(results) == len(account_data_list)

        for result in results:
            assert "account_id" in result
            assert "is_valid" in result
            assert "validation_time" in result
            assert result["validation_time"] > 0

            # Our test data should be valid
            assert result["is_valid"] is True

        # Verify parallel execution
        process_ids = {result["process_id"] for result in results}
        assert len(process_ids) > 1, "Validation should run on multiple processes"

    def test_account_validation_with_errors(self, process_pool):
        """Test account validation with invalid data."""
        # Prepare invalid account data
        invalid_accounts = [
            {"account_id": "invalid_1", "tiger_id": "short", "private_key": "short"},
            {"account_id": "invalid_2", "tiger_id": "", "private_key": ""},
            {
                "account_id": "invalid_3",
                "tiger_id": "valid_tiger_id",
                "private_key": "short",
            },
        ]

        # Submit validation tasks
        futures = [
            process_pool.submit(account_validation_task, account_data)
            for account_data in invalid_accounts
        ]

        # Collect results
        results = [future.result(timeout=5.0) for future in futures]

        # Verify all validation results are invalid
        for result in results:
            assert result["is_valid"] is False


class TestMarketDataProcessingWithProcessPool:
    """Test market data processing using process pool."""

    def test_parallel_market_data_processing(self, process_pool, sample_market_data):
        """Test parallel processing of market data."""
        # Submit processing tasks for each symbol
        futures = [
            process_pool.submit(market_data_processing_task, data)
            for data in sample_market_data.values()
        ]

        # Collect results
        results = [future.result(timeout=10.0) for future in futures]

        # Verify processing results
        assert len(results) == len(sample_market_data)

        for result in results:
            assert "symbol" in result
            assert "processed_price" in result
            assert "sma_5" in result
            assert "rsi" in result
            assert "volatility" in result
            assert result["processing_time"] > 0

            # Verify calculated values are reasonable
            assert 0 <= result["rsi"] <= 100
            assert result["volatility"] >= 0
            assert result["sma_5"] > 0

        # Verify symbols match
        processed_symbols = {result["symbol"] for result in results}
        expected_symbols = set(sample_market_data.keys())
        assert processed_symbols == expected_symbols

    def test_large_scale_market_data_processing(self, process_pool):
        """Test processing large amounts of market data."""
        # Generate large dataset
        large_dataset = []
        symbols = [f"STOCK{i:04d}" for i in range(100)]

        for symbol in symbols:
            large_dataset.append(
                {
                    "symbol": symbol,
                    "latest_price": 100.0 + (hash(symbol) % 1000) / 10.0,
                    "volume": hash(symbol) % 10000000,
                    "timestamp": time.time(),
                }
            )

        start_time = time.time()

        # Process data in parallel
        futures = [
            process_pool.submit(market_data_processing_task, data)
            for data in large_dataset
        ]

        # Collect results
        results = []
        for future in as_completed(futures, timeout=30.0):
            result = future.result()
            results.append(result)

        processing_time = time.time() - start_time

        # Verify results
        assert len(results) == len(large_dataset)

        # Performance check
        assert (
            processing_time < 20.0
        ), f"Large scale processing took too long: {processing_time}s"

        # Verify all symbols processed
        processed_symbols = {result["symbol"] for result in results}
        expected_symbols = {data["symbol"] for data in large_dataset}
        assert processed_symbols == expected_symbols


class TestErrorHandlingInProcessPool:
    """Test error handling and fault tolerance in process pool."""

    def test_task_error_handling(self, process_pool):
        """Test handling of task errors in process pool."""
        num_tasks = 10
        error_probability = 0.3

        # Submit tasks that may fail
        futures = [
            process_pool.submit(error_prone_task, i, error_probability)
            for i in range(num_tasks)
        ]

        # Collect results and errors
        successful_results = []
        failed_tasks = []

        for i, future in enumerate(futures):
            try:
                result = future.result(timeout=5.0)
                successful_results.append(result)
            except Exception as e:
                failed_tasks.append((i, str(e)))

        # Verify some tasks succeeded and some failed
        assert len(successful_results) > 0, "Some tasks should succeed"
        assert (
            len(failed_tasks) > 0
        ), "Some tasks should fail with error_probability > 0"

        # Verify total tasks
        assert len(successful_results) + len(failed_tasks) == num_tasks

        # Verify successful results are correct
        for result in successful_results:
            assert result["success"] is True
            assert "process_id" in result

    def test_process_pool_resilience(self, process_pool):
        """Test process pool resilience to worker failures."""
        # Submit a mix of good and bad tasks
        good_tasks = [process_pool.submit(cpu_intensive_task, i, 0.1) for i in range(5)]
        bad_tasks = [
            process_pool.submit(error_prone_task, i, 1.0) for i in range(3)
        ]  # 100% error rate
        more_good_tasks = [
            process_pool.submit(cpu_intensive_task, i + 10, 0.1) for i in range(5)
        ]

        # Process good tasks (should all succeed)
        good_results = []
        for future in good_tasks:
            result = future.result(timeout=5.0)
            good_results.append(result)

        # Process bad tasks (should all fail)
        bad_results = []
        for future in bad_tasks:
            try:
                result = future.result(timeout=5.0)
                bad_results.append(result)
            except Exception:
                pass  # Expected failures

        # Process more good tasks (should succeed after errors)
        more_good_results = []
        for future in more_good_tasks:
            result = future.result(timeout=5.0)
            more_good_results.append(result)

        # Verify process pool recovered from errors
        assert len(good_results) == 5
        assert len(more_good_results) == 5
        assert len(bad_results) == 0  # All bad tasks should have failed

    def test_timeout_handling(self, process_pool):
        """Test timeout handling for long-running tasks."""
        # Submit a long-running task
        long_task = process_pool.submit(cpu_intensive_task, 1, 5.0)  # 5 second task

        # Try to get result with short timeout
        with pytest.raises(Exception):  # Should timeout
            long_task.result(timeout=1.0)

        # Cancel the task
        cancelled = long_task.cancel()

        # If cancellation failed, wait for completion with longer timeout
        if not cancelled:
            result = long_task.result(timeout=10.0)
            assert result["task_id"] == 1


class TestProcessPoolResourceManagement:
    """Test resource management and optimization in process pool."""

    def test_process_pool_resource_utilization(self, process_pool):
        """Test process pool resource utilization."""
        # Get system CPU count
        cpu_count = mp.cpu_count()

        # Submit tasks equal to 2x CPU count
        num_tasks = cpu_count * 2
        futures = [
            process_pool.submit(cpu_intensive_task, i, 0.5) for i in range(num_tasks)
        ]

        start_time = time.time()
        results = [future.result(timeout=30.0) for future in futures]
        total_time = time.time() - start_time

        # Verify all tasks completed
        assert len(results) == num_tasks

        # Check resource utilization
        process_ids = {result["process_id"] for result in results}

        # Should use multiple processes (up to pool limit)
        assert len(process_ids) > 1
        assert len(process_ids) <= cpu_count + 2  # Allow some flexibility

        # Performance should benefit from parallelization
        sequential_time = sum(result["duration"] for result in results)
        efficiency = sequential_time / total_time

        assert efficiency > 1.5, f"Parallelization efficiency too low: {efficiency}"

    def test_memory_usage_monitoring(self, process_pool):
        """Test memory usage in process pool operations."""
        import os

        import psutil

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Submit memory-intensive tasks
        large_data = list(range(100000))  # Large data structure

        def memory_intensive_task(data, task_id):
            """Task that uses memory."""
            # Process the data
            processed = [x * 2 for x in data]
            return {
                "task_id": task_id,
                "processed_count": len(processed),
                "sum": sum(processed[:1000]),  # Sample sum
            }

        futures = [
            process_pool.submit(memory_intensive_task, large_data, i) for i in range(5)
        ]

        results = [future.result(timeout=10.0) for future in futures]

        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Verify tasks completed
        assert len(results) == 5
        for result in results:
            assert result["processed_count"] == len(large_data)

        # Memory increase should be reasonable (less than 100MB)
        assert (
            memory_increase < 100 * 1024 * 1024
        ), f"Memory usage increased too much: {memory_increase} bytes"

    def test_process_pool_scaling(self):
        """Test process pool scaling with different worker counts."""
        test_results = {}

        # Test different pool sizes
        for pool_size in [1, 2, 4]:
            with ProcessPoolExecutor(max_workers=pool_size) as pool:
                start_time = time.time()

                # Submit CPU-intensive tasks
                num_tasks = 8
                futures = [
                    pool.submit(cpu_intensive_task, i, 0.5) for i in range(num_tasks)
                ]

                results = [future.result(timeout=30.0) for future in futures]
                total_time = time.time() - start_time

                test_results[pool_size] = {
                    "total_time": total_time,
                    "num_results": len(results),
                }

        # Verify scaling improves performance
        assert test_results[1]["total_time"] > test_results[2]["total_time"]

        # 4 workers should be faster than 2 workers for 8 CPU-intensive tasks
        if mp.cpu_count() >= 4:
            assert test_results[2]["total_time"] > test_results[4]["total_time"]


class TestIntegrationWithTigerMCPSystem:
    """Test integration of process pool with Tiger MCP system components."""

    @pytest.mark.asyncio
    async def test_account_routing_with_process_pool(
        self, multiple_tiger_accounts, account_router, process_pool
    ):
        """Test account routing operations using process pool."""

        def route_operation_task(operation_data):
            """Task to route operations (simplified for testing)."""
            operation_type = operation_data["operation_type"]
            account_id = operation_data["account_id"]

            # Simulate routing logic
            time.sleep(0.1)  # Simulate processing time

            return {
                "operation_type": operation_type,
                "routed_account_id": account_id,
                "routing_time": 0.1,
                "success": True,
                "process_id": mp.current_process().pid,
            }

        # Prepare routing operations
        operations = []
        for i, (name, account) in enumerate(multiple_tiger_accounts.items()):
            operations.append(
                {
                    "operation_id": i,
                    "operation_type": OperationType.MARKET_DATA.value,
                    "account_id": str(account.id),
                }
            )

        # Submit routing tasks
        futures = [process_pool.submit(route_operation_task, op) for op in operations]

        # Collect results
        results = [future.result(timeout=10.0) for future in futures]

        # Verify routing results
        assert len(results) == len(operations)
        for result in results:
            assert result["success"] is True
            assert "routed_account_id" in result
            assert result["routing_time"] > 0

    def test_concurrent_token_refresh_with_process_pool(
        self, process_pool, tiger_api_configs
    ):
        """Test concurrent token refresh operations using process pool."""

        def token_refresh_task(account_data):
            """Simulate token refresh operation."""
            account_id = account_data["account_id"]

            # Simulate token refresh API call
            time.sleep(0.2)  # Simulate network delay

            # Mock successful refresh
            return {
                "account_id": account_id,
                "access_token": f"new_token_{account_id}_{time.time()}",
                "refresh_token": f"refresh_token_{account_id}_{time.time()}",
                "expires_in": 3600,
                "refresh_time": 0.2,
                "success": True,
                "process_id": mp.current_process().pid,
            }

        # Prepare account data
        account_data_list = [
            {"account_id": f"account_{i}", "tiger_id": config["tiger_id"]}
            for i, config in enumerate(tiger_api_configs.values())
        ]

        start_time = time.time()

        # Submit token refresh tasks
        futures = [
            process_pool.submit(token_refresh_task, account_data)
            for account_data in account_data_list
        ]

        # Collect results
        results = [future.result(timeout=10.0) for future in futures]

        total_time = time.time() - start_time

        # Verify results
        assert len(results) == len(account_data_list)

        for result in results:
            assert result["success"] is True
            assert "access_token" in result
            assert "refresh_token" in result
            assert result["expires_in"] > 0

        # Verify parallel execution benefit
        sequential_time = len(account_data_list) * 0.2  # 0.2s per task
        assert (
            total_time < sequential_time * 0.8
        ), "Parallel processing should provide speedup"

    def test_batch_market_data_processing_integration(
        self, process_pool, sample_market_data
    ):
        """Test batch market data processing integration."""

        def batch_processing_task(data_batch):
            """Process a batch of market data."""
            results = []

            for symbol, data in data_batch.items():
                # Simulate processing
                processed = market_data_processing_task(data)
                results.append(processed)

            return {
                "batch_size": len(data_batch),
                "processed_symbols": [r["symbol"] for r in results],
                "processing_results": results,
                "batch_processing_time": sum(r["processing_time"] for r in results),
                "process_id": mp.current_process().pid,
            }

        # Split market data into batches
        items = list(sample_market_data.items())
        batch_size = 2
        batches = [
            dict(items[i : i + batch_size]) for i in range(0, len(items), batch_size)
        ]

        # Submit batch processing tasks
        futures = [
            process_pool.submit(batch_processing_task, batch) for batch in batches
        ]

        # Collect results
        batch_results = [future.result(timeout=10.0) for future in futures]

        # Verify batch processing
        total_processed = sum(result["batch_size"] for result in batch_results)
        assert total_processed == len(sample_market_data)

        # Verify all symbols were processed
        all_processed_symbols = []
        for result in batch_results:
            all_processed_symbols.extend(result["processed_symbols"])

        assert set(all_processed_symbols) == set(sample_market_data.keys())
