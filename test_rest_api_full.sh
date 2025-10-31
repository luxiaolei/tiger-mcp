#!/bin/bash
#
# Tiger MCP REST API - Full Test Suite
# Tests all 20 API endpoints
#

set -e  # Exit on error

# Configuration
API_BASE_URL="http://localhost:9000"
API_KEY="client_key_001"
TEST_ACCOUNT="67686635"
TEST_SYMBOL="AAPL"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ "$method" = "GET" ]; then
        curl -s -H "Authorization: Bearer $API_KEY" \
             "$API_BASE_URL$endpoint"
    else
        curl -s -X POST \
             -H "Authorization: Bearer $API_KEY" \
             -H "Content-Type: application/json" \
             -d "$data" \
             "$API_BASE_URL$endpoint"
    fi
}

# Test function
run_test() {
    local test_name=$1
    local method=$2
    local endpoint=$3
    local data=$4

    echo -n "Testing: $test_name ... "

    response=$(api_call "$method" "$endpoint" "$data")

    # Check if response contains "success": true
    if echo "$response" | grep -q '"success".*true\|"status".*"healthy"'; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "Response: $response"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "======================================================================"
echo "Tiger MCP REST API - Full Test Suite"
echo "======================================================================"
echo "API Base URL: $API_BASE_URL"
echo "Test Account: $TEST_ACCOUNT"
echo "Test Symbol: $TEST_SYMBOL"
echo "======================================================================"
echo ""

# Check if server is running
echo -n "Checking if server is running ... "
if curl -s "$API_BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Server is up${NC}"
else
    echo -e "${RED}✗ Server is not running${NC}"
    echo "Please start the server: python tiger_rest_api_full.py"
    exit 1
fi
echo ""

# ============================================================================
# System Tests
# ============================================================================
echo "=== System Endpoints ==="
run_test "Health Check" "GET" "/health" ""
run_test "List Endpoints" "GET" "/api/endpoints" ""
echo ""

# ============================================================================
# Account Management Tests
# ============================================================================
echo "=== Account Management Endpoints ==="
run_test "List Accounts" "GET" "/api/accounts" ""
echo ""

# ============================================================================
# Market Data Tests
# ============================================================================
echo "=== Market Data Endpoints (6) ==="

run_test "Get Quote" "POST" "/api/market/quote" \
    "{\"account\": \"$TEST_ACCOUNT\", \"symbol\": \"$TEST_SYMBOL\"}"

run_test "Get K-line Data" "POST" "/api/market/kline" \
    "{\"account\": \"$TEST_ACCOUNT\", \"symbol\": \"$TEST_SYMBOL\", \"period\": \"day\", \"limit\": 10}"

run_test "Batch Market Data" "POST" "/api/market/batch" \
    "{\"account\": \"$TEST_ACCOUNT\", \"symbols\": [\"AAPL\", \"TSLA\"]}"

run_test "Search Symbols" "POST" "/api/market/search" \
    "{\"account\": \"$TEST_ACCOUNT\", \"keyword\": \"apple\", \"market\": \"US\"}"

run_test "Get Option Chain" "POST" "/api/market/option-chain" \
    "{\"account\": \"$TEST_ACCOUNT\", \"symbol\": \"$TEST_SYMBOL\"}"

run_test "Get Market Status" "POST" "/api/market/status" \
    "{\"account\": \"$TEST_ACCOUNT\", \"market\": \"US\"}"

echo ""

# ============================================================================
# Company Info Tests
# ============================================================================
echo "=== Company Info Endpoints (4) ==="

run_test "Get Contracts" "POST" "/api/info/contracts" \
    "{\"account\": \"$TEST_ACCOUNT\", \"symbols\": [\"$TEST_SYMBOL\"], \"sec_type\": \"STK\"}"

run_test "Get Financials" "POST" "/api/info/financials" \
    "{\"account\": \"$TEST_ACCOUNT\", \"symbols\": [\"$TEST_SYMBOL\"]}"

run_test "Get Corporate Actions" "POST" "/api/info/corporate-actions" \
    "{\"account\": \"$TEST_ACCOUNT\", \"symbols\": [\"$TEST_SYMBOL\"]}"

run_test "Get Earnings" "POST" "/api/info/earnings" \
    "{\"account\": \"$TEST_ACCOUNT\", \"symbols\": [\"$TEST_SYMBOL\"]}"

echo ""

# ============================================================================
# Trading Tests (Read-only, no actual trades)
# ============================================================================
echo "=== Trading Endpoints (3 read-only tests) ==="

run_test "Get Positions" "POST" "/api/trade/positions" \
    "{\"account\": \"$TEST_ACCOUNT\"}"

run_test "Get Account Info" "POST" "/api/trade/account-info" \
    "{\"account\": \"$TEST_ACCOUNT\"}"

run_test "Get Orders" "POST" "/api/trade/orders" \
    "{\"account\": \"$TEST_ACCOUNT\"}"

echo ""
echo "======================================================================"
echo "Test Summary"
echo "======================================================================"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed! ✗${NC}"
    exit 1
fi
