# Tiger MCP + Claude Code: Security & Best Practices

Comprehensive security guidelines for safely integrating Tiger MCP server with Claude Code for trading operations.

## Table of Contents

1. [Security Overview](#security-overview)
2. [Credential Management](#credential-management)
3. [Network Security](#network-security)
4. [Access Control](#access-control)
5. [Trading Safety](#trading-safety)
6. [Monitoring & Auditing](#monitoring--auditing)
7. [Production Security](#production-security)
8. [Incident Response](#incident-response)

## Security Overview

### Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Minimal necessary permissions and access
3. **Zero Trust**: Verify everything, trust nothing
4. **Fail Secure**: Default to secure state on failure
5. **Continuous Monitoring**: Real-time security monitoring

### Risk Assessment

| Risk Level | Impact | Examples | Mitigation Priority |
|------------|---------|----------|-------------------|
| **Critical** | Financial Loss | Unauthorized trading, account compromise | Immediate |
| **High** | Data Breach | API key exposure, credential theft | 24 hours |
| **Medium** | Service Disruption | Connection failures, rate limiting | 7 days |
| **Low** | Information Disclosure | Log data exposure, metadata leaks | 30 days |

## Credential Management

### API Key Security

#### 1. Secure Storage

```bash
# ✅ SECURE: Use environment variables
export TIGER_CLIENT_ID="your_client_id"
export TIGER_PRIVATE_KEY="$(cat ~/.tiger/private_key.pem)"

# ✅ SECURE: Use encrypted configuration files
gpg -c tiger-credentials.env
export TIGER_CONFIG_FILE="tiger-credentials.env.gpg"

# ❌ INSECURE: Never in code or config files
TIGER_CLIENT_ID=abc123  # DON'T DO THIS
```

#### 2. Private Key Protection

```bash
# Set strict file permissions
chmod 600 ~/.tiger/private_key.pem
chown $USER:$USER ~/.tiger/private_key.pem

# Verify permissions
ls -la ~/.tiger/private_key.pem
# Should show: -rw------- 1 user user

# Store in secure directory
mkdir -p ~/.tiger
chmod 700 ~/.tiger
```

#### 3. Key Rotation Schedule

```bash
# Monthly key rotation (automated)
#!/bin/bash
# rotate-tiger-keys.sh

# Generate new key pair
tiger-cli generate-keys --output ~/.tiger/new_key.pem

# Test new keys in sandbox
export TIGER_PRIVATE_KEY="$(cat ~/.tiger/new_key.pem)"
export TIGER_SANDBOX=true
claude -p "Test connection with new keys"

# If successful, replace old keys
mv ~/.tiger/new_key.pem ~/.tiger/private_key.pem

# Update MCP server configuration
claude mcp remove tiger-trading
claude mcp add tiger-trading --env TIGER_PRIVATE_KEY="$(cat ~/.tiger/private_key.pem)" ...
```

### Environment Variable Security

#### Production Environment Setup

```bash
# Use secure secret management
# Option 1: HashiCorp Vault
vault kv get -field=private_key secret/tiger/credentials
vault kv get -field=client_id secret/tiger/credentials

# Option 2: AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id tiger/api-credentials

# Option 3: Azure Key Vault
az keyvault secret show --vault-name tiger-vault --name private-key

# Option 4: Docker Secrets
echo "your_private_key" | docker secret create tiger_private_key -
```

#### Environment Isolation

```bash
# Development Environment
export TIGER_SANDBOX=true
export TIGER_CLIENT_ID="dev_client_id"
export TIGER_ACCOUNT="dev_account"

# Staging Environment  
export TIGER_SANDBOX=true
export TIGER_CLIENT_ID="staging_client_id"
export TIGER_ACCOUNT="staging_account"

# Production Environment
export TIGER_SANDBOX=false
export TIGER_CLIENT_ID="prod_client_id"
export TIGER_ACCOUNT="prod_account"
```

## Network Security

### TLS/SSL Configuration

```python
# In MCP server configuration
import ssl

# Force TLS 1.2+ for all connections
ssl_context = ssl.create_default_context()
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED
```

### Certificate Pinning

```bash
# Pin Tiger Brokers API certificates
export TIGER_CA_BUNDLE="/path/to/tiger-ca-certificates.pem"
export REQUESTS_CA_BUNDLE="/path/to/tiger-ca-certificates.pem"

# Verify certificate chain
openssl s_client -connect api.tiger.com:443 -servername api.tiger.com
```

### Network Monitoring

```bash
# Monitor API traffic
tcpdump -i any -w tiger-api-traffic.pcap host api.tiger.com

# Analyze SSL/TLS connections
sslyze --regular api.tiger.com:443

# Check for suspicious connections
netstat -an | grep :443 | grep api.tiger.com
```

### Firewall Configuration

```bash
# Allow only necessary connections
# Outbound to Tiger API
iptables -A OUTPUT -d api.tiger.com -p tcp --dport 443 -j ACCEPT

# Block all other trading-related domains
iptables -A OUTPUT -d trading-competitors.com -j REJECT

# Log all financial API connections
iptables -A OUTPUT -p tcp --dport 443 -j LOG --log-prefix "HTTPS-OUT: "
```

## Access Control

### MCP Server Access Control

#### Tool-Level Permissions

```json
{
  "permissions": {
    "allow": [
      "mcp__tiger-trading__get_account_info",
      "mcp__tiger-trading__get_portfolio",
      "mcp__tiger-trading__get_market_data"
    ],
    "deny": [
      "mcp__tiger-trading__place_order",
      "mcp__tiger-trading__cancel_order"
    ]
  }
}
```

#### Role-Based Access Control

```bash
# Read-only analyst role
claude config set permissions.trading.read_only true
claude config set permissions.trading.place_orders false

# Day trader role
claude config set permissions.trading.max_order_size 1000
claude config set permissions.trading.max_daily_volume 10000

# Portfolio manager role
claude config set permissions.trading.max_order_size 10000
claude config set permissions.trading.require_approval true
```

### Session Management

```bash
# Session timeout configuration
export CLAUDE_SESSION_TIMEOUT=1800  # 30 minutes
export TIGER_API_TIMEOUT=300        # 5 minutes

# Automatic session cleanup
#!/bin/bash
# cleanup-sessions.sh
find ~/.claude/sessions -name "*.session" -mtime +1 -delete
pkill -f "tiger-mcp-server" -USR1  # Graceful reload
```

### Multi-User Access

```yaml
# tiger-mcp-rbac.yaml
users:
  - name: "trader1"
    permissions:
      - "read_market_data"
      - "view_portfolio"
      - "place_small_orders"  # < $1000
    accounts: ["sandbox_account_1"]
  
  - name: "analyst1" 
    permissions:
      - "read_market_data"
      - "view_portfolio"
      - "generate_reports"
    accounts: ["all_read_only"]
  
  - name: "portfolio_manager"
    permissions:
      - "all_trading_operations"
    accounts: ["production_accounts"]
    approval_required: true
```

## Trading Safety

### Order Validation

```python
# Pre-trade risk checks
def validate_order(order):
    checks = {
        'position_limit': order.quantity <= MAX_POSITION_SIZE,
        'daily_volume': get_daily_volume() + order.value <= DAILY_LIMIT,
        'account_balance': get_account_balance() >= order.value * 1.1,
        'symbol_allowed': order.symbol in ALLOWED_SYMBOLS,
        'market_hours': is_market_open(),
        'price_reasonable': is_price_within_range(order.symbol, order.price)
    }
    
    if not all(checks.values()):
        raise OrderValidationError(f"Failed checks: {checks}")
```

#### Trading Limits

```bash
# Configure trading limits
export TIGER_MAX_ORDER_SIZE=5000
export TIGER_MAX_DAILY_VOLUME=50000
export TIGER_MAX_POSITION_CONCENTRATION=0.1  # 10% of portfolio
export TIGER_STOP_LOSS_REQUIRED=true
export TIGER_MAX_LEVERAGE=2.0
```

#### Circuit Breakers

```python
# Implement circuit breakers
class TradingCircuitBreaker:
    def __init__(self):
        self.daily_loss_limit = 5000
        self.consecutive_loss_limit = 3
        self.rapid_trading_threshold = 10  # orders per minute
        
    def check_circuit_breaker(self):
        if self.get_daily_pnl() < -self.daily_loss_limit:
            self.halt_trading("Daily loss limit exceeded")
            
        if self.get_consecutive_losses() >= self.consecutive_loss_limit:
            self.halt_trading("Consecutive loss limit exceeded")
            
        if self.get_orders_per_minute() > self.rapid_trading_threshold:
            self.halt_trading("Rapid trading detected")
```

### Sandbox Testing Requirements

```bash
# Always test in sandbox first
export TIGER_SANDBOX=true

# Comprehensive testing checklist
claude -p "Run comprehensive trading system test:
1. Validate all credentials
2. Test market data retrieval
3. Test portfolio access
4. Test order placement (sandbox)
5. Test order cancellation
6. Test error handling
7. Test connection recovery
8. Generate test report"

# Only enable production after full validation
if [ "$SANDBOX_TESTS_PASSED" = "true" ]; then
    export TIGER_SANDBOX=false
    echo "✅ Production mode enabled"
else
    echo "❌ Sandbox tests must pass first"
    exit 1
fi
```

## Monitoring & Auditing

### Audit Logging

```python
# Comprehensive audit trail
import logging
import json
from datetime import datetime

def audit_log(action, user, details):
    audit_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'user': user,
        'details': details,
        'session_id': get_session_id(),
        'ip_address': get_client_ip(),
        'tiger_account': get_tiger_account()
    }
    
    # Log to secure audit file
    with open('/var/log/tiger-mcp/audit.log', 'a') as f:
        f.write(json.dumps(audit_entry) + '\n')
    
    # Send to SIEM system
    send_to_siem(audit_entry)
```

#### Critical Events to Log

```python
# Security events
SECURITY_EVENTS = [
    'authentication_success',
    'authentication_failure', 
    'unauthorized_access_attempt',
    'privilege_escalation_attempt',
    'configuration_change',
    'api_key_rotation'
]

# Trading events  
TRADING_EVENTS = [
    'order_placed',
    'order_cancelled', 
    'order_filled',
    'position_opened',
    'position_closed',
    'stop_loss_triggered',
    'trading_halt_activated'
]

# System events
SYSTEM_EVENTS = [
    'server_startup',
    'server_shutdown',
    'connection_established',
    'connection_lost',
    'error_occurred',
    'backup_completed'
]
```

### Real-time Monitoring

```bash
# Set up monitoring alerts
# Prometheus + Grafana configuration
cat > tiger-mcp-alerts.yml << EOF
groups:
- name: tiger-mcp.rules
  rules:
  - alert: TigerAPIConnectionLost
    expr: tiger_api_connection_status == 0
    for: 30s
    annotations:
      summary: "Tiger API connection lost"
      
  - alert: UnauthorizedTradingAttempt  
    expr: increase(tiger_unauthorized_trades_total[5m]) > 0
    annotations:
      summary: "Unauthorized trading attempt detected"
      
  - alert: DailyLossLimitApproached
    expr: tiger_daily_pnl < -4500
    annotations:
      summary: "Daily loss limit approaching"
EOF
```

### Performance Monitoring

```python
# Monitor API performance
import time
import psutil
from prometheus_client import Counter, Histogram, Gauge

# Metrics collection
api_requests_total = Counter('tiger_api_requests_total', 'Total API requests', ['method', 'status'])
api_request_duration = Histogram('tiger_api_request_duration_seconds', 'API request duration')
account_balance = Gauge('tiger_account_balance_usd', 'Account balance in USD')
daily_pnl = Gauge('tiger_daily_pnl_usd', 'Daily P&L in USD')
cpu_usage = Gauge('tiger_mcp_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('tiger_mcp_memory_usage_bytes', 'Memory usage in bytes')

# Update metrics
def update_system_metrics():
    cpu_usage.set(psutil.cpu_percent())
    memory_usage.set(psutil.virtual_memory().used)
```

## Production Security

### Infrastructure Hardening

#### Server Configuration

```bash
# Disable unnecessary services
systemctl disable nginx  # If not using web dashboard
systemctl disable ssh    # If not needed for remote access

# Configure firewall
ufw enable
ufw default deny incoming
ufw allow out 443  # HTTPS to Tiger API only
ufw allow in 22 from 192.168.1.0/24  # SSH from trusted network only

# Secure kernel parameters
echo "net.ipv4.conf.all.send_redirects = 0" >> /etc/sysctl.conf
echo "net.ipv4.conf.all.accept_redirects = 0" >> /etc/sysctl.conf
echo "net.ipv4.conf.all.accept_source_route = 0" >> /etc/sysctl.conf
sysctl -p
```

#### Container Security (Docker)

```dockerfile
# Use minimal base image
FROM python:3.11-alpine

# Create non-root user
RUN adduser -D -s /bin/sh tiger-mcp
USER tiger-mcp

# Set secure permissions
COPY --chown=tiger-mcp:tiger-mcp mcp-server/ /app/
WORKDIR /app

# Remove shell access
RUN rm /bin/sh /bin/bash || true

# Use read-only filesystem
VOLUME ["/app/data"]
```

```yaml
# docker-compose.yml security settings
version: '3.8'
services:
  tiger-mcp:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETUID
      - SETGID
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
```

### Backup and Recovery

#### Secure Backup Strategy

```bash
#!/bin/bash
# secure-backup.sh

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/secure/backups/tiger-mcp"

# Create encrypted backup
tar czf - \
  ~/.claude/mcp-servers/ \
  ~/.tiger/config/ \
  /var/log/tiger-mcp/ \
| gpg --cipher-algo AES256 --compress-algo 1 --symmetric \
  --output "${BACKUP_DIR}/tiger-mcp-${BACKUP_DATE}.tar.gz.gpg"

# Verify backup
gpg --decrypt "${BACKUP_DIR}/tiger-mcp-${BACKUP_DATE}.tar.gz.gpg" \
| tar tzf - > /dev/null && echo "✅ Backup verified"

# Upload to secure cloud storage (optional)
aws s3 cp "${BACKUP_DIR}/tiger-mcp-${BACKUP_DATE}.tar.gz.gpg" \
  s3://secure-backup-bucket/tiger-mcp/ \
  --server-side-encryption AES256
```

#### Disaster Recovery Plan

```bash
#!/bin/bash
# disaster-recovery.sh

# 1. Secure credentials from backup
gpg --decrypt tiger-credentials-backup.gpg > /tmp/credentials.env

# 2. Restore MCP server configuration
claude mcp add tiger-trading-recovery \
  --env "$(cat /tmp/credentials.env)" \
  /path/to/tiger-mcp/server.py

# 3. Validate restoration
claude -p "Validate Tiger MCP recovery and test all critical functions"

# 4. Clean up temporary files
shred -vfz /tmp/credentials.env
```

## Incident Response

### Security Incident Categories

| Severity | Examples | Response Time | Actions |
|----------|----------|---------------|---------|
| **Critical** | Unauthorized trading, credential theft | Immediate | Halt trading, rotate keys, investigate |
| **High** | API abuse, suspicious access patterns | 1 hour | Monitor closely, increase logging |
| **Medium** | Connection anomalies, rate limiting | 4 hours | Review and adjust configuration |
| **Low** | Log anomalies, minor errors | 24 hours | Document and monitor trends |

### Incident Response Playbook

#### 1. Unauthorized Trading Detected

```bash
# Immediate actions (< 5 minutes)
echo "🚨 SECURITY INCIDENT: Unauthorized trading detected"

# Halt all trading operations
export TIGER_TRADING_HALTED=true
pkill -f "tiger-mcp-server"

# Disable API access
claude mcp remove tiger-trading

# Capture evidence
cp /var/log/tiger-mcp/audit.log /tmp/incident-$(date +%Y%m%d-%H%M%S).log
netstat -an > /tmp/network-connections-$(date +%Y%m%d-%H%M%S).txt

# Notify incident response team
echo "Unauthorized trading detected at $(date)" | \
mail -s "CRITICAL: Tiger MCP Security Incident" security@company.com
```

#### 2. API Credential Compromise

```bash
# Immediate actions (< 10 minutes)
echo "🔑 CREDENTIAL COMPROMISE: Rotating all API keys"

# Revoke current API keys at Tiger Brokers
# (Manual action required in Tiger console)

# Generate new credentials
tiger-cli generate-keys --emergency --output /secure/new-credentials/

# Update MCP server with new credentials
claude mcp remove tiger-trading
claude mcp add tiger-trading --env TIGER_PRIVATE_KEY="$(cat /secure/new-credentials/private_key.pem)" ...

# Update monitoring
echo "API_CREDENTIAL_ROTATION_$(date +%s)" >> /var/log/tiger-mcp/security-events.log
```

#### 3. System Compromise Investigation

```bash
#!/bin/bash
# incident-investigation.sh

INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"
EVIDENCE_DIR="/tmp/incident-${INCIDENT_ID}"
mkdir -p $EVIDENCE_DIR

echo "🔍 Starting security investigation: $INCIDENT_ID"

# Collect system information
ps aux > $EVIDENCE_DIR/processes.txt
netstat -an > $EVIDENCE_DIR/network.txt  
lsof > $EVIDENCE_DIR/open-files.txt
last -50 > $EVIDENCE_DIR/login-history.txt

# Collect Tiger MCP specific evidence
cp /var/log/tiger-mcp/* $EVIDENCE_DIR/
docker logs tiger-mcp-server > $EVIDENCE_DIR/docker-logs.txt

# Collect Claude Code logs
cp ~/.claude/logs/* $EVIDENCE_DIR/

# Check for indicators of compromise
grep -i "unauthorized\|breach\|compromise\|attack" /var/log/tiger-mcp/audit.log > $EVIDENCE_DIR/security-alerts.txt

# Create incident report
cat > $EVIDENCE_DIR/incident-report.md << EOF
# Security Incident Report: $INCIDENT_ID

## Timeline
- **Detection Time**: $(date)
- **Response Started**: $(date)
- **Evidence Collected**: $(date)

## Systems Affected
- Tiger MCP Server
- Claude Code Integration
- Tiger Brokers API Access

## Evidence Collection
$(ls -la $EVIDENCE_DIR)

## Next Steps
1. Analyze collected evidence
2. Determine root cause
3. Implement additional safeguards
4. Update incident response procedures
EOF

echo "✅ Evidence collection complete: $EVIDENCE_DIR"
```

### Post-Incident Actions

#### Security Review Checklist

- [ ] **Root Cause Analysis**: Identify how the incident occurred
- [ ] **Impact Assessment**: Determine scope of compromise
- [ ] **Timeline Reconstruction**: Create detailed incident timeline
- [ ] **Evidence Preservation**: Secure all evidence for potential legal needs
- [ ] **Stakeholder Notification**: Inform relevant parties
- [ ] **Remediation Implementation**: Fix identified vulnerabilities
- [ ] **Monitoring Enhancement**: Improve detection capabilities
- [ ] **Documentation Update**: Update security procedures
- [ ] **Training Review**: Address any training gaps
- [ ] **Insurance Notification**: Contact cyber insurance provider if applicable

## Compliance and Regulatory

### Financial Regulations

#### Record Keeping Requirements

```python
# Maintain detailed trading records per regulations
class TradingRecord:
    def __init__(self):
        self.required_fields = {
            'timestamp': 'ISO 8601 format',
            'account_id': 'Tiger account identifier',
            'symbol': 'Security symbol',
            'action': 'BUY/SELL',
            'quantity': 'Number of shares',
            'price': 'Execution price',
            'order_id': 'Unique order identifier',
            'user_id': 'Claude Code user',
            'ip_address': 'Client IP address',
            'session_id': 'Session identifier'
        }
    
    def validate_record(self, record):
        for field in self.required_fields:
            if field not in record:
                raise ComplianceError(f"Missing required field: {field}")
```

#### Audit Trail Integrity

```bash
# Tamper-evident logging with cryptographic signatures
#!/bin/bash
# secure-logging.sh

LOG_FILE="/var/log/tiger-mcp/audit.log"
SIGNATURE_FILE="/var/log/tiger-mcp/audit.log.sig"

# Sign new log entries
tail -n 1 $LOG_FILE | openssl dgst -sha256 -sign /secure/log-signing-key.pem \
  -out $SIGNATURE_FILE

# Verify log integrity
openssl dgst -sha256 -verify /secure/log-verification-key.pub \
  -signature $SIGNATURE_FILE $LOG_FILE

if [ $? -eq 0 ]; then
    echo "✅ Log integrity verified"
else
    echo "❌ Log integrity check FAILED - possible tampering detected"
    # Trigger security alert
fi
```

---

## Security Checklist Summary

### ✅ Pre-Production Checklist

- [ ] All credentials stored securely (not in code/logs)
- [ ] Private keys have proper file permissions (600)
- [ ] Network traffic uses HTTPS only
- [ ] Audit logging enabled and tested
- [ ] Trading limits configured and tested
- [ ] Circuit breakers implemented and tested
- [ ] Backup and recovery procedures tested
- [ ] Incident response plan documented and tested
- [ ] Security monitoring and alerting configured
- [ ] All tests passing in sandbox environment
- [ ] Security review completed by qualified personnel
- [ ] Documentation updated and version controlled

### 🔄 Ongoing Security Tasks

#### Daily
- Review audit logs for anomalies
- Verify system health and connectivity
- Check trading limit compliance

#### Weekly  
- Review security alerts and false positives
- Update threat intelligence feeds
- Backup configuration and credentials

#### Monthly
- Rotate API keys and certificates
- Review and update security policies
- Conduct security awareness training
- Test incident response procedures

#### Quarterly
- Comprehensive security audit
- Penetration testing
- Update risk assessment
- Review and update disaster recovery plans

Remember: Security is an ongoing process, not a one-time setup. Stay vigilant and keep your systems updated!