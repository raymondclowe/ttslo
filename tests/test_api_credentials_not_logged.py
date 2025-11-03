#!/usr/bin/env python3
"""
Test that API credentials are not logged in debug output.

This test ensures that sensitive information like API keys and signatures
are not exposed in debug logging.
"""
import pytest
from unittest.mock import Mock, patch
from io import StringIO
import sys

from kraken_api import KrakenAPI


class MockResponse:
    """Mock response object for requests."""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = str(json_data)
        self.headers = {}
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class TestCredentialsNotLogged:
    """Test that API credentials are not exposed in logs."""
    
    @patch('kraken_api.requests.post')
    def test_private_api_does_not_log_credentials(self, mock_post, capsys):
        """Test that API-Key and API-Sign are not logged in debug output."""
        # Setup mock response
        mock_response = MockResponse({
            "error": [],
            "result": {
                "XXBT": "10.5000",
                "USDT": "50000.0000"
            }
        })
        mock_post.return_value = mock_response
        
        # Create API client with test credentials
        api_key = "test_api_key_12345"
        api_secret = "dGVzdF9zZWNyZXQ="  # base64 encoded "test_secret"
        api = KrakenAPI(api_key=api_key, api_secret=api_secret)
        
        # Call a private endpoint
        result = api.get_balance()
        
        # Capture all output
        captured = capsys.readouterr()
        all_output = captured.out + captured.err
        
        # Verify API key is NOT in output
        assert api_key not in all_output, "API key should not be logged"
        
        # Verify API secret is NOT in output
        assert api_secret not in all_output, "API secret should not be logged"
        
        # Verify "Headers:" is NOT in output (removed to prevent credential leaks)
        assert "Headers:" not in all_output, "Headers should not be logged (contains credentials)"
        
        # Verify "Payload:" is NOT in output (removed to prevent data leaks)
        assert "Payload:" not in all_output, "Payload should not be logged (may contain sensitive data)"
        
        # Verify safe debug info IS present
        assert "KrakenAPI._query_private: Calling" in all_output, "Should still log API call"
        assert "Response status=" in all_output, "Should still log response status"
    
    @patch('kraken_api.requests.post')
    def test_private_api_does_not_log_signature(self, mock_post, capsys):
        """Test that API-Sign (signature) is not logged in debug output."""
        # Setup mock response
        mock_response = MockResponse({
            "error": [],
            "result": {"open": {}}
        })
        mock_post.return_value = mock_response
        
        # Create API client
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        # Call a private endpoint
        result = api.query_open_orders()
        
        # Capture output
        captured = capsys.readouterr()
        all_output = captured.out + captured.err
        
        # Verify signature-related strings are NOT in output
        assert "API-Sign" not in all_output, "API-Sign should not be logged"
        assert "API-Key" not in all_output, "API-Key should not be logged"
    
    @patch('kraken_api.requests.post')
    def test_response_body_not_logged(self, mock_post, capsys):
        """Test that response body is not logged (might contain sensitive account data)."""
        # Setup mock response with sensitive data
        mock_response = MockResponse({
            "error": [],
            "result": {
                "XXBT": "10.5000",  # Sensitive balance info
                "USDT": "50000.0000"
            }
        })
        mock_post.return_value = mock_response
        
        # Create API client
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        # Call endpoint
        result = api.get_balance()
        
        # Capture output
        captured = capsys.readouterr()
        all_output = captured.out + captured.err
        
        # Verify response body is NOT logged
        assert "Response body=" not in all_output, "Response body should not be logged"
        assert "Response headers=" not in all_output, "Response headers should not be logged"
        
        # But status should still be logged
        assert "Response status=200" in all_output, "Response status should be logged"
    
    @patch('kraken_api.requests.post')
    def test_nonce_not_logged_in_payload(self, mock_post, capsys):
        """Test that nonce (from payload) is not logged."""
        # Setup mock response
        mock_response = MockResponse({"error": [], "result": {}})
        mock_post.return_value = mock_response
        
        # Create API client
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        # Call endpoint
        result = api.get_balance()
        
        # Capture output
        captured = capsys.readouterr()
        all_output = captured.out + captured.err
        
        # Verify payload with nonce is NOT logged
        assert '"nonce":' not in all_output, "Nonce in payload should not be logged"
        assert "Payload:" not in all_output, "Payload debug line should be removed"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
