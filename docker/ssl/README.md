# SSL Certificates for Tiger MCP

This directory contains SSL certificates for the Tiger MCP system.

## Development Setup

For development, you can generate self-signed certificates:

```bash
# Generate self-signed certificate for development
openssl req -x509 -newkey rsa:4096 -nodes \
  -out server.crt \
  -keyout server.key \
  -days 365 \
  -subj "/CN=localhost"

# Set secure permissions
chmod 600 server.key
chmod 644 server.crt
```

## Production Setup

For production, you should use certificates from a trusted Certificate Authority:

1. **Let's Encrypt** (recommended for public domains):
   ```bash
   # Install certbot
   sudo apt-get install certbot
   
   # Generate certificate
   sudo certbot certonly --standalone -d yourdomain.com
   
   # Copy certificates
   sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem server.crt
   sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem server.key
   sudo chown $(id -u):$(id -g) server.*
   chmod 644 server.crt
   chmod 600 server.key
   ```

2. **Commercial CA**:
   - Purchase SSL certificate from a trusted CA
   - Copy the certificate and private key to this directory
   - Ensure proper permissions (644 for .crt, 600 for .key)

3. **Internal CA**:
   - Use your organization's internal Certificate Authority
   - Copy the issued certificate and private key
   - Include the CA certificate if needed

## File Structure

Expected files in this directory:

- `server.crt` - SSL certificate (public key)
- `server.key` - SSL private key (**keep secure!**)
- `ca.crt` - Certificate Authority certificate (optional)

## Security Notes

1. **Never commit private keys to version control**
2. **Use proper file permissions**:
   ```bash
   chmod 644 *.crt
   chmod 600 *.key
   ```
3. **Regularly rotate certificates**
4. **Use strong cipher suites** (configured in nginx.conf)
5. **Monitor certificate expiration**

## Testing SSL Configuration

```bash
# Test SSL certificate
openssl x509 -in server.crt -text -noout

# Test SSL connection
openssl s_client -connect localhost:443 -servername localhost

# Check certificate expiration
openssl x509 -in server.crt -noout -dates
```

## Nginx SSL Configuration

The nginx configuration in `../nginx/nginx.conf` includes:

- Modern SSL protocols (TLSv1.2, TLSv1.3)
- Strong cipher suites
- HSTS headers
- Perfect Forward Secrecy
- OCSP stapling (if configured)