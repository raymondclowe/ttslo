# Telegram Notifications for TTSLO

TTSLO can send Telegram notifications for important events during operation. This feature is completely optional and the system works normally without notifications configured.

## Features

The notification system supports the following event types:

1. **Config Changed** - Notifies when `config.csv` has been modified and reloaded
2. **Validation Errors** - Notifies when configuration validation finds errors
3. **Trigger Price Reached** - Notifies when a trigger price threshold is met
4. **TSL Order Created** - Notifies when a trailing stop loss order is created on Kraken
5. **TSL Order Filled** - Notifies when a TSL order is filled/executed (automatically monitored)
6. **Application Exit** - Notifies when the application exits (gracefully)
7. **API Errors** - Notifies when Kraken API calls fail (timeouts, connection errors, server errors, rate limiting)

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow the prompts to name your bot
4. Copy the bot token provided (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy your chat ID (a number like: `123456789`)

### 3. Configure Environment Variable

Add your bot token to your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

The application also checks for `copilot_TELEGRAM_BOT_TOKEN` for GitHub Copilot agent environments.

### 4. Create Notifications Configuration

Create a `notifications.ini` file in the same directory as `ttslo.py`:

```ini
# Define recipients (username = chat_id)
[recipients]
alice = 123456789
bob = 987654321

# Configure which users get notified for each event
[notify.config_changed]
users = alice

[notify.validation_error]
users = alice

[notify.trigger_reached]
users = alice, bob

[notify.tsl_created]
users = alice, bob

[notify.tsl_filled]
users = alice, bob

[notify.app_exit]
users = alice

[notify.api_error]
users = alice
```

You can also create a sample configuration file:

```bash
python3 -c "from notifications import create_sample_notifications_config; create_sample_notifications_config('notifications.ini.example')"
```

## Configuration Format

### Recipients Section

The `[recipients]` section maps usernames to Telegram chat IDs:

```ini
[recipients]
username = chat_id
```

- `username`: Any identifier you want to use (e.g., your name or role)
- `chat_id`: Your Telegram chat ID (numeric)

### Notification Sections

Each event type has its own section in the format `[notify.event_type]`:

```ini
[notify.event_type]
users = username1, username2, username3
```

Available event types:
- `config_changed`
- `validation_error`
- `trigger_reached`
- `tsl_created`
- `tsl_filled`
- `app_exit`
- `api_error`

## Example Notifications

### Trigger Price Reached
```
🎯 TTSLO: Trigger price reached!

Config: btc_sell_1
Pair: XXBTZUSD
Current Price: 52000.00
Threshold: 50000.00 (above)
```

### TSL Order Created
```
✅ TTSLO: Trailing Stop Loss order created!

Config: btc_sell_1
Order ID: OQCLML-BW3P3-BUCMWZ
Pair: XXBTZUSD
Direction: sell
Volume: 0.01
Trailing Offset: 5.0%
Trigger Price: 52000.00
```

### TSL Order Filled
```
💰 TTSLO: Trailing Stop Loss order FILLED!

Config: btc_sell_1
Order ID: OQCLML-BW3P3-BUCMWZ
Pair: XXBTZUSD
Fill Price: 51000.00
```

## Order Fill Monitoring

TTSLO automatically monitors all triggered orders to detect when they are filled:

- **Automatic Detection**: Every monitoring cycle, TTSLO checks the status of all triggered orders via Kraken's API
- **No Duplicate Notifications**: Each order fill is notified only once - tracked via `fill_notified` flag in state
- **Fill Price Included**: When available, the actual fill price is included in the notification
- **Minimal API Usage**: Only checks closed orders, reducing API call overhead
- **Works in Background**: Monitoring happens automatically in the main loop alongside price checking

The system queries Kraken's `ClosedOrders` API endpoint to check if orders created by TTSLO have been executed. When an order transitions from open to closed/filled, a Telegram notification is immediately sent (if configured).

### API Error
```
🔌 TTSLO: Kraken API Error

Error Type: connection
Endpoint: Ticker/get_current_price
Message: Failed to connect to Kraken API for Ticker: [Errno -2] Name or service not known

⚠️ Cannot reach Kraken API. Check your network connection.
```

Example timeout error:
```
⏱️ TTSLO: Kraken API Error

Error Type: timeout
Endpoint: Balance
Message: Request to Kraken API timed out after 30s for Balance
Timeout: 30s

⚠️ This could indicate network issues or Kraken API being slow.
```

Example server error (5xx):
```
🔥 TTSLO: Kraken API Error

Error Type: server_error
Endpoint: AddOrder/add_trailing_stop_loss
Message: Kraken API server error (HTTP 503) for AddOrder
Status Code: 503

⚠️ Kraken API is experiencing issues. Service may be down or under maintenance.
```

Example rate limit error:
```
🚦 TTSLO: Kraken API Error

Error Type: rate_limit
Endpoint: Ticker
Message: Kraken API rate limit exceeded for Ticker

⚠️ API rate limit exceeded. TTSLO will retry with backoff.
```

### Configuration Changed
```
⚙️ TTSLO: Configuration file (config.csv) has been modified and reloaded.
```

## Disabling Notifications

Notifications are automatically disabled if:
- No `notifications.ini` file exists
- No `TELEGRAM_BOT_TOKEN` environment variable is set
- The configuration file is invalid
- No recipients are configured

The application works normally without notifications.

## Testing Notifications

You can test your notification setup by:

1. Sending a test message using Python:

```python
from notifications import NotificationManager

nm = NotificationManager()
nm.send_message('alice', '🧪 Test notification from TTSLO')
```

2. Running TTSLO with verbose output to see if notifications are enabled:

```bash
./ttslo.py --verbose --once
```

You should see: `Telegram notifications enabled for X recipients`

## Watchdog for Crash Detection

The current implementation notifies on graceful exits but cannot detect crashes. A watchdog process would be needed to detect unexpected terminations.

### Watchdog Implementation Roadmap

For full crash detection, consider implementing:

1. **External Watchdog Script**
   - Separate process that monitors ttslo.py
   - Detects when process exits unexpectedly
   - Sends notification if no graceful shutdown detected
   - Can be implemented as a systemd service with restart policies

2. **Heartbeat Mechanism**
   - ttslo.py sends periodic heartbeat notifications
   - Watchdog expects heartbeats at regular intervals
   - Missing heartbeat triggers crash notification

3. **PID File Monitoring**
   - ttslo.py writes PID to file on startup
   - Removes PID file on graceful shutdown
   - Watchdog checks if PID exists but process is gone

4. **Systemd Integration**
   - Run as systemd service
   - Use systemd's restart policies
   - Notification on service failure via systemd hooks

Example external watchdog script structure:

```python
#!/usr/bin/env python3
import subprocess
import time
from notifications import NotificationManager

def monitor_ttslo():
    nm = NotificationManager()
    while True:
        # Check if ttslo.py is running
        result = subprocess.run(['pgrep', '-f', 'ttslo.py'], 
                              capture_output=True)
        if result.returncode != 0:
            nm.notify_application_exit('Process not found - possible crash')
            # Restart ttslo.py or alert operator
        time.sleep(60)  # Check every minute
```

## Troubleshooting

### Notifications Not Working

1. **Check bot token**: Ensure `TELEGRAM_BOT_TOKEN` is set correctly in `.env`
2. **Verify chat ID**: Make sure your chat ID is correct in `notifications.ini`
3. **Test bot**: Message your bot directly to verify it's active
4. **Check verbose output**: Run with `--verbose` to see if notifications are enabled
5. **Check permissions**: Ensure the bot can send messages to your chat

### Network Outage Scenario

**Important Limitation**: During a complete network outage, Telegram notifications cannot be sent.

**Enhanced Behavior (with Notification Queue)**:

TTSLO now includes an intelligent notification queue system that:

1. **Detects** when Telegram API is unreachable (timeout or connection error)
2. **Queues** all notifications that fail to send
3. **Persists** the queue to disk (`notification_queue.json`)
4. **Monitors** for when Telegram becomes reachable again
5. **Flushes** all queued notifications when connectivity is restored
6. **Notifies** users about the downtime period and queued message count

**What happens during network outage**:
- TTSLO detects Kraken API is unreachable (connection error)
- TTSLO logs the error to `logs.csv`
- TTSLO attempts to send Telegram notification
- Telegram notification fails (cannot reach Telegram API either)
- Notification is **queued** for later delivery
- Error message printed to console: `✗ Cannot reach Telegram API (network may be down)`
- Queue is saved to disk: `📬 Queued notification for alice (1 total in queue)`
- Processing continues on next cycle

**What happens when network is restored**:
- Next successful API call triggers queue flush attempt
- All queued notifications are sent with `[Queued from TIMESTAMP]` prefix
- Recovery notification sent to all recipients:
  ```
  ✅ TTSLO: Telegram notifications restored
  
  Notifications were unavailable for 2 hours 15 minutes
  From: 2025-10-23 10:00:00 UTC
  To: 2025-10-23 12:15:00 UTC
  
  Sending 5 queued notifications...
  ```
- Queue is cleared after successful delivery

**What you'll see in logs**:
```
[2025-10-23 12:00:00] ERROR: Kraken API error getting current price for XXBTZUSD: Failed to connect to Kraken API (type: connection)
✗ Cannot reach Telegram API (network may be down): [Errno -2] Name or service not known
⚠️  Telegram marked as unreachable at 2025-10-23T12:00:00+00:00
📬 Queued notification for alice (1 total in queue)
...
[2025-10-23 14:15:00] INFO: Price check successful
Attempting to flush 5 queued notifications...
✓ Sent 5 queued notifications
✓ Telegram is reachable again after 2 hours 15 minutes downtime
```

**Benefits of Notification Queue**:
- **No lost notifications**: All notifications are eventually delivered
- **Automatic recovery**: No manual intervention needed
- **Downtime awareness**: Users are informed about the outage duration
- **Persistent across restarts**: Queue survives application restarts
- **Ordered delivery**: Notifications sent in the order they were queued

**Recommendations**:
1. **Always check logs.csv**: All errors are logged regardless of notification status
2. **Monitor log files**: Set up log monitoring/aggregation (e.g., tail -f, logwatch)
3. **Use systemd**: Run as systemd service to see console output in journalctl
4. **Redundant networking**: Run on server with redundant network connections
5. **External monitoring**: Use external monitoring service to detect when TTSLO server is unreachable

**Recovery**:
- When network is restored, TTSLO automatically resumes normal operation
- New Telegram notifications will work once network is back
- Review logs.csv to see what happened during the outage

### Notifications Not Working

1. **Check bot token**: Ensure `TELEGRAM_BOT_TOKEN` is set correctly in `.env`
2. **Verify chat ID**: Make sure your chat ID is correct in `notifications.ini`
3. **Test bot**: Message your bot directly to verify it's active
4. **Check verbose output**: Run with `--verbose` to see if notifications are enabled
5. **Check permissions**: Ensure the bot can send messages to your chat

### Getting Chat ID

If @userinfobot doesn't work:

1. Message your bot directly
2. Visit: `https://api.telegram.org/bot<YourBOTToken>/getUpdates`
3. Look for `"chat":{"id":123456789` in the response

### Bot Not Responding

1. Verify the bot token is correct
2. Make sure you've sent `/start` to your bot
3. Check that the bot hasn't been deleted or blocked

## Security Considerations

- Keep your bot token secret (never commit it to version control)
- Use `.env` file (which is in `.gitignore`)
- Consider the sensitivity of information sent via Telegram
- Bot tokens can be regenerated via @BotFather if compromised

## API Reference

See `notifications.py` for the complete API. Key classes:

- `NotificationManager`: Main class for managing notifications
- `notify_event()`: Send notification for specific event type
- `notify_config_changed()`: Config file changed notification
- `notify_validation_errors()`: Validation errors notification
- `notify_trigger_price_reached()`: Trigger price reached notification
- `notify_tsl_order_created()`: TSL order created notification
- `notify_tsl_order_filled()`: TSL order filled notification
- `notify_application_exit()`: Application exit notification
