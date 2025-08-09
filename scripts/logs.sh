#!/bin/bash

# Logs script for Tiger MCP Docker services
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="tiger-mcp"
COMPOSE_FILE="docker-compose.dev.yml"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [SERVICES...]

View logs for Tiger MCP Docker services.

OPTIONS:
    -h, --help              Show this help message
    -p, --prod              Use production configuration
    -f, --follow            Follow log output (like tail -f)
    -t, --tail LINES        Number of lines to show from end of logs (default: all)
    --since TIMESTAMP       Show logs since timestamp (e.g., "2023-01-01T00:00:00")
    --until TIMESTAMP       Show logs until timestamp
    --timestamps            Show timestamps
    --no-color              Disable colored output
    -f, --file FILE         Use specific docker-compose file

SERVICES:
    mcp-server              MCP server logs
    dashboard-api           Dashboard API logs
    postgres                PostgreSQL logs
    redis                   Redis logs
    nginx                   Nginx logs (production only)
    db-migrate              Database migration logs

EXAMPLES:
    # Show all logs
    $0

    # Follow logs for all services
    $0 --follow

    # Show last 50 lines for MCP server
    $0 --tail 50 mcp-server

    # Show logs since 1 hour ago
    $0 --since "1h" dashboard-api

    # Show production logs with timestamps
    $0 --prod --timestamps --follow

    # Show logs for multiple services
    $0 mcp-server dashboard-api

EOF
}

# Function to check service availability
check_service() {
    local service=$1
    if ! docker-compose -f "${COMPOSE_FILE}" ps "${service}" &> /dev/null; then
        print_warning "Service '${service}' not found or not running"
        return 1
    fi
    return 0
}

# Function to get service status
get_service_status() {
    local service=$1
    local status=$(docker-compose -f "${COMPOSE_FILE}" ps --format json "${service}" 2>/dev/null | jq -r '.[0].State // "not found"' 2>/dev/null || echo "unknown")
    echo "${status}"
}

# Function to show service overview
show_service_overview() {
    print_status "Service Overview:"
    echo ""
    printf "%-20s %-15s %-10s\n" "SERVICE" "STATUS" "PORTS"
    printf "%-20s %-15s %-10s\n" "-------" "------" "-----"
    
    local services=("postgres" "redis" "mcp-server" "dashboard-api")
    
    # Add nginx for production
    if [[ "${COMPOSE_FILE}" == "docker-compose.prod.yml" ]]; then
        services=("nginx" "${services[@]}")
    fi
    
    for service in "${services[@]}"; do
        if check_service "${service}" &>/dev/null; then
            local status=$(get_service_status "${service}")
            local ports=$(docker-compose -f "${COMPOSE_FILE}" ps --format json "${service}" 2>/dev/null | jq -r '.[0].Publishers[]?.PublishedPort // empty' 2>/dev/null | tr '\n' ',' | sed 's/,$//')
            
            # Color code status
            case "${status}" in
                "running") status="${GREEN}${status}${NC}" ;;
                "exited") status="${RED}${status}${NC}" ;;
                "restarting") status="${YELLOW}${status}${NC}" ;;
                *) status="${BLUE}${status}${NC}" ;;
            esac
            
            printf "%-30s %-25s %-10s\n" "${service}" "${status}" "${ports:-"-"}"
        else
            printf "%-30s %-25s %-10s\n" "${service}" "${RED}not found${NC}" "-"
        fi
    done
    echo ""
}

# Function to format logs with service names
format_logs() {
    local service_filter="$1"
    local logs_args="${@:2}"
    
    if [[ -n "${service_filter}" ]]; then
        docker-compose -f "${COMPOSE_FILE}" logs ${logs_args} ${service_filter}
    else
        docker-compose -f "${COMPOSE_FILE}" logs ${logs_args}
    fi
}

# Parse command line arguments
FOLLOW=false
TAIL=""
SINCE=""
UNTIL=""
TIMESTAMPS=false
NO_COLOR=false
SERVICES=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -p|--prod)
            COMPOSE_FILE="docker-compose.prod.yml"
            shift
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -t|--tail)
            TAIL="--tail $2"
            shift 2
            ;;
        --since)
            SINCE="--since $2"
            shift 2
            ;;
        --until)
            UNTIL="--until $2"
            shift 2
            ;;
        --timestamps)
            TIMESTAMPS=true
            shift
            ;;
        --no-color)
            NO_COLOR=true
            shift
            ;;
        --file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            # Remaining arguments are service names
            SERVICES="${SERVICES} $1"
            shift
            ;;
    esac
done

# Change to script directory
cd "$(dirname "$0")/.."

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if compose file exists
if [[ ! -f "${COMPOSE_FILE}" ]]; then
    print_error "Compose file not found: ${COMPOSE_FILE}"
    exit 1
fi

# Show service overview unless following logs
if [[ "${FOLLOW}" == "false" ]]; then
    show_service_overview
fi

# Validate requested services
if [[ -n "${SERVICES}" ]]; then
    for service in ${SERVICES}; do
        if ! check_service "${service}"; then
            print_warning "Skipping unavailable service: ${service}"
        fi
    done
fi

# Build logs command arguments
LOGS_ARGS=""

if [[ "${FOLLOW}" == "true" ]]; then
    LOGS_ARGS="${LOGS_ARGS} --follow"
fi

if [[ -n "${TAIL}" ]]; then
    LOGS_ARGS="${LOGS_ARGS} ${TAIL}"
fi

if [[ -n "${SINCE}" ]]; then
    LOGS_ARGS="${LOGS_ARGS} ${SINCE}"
fi

if [[ -n "${UNTIL}" ]]; then
    LOGS_ARGS="${LOGS_ARGS} ${UNTIL}"
fi

if [[ "${TIMESTAMPS}" == "true" ]]; then
    LOGS_ARGS="${LOGS_ARGS} --timestamps"
fi

if [[ "${NO_COLOR}" == "true" ]]; then
    LOGS_ARGS="${LOGS_ARGS} --no-color"
fi

# Show logs
print_status "Showing logs for Tiger MCP services..."
print_status "Compose file: ${COMPOSE_FILE}"

if [[ -n "${SERVICES}" ]]; then
    print_status "Services: ${SERVICES}"
else
    print_status "Services: all"
fi

if [[ "${FOLLOW}" == "true" ]]; then
    print_status "Following logs (Press Ctrl+C to stop)..."
fi

echo ""

# Execute logs command
if [[ -n "${SERVICES}" ]]; then
    format_logs "${SERVICES}" ${LOGS_ARGS}
else
    format_logs "" ${LOGS_ARGS}
fi