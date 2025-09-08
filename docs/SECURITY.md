# 🔐 Tiger MCP Security Guide

## 🛡️ **Security Architecture**

### Multi-Layer Security
- **Transport Layer**: TLS 1.3 encryption for all communications
- **Authentication**: JWT tokens with configurable expiration
- **Authorization**: Role-based access control with account-specific permissions
- **Data Protection**: AES-256-GCM encryption for sensitive credentials
- **Audit Trail**: Comprehensive security event logging

### API Key Management
- **Scoped Access**: API keys restricted to specific accounts
- **Permission Control**: Read-only vs trading permissions
- **Token Rotation**: Support for key rotation without downtime
- **Rate Limiting**: Protection against abuse and excessive usage

## 🔒 **Sensitive Files Protection**

### Files NEVER Committed to Git
```bash
# Tiger API credentials (contains private keys and tokens)
tiger_openapi_config.properties
tiger_openapi_token.properties
tiger_openapi_config.properties.*
tiger_openapi_token.properties.*

# Server configuration (contains API keys and account mappings)  
config/tiger_accounts.json
.mcp.json

# Environment files
.env
.env.local
.env.production
```

### Safe Example Files (Committed)
```bash
# Template files for user configuration
tiger_openapi_config.properties.example
tiger_openapi_token.properties.example
config/tiger_accounts.json.example
.mcp.json.example
```

## 🎯 **Security Best Practices**

### For Server Administrators
1. **Credential Management**
   - Store Tiger API credentials securely
   - Use separate credentials for different environments
   - Enable two-factor authentication on Tiger accounts

2. **API Key Distribution**
   - Generate unique API keys for each client
   - Implement key expiration and rotation
   - Monitor API usage and detect anomalies

3. **Network Security**
   - Run server behind firewall
   - Use HTTPS for external connections
   - Implement IP whitelisting for production

### For Client Users
1. **Account Security**
   - Use demo accounts for testing
   - Set trading limits and stop losses
   - Monitor account activity regularly

2. **API Key Safety**
   - Never share API keys in code or logs
   - Store keys in secure environment variables
   - Rotate keys periodically

3. **Trading Safeguards**
   - Start with small position sizes
   - Test strategies thoroughly in demo environment
   - Implement circuit breakers and risk limits

## 🚨 **Security Incident Response**

### Token Compromise
1. Immediately rotate affected API keys
2. Review audit logs for unauthorized access
3. Reset Tiger API credentials if necessary
4. Notify affected users

### Unauthorized Trading
1. Disable affected accounts immediately
2. Review all recent transactions
3. Implement additional authentication layers
4. Update security policies

## 📋 **Security Checklist**

### Pre-Production
- [ ] All sensitive files added to `.gitignore`
- [ ] Example configurations created with placeholder values
- [ ] API keys generated and distributed securely
- [ ] Rate limiting configured appropriately
- [ ] Audit logging enabled and tested

### Production Deployment
- [ ] Server deployed behind firewall
- [ ] HTTPS enabled with valid certificates
- [ ] Database credentials encrypted
- [ ] Backup and disaster recovery tested
- [ ] Security monitoring and alerting configured

### Ongoing Maintenance
- [ ] Regular security audits and penetration testing
- [ ] API key rotation schedule implemented  
- [ ] Security patches applied promptly
- [ ] User access reviews conducted quarterly
- [ ] Incident response procedures tested

---

## 🔍 **Security Reporting**

Report security vulnerabilities to: [security@your-domain.com](mailto:security@your-domain.com)

**We take security seriously and will respond to all reports within 24 hours.**