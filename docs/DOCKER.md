# Docker Configuration for Tiger MCP System

This document describes the Docker setup for the Tiger MCP (Model Context Protocol) system, including development and production configurations.

## Overview

The Tiger MCP system consists of the following containerized services:

- **PostgreSQL**: Primary database for storing application data
- **Redis**: Cache and message broker for real-time features
- **MCP Server**: FastMCP server for Tiger Brokers API integration
- **Dashboard API**: FastAPI backend for the web dashboard
- **Database Migration**: Service for running database migrations
- **Nginx** (Production): Reverse proxy and load balancer

## Directory Structure

```
tiger-mcp/
├── docker/
│   ├── mcp-server/
│   │   ├── Dockerfile
│   │   └── .dockerignore
│   ├── dashboard-api/
│   │   ├── Dockerfile
│   │   └── .dockerignore
│   ├── database/
│   │   ├── Dockerfile
│   │   └── .dockerignore
│   ├── nginx/
│   │   └── nginx.conf
│   ├── redis/
│   │   ├── redis.conf
│   │   └── redis-prod.conf
│   └── postgres/
│       ├── postgresql.conf
│       └── pg_hba.conf
├── scripts/
│   ├── build.sh
│   ├── start.sh
│   ├── stop.sh
│   └── logs.sh
├── secrets/
│   └── README.md
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── .env.template
└── .env.prod.template
```

## Quick Start

### Development Environment

1. **Copy environment template**:
   ```bash
   cp .env.template .env
   # Edit .env with your Tiger API credentials
   ```

2. **Build and start services**:
   ```bash
   ./scripts/build.sh
   ./scripts/start.sh
   ```

3. **View logs**:
   ```bash
   ./scripts/logs.sh --follow
   ```

4. **Stop services**:
   ```bash
   ./scripts/stop.sh
   ```

### Production Environment

1. **Setup secrets**:
   ```bash
   cd secrets
   # Follow instructions in secrets/README.md
   openssl rand -base64 32 > postgres_password.txt
   openssl rand -base64 32 > redis_password.txt
   openssl rand -base64 64 > secret_key.txt
   cp /path/to/tiger_private_key.pem .
   chmod 600 *.txt *.pem
   ```

2. **Configure production environment**:
   ```bash
   cp .env.prod.template .env.prod
   # Edit .env.prod with your production settings
   ```

3. **Build and deploy**:
   ```bash
   ./scripts/build.sh --registry your-registry.com --push
   ./scripts/start.sh --prod
   ```

## Service Details

### MCP Server
- **Image**: `tiger-mcp-mcp-server:latest`
- **Port**: 8000
- **Health Check**: `http://localhost:8000/health`
- **Features**:
  - FastMCP integration
  - Tiger Brokers API connectivity
  - Process pool for concurrent requests
  - Comprehensive logging

### Dashboard API
- **Image**: `tiger-mcp-dashboard-api:latest`
- **Port**: 8001
- **Health Check**: `http://localhost:8001/health`
- **Features**:
  - FastAPI REST API
  - JWT authentication
  - Database integration
  - CORS configuration

### Database Migration
- **Image**: `tiger-mcp-database:latest`
- **Purpose**: Run Alembic migrations
- **Features**:
  - Automatic schema updates
  - Migration rollback support
  - Production-ready migrations

### PostgreSQL
- **Image**: `postgres:15-alpine`
- **Port**: 5432
- **Features**:
  - Optimized configuration
  - Health checks
  - Persistent volumes
  - Security hardening

### Redis
- **Image**: `redis:7-alpine`
- **Port**: 6379
- **Features**:
  - Persistent storage
  - Memory optimization
  - Security configuration
  - Health monitoring

### Nginx (Production)
- **Image**: `nginx:1.25-alpine`
- **Ports**: 80, 443
- **Features**:
  - SSL termination
  - Load balancing
  - Rate limiting
  - Security headers

## Docker Images

### Multi-Stage Builds

All application images use multi-stage builds for optimization:

1. **Builder Stage**:
   - Full development environment
   - UV package manager
   - Build dependencies
   - Source code compilation

2. **Production Stage**:
   - Minimal runtime environment
   - Non-root user
   - Security hardening
   - Health checks

### Image Sizes

| Service | Builder | Production |
|---------|---------|------------|
| MCP Server | ~800MB | ~200MB |
| Dashboard API | ~750MB | ~180MB |
| Database | ~700MB | ~150MB |

## Networking

### Development Network
- **Name**: `tiger-mcp-network-dev`
- **Subnet**: `172.20.0.0/16`
- **Driver**: bridge

### Production Network
- **Name**: `tiger-mcp-network-prod`
- **Subnet**: `172.21.0.0/16`
- **Driver**: bridge
- **Features**: Isolated network with restricted access

## Volume Management

### Development Volumes
- `postgres_data_dev`: PostgreSQL data persistence
- `redis_data_dev`: Redis data persistence
- `./logs`: Application logs (bind mount)

### Production Volumes
- `postgres_data_prod`: Persistent PostgreSQL data
- `redis_data_prod`: Persistent Redis data
- Bind mounts to `/opt/tiger-mcp/data/`

## Security Features

### Container Security
- Non-root user execution
- Read-only root filesystem where possible
- Security scanning in CI/CD
- Regular base image updates

### Network Security
- Internal network isolation
- Rate limiting on public endpoints
- SSL/TLS termination
- Security headers

### Secrets Management
- Docker secrets for sensitive data
- Environment variable validation
- Secure file permissions
- Secret rotation support

## Monitoring and Health Checks

### Health Check Endpoints
- **MCP Server**: `GET /health`
- **Dashboard API**: `GET /health`
- **Combined**: `GET /health/combined`

### Monitoring Stack (Optional)
```yaml
# Add to docker-compose.prod.yml
prometheus:
  image: prom/prometheus:latest
  # ... configuration

grafana:
  image: grafana/grafana:latest
  # ... configuration
```

## Development Features

### Hot Reload
Development containers support hot reload:
```yaml
develop:
  watch:
    - action: sync
      path: ./packages/mcp-server/src
      target: /app
```

### Debug Mode
Enable debug mode in development:
```bash
DEBUG=true ./scripts/start.sh
```

## Production Optimizations

### Resource Limits
```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '1.0'
    reservations:
      memory: 512M
      cpus: '0.5'
```

### Update Strategy
```yaml
deploy:
  update_config:
    parallelism: 1
    delay: 30s
    order: stop-first
  restart_policy:
    condition: on-failure
    delay: 30s
    max_attempts: 3
```

## Troubleshooting

### Common Issues

1. **Permission Denied**:
   ```bash
   sudo chown -R $(id -u):$(id -g) logs/
   ```

2. **Port Already in Use**:
   ```bash
   # Change ports in .env file
   MCP_SERVER_PORT=8002
   DASHBOARD_API_PORT=8003
   ```

3. **Database Connection**:
   ```bash
   # Check database health
   docker-compose -f docker-compose.dev.yml logs postgres
   ```

4. **SSL Certificate Issues**:
   ```bash
   # Generate self-signed certificate for testing
   openssl req -x509 -newkey rsa:4096 -nodes \
     -out docker/ssl/server.crt \
     -keyout docker/ssl/server.key \
     -days 365 -subj "/CN=localhost"
   ```

### Debugging Commands

```bash
# View service status
docker-compose -f docker-compose.dev.yml ps

# Inspect service logs
./scripts/logs.sh --service mcp-server --tail 100

# Access container shell
docker exec -it tiger-mcp-server-dev /bin/bash

# Test service connectivity
curl -f http://localhost:8000/health

# Check resource usage
docker stats
```

### Log Analysis

```bash
# Follow all logs with timestamps
./scripts/logs.sh --follow --timestamps

# Filter specific log levels
./scripts/logs.sh mcp-server | grep ERROR

# Export logs for analysis
./scripts/logs.sh --since "2024-01-01" > analysis.log
```

## Script Reference

### build.sh
```bash
# Build all services
./scripts/build.sh

# Build specific service
./scripts/build.sh --service mcp-server

# Build and push to registry
./scripts/build.sh --registry myregistry.com --push

# Build without cache
./scripts/build.sh --no-cache
```

### start.sh
```bash
# Start development environment
./scripts/start.sh

# Start production environment
./scripts/start.sh --prod

# Start with rebuild
./scripts/start.sh --build

# Start specific service
./scripts/start.sh --service mcp-server
```

### stop.sh
```bash
# Stop all services
./scripts/stop.sh

# Stop and remove volumes
./scripts/stop.sh --volumes

# Stop specific service
./scripts/stop.sh --service mcp-server
```

### logs.sh
```bash
# View all logs
./scripts/logs.sh

# Follow logs
./scripts/logs.sh --follow

# View specific service logs
./scripts/logs.sh mcp-server dashboard-api

# View last 50 lines
./scripts/logs.sh --tail 50
```

## Performance Tuning

### PostgreSQL Tuning
```sql
-- Monitor query performance
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;

-- Monitor connection usage
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
```

### Redis Tuning
```bash
# Monitor Redis performance
docker exec -it tiger-mcp-redis-prod redis-cli INFO stats
docker exec -it tiger-mcp-redis-prod redis-cli SLOWLOG GET 10
```

### Application Tuning
```bash
# Monitor container resources
docker stats tiger-mcp-server-prod

# Profile application performance
docker exec -it tiger-mcp-server-prod py-spy top -p 1
```

## Backup and Recovery

### Database Backup
```bash
# Create backup
docker exec tiger-mcp-postgres-prod pg_dump -U tiger_user tiger_mcp_prod > backup.sql

# Restore from backup
docker exec -i tiger-mcp-postgres-prod psql -U tiger_user -d tiger_mcp_prod < backup.sql
```

### Volume Backup
```bash
# Backup volumes
docker run --rm -v tiger-mcp-postgres-data-prod:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz /data

# Restore volumes
docker run --rm -v tiger-mcp-postgres-data-prod:/data -v $(pwd):/backup \
  alpine tar xzf /backup/postgres-backup.tar.gz -C /
```

## Contributing

### Adding New Services

1. Create Dockerfile in `docker/service-name/`
2. Add service to docker-compose files
3. Update build and start scripts
4. Add health checks and monitoring
5. Update documentation

### Testing Changes

```bash
# Test development environment
./scripts/build.sh --service new-service
./scripts/start.sh --service new-service
./scripts/logs.sh new-service

# Test production environment
./scripts/build.sh --service new-service --target production
./scripts/start.sh --prod --service new-service
```