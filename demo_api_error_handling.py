#!/usr/bin/env python3
"""
Demo script showing Kraken API error handling and notifications.

This script demonstrates how TTSLO handles various API failure scenarios:
- Timeout errors
- Connection errors
- Server errors (5xx)
- Rate limiting (429)
"""
from unittest.mock import Mock, patch
import requests

from kraken_api import (
    KrakenAPI, KrakenAPIError, KrakenAPITimeoutError,
    KrakenAPIConnectionError, KrakenAPIServerError, KrakenAPIRateLimitError
)
from notifications import NotificationManager


def demo_timeout_error():
    """Demonstrate timeout error handling."""
    print("\n" + "="*80)
    print("DEMO 1: Timeout Error")
    print("="*80)
    print("\nScenario: API request takes too long and times out")
    print("-" * 80)
    
    # Mock at the lower level to ensure we catch the timeout
    with patch('kraken_api.requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        api = KrakenAPI(use_websocket=False)  # Disable websocket to test REST API
        try:
            # Call _query_public directly to bypass websocket logic
            api._query_public('Ticker', {'pair': 'XXBTZUSD'})
        except KrakenAPITimeoutError as e:
            print(f"\n✓ Caught KrakenAPITimeoutError:")
            print(f"  Error Type: {e.error_type}")
            print(f"  Message: {str(e)}")
            print(f"  Details: {e.details}")
            print(f"\n✓ System Response:")
            print(f"  - Error logged")
            print(f"  - Notification: '⏱️ This could indicate network issues or Kraken API being slow.'")
            print(f"  - Operation aborted safely")
            print(f"  - Will retry on next cycle")


def demo_connection_error():
    """Demonstrate connection error handling."""
    print("\n" + "="*80)
    print("DEMO 2: Connection Error")
    print("="*80)
    print("\nScenario: Cannot reach Kraken API (network down, DNS failure)")
    print("-" * 80)
    
    with patch('kraken_api.requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Failed to establish connection: [Errno -2] Name or service not known"
        )
        
        api = KrakenAPI()
        try:
            api.get_ticker('XXBTZUSD')
        except KrakenAPIConnectionError as e:
            print(f"\n✓ Caught KrakenAPIConnectionError:")
            print(f"  Error Type: {e.error_type}")
            print(f"  Message: {str(e)}")
            print(f"  Details: {e.details}")
            print(f"\n✓ System Response:")
            print(f"  - Error logged")
            print(f"  - Notification: '🔌 Cannot reach Kraken API. Check your network connection.'")
            print(f"  - Operation aborted safely")
            print(f"  - Will retry on next cycle")


def demo_server_error():
    """Demonstrate server error handling."""
    print("\n" + "="*80)
    print("DEMO 3: Server Error (503 Service Unavailable)")
    print("="*80)
    print("\nScenario: Kraken API is down for maintenance or experiencing issues")
    print("-" * 80)
    
    with patch('kraken_api.requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service Temporarily Unavailable"
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        try:
            api.get_balance()
        except KrakenAPIServerError as e:
            print(f"\n✓ Caught KrakenAPIServerError:")
            print(f"  Error Type: {e.error_type}")
            print(f"  Status Code: {e.details['status_code']}")
            print(f"  Message: {str(e)}")
            print(f"\n✓ System Response:")
            print(f"  - Error logged with status code")
            print(f"  - Notification: '🔥 Kraken API is experiencing issues. Service may be down or under maintenance.'")
            print(f"  - Operation aborted safely")
            print(f"  - Will retry on next cycle")


def demo_rate_limit_error():
    """Demonstrate rate limit error handling."""
    print("\n" + "="*80)
    print("DEMO 4: Rate Limit Error (429)")
    print("="*80)
    print("\nScenario: Too many API requests, rate limit exceeded")
    print("-" * 80)
    
    with patch('kraken_api.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_get.return_value = mock_response
        
        api = KrakenAPI()
        try:
            api.get_ticker('XXBTZUSD')
        except KrakenAPIRateLimitError as e:
            print(f"\n✓ Caught KrakenAPIRateLimitError:")
            print(f"  Error Type: {e.error_type}")
            print(f"  Message: {str(e)}")
            print(f"\n✓ System Response:")
            print(f"  - Error logged")
            print(f"  - Notification: '🚦 API rate limit exceeded. TTSLO will retry with backoff.'")
            print(f"  - Operation aborted safely")
            print(f"  - Will retry on next cycle")


def demo_notification_message():
    """Demonstrate notification message format."""
    print("\n" + "="*80)
    print("DEMO 5: Notification Message Example")
    print("="*80)
    print("\nExample Telegram notification for a timeout error:")
    print("-" * 80)
    
    nm = NotificationManager()
    nm.enabled = True
    nm.recipients = {'alice': '123456789'}
    nm.subscriptions = {'api_error': ['alice']}
    
    # Build a sample notification message
    error_type = 'timeout'
    endpoint = 'Ticker/get_current_price'
    error_message = 'Request to Kraken API timed out after 30s for Ticker'
    details = {'timeout': 30, 'method': 'Ticker'}
    
    icon_map = {
        'timeout': '⏱️',
        'connection': '🔌',
        'server_error': '🔥',
        'rate_limit': '🚦',
    }
    
    icon = icon_map.get(error_type)
    message = f"{icon} TTSLO: Kraken API Error\n\n"
    message += f"Error Type: {error_type}\n"
    message += f"Endpoint: {endpoint}\n"
    message += f"Message: {error_message}\n"
    message += f"Timeout: {details['timeout']}s\n"
    message += "\n⚠️ This could indicate network issues or Kraken API being slow."
    
    print(f"\n{message}")
    print("\n✓ This notification would be sent via Telegram to all subscribed users")


def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("TTSLO API Error Handling Demo")
    print("="*80)
    print("\nThis demo shows how TTSLO handles various Kraken API failures")
    print("and sends notifications to keep you informed.")
    
    demo_timeout_error()
    demo_connection_error()
    demo_server_error()
    demo_rate_limit_error()
    demo_notification_message()
    
    print("\n" + "="*80)
    print("Summary")
    print("="*80)
    print("\nKey Points:")
    print("  1. All API errors are caught and classified by type")
    print("  2. Errors are logged with detailed information")
    print("  3. Telegram notifications keep you informed (if configured)")
    print("  4. System never crashes on API errors - continues monitoring")
    print("  5. Operations are aborted safely - no incorrect orders created")
    print("  6. Automatic retry on next monitoring cycle")
    print("\nTo enable notifications:")
    print("  1. Add [notify.api_error] section to notifications.ini")
    print("  2. Add your username to the users list")
    print("  3. Set TELEGRAM_BOT_TOKEN environment variable")
    print("\nFor more details, see NOTIFICATIONS_README.md")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
