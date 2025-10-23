#!/usr/bin/env python3
"""
Test suite for notification queue functionality.
"""
import json
import os
import tempfile
from unittest.mock import Mock, patch
import pytest
import requests

from notifications import NotificationManager


class TestNotificationQueue:
    """Test notification queueing when Telegram is unreachable."""
    
    def test_queue_on_timeout(self):
        """Test that notifications are queued when Telegram times out."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as qf:
            queue_file = qf.name
        
        try:
            nm = NotificationManager(queue_file=queue_file)
            nm.enabled = True
            nm.recipients = {'alice': '123456789'}
            nm.telegram_token = 'test_token'
            
            with patch('notifications.requests.post') as mock_post:
                mock_post.side_effect = requests.exceptions.Timeout('Connection timeout')
                
                result = nm.send_message('alice', 'test message')
                
                assert result == False, 'Should return False on timeout'
                assert len(nm.notification_queue) == 1, 'Should queue the notification'
                assert nm.notification_queue[0]['username'] == 'alice'
                assert nm.notification_queue[0]['message'] == 'test message'
                assert nm.notification_queue[0]['reason'] == 'timeout'
                assert nm.telegram_unreachable_since is not None
        finally:
            if os.path.exists(queue_file):
                os.remove(queue_file)
    
    def test_queue_on_connection_error(self):
        """Test that notifications are queued on connection error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as qf:
            queue_file = qf.name
        
        try:
            nm = NotificationManager(queue_file=queue_file)
            nm.enabled = True
            nm.recipients = {'alice': '123456789'}
            nm.telegram_token = 'test_token'
            
            with patch('notifications.requests.post') as mock_post:
                mock_post.side_effect = requests.exceptions.ConnectionError('Network down')
                
                result = nm.send_message('alice', 'test message')
                
                assert result == False
                assert len(nm.notification_queue) == 1
                assert nm.notification_queue[0]['reason'] == 'connection_error'
        finally:
            if os.path.exists(queue_file):
                os.remove(queue_file)
    
    def test_queue_persistence(self):
        """Test that queue is saved to disk and loaded on restart."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as qf:
            queue_file = qf.name
        
        try:
            # First instance - queue a notification
            nm1 = NotificationManager(queue_file=queue_file)
            nm1.enabled = True
            nm1.recipients = {'alice': '123456789'}
            nm1.telegram_token = 'test_token'
            
            with patch('notifications.requests.post') as mock_post:
                mock_post.side_effect = requests.exceptions.Timeout('timeout')
                nm1.send_message('alice', 'queued message')
            
            assert len(nm1.notification_queue) == 1
            
            # Second instance - should load the queue
            nm2 = NotificationManager(queue_file=queue_file)
            nm2.enabled = True
            nm2.recipients = {'alice': '123456789'}
            nm2.telegram_token = 'test_token'
            
            assert len(nm2.notification_queue) == 1
            assert nm2.notification_queue[0]['message'] == 'queued message'
            assert nm2.telegram_was_unreachable == True
        finally:
            if os.path.exists(queue_file):
                os.remove(queue_file)
    
    def test_flush_queue_on_success(self):
        """Test that queued notifications are sent when Telegram becomes reachable."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as qf:
            queue_file = qf.name
        
        try:
            nm = NotificationManager(queue_file=queue_file)
            nm.enabled = True
            nm.recipients = {'alice': '123456789'}
            nm.telegram_token = 'test_token'
            
            # First, queue some notifications
            with patch('notifications.requests.post') as mock_post:
                mock_post.side_effect = requests.exceptions.Timeout('timeout')
                nm.send_message('alice', 'message 1')
                nm.send_message('alice', 'message 2')
            
            assert len(nm.notification_queue) == 2
            
            # Now simulate Telegram becoming reachable
            with patch('notifications.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {'ok': True}
                mock_response.text = '{"ok": true}'
                mock_post.return_value = mock_response
                
                # Send a new message - this should flush the queue
                result = nm.send_message('alice', 'new message')
                
                assert result == True
                # Should have sent: queued message 1, queued message 2, recovery notification, new message
                assert mock_post.call_count >= 3
        finally:
            if os.path.exists(queue_file):
                os.remove(queue_file)
    
    def test_recovery_notification_includes_downtime(self):
        """Test that recovery notification includes downtime duration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as qf:
            queue_file = qf.name
        
        try:
            nm = NotificationManager(queue_file=queue_file)
            nm.enabled = True
            nm.recipients = {'alice': '123456789'}
            nm.telegram_token = 'test_token'
            
            # Queue a notification
            with patch('notifications.requests.post') as mock_post:
                mock_post.side_effect = requests.exceptions.Timeout('timeout')
                nm.send_message('alice', 'queued')
            
            # Simulate Telegram becoming reachable
            with patch('notifications.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {'ok': True}
                mock_response.text = '{"ok": true}'
                mock_post.return_value = mock_response
                
                nm.send_message('alice', 'new message')
                
                # Check that a recovery notification was sent
                calls = mock_post.call_args_list
                recovery_found = False
                for call in calls:
                    if 'data' in call[1]:
                        message = call[1]['data'].get('text', '')
                        if 'Telegram notifications restored' in message:
                            recovery_found = True
                            assert 'unavailable for' in message
                            assert 'queued notification' in message
                            break
                
                assert recovery_found, 'Recovery notification should be sent'
        finally:
            if os.path.exists(queue_file):
                os.remove(queue_file)
    
    def test_multiple_queued_notifications(self):
        """Test queueing multiple notifications from different sources."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as qf:
            queue_file = qf.name
        
        try:
            nm = NotificationManager(queue_file=queue_file)
            nm.enabled = True
            nm.recipients = {'alice': '123', 'bob': '456'}
            nm.telegram_token = 'test_token'
            
            with patch('notifications.requests.post') as mock_post:
                mock_post.side_effect = requests.exceptions.ConnectionError('down')
                
                nm.send_message('alice', 'message for alice')
                nm.send_message('bob', 'message for bob')
                nm.send_message('alice', 'another for alice')
            
            assert len(nm.notification_queue) == 3
            
            # Verify each message is in the queue
            messages = [item['message'] for item in nm.notification_queue]
            assert 'message for alice' in messages
            assert 'message for bob' in messages
            assert 'another for alice' in messages
        finally:
            if os.path.exists(queue_file):
                os.remove(queue_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
