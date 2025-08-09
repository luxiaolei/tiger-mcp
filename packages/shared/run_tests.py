#!/usr/bin/env python3
"""
Test runner script for shared package.

Runs comprehensive unit tests with coverage reporting and validates
that all modules achieve the required 90%+ coverage threshold.
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Run tests with comprehensive coverage reporting."""
    # Change to shared package directory
    shared_dir = Path(__file__).parent
    os.chdir(shared_dir)

    print("🧪 Running comprehensive unit tests for shared package...")
    print(f"📁 Working directory: {shared_dir}")
    print("=" * 60)

    # Check if pytest is available
    try:
        subprocess.run(
            ["python", "-m", "pytest", "--version"], check=True, capture_output=True
        )
    except subprocess.CalledProcessError:
        print("❌ pytest not found. Please install pytest and pytest-cov:")
        print("   pip install pytest pytest-cov pytest-asyncio")
        return 1

    # Run tests with coverage
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/",
        "--cov=src/shared",
        "--cov-report=html:htmlcov",
        "--cov-report=term-missing",
        "--cov-report=xml:coverage.xml",
        "--cov-fail-under=90",
        "-v",
        "--tb=short",
    ]

    try:
        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("✅ All tests passed with 90%+ coverage!")
            print("📊 Coverage reports generated:")
            print(f"   - HTML: {shared_dir}/htmlcov/index.html")
            print(f"   - XML:  {shared_dir}/coverage.xml")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("❌ Tests failed or coverage below 90%")
            print("📋 Check the output above for details")
            print("=" * 60)
            return result.returncode

    except KeyboardInterrupt:
        print("\n⚠️  Test run interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
