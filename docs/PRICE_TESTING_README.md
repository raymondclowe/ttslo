# Price Update Frequency Testing and Examples

This directory contains research, testing tools, and examples related to Kraken API price update frequency.

## Quick Summary

**Question:** How often are prices updated in public vs private endpoints?

**Answer:** 
- Both public and private endpoints return the **same** market prices
- REST API returns current prices when polled (you control frequency)
- WebSocket API pushes updates in real-time as trades occur
- The "delay" in REST is due to polling interval, not the endpoint itself

## Files in This Research

### Documentation
- **`PRICE_UPDATE_RESEARCH.md`** - Comprehensive research findings with measurements and analysis

### Testing Tools
1. **`quick_price_test.py`** - Fast 30-second test comparing REST vs WebSocket
2. **`price_update_frequency_test.py`** - Full 2-minute detailed test with statistics

### Examples
3. **`realtime_price_monitor.py`** - Simple real-time price monitor using WebSocket
4. **`websocket_integration_example.py`** - Shows how TTSLO could use WebSocket

## Quick Start

### Run the Quick Test (30 seconds)
```bash
uv run python quick_price_test.py
```

This will:
- Poll REST API once per second for 30 seconds
- Stream WebSocket updates for 30 seconds
- Compare the results
- Show statistics

### Run the Full Test (2 minutes)
```bash
uv run python price_update_frequency_test.py
```

More comprehensive testing with detailed statistics.

### Monitor Real-Time Prices
```bash
uv run python realtime_price_monitor.py
```

Shows live BTC/USD and ETH/USD prices streaming in real-time via WebSocket.
Press Ctrl+C to stop.

### See Integration Example
```bash
# Show comparison
uv run python websocket_integration_example.py --compare

# Run demo integration
uv run python websocket_integration_example.py
```

## Key Findings

### REST API Polling (Current TTSLO Method)
- **Update frequency:** Controlled by you (currently ~60 seconds in TTSLO)
- **Latency:** 200-400ms per request
- **Rate limit:** ~1 request per second
- **Best for:** Periodic monitoring (every minute or so)

**Example measurement:**
```
Total polls:          30 (in 30 seconds)
Updates per minute:   60 (at 1-second interval)
Average latency:      250ms
Price changes seen:   Depends on market activity during polls
```

### WebSocket Streaming (Alternative Method)
- **Update frequency:** Real-time as trades occur (typically every 1-10 seconds)
- **Latency:** Sub-second (< 100ms)
- **Rate limit:** No limit on receiving updates
- **Best for:** Real-time monitoring and trading

**Example measurement:**
```
Total updates:        11 (in 30 seconds)
Updates per minute:   20-60 (varies with trading volume)
Average interval:     2.9 seconds (depends on market activity)
Price changes seen:   Every single trade
```

### Public vs Private Endpoints
**Important:** Both return the same market prices!

- Public endpoints: No authentication needed
- Private endpoints: Authentication required
- **Price data is identical** - private endpoints don't provide "better" prices
- Private endpoints are for account management, not price data

## Sample Output

### Quick Test Results
```
================================================================================
REST API Results
================================================================================
Total Updates:        30
Duration:             28.90 seconds
Unique Prices:        1
Price Range:          $108,000.00 - $108,000.00
Average Price:        $108,000.00

Update Intervals:
  Average:            0.996 seconds
  Median:             1.020 seconds
  Min:                0.565 seconds
  Max:                1.420 seconds
  Updates per minute: 60.22
================================================================================

================================================================================
WebSocket Results
================================================================================
Total Updates:        11
Duration:             28.79 seconds
Unique Prices:        2
Price Range:          $107,999.90 - $108,000.00
Average Price:        $107,999.99

Update Intervals:
  Average:            2.879 seconds
  Median:             1.756 seconds
  Min:                0.015 seconds
  Max:                9.026 seconds
  Updates per minute: 20.84
================================================================================
```

## For TTSLO Application

### Current Implementation (REST Polling)
The current TTSLO application polls the REST API every 60 seconds. This is:
- ✅ Simple and reliable
- ✅ Sufficient for position management
- ✅ Easy to understand and maintain
- ✅ No persistent connections needed

### Potential Enhancement (WebSocket)
WebSocket could provide:
- ⚡ Instant trigger detection (< 1 second)
- ⚡ No polling overhead
- ⚡ See every price movement
- ⚠️ More complex (reconnection handling, etc.)

### Recommendation
**The current REST polling is adequate for TTSLO's use case.**

Consider WebSocket only if you need:
- Sub-minute trigger detection
- Monitoring many trading pairs
- Minimal API rate limit usage

## Requirements

All examples require:
```bash
uv add websocket-client
```

Or:
```bash
pip install websocket-client
```

The existing dependencies (requests, etc.) are already in the project.

## No Credentials Required

All testing tools and examples work without Kraken API credentials because they:
- Use public market data endpoints
- Don't require authentication
- Access the same price data available to everyone

## Understanding the "Delay"

If you observe a "1-2 minute delay" when polling:
1. **It's not the API** - The API returns current prices instantly
2. **It's your polling interval** - If you poll every 1-2 minutes, you only see prices every 1-2 minutes
3. **Websites use WebSocket** - They get updates in real-time as trades occur

To see faster updates:
- Reduce polling interval (down to ~1 second minimum)
- Or use WebSocket for true real-time streaming

## Additional Resources

- [Kraken REST API Documentation](https://docs.kraken.com/api/)
- [Kraken WebSocket API Documentation](https://docs.kraken.com/api/docs/guides/spot-websocket-api)
- [WebSocket API FAQ](https://support.kraken.com/articles/360022326871)
- [API Rate Limits](https://support.kraken.com/articles/206548367)

## Questions?

See `PRICE_UPDATE_RESEARCH.md` for comprehensive documentation of all findings, measurements, and technical details.
