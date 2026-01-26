# Docker Deployment

This repository supports running ttslo in Docker containers with both the monitoring service and web dashboard.

## Key Change: Both Services Now Run

**Previous Setup (Broken):** Only ran `dashboard.py` (web UI), so orders never triggered.

**New Setup (Fixed):** Runs BOTH services using supervisord:
1. **ttslo-monitor** - Background service that triggers orders when thresholds are met
2. **ttslo-dashboard** - Web UI for monitoring and manual control

## Quick Start

```bash
cd docker
docker compose up -d
```

Access dashboard: http://localhost:5000

See detailed instructions in `docker/README.md`

## What This Fixes

**Issue**: Orders showing "READY TO TRIGGER" but never triggering.

**Root Cause**: The Docker container only ran the dashboard web UI (`dashboard.py`), not the monitoring service (`ttslo.py`) that actually checks thresholds and creates orders.

**Solution**: Use supervisord to run both processes in the same container:
- Monitor service checks every 60 seconds and triggers orders
- Dashboard provides real-time visibility and manual controls

## Files

- `docker/Dockerfile` - Container image with supervisord
- `docker/supervisord.conf` - Process manager configuration  
- `docker/entrypoint.sh` - Startup script
- `docker/docker-compose.yml` - Service configuration
- `docker/README.md` - Detailed documentation
- `docker/config/` - Per-instance data folder (created on first run)

## Multiple Instances

Each instance requires separate Kraken API keys and runs on a different port.

Example in `docker-compose.yml`:
```yaml
ttslo_instance2:
  environment:
    - DASHBOARD_PORT=5001
  volumes:
    - ./instance2:/config
  ports:
    - "5001:5001"
```

Access: http://localhost:5001

## Architecture

```
Docker Container
├── supervisord (process manager)
│   ├── ttslo-monitor (runs ttslo.py every 60s)
│   └── ttslo-dashboard (runs dashboard.py on port 5000)
└── /config volume (state, logs, config)
```

Both services share:
- Kraken API credentials
- Config/state files
- Thread-safe nonce generation

See `docker/README.md` for troubleshooting, logs, and advanced configuration.
