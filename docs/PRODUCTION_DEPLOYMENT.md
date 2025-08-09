# Tiger MCP Production Deployment Guide

Comprehensive guide for deploying Tiger MCP system in production environments with security, monitoring, and operational best practices.

## Pre-Deployment Checklist

### System Requirements

**Hardware Minimums:**
- **CPU**: 4 cores (8 recommended)
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 50GB SSD minimum (100GB recommended)
- **Network**: Stable internet with low latency to Tiger API servers

**Software Requirements:**
- **OS**: Ubuntu 20.04+ / RHEL 8+ / Amazon Linux 2
- **Docker**: 24.0+
- **Docker Compose**: v2.20+
- **SSL Certificate**: Valid certificate for HTTPS
- **Firewall**: Properly configured security groups

### Security Prerequisites

✅ **SSL/TLS Certificates** - Valid certificates for all domains  
✅ **Secrets Management** - Proper secret storage and rotation  
✅ **Network Security** - Firewall rules and VPC configuration  
✅ **Access Control** - SSH keys, user management, and permissions  
✅ **Backup Strategy** - Database and configuration backups  
✅ **Monitoring Setup** - Logging, metrics, and alerting systems  

## Production Environment Setup

### Step 1: Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
sudo mkdir -p /opt/tiger-mcp
sudo chown $USER:$USER /opt/tiger-mcp
cd /opt/tiger-mcp
```

### Step 2: SSL Certificate Setup

#### Option A: Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com -d api.yourdomain.com

# Copy certificates to Docker directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/ssl/server.crt
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/ssl/server.key
sudo chown $USER:$USER docker/ssl/server.*
chmod 644 docker/ssl/server.crt
chmod 600 docker/ssl/server.key

# Setup auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### Option B: Custom Certificate

```bash
# Copy your certificates
cp /path/to/your/certificate.pem docker/ssl/server.crt
cp /path/to/your/private-key.pem docker/ssl/server.key
chmod 644 docker/ssl/server.crt
chmod 600 docker/ssl/server.key
```

### Step 3: Secrets Management

```bash
# Create secrets directory
mkdir -p secrets/
cd secrets/

# Generate secure passwords
openssl rand -base64 32 > postgres_password.txt
openssl rand -base64 32 > redis_password.txt
openssl rand -base64 64 > secret_key.txt

# Copy Tiger private key
cp /secure/path/to/tiger_private_key.pem .
chmod 600 *.txt *.pem

# Create Tiger properties files
cat > tiger_openapi_config.properties << EOF
tiger_id=YOUR_TIGER_ID
account=YOUR_ACCOUNT_NUMBER
license=YOUR_LICENSE
env=PROD
private_key_pk1=-----BEGIN RSA PRIVATE KEY-----
YOUR_PRIVATE_KEY_CONTENT_HERE
-----END RSA PRIVATE KEY-----
EOF

cat > tiger_openapi_token.properties << EOF
token=
EOF

chmod 600 *.properties
```

### Step 4: Production Configuration

Create production environment file:

```bash
# Create .env.prod
cat > .env.prod << EOF
# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
POSTGRES_DB=tiger_mcp_prod
POSTGRES_USER=tiger_prod
POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
DATABASE_URL=postgresql://tiger_prod:@postgres:5432/tiger_mcp_prod

# Redis Configuration  
REDIS_PASSWORD_FILE=/run/secrets/redis_password

# Application Secrets
SECRET_KEY_FILE=/run/secrets/secret_key
ENCRYPTION_MASTER_KEY=YOUR_GENERATED_MASTER_KEY

# Tiger API Configuration
TIGER_USE_PROPERTIES=true
TIGER_PROPERTIES_PATH=/app/secrets
TIGER_API_TIMEOUT=30
TIGER_API_RETRIES=3

# Security Configuration
JWT_SECRET=YOUR_JWT_SECRET
PBKDF2_ITERATIONS=100000
PASSWORD_HASH_ALGORITHM=argon2
SECURITY_RATE_LIMIT=1000

# Network Configuration
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
SECURE_COOKIES=true
HTTPS_ONLY=true

# Process Configuration
MCP_PROCESS_MIN_WORKERS=4
MCP_PROCESS_MAX_WORKERS=16
MCP_PROCESS_TARGET_WORKERS=8

# Resource Limits
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
REDIS_MAX_CONNECTIONS=50
EOF
```

### Step 5: Production Docker Compose

Update `docker-compose.prod.yml` for your environment:

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/ssl/server.crt:/etc/nginx/ssl/server.crt:ro
      - ./docker/ssl/server.key:/etc/nginx/ssl/server.key:ro
    depends_on:
      - mcp-server
      - dashboard-api
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: tiger_mcp_prod
      POSTGRES_USER: tiger_prod
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
      - ./docker/postgres/postgresql.conf:/etc/postgresql/postgresql.conf
      - ./docker/postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf
    secrets:
      - postgres_password
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tiger_prod -d tiger_mcp_prod"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server /etc/redis/redis.conf --requirepass_file /run/secrets/redis_password
    volumes:
      - redis_data_prod:/data
      - ./docker/redis/redis-prod.conf:/etc/redis/redis.conf:ro
    secrets:
      - redis_password
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  mcp-server:
    build:
      context: .
      dockerfile: docker/mcp-server/Dockerfile
      target: production
    environment:
      - DATABASE_URL=postgresql://tiger_prod:@postgres:5432/tiger_mcp_prod
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env.prod
    volumes:
      - ./secrets:/app/secrets:ro
      - ./logs:/app/logs
    secrets:
      - postgres_password
      - redis_password
      - secret_key
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
      replicas: 2
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  dashboard-api:
    build:
      context: .
      dockerfile: docker/dashboard-api/Dockerfile
      target: production
    environment:
      - DATABASE_URL=postgresql://tiger_prod:@postgres:5432/tiger_mcp_prod
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env.prod
    secrets:
      - postgres_password
      - redis_password
      - secret_key
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
      replicas: 2
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
  secret_key:
    file: ./secrets/secret_key.txt

volumes:
  postgres_data_prod:
    driver: local
  redis_data_prod:
    driver: local

networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
```

### Step 6: Deploy to Production

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run database migrations
docker-compose -f docker-compose.prod.yml exec mcp-server python -m database.manage_db migrate

# Check service status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs
```

## Monitoring and Logging

### Step 1: Configure Structured Logging

Create `logging.conf`:

```ini
[loggers]
keys=root,tiger_mcp

[handlers]
keys=console,file,syslog

[formatters]
keys=json

[logger_root]
level=INFO
handlers=console,file,syslog

[logger_tiger_mcp]
level=INFO
handlers=file,syslog
qualname=tiger_mcp
propagate=0

[handler_console]
class=StreamHandler
level=INFO
formatter=json
args=(sys.stdout,)

[handler_file]
class=logging.handlers.RotatingFileHandler
level=INFO
formatter=json
args=('/app/logs/tiger-mcp.log', 'a', 100*1024*1024, 5)

[handler_syslog]
class=logging.handlers.SysLogHandler
level=WARNING
formatter=json
args=('/dev/log',)

[formatter_json]
format={"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s","module":"%(module)s","function":"%(funcName)s","line":%(lineno)d}
```

### Step 2: Health Monitoring Setup

Create monitoring script:

```bash
#!/bin/bash
# monitoring/health-check.sh

set -e

echo "=== Tiger MCP Health Check ==="
echo "Timestamp: $(date -Iseconds)"

# Check service health
echo "Checking service health..."
curl -f -s http://localhost/api/health || echo "❌ API health check failed"
curl -f -s http://localhost/mcp/health || echo "❌ MCP health check failed"

# Check database
echo "Checking database..."
docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U tiger_prod -d tiger_mcp_prod || echo "❌ Database check failed"

# Check Redis
echo "Checking Redis..."
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping || echo "❌ Redis check failed"

# Check disk space
echo "Checking disk space..."
df -h | grep -E '^/dev/' | awk '{print $1 " " $5 " " $6}' | while read output; do
  usep=$(echo $output | awk '{print $2}' | cut -d'%' -f1)
  partition=$(echo $output | awk '{print $3}')
  if [ $usep -ge 90 ]; then
    echo "❌ Running out of space on $partition ($usep%)"
  else
    echo "✅ Disk space OK on $partition ($usep%)"
  fi
done

# Check memory
echo "Checking memory..."
free -m | awk 'NR==2{printf "Memory: %s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }'

echo "Health check complete."
```

### Step 3: Application Metrics

Add to your monitoring configuration:

```yaml
# monitoring/docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_password_here

volumes:
  prometheus_data:
  grafana_data:
```

## Security Hardening

### Step 1: Network Security

```bash
# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Configure fail2ban
sudo apt install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Edit /etc/fail2ban/jail.local
sudo tee -a /etc/fail2ban/jail.local << EOF
[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600
EOF
```

### Step 2: Container Security

```bash
# Run Docker security benchmark
docker run --rm --net host --pid host --userns host --cap-add audit_control \
    -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST \
    -v /etc:/etc:ro \
    -v /usr/bin/containerd:/usr/bin/containerd:ro \
    -v /usr/bin/runc:/usr/bin/runc:ro \
    -v /usr/lib/systemd:/usr/lib/systemd:ro \
    -v /var/lib:/var/lib:ro \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    --label docker_bench_security \
    docker/docker-bench-security
```

### Step 3: Application Security

Update nginx configuration for security headers:

```nginx
# docker/nginx/nginx.conf - Security headers section
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Referrer-Policy "strict-origin-when-cross-origin";
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';";

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=1r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    # ... rest of location config
}

location /auth/ {
    limit_req zone=auth burst=5 nodelay;
    # ... rest of location config
}
```

## Backup Strategy

### Step 1: Database Backups

```bash
#!/bin/bash
# scripts/backup-database.sh

BACKUP_DIR="/opt/backups/tiger-mcp"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="tiger_mcp_backup_${TIMESTAMP}.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U tiger_prod tiger_mcp_prod > "$BACKUP_DIR/$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_DIR/$BACKUP_FILE"

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Database backup completed: ${BACKUP_FILE}.gz"
```

### Step 2: Configuration Backups

```bash
#!/bin/bash
# scripts/backup-config.sh

BACKUP_DIR="/opt/backups/tiger-mcp/config"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACKUP_DIR

# Backup configuration (excluding secrets)
tar -czf "$BACKUP_DIR/config_${TIMESTAMP}.tar.gz" \
    --exclude="secrets/*" \
    --exclude="*.log" \
    --exclude="__pycache__" \
    .env.prod docker/ logs/ *.yml *.yaml

echo "Configuration backup completed: config_${TIMESTAMP}.tar.gz"
```

### Step 3: Automated Backup Schedule

```bash
# Add to crontab
crontab -e

# Add these lines:
# Database backup every 6 hours
0 */6 * * * /opt/tiger-mcp/scripts/backup-database.sh

# Configuration backup daily at 2 AM
0 2 * * * /opt/tiger-mcp/scripts/backup-config.sh

# Health check every 5 minutes
*/5 * * * * /opt/tiger-mcp/monitoring/health-check.sh >> /var/log/tiger-mcp-health.log 2>&1
```

## Operational Procedures

### Deployment Updates

```bash
#!/bin/bash
# scripts/deploy-update.sh

set -e

echo "Starting Tiger MCP deployment update..."

# Pull latest changes
git pull origin main

# Build new images
docker-compose -f docker-compose.prod.yml build

# Run database migrations
docker-compose -f docker-compose.prod.yml run --rm mcp-server python -m database.manage_db migrate

# Rolling update (zero downtime)
docker-compose -f docker-compose.prod.yml up -d --no-deps mcp-server
sleep 30
docker-compose -f docker-compose.prod.yml up -d --no-deps dashboard-api

# Health check
sleep 60
./monitoring/health-check.sh

echo "Deployment update completed successfully."
```

### Log Rotation

```bash
# Configure logrotate
sudo tee /etc/logrotate.d/tiger-mcp << EOF
/opt/tiger-mcp/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 tiger tiger
    postrotate
        docker-compose -f /opt/tiger-mcp/docker-compose.prod.yml kill -s USR1 mcp-server dashboard-api
    endscript
}
EOF
```

### Emergency Procedures

#### Service Recovery
```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Check for issues
docker system prune -f
docker volume ls

# Restore from backup if needed
zcat /opt/backups/tiger-mcp/tiger_mcp_backup_YYYYMMDD_HHMMSS.sql.gz | \
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U tiger_prod -d tiger_mcp_prod

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

#### Rollback Procedure
```bash
# Rollback to previous version
git checkout PREVIOUS_COMMIT
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# If database rollback needed
# 1. Stop services
# 2. Restore database backup
# 3. Restart services
```

## Performance Optimization

### Database Performance

```sql
-- Add to PostgreSQL configuration
-- postgresql.conf optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

### Application Performance

```bash
# Monitor performance
docker stats

# Check resource usage
docker-compose -f docker-compose.prod.yml exec mcp-server top
docker-compose -f docker-compose.prod.yml logs --tail=100 -f
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Check process pool settings
   - Monitor database connections
   - Review application logs

2. **Database Connection Issues**
   - Verify connection limits
   - Check authentication
   - Monitor connection pool

3. **SSL Certificate Issues**
   - Verify certificate expiration
   - Check certificate chain
   - Test with SSL Labs

4. **Performance Issues**
   - Monitor API response times
   - Check database query performance
   - Review resource utilization

This production deployment guide ensures a secure, monitored, and maintainable Tiger MCP system ready for enterprise use.