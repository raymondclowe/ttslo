"""
Telegram notification system for TTSLO.

Simple notification implementation following the pattern from
@raymondclowe/telegram-send-file/tgsnd.py
"""
import os
import configparser
import requests
import threading
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta


class NotificationManager:
    """Manages Telegram notifications based on configuration."""
    
    def __init__(self, config_file: str = 'notifications.ini'):
        """
        Initialize notification manager.
        
        Args:
            config_file: Path to notifications configuration file
        """
        self.config_file = config_file
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('copilot_TELEGRAM_BOT_TOKEN')
        self.recipients = {}
        self.enabled = False
        
        if os.path.exists(config_file):
            self._load_config()
        
    def _load_config(self):
        """Load notification configuration from INI file."""
        try:
            config = configparser.ConfigParser()
            config.read(self.config_file)
            
            # Load recipients
            if 'recipients' in config:
                for username, chat_id in config['recipients'].items():
                    self.recipients[username] = chat_id
            
            # Load event subscriptions
            self.subscriptions = {}
            for section in config.sections():
                if section.startswith('notify.'):
                    event_type = section[7:]  # Remove 'notify.' prefix
                    if 'users' in config[section]:
                        users = [u.strip() for u in config[section]['users'].split(',')]
                        self.subscriptions[event_type] = users
            
            # Check if notifications are enabled
            if self.telegram_token and self.recipients:
                self.enabled = True
                
        except Exception as e:
            print(f"Warning: Failed to load notification config: {e}")
            self.enabled = False
    
    def send_message(self, username: str, message: str) -> bool:
        """
        Send a message to a Telegram user.
        
        Args:
            username: Username from notifications.ini
            message: Message text to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.enabled:
            print(f"Warning: Notifications not enabled. Token present: {bool(self.telegram_token)}, Recipients: {len(self.recipients)}")
            return False
        
        if username not in self.recipients:
            print(f"Warning: Unknown notification recipient: {username}")
            print(f"Available recipients: {list(self.recipients.keys())}")
            return False
        
        chat_id = self.recipients[username]
        
        try:
            url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
            response = requests.post(url, data={'chat_id': chat_id, 'text': message}, timeout=10)
            
            print(f"Telegram API Response: Status={response.status_code}, Body={response.text}")
            
            # Check both status code and response JSON
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    print(f"✓ Telegram message sent successfully to {username}")
                    return True
                else:
                    print(f"✗ Telegram API returned ok=False: {result}")
                    return False
            else:
                print(f"✗ Failed to send Telegram message (HTTP {response.status_code}): {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Exception sending Telegram message: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def notify_event(self, event_type: str, message: str):
        """
        Send notification for a specific event type to all subscribed users.
        
        Args:
            event_type: Type of event (e.g., 'config_changed', 'validation_error')
            message: Message to send
        """
        if not self.enabled:
            print(f"Warning: Notifications not enabled for event '{event_type}'")
            return
        
        if event_type not in self.subscriptions:
            print(f"Warning: No subscriptions found for event type '{event_type}'")
            print(f"Available event types: {list(self.subscriptions.keys())}")
            return
        
        print(f"Sending '{event_type}' notification to: {self.subscriptions[event_type]}")
        for username in self.subscriptions[event_type]:
            self.send_message(username, message)
    
    def notify_config_changed(self):
        """Notify that config.csv has been modified."""
        self.notify_event('config_changed', 
                         '⚙️ TTSLO: Configuration file (config.csv) has been modified and reloaded.')
    
    def notify_validation_errors(self, errors: List[Dict]):
        """
        Notify about configuration validation errors.
        
        Args:
            errors: List of validation error dictionaries
        """
        if not errors:
            return
        
        message = f"❌ TTSLO: Configuration validation errors found:\n\n"
        for error in errors[:5]:  # Limit to first 5 errors
            config_id = error.get('config_id', 'unknown')
            field = error.get('field', 'unknown')
            msg = error.get('message', 'unknown error')
            message += f"[{config_id}] {field}: {msg}\n"
        
        if len(errors) > 5:
            message += f"\n...and {len(errors) - 5} more errors."
        
        self.notify_event('validation_error', message)
    
    def notify_trigger_price_reached(self, config_id: str, pair: str, 
                                     current_price: float, threshold_price: float,
                                     threshold_type: str):
        """
        Notify that a trigger price has been reached.
        
        Args:
            config_id: Configuration ID
            pair: Trading pair
            current_price: Current price
            threshold_price: Threshold price
            threshold_type: Type of threshold (above/below)
        """
        message = (f"🎯 TTSLO: Trigger price reached!\n\n"
                  f"Config: {config_id}\n"
                  f"Pair: {pair}\n"
                  f"Current Price: {current_price}\n"
                  f"Threshold: {threshold_price} ({threshold_type})")
        
        self.notify_event('trigger_reached', message)
    
    def notify_tsl_order_created(self, config_id: str, order_id: str, 
                                pair: str, direction: str, volume: str,
                                trailing_offset: float, trigger_price: float):
        """
        Notify that a TSL order has been created.
        
        Args:
            config_id: Configuration ID
            order_id: Kraken order ID
            pair: Trading pair
            direction: Order direction (buy/sell)
            volume: Order volume
            trailing_offset: Trailing offset percentage
            trigger_price: Price at which threshold was triggered
        """
        message = (f"✅ TTSLO: Trailing Stop Loss order created!\n\n"
                  f"Config: {config_id}\n"
                  f"Order ID: {order_id}\n"
                  f"Pair: {pair}\n"
                  f"Direction: {direction}\n"
                  f"Volume: {volume}\n"
                  f"Trailing Offset: {trailing_offset}%\n"
                  f"Trigger Price: {trigger_price}")
        
        self.notify_event('tsl_created', message)
    
    def notify_tsl_order_filled(self, config_id: str, order_id: str,
                                pair: str, fill_price: Optional[float] = None,
                                volume: Optional[str] = None,
                                trigger_price: Optional[str] = None,
                                trigger_time: Optional[str] = None,
                                offset: Optional[str] = None,
                                fill_time: Optional[float] = None):
        """
        Notify that a TSL order has been filled.
        
        Args:
            config_id: Configuration ID
            order_id: Kraken order ID
            pair: Trading pair
            fill_price: Price at which order was filled (optional)
        """
        message = (f"💰 TTSLO: Trailing Stop Loss order FILLED!\n\n"
                  f"Config: {config_id}\n"
                  f"Order ID: {order_id}\n"
                  f"Pair: {pair}")

        # Helper: convert epoch or ISO UTC time to HKT (UTC+8) string
        def _format_hkt(t):
            # Accept epoch seconds (float/int) or ISO string
            if not t:
                return None
            try:
                if isinstance(t, (int, float)):
                    dt = datetime.fromtimestamp(float(t), tz=timezone.utc)
                else:
                    # Try parse ISO
                    dt = datetime.fromisoformat(str(t))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                # Convert to HKT (UTC+8)
                hkt = dt.astimezone(timezone(timedelta(hours=8)))
                return hkt.strftime('%Y-%m-%d %H:%M:%S') + ' HKT'
            except Exception:
                return str(t)

        # Append as much useful information as is available
        if fill_price is not None:
            message += f"\nFill Price: {fill_price}"
        if volume:
            message += f"\nExecuted Volume: {volume}"
        if trigger_price:
            message += f"\nTrigger Price: {trigger_price}"
        if offset:
            message += f"\nTrailing Offset: {offset}"
        if trigger_time:
            ft = _format_hkt(trigger_time)
            message += f"\nTriggered At: {ft if ft else trigger_time}"
        if fill_time:
            ff = _format_hkt(fill_time)
            message += f"\nFilled At: {ff if ff else fill_time}"

        self.notify_event('tsl_filled', message)
    
    def notify_insufficient_balance(self, config_id: str, pair: str,
                                   direction: str, volume: str,
                                   available: str, trigger_price: float):
        """
        Notify that an order could not be created due to insufficient balance.
        
        Args:
            config_id: Configuration ID
            pair: Trading pair
            direction: Order direction (buy/sell)
            volume: Requested order volume
            available: Available balance
            trigger_price: Price at which threshold was triggered
        """
        message = (f"⚠️ TTSLO: Cannot create order - Insufficient balance!\n\n"
                  f"Config: {config_id}\n"
                  f"Pair: {pair}\n"
                  f"Direction: {direction}\n"
                  f"Required Volume: {volume}\n"
                  f"Available Balance: {available}\n"
                  f"Trigger Price: {trigger_price}\n\n"
                  f"⚠️ Action needed: Add funds to your account or adjust the order volume.")
        
        self.notify_event('insufficient_balance', message)
    
    def notify_order_failed(self, config_id: str, pair: str,
                           direction: str, volume: str,
                           error: str, trigger_price: float):
        """
        Notify that an order failed to be created on Kraken.
        
        Args:
            config_id: Configuration ID
            pair: Trading pair
            direction: Order direction (buy/sell)
            volume: Order volume
            error: Error message from Kraken API
            trigger_price: Price at which threshold was triggered
        """
        message = (f"❌ TTSLO: Order creation failed!\n\n"
                  f"Config: {config_id}\n"
                  f"Pair: {pair}\n"
                  f"Direction: {direction}\n"
                  f"Volume: {volume}\n"
                  f"Trigger Price: {trigger_price}\n\n"
                  f"Error: {error}\n\n"
                  f"⚠️ Please check your account balance and configuration.")
        
        self.notify_event('order_failed', message)
    
    def notify_application_exit(self, reason: str = "unknown"):
        """
        Notify that the application has exited.
        
        Args:
            reason: Reason for exit
        """
        message = f"🛑 TTSLO: Application has exited.\n\nReason: {reason}"
        self.notify_event('app_exit', message)
    
    def notify_service_started(self, service_name: str = "TTSLO Dashboard", host: str = None, port: int = None):
        """
        Notify that the service has started.
        
        Args:
            service_name: Name of the service
            host: Host address (optional)
            port: Port number (optional)
        """
        msg = f"🚀 {service_name} started successfully."
        if host and port:
            msg += f"\nURL: http://{host}:{port}"
        self.notify_event('service_started', msg)

    def _dispatch_async(self, func, *args, **kwargs):
        """
        Helper to dispatch a notification call in a daemon thread so callers
        (e.g., signal handlers) aren't blocked by network IO.
        """
        try:
            t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
            t.start()
        except Exception as e:
            print(f"Warning: Failed to dispatch async notification: {e}")

    def notify_service_started_async(self, service_name: str = "TTSLO Dashboard", host: str = None, port: int = None):
        """Non-blocking wrapper for service started notification."""
        self._dispatch_async(self.notify_service_started, service_name, host, port)

    def notify_service_stopped(self, service_name: str = "TTSLO Dashboard", reason: str = None):
        """
        Notify that the service has stopped.
        
        Args:
            service_name: Name of the service
            reason: Reason for stopping (optional)
        """
        msg = f"🛑 {service_name} stopped."
        if reason:
            msg += f"\nReason: {reason}"
        self.notify_event('service_stopped', msg)

    def notify_service_stopped_async(self, service_name: str = "TTSLO Dashboard", reason: str = None):
        """Non-blocking wrapper for service stopped notification."""
        self._dispatch_async(self.notify_service_stopped, service_name, reason)


def create_sample_notifications_config(filename: str = 'notifications.ini.example'):
    """
    Create a sample notifications configuration file.
    
    Args:
        filename: Output filename
    """
    sample_content = """# TTSLO Notifications Configuration
# This file configures who receives which notifications via Telegram

# First, define your recipients
# Format: username = telegram_chat_id
# To get your chat_id, message @userinfobot on Telegram
[recipients]
# Example:
# alice = 123456789
# bob = 987654321

# Then, configure which users get notified for each event type
# Multiple users can be comma-separated

[notify.service_started]
# Notified when the TTSLO Monitor or Dashboard service starts up
# Triggered by: systemctl start, manual script execution
users = 

[notify.service_stopped]
# Notified when the TTSLO Monitor or Dashboard service stops
# Triggered by: systemctl stop/restart, SIGTERM, SIGINT (Ctrl+C), SIGHUP, crashes
users = 

[notify.config_changed]
# Notified when config.csv is modified and reloaded
# Triggered by: File modification detected by the monitor
users = 

[notify.validation_error]
# Notified when config.csv has validation errors
# Triggered by: Invalid configuration detected on startup or reload
users = 

[notify.trigger_reached]
# Notified when a trigger price threshold is reached
# Triggered by: Current price crosses the configured threshold (above/below)
users = 

[notify.tsl_created]
# Notified when a Trailing Stop Loss order is created on Kraken
# Triggered by: Successful order placement after trigger price reached
users = 

[notify.tsl_filled]
# Notified when a Trailing Stop Loss order is filled/executed
# Triggered by: Order execution detected by Kraken API
users = 

[notify.insufficient_balance]
# Notified when an order cannot be created due to insufficient balance
# Triggered by: Balance check fails before order creation
users = 

[notify.order_failed]
# Notified when an order fails to be created on Kraken
# Triggered by: Kraken API returns an error during order creation
users = 

[notify.app_exit]
# Notified when the application exits unexpectedly (crashes/exceptions)
# Triggered by: Uncaught exceptions, fatal errors
# Note: This only works if the app can send the notification before exiting
users = 

# To enable notifications:
# 1. Copy this file to notifications.ini
# 2. Add recipient usernames and their Telegram chat IDs in [recipients]
# 3. Add usernames to the event types you want to be notified about
# 4. Set environment variable: TELEGRAM_BOT_TOKEN=your_bot_token
#    (Get a bot token from @BotFather on Telegram)

# Example notification messages:
# - service_started: "🚀 TTSLO Dashboard started successfully. URL: http://localhost:5000"
# - service_stopped: "🛑 TTSLO Monitor stopped. Reason: Received SIGTERM signal"
# - config_changed: "⚙️ TTSLO: Configuration file (config.csv) has been modified and reloaded."
# - validation_error: "❌ TTSLO: Configuration validation errors found: [config_id] field: message"
# - trigger_reached: "🎯 TTSLO: Trigger price reached! Config: xyz, Pair: BTC/USD, Current: 50000"
# - tsl_created: "✅ TTSLO: Trailing Stop Loss order created! Order ID: ABC123"
# - tsl_filled: "💰 TTSLO: Trailing Stop Loss order FILLED! Order ID: ABC123"
# - insufficient_balance: "⚠️ TTSLO: Cannot create order - Insufficient balance!"
# - order_failed: "❌ TTSLO: Order creation failed! Error: [Kraken error message]"
# - app_exit: "🛑 TTSLO: Application has exited. Reason: Unexpected exception"
"""
    
    with open(filename, 'w') as f:
        f.write(sample_content)
    
    print(f"Sample notifications configuration created: {filename}")
