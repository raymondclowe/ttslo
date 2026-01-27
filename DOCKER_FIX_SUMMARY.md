# Docker Fix: Ready to Trigger Orders Not Triggering

## Problem Solved

Orders showing "READY TO TRIGGER" status in the dashboard were never actually triggering in Docker deployments.

## Root Cause

The Docker container was only running `dashboard.py` (the web UI), but NOT running `ttslo.py` (the monitoring service that checks price thresholds and creates orders).

**Before:** Only dashboard web UI was running
**After:** Both dashboard AND monitoring service run together

## How It Works Now

The Docker container uses **supervisord** to run two services simultaneously:

1. **ttslo-monitor** - Background service (ttslo.py)
   - Checks price thresholds every 60 seconds
   - Automatically creates orders when thresholds are met
   - Tracks order status

2. **ttslo-dashboard** - Web interface (dashboard.py)
   - Shows pending, active, and completed orders
   - Allows manual intervention (Force/Cancel)
   - Displays balances and risks

## Quick Start

### 1. Copy the template and add your API keys

```bash
cd docker
cp docker-compose.example.yml docker-compose.yml
```

Edit `docker-compose.yml` and replace these placeholder values with your actual Kraken API keys:
```yaml
- KRAKEN_API_KEY=your_readonly_api_key_here
- KRAKEN_API_SECRET=your_readonly_api_secret_here
- KRAKEN_API_KEY_RW=your_readwrite_api_key_here
- KRAKEN_API_SECRET_RW=your_readwrite_api_secret_here
```

⚠️ **Important**: Your read-write API key needs "Create & Modify Orders" permission in Kraken.

### 2. Add your configuration

```bash
mkdir -p config
cp ../config_sample.csv config/config.csv
# Edit config/config.csv with your trading rules
```

### 3. Start the container

```bash
docker compose up -d
```

### 4. Verify both services are running

```bash
docker compose exec ttslo supervisorctl status
```

You should see:
```
ttslo-dashboard                  RUNNING   pid 123, uptime 0:00:05
ttslo-monitor                    RUNNING   pid 124, uptime 0:00:05
```

### 5. Access the dashboard

Open your browser to: http://localhost:5000

### 6. Monitor the logs

**View monitor logs (where triggering happens):**
```bash
docker compose exec ttslo tail -f /var/log/supervisor/ttslo-monitor.out.log
```

**View dashboard logs (web UI):**
```bash
docker compose exec ttslo tail -f /var/log/supervisor/ttslo-dashboard.out.log
```

## Troubleshooting

### Orders still not triggering?

1. **Check if monitor service is running:**
   ```bash
   docker compose exec ttslo supervisorctl status ttslo-monitor
   ```

2. **View monitor logs for errors:**
   ```bash
   docker compose exec ttslo tail -f /var/log/supervisor/ttslo-monitor.out.log
   ```

3. **Manually restart the monitor:**
   ```bash
   docker compose exec ttslo supervisorctl restart ttslo-monitor
   ```

### Nonce errors still appearing?

The code already has a nonce fix with:
- Thread-safe nonce generation
- Microsecond precision timestamps
- Automatic retry on nonce errors

If errors persist:
1. Check you're not using the same API keys elsewhere
2. Increase the nonce window in your Kraken API settings
3. Consider creating separate API keys for this instance

### Can't access dashboard?

1. **Check if dashboard service is running:**
   ```bash
   docker compose exec ttslo supervisorctl status ttslo-dashboard
   ```

2. **View dashboard logs:**
   ```bash
   docker compose exec ttslo tail -f /var/log/supervisor/ttslo-dashboard.out.log
   ```

3. **Verify port mapping:**
   ```bash
   docker compose ps
   ```

## What Changed

### Files Created
- `docker/supervisord.conf` - Process manager configuration
- `docker/run-dashboard.sh` - Port validation wrapper
- `docker/docker-compose.example.yml` - Deployment template
- `docker/config/README.md` - Config directory placeholder

### Files Modified
- `docker/Dockerfile` - Added supervisor installation
- `docker/entrypoint.sh` - Now launches supervisord
- `docker/README.md` - Complete rewrite with new instructions
- `DOCKER.md` - Updated overview
- `LEARNINGS.md` - Documented the fix

## Running Multiple Instances

You can run multiple independent instances for different accounts.

Edit `docker-compose.yml` and add a second service:

```yaml
ttslo_instance2:
  build:
    context: ..
    dockerfile: docker/Dockerfile
  container_name: ttslo_instance2
  environment:
    - KRAKEN_API_KEY=your_second_account_key
    - KRAKEN_API_SECRET=your_second_account_secret
    - KRAKEN_API_KEY_RW=your_second_account_rw_key
    - KRAKEN_API_SECRET_RW=your_second_account_rw_secret
    - DASHBOARD_PORT=5001
  volumes:
    - ./instance2:/config
  ports:
    - "5001:5001"
  restart: unless-stopped
```

Create the instance directory:
```bash
mkdir -p instance2
cp ../config_sample.csv instance2/config.csv
```

Access second dashboard: http://localhost:5001

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│       Docker Container                  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │        supervisord                │  │
│  │                                   │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │   ttslo-monitor             │  │  │
│  │  │   (ttslo.py)                │  │  │
│  │  │   • Checks thresholds       │  │  │
│  │  │   • Creates orders          │  │  │
│  │  │   • Every 60 seconds        │  │  │
│  │  └─────────────────────────────┘  │  │
│  │                                   │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │   ttslo-dashboard           │  │  │
│  │  │   (dashboard.py)            │  │  │
│  │  │   • Web UI                  │  │  │
│  │  │   • Port 5000               │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
│                                         │
│  /config (Docker volume)                │
│  • config.csv - Your trading rules     │
│  • state.csv - Trigger tracking        │
│  • logs.csv - Event log                │
└─────────────────────────────────────────┘
```

## Security Notes

- API keys are passed via environment variables (not in code)
- Port validation prevents command injection
- Each instance isolated with its own config
- Credentials never logged

## Next Steps

1. ✅ Docker fix complete
2. ✅ Documentation updated
3. 🔲 User builds and tests container
4. 🔲 Verify orders trigger correctly
5. 🔲 Monitor for nonce errors

If you encounter any issues, check the troubleshooting section above or review the logs.
