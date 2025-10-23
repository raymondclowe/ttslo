# Kraken API Testing Guide

## Overview

The Kraken API client (`kraken_api.py`) now includes proper JSON-based request formatting and comprehensive test coverage with mocked API responses.

## Changes Made

### 1. Fixed Request Format and Signing

The API client was updated to match Kraken's actual API requirements:

- **Request Body Format**: Changed from URL-encoded form data to JSON format with `Content-Type: application/json`
- **Signature Generation**: Updated to sign JSON string instead of URL-encoded data
- **Signature Algorithm**: `HMAC-SHA512(path + SHA256(nonce + json_data), base64_decode(secret))`

### 2. Added Order Management Methods

New methods for managing orders:

- `query_open_orders(trades=False, userref=None)` - Query currently open orders
- `cancel_order(txid)` - Cancel an order by transaction ID
- `edit_order(txid, pair=None, volume=None, price=None, **kwargs)` - Edit an existing order

### 3. Base URL Override for Testing

The `KrakenAPI` constructor accepts a `base_url` parameter, allowing you to:

- Use a mock server for integration testing
- Test against a staging environment
- Run tests without hitting production API

```python
# Production (default)
api = KrakenAPI(api_key="...", api_secret="...")

# Testing with mock server
api = KrakenAPI(
    api_key="test_key",
    api_secret="test_secret",
    base_url="http://localhost:8080"
)
```

## Test Suite

### Running Tests

```bash
# Run all Kraken API tests
uv run pytest tests/test_kraken_api.py -v

# Run all tests
uv run pytest -q

# Run specific test class
uv run pytest tests/test_kraken_api.py::TestKrakenAPIPublic -v
```

### Test Coverage

The test suite (`tests/test_kraken_api.py`) includes 25 comprehensive tests:

#### Public Endpoints
- ✓ Initialization with default and custom base URLs
- ✓ Get ticker information
- ✓ Get current price with validation
- ✓ Error handling for invalid parameters

#### Private Endpoints
- ✓ Get account balance
- ✓ Get trade balance
- ✓ Query open orders (with and without parameters)
- ✓ Add orders (market, limit, trailing-stop)
- ✓ Cancel orders
- ✓ Edit orders
- ✓ Authentication requirements

#### Signature Generation
- ✓ Correct signature format
- ✓ Different data produces different signatures
- ✓ Base64 encoding validation

#### Error Handling
- ✓ HTTP errors (404, 500, etc.)
- ✓ API errors from Kraken
- ✓ Parameter validation
- ✓ Missing credentials

### Mock Response Pattern

All tests use the `MockResponse` class to simulate API responses:

```python
from unittest.mock import patch

@patch('kraken_api.requests.post')
def test_example(mock_post):
    mock_response = MockResponse({
        "error": [],
        "result": {"key": "value"}
    })
    mock_post.return_value = mock_response
    
    api = KrakenAPI(api_key="test", api_secret="test")
    result = api.some_method()
    
    assert result['key'] == 'value'
```

## Integration Testing with Mock Server

For integration testing, you can create a mock HTTP server:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading

class MockKrakenHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if '/0/private/Balance' in self.path:
            response = {
                "error": [],
                "result": {"XXBT": "10.5000"}
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

# Start mock server
server = HTTPServer(('localhost', 8765), MockKrakenHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()

# Test with mock server
api = KrakenAPI(
    api_key="test",
    api_secret="test",
    base_url="http://localhost:8765"
)
balance = api.get_balance()
```

## API Method Examples

### Public Methods

```python
from kraken_api import KrakenAPI

api = KrakenAPI()

# Get ticker information
ticker = api.get_ticker('XBTUSDT')

# Get current price
price = api.get_current_price('XBTUSDT')
print(f"Current BTC/USDT price: ${price:,.2f}")
```

### Private Methods

```python
from kraken_api import KrakenAPI

api = KrakenAPI(
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# Get account balance
balance = api.get_balance()
print(f"BTC Balance: {balance.get('XXBT', '0')}")

# Query open orders
orders = api.query_open_orders()
for order_id, order in orders.get('open', {}).items():
    print(f"Order {order_id}: {order['descr']['order']}")

# Add a limit order
result = api.add_order(
    pair='XBTUSDT',
    order_type='limit',
    direction='buy',
    volume=0.001,
    price='45000.0'
)
print(f"Order placed: {result['txid']}")

# Add a trailing stop loss order
result = api.add_trailing_stop_loss(
    pair='XBTUSDT',
    direction='sell',
    volume=0.001,
    trailing_offset_percent=5.0
)

# Cancel an order
result = api.cancel_order('ORDER-ID-HERE')
print(f"Order cancelled: {result}")

# Edit an order
result = api.edit_order(
    txid='ORDER-ID-HERE',
    pair='XBTUSDT',
    volume=0.002,
    price='46000.0'
)
```

## Security Notes

1. **Never commit API keys** - Always use environment variables or secure configuration
2. **Test with mock data** - Use the test suite with mocked responses for CI/CD
3. **Validate inputs** - All methods include parameter validation
4. **Error handling** - All methods raise exceptions on API errors

## Sample Test Vectors

For signature validation, here's a test vector:

```python
urlpath = '/0/private/Balance'
nonce = '1234567890000'
data = '{"nonce": "1234567890000"}'
api_secret = base64.b64encode(b"test_secret_key").decode()

signature = api._get_kraken_signature(urlpath, data, nonce)
# signature should be a valid base64-encoded HMAC-SHA512 hash
```

## Troubleshooting

### Common Issues

1. **"API key and secret required"**
   - Solution: Pass credentials to `KrakenAPI()` constructor

2. **"Invalid signature"**
   - Solution: Ensure API secret is base64-encoded
   - Solution: Check that request format matches (JSON, not form data)

3. **Tests failing on signature generation**
   - Solution: Verify the signature method signature: `_get_kraken_signature(urlpath, data, nonce)`

### Debug Tips

```python
# Enable request logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Print request details in tests
call_args = mock_post.call_args
print(f"URL: {call_args[0][0]}")
print(f"Headers: {call_args[1]['headers']}")
print(f"Data: {call_args[1]['data']}")
```

## Resources

- [Kraken API Documentation](https://docs.kraken.com/api/)
- [Kraken REST Authentication](https://docs.kraken.com/api/docs/guides/global-intro/authentication)
- Sample implementation: `api-docs/add-order-sample.py`
- Sample implementation: `api-docs/query-open-orders-sample.py`
