# ttslo Docker Multi-Instance Setup

Run multiple ttslo instances on one machine, each with unique config, state, and Kraken API keys.

## Quick Start

### 1. Prepare Instance Folders
```bash
cd /home/tc3/ttslo
# Copy your config to each instance folder
cp config.csv instance1/config.csv
cp config.csv instance2/config.csv
# Edit each config as needed
```

### 2. Set Up Telegram (Optional - Shared Across All Instances)
```bash
cd docker
cp .env.example .env
# Edit .env and add your Telegram bot token
```

To get a Telegram bot token:
1. Message @BotFather on Telegram
2. Send `/newbot` and follow instructions
3. Copy the token to `.env`

### 3. Set Kraken API Keys
Edit `docker/docker-compose.yml` and replace placeholder keys for each instance:
- `KRAKEN_API_KEY` (read-only)
- `KRAKEN_API_SECRET` (read-only)
- `KRAKEN_API_KEY_RW` (read-write)
- `KRAKEN_API_SECRET_RW` (read-write)

### 4. Configure Telegram Recipients (Per Instance)
Edit `instanceX/notifications.ini` for each instance to configure who receives alerts.
See `notifications.ini.example` in the project root for format.

### 5. Build & Run
```bash
cd /home/tc3/ttslo
docker compose -f docker/docker-compose.yml up -d
```

### 6. Access Dashboards
- Instance1: http://localhost:8001
- Instance2: http://localhost:8002

### 7. Check Status & Logs
```bash
# View running containers
docker compose -f docker/docker-compose.yml ps

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Stop containers
docker compose -f docker/docker-compose.yml down
```

## Add More Instances

1. Create new instance folder:
   ```bash
   mkdir instance3
   cp config.csv instance3/config.csv
   ```

2. Add service to `docker/docker-compose.yml`:
   ```yaml
   ttslo_instance3:
     build:
       context: ..
       dockerfile: docker/Dockerfile
     container_name: ttslo_instance3
     environment:
       - KRAKEN_API_KEY=your_ro_key_3
       - KRAKEN_API_SECRET=your_ro_secret_3
       - KRAKEN_API_KEY_RW=your_rw_key_3
       - KRAKEN_API_SECRET_RW=your_rw_secret_3
       - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
       - DASHBOARD_PORT=8003
     volumes:
       - ../instance3:/config
     ports:
       - "8003:8003"
   ```

3. Restart:
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

## Data Persistence
- Config/state/logs are stored in `instanceX/` folders on host
- Survives container restarts and rebuilds

## Security Notes
- For production, use Docker secrets or .env files instead of hardcoding keys
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
