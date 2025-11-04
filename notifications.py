"""
Telegram notification system for TTSLO.

Simple notification implementation following the pattern from
@raymondclowe/telegram-send-file/tgsnd.py
"""
import os
import configparser
import requests
import threading
import json
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone, timedelta
from decimal import Decimal


def format_balance(value: Union[Decimal, float, int, str, None]) -> str:
    """
    Format a balance value with appropriate decimal precision.
    
    Matches the formatPrice() logic from dashboard.html to ensure
    consistent display across notifications and UI.
    
    Args:
        value: Balance value (Decimal, float, int, str, or None)
        
    Returns:
        Formatted string with appropriate decimal places
        
    Examples:
        >>> format_balance(Decimal('0.00123456'))
        '0.00123456'
        >>> format_balance(Decimal('0.0000012345'))
        '0.00000123'
        >>> format_balance(Decimal('1.234567'))
        '1.23'
        >>> format_balance(Decimal('100.5'))
        '100.50'
        >>> format_balance(Decimal('1234.567'))
        '1,234.57'
        >>> format_balance(None)
        'N/A'
    """
    if value is None or value == 'N/A':
        return 'N/A'
    
    try:
        # Convert to float for formatting
        if isinstance(value, Decimal):
            price = float(value)
        elif isinstance(value, str):
            price = float(value)
        else:
            price = float(value)
    except (ValueError, TypeError):
        return 'N/A'
    
    # For very small values (< 0.01), use up to 8 decimal places
    if abs(price) < 0.01:
        # Format with 8 decimals and remove trailing zeros
        formatted = f"{price:.8f}"
        result = formatted.rstrip('0').rstrip('.')
        # Safety check: ensure we never return empty string
        return result or '0'
    # For small values (< 1), use 4 decimal places
    elif abs(price) < 1:
        return f"{price:.4f}"
    # For medium values (< 100), use 2 decimal places
    elif abs(price) < 100:
        return f"{price:.2f}"
    # For large values, use 2 decimal places with thousands separator
    else:
        return f"{price:,.2f}"


class NotificationManager:
    """Manages Telegram notifications based on configuration."""
    
    def __init__(self, config_file: str = 'notifications.ini', queue_file: str = 'notification_queue.json'):
        """
        Initialize notification manager.
        
        Args:
            config_file: Path to notifications configuration file
            queue_file: Path to notification queue file (for offline queueing)
        """
        self.config_file = config_file
        self.queue_file = queue_file
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('copilot_TELEGRAM_BOT_TOKEN')
        self.recipients = {}
        self.enabled = False
        
        # Notification queue for when Telegram is unreachable
        self.notification_queue = []
        self.telegram_unreachable_since = None  # Track when Telegram became unreachable
        self.telegram_was_unreachable = False  # Track if we need to send recovery notification
        
        # Track last notification status for health monitoring
        self.last_notification_success = None  # True/False/None
        self.last_notification_time = None
        self.last_notification_error = None
        
        if os.path.exists(config_file):
            self._load_config()
        
        # Load any queued notifications from previous runs
        self._load_queue()
        
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
    
    def _load_queue(self):
        """Load queued notifications from disk."""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r') as f:
                    data = json.load(f)
                    self.notification_queue = data.get('queue', [])
                    
                    # Restore unreachable state if it was set
                    if data.get('unreachable_since'):
                        self.telegram_unreachable_since = datetime.fromisoformat(data['unreachable_since'])
                        self.telegram_was_unreachable = True
                    
                    if self.notification_queue:
                        print(f"Loaded {len(self.notification_queue)} queued notifications from {self.queue_file}")
        except Exception as e:
            print(f"Warning: Failed to load notification queue: {e}")
            self.notification_queue = []
    
    def _save_queue(self):
        """Save queued notifications to disk."""
        try:
            data = {
                'queue': self.notification_queue,
                'unreachable_since': self.telegram_unreachable_since.isoformat() if self.telegram_unreachable_since else None
            }
            with open(self.queue_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save notification queue: {e}")
    
    def _mark_telegram_unreachable(self):
        """Mark Telegram as unreachable and record the timestamp."""
        if self.telegram_unreachable_since is None:
            self.telegram_unreachable_since = datetime.now(timezone.utc)
            self.telegram_was_unreachable = True
            print(f"⚠️  Telegram marked as unreachable at {self.telegram_unreachable_since.isoformat()}")
            self._save_queue()
    
    def _mark_telegram_reachable(self):
        """Mark Telegram as reachable and send recovery notification if needed."""
        if self.telegram_was_unreachable and self.telegram_unreachable_since:
            # Calculate downtime duration
            downtime_end = datetime.now(timezone.utc)
            downtime_duration = downtime_end - self.telegram_unreachable_since
            
            # Format duration nicely
            hours = int(downtime_duration.total_seconds() // 3600)
            minutes = int((downtime_duration.total_seconds() % 3600) // 60)
            
            duration_str = ""
            if hours > 0:
                duration_str = f"{hours} hour{'s' if hours != 1 else ''}"
                if minutes > 0:
                    duration_str += f" {minutes} min{'s' if minutes != 1 else ''}"
            else:
                duration_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
            
            # Send recovery notification to all users
            recovery_msg = (
                f"✅ TTSLO: Telegram notifications restored\n\n"
                f"Notifications were unavailable for {duration_str}\n"
                f"From: {self.telegram_unreachable_since.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"To: {downtime_end.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                f"Sending {len(self.notification_queue)} queued notification{'s' if len(self.notification_queue) != 1 else ''}..."
            )
            
            # Send to all recipients (not just subscribed to specific events)
            for username in self.recipients.keys():
                self._send_message_direct(username, recovery_msg)
            
            print(f"✓ Telegram is reachable again after {duration_str} downtime")
            
            # Reset state
            self.telegram_unreachable_since = None
            self.telegram_was_unreachable = False
            self._save_queue()
    
    def _flush_queue(self):
        """Attempt to send all queued notifications."""
        if not self.notification_queue:
            return
        
        print(f"Attempting to flush {len(self.notification_queue)} queued notifications...")
        
        sent_count = 0
        failed_queue = []
        
        for item in self.notification_queue:
            username = item.get('username')
            message = item.get('message')
            timestamp = item.get('timestamp')
            
            # Add timestamp to the message
            timestamped_message = f"[Queued from {timestamp}]\n\n{message}"
            
            # Try to send
            if self._send_message_direct(username, timestamped_message):
                sent_count += 1
            else:
                # If send fails, keep in queue
                failed_queue.append(item)
        
        # Update queue with only failed items
        self.notification_queue = failed_queue
        self._save_queue()
        
        if sent_count > 0:
            print(f"✓ Sent {sent_count} queued notification{'s' if sent_count != 1 else ''}")
        
        if failed_queue:
            print(f"⚠️  {len(failed_queue)} notification{'s' if len(failed_queue) != 1 else ''} still queued")
    
    def _send_message_direct(self, username: str, message: str) -> bool:
        """
        Send a message directly without queueing (internal method).
        
        Args:
            username: Username from notifications.ini
            message: Message text to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        if username not in self.recipients:
            return False
        
        chat_id = self.recipients[username]
        
        try:
            url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
            response = requests.post(url, data={'chat_id': chat_id, 'text': message}, timeout=10)
            
            # Check both status code and response JSON
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    # Track success
                    self.last_notification_success = True
                    self.last_notification_time = datetime.now(timezone.utc)
                    self.last_notification_error = None
                    return True
            # Track failure
            self.last_notification_success = False
            self.last_notification_time = datetime.now(timezone.utc)
            self.last_notification_error = f"HTTP {response.status_code}"
            return False
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # Track failure
            self.last_notification_success = False
            self.last_notification_time = datetime.now(timezone.utc)
            self.last_notification_error = str(type(e).__name__)
            return False
        except Exception as e:
            # Track failure
            self.last_notification_success = False
            self.last_notification_time = datetime.now(timezone.utc)
            self.last_notification_error = str(e)
            return False
    
    def send_message(self, username: str, message: str) -> bool:
        """
        Send a message to a Telegram user.
        
        If Telegram is unreachable, the message is queued and will be sent
        when connectivity is restored.
        
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
        
        # First, try to flush any queued notifications (in case Telegram is reachable again)
        if self.notification_queue:
            self._flush_queue()
        
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
                    
                    # If this succeeds and we were previously unreachable, mark as reachable
                    if self.telegram_was_unreachable:
                        self._mark_telegram_reachable()
                    
                    return True
                else:
                    print(f"✗ Telegram API returned ok=False: {result}")
                    return False
            else:
                print(f"✗ Failed to send Telegram message (HTTP {response.status_code}): {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"✗ Timeout sending Telegram message to {username} (network may be slow or down)")
            self._queue_notification(username, message, "timeout")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"✗ Cannot reach Telegram API (network may be down): {e}")
            self._queue_notification(username, message, "connection_error")
            return False
        except Exception as e:
            print(f"✗ Exception sending Telegram message: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _queue_notification(self, username: str, message: str, reason: str):
        """
        Queue a notification for later delivery.
        
        Args:
            username: Username to send to
            message: Message to send
            reason: Reason for queueing (timeout, connection_error, etc.)
        """
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        self.notification_queue.append({
            'username': username,
            'message': message,
            'timestamp': timestamp,
            'reason': reason
        })
        
        # Mark Telegram as unreachable
        self._mark_telegram_unreachable()
        
        print(f"📬 Queued notification for {username} ({len(self.notification_queue)} total in queue)")
        
        # Save queue to disk
        self._save_queue()
    
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
                                     threshold_type: str, linked_order_id: Optional[str] = None):
        """
        Notify that a trigger price has been reached.
        
        Args:
            config_id: Configuration ID
            pair: Trading pair
            current_price: Current price
            threshold_price: Threshold price
            threshold_type: Type of threshold (above/below)
            linked_order_id: ID of linked order that will be activated when this order fills (optional)
        """
        message = (f"🎯 TTSLO: Trigger price reached!\n\n"
                  f"Config: {config_id}\n"
                  f"Pair: {pair}\n"
                  f"Current Price: {current_price}\n"
                  f"Threshold: {threshold_price} ({threshold_type})")
        
        if linked_order_id:
            message += f"\n\n🔗 Linked Order: {linked_order_id}\n💡 Will be activated when this order fills"
        
        self.notify_event('trigger_reached', message)
    
    def notify_tsl_order_created(self, config_id: str, order_id: str, 
                                pair: str, direction: str, volume: str,
                                trailing_offset: float, trigger_price: float,
                                linked_order_id: Optional[str] = None):
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
            linked_order_id: ID of linked order that will be activated when this order fills (optional)
        """
        message = (f"✅ TTSLO: Trailing Stop Loss order created!\n\n"
                  f"Config: {config_id}\n"
                  f"Order ID: {order_id}\n"
                  f"Pair: {pair}\n"
                  f"Direction: {direction}\n"
                  f"Volume: {volume}\n"
                  f"Trailing Offset: {trailing_offset}%\n"
                  f"Trigger Price: {trigger_price}")
        
        if linked_order_id:
            message += f"\n\n🔗 Linked Order: {linked_order_id}\n💡 Will be activated when this order fills"
        
        self.notify_event('tsl_created', message)
    
    def notify_tsl_order_filled(self, config_id: str, order_id: str,
                                pair: str, fill_price: Optional[float] = None,
                                volume: Optional[str] = None,
                                trigger_price: Optional[str] = None,
                                trigger_time: Optional[str] = None,
                                offset: Optional[str] = None,
                                fill_time: Optional[float] = None,
                                linked_order_id: Optional[str] = None):
        """
        Notify that a TSL order has been filled.
        
        Args:
            config_id: Configuration ID
            order_id: Kraken order ID
            pair: Trading pair
            fill_price: Price at which order was filled (optional)
            volume: Executed volume (optional)
            trigger_price: Price at which order was triggered (optional)
            trigger_time: Time at which order was triggered (optional)
            offset: Trailing offset percentage (optional)
            fill_time: Time at which order was filled (optional)
            linked_order_id: ID of linked order that will be activated (optional)
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
        
        if linked_order_id:
            message += f"\n\n🔗 Linked Order: {linked_order_id}\n✓ Now being activated..."

        self.notify_event('tsl_filled', message)
    
    def notify_insufficient_balance(self, config_id: str, pair: str,
                                   direction: str, volume: str,
                                   available: Union[Decimal, float, int, str, None], 
                                   trigger_price: float):
        """
        Notify that an order could not be created due to insufficient balance.
        
        Args:
            config_id: Configuration ID
            pair: Trading pair
            direction: Order direction (buy/sell)
            volume: Requested order volume
            available: Available balance (Decimal, float, int, str, or None - will be formatted)
            trigger_price: Price at which threshold was triggered
        """
        # Format the available balance with appropriate decimal precision
        formatted_balance = format_balance(available)
        
        message = (f"⚠️ TTSLO: Cannot create order - Insufficient balance!\n\n"
                  f"Config: {config_id}\n"
                  f"Pair: {pair}\n"
                  f"Direction: {direction}\n"
                  f"Required Volume: {volume}\n"
                  f"Available Balance: {formatted_balance}\n"
                  f"Trigger Price: {trigger_price}\n\n"
                  f"⚠️ Action needed: Add funds to your account or adjust the order volume.")
        
        self.notify_event('insufficient_balance', message)
    
    def notify_linked_order_activated(self, parent_id: str, linked_id: str,
                                      parent_pair: str, linked_pair: str):
        """
        Notify that a linked order has been activated after parent order filled.
        
        Args:
            parent_id: ID of the parent order that filled
            linked_id: ID of the linked order being activated
            parent_pair: Trading pair of parent order
            linked_pair: Trading pair of linked order
        """
        message = (f"🔗 TTSLO: Linked order activated!\n\n"
                  f"Parent Order: {parent_id}\n"
                  f"Parent Pair: {parent_pair}\n"
                  f"Status: Filled ✓\n\n"
                  f"→ Activated Linked Order:\n"
                  f"Order ID: {linked_id}\n"
                  f"Pair: {linked_pair}\n"
                  f"Status: Now enabled and monitoring\n\n"
                  f"💡 The linked order will trigger when its threshold is met.")
        
        self.notify_event('linked_order_activated', message)
    
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

    def notify_api_error(self, error_type: str, endpoint: str, error_message: str, 
                        details: Optional[Dict] = None):
        """
        Notify about Kraken API errors.
        
        Args:
            error_type: Type of error (timeout, connection, server_error, rate_limit, etc.)
            endpoint: API endpoint that failed
            error_message: Error message
            details: Additional error details (optional)
        """
        icon_map = {
            'timeout': '⏱️',
            'connection': '🔌',
            'server_error': '🔥',
            'rate_limit': '🚦',
            'unknown': '❌'
        }
        
        icon = icon_map.get(error_type, icon_map['unknown'])
        
        message = f"{icon} TTSLO: Kraken API Error\n\n"
        message += f"Error Type: {error_type}\n"
        message += f"Endpoint: {endpoint}\n"
        message += f"Message: {error_message}\n"
        
        if details:
            if 'status_code' in details:
                message += f"Status Code: {details['status_code']}\n"
            if 'timeout' in details:
                message += f"Timeout: {details['timeout']}s\n"
        
        if error_type == 'timeout':
            message += "\n⚠️ This could indicate network issues or Kraken API being slow."
        elif error_type == 'connection':
            message += "\n⚠️ Cannot reach Kraken API. Check your network connection."
        elif error_type == 'server_error':
            message += "\n⚠️ Kraken API is experiencing issues. Service may be down or under maintenance."
        elif error_type == 'rate_limit':
            message += "\n⚠️ API rate limit exceeded. TTSLO will retry with backoff."
        
        self.notify_event('api_error', message)
    
    def send_test_notification(self, health_info: dict) -> dict:
        """
        Send a test notification with health information to all recipients.
        
        Args:
            health_info: Dictionary containing health check information
            
        Returns:
            Dictionary with success status and details for each recipient
        """
        results = {}
        
        # Build health message
        health_status = health_info.get('status', 'unknown')
        checks = health_info.get('checks', {})
        timestamp = health_info.get('timestamp', datetime.now(timezone.utc).isoformat())
        
        status_icon = "✅" if health_status == 'healthy' else "⚠️"
        
        message = (
            f"{status_icon} TTSLO Health Test Notification\n\n"
            f"Status: {health_status.upper()}\n"
            f"Timestamp: {timestamp}\n\n"
            f"Health Checks:\n"
        )
        
        for check_name, check_status in checks.items():
            check_icon = "✓" if check_status else "✗"
            message += f"  {check_icon} {check_name.replace('_', ' ').title()}: {'OK' if check_status else 'FAILED'}\n"
        
        # Add system info if available
        if 'system_info' in health_info:
            message += f"\nSystem Information:\n"
            for key, value in health_info['system_info'].items():
                message += f"  • {key.replace('_', ' ').title()}: {value}\n"
        
        message += f"\nThis is a test notification from TTSLO Dashboard."
        
        # Send to all recipients
        if not self.enabled:
            return {
                'success': False,
                'error': 'Notifications not enabled',
                'details': {}
            }
        
        for username in self.recipients.keys():
            success = self.send_message(username, message)
            results[username] = {
                'success': success,
                'chat_id': self.recipients[username]
            }
        
        return {
            'success': any(r['success'] for r in results.values()),
            'recipients': results,
            'message': message
        }


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

[notify.api_error]
# Notified when Kraken API calls fail
# Triggered by: Timeouts, connection errors, server errors (5xx), rate limiting
# Includes error type, endpoint, and details about the failure
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
# - api_error: "🔌 TTSLO: Kraken API Error - Error Type: connection, Endpoint: Ticker, Message: Failed to connect"
"""
    
    with open(filename, 'w') as f:
        f.write(sample_content)
    
    print(f"Sample notifications configuration created: {filename}")
