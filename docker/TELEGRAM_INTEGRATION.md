# Telegram Notifications Support Added ✅

## What Changed

Added Telegram bot notification support to the Docker multi-instance deployment.

## Files Updated

### Configuration Files
- **`docker/docker-compose.yml`** - Added `TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}` to both instances
- **`docker/.env`** - Created with `TELEGRAM_BOT_TOKEN` variable (shared across all instances)
- **`docker/.env.example`** - Template for users to copy

### Instance Folders
- **`instance1/notifications.ini`** - Copied from notifications.ini.example
- **`instance2/notifications.ini`** - Copied from notifications.ini.example

### Documentation
- **`docker/SETUP_GUIDE.md`** - Comprehensive setup guide with Telegram instructions
- **`docker/README.md`** - Updated with Telegram setup steps
- **`DOCKER.md`** - Updated configuration section

## How It Works

### Shared Bot Token
All instances share the same Telegram bot token (set in `docker/.env`):
```bash
TELEGRAM_BOT_TOKEN=your_token_here
```

This is passed to each container via `docker-compose.yml`:
```yaml
environment:
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
```

### Per-Instance Recipients
Each instance has its own `notifications.ini` file to configure who receives alerts:
```ini
[recipient1]
name = Person Name
chat_id = 123456789
```

This allows:
- Instance 1 to notify one set of people
- Instance 2 to notify a different set
- All using the same bot

## Setup Steps for Users

1. **Get Bot Token** from @BotFather on Telegram
2. **Edit** `docker/.env` and add token
3. **Configure Recipients** in each `instanceX/notifications.ini`
4. **Restart** containers: `docker compose restart`

## Testing

Verified:
- ✅ Environment variable passed to containers
- ✅ Containers start successfully
- ✅ No errors in logs
- ✅ Dashboard shows notification status

## Benefits

- **Shared Bot**: One bot serves all instances (simpler management)
- **Flexible Recipients**: Each instance can notify different people
- **Easy Setup**: Single `.env` file for the bot token
- **Secure**: Token not hardcoded in docker-compose.yml

## Files Created/Modified Summary

```
docker/
  .env                    # Created - Telegram bot token
  .env.example           # Created - Template
  docker-compose.yml     # Updated - Added TELEGRAM_BOT_TOKEN
  README.md              # Updated - Telegram setup steps
  SETUP_GUIDE.md         # Created - Comprehensive guide

instance1/
  notifications.ini      # Created - Recipient config

instance2/
  notifications.ini      # Created - Recipient config

DOCKER.md                # Updated - Configuration section
```

## Current Status

✅ Telegram support fully integrated  
✅ All documentation updated  
✅ Containers running successfully  
✅ Ready for production use with notifications  

Users can now:
1. Add their Telegram bot token
2. Configure recipients per instance
3. Receive notifications about trades, errors, balances, etc.
