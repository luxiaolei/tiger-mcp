# Docker Secrets for Tiger MCP

This directory contains Docker secrets for production deployment. **Never commit actual secret files to version control.**

## Required Files

Create these files with secure values for production:

### `postgres_password.txt`
```bash
# Generate a secure PostgreSQL password
openssl rand -base64 32 > postgres_password.txt
```

### `redis_password.txt`
```bash
# Generate a secure Redis password
openssl rand -base64 32 > redis_password.txt
```

### `secret_key.txt`
```bash
# Generate a secure application secret key
openssl rand -base64 64 > secret_key.txt
```

### `tiger_private_key.pem`
```bash
# Copy your Tiger Brokers private key
cp /path/to/your/tiger_private_key.pem .
chmod 600 tiger_private_key.pem
```

## SSL Certificates (Optional)

If using custom SSL certificates, also create:

### `server.crt`
```bash
# Copy your SSL certificate
cp /path/to/your/server.crt ../docker/ssl/
```

### `server.key`
```bash
# Copy your SSL private key
cp /path/to/your/server.key ../docker/ssl/
chmod 600 ../docker/ssl/server.key
```

## Security Notes

1. **File Permissions**: Ensure secret files have restricted permissions:
   ```bash
   chmod 600 *.txt *.pem
   ```

2. **Gitignore**: The `.gitignore` file should exclude this directory:
   ```
   secrets/*.txt
   secrets/*.pem
   secrets/*.key
   secrets/*.crt
   ```

3. **Production**: Use a proper secrets management system (AWS Secrets Manager, HashiCorp Vault, etc.) in production.

4. **Rotation**: Regularly rotate all secrets and passwords.

## Quick Setup Script

```bash
#!/bin/bash
# Generate all required secrets

echo "Generating Docker secrets..."

# PostgreSQL password
openssl rand -base64 32 > postgres_password.txt
echo "✓ Generated postgres_password.txt"

# Redis password  
openssl rand -base64 32 > redis_password.txt
echo "✓ Generated redis_password.txt"

# Application secret key
openssl rand -base64 64 > secret_key.txt
echo "✓ Generated secret_key.txt"

# Set restrictive permissions
chmod 600 *.txt

echo "✓ Set secure file permissions"
echo ""
echo "⚠️  Still needed:"
echo "   - Copy your Tiger private key to tiger_private_key.pem"
echo "   - Configure SSL certificates if needed"
echo "   - Update production environment variables"
```