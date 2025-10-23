# WebSocket Price Integration

## Overview

The TTSLO application now uses Kraken's WebSocket API for real-time price monitoring instead of REST API polling. This provides:

- **Instant price updates**: Receive prices as trades occur on Kraken
- **Lower latency**: Sub-second response time after initial connection
- **Efficient monitoring**: No repeated API calls, single persistent connection
- **Automatic fallback**: If WebSocket fails, automatically falls back to REST API

## How It Works

### WebSocket Price Provider

The `WebSocketPriceProvider` class maintains a persistent WebSocket connection to Kraken:

1. **Connection Management**
   - Establishes connection on first price request
   - Maintains single shared connection for all pairs
   - Auto-reconnects if connection drops

2. **Price Subscription**
   - Subscribes to ticker channel for requested trading pairs
   - Converts REST API pair format to WebSocket format automatically
   - Caches prices in memory with thread-safe access

3. **Real-Time Updates**
   - Receives ticker updates as trades occur
   - Updates price cache immediately
   - Provides instant access to latest prices

### Integration with KrakenAPI

The `KrakenAPI` class has been updated:

```python
# WebSocket enabled by default
api = KrakenAPI(use_websocket=True)

# Disable WebSocket (use REST only)
api = KrakenAPI(use_websocket=False)

# Get price (WebSocket if enabled, REST fallback)
price = api.get_current_price('XXBTZUSD')
```

### Price Retrieval Flow

1. **First Request**:
   - Subscribe to WebSocket ticker for pair
   - Wait up to 2 seconds for first update
   - Fall back to REST if no WebSocket data

2. **Subsequent Requests**:
   - Return cached price from WebSocket (instant)
   - No API calls needed

3. **Fallback Behavior**:
   - If WebSocket unavailable: use REST
   - If WebSocket not installed: use REST
   - If explicitly disabled: use REST

## Performance

### Speed Comparison

| Method | First Call | Cached Call |
|--------|-----------|-------------|
| WebSocket | ~1.7s | <0.001s |
| REST API | ~0.27s | ~0.27s |

### Benefits

- **Instant cached access**: 30,000x+ faster than REST for repeat calls
- **Real-time updates**: No polling delay, see every price change
- **Reduced API load**: Single connection vs. repeated requests

## Usage Examples

### Basic Usage

```python
from kraken_api import KrakenAPI

# Create API instance (WebSocket enabled by default)
api = KrakenAPI()

# Get current price
price = api.get_current_price('XXBTZUSD')
print(f"BTC/USD: ${price:,.2f}")
```

### With TTSLO Application

The TTSLO application automatically uses WebSocket:

```bash
# Run TTSLO (WebSocket enabled by default)
python3 ttslo.py --once --verbose

# Disable WebSocket if needed
# (modify code to pass use_websocket=False to KrakenAPI constructor)
```

### Monitoring Multiple Pairs

```python
from kraken_api import KrakenAPI

api = KrakenAPI()

# Subscribe to multiple pairs
pairs = ['XXBTZUSD', 'XETHZUSD', 'XXRPZUSD']

for pair in pairs:
    price = api.get_current_price(pair)
    print(f"{pair}: ${price:,.2f}")

# Subsequent calls are instant (from cache)
for pair in pairs:
    price = api.get_current_price(pair)
    print(f"{pair}: ${price:,.2f}")  # Instant!
```

## Pair Format Conversion

WebSocket uses different pair format than REST API:

| REST Format | WebSocket Format |
|------------|------------------|
| XXBTZUSD | XBT/USD |
| XETHZUSD | ETH/USD |
| XXBTZUSDT | XBT/USDT |

Conversion is handled automatically - you can use REST format everywhere in your code.

## Error Handling

### Connection Errors

If WebSocket connection fails:
1. Logs error (if significant)
2. Attempts to reconnect automatically
3. Falls back to REST API for price requests

### Missing Dependencies

If `websocket-client` is not installed:
- WebSocket is automatically disabled
- REST API is used for all requests
- No errors or warnings

To install WebSocket support:
```bash
pip install websocket-client
# or
uv add websocket-client
```

## Configuration

### Enable/Disable WebSocket

In your code:

```python
# Enable WebSocket (default)
api = KrakenAPI(use_websocket=True)

# Disable WebSocket
api = KrakenAPI(use_websocket=False)
```

For TTSLO application, WebSocket is enabled by default. To disable, modify `ttslo.py`:

```python
# In main() function, when creating KrakenAPI instances:
kraken_api_readonly = KrakenAPI(
    api_key=api_key_ro, 
    api_secret=api_secret_ro,
    use_websocket=False  # Add this line
)
```

## Technical Details

### Thread Safety

- Uses thread-safe locking for price cache access
- WebSocket runs in daemon thread (auto-exits when main thread exits)
- Safe for concurrent access from multiple threads

### Connection Lifecycle

1. **First price request**: Connection established
2. **Subscription**: Subscribe to ticker for pair
3. **Updates**: Receive real-time ticker updates
4. **Reconnection**: Auto-reconnect on disconnect
5. **Shutdown**: Connection closed when program exits

### Resource Usage

- Single WebSocket connection shared across all pairs
- Minimal memory usage (caches only latest price per pair)
- Daemon thread doesn't prevent program exit

## Testing

Run the test suite to verify WebSocket integration:

```bash
# Run all TTSLO tests
python3 -m pytest tests/test_ttslo.py -v

# Run specific test
python3 -m pytest tests/test_ttslo.py::test_threshold_checking -v
```

All existing tests pass with WebSocket enabled.

## Backward Compatibility

- All existing code works without modification
- Tests pass without changes
- REST fallback ensures functionality if WebSocket fails
- Can disable WebSocket if needed

## Troubleshooting

### WebSocket not connecting

Check if `websocket-client` is installed:
```bash
python3 -c "import websocket; print('OK')"
```

If missing:
```bash
pip install websocket-client
```

### Connection keeps dropping

- Check network connectivity
- Verify firewall allows WebSocket connections
- Check Kraken status: https://status.kraken.com/

### Prices not updating

- Ensure WebSocket is enabled: `use_websocket=True`
- Check if pair format is correct (use REST format like 'XXBTZUSD')
- Verify pair is valid on Kraken

## Future Enhancements

Possible future improvements:

1. **Health Monitoring**: Add connection health checks
2. **Metrics**: Track WebSocket uptime and update frequency
3. **Multiple Subscriptions**: Subscribe to more than just ticker (trades, order book)
4. **Configurable Timeout**: Make WebSocket wait timeout configurable

## References

- [Kraken WebSocket API Documentation](https://docs.kraken.com/websockets/)
- [websocket-client Documentation](https://websocket-client.readthedocs.io/)
- [TTSLO README](README.md)
