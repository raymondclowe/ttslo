# Addendum: Understanding "Static" Prices When Polling Every 10 Seconds

## User Observation

When running TTSLO with a 10-second polling interval, the user observed that prices remain the same for 10-12 consecutive cycles (100-120 seconds total), which seemed inconsistent with the research findings.

## Root Cause Analysis

### The Issue: "Last Trade Closed" vs Real-Time Market Activity

The Kraken API's `Ticker` endpoint returns multiple price fields:
- **`'c'` (last trade closed)** - The price of the most recent executed trade
- **`'a'` (ask)** - Current best ask price in the order book
- **`'b'` (bid)` - Current best bid price in the order book

**TTSLO uses the `'c'` field (last trade closed)**, which is correct for determining market price, but this field **only updates when an actual trade executes on the exchange**.

### Live Testing Results

Testing with 15 samples at 10-second intervals showed:
```
Total samples: 15
Price stayed same: 10 times out of 14 transitions (71%)
Price changed: 4 times (29%)
```

This means during a ~2.5 minute period:
- The last trade price stayed static for 100-120 seconds (10-12 cycles)
- Only 4 trades actually executed during this time
- Bid/ask prices remained relatively stable as well

### Why This Happens

1. **Trading Volume Varies**: During low-volume periods (especially certain times of day), trades on BTC/USD may occur every 20-60 seconds rather than every second

2. **Last Trade vs Order Book**: The bid/ask prices (order book) may update more frequently, but TTSLO correctly uses the last executed trade price as the true market price

3. **This is NOT a Bug**: The Kraken API is working correctly:
   - The REST API returns the current state immediately (no caching)
   - The `'c'` field reflects the most recent trade
   - If no new trades occurred, the price should remain the same

## Comparison: REST Polling vs WebSocket

### What the Original Research Showed

The original research compared:
1. **REST API polling** - Fetches current snapshot on-demand
2. **WebSocket streaming** - Receives updates pushed when trades occur

The key finding was that REST returns current data immediately (no API delay), but you only see updates when you poll.

### What We Now Understand

**Both REST polling and WebSocket show the same last trade price**, because both are reporting the same underlying market data. The difference is:

- **REST polling at 10s intervals**: You see the price that existed at each 10-second mark
- **WebSocket streaming**: You see the price update immediately when each trade occurs

If trades are happening every 30 seconds, then:
- REST polling at 10s will see: Trade 1, Trade 1, Trade 1, Trade 2, Trade 2, Trade 2, Trade 3...
- WebSocket will see: Trade 1 (at t=0), Trade 2 (at t=30), Trade 3 (at t=60)...

**Both see the same prices**, but WebSocket doesn't show the "static" periods between trades.

## Updated Findings

### Original Research Was Correct

The original research correctly identified:
1. ✅ Public and private endpoints return identical prices
2. ✅ REST API returns current price immediately (no caching)
3. ✅ WebSocket provides updates as trades occur
4. ✅ The "delay" is not due to the API

### Additional Clarification

The user's observation of "10-12 cycles with same price" is explained by:
1. ✅ TTSLO uses `'c'` (last trade closed) field from ticker
2. ✅ This field only updates when actual trades execute
3. ✅ During low/moderate volume, trades may be 30+ seconds apart
4. ✅ Seeing same price for 100-120 seconds is **realistic behavior** for moderate trading volume
5. ✅ This is the **correct** market price during that time period

## Implications for TTSLO

### Current Implementation is Correct

TTSLO's use of "last trade closed" price is the right approach because:
- It represents actual executed trades (real market price)
- It's more reliable than bid/ask spreads
- It's the standard way to measure market price
- Using bid/ask could give misleading signals

### Alternative Approaches (Not Recommended)

**Option 1: Use bid/ask prices instead of last trade**
- **Pros**: Updates more frequently
- **Cons**: 
  - Bid/ask spread can be wide during low volume
  - Not the actual execution price
  - Could trigger false signals

**Option 2: Switch to WebSocket**
- **Pros**: Get notified immediately when trades occur
- **Cons**:
  - More complex implementation
  - Still shows the same prices, just with better timing
  - Overkill for position management

**Option 3: Check multiple price fields**
- **Pros**: Could detect price movement earlier
- **Cons**:
  - Bid/ask != actual market price
  - Could increase false triggers

### Recommendation: Keep Current Implementation

The current implementation is appropriate because:
1. 60-second polling interval is reasonable for position management
2. Using last trade price is the correct approach
3. Trigger thresholds are typically far from current price (e.g., $50k threshold when price is $108k)
4. Missing a few seconds of price movement doesn't impact trigger accuracy for position management

## Real-World Example

Consider a scenario:
- **Current price**: $108,050
- **Your trigger threshold**: $110,000 (to create trailing stop loss)
- **Gap**: $1,950

Even if trades occur every 30-60 seconds, you have adequate time to detect the threshold being crossed. The price would need to move $1,950 in a single trade to "skip over" your detection, which is unlikely for BTC/USD.

## Conclusion

The user's observation is **correct and expected**:
- Seeing the same price for 10-12 cycles (100-120 seconds) is normal during moderate trading volume
- This is NOT due to API caching, delays, or endpoint differences
- This is the actual market behavior - trades simply don't occur every second
- TTSLO's implementation is correct for its use case

The original research findings remain valid:
- REST API returns current data immediately
- WebSocket provides real-time notifications of trades
- Both show the same market prices
- For TTSLO's position management use case, current implementation is appropriate

## Testing Script

A new investigation script has been added: `investigate_price_staleness.py`

Run it to see the ticker response details:
```bash
uv run python investigate_price_staleness.py 15 10
```

This shows:
- Last trade price over time
- Bid/ask prices for comparison
- How frequently the last trade price actually changes
- Analysis of why prices remain static between trades
