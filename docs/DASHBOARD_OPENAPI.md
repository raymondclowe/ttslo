# Dashboard OpenAPI Endpoints - Usage Guide

This document demonstrates how to use the new OpenAPI-related endpoints added to the TTSLO dashboard.

## New Endpoints

### 1. `/openapi.json` - OpenAPI Specification

Get the complete OpenAPI 3.0 specification for API discovery and integration.

**Example:**
```bash
curl http://localhost:5000/openapi.json | jq '.'
```

**Response:**
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "TTSLO Dashboard API",
    "version": "1.0.0",
    ...
  },
  "paths": {
    "/health": { ... },
    "/backup": { ... },
    "/api/status": { ... },
    ...
  }
}
```

**Use Cases:**
- Generate client SDKs using tools like OpenAPI Generator
- Import into API testing tools (Postman, Insomnia, Swagger UI)
- Auto-generate documentation
- Validate API responses against schemas

### 2. `/health` - Health Check Endpoint

Check if the dashboard service is healthy and operational.

**Example:**
```bash
curl http://localhost:5000/health
```

**Response (Healthy - HTTP 200):**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-23T04:48:43.596934+00:00",
  "checks": {
    "config_file": true,
    "kraken_api": true
  }
}
```

**Response (Unhealthy - HTTP 503):**
```json
{
  "status": "unhealthy",
  "timestamp": "2025-10-23T04:48:43.596934+00:00",
  "checks": {
    "config_file": false,
    "kraken_api": true
  }
}
```

**Use Cases:**
- Kubernetes liveness/readiness probes
- Load balancer health checks
- Monitoring systems (Prometheus, Grafana)
- Alerting on service degradation

**Example with monitoring:**
```bash
# Check health every 30 seconds
while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
  if [ "$STATUS" != "200" ]; then
    echo "ALERT: Dashboard unhealthy (HTTP $STATUS)"
  fi
  sleep 30
done
```

### 3. `/backup` - Download Backup Archive

Download a complete backup of all configuration and data files as a zip archive.

**Example:**
```bash
curl http://localhost:5000/backup -o ttslo-backup.zip
```

**Backup Contents:**
- `config.csv` - Configuration file (if exists)
- `state.csv` - State file (if exists)
- `logs.csv` - Log file (if exists)
- `.env` - Environment variables with credentials (if exists)
- `notifications.ini` - Notification configuration (if exists)
- `backup_manifest.json` - Metadata about the backup

**Manifest Example:**
```json
{
  "backup_time": "2025-10-23T04:48:11.810419+00:00",
  "files_included": [
    "config.csv",
    "state.csv",
    "logs.csv",
    ".env",
    "notifications.ini"
  ]
}
```

**Use Cases:**
- Regular automated backups via cron
- Pre-upgrade backups
- System migration/recovery
- Disaster recovery planning

**Example automated backup:**
```bash
#!/bin/bash
# Save to scripts/backup_ttslo.sh

BACKUP_DIR="/var/backups/ttslo"
DATE=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"

curl -s http://localhost:5000/backup -o "$BACKUP_DIR/ttslo-backup-$DATE.zip"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "ttslo-backup-*.zip" -mtime +30 -delete

echo "Backup saved to $BACKUP_DIR/ttslo-backup-$DATE.zip"
```

**Example cron job:**
```cron
# Run daily backup at 2 AM
0 2 * * * /home/user/scripts/backup_ttslo.sh
```

## Integration Examples

### Using with Swagger UI

You can view and interact with the API using Swagger UI:

1. Start Swagger UI Docker container:
```bash
docker run -p 8080:8080 -e SWAGGER_JSON=/openapi.json \
  -v $(pwd)/openapi.json:/openapi.json \
  swaggerapi/swagger-ui
```

2. Open http://localhost:8080 in your browser

### Generating Python Client

Generate a Python client SDK:

```bash
# Install OpenAPI Generator
npm install -g @openapitools/openapi-generator-cli

# Generate Python client
openapi-generator-cli generate \
  -i http://localhost:5000/openapi.json \
  -g python \
  -o ./ttslo-client-python
```

### Generating TypeScript Client

Generate a TypeScript/JavaScript client:

```bash
openapi-generator-cli generate \
  -i http://localhost:5000/openapi.json \
  -g typescript-axios \
  -o ./ttslo-client-ts
```

## Testing the Endpoints

Run the test suite:

```bash
# Test all dashboard endpoints including new ones
uv run pytest tests/test_dashboard_openapi.py -v

# Test all dashboard tests
uv run pytest tests/test_dashboard*.py -v
```

## Security Considerations

### Backup Endpoint Security

The `/backup` endpoint includes sensitive files like `.env` which may contain API credentials. Recommendations:

1. **Local Access Only**: Run dashboard on localhost or restrict via firewall
2. **Authentication**: Consider adding authentication if exposing to network
3. **HTTPS**: Use HTTPS in production to encrypt backup downloads
4. **Access Logs**: Monitor access to /backup endpoint

**Example firewall rules:**
```bash
# Allow only local subnet to access dashboard
sudo ufw allow from 192.168.1.0/24 to any port 5000
sudo ufw deny 5000
```

### Health Endpoint

The health endpoint is safe to expose as it only returns boolean status checks, no sensitive data.

## Troubleshooting

### Empty Backup

If backup is empty or missing files:
- Check that config.csv, state.csv, etc. exist in the working directory
- Verify file permissions allow dashboard to read files
- Check dashboard logs for errors

### Health Check Always Unhealthy

If health endpoint returns 503:
- Check if config.csv exists (`config_file` check)
- Verify Kraken API credentials are set (`kraken_api` check)
- Review dashboard startup logs

### OpenAPI Spec Not Loading

If `/openapi.json` returns 404:
- Ensure openapi.json file exists in dashboard directory
- Check file permissions
- Restart dashboard service

## Additional Resources

- [OpenAPI Specification](https://swagger.io/specification/)
- [OpenAPI Generator](https://openapi-generator.tech/)
- [Swagger UI](https://swagger.io/tools/swagger-ui/)
- [TTSLO Documentation](../README.md)
