# Tiger MCP Troubleshooting Guide

Comprehensive troubleshooting guide for common issues, errors, and performance problems in the Tiger MCP system.

## 🚨 Emergency Quick Fixes

### System Down - Critical Services Not Responding

```bash
# Quick system restart
docker-compose down && docker-compose up -d

# Check service status
docker-compose ps
docker-compose logs --tail=50

# Health check all services
curl -f http://localhost:8000/health  # MCP Server
curl -f http://localhost:8001/health  # Dashboard API
```

### Database Connection Lost

```bash
# Restart database
docker-compose restart postgres

# Check database logs
docker-compose logs postgres | tail -50

# Test connection
docker-compose exec postgres pg_isready -U tiger_user -d tiger_mcp
```

### Tiger API Authentication Failed

```bash
# Check properties files exist
ls -la tiger_openapi_*.properties

# Verify token status
docker-compose exec mcp-server python -c "
from shared import get_token_manager
import asyncio
async def check_tokens():
    tm = get_token_manager()
    accounts = await tm.get_accounts_needing_refresh()
    for acc in accounts:
        print(f'Account {acc.account_number}: Token expires {acc.token_expires_at}')
asyncio.run(check_tokens())
"
```

## 🔍 Diagnostic Tools and Commands

### System Health Check

```bash
#!/bin/bash
# Create file: scripts/health-diagnostic.sh

echo "=== Tiger MCP System Diagnostic ==="
echo "Timestamp: $(date)"
echo

# Docker services
echo "🐳 Docker Services:"
docker-compose ps
echo

# System resources
echo "💻 System Resources:"
echo "Memory Usage:"
free -h
echo "Disk Usage:"
df -h | head -5
echo "CPU Load:"
uptime
echo

# Service logs (last 10 lines each)
echo "📋 Recent Logs:"
echo "--- MCP Server ---"
docker-compose logs --tail=10 mcp-server
echo "--- Dashboard API ---"
docker-compose logs --tail=10 dashboard-api
echo "--- Database ---"
docker-compose logs --tail=10 postgres
echo

# Network connectivity
echo "🌐 Network Tests:"
echo "Tiger API connectivity:"
timeout 10 curl -s -o /dev/null -w "%{http_code}" https://openapi.itiger.com/gateway || echo "Failed"
echo "Database connection:"
docker-compose exec postgres pg_isready -U tiger_user -d tiger_mcp || echo "Failed"
```

### Log Analysis Tools

```bash
# Real-time log monitoring with filtering
docker-compose logs -f | grep -E "(ERROR|CRITICAL|WARNING)"

# Find specific errors
docker-compose logs mcp-server | grep "tiger_api" | tail -20

# Database connection errors
docker-compose logs | grep -i "connection\|timeout\|refused"

# Performance issues
docker-compose logs | grep -E "(slow|timeout|latency)" | tail -20
```

## 🛠️ Common Issues and Solutions

### 1. Authentication and API Access Issues

#### Issue: "Tiger API authentication failed"
**Symptoms:**
- API calls returning 401 errors
- "Invalid credentials" messages
- Token refresh failures

**Diagnosis:**
```bash
# Check Tiger properties files
cat tiger_openapi_config.properties
ls -la tiger_openapi_*.properties

# Test token manually
docker-compose exec mcp-server python -c "
from shared.tiger_config import load_tiger_config_from_properties
config = load_tiger_config_from_properties()
print(f'Tiger ID: {config.tiger_id}')
print(f'Account: {config.account}')
print(f'License: {config.license}')
print(f'Environment: {config.environment}')
"
```

**Solutions:**
1. **Verify credentials:**
   ```bash
   # Re-download from Tiger website
   # Ensure tiger_id, account, and license are correct
   ```

2. **Check private key format:**
   ```bash
   # Key should start with -----BEGIN RSA PRIVATE KEY-----
   head -1 tiger_openapi_config.properties | grep "BEGIN RSA"
   ```

3. **Token refresh:**
   ```bash
   # Force token refresh
   docker-compose exec mcp-server python -c "
   from shared import get_token_manager, get_account_manager
   import asyncio
   async def refresh():
       am = get_account_manager()
       accounts = await am.list_accounts()
       if accounts:
           tm = get_token_manager()
           success, error = await tm.refresh_token(accounts[0])
           print(f'Refresh: {success}, Error: {error}')
   asyncio.run(refresh())
   "
   ```

#### Issue: "Account not found or access denied"
**Symptoms:**
- Account-specific API calls fail
- "No default account configured" errors

**Diagnosis:**
```bash
# List configured accounts
docker-compose exec mcp-server python -c "
from shared import get_account_manager
import asyncio
async def list_accounts():
    am = get_account_manager()
    accounts = await am.list_accounts()
    for acc in accounts:
        print(f'{acc.account_name}: {acc.account_number} ({acc.status})')
        print(f'  Default Trading: {acc.is_default_trading}')
        print(f'  Default Data: {acc.is_default_data}')
        print()
asyncio.run(list_accounts())
"
```

**Solutions:**
1. **Add account:**
   ```bash
   # Add account from properties
   docker-compose exec mcp-server python -c "
   from shared import get_account_manager
   import asyncio
   async def add_account():
       am = get_account_manager()
       account = await am.create_account_from_properties(
           account_name='Production Account',
           properties_path='.',
           is_default_trading=True,
           is_default_data=True
       )
       print(f'Added: {account.account_name} ({account.id})')
   asyncio.run(add_account())
   "
   ```

2. **Set default accounts:**
   ```bash
   # Set default trading account
   # Replace ACCOUNT_ID with actual UUID
   docker-compose exec mcp-server python -c "
   from shared import get_account_manager
   import asyncio
   async def set_default():
       am = get_account_manager()
       await am.set_default_trading_account('ACCOUNT_ID')
       await am.set_default_data_account('ACCOUNT_ID')
   asyncio.run(set_default())
   "
   ```

### 2. Database Issues

#### Issue: "Database connection refused"
**Symptoms:**
- Services fail to start
- "Connection refused" errors
- Database timeout errors

**Diagnosis:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres | tail -30

# Test connection manually
docker-compose exec postgres psql -U tiger_user -d tiger_mcp -c "SELECT version();"
```

**Solutions:**
1. **Restart database:**
   ```bash
   docker-compose restart postgres
   sleep 10
   docker-compose logs postgres | tail -20
   ```

2. **Check connection settings:**
   ```bash
   # Verify environment variables
   grep DATABASE_URL .env
   
   # Test with correct credentials
   docker-compose exec postgres psql -U tiger_user -d tiger_mcp -c "\dt"
   ```

3. **Reset database (⚠️ DESTRUCTIVE):**
   ```bash
   # This will delete all data
   docker-compose down -v
   docker-compose up -d postgres
   sleep 15
   docker-compose exec database python manage_db.py migrate
   ```

#### Issue: "Migration failed" or schema errors
**Symptoms:**
- Services start but database queries fail
- "Table does not exist" errors
- Schema version mismatches

**Diagnosis:**
```bash
# Check current database schema
docker-compose exec postgres psql -U tiger_user -d tiger_mcp -c "\dt"

# Check migration history
docker-compose exec database python manage_db.py history

# Check for pending migrations
docker-compose exec database python manage_db.py current
```

**Solutions:**
1. **Run migrations:**
   ```bash
   docker-compose exec database python manage_db.py migrate
   ```

2. **Reset and rebuild schema:**
   ```bash
   # Create backup first
   docker-compose exec postgres pg_dump -U tiger_user tiger_mcp > backup.sql
   
   # Reset and migrate
   docker-compose down -v
   docker-compose up -d postgres
   sleep 15
   docker-compose exec database python manage_db.py migrate
   ```

### 3. Performance Issues

#### Issue: High CPU or memory usage
**Symptoms:**
- System becomes slow or unresponsive
- Docker containers consuming excessive resources
- API response times increase

**Diagnosis:**
```bash
# Monitor resource usage
docker stats

# Check process pool status
docker-compose exec mcp-server python -c "
from mcp_server.process_manager import ProcessManager
pm = ProcessManager()
print(pm.get_pool_status())
"

# Find memory-intensive processes
docker-compose exec mcp-server top -b -n 1 | head -20
```

**Solutions:**
1. **Adjust process pool settings:**
   ```bash
   # In .env file:
   echo "MCP_PROCESS_MAX_WORKERS=4" >> .env
   echo "MCP_PROCESS_TARGET_WORKERS=2" >> .env
   docker-compose restart mcp-server
   ```

2. **Increase container resources:**
   ```yaml
   # In docker-compose.yml
   mcp-server:
     deploy:
       resources:
         limits:
           memory: 2G
           cpus: '2.0'
   ```

3. **Database optimization:**
   ```bash
   # Check slow queries
   docker-compose exec postgres psql -U tiger_user -d tiger_mcp -c "
   SELECT query, calls, total_time, mean_time 
   FROM pg_stat_statements 
   ORDER BY total_time DESC LIMIT 10;
   "
   ```

#### Issue: Slow API responses
**Symptoms:**
- API calls taking > 30 seconds
- Timeouts on client side
- High latency in logs

**Diagnosis:**
```bash
# Check API response times
time curl -s http://localhost:8000/health

# Monitor database connections
docker-compose exec postgres psql -U tiger_user -d tiger_mcp -c "
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
"

# Check for long-running queries
docker-compose exec postgres psql -U tiger_user -d tiger_mcp -c "
SELECT pid, state, query_start, query 
FROM pg_stat_activity 
WHERE state != 'idle' AND query_start < now() - interval '1 minute';
"
```

**Solutions:**
1. **Increase timeout settings:**
   ```bash
   # In .env file
   echo "TIGER_API_TIMEOUT=60" >> .env
   echo "DATABASE_TIMEOUT=30" >> .env
   ```

2. **Scale services:**
   ```yaml
   # In docker-compose.yml
   mcp-server:
     deploy:
       replicas: 2
   ```

3. **Database connection pooling:**
   ```bash
   echo "DB_POOL_SIZE=20" >> .env
   echo "DB_MAX_OVERFLOW=30" >> .env
   ```

### 4. Network and Connectivity Issues

#### Issue: "Cannot connect to Tiger API"
**Symptoms:**
- All Tiger API calls fail
- Network timeout errors
- Connection refused to Tiger servers

**Diagnosis:**
```bash
# Test Tiger API connectivity
curl -v https://openapi.itiger.com/gateway

# Check DNS resolution
nslookup openapi.itiger.com

# Test from container
docker-compose exec mcp-server curl -v https://openapi.itiger.com/gateway

# Check firewall/proxy settings
telnet openapi.itiger.com 443
```

**Solutions:**
1. **Check network configuration:**
   ```bash
   # Verify Docker network
   docker network ls
   docker network inspect tiger-mcp_default
   ```

2. **Configure proxy if needed:**
   ```bash
   # In .env file
   echo "HTTP_PROXY=http://proxy.company.com:8080" >> .env
   echo "HTTPS_PROXY=http://proxy.company.com:8080" >> .env
   ```

3. **Firewall rules:**
   ```bash
   # Allow outbound HTTPS
   sudo ufw allow out 443
   ```

### 5. Docker and Container Issues

#### Issue: "Container keeps restarting"
**Symptoms:**
- Services show "Restarting" status
- Containers exit immediately after start
- Resource exhaustion

**Diagnosis:**
```bash
# Check exit codes and restart history
docker-compose ps

# Check container logs for errors
docker-compose logs mcp-server | grep -E "(ERROR|CRITICAL|exit)"

# Check resource limits
docker stats --no-stream

# Inspect container configuration
docker inspect tiger-mcp_mcp-server_1
```

**Solutions:**
1. **Fix startup errors:**
   ```bash
   # Run container interactively to debug
   docker-compose run --rm mcp-server bash
   
   # Check Python import issues
   docker-compose run --rm mcp-server python -c "import mcp_server; print('OK')"
   ```

2. **Increase resource limits:**
   ```yaml
   # In docker-compose.yml
   services:
     mcp-server:
       deploy:
         resources:
           limits:
             memory: 2G
           reservations:
             memory: 512M
   ```

3. **Fix configuration issues:**
   ```bash
   # Validate configuration
   docker-compose config

   # Check environment variables
   docker-compose exec mcp-server env | grep TIGER
   ```

## 📊 Performance Monitoring

### Real-time Monitoring Setup

```bash
# Create monitoring script
cat > scripts/monitor.sh << 'EOF'
#!/bin/bash
echo "Tiger MCP Real-time Monitor"
echo "=========================="
while true; do
    clear
    echo "$(date) - System Status"
    echo
    
    echo "🐳 Docker Services:"
    docker-compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}"
    echo
    
    echo "💻 Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
    echo
    
    echo "📊 API Health:"
    curl -s -w "MCP Server: %{http_code} (%{time_total}s)\n" -o /dev/null http://localhost:8000/health
    curl -s -w "Dashboard: %{http_code} (%{time_total}s)\n" -o /dev/null http://localhost:8001/health
    echo
    
    echo "Press Ctrl+C to exit"
    sleep 5
done
EOF
chmod +x scripts/monitor.sh
```

### Log Analysis Scripts

```bash
# Error summary script
cat > scripts/error-summary.sh << 'EOF'
#!/bin/bash
echo "Tiger MCP Error Summary - Last 24 hours"
echo "======================================"

# Count errors by type
echo "Error Types:"
docker-compose logs --since 24h | grep -i error | awk '{print $NF}' | sort | uniq -c | sort -nr

echo
echo "Recent Critical Errors:"
docker-compose logs --since 24h | grep -i "critical\|fatal" | tail -10

echo
echo "Database Errors:"
docker-compose logs postgres --since 24h | grep -i "error\|fail" | tail -5

echo
echo "Tiger API Errors:"
docker-compose logs mcp-server --since 24h | grep -i "tiger.*error" | tail -5
EOF
chmod +x scripts/error-summary.sh
```

## 🔧 Maintenance Procedures

### Regular Maintenance Checklist

**Weekly:**
- [ ] Check disk space usage
- [ ] Review error logs
- [ ] Verify backup integrity
- [ ] Update Docker images
- [ ] Check SSL certificate expiry

**Monthly:**
- [ ] Database optimization and cleanup
- [ ] Security updates
- [ ] Performance metrics review
- [ ] Disaster recovery test
- [ ] Documentation updates

### Automated Maintenance Scripts

```bash
# Weekly maintenance script
cat > scripts/weekly-maintenance.sh << 'EOF'
#!/bin/bash
echo "Weekly Tiger MCP Maintenance"
echo "============================"

# Clean up Docker resources
echo "Cleaning Docker resources..."
docker system prune -f

# Backup database
echo "Creating database backup..."
docker-compose exec -T postgres pg_dump -U tiger_user tiger_mcp | gzip > "backups/weekly_$(date +%Y%m%d).sql.gz"

# Check disk space
echo "Checking disk space..."
df -h | grep -E '^/dev/' | awk '$5 >= 80 {print "Warning: " $0}'

# Update images
echo "Checking for image updates..."
docker-compose pull

# Health check
echo "Running health check..."
./scripts/health-diagnostic.sh

echo "Maintenance completed: $(date)"
EOF
chmod +x scripts/weekly-maintenance.sh
```

## 📞 Support and Escalation

### When to Escalate

**Immediate Escalation:**
- Production system completely down
- Data corruption detected
- Security breach suspected
- Financial data integrity issues

**Regular Support:**
- Performance degradation
- Configuration questions
- Feature requests
- Non-critical bugs

### Support Information Collection

When reporting issues, collect:

```bash
# System information
uname -a
docker version
docker-compose version

# Service status
docker-compose ps
docker-compose logs --tail=100

# System resources
free -h
df -h
top -b -n 1 | head -20

# Recent errors
./scripts/error-summary.sh

# Configuration (sanitized)
grep -v "PASSWORD\|SECRET\|KEY" .env
```

### Emergency Contacts

- **Tiger Brokers API Support**: [Tiger support channels]
- **System Administrator**: [Your system admin contact]
- **Development Team**: [Development team contact]

## 📚 Additional Resources

- **Tiger API Documentation**: https://www.itiger.com/openapi/docs
- **Docker Documentation**: https://docs.docker.com/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **System Monitoring Guide**: [Link to monitoring documentation]

---

*This troubleshooting guide is designed to help resolve 90% of common issues. For complex problems or system modifications, consult the development team.*