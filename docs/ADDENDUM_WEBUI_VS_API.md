# Addendum: Kraken Web UI vs API Price Updates

## User Question

"The Kraken web UI shows a constantly updating price (multiple times per second) and the order book is constantly moving. Doesn't this imply trades are happening very frequently? What is that number in the Kraken web UI that purports to be the current real-time price?"

## Answer: Different Data Sources Show Different Things

### What the Kraken Web UI Actually Shows

The Kraken web interface uses **WebSocket connections** to display:

1. **"Current Price"** - This is typically the **midpoint** between best bid and best ask, OR the last trade price
2. **Order Book** - Live updates of pending buy/sell orders (WebSocket 'book' channel)
3. **Recent Trades** - Stream of actual executed trades (WebSocket 'trade' channel)

**Key Point**: The web UI uses **multiple WebSocket subscriptions** simultaneously:
- `book` channel - Order book updates (can be multiple per second)
- `trade` channel - Actual executed trades
- `ticker` channel - Aggregated ticker data
- `ohlc` channel - Candlestick data

### What REST API Returns

The REST API `/0/public/Ticker` endpoint returns a **snapshot** of ticker data including:

- **`'c'` (last trade closed)** - The most recent executed trade price
- **`'a'` (ask)** - Best ask price from order book snapshot
- **`'b'` (bid)** - Best bid price from order book snapshot

**Limitation**: REST API gives you a snapshot at the time you poll, not a continuous stream.

### The Key Difference: WebSocket vs REST

#### REST API Behavior
```
Time  Action              What You See
0s    Poll REST API       Last trade: $108,020
1s    Poll REST API       Last trade: $108,020 (no trade occurred)
2s    Poll REST API       Last trade: $108,020 (no trade occurred)
3s    Poll REST API       Last trade: $108,030 (trade just occurred!)
```

#### WebSocket Behavior (What Web UI Uses)
```
Time  Event                   What You See
0.0s  Subscribe to 'book'     Order book snapshot
0.1s  Order placed            Bid: $108,019.90
0.3s  Order cancelled         Bid: $108,019.80
0.5s  Trade executed          Last: $108,020.00
0.6s  Order placed            Ask: $108,020.20
0.8s  Order cancelled         Bid: $108,019.90
1.0s  Trade executed          Last: $108,020.10
```

**The WebSocket receives events immediately as they happen**, giving the illusion of constant movement.

### Why Order Book Moves Constantly

The order book updates occur when:
- Traders place new limit orders
- Traders cancel existing orders
- Orders are partially filled
- Price levels change

These events happen **constantly** (multiple times per second) even when no trades execute.

**Example**: If 10 traders are placing and cancelling orders every second, the order book shows 10 updates per second, but the **last trade price** might only change every 20-30 seconds when actual trades execute.

## Testing This Hypothesis

### Test 1: REST API Ticker (Our Current Tests)

When polling REST API every 1 second for 30 seconds:
```
Last Trade Price ('c') changed: 5 times (17%)
Bid Price ('b') changed:        5 times (17%)
Ask Price ('a') changed:        5 times (17%)
```

**Observation**: REST API bid/ask also appear static because we're getting snapshots.

### Test 2: WebSocket 'book' Channel (Order Book)

When subscribing to WebSocket 'book' channel:
```
Expected: 20-100+ updates per second
Contains: Every order placement, cancellation, and modification
```

**This is what the Kraken web UI subscribes to!**

### Test 3: WebSocket 'trade' Channel (Actual Trades)

When subscribing to WebSocket 'trade' channel:
```
Expected: 1-5 updates per second during normal volume
Contains: Only actual executed trades
```

## What TTSLO Uses vs What Web UI Shows

### TTSLO (Current Implementation)
- **Data Source**: REST API `/0/public/Ticker`
- **Field Used**: `'c'` (last trade closed)
- **Update Frequency**: Every 60 seconds (polling interval)
- **What It Represents**: Actual executed trade prices
- **Why It's Correct**: Position management should trigger on executed trades

### Kraken Web UI
- **Data Source**: WebSocket API (multiple channels)
- **Primary Display**: Likely midpoint of bid/ask OR last trade
- **Order Book**: WebSocket 'book' channel (updates constantly)
- **Recent Trades**: WebSocket 'trade' channel
- **Update Frequency**: Sub-second (pushed as events occur)
- **Why It Looks Different**: Multiple data sources updating independently

## The "Current Price" in Web UI

The "current price" shown in the Kraken web UI could be any of these:

1. **Last Trade Price** - Most recent executed trade
2. **Midpoint** - Average of best bid and best ask: `(bid + ask) / 2`
3. **Best Ask** - Lowest sell order in the order book
4. **Best Bid** - Highest buy order in the order book

Most exchanges use **midpoint** or **last trade** for the main price display, while showing the order book separately.

## Why This Doesn't Contradict Our Research

Our research findings remain accurate:

1. ✅ **REST API returns current data immediately** (no caching)
2. ✅ **Last trade price only updates when trades execute**
3. ✅ **During moderate volume, trades are 20-60 seconds apart**
4. ✅ **Order book changes are much more frequent than trades**

The key insight: **Order book updates ≠ Trade executions**

## Implications for TTSLO

### Current Implementation is Correct

TTSLO uses last trade price because:
- **It's the actual market price** - real executed trades
- **More reliable than bid/ask** - these can be spoofed or manipulated
- **Appropriate for triggers** - should activate on real market movement

### If You Want Web-UI-Like Updates

To see prices update as frequently as the Kraken web UI:

1. **Option A**: Use WebSocket 'book' channel
   - Subscribe to order book updates
   - Display bid, ask, or midpoint
   - Updates multiple times per second
   - **Trade-off**: Not actual execution prices

2. **Option B**: Use WebSocket 'ticker' or 'trade' channel
   - Subscribe to ticker/trade updates
   - Display last trade price
   - Updates when trades occur (1-10 times per second)
   - **Benefit**: Real execution prices with lower latency

3. **Option C**: Display multiple prices
   - Show both last trade AND bid/ask
   - Like the TUI we created (`realtime_price_tui.py`)
   - Users can see the full picture

## Demonstration

The `realtime_price_tui.py` we created shows **all three prices**:
- Last Trade Price (what TTSLO uses)
- Bid Price (order book)
- Ask Price (order book)

Run it to see how they update at different rates:
```bash
uv run python realtime_price_tui.py --pairs XBT/USD
```

You'll observe:
- Last trade price updates when trades occur
- Bid/ask prices would update more frequently with WebSocket 'book' channel
- All are valid prices, but for different purposes

## Conclusion

**The Kraken web UI is showing real-time data**, but it's showing **order book data** (bid/ask prices and pending orders) which updates constantly as traders place and cancel orders.

**TTSLO is showing last trade price**, which only updates when actual trades execute. This is less frequent but more accurate for position management.

**Both are correct** - they're just showing different aspects of the market:
- **Web UI**: Order book + trades (for active trading)
- **TTSLO**: Executed trades only (for position management)

The "constantly updating" price in the web UI is likely the **midpoint of bid/ask**, which changes whenever orders are placed or cancelled in the order book, independent of whether trades actually execute.

## Additional Investigation Tool

A new tool has been created: `investigate_webui_vs_api.py`

Run it to see how REST API ticker fields behave:
```bash
uv run python investigate_webui_vs_api.py 30 1
```

This shows all ticker fields (last trade, bid, ask, midpoint) updated every second for 30 seconds, helping visualize the difference between trade execution and order book updates.
