# Docker Multi-Instance Setup Guide

## Complete Setup Checklist

### ✅ 1. Telegram Bot Setup (Optional - Shared Across All Instances)

If you want Telegram notifications:

1. **Create a Telegram Bot**:
   - Open Telegram and search for @BotFather
   - Send `/newbot` command
   - Follow instructions to create your bot
   - Copy the bot token

2. **Add Token to Environment**:
   ```bash
   cd /home/tc3/ttslo/docker
   # Edit .env file
   nano .env
   ```
   Add your token:
   ```
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

3. **Configure Recipients Per Instance**:
   
   Each instance can have different notification recipients.
   
   Edit `instance1/notifications.ini`:
   ```ini
   [recipient1]
   name = Your Name
   chat_id = 123456789
   
   [recipient2]
   name = Another Person
   chat_id = 987654321
   ```
   
   To get your chat_id:
   - Message your bot on Telegram
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your chat_id in the response

### ✅ 2. Kraken API Keys (Per Instance)

Edit `docker/docker-compose.yml` and replace placeholders:

**For Instance 1:**
```yaml
environment:
  - KRAKEN_API_KEY=your_actual_ro_key_1
  - KRAKEN_API_SECRET=your_actual_ro_secret_1
  - KRAKEN_API_KEY_RW=your_actual_rw_key_1
  - KRAKEN_API_SECRET_RW=your_actual_rw_secret_1
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  - DASHBOARD_PORT=8001
```

**For Instance 2:**
```yaml
environment:
  - KRAKEN_API_KEY=your_actual_ro_key_2
  - KRAKEN_API_SECRET=your_actual_ro_secret_2
  - KRAKEN_API_KEY_RW=your_actual_rw_key_2
  - KRAKEN_API_SECRET_RW=your_actual_rw_secret_2
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  - DASHBOARD_PORT=8002
```

### ✅ 3. Configure Trading Strategy (Per Instance)

Edit each instance's config:

```bash
# Instance 1
nano instance1/config.csv

# Instance 2
nano instance2/config.csv
```

Configure your trading pairs, thresholds, and limits.

### ✅ 4. Start Containers

```bash
cd /home/tc3/ttslo
docker compose -f docker/docker-compose.yml up -d
```

### ✅ 5. Verify Everything Works

**Check container status:**
```bash
docker compose -f docker/docker-compose.yml ps
```

**View logs:**
```bash
docker compose -f docker/docker-compose.yml logs -f
```

**Access dashboards:**
- Instance 1: http://localhost:8001
- Instance 2: http://localhost:8002

**Test Telegram (if configured):**
- Check dashboard logs for "Telegram notifications enabled"
- Or send test notification from dashboard UI

## Environment Variables Summary

### Shared (in `docker/.env`)
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather (optional)

### Per-Instance (in `docker-compose.yml`)
- `KRAKEN_API_KEY` - Read-only API key
- `KRAKEN_API_SECRET` - Read-only API secret
- `KRAKEN_API_KEY_RW` - Read-write API key
- `KRAKEN_API_SECRET_RW` - Read-write API secret
- `DASHBOARD_PORT` - Port for dashboard (8001, 8002, etc.)

### Auto-Set (by entrypoint.sh)
- `TTSLO_CONFIG_FILE=/config/config.csv`
- `TTSLO_STATE_FILE=/config/state.csv`
- `TTSLO_LOG_FILE=/config/logs.csv`

## File Locations Per Instance

Each instance has its own isolated data:

```
instance1/
├── config.csv              # Trading configuration
├── state.csv              # State tracking
├── logs.csv               # Application logs
└── notifications.ini      # Telegram recipients

instance2/
├── config.csv
├── state.csv
├── logs.csv
└── notifications.ini
```

## Common Operations

**Restart a specific instance:**
```bash
docker compose -f docker/docker-compose.yml restart ttslo_instance1
```

**View logs for one instance:**
```bash
docker compose -f docker/docker-compose.yml logs -f ttslo_instance1
```

**Stop all instances:**
```bash
docker compose -f docker/docker-compose.yml down
```

**Rebuild after code changes:**
```bash
docker compose -f docker/docker-compose.yml up --build -d
```

**Execute command in container:**
```bash
docker exec -it ttslo_instance1 bash
```

## Troubleshooting

### Telegram not working
1. Check `.env` file has valid bot token
2. Check `notifications.ini` has correct chat_ids
3. View logs: `docker compose logs ttslo_instance1 | grep -i telegram`

### Dashboard not accessible
1. Check container is running: `docker ps`
2. Check port mapping in docker-compose.yml
3. Check firewall rules

### API errors
1. Verify Kraken API keys are correct
2. Check key permissions (read/read-write)
3. View logs for specific error messages

### Config changes not applying
1. Restart container: `docker compose restart ttslo_instance1`
2. Or rebuild: `docker compose up --build -d`

## Security Notes

- Never commit `.env` file to git (it contains secrets)
- Each instance can use different Kraken accounts
- Telegram bot token is shared but recipients are per-instance
- Use read-only keys where possible
- Consider using Docker secrets for production deployments
