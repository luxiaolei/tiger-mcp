#!/bin/bash

# Build script for Tiger MCP Docker images
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="tiger-mcp"
BUILD_CACHE_FROM=${BUILD_CACHE_FROM:-""}
TARGET=${TARGET:-"production"}
PUSH=${PUSH:-false}
REGISTRY=${REGISTRY:-""}

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

# Function to build a service
build_service() {
    local service=$1
    local dockerfile=$2
    local context=${3:-"."}
    
    print_status "Building ${service}..."
    
    local build_args=""
    if [[ -n "${BUILD_CACHE_FROM}" ]]; then
        build_args="--cache-from ${BUILD_CACHE_FROM}/${PROJECT_NAME}-${service}:latest"
    fi
    
    local tag="${PROJECT_NAME}-${service}:latest"
    if [[ -n "${REGISTRY}" ]]; then
        tag="${REGISTRY}/${tag}"
    fi
    
    if docker build \
        --target "${TARGET}" \
        --tag "${tag}" \
        --file "${dockerfile}" \
        ${build_args} \
        "${context}"; then
        print_success "Built ${service} successfully"
        
        # Push if requested
        if [[ "${PUSH}" == "true" && -n "${REGISTRY}" ]]; then
            print_status "Pushing ${service} to registry..."
            docker push "${tag}"
            print_success "Pushed ${service} to registry"
        fi
    else
        print_error "Failed to build ${service}"
        return 1
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build Docker images for Tiger MCP services.

OPTIONS:
    -h, --help              Show this help message
    -t, --target TARGET     Build target (builder|production) [default: production]
    -r, --registry URL      Docker registry URL for tagging
    -p, --push              Push images to registry after building
    -c, --cache-from URL    Use cache from registry
    -s, --service SERVICE   Build specific service only (mcp-server|dashboard-api|database)
    --no-cache              Build without cache

EXAMPLES:
    # Build all services for production
    $0

    # Build all services and push to registry
    $0 --registry myregistry.com --push

    # Build only the MCP server
    $0 --service mcp-server

    # Build with cache from registry
    $0 --cache-from myregistry.com --registry myregistry.com --push

EOF
}

# Parse command line arguments
SPECIFIC_SERVICE=""
NO_CACHE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -c|--cache-from)
            BUILD_CACHE_FROM="$2"
            shift 2
            ;;
        -s|--service)
            SPECIFIC_SERVICE="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate target
if [[ "${TARGET}" != "builder" && "${TARGET}" != "production" ]]; then
    print_error "Invalid target: ${TARGET}. Must be 'builder' or 'production'"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Change to script directory
cd "$(dirname "$0")/.."

print_status "Building Tiger MCP Docker images..."
print_status "Target: ${TARGET}"
print_status "Registry: ${REGISTRY:-"local"}"
print_status "Push: ${PUSH}"

# Add no-cache flag if requested
if [[ "${NO_CACHE}" == "true" ]]; then
    BUILD_ARGS="--no-cache"
else
    BUILD_ARGS=""
fi

# Build services
if [[ -n "${SPECIFIC_SERVICE}" ]]; then
    case "${SPECIFIC_SERVICE}" in
        mcp-server)
            build_service "mcp-server" "docker/mcp-server/Dockerfile"
            ;;
        dashboard-api)
            build_service "dashboard-api" "docker/dashboard-api/Dockerfile"
            ;;
        database)
            build_service "database" "docker/database/Dockerfile"
            ;;
        *)
            print_error "Unknown service: ${SPECIFIC_SERVICE}"
            print_error "Available services: mcp-server, dashboard-api, database"
            exit 1
            ;;
    esac
else
    # Build all services
    services=("mcp-server" "dashboard-api" "database")
    
    for service in "${services[@]}"; do
        if ! build_service "${service}" "docker/${service}/Dockerfile"; then
            print_error "Build failed for ${service}"
            exit 1
        fi
    done
fi

# Show built images
print_status "Built images:"
docker images | grep "${PROJECT_NAME}" | head -10

print_success "All builds completed successfully!"

# Show next steps
echo ""
print_status "Next steps:"
echo "  - Run development environment: ./scripts/start.sh"
echo "  - Run production environment: ./scripts/start.sh --prod"
echo "  - View logs: ./scripts/logs.sh"
echo "  - Stop services: ./scripts/stop.sh"