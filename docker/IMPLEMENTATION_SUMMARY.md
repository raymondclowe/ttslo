# Docker Multi-Instance Implementation Summary

## Completed Tasks

✅ Created Docker containerization for ttslo  
✅ Multi-instance support with isolated configs and API keys  
✅ Persistent storage for config/state/logs  
✅ Dashboard accessible per instance  
✅ Tested and verified working  

## Files Created

### Docker Infrastructure
- `docker/Dockerfile` - Python 3.11-slim with uv package manager
- `docker/entrypoint.sh` - Container startup script with environment setup
- `docker/docker-compose.yml` - Multi-instance orchestration
- `docker/README.md` - Detailed setup and usage documentation
- `.dockerignore` - Build optimization (excludes unnecessary files)
- `DOCKER.md` - Quick reference at project root

### Instance Directories
- `instance1/` - First instance data folder
  - `config.csv` - Configuration (placeholder)
  - `state.csv` - State tracking (placeholder)
- `instance2/` - Second instance data folder
  - `config.csv` - Configuration (placeholder)
  - `state.csv` - State tracking (placeholder)

## Current Status

Both instances running successfully:
- Instance 1: http://localhost:8001 ✅
- Instance 2: http://localhost:8002 ✅

```
NAME              STATUS         PORTS
ttslo_instance1   Up 9 seconds   0.0.0.0:8001->8001/tcp
ttslo_instance2   Up 9 seconds   0.0.0.0:8002->8002/tcp
```

## Environment Variables Per Instance

Each container requires:
- `KRAKEN_API_KEY` - Read-only API key
- `KRAKEN_API_SECRET` - Read-only API secret
- `KRAKEN_API_KEY_RW` - Read-write API key
- `KRAKEN_API_SECRET_RW` - Read-write API secret
- `DASHBOARD_PORT` - Port for Flask dashboard

Plus internal paths (auto-set by entrypoint):
- `TTSLO_CONFIG_FILE=/config/config.csv`
- `TTSLO_STATE_FILE=/config/state.csv`
- `TTSLO_LOG_FILE=/config/logs.csv`

## How It Works

1. **Build Context**: Project root provides all Python code
2. **Dockerfile**: Installs uv, syncs dependencies, sets entrypoint
3. **Entrypoint**: Exports env vars and starts dashboard.py
4. **Volumes**: Each instance mounts its own `instanceX/` folder to `/config`
5. **Ports**: Unique host port maps to container port (8001:8001, 8002:8002)
6. **Isolation**: Each container runs independently with its own config and keys

## Key Features

- ✅ **Multi-instance**: Run multiple bots on one machine
- ✅ **Isolated configs**: Each instance has separate config.csv and state.csv
- ✅ **Separate API keys**: Each instance can use different Kraken accounts
- ✅ **Persistent data**: Config/state/logs survive container restarts
- ✅ **Easy scaling**: Add more instances by duplicating service blocks
- ✅ **Docker Compose v2**: Uses modern `docker compose` (without hyphen)
- ✅ **Dashboard per instance**: Each instance has its own web UI

## Next Steps for Users

1. Edit `instance1/config.csv` and `instance2/config.csv` with real configurations
2. Update `docker/docker-compose.yml` with real Kraken API keys
3. Optionally add more instances by:
   - Creating `instanceX/` folder with config.csv
   - Adding service block to docker-compose.yml
   - Assigning unique port and keys

## Commands Reference

```bash
# Start all instances
docker compose -f docker/docker-compose.yml up -d

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Stop all instances
docker compose -f docker/docker-compose.yml down

# Rebuild after changes
docker compose -f docker/docker-compose.yml up --build -d
```

## Notes

- Uses Flask development server (suitable for local/LAN use)
- For production: Consider adding Gunicorn/uWSGI
- Security: Replace hardcoded keys with Docker secrets for production
- Docker Compose v2 required (avoid old `docker-compose` v1.29.2)
