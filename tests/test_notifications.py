#!/usr/bin/env python3
"""
Tests for notification functionality.
"""
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notifications import NotificationManager, create_sample_notifications_config


def test_notification_manager_disabled_without_config():
    """Test that notification manager is disabled without config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'notifications.ini')
        nm = NotificationManager(config_file=config_file)
        
        assert nm.enabled == False, "Should be disabled without config file"
        
        # Should not crash when calling notify methods
        nm.notify_config_changed()
        nm.notify_validation_errors([])
        nm.notify_trigger_price_reached('test', 'BTC/USD', 50000, 48000, 'above')
        
        print("✓ Notification manager disabled without config test passed")


def test_notification_manager_loads_config():
    """Test that notification manager loads configuration correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'notifications.ini')
        
        # Create a test config file
        with open(config_file, 'w') as f:
            f.write("""[recipients]
alice = 123456789
bob = 987654321

[notify.config_changed]
users = alice, bob

[notify.trigger_reached]
users = alice
""")
        
        # Mock environment variable for token
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test_token'}):
            nm = NotificationManager(config_file=config_file)
            
            assert nm.enabled == True, "Should be enabled with config and token"
            assert 'alice' in nm.recipients, "Should have alice as recipient"
            assert 'bob' in nm.recipients, "Should have bob as recipient"
            assert nm.recipients['alice'] == '123456789', "Alice's chat ID should match"
            assert 'config_changed' in nm.subscriptions, "Should have config_changed subscription"
            assert 'alice' in nm.subscriptions['config_changed'], "Alice should be subscribed to config_changed"
            assert 'bob' in nm.subscriptions['config_changed'], "Bob should be subscribed to config_changed"
            assert 'trigger_reached' in nm.subscriptions, "Should have trigger_reached subscription"
            assert 'alice' in nm.subscriptions['trigger_reached'], "Alice should be subscribed to trigger_reached"
        
        print("✓ Notification manager config loading test passed")


def test_send_message():
    """Test sending a Telegram message."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'notifications.ini')
        
        # Create a test config file
        with open(config_file, 'w') as f:
            f.write("""[recipients]
alice = 123456789
""")
        
        # Mock environment variable and requests.post
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test_token'}):
            with patch('notifications.requests.post') as mock_post:
                # Mock successful response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                nm = NotificationManager(config_file=config_file)
                result = nm.send_message('alice', 'Test message')
                
                assert result == True, "Should return True on success"
                assert mock_post.called, "Should call requests.post"
                
                # Verify the API URL was constructed correctly
                call_args = mock_post.call_args
                # URL is the first positional argument (args) not in kwargs
                url = call_args.kwargs.get('url') or call_args.args[0] if call_args.args else None
                assert url is not None, "URL should be passed"
                assert 'https://api.telegram.org/bot' in url
                assert 'test_token' in url
                
                # Verify message data
                assert call_args.kwargs['data']['chat_id'] == '123456789'
                assert call_args.kwargs['data']['text'] == 'Test message'
        
        print("✓ Send message test passed")


def test_notify_event():
    """Test event notification to multiple users."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'notifications.ini')
        
        # Create a test config file
        with open(config_file, 'w') as f:
            f.write("""[recipients]
alice = 123456789
bob = 987654321

[notify.test_event]
users = alice, bob
""")
        
        # Mock environment variable and requests.post
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test_token'}):
            with patch('notifications.requests.post') as mock_post:
                # Mock successful response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                nm = NotificationManager(config_file=config_file)
                nm.notify_event('test_event', 'Test notification')
                
                # Should be called twice (once for alice, once for bob)
                assert mock_post.call_count == 2, "Should send to both users"
        
        print("✓ Notify event test passed")


def test_create_sample_config():
    """Test creating sample notifications config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = os.path.join(tmpdir, 'notifications.ini.example')
        create_sample_notifications_config(sample_file)
        
        assert os.path.exists(sample_file), "Sample file should be created"
        
        # Verify it's valid INI format
        import configparser
        config = configparser.ConfigParser()
        config.read(sample_file)
        
        assert 'recipients' in config.sections(), "Should have recipients section"
        assert 'notify.config_changed' in config.sections(), "Should have notify sections"
        
        print("✓ Create sample config test passed")


def test_notification_manager_without_token():
    """Test that notification manager is disabled without token."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'notifications.ini')
        
        # Create a test config file
        with open(config_file, 'w') as f:
            f.write("""[recipients]
alice = 123456789
""")
        
        # Make sure token is not in environment
        with patch.dict(os.environ, {}, clear=True):
            nm = NotificationManager(config_file=config_file)
            
            assert nm.enabled == False, "Should be disabled without token"
        
        print("✓ Notification manager without token test passed")


def test_notify_insufficient_balance():
    """Test notification for insufficient balance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'notifications.ini')
        
        # Create config file
        with open(config_file, 'w') as f:
            f.write("""[recipients]
alice = 123456789

[notify.insufficient_balance]
users = alice
""")
        
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test_token'}):
            nm = NotificationManager(config_file=config_file)
            
            assert nm.enabled == True
            
            # Mock the send_message method
            nm.send_message = Mock(return_value=True)
            
            # Call notify_insufficient_balance
            nm.notify_insufficient_balance(
                config_id='test_config',
                pair='XXBTZUSD',
                direction='sell',
                volume='1.0',
                available='0.5',
                trigger_price=50000.0
            )
            
            # Verify message was sent
            nm.send_message.assert_called_once()
            call_args = nm.send_message.call_args[0]
            assert call_args[0] == 'alice'
            message = call_args[1]
            assert 'Insufficient balance' in message
            assert 'test_config' in message
            assert '1.0' in message
            assert '0.5' in message
        
        print("✓ Insufficient balance notification test passed")


def test_notify_order_failed():
    """Test notification for order creation failure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'notifications.ini')
        
        # Create config file
        with open(config_file, 'w') as f:
            f.write("""[recipients]
alice = 123456789

[notify.order_failed]
users = alice
""")
        
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test_token'}):
            nm = NotificationManager(config_file=config_file)
            
            assert nm.enabled == True
            
            # Mock the send_message method
            nm.send_message = Mock(return_value=True)
            
            # Call notify_order_failed
            nm.notify_order_failed(
                config_id='test_config',
                pair='XXBTZUSD',
                direction='sell',
                volume='1.0',
                error='Kraken API error: Insufficient funds',
                trigger_price=50000.0
            )
            
            # Verify message was sent
            nm.send_message.assert_called_once()
            call_args = nm.send_message.call_args[0]
            assert call_args[0] == 'alice'
            message = call_args[1]
            assert 'Order creation failed' in message
            assert 'test_config' in message
            assert 'Insufficient funds' in message
        
        print("✓ Order failed notification test passed")


if __name__ == '__main__':
    test_notification_manager_disabled_without_config()
    test_notification_manager_loads_config()
    test_send_message()
    test_notify_event()
    test_create_sample_config()
    test_notification_manager_without_token()
    test_notify_insufficient_balance()
    test_notify_order_failed()
    print("\n✅ All notification tests passed!")
