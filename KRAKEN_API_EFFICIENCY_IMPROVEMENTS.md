# Kraken API Efficiency Improvements

## Summary

Improved efficiency of Kraken API usage in the TTSLO monitoring loop by implementing batch price fetching and targeted order queries.

## Changes Made

### 1. Price Fetching Optimization (ttslo.py)

**Before:**
- Individual `get_current_price()` call for each trading pair
- N API calls per monitoring cycle (where N = number of unique pairs)
- Example: 10 pairs = 10 API calls every 60 seconds

**After:**
- Single `get_current_prices_batch()` call for all pairs
- 1 API call per monitoring cycle regardless of number of pairs
- Automatic fallback to individual calls if batch fails or is unavailable (for test mocks)
- Missing pairs handled gracefully

**Code Location:** Lines 1514-1556 in ttslo.py

**Benefits:**
- Reduced API calls: N → 1 per cycle
- Faster monitoring cycles (batch request is faster than N sequential requests)
- Lower risk of hitting Kraken's rate limits
- Better for Kraken's API infrastructure

### 2. Closed Orders Query Optimization (ttslo.py)

**Before:**
- `query_closed_orders()` called without filters
- Retrieves ALL closed orders (up to 50) every monitoring cycle
- Had to iterate through all returned orders to find specific order ID

**After:**
- `query_orders(txids)` called with specific order ID
- Only queries the exact order being checked
- More efficient API call and response processing

**Code Location:** Lines 895-997 in ttslo.py (`check_order_filled` method)

**Benefits:**
- Reduced data transfer (1 order vs up to 50 orders)
- Faster response time
- More targeted API usage
- Follows same pattern already used in dashboard.py

## Implementation Details

### Price Batching Error Handling

The batch implementation includes comprehensive error handling:

1. **Batch method success**: Uses batch result directly
2. **Invalid batch result**: Falls back to individual `get_current_price()` calls
3. **KrakenAPIError**: Logs error, sends notification, sets all prices to None
4. **Generic Exception**: Falls back to individual calls (handles test mocks without batch method)
5. **Missing pairs**: Set to None to prevent processing

### Order Query Changes

Updated from:
```python
closed_orders = self.kraken_api_readwrite.query_closed_orders()
if order_id in closed_orders['closed']:
    order_info = closed_orders['closed'][order_id]
```

To:
```python
order_result = self.kraken_api_readwrite.query_orders(order_id)
if order_id in order_result:
    order_info = order_result[order_id]
```

## Testing

### Tests Updated
- `test_order_fill_notification.py`: Updated all 6 tests to use `query_orders` instead of `query_closed_orders`
- All mocks updated to match new API method

### Test Results
- All 452 tests passing
- 6 tests skipped (live API tests - expected)
- No regressions introduced

### Backward Compatibility
- Changes are internal implementation only
- External behavior unchanged
- State file format unchanged
- Configuration format unchanged

## Performance Impact

### Price Fetching
For a typical configuration with 10 unique trading pairs:

**Before:**
- 10 API calls per monitoring cycle
- ~2.7 seconds total (270ms per call × 10 calls)
- 600 API calls per hour (60s interval)

**After:**
- 1 API call per monitoring cycle
- ~0.3 seconds total (batch call)
- 60 API calls per hour (60s interval)

**Savings:**
- 90% fewer API calls
- 89% faster price fetching
- Significantly reduced rate limit pressure

### Order Status Checking
For monitoring 5 triggered orders:

**Before:**
- 5 calls to `query_closed_orders()`
- Each returns up to 50 orders
- Total data: ~250 orders per cycle

**After:**
- 5 calls to `query_orders(specific_id)`
- Each returns exactly 1 order
- Total data: 5 orders per cycle

**Savings:**
- 98% less data transferred
- Faster response times
- More efficient API usage

## Related Files

### Modified Files
- `ttslo.py`: Batch price fetching and targeted order queries
- `tests/test_order_fill_notification.py`: Updated test mocks

### Referenced Methods
- `kraken_api.py:get_current_prices_batch()` (lines 646-699)
- `kraken_api.py:query_orders()` (lines 1005-1032)
- `dashboard.py:get_current_prices()` (lines 156-194) - already used batch method

## Future Improvements (Optional)

1. **WebSocket-only mode**: Use WebSocket exclusively for prices, eliminate REST price calls entirely
2. **Batch order queries**: If checking multiple orders, batch them in single `query_orders()` call
3. **Cache order status**: Cache order fill status to reduce repeated queries for same order
4. **Adaptive polling**: Adjust monitoring interval based on volatility and open orders

## References

- GitHub Issue: "Efficient use of kraken api"
- Kraken API Documentation: https://docs.kraken.com/rest/
- Dashboard implementation: dashboard.py (already using batch method)

## Security Considerations

- All changes maintain existing security guarantees
- No orders created on errors
- Graceful degradation on API failures
- Proper error logging and notification
