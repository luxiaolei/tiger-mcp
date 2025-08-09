#!/bin/bash

# Stop script for Tiger MCP Docker services
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
Usage: $0 [OPTIONS]

Stop Tiger MCP Docker services.

OPTIONS:
    -h, --help              Show this help message
    -p, --prod              Use production configuration
    -v, --volumes           Remove volumes as well
    -r, --remove-orphans    Remove orphaned containers
    --remove-images         Remove images after stopping
    --timeout TIMEOUT       Specify timeout for stopping containers (default: 10s)
    -f, --file FILE         Use specific docker-compose file
    -s, --service SERVICE   Stop specific service only

EXAMPLES:
    # Stop development environment
    $0

    # Stop production environment
    $0 --prod

    # Stop and remove volumes
    $0 --volumes

    # Stop specific service
    $0 --service mcp-server

    # Stop with custom timeout
    $0 --timeout 30

EOF
}

# Function to cleanup containers and networks
cleanup_resources() {
    local remove_volumes=$1
    local remove_images=$2
    local remove_orphans=$3
    
    # Stop and remove containers
    if ${COMPOSE_CMD} down \
        $([ "${remove_volumes}" = true ] && echo "--volumes") \
        $([ "${remove_orphans}" = true ] && echo "--remove-orphans") \
        --timeout "${TIMEOUT}"; then
        print_success "Containers stopped and removed"
    else
        print_warning "Some containers may not have stopped cleanly"
    fi
    
    # Remove images if requested
    if [[ "${remove_images}" == "true" ]]; then
        print_status "Removing images..."
        
        # Remove project images
        local images=$(docker images --filter="reference=${PROJECT_NAME}-*" -q)
        if [[ -n "${images}" ]]; then
            docker rmi ${images} || print_warning "Some images could not be removed"
            print_success "Project images removed"
        else
            print_status "No project images found to remove"
        fi
        
        # Remove dangling images
        local dangling=$(docker images -f "dangling=true" -q)
        if [[ -n "${dangling}" ]]; then
            docker rmi ${dangling} || print_warning "Some dangling images could not be removed"
            print_success "Dangling images removed"
        fi
    fi
}

# Function to show resource usage before cleanup
show_resources() {
    print_status "Current Docker resources:"
    echo "Containers:"
    docker ps -a --filter="label=com.docker.compose.project=${PROJECT_NAME}" --format="table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true
    
    echo ""
    echo "Images:"
    docker images --filter="reference=${PROJECT_NAME}-*" --format="table {{.Repository}}\t{{.Tag}}\t{{.Size}}" || true
    
    echo ""
    echo "Volumes:"
    docker volume ls --filter="label=com.docker.compose.project=${PROJECT_NAME}" --format="table {{.Name}}\t{{.Driver}}" || true
    
    echo ""
    echo "Networks:"
    docker network ls --filter="label=com.docker.compose.project=${PROJECT_NAME}" --format="table {{.Name}}\t{{.Driver}}" || true
}

# Parse command line arguments
REMOVE_VOLUMES=false
REMOVE_IMAGES=false
REMOVE_ORPHANS=false
TIMEOUT=10
SPECIFIC_SERVICE=""

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
        -v|--volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        -r|--remove-orphans)
            REMOVE_ORPHANS=true
            shift
            ;;
        --remove-images)
            REMOVE_IMAGES=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -s|--service)
            SPECIFIC_SERVICE="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
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

# Build compose command
COMPOSE_CMD="docker-compose -f ${COMPOSE_FILE}"

# Show current resources
show_resources

print_status "Stopping Tiger MCP services..."
print_status "Compose file: ${COMPOSE_FILE}"
print_status "Timeout: ${TIMEOUT}s"

if [[ "${REMOVE_VOLUMES}" == "true" ]]; then
    print_warning "Volumes will be removed (data will be lost)"
fi

if [[ "${REMOVE_IMAGES}" == "true" ]]; then
    print_warning "Images will be removed"
fi

# Confirmation for destructive operations
if [[ "${REMOVE_VOLUMES}" == "true" || "${REMOVE_IMAGES}" == "true" ]]; then
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Operation cancelled"
        exit 0
    fi
fi

# Stop specific service or all services
if [[ -n "${SPECIFIC_SERVICE}" ]]; then
    print_status "Stopping ${SPECIFIC_SERVICE}..."
    
    if ${COMPOSE_CMD} stop --timeout "${TIMEOUT}" "${SPECIFIC_SERVICE}"; then
        print_success "${SPECIFIC_SERVICE} stopped"
        
        # Remove container if requested
        if [[ "${REMOVE_VOLUMES}" == "true" || "${REMOVE_ORPHANS}" == "true" ]]; then
            ${COMPOSE_CMD} rm -f "${SPECIFIC_SERVICE}"
            print_success "${SPECIFIC_SERVICE} container removed"
        fi
    else
        print_error "Failed to stop ${SPECIFIC_SERVICE}"
        exit 1
    fi
else
    # Stop all services
    cleanup_resources "${REMOVE_VOLUMES}" "${REMOVE_IMAGES}" "${REMOVE_ORPHANS}"
fi

# Show remaining resources
print_status "Remaining Docker resources:"
show_resources

# Cleanup suggestions
print_status "Cleanup suggestions:"
echo "  🧹 Remove all stopped containers: docker container prune"
echo "  🗂️  Remove unused volumes:         docker volume prune"
echo "  🖼️  Remove unused images:          docker image prune"
echo "  🌐 Remove unused networks:        docker network prune"
echo "  🚀 Remove everything unused:      docker system prune -a"

print_success "Tiger MCP services stopped!"

# Show start command
echo ""
print_status "To start services again:"
echo "  ./scripts/start.sh$([ "${COMPOSE_FILE}" != "docker-compose.dev.yml" ] && echo " --prod")"