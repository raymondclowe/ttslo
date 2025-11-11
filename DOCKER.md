# Docker Multi-Instance Deployment

This repository supports running multiple ttslo instances in isolated Docker containers, each with its own configuration and Kraken API keys.

## Quick Start

```bash
# From project root
docker compose -f docker/docker-compose.yml up -d
```

Access dashboards:
- Instance 1: http://localhost:8001
- Instance 2: http://localhost:8002

## Files
- `docker/Dockerfile` - Container image definition
- `docker/entrypoint.sh` - Startup script
- `docker/docker-compose.yml` - Multi-instance configuration
- `docker/README.md` - Detailed documentation
- `instance1/`, `instance2/` - Per-instance data folders

## Configuration

Each instance requires 4 environment variables in `docker-compose.yml`:
- `KRAKEN_API_KEY` - Read-only API key
- `KRAKEN_API_SECRET` - Read-only API secret
- `KRAKEN_API_KEY_RW` - Read-write API key
- `KRAKEN_API_SECRET_RW` - Read-write API secret

Shared across all instances (set in `docker/.env`):
- `TELEGRAM_BOT_TOKEN` - Telegram bot token for notifications (optional)

Plus per-instance:
- `DASHBOARD_PORT` - Port for the dashboard (must match container port mapping)

## Key Commands

```bash
# Start all instances
docker compose -f docker/docker-compose.yml up -d

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Stop all instances
docker compose -f docker/docker-compose.yml down

# Rebuild after code changes
docker compose -f docker/docker-compose.yml up --build -d
```

See `docker/README.md` for full documentation.
