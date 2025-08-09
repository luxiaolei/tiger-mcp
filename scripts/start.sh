#!/bin/bash

# Start script for Tiger MCP Docker services
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
ENV_FILE=".env"

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

Start Tiger MCP Docker services.

OPTIONS:
    -h, --help              Show this help message
    -p, --prod              Use production configuration
    -d, --detach            Run in detached mode
    -b, --build             Build images before starting
    --pull                  Pull latest images before starting
    --scale SERVICE=NUM     Scale a service to NUM instances
    --profile PROFILE       Use specific docker-compose profile
    -f, --file FILE         Use specific docker-compose file
    -s, --service SERVICE   Start specific service only
    --no-deps               Don't start linked services

EXAMPLES:
    # Start development environment
    $0

    # Start production environment
    $0 --prod

    # Start with rebuild
    $0 --build

    # Start in detached mode
    $0 --detach

    # Start only specific service
    $0 --service mcp-server

    # Scale dashboard API to 3 instances
    $0 --scale dashboard-api=3

EOF
}

# Function to check prerequisites
check_prerequisites() {
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi

    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi

    # Check if .env file exists
    if [[ ! -f "${ENV_FILE}" ]]; then
        print_warning ".env file not found. Creating from template..."
        if [[ -f ".env.template" ]]; then
            cp .env.template "${ENV_FILE}"
            print_status "Created ${ENV_FILE} from template. Please configure your environment variables."
        else
            create_env_template
            print_warning "Please configure your environment variables in ${ENV_FILE}"
        fi
    fi
}

# Function to create basic .env template
create_env_template() {
    cat > "${ENV_FILE}" << EOF
# Tiger API Configuration
TIGER_CLIENT_ID=your_client_id_here
TIGER_PRIVATE_KEY=your_private_key_here
TIGER_ACCOUNT=your_account_here
TIGER_SANDBOX=true

# Database Configuration
POSTGRES_DB=tiger_mcp_dev
POSTGRES_USER=tiger_user
POSTGRES_PASSWORD=tiger_dev_password
POSTGRES_PORT=5432

# Redis Configuration
REDIS_PORT=6379
REDIS_PASSWORD=

# Application Configuration
SECRET_KEY=dev-secret-key-change-in-production
LOG_LEVEL=info
DEBUG=true

# API Configuration
MCP_SERVER_PORT=8000
DASHBOARD_API_PORT=8001

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]

# JWT Configuration
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
EOF
    print_success "Created ${ENV_FILE} template"
}

# Function to wait for service health
wait_for_service() {
    local service=$1
    local timeout=${2:-120}
    local interval=${3:-5}
    
    print_status "Waiting for ${service} to be healthy..."
    
    local count=0
    local max_count=$((timeout / interval))
    
    while [[ $count -lt $max_count ]]; do
        if docker-compose -f "${COMPOSE_FILE}" ps "${service}" | grep -q "healthy"; then
            print_success "${service} is healthy"
            return 0
        fi
        
        if docker-compose -f "${COMPOSE_FILE}" ps "${service}" | grep -q "unhealthy"; then
            print_error "${service} is unhealthy"
            print_status "Checking logs for ${service}:"
            docker-compose -f "${COMPOSE_FILE}" logs --tail=20 "${service}"
            return 1
        fi
        
        sleep $interval
        count=$((count + 1))
        echo -n "."
    done
    
    echo ""
    print_error "Timeout waiting for ${service} to be healthy"
    return 1
}

# Parse command line arguments
DETACH=false
BUILD=false
PULL=false
SCALE_ARGS=""
PROFILE=""
SPECIFIC_SERVICE=""
NO_DEPS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -p|--prod)
            COMPOSE_FILE="docker-compose.prod.yml"
            ENV_FILE=".env.prod"
            shift
            ;;
        -d|--detach)
            DETACH=true
            shift
            ;;
        -b|--build)
            BUILD=true
            shift
            ;;
        --pull)
            PULL=true
            shift
            ;;
        --scale)
            SCALE_ARGS="--scale $2"
            shift 2
            ;;
        --profile)
            PROFILE="--profile $2"
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
        --no-deps)
            NO_DEPS=true
            shift
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

# Check prerequisites
check_prerequisites

# Build compose command
COMPOSE_CMD="docker-compose -f ${COMPOSE_FILE}"

if [[ -n "${PROFILE}" ]]; then
    COMPOSE_CMD="${COMPOSE_CMD} ${PROFILE}"
fi

# Pull images if requested
if [[ "${PULL}" == "true" ]]; then
    print_status "Pulling latest images..."
    ${COMPOSE_CMD} pull
fi

# Build images if requested
if [[ "${BUILD}" == "true" ]]; then
    print_status "Building images..."
    ${COMPOSE_CMD} build
fi

# Prepare startup command
START_CMD="${COMPOSE_CMD} up"

if [[ "${DETACH}" == "true" ]]; then
    START_CMD="${START_CMD} -d"
fi

if [[ -n "${SCALE_ARGS}" ]]; then
    START_CMD="${START_CMD} ${SCALE_ARGS}"
fi

if [[ "${NO_DEPS}" == "true" ]]; then
    START_CMD="${START_CMD} --no-deps"
fi

if [[ -n "${SPECIFIC_SERVICE}" ]]; then
    START_CMD="${START_CMD} ${SPECIFIC_SERVICE}"
fi

# Start services
print_status "Starting Tiger MCP services..."
print_status "Compose file: ${COMPOSE_FILE}"
print_status "Environment: ${ENV_FILE}"

if ${START_CMD}; then
    if [[ "${DETACH}" == "true" ]]; then
        print_success "Services started in detached mode"
        
        # Wait for critical services to be healthy
        critical_services=("postgres" "redis")
        if [[ -z "${SPECIFIC_SERVICE}" ]]; then
            for service in "${critical_services[@]}"; do
                wait_for_service "${service}" 60 5
            done
            
            # Wait for application services
            app_services=("mcp-server" "dashboard-api")
            for service in "${app_services[@]}"; do
                wait_for_service "${service}" 120 10
            done
        elif [[ "${SPECIFIC_SERVICE}" =~ ^(mcp-server|dashboard-api)$ ]]; then
            wait_for_service "${SPECIFIC_SERVICE}" 120 10
        fi
        
        # Show service status
        print_status "Service status:"
        ${COMPOSE_CMD} ps
        
        # Show URLs
        echo ""
        print_success "Tiger MCP services are running!"
        echo ""
        print_status "Available endpoints:"
        if [[ "${COMPOSE_FILE}" == "docker-compose.prod.yml" ]]; then
            echo "  🌐 Dashboard API:     https://localhost/api"
            echo "  🔧 MCP Server:       https://localhost/mcp"
            echo "  📊 Health Check:     https://localhost/health"
        else
            echo "  🔧 MCP Server:       http://localhost:8000"
            echo "  🌐 Dashboard API:    http://localhost:8001"
            echo "  📊 PostgreSQL:       localhost:5432"
            echo "  🔴 Redis:            localhost:6379"
        fi
        echo ""
        print_status "Useful commands:"
        echo "  📋 View logs:        ./scripts/logs.sh"
        echo "  🛑 Stop services:    ./scripts/stop.sh"
        echo "  📊 Service status:   docker-compose -f ${COMPOSE_FILE} ps"
        echo "  🔍 Service logs:     docker-compose -f ${COMPOSE_FILE} logs -f [service]"
    else
        print_success "Services started successfully"
    fi
else
    print_error "Failed to start services"
    exit 1
fi