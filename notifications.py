"""
Telegram notification system for TTSLO.

Simple notification implementation following the pattern from
@raymondclowe/telegram-send-file/tgsnd.py
"""
import os
import configparser
import requests
from typing import Dict, List, Optional


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
            return False
        
        if username not in self.recipients:
            print(f"Warning: Unknown notification recipient: {username}")
            return False
        
        chat_id = self.recipients[username]
        
        try:
            url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
            response = requests.post(url, data={'chat_id': chat_id, 'text': message}, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                print(f"Warning: Failed to send Telegram message: {response.text}")
                return False
                
        except Exception as e:
            print(f"Warning: Exception sending Telegram message: {e}")
            return False
    
    def notify_event(self, event_type: str, message: str):
        """
        Send notification for a specific event type to all subscribed users.
        
        Args:
            event_type: Type of event (e.g., 'config_changed', 'validation_error')
            message: Message to send
        """
        if not self.enabled:
            return
        
        if event_type not in self.subscriptions:
            return
        
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
                                pair: str, fill_price: Optional[float] = None):
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
        
        if fill_price:
            message += f"\nFill Price: {fill_price}"
        
        self.notify_event('tsl_filled', message)
    
    def notify_application_exit(self, reason: str = "unknown"):
        """
        Notify that the application has exited.
        
        Args:
            reason: Reason for exit
        """
        message = f"🛑 TTSLO: Application has exited.\n\nReason: {reason}"
        self.notify_event('app_exit', message)


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

[notify.config_changed]
# Notified when config.csv is modified
users = 

[notify.validation_error]
# Notified when config.csv has validation errors
users = 

[notify.trigger_reached]
# Notified when a trigger price is reached
users = 

[notify.tsl_created]
# Notified when a TSL order is created on Kraken
users = 

[notify.tsl_filled]
# Notified when a TSL order is filled
users = 

[notify.app_exit]
# Notified when the application exits or crashes
# Note: This only works if the app exits gracefully
users = 

# To enable notifications:
# 1. Copy this file to notifications.ini
# 2. Add recipient usernames and their Telegram chat IDs in [recipients]
# 3. Add usernames to the event types you want to be notified about
# 4. Set environment variable: TELEGRAM_BOT_TOKEN=your_bot_token
#    (Get a bot token from @BotFather on Telegram)
"""
    
    with open(filename, 'w') as f:
        f.write(sample_content)
    
    print(f"Sample notifications configuration created: {filename}")
