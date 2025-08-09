#!/usr/bin/env python3
"""
Integration test runner for Tiger MCP multi-account workflows.

Provides comprehensive test execution with proper setup, teardown,
and reporting for database, process pool, and MCP server integration tests.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

import psutil
from loguru import logger

import docker

# Test configuration
TEST_CONFIG = {
    "postgres_port": 15432,
    "redis_port": 16379,
    "test_db_name": "tiger_mcp_test",
    "test_user": "tiger_test",
    "test_password": "tiger_test",
    "docker_network": "tiger-mcp-test-network",
}


class IntegrationTestRunner:
    """Integration test runner with Docker container management."""

    def __init__(self, config: Dict):
        self.config = config
        self.docker_client = None
        self.containers = {}
        self.setup_logging()

    def setup_logging(self):
        """Set up logging configuration."""
        logger.remove()  # Remove default handler

        # Console logging
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
            level="INFO",
        )

        # File logging
        log_file = Path(__file__).parent / "test_results" / "integration_tests.log"
        log_file.parent.mkdir(exist_ok=True)

        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
        )

    def check_prerequisites(self):
        """Check system prerequisites for running integration tests."""
        logger.info("Checking prerequisites...")

        # Check Docker
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("✓ Docker is available")
        except Exception as e:
            logger.error(f"✗ Docker is not available: {e}")
            return False

        # Check available ports
        for service, port in [
            ("PostgreSQL", self.config["postgres_port"]),
            ("Redis", self.config["redis_port"]),
        ]:
            if self.is_port_in_use(port):
                logger.warning(f"Port {port} is already in use (for {service})")

        # Check system resources
        memory = psutil.virtual_memory()
        if memory.available < 2 * 1024 * 1024 * 1024:  # 2GB
            logger.warning("Less than 2GB of available memory - tests may be slow")

        logger.info("Prerequisites check completed")
        return True

    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0

    def start_infrastructure(self):
        """Start required infrastructure containers."""
        logger.info("Starting infrastructure containers...")

        # Start PostgreSQL
        logger.info("Starting PostgreSQL container...")
        postgres_container = self.docker_client.containers.run(
            "postgres:15-alpine",
            name="tiger-mcp-postgres-test",
            environment={
                "POSTGRES_DB": self.config["test_db_name"],
                "POSTGRES_USER": self.config["test_user"],
                "POSTGRES_PASSWORD": self.config["test_password"],
                "POSTGRES_INITDB_ARGS": "--auth-host=scram-sha-256",
            },
            ports={"5432/tcp": self.config["postgres_port"]},
            detach=True,
            remove=True,
            network_mode="bridge",
        )
        self.containers["postgres"] = postgres_container

        # Start Redis
        logger.info("Starting Redis container...")
        redis_container = self.docker_client.containers.run(
            "redis:7-alpine",
            name="tiger-mcp-redis-test",
            command="redis-server --appendonly yes",
            ports={"6379/tcp": self.config["redis_port"]},
            detach=True,
            remove=True,
            network_mode="bridge",
        )
        self.containers["redis"] = redis_container

        # Wait for containers to be healthy
        self.wait_for_infrastructure()

    def wait_for_infrastructure(self, timeout: int = 60):
        """Wait for infrastructure containers to be ready."""
        logger.info("Waiting for infrastructure to be ready...")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Check PostgreSQL
                postgres_ready = self.check_postgres_health()
                redis_ready = self.check_redis_health()

                if postgres_ready and redis_ready:
                    logger.info("✓ All infrastructure containers are ready")
                    return True

                logger.info("Waiting for containers to be ready...")
                time.sleep(2)

            except Exception as e:
                logger.debug(f"Health check error (expected during startup): {e}")
                time.sleep(2)

        logger.error("Timeout waiting for infrastructure")
        return False

    def check_postgres_health(self) -> bool:
        """Check PostgreSQL container health."""
        try:
            result = subprocess.run(
                [
                    "pg_isready",
                    "-h",
                    "localhost",
                    "-p",
                    str(self.config["postgres_port"]),
                    "-U",
                    self.config["test_user"],
                    "-d",
                    self.config["test_db_name"],
                ],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def check_redis_health(self) -> bool:
        """Check Redis container health."""
        try:
            result = subprocess.run(
                [
                    "redis-cli",
                    "-h",
                    "localhost",
                    "-p",
                    str(self.config["redis_port"]),
                    "ping",
                ],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0 and b"PONG" in result.stdout
        except Exception:
            return False

    def setup_test_database(self):
        """Set up test database schema."""
        logger.info("Setting up test database schema...")

        # Set environment variables for database setup
        env = os.environ.copy()
        env.update(
            {
                "DATABASE_URL": f"postgresql+asyncpg://{self.config['test_user']}:{self.config['test_password']}@localhost:{self.config['postgres_port']}/{self.config['test_db_name']}",
                "PYTHONPATH": str(Path(__file__).parent.parent.parent / "src"),
            }
        )

        # Run database setup script
        setup_script = Path(__file__).parent / "setup_test_db.py"
        if setup_script.exists():
            result = subprocess.run(
                [sys.executable, str(setup_script)],
                env=env,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"Database setup failed: {result.stderr}")
                return False

        logger.info("✓ Test database schema created")
        return True

    def run_tests(self, test_args: List[str]) -> bool:
        """Run the integration tests."""
        logger.info("Running integration tests...")

        # Set up test environment
        env = os.environ.copy()
        env.update(
            {
                "DATABASE_URL": f"postgresql+asyncpg://{self.config['test_user']}:{self.config['test_password']}@localhost:{self.config['postgres_port']}/{self.config['test_db_name']}",
                "REDIS_URL": f"redis://localhost:{self.config['redis_port']}/15",
                "ENVIRONMENT": "test",
                "ENCRYPTION_MASTER_KEY": "dGVzdF9lbmNyeXB0aW9uX2tleV8zMl9ieXRlc190ZXN0",
                "JWT_SECRET": "test_jwt_secret_integration_tests_very_secure",
                "TIGER_MOCK_MODE": "true",
                "PYTHONPATH": str(Path(__file__).parent.parent.parent / "src"),
            }
        )

        # Build pytest command
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(Path(__file__).parent),
            "-v",
            "--tb=short",
            "--strict-markers",
            "--strict-config",
        ] + test_args

        logger.info(f"Running command: {' '.join(cmd)}")

        # Run tests
        start_time = time.time()
        result = subprocess.run(cmd, env=env)
        duration = time.time() - start_time

        if result.returncode == 0:
            logger.info(f"✓ All tests passed in {duration:.2f}s")
            return True
        else:
            logger.error(f"✗ Tests failed after {duration:.2f}s")
            return False

    def cleanup(self):
        """Clean up containers and resources."""
        logger.info("Cleaning up infrastructure...")

        for name, container in self.containers.items():
            try:
                logger.info(f"Stopping {name} container...")
                container.stop()
                container.wait(timeout=10)
                logger.info(f"✓ {name} container stopped")
            except Exception as e:
                logger.warning(f"Error stopping {name} container: {e}")

        logger.info("Cleanup completed")

    def run(self, test_args: List[str]) -> bool:
        """Run the complete integration test suite."""
        success = True

        try:
            # Check prerequisites
            if not self.check_prerequisites():
                return False

            # Start infrastructure
            self.start_infrastructure()

            # Setup database
            if not self.setup_test_database():
                return False

            # Run tests
            success = self.run_tests(test_args)

        except KeyboardInterrupt:
            logger.info("Test run interrupted by user")
            success = False
        except Exception as e:
            logger.error(f"Test run failed with error: {e}")
            success = False
        finally:
            # Always cleanup
            self.cleanup()

        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Integration test runner for Tiger MCP multi-account workflows"
    )

    parser.add_argument(
        "--test-pattern", "-k", help="Only run tests matching this pattern"
    )

    parser.add_argument("--test-file", "-f", help="Only run tests from this file")

    parser.add_argument(
        "--parallel", "-n", type=int, default=4, help="Number of parallel test workers"
    )

    parser.add_argument(
        "--coverage", action="store_true", help="Run with coverage reporting"
    )

    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run performance tests (longer duration)",
    )

    parser.add_argument(
        "--load-test", action="store_true", help="Run load tests (high resource usage)"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Build pytest arguments
    test_args = []

    if args.test_pattern:
        test_args.extend(["-k", args.test_pattern])

    if args.test_file:
        test_args.append(args.test_file)

    if args.parallel > 1:
        test_args.extend(["-n", str(args.parallel)])

    if args.coverage:
        test_args.extend(
            [
                "--cov=shared",
                "--cov-report=xml:test_results/coverage.xml",
                "--cov-report=html:test_results/coverage_html",
                "--cov-report=term",
            ]
        )

    if args.performance:
        test_args.extend(["-m", "performance"])

    if args.load_test:
        test_args.extend(["-m", "load_test"])

    if args.verbose:
        test_args.append("-vv")

    # Add JUnit XML output
    test_args.extend(["--junit-xml=test_results/integration-results.xml"])

    # Create test runner and run tests
    runner = IntegrationTestRunner(TEST_CONFIG)
    success = runner.run(test_args)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
