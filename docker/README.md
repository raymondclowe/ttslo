# ttslo Docker Setup

Run ttslo in a Docker container with both the monitoring service and web dashboard.

## What Runs in the Container

The Docker container runs **BOTH** of these services using supervisord:

1. **ttslo monitor** (`ttslo.py`) - Background service that:
   - Monitors price thresholds every 60 seconds
   - Automatically triggers orders when thresholds are met
   - Tracks order status and completion

2. **ttslo dashboard** (`dashboard.py`) - Web UI that:
   - Shows pending, active, and completed orders
   - Allows manual order cancellation/forcing
   - Displays real-time balances and risks

## Quick Start

### 1. Prepare Configuration

Create a config directory with your configuration:

```bash
cd docker
mkdir -p config
cp ../config_sample.csv config/config.csv
# Edit config/config.csv with your trading rules
```

### 2. Set Kraken API Keys

Edit `docker-compose.yml` and replace the placeholder API keys:
- `KRAKEN_API_KEY` - Read-only API key (for price checks)
- `KRAKEN_API_SECRET` - Read-only API secret
- `KRAKEN_API_KEY_RW` - Read-write API key (for creating orders)
- `KRAKEN_API_SECRET_RW` - Read-write API secret

⚠️ **Important**: The read-write key needs "Create & Modify Orders" permission.

### 3. Optional: Set Up Telegram Notifications

```bash
cd docker
cp .env.example .env
# Edit .env and add your Telegram bot token
```

To get a Telegram bot token:
1. Message @BotFather on Telegram
2. Send `/newbot` and follow instructions
3. Copy the token to `.env`

Then configure recipients in `config/notifications.ini` (see `../notifications.ini.example`).

### 4. Build & Run

```bash
cd docker
docker compose up -d
```

### 5. Access Dashboard

Open your browser to: http://localhost:5000

### 6. Check Logs

```bash
# View all logs
docker compose logs -f

# View only monitor logs
docker compose exec ttslo tail -f /var/log/supervisor/ttslo-monitor.out.log

# View only dashboard logs
docker compose exec ttslo tail -f /var/log/supervisor/ttslo-dashboard.out.log
```

### 7. Monitor Status

```bash
# Check if both services are running
docker compose exec ttslo supervisorctl status

# Restart a specific service
docker compose exec ttslo supervisorctl restart ttslo-monitor
docker compose exec ttslo supervisorctl restart ttslo-dashboard
```

## Data Persistence

- Config, state, and logs are stored in `docker/config/` on the host
- Data survives container restarts and rebuilds
- The monitor service (`ttslo.py`) creates orders when thresholds are met
- The dashboard shows real-time status

## Troubleshooting

### Orders Not Triggering

**Symptom**: Orders show "READY TO TRIGGER" but nothing happens.

**Solution**: Ensure the monitor service is running:
```bash
docker compose exec ttslo supervisorctl status ttslo-monitor
```

If stopped, start it:
```bash
docker compose exec ttslo supervisorctl start ttslo-monitor
```

### Nonce Errors

**Symptom**: Logs show `EAPI:Invalid nonce` errors.

**Cause**: Each service (monitor and dashboard) uses the same API keys and nonces can collide.

**Solution**: The code already implements thread-safe nonce generation with retry logic. If errors persist:
1. Check if you're using the same API keys elsewhere
2. Increase the nonce window in your Kraken API settings
3. Create separate API keys for different services

### Dashboard Not Accessible

**Symptom**: Cannot access http://localhost:5000

**Solution**: 
```bash
# Check if dashboard service is running
docker compose exec ttslo supervisorctl status ttslo-dashboard

# Check if port is mapped correctly
docker compose ps

# View dashboard logs
docker compose exec ttslo tail -f /var/log/supervisor/ttslo-dashboard.out.log
```

## Run Multiple Instances

To run multiple independent instances (e.g., different accounts):

1. Copy the service definition in `docker-compose.yml`
2. Change the container name, ports, and volume paths
3. Use different API keys for each instance

Example:
```yaml
ttslo_instance2:
  build:
    context: ..
    dockerfile: docker/Dockerfile
  container_name: ttslo_instance2
  environment:
    - KRAKEN_API_KEY=your_key_2
    - KRAKEN_API_SECRET=your_secret_2
    - KRAKEN_API_KEY_RW=your_rw_key_2
    - KRAKEN_API_SECRET_RW=your_rw_secret_2
    - DASHBOARD_PORT=5001
  volumes:
    - ./instance2:/config
  ports:
    - "5001:5001"
  restart: unless-stopped
```

Then access the second dashboard at http://localhost:5001

## Architecture

The Docker container uses **supervisord** to manage both processes:

```
┌─────────────────────────────────────┐
│         Docker Container            │
│                                     │
│  ┌──────────────────────────────┐  │
│  │      Supervisord             │  │
│  │                              │  │
│  │  ┌────────────────────────┐  │  │
│  │  │  ttslo-monitor         │  │  │
│  │  │  (ttslo.py)            │  │  │
│  │  │  - Checks thresholds   │  │  │
│  │  │  - Creates orders       │  │  │
│  │  │  - Runs every 60s      │  │  │
│  │  └────────────────────────┘  │  │
│  │                              │  │
│  │  ┌────────────────────────┐  │  │
│  │  │  ttslo-dashboard       │  │  │
│  │  │  (dashboard.py)        │  │  │
│  │  │  - Web UI              │  │  │
│  │  │  - Port 5000           │  │  │
│  │  └────────────────────────┘  │  │
│  └──────────────────────────────┘  │
│                                     │
│  Both share:                        │
│  - /config volume (state/logs)     │
│  - Kraken API credentials          │
│  - Thread-safe nonce generation    │
└─────────────────────────────────────┘
```

## Security Notes

- Each service instance has its own thread-safe nonce generator
- API calls are serialized within each service to prevent nonce collisions
- Use Docker secrets or environment files for production (not hardcoded keys)
- Each instance runs isolated with its own config and API keys
- Dashboard runs on Flask dev server; consider production WSGI for public deployments

## Troubleshooting

### Containers exit immediately
Check logs: `docker compose -f docker/docker-compose.yml logs`

### Port already in use
Change port mapping in docker-compose.yml: `"8004:8001"` (host:container)

### Dashboard not accessible
Ensure ports are mapped correctly and not blocked by firewall

### Use docker compose v2
If you get `ContainerConfig` errors with old `docker-compose`, use: `docker compose` (without hyphen)
