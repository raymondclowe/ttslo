# Price Update Frequency Research: Public vs Private Endpoints

## Research Question
How often are prices updated in the public versus the private endpoint, and what's the best way to get real-time price data from Kraken?

## Executive Summary

After testing and researching Kraken's API endpoints, we found:

1. **Both public and private endpoints return the same market price data** - there is no difference in price freshness
2. **REST API polling** provides prices at your polling frequency (limited to ~1 request/second)
3. **WebSocket API** provides true real-time streaming updates triggered by actual market trades
4. **The perceived delay** in REST API polling is due to the polling interval, not the data itself
5. **For real-time price monitoring, use WebSocket API** instead of REST polling

## Detailed Findings

### 1. REST API Public Endpoint Behavior

**Endpoint:** `GET /0/public/Ticker`

**Characteristics:**
- Returns current market snapshot when requested
- Price is fresh and current at the time of the request
- Rate limited to approximately 1 request per second
- Average latency: 200-400ms per request
- Suitable for occasional price checks

**Test Results (30-second sample):**
- Total polls: 30 requests
- Updates per minute: ~60 (one per second)
- Average interval: 0.996 seconds
- Price updates only reflect market changes when polled

**Key Insight:** The REST API doesn't "cache" or "delay" prices. Each request returns the current market price. However, you only see price changes when you poll, so if the market moves between your polls, you miss those changes.

### 2. WebSocket API Public Streaming

**Endpoint:** `wss://ws.kraken.com/` (Ticker channel)

**Characteristics:**
- Establishes persistent connection
- Pushes price updates in real-time as trades occur
- No authentication required for public market data
- Sub-second latency for price updates
- Updates triggered by actual market activity

**Test Results (30-second sample):**
- Total updates received: 11 events
- Updates per minute: ~21 (varies with market activity)
- Average interval: 2.879 seconds (depends on trading volume)
- Minimum interval: 0.015 seconds (sub-second updates possible)
- Maximum interval: 9.026 seconds (during quiet periods)

**Key Insight:** WebSocket updates arrive when trades actually happen, not on a fixed schedule. During active trading, you get updates every few seconds or even multiple times per second. During quiet periods, updates may be 8-10 seconds apart.

### 3. Private vs Public Endpoints for Price Data

**Important Finding:** Private endpoints (authenticated) and public endpoints return the **same market price data**.

**Private endpoints are for:**
- Account management (balances, positions)
- Order placement and management
- Trade history
- Personal account data

**Price data is the same whether accessed via:**
- Public REST API (no authentication)
- Private REST API (authenticated)
- Public WebSocket (no authentication)
- Private WebSocket (authenticated)

**Conclusion:** There is no advantage to using private endpoints for price data. The "delay" observed in the original issue is not related to public vs private endpoints, but rather to the polling method used.

## Why Polling Seems Slower

When polling the REST API every 1-2 minutes (as mentioned in the issue), you will see:
1. Price only updates once every 1-2 minutes (your polling interval)
2. You miss all the price changes that happened between polls
3. It appears "slow" compared to watching a real-time chart

Meanwhile, a website uses WebSocket connections to display prices that update every second or sub-second, creating the perception of a much faster update rate.

## Recommendations

### For Real-Time Price Monitoring (Recommended)
**Use WebSocket API:**
```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    if isinstance(data, list) and len(data) >= 4:
        if data[-2] == 'ticker':
            price = float(data[1]['c'][0])
            print(f"BTC/USD: ${price:,.2f}")

ws = websocket.WebSocketApp(
    "wss://ws.kraken.com/",
    on_message=on_message
)

# Subscribe to ticker
subscribe_msg = {
    "event": "subscribe",
    "pair": ["XBT/USD"],
    "subscription": {"name": "ticker"}
}
ws.on_open = lambda ws: ws.send(json.dumps(subscribe_msg))
ws.run_forever()
```

**Advantages:**
- Real-time updates as trades occur
- No polling overhead
- Sub-second latency
- Automatically pushed to you
- No rate limit concerns

### For Occasional Price Checks
**Use REST API:**
```python
from kraken_api import KrakenAPI

api = KrakenAPI()
price = api.get_current_price('XXBTZUSD')
print(f"Current BTC/USD: ${price:,.2f}")
```

**Advantages:**
- Simple and straightforward
- Good for one-time checks
- No persistent connection needed
- Suitable for periodic monitoring (every few minutes)

## Testing Tools Provided

We've created two testing tools in this repository:

1. **`price_update_frequency_test.py`** - Full 2-minute test comparing REST and WebSocket
2. **`quick_price_test.py`** - Quick 30-second test for faster validation

### Running the Tests

```bash
# Quick 30-second test
uv run python quick_price_test.py

# Full 2-minute test
uv run python price_update_frequency_test.py
```

### Sample Output

The test provides:
- Real-time price updates with timestamps
- Update frequency statistics (avg, min, max intervals)
- Price change detection
- Comparison between REST and WebSocket methods
- Latency measurements

## Technical Details

### REST API Rate Limits
- Public endpoints: ~1 request per second
- Exceeding rate limits causes temporary blocks
- Suitable for polling intervals ≥ 1 second

### WebSocket Connection Details
- Public market data: `wss://ws.kraken.com/`
- Private account data: `wss://ws-auth.kraken.com/`
- Heartbeat every 1 second to maintain connection
- Automatic reconnection recommended for production use

### Ticker Update Triggers (WebSocket)
Updates are pushed when:
1. A trade occurs (default trigger)
2. Best-bid-offer (BBO) changes (if configured)

Configure with:
```json
{
  "event": "subscribe",
  "pair": ["XBT/USD"],
  "subscription": {
    "name": "ticker",
    "event_trigger": "trades"  // or "bbo"
  }
}
```

## Measurement Results Summary

| Metric | REST API (Polling) | WebSocket (Streaming) |
|--------|-------------------|----------------------|
| Update Method | On-demand (you poll) | Push (server sends) |
| Typical Frequency | 60/min (if polling every 1s) | 20-60/min (varies with trades) |
| Latency | 200-400ms per request | Sub-second push |
| Price Freshness | Current when polled | Real-time as trades occur |
| Rate Limit | ~1 req/sec | No limit on receiving |
| Best For | Occasional checks | Real-time monitoring |

## Conclusion

**Answer to the original question:**
- **Public endpoints do NOT delay or cache prices** - they return current market prices
- **Private endpoints provide the same price data** as public endpoints
- **The "1-2 minute delay" observed** is due to polling the API every 1-2 minutes, not a limitation of the endpoint
- **For real-time prices (updating every second)**, use the WebSocket API instead of REST API polling
- **Both methods are accurate**, but WebSocket provides true real-time streaming while REST requires active polling

## References

- [Kraken REST API Documentation](https://docs.kraken.com/api/)
- [Kraken WebSocket API Documentation](https://docs.kraken.com/api/docs/guides/spot-websocket-api)
- [Kraken API Rate Limits](https://support.kraken.com/articles/206548367-what-are-the-api-rate-limits-)
- [WebSocket API FAQ](https://support.kraken.com/articles/360022326871-kraken-websocket-api-frequently-asked-questions)

## Next Steps

If you want to implement real-time price monitoring in this application:
1. Use the provided `price_update_frequency_test.py` as a reference
2. Implement WebSocket client for ticker subscriptions
3. Add reconnection logic for production reliability
4. Consider implementing a price cache to avoid redundant processing
