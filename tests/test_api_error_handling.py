#!/usr/bin/env python3
"""
Test suite for Kraken API error handling and notifications.
"""
import json
from unittest.mock import Mock, patch, MagicMock
import pytest
import requests

from kraken_api import (
    KrakenAPI, KrakenAPIError, KrakenAPITimeoutError,
    KrakenAPIConnectionError, KrakenAPIServerError, KrakenAPIRateLimitError
)
from notifications import NotificationManager


class TestKrakenAPIErrorHandling:
    """Test error handling in Kraken API client."""
    
    def test_timeout_error_on_public_endpoint(self):
        """Test timeout error on public API endpoint."""
        with patch('kraken_api.requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
            
            api = KrakenAPI()
            with pytest.raises(KrakenAPITimeoutError) as exc_info:
                api._query_public('Ticker', {'pair': 'XXBTZUSD'})
            
            assert 'timed out' in str(exc_info.value).lower()
            assert exc_info.value.error_type == 'timeout'
            assert 'timeout' in exc_info.value.details
    
    def test_connection_error_on_public_endpoint(self):
        """Test connection error on public API endpoint."""
        with patch('kraken_api.requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")
            
            api = KrakenAPI()
            with pytest.raises(KrakenAPIConnectionError) as exc_info:
                api._query_public('Ticker', {'pair': 'XXBTZUSD'})
            
            assert 'connect' in str(exc_info.value).lower()
            assert exc_info.value.error_type == 'connection'
    
    def test_server_error_500_on_public_endpoint(self):
        """Test 500 server error on public API endpoint."""
        with patch('kraken_api.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_get.return_value = mock_response
            
            api = KrakenAPI()
            with pytest.raises(KrakenAPIServerError) as exc_info:
                api._query_public('Ticker', {'pair': 'XXBTZUSD'})
            
            assert 'server error' in str(exc_info.value).lower()
            assert exc_info.value.error_type == 'server_error'
            assert exc_info.value.details['status_code'] == 500
    
    def test_server_error_502_on_public_endpoint(self):
        """Test 502 bad gateway error on public API endpoint."""
        with patch('kraken_api.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 502
            mock_response.text = "Bad Gateway"
            mock_get.return_value = mock_response
            
            api = KrakenAPI()
            with pytest.raises(KrakenAPIServerError) as exc_info:
                api._query_public('Ticker', {'pair': 'XXBTZUSD'})
            
            assert exc_info.value.details['status_code'] == 502
    
    def test_server_error_503_on_public_endpoint(self):
        """Test 503 service unavailable error on public API endpoint."""
        with patch('kraken_api.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.text = "Service Unavailable"
            mock_get.return_value = mock_response
            
            api = KrakenAPI()
            with pytest.raises(KrakenAPIServerError) as exc_info:
                api._query_public('Ticker', {'pair': 'XXBTZUSD'})
            
            assert exc_info.value.details['status_code'] == 503
    
    def test_rate_limit_error_429_on_public_endpoint(self):
        """Test 429 rate limit error on public API endpoint."""
        with patch('kraken_api.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_get.return_value = mock_response
            
            api = KrakenAPI()
            with pytest.raises(KrakenAPIRateLimitError) as exc_info:
                api._query_public('Ticker', {'pair': 'XXBTZUSD'})
            
            assert 'rate limit' in str(exc_info.value).lower()
            assert exc_info.value.error_type == 'rate_limit'
    
    def test_timeout_error_on_private_endpoint(self):
        """Test timeout error on private API endpoint."""
        with patch('kraken_api.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Connection timeout")
            
            api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
            with pytest.raises(KrakenAPITimeoutError) as exc_info:
                api._query_private('Balance')
            
            assert 'timed out' in str(exc_info.value).lower()
            assert exc_info.value.error_type == 'timeout'
    
    def test_connection_error_on_private_endpoint(self):
        """Test connection error on private API endpoint."""
        with patch('kraken_api.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Failed to connect")
            
            api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
            with pytest.raises(KrakenAPIConnectionError) as exc_info:
                api._query_private('Balance')
            
            assert 'connect' in str(exc_info.value).lower()
            assert exc_info.value.error_type == 'connection'
    
    def test_server_error_on_private_endpoint(self):
        """Test server error on private API endpoint."""
        with patch('kraken_api.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response
            
            api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
            with pytest.raises(KrakenAPIServerError) as exc_info:
                api._query_private('Balance')
            
            assert 'server error' in str(exc_info.value).lower()
            assert exc_info.value.error_type == 'server_error'
            assert exc_info.value.details['status_code'] == 500
    
    def test_rate_limit_error_on_private_endpoint(self):
        """Test rate limit error on private API endpoint."""
        with patch('kraken_api.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_post.return_value = mock_response
            
            api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
            with pytest.raises(KrakenAPIRateLimitError) as exc_info:
                api._query_private('Balance')
            
            assert 'rate limit' in str(exc_info.value).lower()
            assert exc_info.value.error_type == 'rate_limit'
    
    def test_custom_timeout_parameter(self):
        """Test that custom timeout is passed to requests."""
        with patch('kraken_api.requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
            
            api = KrakenAPI()
            with pytest.raises(KrakenAPITimeoutError) as exc_info:
                api._query_public('Ticker', {'pair': 'XXBTZUSD'}, timeout=60)
            
            # Verify timeout was passed to requests.get
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs['timeout'] == 60
            assert exc_info.value.details['timeout'] == 60


class TestNotificationManagerAPIErrors:
    """Test notification manager API error notifications."""
    
    def test_notify_api_error_timeout(self):
        """Test notification for timeout error."""
        nm = NotificationManager()
        nm.enabled = True
        nm.recipients = {'alice': '123456789'}
        nm.subscriptions = {'api_error': ['alice']}
        
        with patch.object(nm, 'send_message') as mock_send:
            mock_send.return_value = True
            
            nm.notify_api_error(
                error_type='timeout',
                endpoint='Ticker',
                error_message='Request timed out after 30s',
                details={'timeout': 30}
            )
            
            mock_send.assert_called_once()
            message = mock_send.call_args[0][1]
            assert '⏱️' in message
            assert 'timeout' in message.lower()
            assert 'Ticker' in message
            assert '30s' in message
            assert 'network issues' in message.lower()
    
    def test_notify_api_error_connection(self):
        """Test notification for connection error."""
        nm = NotificationManager()
        nm.enabled = True
        nm.recipients = {'alice': '123456789'}
        nm.subscriptions = {'api_error': ['alice']}
        
        with patch.object(nm, 'send_message') as mock_send:
            mock_send.return_value = True
            
            nm.notify_api_error(
                error_type='connection',
                endpoint='Balance',
                error_message='Failed to connect to API',
                details={}
            )
            
            mock_send.assert_called_once()
            message = mock_send.call_args[0][1]
            assert '🔌' in message
            assert 'connection' in message.lower()
            assert 'Balance' in message
            assert 'Cannot reach' in message
    
    def test_notify_api_error_server_error(self):
        """Test notification for server error."""
        nm = NotificationManager()
        nm.enabled = True
        nm.recipients = {'alice': '123456789'}
        nm.subscriptions = {'api_error': ['alice']}
        
        with patch.object(nm, 'send_message') as mock_send:
            mock_send.return_value = True
            
            nm.notify_api_error(
                error_type='server_error',
                endpoint='AddOrder',
                error_message='Internal server error',
                details={'status_code': 500}
            )
            
            mock_send.assert_called_once()
            message = mock_send.call_args[0][1]
            assert '🔥' in message
            assert 'server_error' in message.lower()
            assert 'AddOrder' in message
            assert 'Status Code: 500' in message
            assert 'maintenance' in message.lower()
    
    def test_notify_api_error_rate_limit(self):
        """Test notification for rate limit error."""
        nm = NotificationManager()
        nm.enabled = True
        nm.recipients = {'alice': '123456789'}
        nm.subscriptions = {'api_error': ['alice']}
        
        with patch.object(nm, 'send_message') as mock_send:
            mock_send.return_value = True
            
            nm.notify_api_error(
                error_type='rate_limit',
                endpoint='Ticker',
                error_message='API rate limit exceeded',
                details={}
            )
            
            mock_send.assert_called_once()
            message = mock_send.call_args[0][1]
            assert '🚦' in message
            assert 'rate_limit' in message.lower()
            assert 'rate limit exceeded' in message.lower()
            assert 'retry' in message.lower()
    
    def test_notify_api_error_no_subscription(self):
        """Test that no notification is sent if no one is subscribed."""
        nm = NotificationManager()
        nm.enabled = True
        nm.recipients = {'alice': '123456789'}
        nm.subscriptions = {}  # No api_error subscription
        
        with patch.object(nm, 'send_message') as mock_send:
            nm.notify_api_error(
                error_type='timeout',
                endpoint='Ticker',
                error_message='Request timed out',
                details={}
            )
            
            # Should not send message if no subscription
            mock_send.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
