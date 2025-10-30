# LEARNINGS

Key learnings and gotchas discovered during TTSLO development.

## Statistical Distribution Display in HTML Reports (2025-10-30)

**Feature**: Enhanced HTML report in coin_stats.py to display which statistical distribution was used for analysis.

**Background**:
- coin_stats.py already implemented Student's t-distribution testing
- Best-fit distribution was selected and used for probability calculations
- However, HTML report only showed "Normal Distribution?" (yes/no)
- Users couldn't see which specific distribution was actually used

**Solution**:
1. Added "Distribution Used" row showing best-fit distribution:
   - "Normal (Gaussian)" for normal distributions
   - "Fat tails (Student-t, df=X)" for fat-tailed distributions
   - "Student-t (df=X)" for Student's t-distributions
   - "Insufficient data" when sample size < 30

2. Added "Threshold Distribution" row showing distribution used for probability threshold calculations

3. Consistent color coding:
   - Green (`normal-yes`) for normal distributions
   - Red (`normal-no`) for non-normal distributions
   - Applied to both "Distribution Used" and "Threshold Distribution" fields

**Implementation Details**:
```python
# Extract distribution info from stats
dist_fit = stats.get('distribution_fit', {})
if dist_fit.get('best_fit') == 'student_t':
    df = dist_fit.get('df', '?')
    if dist_fit.get('distribution') == 'fat_tails':
        dist_text = f'Fat tails (Student-t, df={df})'
    # ...

# Apply color coding to threshold distribution
thresh_dist_class = 'normal-yes' if 'normal' in thresh_dist.lower() else 'normal-no'
```

**Testing**:
- Added `test_html_report_shows_distribution()` in test_coin_stats.py
- Verified HTML contains both distribution fields
- Manual testing confirmed proper formatting for all cases
- All 17 tests pass, no regressions

**Key Insights**:
1. **Transparency**: Users can now see which statistical model is being used
2. **Consistency**: Same color coding across all distribution-related fields
3. **Minimal Changes**: Only 85 lines added, no breaking changes
4. **Already Implemented**: Most of the feature was already coded, just needed UI display

**Related Files**:
- `tools/coin_stats.py`: Lines 812-828, 868-871, 877-890
- `tests/test_coin_stats.py`: test_html_report_shows_distribution()

---

## Kraken API Efficiency - Batch Price Fetching and Targeted Order Queries (2025-10-27)

**Feature**: Optimized Kraken API usage by implementing batch price fetching and targeted order queries in the monitoring loop.

**Problem**:
- Price fetching: Individual `get_current_price()` calls for each pair (N API calls per cycle)
- Order status: `query_closed_orders()` retrieved ALL closed orders (up to 50) just to check 1 order
- Inefficient API usage leading to unnecessary rate limit pressure

**Solution**:

1. **Batch Price Fetching** (ttslo.py lines 1514-1556):
   - Changed from N individual `get_current_price()` calls to 1 `get_current_prices_batch()` call
   - Reduced API calls from N → 1 per monitoring cycle
   - Automatic fallback to individual calls if batch fails or unavailable
   - Graceful handling of missing pairs

2. **Targeted Order Queries** (ttslo.py lines 895-997):
   - Changed from `query_closed_orders()` to `query_orders(specific_id)`
   - Only queries the exact order being checked
   - Reduced data transfer from 50 orders → 1 order per check
   - Follows pattern already used in dashboard.py

**Implementation Details**:

```python
# Price batching with comprehensive error handling
if pairs_to_fetch:
    try:
        prices_result = self.kraken_api_readonly.get_current_prices_batch(pairs_to_fetch)
        if prices_result and isinstance(prices_result, dict):
            prices = prices_result
        else:
            # Fallback to individual fetches (handles test mocks)
            for pair in pairs_to_fetch:
                prices[pair] = self.kraken_api_readonly.get_current_price(pair)
    except KrakenAPIError as e:
        # Log error, send notification, set all to None
    except Exception as e:
        # Fallback to individual fetches
```

```python
# Targeted order query
order_result = self.kraken_api_readwrite.query_orders(order_id)
if order_id in order_result:
    order_info = order_result[order_id]
```

**Performance Impact**:

For 10 trading pairs and 5 triggered orders:

*Price fetching:*
- Before: 10 API calls × 270ms = 2.7s per cycle, 600 calls/hour
- After: 1 API call × 300ms = 0.3s per cycle, 60 calls/hour
- **Savings: 90% fewer API calls, 89% faster**

*Order status:*
- Before: 5 × query_closed_orders = 250 orders transferred
- After: 5 × query_orders = 5 orders transferred
- **Savings: 98% less data transferred**

**Testing**:
- Updated `test_order_fill_notification.py` mocks from `query_closed_orders` to `query_orders`
- All 452 tests passing, no regressions
- Backward compatible (internal changes only)

**Key Insights**:
1. **Batch > Individual**: Always use batch methods when available for multiple items
2. **Targeted Queries**: Query specific items rather than filtering large result sets
3. **Graceful Fallback**: Handle missing batch methods for test mocks compatibility
4. **Follow Patterns**: Dashboard already used batch method - replicated to monitoring loop
5. **Error Handling**: Comprehensive error handling prevents failures from breaking monitoring

**Related Files**:
- `ttslo.py`: Lines 1514-1556 (batch prices), 895-997 (targeted orders)
- `tests/test_order_fill_notification.py`: Updated all 6 tests
- `KRAKEN_API_EFFICIENCY_IMPROVEMENTS.md`: Complete documentation

**Similar Implementations**:
- Dashboard: `dashboard.py` lines 156-194 (already used batch method)
- Dashboard: `dashboard.py` lines 450-669 (already used query_orders for completed orders)

---

## Dashboard get_completed_orders Optimization - Already Implemented (2025-10-30)

**Status**: ✅ ALREADY IMPLEMENTED (commit b59c530, Oct 24, 2025)

**Implementation Details**:

The `get_completed_orders()` function in `dashboard.py` (lines 450-669) is already optimized:

1. **Collects order IDs from state.csv** (lines 476-492):
   - Iterates through state entries
   - Filters for `triggered='true'` entries only
   - Extracts `order_id` for each triggered entry
   - Builds mapping: `config_id_by_order[order_id] = config_id`

2. **Uses query_orders() for specific IDs** (line 503):
   - Calls `kraken_api.query_orders(order_ids)`
   - Fetches only the specific order IDs from state
   - Kraken QueryOrders endpoint can handle up to 50 orders at once

3. **Fallback mechanisms** (lines 508-531):
   - Falls back to `get_cached_closed_orders()` only when needed
   - Handles missing orders from query_orders response
   - Handles API failures gracefully

4. **Manual orders handling** (lines 609-654):
   - Scans all closed orders for manual trailing-stop orders
   - Only includes manual orders not already in state

**Performance**:
- **Before**: Fetched 50+ unrelated closed orders, filtered in memory
- **After**: Queries only 3-4 specific order IDs directly
- **Result**: ~90% reduction in data transfer

**Verification**:
- All dashboard tests pass (14/14)
- Commit b59c530: "Fix: Use QueryOrders to fetch specific completed orders by ID"
- No changes needed - optimization fully working

---

## Dashboard Force Button Minimum Purchase Threshold (2025-10-27)

**Feature**: Grey out Force button when order cost is below Kraken's minimum purchase threshold (`costmin`).

**Problem**: 
- Force button was only checking `ordermin` (minimum volume)
- Didn't check `costmin` (minimum order cost in quote currency)
- Example: NEARUSD with volume=0.5, price=$8, cost=$4 < costmin=$5
- User could click Force → order creation would fail at Kraken API

**Solution**: Added `costmin` validation in dashboard pending orders:
- Backend checks: `order_cost = volume * current_price >= costmin`
- New fields: `cost_too_low` and `cost_message`
- Frontend: Warning icon + disabled Force button when violated

**Implementation**:

1. **Backend** (`dashboard.py` lines 286-305):
   ```python
   # Check minimum cost (purchase threshold)
   if pair_info and 'costmin' in pair_info and current_price:
       costmin = float(pair_info['costmin'])
       order_cost = volume * current_price
       if order_cost < costmin:
           cost_too_low = True
           cost_message = f"Order cost ${order_cost:.2f} is below minimum ${costmin:.2f} for {pair}"
   ```

2. **Frontend** (`templates/dashboard.html`):
   - Check `cost_too_low` in warning logic (priority: volume > cost > balance)
   - Disable Force button: `|| order.cost_too_low`
   - Show tooltip with detailed cost message

3. **Testing** (`tests/test_minimum_cost_validation.py`):
   - 6 tests covering all scenarios
   - Graceful handling of missing costmin/price
   - Both buy and sell orders tested
   - Combined volume+cost violations handled

**Key Insights**:
1. **Two Minimums**: Kraken enforces both `ordermin` (volume) AND `costmin` (purchase threshold)
2. **Dynamic Check**: Cost depends on current price, must recalculate each time
3. **Graceful Degradation**: Missing costmin/price → allow order (Kraken validates)
4. **Priority Order**: Show most specific warning first (volume > cost > balance)
5. **Dual Validation**: Backend validates + UI disables button (defense in depth)

**Related Files**:
- `dashboard.py`: Lines 277-338 (costmin check in get_pending_orders)
- `templates/dashboard.html`: Lines 754-774, 844-864 (warning + disable logic)
- `tests/test_minimum_cost_validation.py`: Complete test suite (6 tests)

---

## Dashboard Cancel Button Cache Invalidation (2025-10-27)

**Problem**: When users clicked cancel button in pending/active panes, the cancel succeeded but screen didn't update - canceled items remained visible.

**Root Cause**: TTL cache not invalidated after cancel operations. Frontend's `refreshData()` call fetched stale cached data.

**Solution**: Added `invalidate()` method to ttl_cache decorator:
```python
def invalidate():
    cache['result'] = None
    cache['timestamp'] = 0
    if disk_key:
        disk_cache.delete(disk_key)
```

Call after successful cancels:
- Pending cancel → invalidate `get_pending_orders` + `get_cached_config`
- Active cancel → invalidate `get_active_orders`
- Cancel-all → invalidate `get_active_orders`

**Key Insights**:
1. **Cache Invalidation Critical**: Modify operations MUST invalidate relevant caches
2. **Dual Update Strategy**: Frontend manual DOM update (immediate) + backend refresh (consistency)
3. **Decorator Enhancement**: Add methods to decorators for control (like `invalidate()`)
4. **Test Cache Behavior**: Verify caches are cleared, not just that operations succeed
5. **Invalidate Dependencies**: Pending cancel modifies config.csv → invalidate both pending AND config caches

**Related Files**:
- `dashboard.py`: Lines 52-60 (invalidate method), 1023-1028 (pending), 1277-1280 (active), 1334-1337 (cancel-all)
- `tests/test_dashboard_cancel_cache_invalidation.py`: 5 tests
- `DASHBOARD_CANCEL_FIX.md`: Full documentation

---

## Dashboard Pending Panel Wording Improvement (2025-10-27)

**Feature**: Improved clarity of Direction and Volume labels in pending orders panel.

**Problem**: Users found the pending panel confusing:
- "Direction: sell" - unclear whether selling the base asset or quote currency
- "Volume: 0.1000" - unclear which asset the volume refers to
- Example: For WALUSD pair, is it selling WAL or USD? Volume of WAL or USD?

**Solution**: Enhanced wording to be explicit and user-friendly:
- Direction: "Sell WAL to buy USD" (instead of "sell")
- Volume: "Volume WAL: 0.1000" (instead of "Volume: 0.1000")

**Implementation Details**:

1. **Backend** (`dashboard.py`):
   - Extract base_asset and quote_asset early in `get_pending_orders()`
   - Reuse extraction for both display and balance checking (efficiency)
   - Include `base_asset` and `quote_asset` fields in API response

2. **Frontend** (`templates/dashboard.html`):
   - `formatDirection(direction, baseAsset, quoteAsset)`: Creates descriptive text
     - "sell" + WAL/USD → "Sell WAL to buy USD"
     - "buy" + WAL/USD → "Buy WAL with USD"
   - `formatVolumeLabel(direction, baseAsset)`: Specifies asset in label
     - "Volume:" → "Volume WAL:"
   - Removes X and Z prefixes for cleaner display (XXBT → BTC, ZUSD → USD)
   - Applied to both normal rendering and error-handling re-render paths

**Key Insights**:

1. **User-Friendly Labels**: Technical terms (sell/buy) need context for non-experts
2. **Asset Name Cleaning**: Remove Kraken's internal prefixes (X, Z) for display
3. **Consistency**: Apply same formatting in all render paths (normal + error)
4. **Reuse Code**: Extract assets once, use for multiple purposes (display + validation)

**Example**:
```
Before:  Direction: sell          Volume: 0.1000
After:   Direction: Sell WAL to buy USD    Volume WAL: 0.1000
```

**Related Files**:
- `dashboard.py`: Lines 263-265, 291-292 (asset extraction and response)
- `templates/dashboard.html`: Lines 612-654 (helper functions), 780-788, 857-865 (rendering)

**Testing**: All 419 existing tests pass, no new tests needed (UI-only change)

---

## Dashboard Insufficient Balance Warning Icons (2025-10-27)

**Feature**: Added warning triangle icons to pending orders when there's insufficient balance to execute them.

**Problem**: Users couldn't tell if their pending orders would fail due to insufficient balance until the order actually tried to trigger. This led to failed orders and confusion.

**Implementation Details**:

1. **Backend** (`dashboard.py`):
   - Modified `get_pending_orders()` to fetch account balances via `kraken_api.get_balance()`
   - Added balance checking for each pending order:
     - **Sell orders**: Check base asset balance (need SOL to sell SOL)
     - **Buy orders**: Check quote currency balance (need USD to buy SOL)
   - Uses existing `_extract_base_asset()` and `_extract_quote_asset()` functions
   - Added two new fields to each order:
     - `insufficient_balance`: Boolean flag
     - `balance_message`: String like "Insufficient balance: need 10.0000 SOL but have 5.0000 SOL"

2. **Frontend** (`templates/dashboard.html`):
   - Added `.warning-icon` CSS class with SVG triangle + exclamation mark
   - Warning icon appears next to order ID (on same line)
   - Tooltip shows detailed balance message on hover
   - Added `.btn-disabled` CSS class for greyed-out buttons
   - Force button disabled when `insufficient_balance` is true
   - Applied to both main rendering and error-handler re-rendering

3. **Testing** (`tests/test_insufficient_balance_warning.py`):
   - 7 comprehensive tests covering all scenarios
   - Used `dashboard.get_pending_orders.__wrapped__()` to bypass TTL cache
   - Tests for sell/buy orders, API unavailable, error handling, etc.
   - All 416 tests pass (7 new + 409 existing)

**Key Insights**:

1. **Balance Logic Matters**:
   - Sell orders need base asset (selling SOL requires SOL balance)
   - Buy orders need quote currency (buying SOL requires USD balance)
   - Must normalize currency codes (USD → ZUSD for Kraken API)

2. **Graceful Degradation**:
   - If Kraken API unavailable: no warnings shown (don't crash)
   - If balance fetch fails: no warnings shown (don't crash)
   - Feature is optional enhancement, not critical path

3. **TTL Cache Testing**:
   - `@ttl_cache` decorator caches results between tests
   - Use `__wrapped__()` to bypass cache in tests
   - Alternatively, give each test unique IDs to avoid collisions

4. **UI/UX Best Practices**:
   - Warning icon on same line as order ID (not separate row)
   - Tooltip shows detailed message, not just generic "insufficient"
   - Disable Force button (don't just warn) - prevent user from trying
   - SVG icons better than CSS triangles (more control, cleaner)

5. **Asset Extraction**:
   - Pair suffixes vary: SOLUSD, XXBTZUSD, SOLUSDT
   - Must handle both Z-prefixed (ZUSD) and plain (USD) suffixes
   - Order matters when checking suffixes (USDT before USD)

**Visual Design**:
```
Order ID: sol_sell_1⚠️  [triangle icon]
          Hover: "Insufficient balance: need 10.0000 SOL but have 5.0000 SOL"

Buttons: [Cancel]  [Force - greyed out, disabled]
```

**Related Files**:
- `dashboard.py`: Lines 227-286 (balance checking in get_pending_orders)
- `dashboard.py`: Lines 594-680 (_extract_base_asset, _extract_quote_asset)
- `templates/dashboard.html`: Lines 325-395 (warning-icon and button CSS)
- `templates/dashboard.html`: Lines 711-760 (warning icon and button rendering)
- `tests/test_insufficient_balance_warning.py`: Complete test suite (7 tests)

**Demo**: See `/tmp/warning_icon_demo.html` for visual demonstration of the feature.

---

## Dashboard Force Button Immediate Execution (2025-10-27)

**Enhancement**: Force button now immediately creates TSL order on Kraken instead of waiting for next monitoring cycle.

**Problem with Original Implementation**:
- Force button only updated threshold_price in config.csv
- Had to wait for next monitoring cycle (60s default) for order to be created
- No immediate feedback to user
- User couldn't be sure order was actually created

**New Behavior**:
1. Updates threshold_price to current_price
2. **Immediately calls Kraken API** to create TSL order
3. Updates state.csv with trigger info (order_id, trigger_price, trigger_time)
4. Returns order ID to user instantly

**Implementation Details**:

1. **Backend** (`dashboard.py`): Enhanced `/api/pending/<config_id>/force` endpoint
   - Validates all required fields (pair, direction, volume, trailing_offset_percent)
   - Fetches current price from Kraken API
   - Updates threshold_price in config.csv
   - **NEW**: Directly calls `kraken_api.add_trailing_stop_loss()`
   - **NEW**: Updates state.csv to mark as triggered
   - **NEW**: Updates config.csv with trigger info
   - Handles index price unavailable (retries with last price)
   - Returns order ID and details to UI

2. **Frontend** (`templates/dashboard.html`): Updated confirmation message
   - Dialog now says "IMMEDIATELY" to clarify new behavior
   - Success message includes order ID
   - Shows trigger price and order details

3. **State Management**: Properly tracks order lifecycle
   - Creates/updates state entry with triggered='true'
   - Stores order_id, trigger_price, trigger_time
   - Preserves initial_price if already set

**Error Handling**:
- Missing required fields → 400 Bad Request with clear error
- Kraken API unavailable → 503 Service Unavailable
- Price fetch failure → 500 with details
- TSL order creation failure → 500 with error message
- Index price unavailable → Automatic retry with last price

**Key Architectural Insights**:

1. **Reused ttslo.py Logic**: Dashboard now has same order creation logic as monitoring service
   - Same API call pattern
   - Same index→last fallback
   - Same fee optimization (fciq for BTC)

2. **State Consistency**: Both paths (dashboard force vs. monitoring trigger) update state identically
   - Same state fields
   - Same timing
   - No drift between dashboard and monitoring

3. **No Code Duplication**: Dashboard imports logic, doesn't reimplement
   - Uses same `_extract_base_asset()` helper
   - Uses same Kraken API methods
   - Follows same error handling patterns

**Testing**:
- 10 comprehensive tests (updated from 7)
- All scenarios covered:
  - ✅ Successful order creation
  - ✅ Missing config fields  
  - ✅ Config not found
  - ✅ Kraken API unavailable
  - ✅ Price fetch errors
  - ✅ TSL order creation failures
  - ✅ Index price unavailable fallback
  - ✅ State and config updates verified
- All 419 tests passing

**Performance**:
- Old: 60s wait for next cycle → order created
- New: <2s for API call → order created immediately
- 30x faster user experience

**UI Impact**:
```
Before: "Order will trigger on next check cycle"
After:  "TSL order created successfully! Order ID: OIZXVF-N5TQ5..."
```

**Related Files**:
- `dashboard.py`: Lines 1019-1245 (api_force_pending endpoint - completely rewritten)
- `templates/dashboard.html`: Lines 1344-1372 (forcePendingOrder JS - updated messages)
- `tests/test_dashboard_force.py`: All 10 tests updated/added

**Migration Notes**:
- Backward compatible - existing configs work
- No database migration needed
- State.csv format unchanged
- Dashboard can now create orders independently of monitoring service

---

## Dashboard Force Button Implementation (2025-10-27)

**Feature**: Added "Force" button to pending orders in dashboard that forces immediate order creation by setting threshold_price = current_price.

**DEPRECATED**: This section describes the original implementation. See "Dashboard Force Button Immediate Execution" above for current behavior.

**Implementation Details**:
1. **Backend** (`config.py`): Added `update_config_threshold_price()` method
   - Atomically updates threshold_price field in config.csv
   - Preserves all other fields and CSV structure
   
2. **Backend** (`dashboard.py`): Added `/api/pending/<config_id>/force` POST endpoint
   - Fetches current market price from Kraken API
   - Updates config's threshold_price to current_price
   - Returns success with details or error messages
   - Handles edge cases: API unavailable, price fetch failure, config not found
   
3. **Frontend**: Green "Force" button on right side of pending order cards
   - Red "Cancel" button on left, green "Force" button on right
   - Uses `justify-content: space-between` for button layout
   - Confirmation dialog explains what will happen
   - Success dialog shows new threshold price and next steps
   
4. **Error Handling**: Surfaces Kraken API errors in UI
   - Insufficient balance will show when order creation is attempted
   - Error messages displayed in alert dialogs
   - Logs written to console for debugging

**How It Works** (OLD):
1. User clicks green "Force" button
2. Confirmation: "This will set threshold price to current market price..."
3. Backend: GET current price, UPDATE config.csv
4. Success alert: "New Threshold: $X.XX, Order will trigger on next check cycle"
5. Next monitoring cycle (60s default): threshold met → order created
6. Any errors (e.g., insufficient balance) surface in order creation logs

**Key Insights**:
- Works even if trigger doesn't make sense (as requested)
- No validation - just sets threshold = current_price
- Safe: uses atomic CSV write to prevent data corruption
- Testing: 7 comprehensive tests for force functionality
- All 409 existing tests still pass

**UI Design**:
- Red Cancel (left) vs Green Force (right) = clear visual distinction
- Progress bar shows "READY TO TRIGGER" or distance to threshold
- After forcing, progress updates to show near-zero distance

**Related Files**:
- `config.py`: Lines 546-583 (update_config_threshold_price)
- `dashboard.py`: Lines 983-1055 (api_force_pending endpoint - OLD VERSION)
- `templates/dashboard.html`: CSS, HTML, JavaScript for Force button
- `tests/test_dashboard_force.py`: Complete test suite (7 tests - OLD VERSION)

---

## Validator Price Formatting for Log Messages (2025-10-27)

**Problem**: Validator log messages showed very small cryptocurrency prices as "(0.00)" making them unreadable.
- PEPE at 0.00000768 displayed as "0.00"
- MEW at 0.00187083 displayed as "0.00"
- Users couldn't see actual threshold prices in validation warnings

**Root Cause**:
- `_format_decimal()` method used hardcoded 2 decimal places for all price formatting
- Works fine for BTC ($50,000) but terrible for meme coins ($0.00000768)
- Gap warnings, threshold warnings all showed "0.00" for small-value coins

**Solution**: Implemented smart price formatting similar to dashboard's `formatPrice()`:
```python
def _format_decimal(self, value: Decimal, places: int = None) -> str:
    """Smart formatting based on magnitude if places is None."""
    if places is not None:
        # Explicit places still works (for percentages)
        return fixed_decimal_format(value, places)
    
    # Smart formatting based on value
    abs_value = abs(value)
    if abs_value < 0.01:
        # Very small: up to 8 decimals, remove trailing zeros
        return format_up_to_8_decimals(value)
    elif abs_value < 1:
        # Small: 4 decimals
        return format_4_decimals(value)
    else:
        # Medium/Large: 2 decimals
        return format_2_decimals(value)
```

**Changes Made**:
1. Updated `_format_decimal()` to accept optional `places` parameter
   - None (default): use smart formatting
   - Integer: use that many decimal places (for percentages)

2. Removed explicit `places=2` from all price formatting calls
   - Threshold prices, current prices, historical prices all use smart formatting
   - Percentages still explicitly use `places=2`

3. Added comprehensive test suite (10 tests)

**Results**:
```
BEFORE: Small gap between threshold (0.00) and current price (0.00)
AFTER:  Small gap between threshold (0.00000768) and current price (0.00000742)
```

**Key Insights**:
1. **Different assets need different precision**: BTC needs 2 decimals, PEPE needs 8
2. **Smart formatting prevents information loss**: Users can see actual values now
3. **Keep percentages consistent**: Always 2 decimals for gap%, offset%, etc.
4. **Remove trailing zeros for cleanliness**: "0.001" not "0.00100000"
5. **Pattern from dashboard works well**: Reused same logic from `formatPrice()`

**Testing**:
- 10 new tests for price formatting
- Updated 1 existing test for new format
- All 402 tests passing

**Related Files**:
- `validator.py`: Lines 775-820 (_format_decimal implementation)
- `validator.py`: Lines 412-449 (price formatting in warnings)
- `tests/test_validator_price_formatting.py`: Comprehensive test suite
- `tests/test_balance_normalization.py`: Updated test expectation

**Similar Implementation**:
- Dashboard: `templates/dashboard.html` lines 381-437 (`formatPrice()` JavaScript)
- Notifications: `notifications.py` lines 16-70 (`format_balance()` Python)

---

## Dashboard Disk Cache for Performance (2025-10-26)

**Problem**: Dashboard slow to load (minutes lag), particularly completed orders pane. In-memory cache lost on restart.

**Solution**: Implemented hybrid memory + disk cache system:
- Memory cache (fastest, TTL-based)
- Disk cache (persistent across restarts, JSON files in `.cache/`)
- Automatic fallback: memory → disk → API call
- Cache warming on startup from disk

**Implementation**:
- Created `disk_cache.py` module with `DiskCache` class
- Modified `ttl_cache` decorator to support optional `disk_key` parameter
- Updated all dashboard cache functions to use disk persistence
- Added `/api/cache-stats` endpoint for monitoring

**Key Features**:
- Configurable cache directory via `TTSLO_CACHE_DIR` env var (default: `.cache`)
- TTL-based expiration (aligns with `DASHBOARD_REFRESH_INTERVAL`)
- Automatic cleanup of expired entries
- Cache statistics (entry count, size)
- JSON serialization for complex data structures

**Performance Benefits**:
- First load after restart: Uses disk cache (instant vs minutes)
- Subsequent loads: Uses memory cache (microseconds)
- Reduced Kraken API calls (rate limit friendly)
- Persistent cache survives service restarts

**Cache Keys**:
- `open_orders` - Open orders from Kraken
- `closed_orders` - Closed orders from Kraken
- `config` - Config CSV data
- `state` - State CSV data
- `current_prices` - Current prices for all pairs
- `pending_orders` - Calculated pending orders
- `active_orders` - Calculated active orders
- `completed_orders` - Calculated completed orders
- `balances_and_risks` - Balance and risk analysis

**Testing**:
- 10 tests for `DiskCache` class (basic operations, TTL, persistence)
- 4 tests for dashboard integration
- All 398 tests passing

**Related Files**:
- `disk_cache.py`: Core disk cache module
- `dashboard.py`: Lines 20-35 (imports, init), 38-77 (hybrid cache decorator), 91-125 (cache functions)
- `tests/test_disk_cache.py`: DiskCache unit tests
- `tests/test_dashboard_disk_cache.py`: Dashboard integration tests

**Key Insights**:
1. Hybrid caching (memory + disk) provides best of both worlds
2. Disk cache must handle JSON serialization gracefully
3. TTL should align with data freshness requirements
4. Cache statistics help monitor performance
5. Reuse existing patterns (e.g., kraken_pairs_util.py disk cache)

---

## Coin Stats Configurable Bracket Parameters (2025-10-26)

**Feature**: Added `--suggestbracket` and `--suggestoffset` parameters to `tools/coin_stats.py` for generating config suggestions with custom bracket and trailing offset values.

**Problem**: The tool hardcoded 2% bracket offset and 1% trailing offset for generating suggested configs. Users wanted flexibility to specify different values like 10% bracket with 5% trailing offset.

**Solution**:
- Added `--suggestbracket` CLI argument (default: 2.0) for bracket offset percentage
- Added `--suggestoffset` CLI argument (default: 1.0) for trailing offset percentage
- Updated `generate_config_suggestions()` to accept these as parameters
- Modified all hardcoded values to use the configurable parameters
- Updated output messages to show actual values being used

**Usage**:
```bash
# Default behavior (2% bracket, 1% trailing)
uv run python tools/coin_stats.py

# Custom 10% bracket with 5% trailing offset
uv run python tools/coin_stats.py --suggestbracket 10 --suggestoffset 5

# Custom 5% bracket with 2% trailing offset
uv run python tools/coin_stats.py --suggestbracket 5 --suggestoffset 2
```

**Key Insights**:
1. When adding parameters to existing functions, ensure backward compatibility with defaults
2. Update ALL references to hardcoded values (function body, print statements, comments, docstrings)
3. Test both default and custom parameter values
4. Watch for duplicate print statements when merging changes
5. Use `type=float` for percentage arguments to allow decimal values

**Testing**:
- Added 2 comprehensive tests: default params and custom params
- Tests validate both the trailing offset AND the bracket offset calculations
- All 378 tests passing

**Related Files**:
- `tools/coin_stats.py`: Lines 754-899 (generate_config_suggestions), 959-976 (argparse)
- `tests/test_coin_stats.py`: Lines 303-400 (new tests)

---

## Available Balance Decimal Formatting (2025-10-25)

**Problem**: Notification messages showed Available Balance with inconsistent formatting:
- Scientific notation for very small balances: `1.23E-9`
- Too many decimals for medium balances: `123.1595217414`
- No thousands separator for large amounts

**Root Cause**:
- `ttslo.py` line 520 used `str(available)` which converts small Decimal to scientific notation
- Dashboard had `formatPrice()` with smart decimal handling but notifications didn't
- Result: Users confused seeing "0" balance in notifications but "sufficient" in other places

**Solution**:
- Created `format_balance()` function in `notifications.py` (Python equivalent of `formatPrice()`)
- Updated `notify_insufficient_balance()` to use formatted balance
- Pass `Decimal` directly instead of converting to string prematurely

**Formatting Logic**:
```python
def format_balance(value):
    # Very small (< $0.01): up to 8 decimals, remove trailing zeros
    if abs(price) < 0.01:
        return f"{price:.8f}".rstrip('0').rstrip('.')
    # Small (< $1): 4 decimals
    elif abs(price) < 1:
        return f"{price:.4f}"
    # Medium (< $100): 2 decimals
    elif abs(price) < 100:
        return f"{price:.2f}"
    # Large: 2 decimals with thousands separator
    else:
        return f"{price:,.2f}"
```

**Examples**:
- `Decimal('1.23E-9')` → `"0"` (was `"1.23E-9"`)
- `Decimal('0.000001679')` → `"0.00000168"` (was `"0.000001679"`)
- `Decimal('123.1595217414')` → `"123.16"` (was `"123.1595217414"`)
- `Decimal('1234.56')` → `"1,234.56"` (was `"1234.56"`)

**Key Insights**:
1. Always format Decimal values before display to avoid scientific notation
2. Different value ranges need different decimal precision for readability
3. Keep formatting consistent between dashboard UI and notifications
4. Remove trailing zeros for cleaner display of small balances
5. Pass native types (Decimal) through the chain, format only at display time

**Testing**:
- 17 new tests covering all value ranges and edge cases
- All 377 tests passing
- No regressions

**Related Files**:
- `notifications.py`: Lines 16-70 (format_balance function), 547-573 (notify_insufficient_balance)
- `ttslo.py`: Line 520 (pass Decimal directly)
- `templates/dashboard.html`: Line 1059 (already uses formatPrice)
- `tests/test_balance_formatting.py`: Comprehensive test suite

---

## Pytest Test Failures Investigation (2025-10-25)

**Issue**: 4 test failures and 6 skips in pytest run.

**Investigation Findings**:

### 1. creds.py Duplicate Code (3 failures fixed)
- **Problem**: Lines 103-120 had duplicate credential checks
- **Root cause**: `COPILOT_KRAKEN_API_KEY` checked at line 85-88 BEFORE `COPILOT_W_KR_*` variants (line 103-113)
- **Expected precedence**: `COPILOT_W_KR_RO_PUBLIC` > `COPILOT_W_KR_PUBLIC` > `COPILOT_KRAKEN_API_KEY`
- **Actual precedence**: `COPILOT_KRAKEN_API_KEY` won (checked first)
- **Fix**: Removed duplicate code, reordered checks to match expected precedence
- **Key insight**: Check order matters! More specific keys (COPILOT_W_*) must be checked before generic fallbacks

### 2. formatPrice Scientific Notation (1 failure fixed)
- **Problem**: `parseFloat(formatted).toString()` in JavaScript converts small numbers to scientific notation
- **Example**: `0.00000123` → `"1.23e-06"` instead of `"0.00000123"`
- **Root cause**: JavaScript's `Number.toString()` uses scientific notation for numbers < 1e-6
- **Fix**: Use manual string manipulation: `formatted.replace(/\.?0+$/, '')` to remove trailing zeros
- **Python equivalent**: `formatted.rstrip('0').rstrip('.')`
- **Affected files**: `templates/dashboard.html`, `tests/test_dashboard_price_formatting.py`

### 3. Skipped Tests (6 tests - CONDITIONAL, NOT ALWAYS SKIPPED)
- **Location**: All in `test_kraken_api_live.py`
- **Skip logic**: Line 88 - `pytest.skip("Live API credentials not available")` - only when credentials missing
- **Behavior**: 
  - **WITH credentials**: Tests RUN (may fail with API errors if credentials invalid)
  - **WITHOUT credentials**: Tests SKIP (intentional - can't test live API)
- **Current environment**: Has `COPILOT_W_KR_RW_PUBLIC/SECRET` set, tests run but fail with "EAPI:Invalid key" (credentials exist but are invalid/placeholder)
- **Dev environment**: With valid credentials in `.env`, these tests should PASS
- **Verdict**: CORRECT BEHAVIOR - integration tests that conditionally skip based on credential availability

**Key Learnings**:
1. Always check for duplicate code blocks when tests fail unexpectedly
2. Variable precedence order must match documentation and test expectations
3. JavaScript number formatting can trigger scientific notation - use string manipulation instead
4. Skipped tests are not failures - check the skip reason before "fixing" them
5. Integration tests should gracefully skip when external resources unavailable

**Files Modified**:
- `creds.py`: Removed duplicate code, fixed precedence order
- `templates/dashboard.html`: Fixed formatPrice to avoid scientific notation
- `tests/test_dashboard_price_formatting.py`: Updated Python equivalent to match JS fix

---

## GitHub Copilot Workspace Setup (2025-10-25)

**Problem**: GitHub Copilot agents started in fresh environments without `uv` or `pytest` installed, requiring manual setup every session.

**Solution**: Created `.github/workflows/copilot-setup-steps.yml` workflow that runs before Copilot agent starts.

**Key Points**:
1. **Workflow runs automatically**: GitHub Actions executes `copilot-setup-steps` job before agent initialization
2. **Install uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. **Add to PATH**: `echo "$HOME/.local/bin" >> $GITHUB_PATH`
4. **Sync deps**: `uv sync` installs all pyproject.toml dependencies (including pytest)
5. **Verification**: Tests run `uv --version` and `uv run pytest --version`

**Workflow Structure**:
```yaml
jobs:
  copilot-setup-steps:  # Special job name recognized by Copilot
    runs-on: ubuntu-latest
    steps:
      - Checkout
      - Setup Python 3.12
      - Install uv
      - Verify uv
      - Sync dependencies
      - Verify pytest
```

**Benefits**:
- No manual installation needed
- Consistent environment every session
- All dependencies from pyproject.toml automatically available
- Pytest ready to run immediately

**Testing**:
- Workflow can be manually triggered via `workflow_dispatch`
- Agent environment matches developer environment (same uv version, same deps)

**Related Files**:
- `.github/workflows/copilot-setup-steps.yml`: Workflow definition
- `AGENTS.md`: Updated with environment setup documentation
- `pyproject.toml`: Dependency source of truth

---

## Dashboard Completed Orders - Canceled Order Filtering

**Date**: 2025-10-24

**Problem**: Dashboard Completed Orders pane showed ALL canceled orders from Kraken, including manual orders that users canceled. This cluttered the view with irrelevant data.

**Requirements**:
1. For **TTSLO-created orders** (tracked in state.csv): Show canceled orders WITH a "CANCELED" tag
   - Users need to see these because they track orders the service created
2. For **Manual orders** (NOT in state.csv): Filter out canceled orders completely
   - These are irrelevant - user canceled them manually in Kraken UI

**Root Cause**:
- Line 468 in `dashboard.py`: `if order_info.get('status') not in ['closed', 'canceled']`
- This included canceled manual orders in the completed list

**Solution**:
```python
# dashboard.py - Lines 467-469
# For manual orders (not in state), only show closed orders
# Canceled manual orders are not relevant
if order_info.get('status') != 'closed':
    continue
```

**UI Enhancement**:
```javascript
// templates/dashboard.html - Added CANCELED tag
if (order.status === 'canceled') {
    statusTags += '<span style="...background:#e74c3c...">CANCELED</span>';
}
```

**Key Distinctions**:
1. **TTSLO orders** (lines 412-450): Accept both 'closed' and 'canceled', pass status to UI
2. **Manual orders** (lines 452-494): Only accept 'closed', filter out 'canceled'

**Visual Indicators**:
- MANUAL tag: Orange (#e67e22) - indicates order not created by TTSLO
- CANCELED tag: Red (#e74c3c) - indicates TTSLO order was canceled

**Testing**:
- `test_canceled_order_filtering()`: Validates filtering logic for both order types
- `test_completed_order_status_tag()`: Validates status field structure for UI

**Related Files**:
- `dashboard.py`: Lines 467-469 (manual order filtering)
- `dashboard.py`: Line 445 (status field passed to UI)
- `templates/dashboard.html`: Lines 737-745 (status tag display)
- `tests/test_dashboard.py`: Added 2 new tests
## State.csv Reconciliation - Handling Order Creation Failures

**Date**: 2025-10-24

**Problem**: Issue #88 - state.csv may not update if exception occurs during order creation, leading to orders incorrectly marked as "manual" when they were created by ttslo.py.

**Validation Process**:
1. Fetch current open orders from Kraken API
2. Parse logs.csv to find all "TSL order created successfully" entries
3. Cross-reference: orders in logs that are still open on Kraken
4. Result: Found 3 orders incorrectly classified

**Orders Found**:
- OIZXVF-N5TQ5-DHTPIR (near_usd_sell_29) - Created 2025-10-24T05:15:09
- O2VLNP-DNSKF-LAFIJP (dydx_usd_sell_19) - Created 2025-10-24T05:15:04  
- OGMFI4-MABOV-YGJDWI (eth_usd_sell_3) - Created 2025-10-24T04:33:25

**Solution**: Created `reconcile_state.py` tool:
- Fetches open orders from Kraken
- Parses logs.csv for order creation history (including trailing offset, trigger price)
- Identifies missing/incorrect state.csv entries
- Creates backups before modifying state.csv
- Supports dry-run mode for safety

**Key Insights**:
1. Logs.csv structure: Order creation happens in 2 log entries:
   - "Creating TSL order: ..." (has trailing_offset, trigger_price in message and row[4])
   - "TSL order created successfully: order_id=..." (has order_id in row[4])
   - Config ID is always in row[3]

2. State.csv fields needed for proper tracking:
   - id, triggered, trigger_price, trigger_time, order_id, offset

3. Reconciliation should be run periodically (e.g., daily cron job) to prevent drift

**Best Practice**: 
- Always validate state.csv against live Kraken data + logs
- Use logs.csv as source of truth for order creation events
- Implement reconciliation as periodic maintenance task
- Always create backups before modifying state.csv

**Related Files**:
- `reconcile_state.py`: Main reconciliation tool
- `STATE_FIX_README.md`: Documentation and usage
- `state_fix.csv`: Pre-computed fix data for identified issues
- `config.py`: State file structure (save_state, load_state)

---

## Active TSL Orders Display - Manual Order Data Extraction

**Date**: 2025-10-24

**Problem**: Active TSL Orders pane showed inconsistent data:
- Service-created orders: Human-readable ID, trailing offset (1.00%), trigger time ✓
- Manual orders (from Kraken): Kraken order IDs, NO trailing offset or trigger time ✗

**Root Causes**:
1. Manual orders have trailing offset in Kraken's `price` field (format: `"+1.5000%"` or `"-2.0000%"`)
2. Dashboard wasn't extracting this value, left it as `None`
3. Missing MANUAL badge in Active pane (existed in Pending/Completed)

**Solution**:
```python
# Extract trailing offset from price field for manual orders
price_str = descr.get('price', '')
trailing_offset_percent = None
if price_str:
    # Remove '+', '-', and '%' to get the numeric value
    trailing_offset_percent = price_str.replace('+', '').replace('-', '').replace('%', '').strip()
```

**Key Insight**: Kraken API returns different data structures for:
- Orders created via API (have state.csv entry) → Full data available
- Manual orders (created in Kraken UI) → Must extract from alternative fields

**Best Practice**: Always check alternative data sources in API responses:
- Trailing offset may be in `price` field for trailing-stop orders
- Direction may be in different location for manual vs API orders
- Always add visual indicators (MANUAL badge) to distinguish data sources

**Related Files**:
- `dashboard.py`: Lines 313-320 (extraction logic)
- `templates/dashboard.html`: Line 639 (MANUAL badge)
- `extract_open_orders.py`: Lines 54-60 (same pattern, already implemented)
- `tests/test_dashboard.py`: test_manual_order_trailing_offset_extraction

---

## Dashboard Performance & Caching

**Date**: 2025-10-24

**Problem**: Dashboard API endpoints (especially /api/active and /api/completed) were slow (437-965ms) because endpoint functions weren't cached.

**Root Cause**: 
- `get_active_orders()` and `get_completed_orders()` were NOT decorated with `@ttl_cache`
- Even though underlying API calls (like `query_open_orders`) were cached, the filtering/processing logic ran on every request
- This meant every dashboard refresh triggered full API calls + processing

**Solution**: Add `@ttl_cache(seconds=5)` to both functions:
```python
@ttl_cache(seconds=5)
def get_active_orders():
    ...

@ttl_cache(seconds=5)  
def get_completed_orders():
    ...
```

**Impact**:
- Active orders endpoint: 0.311s → 0.000s on cache hits (31,786x faster)
- Completed orders endpoint: Similar dramatic speedup
- Dashboard now loads instantly on refresh (within 5s cache window)
- 30-second auto-refresh feels snappy instead of laggy

**Key Insight**: Cache at the endpoint level, not just the API call level. The filtering/processing overhead can be significant even if API calls are cached.

**Related Files**:
- `dashboard.py`: Lines 247-334 (get_active_orders), 337-488 (get_completed_orders)
- `tests/test_dashboard_performance.py`: Validates caching behavior

---

## Repository Organization

**Date**: 2025-10-23

**Context**: Repository had become cluttered with 100+ files in root directory, making it hard to navigate.

**Solution**: Organized into logical directories:
- `docs/` - All documentation (51 files)
- `tests/` - All test files (35 files) 
- `demos/` - Demo scripts and examples (15 files)
- `tools/` - Debug/investigation scripts (12 files)
- Root - Only core application files and required docs (AGENTS.md, README.md, LEARNINGS.md)

**Key steps**:
1. Use `git mv` to preserve history
2. Create `tests/conftest.py` to add project root to Python path for imports
3. Add `[tool.pytest.ini_options]` to `pyproject.toml` with `testpaths = ["tests"]`
4. Update all documentation references: `sed -i 's|pytest test_|pytest tests/test_|g'`
5. Update README.md links to moved docs: `[SECURITY.md](docs/SECURITY.md)`

**Result**: Clean root directory, better organization, all 258 tests still passing.

---

## IP Detection for Network Services

**Problem**: When binding Flask/web services to `0.0.0.0`, `socket.gethostname()` and `socket.getaddrinfo()` may return localhost IPs like `127.0.1.1` instead of the actual LAN IP.

**Solution**: Use UDP socket connection to external IP to determine local interface IP:
```python
import socket

# Primary method - works reliably
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('8.8.8.8', 80))  # Doesn't send data, just determines routing
host_ip = s.getsockname()[0]
s.close()
```

**Why this works**: 
- Creating a UDP socket and "connecting" to an external IP (like Google DNS 8.8.8.8) forces the OS to determine which local network interface would be used
- The socket's local address (`getsockname()[0]`) is the actual LAN IP
- No data is actually sent (UDP connect is just routing info)

**Fallback strategy**:
1. Try UDP socket method first (most reliable)
2. Fall back to `socket.getaddrinfo()` with enhanced filtering
3. Filter out ALL `127.x.x.x` addresses (not just `127.0.0.1`)
4. Prioritize private network ranges: `192.168.x.x` and `10.x.x.x`
5. Accept `172.16.x.x` through `172.31.x.x` as private networks too

**Related files**:
- `dashboard.py`: Lines 488-525 (notification IP detection)
- `test_ip_detection.py`: Unit tests for IP detection methods
- `test_dashboard_ip_detection.py`: End-to-end verification

**Testing**: Verify with `python3 test_dashboard_ip_detection.py` to see actual IPs detected.

---

## Network Security Best Practices

When binding services to `0.0.0.0`:
- Use firewall rules to restrict access to local subnet only
- Example (UFW): `sudo ufw allow from 192.168.1.0/24 to any port 5000`
- Example (iptables): `sudo iptables -A INPUT -p tcp --dport 5000 -s 192.168.1.0/24 -j ACCEPT`
- Document security expectations in README
- Systemd services should run as unprivileged users
- Use read-only mode for monitoring/dashboard services

---

## Dashboard Data Persistence

**Problem**: Dashboard panes would intermittently go blank when API calls returned empty arrays or failed, even after previously showing data.

**Root Cause**: The JavaScript was updating the `currentData` variable BEFORE checking if the response was empty, causing the condition `currentData.length === 0` to always be true on subsequent empty responses.

**Solution**: Update the `currentData` variable AFTER processing the response:

```javascript
// WRONG - updates current data too early
const orders = await response.json();
currentData = orders;  // ❌ Sets before checking

if (!orders.length) {
    if (!currentData || currentData.length === 0) {  // Always true!
        showEmptyState();
    }
    return;
}

// CORRECT - updates current data after checks
const orders = await response.json();

if (!orders.length) {
    if (!currentData || currentData.length === 0) {  // Checks old data
        showEmptyState();
    }
    currentData = orders;  // ✅ Updates after decision
    return;
}

currentData = orders;  // ✅ Updates after successful render
renderData(orders);
```

**Key Points**:
1. Store current data in variables: `currentPendingData`, `currentActiveData`, `currentCompletedData`
2. Only show empty state if `currentData` was never populated (initial load)
3. On error or empty response, keep showing last known data
4. Update `currentData` AFTER deciding whether to show empty state
5. Use `console.warn()` for errors to preserve last known data

**Related files**:
- `templates/dashboard.html`: Lines 366-530 (pending), 533-627 (active), 630-734 (completed)
- `test_dashboard_data_persistence.py`: Tests for data persistence behavior

---

## Order Fill Monitoring

**Feature**: Automatic monitoring and Telegram notification when TSL orders are filled.

**Implementation**: 
- Monitor triggered orders in `check_triggered_orders()` method called in main loop
- Query Kraken's `ClosedOrders` API to check status
- Send Telegram notification when order status becomes 'closed'
- Track with `fill_notified` flag in state to prevent duplicate notifications

**Key Components**:
1. `check_order_filled(config_id, order_id)`: Queries Kraken API for order status
2. `check_triggered_orders()`: Iterates through all triggered orders and checks status
3. State field `fill_notified`: Tracks if notification was sent (prevents duplicates)
4. Integration in `run_once()`: Runs after processing configs, before saving state

**Behavior**:
- Runs every monitoring cycle (default 60s)
- Only checks orders with `triggered='true'` and valid `order_id`
- Skips orders already notified (`fill_notified='true'`)
- Skips in dry-run mode
- Includes fill price when available from Kraken API

**Error Handling**:
- Errors in monitoring don't affect order creation or price checking
- API errors logged but don't crash the application
- Missing credentials handled gracefully (logs warning)

**Testing**:
- `test_order_fill_notification.py`: 6 tests covering all scenarios
- `demo_order_fill_notification.py`: Visual demonstration of workflow

**Related files**:
- `ttslo.py`: Lines 637-695 (check_order_filled, check_triggered_orders)
- `config.py`: Line 343 (state fieldnames including fill_notified)
- `notifications.py`: Lines 202-221 (notify_tsl_order_filled method)
- `NOTIFICATIONS_README.md`: Documentation of feature

---

## CSV Editor UX Design Patterns

**Problem**: TUI editors need balance between discoverability (for new users) and efficiency (for power users).

**Key Insights**:
- Footer-only keybindings are insufficient for discoverability
- Need dedicated help screen accessible via `?` or `F1`
- Visual validation indicators (colors, icons) reduce cognitive load
- Users expect immediate feedback (save indicators, validation status)
- Common workflows should have shortcuts (row duplication, bulk edits)

**Best Practices**:
1. Show validation status in table view (not just edit modal)
2. Provide multiple ways to trigger actions:
   - Menu selection
   - Keybinding
   - Command palette (future)
3. Use progressive disclosure (simple by default, advanced on demand)
4. Always show file modification status in title/footer
5. Confirm destructive actions (delete, overwrite)

**Anti-patterns to Avoid**:
- Forcing modal edit for every cell (too many keystrokes)
- Hiding validation errors until save attempt
- No undo/redo (forces defensive editing)
- Search/filter only via external tools (breaks workflow)
- No indication of which fields have auto-formatting

**Related files**:
- `csv_editor.py`: Main TUI implementation
- `CSV_EDITOR_ROADMAP.md`: Comprehensive improvement plan
- `test_csv_editor.py`: Validation and feature tests

**References**:
- Textual framework docs: https://textual.textualize.io/
- VisiData (advanced CSV TUI): https://www.visidata.org/
- Micro editor (modern TUI patterns): https://micro-editor.github.io/

---

## CSV Editor Phase 1 Implementation

**Implementation Date**: October 2025

### Features Implemented
1. **Help Screen** (`?` or `F1` key)
   - Comprehensive modal with all keybindings, validation rules, tips
   - Scrollable content for easy reference
   - Self-documenting for new users

2. **Row Duplication** (`Ctrl+Shift+D`)
   - Smart ID auto-increment algorithm
   - Handles various ID formats: `btc_1` → `btc_2`, `eth_test` → `eth_test_1`
   - Common workflow made much faster

3. **Unsaved Changes Indicator**
   - Title shows `*` when file modified
   - Custom quit handler with confirmation dialog
   - Prevents accidental data loss

### Key Design Patterns

**Modal Screens in Textual**:
- Create by subclassing `ModalScreen[T]` where T is return type
- Use `self.dismiss(value)` to return value to caller
- Use `self.push_screen(screen, callback)` to show modal
- Callback receives the dismissed value

**Title Updates**:
- Create helper method `_update_title()` for consistent title formatting
- Create `_set_modified(bool)` to update both flag and title
- Replace direct `self.modified = X` with `self._set_modified(X)`

**Action Override**:
- Override `action_quit()` to customize quit behavior
- Use `super(CSVEditor, self).action_quit()` to call parent implementation
- Can show confirmation dialogs before executing action

**ID Auto-Increment Algorithm**:
```python
import re
match = re.search(r'(.+?)(\d+)$', original_id)
if match:
    return f"{match.group(1)}{int(match.group(2)) + 1}"
else:
    return f"{original_id}_1"
```

### Testing Approach
- Unit tests for helper methods (`_auto_increment_id`, `_update_title`)
- Screen creation tests (ensure modals can be instantiated)
- State tests (verify modified flag behavior)
- All tests pass without running full TUI

### Documentation Updates
- Updated `CSV_EDITOR_README.md` with new features section
- Updated `README.md` keybindings table
- Updated `CSV_EDITOR_ROADMAP.md` with completion status
- Created demo script to showcase features

### Metrics
- **Code Added**: ~200 lines (help screen, duplication, quit confirmation)
- **Tests Added**: 4 new tests (auto-increment, help, modified, confirm)
- **All Tests**: 13/13 passing
- **Development Time**: ~2 hours
- **User Impact**: High (better discoverability, faster workflow, safer editing)

---

## Kraken API Error Handling

**Implementation Date**: October 2025

### Problem
During maintenance, network issues, or service outages, Kraken API calls could fail in various ways:
- Timeouts (slow network, overloaded server)
- Connection errors (network down, DNS failures)
- Server errors 5xx (maintenance, crashes)
- Rate limiting 429 (too many requests)

These failures needed to be:
1. Properly classified and logged
2. Handled gracefully without crashing
3. Notified to users via Telegram

### Solution
Created custom exception hierarchy for API errors:

```python
KrakenAPIError (base)
├── KrakenAPITimeoutError
├── KrakenAPIConnectionError
├── KrakenAPIServerError
└── KrakenAPIRateLimitError
```

Each exception stores:
- `error_type`: String identifier (timeout, connection, server_error, rate_limit)
- `details`: Dict with context (status_code, timeout value, endpoint, etc.)

### Implementation Details

**API Client Changes** (`kraken_api.py`):
1. Added timeout parameter to all requests (default 30s)
2. Wrapped all API calls in try-except with specific error classification
3. Check status codes before raising generic exceptions
4. Preserve original exception with `from e` for debugging

**Error Detection Order**:
1. Catch `requests.exceptions.Timeout` → `KrakenAPITimeoutError`
2. Catch `requests.exceptions.ConnectionError` → `KrakenAPIConnectionError`
3. Check status code 429 → `KrakenAPIRateLimitError`
4. Check status code >= 500 → `KrakenAPIServerError`
5. Call `response.raise_for_status()` for other HTTP errors
6. Catch `requests.exceptions.RequestException` → `KrakenAPIError`

**Notification System** (`notifications.py`):
- Added `notify_api_error()` method
- Icon mapping for visual distinction (⏱️ timeout, 🔌 connection, 🔥 server, 🚦 rate limit)
- Contextual help messages for each error type
- Includes endpoint, error message, and relevant details

**Integration** (`ttslo.py`):
- Catch `KrakenAPIError` before generic `Exception`
- Send notification on API errors
- Log with error_type for filtering
- Continue running (don't crash on API errors)
- Safe abort (no orders created on errors)

### Testing
16 new tests covering:
- All error types on public endpoints
- All error types on private endpoints
- Custom timeout parameter
- Notification message formatting
- Subscription handling

All tests pass, no regressions in existing tests.

### Key Insights

1. **Exception Hierarchy**: Use custom exceptions with type field rather than string parsing
2. **Chaining**: Use `raise ... from e` to preserve original traceback
3. **Order Matters**: Check specific exceptions before generic ones
4. **Status Codes First**: Check status codes before `.raise_for_status()`
5. **Timeouts**: Always set explicit timeouts on network requests
6. **Context**: Store detailed context in exception for debugging and notifications

### Related Files
- `kraken_api.py`: Lines 17-62 (exception classes), 304-408 (_query_public/private)
- `notifications.py`: Lines 367-408 (notify_api_error)
- `ttslo.py`: Import statement, error handling in process_config, run_once
- `test_api_error_handling.py`: Complete test suite
- `demo_api_error_handling.py`: Visual demonstration

### Documentation
- `README.md`: API Error Handling section
- `NOTIFICATIONS_README.md`: API error notification examples
- `notifications.ini.example`: api_error event type

---

## Textual App Action Quit Override

**Problem**: When overriding `action_quit()` in a Textual App, calling `super().action_quit()` doesn't work.

**Root Cause**: 
- `App.action_quit()` is defined as `async def action_quit(self)` 
- When you override it as `def action_quit(self)` (not async), calling `super().action_quit()` returns a coroutine that never executes
- The quit action appears to do nothing

**Solution**: Call `self.exit()` directly instead of `super().action_quit()`

**Example**:
```python
# ❌ WRONG - doesn't work
def action_quit(self) -> None:
    if self.confirm_quit():
        super(CSVEditor, self).action_quit()  # Returns unawaited coroutine!
    
# ✓ CORRECT - works properly  
def action_quit(self) -> None:
    if self.confirm_quit():
        self.exit()  # Directly calls exit method
```

**Key Points**:
1. `App.action_quit()` is async, but your override is typically sync
2. Use `self.exit()` to properly terminate the app
3. `exit()` accepts optional parameters: `result`, `return_code`, `message`
4. Don't try to await the super call unless your override is also async

**Related Issue**: csv_editor.py quit button didn't work (Ctrl+Q, ESC)

**Related Files**:
- `csv_editor.py`: Lines 1272-1292 (action_quit implementation)
- `test_csv_editor.py`: test_quit_action_calls_exit() test

---

## Profitable Candidates Tool Implementation

**Implementation Date**: October 2025

### Problem Statement
Traders needed a way to identify volatile trading pairs with oscillating prices that could be profitable for bracketing strategies (buying low and selling high when prices oscillate).

### Solution
Created `tools/find_profitable_candidates.py` - a comprehensive analysis tool that:
1. Fetches hourly OHLC (Open/High/Low/Close) data from Kraken
2. Calculates volatility metrics and oscillation patterns
3. Estimates profit probability based on historical frequency
4. Ranks candidates by profitability
5. Creates bracketing orders interactively

### Key Features

**Statistical Analysis**:
- Calculates percentage oscillations between consecutive periods
- Measures volatility (average, max, standard deviation)
- Counts significant swings (moves >2% by default)
- Tracks direction changes (price reversals)

**Probability Model**:
```python
probability = (historical_hits / periods) × (1 + oscillation_frequency × 0.5)
```
- Based on historical frequency of hitting target
- Adjusts for oscillation consistency
- Provides confidence levels (low/medium/high)
- Estimates expected time to hit target

**Interactive Mode**:
- Lists ranked candidates
- User selects pair and volume
- Preview order details before execution
- Dry-run mode for safe testing
- Creates limit orders for bracketing

### Implementation Details

**Classes**:
1. `CandidateAnalyzer`: Analyzes pairs for profitability
   - `fetch_ohlc_data()`: Get historical candles
   - `calculate_oscillations()`: Compute volatility metrics
   - `calculate_profit_probability()`: Estimate success probability
   - `analyze_pair()`: Complete analysis pipeline

2. `OrderCreator`: Creates bracketing orders
   - `create_bracket_orders()`: Place buy+sell limit orders
   - `estimate_balance_needed()`: Calculate required funds

**Algorithm for Oscillation Analysis**:
```python
# Calculate % change between consecutive closes
pct_change = ((close[i] - close[i-1]) / close[i-1]) * 100

# Count significant swings
significant = sum(1 for osc in oscillations if abs(osc) >= threshold)

# Count direction changes (oscillation frequency)
changes = sum(1 for i in range(1, len(osc)) 
              if (osc[i] > 0) != (osc[i-1] > 0))
```

**Probability Confidence Levels**:
- **High**: ≥40 periods analyzed AND ≥3 historical hits
- **Medium**: ≥20 periods analyzed AND ≥1 historical hit
- **Low**: Insufficient data or no historical hits

### Usage Examples

**Basic analysis**:
```bash
uv run python tools/find_profitable_candidates.py
```

**Custom parameters**:
```bash
uv run python tools/find_profitable_candidates.py \
  --pairs XXBTZUSD XETHZUSD SOLUSD \
  --hours 72 --target-profit 3.0 --top 5
```

**Interactive with dry-run**:
```bash
uv run python tools/find_profitable_candidates.py \
  --interactive --dry-run
```

### Testing Strategy

Created 10 unit tests covering:
- Oscillation calculations (basic, edge cases)
- Significant swing detection
- Direction change counting
- Probability calculation (high/low/moderate volatility)
- Pair name formatting
- Insufficient data handling

All tests pass without making actual API calls.

### Key Insights

1. **Historical Frequency**: Best predictor is actual historical frequency of hitting target, not just theoretical probability from normal distribution

2. **Oscillation Consistency**: Pairs that oscillate consistently (frequent direction changes) are better candidates than those with rare large moves

3. **Market Conditions**: Tool correctly identifies when market is calm (low volatility) vs volatile - important for risk management

4. **Dry-Run Essential**: Interactive mode with dry-run allows users to safely explore without risking funds

5. **Balance Requirements**: For bracketing, need both fiat (for buy orders) and crypto (for sell orders) - document clearly

### Documentation

- `docs/FIND_PROFITABLE_CANDIDATES.md`: Complete user guide (190 lines)
- `README.md`: Tools section with quick examples
- `demos/demo_find_profitable_candidates.py`: Visual demonstration (200 lines)

### Metrics

- **Code**: 470 lines (tool) + 230 lines (tests) + 200 lines (demo) = 900 lines
- **Tests**: 10 new tests, all passing
- **API Calls**: Efficient - 1 OHLC call per pair analyzed
- **Performance**: Analyzes 4 pairs in ~2 seconds
- **Security**: Passed CodeQL scan, no vulnerabilities

### Related Files
- `tools/find_profitable_candidates.py`: Main implementation
- `tests/test_find_profitable_candidates.py`: Unit tests
- `docs/FIND_PROFITABLE_CANDIDATES.md`: User documentation
- `demos/demo_find_profitable_candidates.py`: Demo script
- `kraken_api.py`: Lines 507-537 (get_ohlc method)

### Future Enhancements (Optional)

1. **Stop Loss Integration**: Add stop-loss orders to bracketing strategy
2. **Backtesting**: Simulate historical performance of identified candidates
3. **Multiple Timeframes**: Analyze 1h, 4h, 1d simultaneously
4. **Export Results**: Save analysis to CSV for further review
5. **Notification Integration**: Alert when good candidates emerge
6. **Risk Metrics**: Calculate max drawdown, Sharpe ratio
7. **Fee Consideration**: Adjust probability for trading fees

---

## Index Price Unavailable Fallback

**Implementation Date**: October 2025

### Problem
Some trading pairs on Kraken don't have an "index price" available, only "last trade price". When creating trailing stop loss orders with `trigger='index'`, these pairs fail with error:
```
EGeneral:Invalid arguments:Index unavailable
```

### Root Cause
- Kraken API supports two trigger types for stop orders: `index` and `last`
- Index price is preferred (more stable, less manipulable)
- Some coins (e.g., smaller altcoins) only have last trade price
- AssetPairs API doesn't indicate which pairs support index price

### Solution
Implemented automatic fallback in `create_tsl_order()` method:
1. Try creating order with `trigger='index'` first (preferred)
2. Catch "Index unavailable" error specifically (case-insensitive)
3. Automatically retry with `trigger='last'`
4. Log the fallback for visibility

### Implementation Details

**Code Location**: `ttslo.py` lines 535-696 (create_tsl_order method)

**Error Detection**:
```python
if 'index unavailable' in error_msg.lower():
   # Retry with trigger='last'
```

**Retry Logic**:
```python
# First attempt
api_kwargs = {'trigger': 'index'}
result = api.add_trailing_stop_loss(..., **api_kwargs)

# On index unavailable error
api_kwargs['trigger'] = 'last'
result = api.add_trailing_stop_loss(..., **api_kwargs)
```

**Logging**:
- WARNING: "Index price unavailable for {pair}, retrying with last trade price"
- INFO: "TSL order created successfully using last price trigger for {pair}"

### Testing

**Test File**: `tests/test_index_unavailable_fallback.py`

**Test Cases** (5 tests, all passing):
1. `test_index_unavailable_retries_with_last_price`: Verify retry succeeds
2. `test_non_index_error_does_not_retry`: Other errors don't trigger retry
3. `test_both_index_and_last_fail`: Handle case where both fail
4. `test_case_insensitive_index_unavailable_detection`: Case variations work
5. `test_successful_first_attempt_no_retry`: Success on first attempt (no retry)

### Key Insights

1. **Prefer Index**: Always try index price first - it's more stable and less prone to manipulation
2. **Automatic Fallback**: Users don't need to configure anything - system handles it transparently
3. **Case Insensitive**: Error detection works regardless of error message case
4. **Minimal Changes**: Only retries on specific error, maintains all other error handling
5. **Logging**: Clear visibility into which trigger was used for each order

### Related Files
- `ttslo.py`: Lines 535-696 (implementation)
- `tests/test_index_unavailable_fallback.py`: Complete test suite
- `api-docs/add-order.md`: API documentation for trigger parameter

### Documentation
From Kraken API docs:
> **trigger** (string): Price signal used to trigger stop/take-profit orders
> - Possible values: `index`, `last`
> - Default value: `last`

### Metrics
- **Code Added**: ~110 lines (retry logic with error handling)
- **Tests Added**: 5 new tests, all passing
- **Total Tests**: 286 passing (up from 281)
- **Performance**: No impact (retry only on specific error)
- **Security**: Maintains all existing safety checks

## Cryptocurrency Statistics Analysis Tool
## Cryptocurrency Statistics Analysis Tool

**Implementation Date**: October 2025

### Problem Statement
Need to analyze cryptocurrency price distributions to make probabilistic predictions about price movements. Specifically: "Can we predict with 95% probability that an asset will exceed a certain threshold within 24 hours?"

### Solution
Created `tools/coin_stats.py` - a comprehensive statistical analysis tool that:
1. Fetches minute-by-minute OHLC data from Kraken (up to 2,880 data points per pair)
2. Calculates comprehensive statistics (mean, median, stdev)
3. Tests for normal distribution using Shapiro-Wilk test
4. Generates distribution graphs with matplotlib
5. Calculates 95% probability thresholds based on statistical analysis

### Key Features

**Statistical Analysis**:
- Basic stats: mean, median, standard deviation, min/max, range
- Percentage change stats: mean, median, stdev of minute-to-minute changes
- Shapiro-Wilk normality test with p-value interpretation
- 95% confidence threshold calculations using normal distribution theory

**Visual Analytics**:
- Dual histogram graphs (price distribution + percentage changes)
- Normal distribution overlay when applicable
- Statistical annotations on graphs
- PNG export for documentation

**Data Export**:
- JSON export with proper numpy/scipy type conversion
- Summary table in terminal
- Detailed per-pair analysis

### Implementation Details

**Normality Testing**:
```python
from scipy import stats as scipy_stats

# Shapiro-Wilk test on percentage changes
statistic, p_value = scipy_stats.shapiro(pct_changes)
is_normal = p_value > 0.05  # p > 0.05 suggests normal distribution
```

**95% Threshold Calculation**:
```python
# Use inverse CDF (percent point function) for 95% probability
z_score = scipy_stats.norm.ppf(1 - 0.95)  # -1.645 for 95%
threshold_pct = abs(z_score * pct_stdev)

# Calculate actual price thresholds
threshold_price_up = mean * (1 + threshold_pct / 100)
threshold_price_down = mean * (1 - threshold_pct / 100)
```

**JSON Serialization Fix**:
- Numpy/scipy types (np.bool_, np.integer, np.floating) not JSON serializable
- Created recursive converter function to handle nested dicts
- Converts all numpy types to native Python types

### Key Insights

1. **Crypto is NOT Normally Distributed**: 
   - In testing, 100% of crypto pairs failed normality tests
   - "Fat tails" are common - more extreme events than normal distribution predicts
   - Confidence levels adjusted accordingly (mostly "LOW")

2. **Minute Data is Valuable**:
   - 2,880 data points (48h) provides good statistical power
   - Captures intraday volatility patterns
   - Better than hourly for short-term predictions

3. **Volatility Varies by Coin**:
   - BTC: Relatively stable, ±0.10% typical 95% threshold
   - ETH: Slightly more volatile, ±0.15%
   - Smaller coins: Can be ±2-5% or more
   - StdDev is good indicator of trading opportunities

4. **Distribution Shapes Matter**:
   - Symmetric distribution = stable, no trend
   - Skewed distribution = directional bias
   - Multiple peaks = trading ranges/support levels
   - Visual inspection complements statistical tests

5. **Tool Design Patterns**:
   - Follow existing tool structure (`find_profitable_candidates.py`)
   - Use same `format_pair_name()` mapping
   - Graceful degradation when scipy/matplotlib unavailable
   - Clear separation: analysis logic vs. presentation

### Testing Strategy

Created 11 unit tests covering:
- Pair name formatting
- Basic statistics calculation
- Statistics consistency with stdlib
- Normality test integration
- Probability threshold calculation
- Data filtering by time
- Complete analysis pipeline
- Graph generation
- Error handling (insufficient data)

All tests use mock data, no API calls required.

### Usage Examples

**Quick Analysis**:
```bash
python3 tools/coin_stats.py --pairs XXBTZUSD --hours 24 --no-graphs
```

**Full Analysis with Graphs**:
```bash
python3 tools/coin_stats.py --pairs XXBTZUSD XETHZUSD SOLUSD --hours 48
```

**Export for Further Processing**:
```bash
python3 tools/coin_stats.py --hours 48 --json-output results.json
```

### Limitations and Warnings

**Statistical Limitations**:
1. Past performance doesn't predict future results
2. 48 hours may not capture weekly/monthly patterns
3. Black swan events not reflected in statistics
4. Non-normal distributions reduce prediction reliability

**Technical Limitations**:
1. Kraken API may limit minute data availability
2. Some pairs may not have full 48 hours of data
3. Requires scipy/matplotlib for full functionality
4. Large memory usage for many pairs (stores all candles)

### Documentation

- `docs/COIN_STATS.md`: Complete user guide (250+ lines)
- `demos/demo_coin_stats.py`: Interactive demonstration (200+ lines)
- `README.md`: Quick examples in Tools section
- `tests/test_coin_stats.py`: Test suite with examples

### Metrics

- **Code**: 615 lines (tool) + 280 lines (tests) + 240 lines (demo) = 1,135 lines
- **Tests**: 11 tests, all passing
- **Documentation**: 250 lines user guide + 200 lines demo
- **API Calls**: 1 OHLC call per pair (efficient)
- **Performance**: Analyzes 3 pairs in ~5 seconds
- **Security**: Passed CodeQL scan, no vulnerabilities

### Related Files
- `tools/coin_stats.py`: Main implementation
- `tests/test_coin_stats.py`: Unit tests  
- `docs/COIN_STATS.md`: User documentation
- `demos/demo_coin_stats.py`: Demo script
- `kraken_api.py`: OHLC endpoint (interval=1 for minute data)

### Future Enhancements (Optional)

1. **Multiple Timeframes**: Analyze 1m, 5m, 15m, 1h simultaneously
2. **Correlation Analysis**: Compare movement between pairs
3. **Backtesting**: Validate threshold predictions against historical data
4. **Volatility Forecasting**: Predict future volatility (GARCH models)
5. **Risk Metrics**: VaR, CVaR, Sharpe ratio calculations
6. **Machine Learning**: LSTM/ARIMA for time series prediction
7. **Real-time Updates**: Stream data and update statistics live
8. **Alert Integration**: Notify when volatility exceeds thresholds

---

## Dashboard /api/completed Missing Recent Orders (2025-10-24)

**Problem**: Dashboard only showed 2 old completed orders even though new orders were being filled.

**Initial Incorrect Diagnosis**: 
- Initially thought Kraken API's 50-order limit on `ClosedOrders` was the issue
- Added `start` parameter to fetch last 30 days - but testing showed this didn't help
- The real issue: triggered orders in state.csv weren't in the most recent 50 closed orders

**Root Cause** (Corrected):
- Dashboard matched state entries against `ClosedOrders` API response (max 50 orders)
- If the specific order IDs from state.csv weren't in those 50 recent orders, they wouldn't appear
- Account had 362 total closed orders, but API only returns 50 at a time
- The `start` parameter doesn't change this - still returns only 50 orders even with time filter

**Solution**:
- Added `query_orders(txids)` method to kraken_api.py using Kraken's `QueryOrders` endpoint
- Modified `get_completed_orders()` to directly query specific order IDs from state
- More efficient: only queries the exact orders needed (typically 3-4) vs fetching 50 unrelated orders
- Includes fallback to old method if query_orders fails

**Implementation**:
1. **kraken_api.py**: Added `query_orders(txids)` method
   - Accepts list or comma-separated string of order IDs (up to 50)
   - Uses Kraken's `QueryOrders` private API endpoint
   - Returns order details for specified transaction IDs

2. **dashboard.py**: Updated `get_completed_orders()`
   - Collects order IDs from triggered state entries first
   - Calls `query_orders()` with specific order IDs
   - Falls back to `get_cached_closed_orders()` on error
   - More efficient and reliable

3. **creds.py**: Added support for `COPILOT_KRAKEN_API_KEY` and `COPILOT_KRAKEN_API_SECRET`
   - Allows GitHub Copilot agent to test with live production data (read-only)

**Testing**:
- All dashboard tests pass
- Live testing confirmed `query_orders()` works with production API
- Queried 3 specific orders successfully from 362 total closed orders

**Key Insights**:
1. **Direct Query > Listing**: Querying specific order IDs is more efficient than listing all and filtering
2. **Kraken API Limits**: `ClosedOrders` returns max 50 orders, even with `start` parameter
3. **QueryOrders Endpoint**: Can query up to 50 specific order IDs in one call
4. **State-Driven Approach**: Use state.csv as source of truth for which orders to query

**Related Files**:
- `kraken_api.py`: Lines 960-990 (query_orders method)
- `dashboard.py`: Lines 337-445 (get_completed_orders function)
- `creds.py`: Lines 91-95 (COPILOT_KRAKEN_API_KEY support)

---

## Dashboard Price Formatting for Small Value Coins (2025-10-25)

**Problem**: Dashboard displayed very small coin prices as "$0.00" because all prices used `.toFixed(2)` (2 decimal places).
- Example: MEMEUSD worth $0.001679 showed as "$0.00"
- Users couldn't see actual trigger prices for meme coins and other low-value assets

**Root Cause**: 
- `templates/dashboard.html` used hardcoded `.toFixed(2)` for ALL price displays
- Line 649: `$${parseFloat(order.trigger_price || 0).toFixed(2)}`
- Same pattern in ~20 places throughout the template

**Solution**: Created smart `formatPrice()` JavaScript function with dynamic decimal places:
```javascript
function formatPrice(value) {
    const price = parseFloat(value);
    
    // Very small values (< $0.01): up to 8 decimals, remove trailing zeros
    if (Math.abs(price) < 0.01) {
        return price.toFixed(8).replace(/\.?0+$/, '');
    }
    // Small values (< $1): 4 decimals
    else if (Math.abs(price) < 1) {
        return price.toFixed(4);
    }
    // Medium values (< $100): 2 decimals
    else if (Math.abs(price) < 100) {
        return price.toFixed(2);
    }
    // Large values: 2 decimals with thousands separator
    else {
        return price.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
}
```

**Examples**:
- $0.001679 → "$0.001679" (was "$0.00")
- $0.00000123 → "$0.00000123" (was "$0.00")
- $0.5678 → "$0.5678"
- $12.345 → "$12.35"
- $1234.567 → "$1,234.57"

**Changes Made**:
- Pending Orders: threshold price, current price, distance to trigger
- Active Orders: trigger price
- Completed Orders: trigger price, executed price, benefit amount

**Testing**:
- Created `tests/test_dashboard_price_formatting.py` with Python equivalents
- Tests verify all price ranges work correctly
- Specifically tests the MEME coin issue case

**Key Insights**:
1. **Dynamic Precision**: Different price ranges need different decimal places
2. **Trailing Zeros**: Remove for cleaner display (0.001 not 0.00100000)
3. **Readability**: Larger numbers benefit from thousands separators
4. **Edge Cases**: Handle null/undefined/N/A gracefully

**Related Files**:
- `templates/dashboard.html`: Lines 381-437 (formatPrice function), all price displays
- `tests/test_dashboard_price_formatting.py`: Test suite

---

## Dashboard Cancel Buttons & Actions (2025-10-25)

**Implementation**: Added cancel functionality to dashboard for managing pending and active orders.

**Features**:
1. **Pending Orders Cancel** - Set enabled status
   - POST `/api/pending/<id>/cancel` - disable/pause/cancel pending config
   - Supports states: `true`, `false`, `paused`, `canceled`
   - Updates config.csv atomically (preserves comments)
   - Red "Cancel" button on each pending order card

2. **Active Orders Cancel** - Cancel live Kraken orders
   - POST `/api/active/<order_id>/cancel` - cancels live order on Kraken
   - Calls `KrakenAPI.cancel_order(txid)`
   - Red "Cancel Order" button on each active order card

3. **Cancel All** - Emergency stop for all orders
   - POST `/api/cancel-all` - cancels ALL open orders
   - Double confirmation dialog (destructive action)
   - Handles partial failures gracefully
   - Red "🛑 Cancel All Active Orders" button at bottom

**UI Design**:
- Red buttons (btn-danger) for destructive actions
- Small buttons on cards (btn-small)
- Confirmation dialogs before cancel
- Double confirmation for Cancel All
- Clear error messages

**Backend** (`config.py`):
- `update_config_enabled(config_id, status)` - updates single config
- Supports: `true`, `false`, `paused`, `canceled`
- Uses atomic write (prevents data loss)
- Preserves ALL CSV lines (comments, empty rows)

**Testing** (`tests/test_dashboard_cancel.py`):
- 13 tests covering all scenarios
- Tests status updates, API calls, error handling
- Tests graceful degradation (no Kraken API)
- Tests partial failures in Cancel All

**Kraken API Quirks** (handled):
- `cancel_order(txid)` works for spot/funding wallets
- Returns `{'count': 1}` on success
- Handles API errors gracefully
- No special wallet handling needed (Kraken handles internally)

**Security**:
- POST endpoints only (prevents accidental GET cancels)
- Confirmation dialogs prevent fat-finger errors
- Double confirmation for Cancel All
- Clear error messages (no sensitive data exposed)

**Related Files**:
- `dashboard.py`: Lines 825-943 (cancel endpoints)
- `config.py`: Lines 510-540 (update_config_enabled)
- `templates/dashboard.html`: Cancel buttons, JS functions
- `tests/test_dashboard_cancel.py`: Complete test suite

**Usage**:
- Pending orders: Click "Cancel" → confirms → sets enabled=canceled
- Active orders: Click "Cancel Order" → confirms → cancels on Kraken
- Cancel All: Click button → double confirm → cancels all open orders

**Notes**:
- Cancel pending: Only updates config.csv (order not yet on Kraken)
- Cancel active: Calls Kraken API to cancel live order
- enabled field is text, supports future states (e.g., "scheduled", "error")
- Comment in config.csv updated to reflect new values

---

## Dashboard Cancel Button Permission Fix (2025-10-26)

**Problem**: Cancel buttons in dashboard (cancel pending, cancel active, cancel all) returned "permission denied" errors when users tried to cancel orders.

**Root Cause**: Dashboard initialized Kraken API with `readwrite=False` (line 80 of dashboard.py), using read-only credentials. Cancel operations require write permissions to modify/cancel orders on Kraken.

**Solution**: Changed dashboard initialization to use read-write credentials:
```python
# BEFORE (wrong - caused permission denied)
kraken_api = KrakenAPI.from_env(readwrite=False)

# AFTER (correct - allows cancellation)
kraken_api = KrakenAPI.from_env(readwrite=True)
```

**Impact**:
- Cancel All button now works
- Individual "Cancel" buttons on pending orders now work
- Individual "Cancel Order" buttons on active orders now work
- Requires `KRAKEN_API_KEY_RW` and `KRAKEN_API_SECRET_RW` environment variables to be set

**Key Insight**: Dashboard needs write permissions for cancel functionality, even though it only reads data most of the time. The cancel endpoints were already implemented correctly - only the API initialization was wrong.

**Documentation Updated**:
- README.md: Updated security note about credentials
- docs/DASHBOARD_README.md: Updated security notes section

**Related Files**:
- `dashboard.py`: Line 80 (API initialization)
- `tests/test_dashboard_cancel.py`: All 13 tests pass
- Issue referenced in problem statement about cancel buttons not working

---

## Minimum Volume Validation to Prevent Repeated Errors (2025-10-27)

**Feature**: Added early validation of order volume against Kraken's minimum order size (ordermin) to prevent repeated errors and notifications.

**Problem**: When trigger price reached but volume < Kraken's minimum (e.g., NEARUSD min=0.7, config has 0.1):
- System detects threshold met
- Tries to create order
- Gets "volume minimum not met" error from Kraken
- Repeats EVERY monitoring cycle (60s)
- Sends repeated Telegram notifications
- Clutters logs with same error

**Root Cause**:
- No pre-validation of volume against pair-specific minimums
- No error state tracking to prevent repeated attempts
- Every cycle: threshold check → order attempt → failure → notification

**Solution**: Multi-layered approach to handle volume validation properly

**Implementation**:

1. **Fetch Pair Info** (`kraken_api.py`):
   ```python
   def get_asset_pair_info(self, pair):
       """Get ordermin, costmin, decimals from AssetPairs API."""
       result = self._query_public('AssetPairs', {'pair': pair})
       # Returns: {'ordermin': '0.7', 'costmin': '0.5', ...}
   ```

2. **Early Volume Validation** (`ttslo.py`):
   ```python
   def check_minimum_volume(self, pair, volume, config_id):
       """Check volume against Kraken's ordermin BEFORE creating order."""
       pair_info = self.kraken_api_readonly.get_asset_pair_info(pair)
       if not pair_info:
           # Pair info unavailable - allow order (Kraken will validate)
           return (True, 'Could not verify minimum volume', None)
       
       ordermin_str = pair_info.get('ordermin')
       if not ordermin_str:
           return (True, 'No minimum volume specified', None)
       
       ordermin = Decimal(ordermin_str)
       volume_decimal = Decimal(str(volume))
       
       if volume_decimal < ordermin:
           return (False, f'Volume {volume} below minimum {ordermin}', str(ordermin))
       return (True, f'Volume meets minimum', str(ordermin))
   ```

3. **Error State Tracking** (`ttslo.py`):
   ```python
   def _handle_order_error_state(self, config_id, error_msg, notify_type, notify_args):
       """Track errors and send notification only once."""
       self.state[config_id]['last_error'] = error_msg
       
       # Send notification only if not already notified
       if not self.state[config_id].get('error_notified'):
           self.notification_manager.notify_order_failed(**notify_args)
           self.state[config_id]['error_notified'] = True
   ```

4. **Dashboard Warning** (`dashboard.py`):
   ```python
   # Check minimum volume for each pending order
   pair_info = kraken_api.get_asset_pair_info(pair)
   ordermin = float(pair_info['ordermin'])
   
   if volume < ordermin:
       volume_too_low = True
       volume_message = f'Volume {volume} below minimum {ordermin} for {pair}'
   ```

5. **UI Display** (`templates/dashboard.html`):
   ```javascript
   // Show warning icon with tooltip
   if (order.volume_too_low) {
       warningMessage = order.volume_message;
       showWarning = true;
   }
   
   const warningIcon = showWarning
       ? '<span class="warning-icon" data-tooltip="...">⚠️</span>'
       : '';
   
   // Disable Force button
   const forceButtonDisabled = order.volume_too_low ? 'disabled' : '';
   ```

**Key Features**:

1. **Early Detection**: Volume validated BEFORE attempting order creation
2. **Single Notification**: Error tracked in state.csv → notify only once
3. **Dashboard Warning**: Visual ⚠️ indicator in pending panel with tooltip
4. **Graceful Degradation**: If API unavailable, allows order to proceed (validation at Kraken)
5. **State Tracking**: Uses `last_error` and `error_notified` fields in state.csv

**State Fields**:
- `last_error`: Stores error message (e.g., "Volume 0.1 below minimum 0.7")
- `error_notified`: Boolean flag to prevent repeated notifications
- Both cleared when config re-enabled or threshold type changes

**Flow**:

```
Cycle 1:
  ✓ Threshold met
  ✓ Check volume: 0.1 < 0.7 → FAIL
  ✓ Update last_error in state
  ✓ Send Telegram notification (error_notified=False)
  ✓ Set error_notified=True
  ✗ Do not create order

Cycle 2+:
  ✓ Threshold still met
  ✓ Check volume: 0.1 < 0.7 → FAIL
  ✓ last_error already set
  ✗ Skip notification (error_notified=True)
  ✗ Do not create order
```

**Testing**:
- 8 new tests covering all scenarios
- All 427 existing tests still passing
- Tests verify: validation logic, error state tracking, notification suppression, dashboard display

**Key Insights**:

1. **Validate Early**: Check requirements BEFORE attempting expensive operations
2. **Track Error State**: Prevent repeated notifications for same error
3. **Graceful Fallback**: If validation unavailable, let Kraken reject (fail gracefully)
4. **Clear Error State**: Reset when config changed/re-enabled
5. **User-Friendly**: Show warnings in dashboard before user forces trigger

**Example Minimum Volumes** (from AssetPairs API):
- NEARUSD: 0.7
- BTCUSD: 0.0001  
- ETHUSD: 0.005
- SOLUSD: 0.05

**Related Files**:
- `kraken_api.py`: Lines 700-738 (get_asset_pair_info)
- `ttslo.py`: Lines 273-329 (check_minimum_volume), 430-468 (_handle_order_error_state), 550-575 (validation call)
- `dashboard.py`: Lines 267-291 (volume check in get_pending_orders)
- `templates/dashboard.html`: Lines 753-773, 841-861 (warning icon rendering)
- `tests/test_minimum_volume_validation.py`: Complete test suite (8 tests)

**Documentation**: This prevents the exact issue described in GitHub Issue - repeated errors and notifications when volume < ordermin.

---

## Dashboard Force Button Cache Invalidation (2025-10-27)

**Problem**: After clicking Force button on pending order, order initially showed "Manual" tag incorrectly. Tag disappeared after ~30 seconds.

**Root Cause**: `api_force_pending` endpoint updated state.csv with order_id but didn't invalidate caches:
- `get_cached_state()` returned stale data (no order_id)
- `get_active_orders()` couldn't match order to state
- Order incorrectly marked as "Manual" (line 434)
- After cache expired, fresh state loaded with order_id
- Order then matched via state, "Manual" tag disappeared

**Solution**: Added cache invalidation after state update (lines 1260-1267):
```python
# Invalidate caches so next request gets fresh data
# Force button affects multiple views:
# - Pending: order moves from pending to active (triggered=true in state)
# - Active: order now appears here (matched via order_id in state)  
# - State: contains new order_id, triggered flag, trigger_time
# - Config: contains updated threshold_price and trigger info
get_cached_state.invalidate()  # State was modified (order_id added)
get_active_orders.invalidate()  # Active orders will now match via state
get_pending_orders.invalidate()  # Order no longer pending (triggered=true)
get_cached_config.invalidate()  # Config was modified (trigger info added)
```

**Why 4 Caches?**:
1. **get_cached_state**: Contains order_id, triggered flag, trigger_time (changed)
2. **get_active_orders**: Now matches order via state (must refresh to show)
3. **get_pending_orders**: Order no longer pending (must refresh to remove)
4. **get_cached_config**: Contains updated threshold_price and trigger info (changed)

**Key Insights**:
1. **Cache Invalidation is Critical**: Any endpoint that modifies state/config MUST invalidate ALL affected caches
2. **Consistency Pattern**: Follow same pattern as `api_cancel_pending` (lines 1045-1046)
3. **Multiple Views**: Force button affects pending, active, state, and config views - invalidate all
4. **Order Matching Logic**: Orders marked "Manual" when in Kraken but NOT in cached state
5. **Test Coverage**: Add regression test to prevent future cache invalidation bugs
6. **Document Why**: Add comments explaining which caches need invalidation and why

**Related Files**:
- `dashboard.py`: Lines 1260-1267 (fix), 434 (manual flag logic), 1045-1046 (reference pattern)
- `tests/test_force_button_cache_invalidation.py`: Regression test verifies all 4 caches
- Issue description: User workflow that exposed the bug

**Similar Issues Fixed Previously**:
- Cancel button cache invalidation (2025-10-27) - same root cause, same pattern

---

*Add new learnings here as we discover them*


---

## Initial Price Tracking for Total Benefit Calculation (2025-10-26)

**Feature**: Added tracking of initial price to show the true benefit of using the TTSLO system.

**Problem**: Dashboard only showed "slippage" (trigger price vs executed price), which is typically negative due to the trailing offset mechanism. Users couldn't see the **real benefit** of waiting for better prices instead of executing a market order immediately.

**Solution**: Added `initial_price` field that captures the price when a config is first created/enabled.

**Implementation**:

1. **State.csv**: Added `initial_price` field to state fieldnames
   - Automatically populated on first run when config is processed
   - Never overwritten - preserves the original decision price

2. **ttslo.py**: Step 10 in `process_config()` populates initial_price
   ```python
   if not self.state[config_id].get('initial_price'):
       self.state[config_id]['initial_price'] = str(current_price)
   ```

3. **dashboard.py**: Calculate two benefit metrics
   - **Slippage** (existing): trigger_price vs executed_price (usually negative)
   - **Total Benefit** (new): initial_price vs executed_price (usually positive!)

4. **Dashboard UI**: Added two display rows
   - "Initial Price" - shows price when config was created
   - "Total Benefit" - shows real benefit with help tooltip

**Example**:
```
Sell BTC:
  Initial Price:   $45,000 (when user created config)
  Trigger Price:   $48,000 (when threshold met)
  Executed Price:  $47,500 (when TSL order filled)
  
  Slippage:        -$500   (-1.04%) ← Normal TSL cost
  Total Benefit:   +$2,500 (+5.56%) ← Real benefit!
```

**Key Insight**: Even with negative slippage, the user is $2,500 better off than if they had sold immediately. This is the core value proposition of the TTSLO system.

**Documentation**: Updated `docs/UNDERSTANDING_BENEFIT.md` with comprehensive explanation of both metrics and when each is useful.

**Testing**: Added 4 new tests in `tests/test_initial_price.py`:
- Test initial_price populated on first run
- Test initial_price not overwritten on subsequent runs
- Test total_benefit calculation for sell orders
- Test total_benefit calculation for buy orders

**Files Changed**:
- `config.py`: Added initial_price to state fieldnames
- `ttslo.py`: Auto-populate initial_price on first run
- `dashboard.py`: Calculate and return total_benefit
- `templates/dashboard.html`: Display initial_price and total_benefit
- `docs/UNDERSTANDING_BENEFIT.md`: Comprehensive documentation
- `tests/test_initial_price.py`: New test suite

**Result**: All 358 tests passing. Feature ready for production use.

---

## GitHub Environment Secrets Support (2025-10-24)

**Implementation Date**: October 2025

### Problem
Need to enable read-only live API tests in GitHub Actions CI/CD using repository secrets without hardcoding credentials or using complex secret name patterns.

### Solution
Extended `creds.py` to support `COPILOT_KRAKEN_API_KEY` and `COPILOT_KRAKEN_API_SECRET` as fallback options for read-only Kraken API credentials.

### Implementation Details

**Precedence Order** (for `KRAKEN_API_KEY` and `KRAKEN_API_SECRET`):
1. Exact environment variable name (e.g., `KRAKEN_API_KEY`)
2. Copilot-prefixed name (e.g., `copilot_KRAKEN_API_KEY`)
3. COPILOT_W_KR_RO_PUBLIC / COPILOT_W_KR_RO_SECRET (existing pattern)
4. COPILOT_W_KR_PUBLIC / COPILOT_W_KR_SECRET (existing fallback)
5. **NEW**: `COPILOT_KRAKEN_API_KEY` / `COPILOT_KRAKEN_API_SECRET` (GitHub secrets)

**Code Changes**:
- Modified `get_env_var()` in `creds.py` to add new fallback options
- Only 6 lines of code changed (surgical modification)
- Maintained backward compatibility with all existing patterns

**Testing**:
- Created 18 new tests in `tests/test_creds.py`
- All tests pass, no regressions
- Comprehensive coverage of precedence rules and fallback behavior

**Documentation**:
- Updated `.env.example` with explanation of all supported patterns
- Updated `README.md` to document multiple credential sources
- Updated `tests/test_kraken_api_live.py` docstring
- Created `demos/demo_github_secrets.py` to demonstrate functionality

### Usage in GitHub Actions

Set repository secrets in GitHub:
```yaml
secrets:
  COPILOT_KRAKEN_API_KEY: ${{ secrets.COPILOT_KRAKEN_API_KEY }}
  COPILOT_KRAKEN_API_SECRET: ${{ secrets.COPILOT_KRAKEN_API_SECRET }}
```

The application will automatically pick these up for read-only operations without code changes.

### Key Benefits

1. **Zero Code Changes**: Existing code automatically works with GitHub secrets
2. **Flexible Deployment**: Supports dev (.env), CI/CD (GitHub secrets), and production (env vars)
3. **Secure by Default**: Secrets never committed to repository
4. **Clear Precedence**: Standard names always take priority over secret patterns

### Related Files
- `creds.py`: Lines 92-99 (implementation)
- `tests/test_creds.py`: Complete test suite (18 tests)
- `demos/demo_github_secrets.py`: Demonstration script
- `.env.example`: Updated documentation
- `README.md`: Updated credential documentation

---

## Merge & Test Learnings (2025-10-24)

- Resolved merge conflicts on branch `copilot/fix-tslo-index-error` keeping both behaviors:
  - Automatic fallback from `trigger='index'` to `trigger='last'` when Kraken returns "Index unavailable".
  - Preserve `KrakenAPIError`-specific logging, notifications and state updates from `origin/main`.

- Fixes made:
  - `ttslo.create_tsl_order()` now:
    - retries with `trigger='last'` when index is unavailable and uses the retry result instead of falling through to generic error handling;
    - notifies via `NotificationManager.notify_insufficient_balance` when balance check fails (even if no state entry exists yet);
    - preserves existing state-based `_handle_order_error_state()` updates when state entry exists.
  - `config.ConfigManager.save_state()` and `initialize_state_file()` updated to include `last_error` and `error_notified` in CSV headers so saving state won't raise a fields mismatch.

- Validation:
  - Created a local venv and ran the full pytest suite inside it.
  - Test results: 297 passed, 6 skipped.

- Git/PR status:
  - Branch `copilot/fix-tslo-index-error` contains the merge resolution and tests-green changes.
  - After this commit I'll push the LEARNINGS update and check the existing PR for mergeability.

- Notes / follow-ups:
  - PR: "Fix: Add automatic fallback to last price when index price unavailable" (active PR in this repo) — verify CI/branch protection in GitHub before merging.
  - Consider adding a tiny unit test to assert that `NotificationManager.notify_insufficient_balance` is called when balance is insufficient (already covered by existing tests, but worth an explicit assertion in integration tests).



---

## Merge & Test Learnings (2025-10-24)

- Resolved merge conflicts on branch `copilot/fix-tslo-index-error` keeping both behaviors:
  - Automatic fallback from `trigger='index'` to `trigger='last'` when Kraken returns "Index unavailable".
  - Preserve `KrakenAPIError`-specific logging, notifications and state updates from `origin/main`.

- Fixes made:
  - `ttslo.create_tsl_order()` now:
    - retries with `trigger='last'` when index is unavailable and uses the retry result instead of falling through to generic error handling;
    - notifies via `NotificationManager.notify_insufficient_balance` when balance check fails (even if no state entry exists yet);
    - preserves existing state-based `_handle_order_error_state()` updates when state entry exists.
  - `config.ConfigManager.save_state()` and `initialize_state_file()` updated to include `last_error` and `error_notified` in CSV headers so saving state won't raise a fields mismatch.

- Validation:
  - Created a local venv and ran the full pytest suite inside it.
  - Test results: 297 passed, 6 skipped.

- Git/PR status:
  - Branch `copilot/fix-tslo-index-error` contains the merge resolution and tests-green changes.
  - After this commit I'll push the LEARNINGS update and check the existing PR for mergeability.

- Notes / follow-ups:
  - PR: "Fix: Add automatic fallback to last price when index price unavailable" (active PR in this repo) — verify CI/branch protection in GitHub before merging.
  - Consider adding a tiny unit test to assert that `NotificationManager.notify_insufficient_balance` is called when balance is insufficient (already covered by existing tests, but worth an explicit assertion in integration tests).


---

## Repeated Notification Prevention (2025-10-27)

**Feature**: Added `trigger_notified` flag to prevent repeated notifications when trigger price reached but order creation impossible.

**Problem**: GitHub Issue - "Repeated errors when trigger price reached but no balance"
- System sent "🎯 Trigger price reached!" notification EVERY monitoring cycle
- System sent "⚠️ Cannot create order - Insufficient balance!" notification EVERY cycle
- No order created → state NOT updated → notifications repeated forever
- User spammed with identical messages every 60 seconds

**Root Cause**:
1. `process_config()` at line 1238: Sends "trigger price reached" when threshold met
2. `create_tsl_order()` at line 625: Balance check fails, sends "insufficient balance", returns None
3. `process_config()` at line 1254: If order_id is None, does NOT mark config as triggered
4. Next cycle: threshold still met → repeat from step 1

**Solution**: Track notification state to prevent spam

**Implementation**:

1. **State Field** (`config.py`):
   ```python
   fieldnames = [..., 'trigger_notified']  # Track trigger notification sent
   ```

2. **Initialize Flag** (`ttslo.py` line 1108):
   ```python
   self.state[config_id] = {
       ...
       'trigger_notified': False,  # Track if we've sent "trigger price reached"
   }
   ```

3. **Check Before Sending** (`ttslo.py` line 1241):
   ```python
   if self.notification_manager and not self.state[config_id].get('trigger_notified'):
       self.notification_manager.notify_trigger_price_reached(...)
       self.state[config_id]['trigger_notified'] = True
   ```

4. **Balance Check Notification** (`ttslo.py` line 632):
   - Uses `_handle_order_error_state` when state exists
   - Checks `error_notified` flag to prevent repeated error notifications
   - Falls back to direct notification for standalone calls

**Behavior**:

```
Cycle 1 (Balance Insufficient):
  ✓ Threshold met
  ✓ Send "trigger price reached" notification
  ✓ Set trigger_notified=True
  ✓ Balance check fails
  ✓ Send "insufficient balance" notification (via _handle_order_error_state)
  ✓ Set error_notified=True
  ✗ No order created

Cycle 2+:
  ✓ Threshold still met
  ✗ Skip "trigger price reached" (trigger_notified=True)
  ✓ Balance check still fails
  ✗ Skip "insufficient balance" (error_notified=True)
  ✗ No order created
  → No spam!
```

**Retry Workflow**:
- User must disable/re-enable config to reset flags
- Or delete state entry for fresh start
- Flags persist while issue unfixed (prevents spam)

**Key Features**:
1. **Single Notification**: Each error type sent only once
2. **Persistent State**: Flags saved in state.csv across restarts
3. **User Control**: Disable/re-enable to retry after fixing issue
4. **Backward Compatible**: Existing configs work without changes

**Testing**:
- 4 new tests covering all scenarios
- 1 updated test reflecting new behavior
- All 449 tests passing

**Related Files**:
- `config.py`: Lines 345, 425 (fieldnames)
- `ttslo.py`: Lines 1108, 1120-1127, 1241-1250 (implementation)
- `tests/test_repeated_notification_fix.py`: Complete test suite
- `tests/test_minimum_volume_validation.py`: Updated test

**Similar Pattern**: Reuses `error_notified` pattern from minimum volume validation feature

---



**Problem**: Balance checks were failing with "Available Balance: unknown" for pairs like DYDXUSD because:
1. GitHub Copilot agent sets credentials as `COPILOT_KRAKEN_API_KEY` (uppercase prefix)
2. `creds.py` was only checking for `copilot_KRAKEN_API_KEY` (lowercase prefix)
3. Credentials were not found, so balance API call failed

**Fix**: Updated `get_env_var()` in `creds.py` to check both uppercase and lowercase variants:
- Check exact name
- Check `COPILOT_` prefix (uppercase) - **NEW**
- Check `copilot_` prefix (lowercase) - existing
- Check `COPILOT_W_*` mappings - existing

**Testing**: Created `tools/test_balance_copilot.py` to verify credentials are found and balance API works.

---

## Understanding Negative "Benefit" in Dashboard (2025-10-25)

**Issue**: Users confused by negative "benefit" values in Completed Orders section, thinking they were losing money.

**Root Cause**: 
- "Benefit" is actually **slippage** - difference between trigger price and execution price
- For TSL orders, negative slippage is NORMAL and EXPECTED
- The trailing mechanism means price must move against you (by trailing offset %) before order executes
- Example: Sell triggers at $2.53, executes at $2.50 with 1% trailing = -1.23% slippage

**Why This Happens**:
- TSL orders trail the price by the offset percentage
- When price reverses, order triggers at the offset distance
- This is the COST of using TSL protection (like insurance)
- It's NOT a net loss on the total trade

**Solution**:
1. Created comprehensive guide: `docs/UNDERSTANDING_BENEFIT.md`
2. Renamed "Benefit" to "Slippage" in dashboard UI
3. Added help icons with tooltips explaining what slippage means
4. Added README section explaining negative values are normal
5. Documented expected ranges: -1% to -2% matching trailing offset

**Key Insight**: 
- Users should focus on TOTAL PROFIT (buy price vs sell price minus fees/slippage)
- Not on individual order slippage
- The bracket strategy (buy low, sell high) still profits despite slippage
- Example: Buy at $2.31, sell at $2.50 = +$0.19 gross, -$0.04 slippage, +$0.14 net profit

**Related Files**:
- `docs/UNDERSTANDING_BENEFIT.md`: Complete explanation with examples
- `templates/dashboard.html`: UI updates (label, tooltips)
- `README.md`: Quick explanation section
- `dashboard.py`: Lines 424-433 (benefit calculation)

---

## USD Pair Suffix Support (2025-10-24)

**Problem**: Balance checks were failing for pairs ending in 'USD' (like DYDXUSD, ATOMUSD, SOLUSD) because:
1. `_extract_base_asset()` only checked for suffixes: USDT, ZUSD, ZEUR, EUR, etc.
2. It didn't check for plain 'USD' suffix
3. For DYDXUSD, base asset extraction returned empty string
4. Balance lookup failed completely

**Fix**: Added 'USD' to the list of quote currency suffixes in `_extract_base_asset()`:
```python
# Note: Order matters - check longer suffixes first (e.g., USDT before USD)
for quote in ['USDT', 'ZUSD', 'ZEUR', 'EUR', 'ZGBP', 'GBP', 'ZJPY', 'JPY', 'USD']:
```

**Why order matters**: 
- Some pairs might theoretically end with both USDT and USD
- Checking USDT first ensures we get the most specific match
- Example: "XXBTUSDT" should match USDT (4 chars) not USD (3 chars)

**Testing**: 
- Created `tools/test_dydx_balance.py` to test with live API
- Created `tests/test_balance_fix.py` with unit tests
- Verified DYDXUSD, ATOMUSD, SOLUSD all work correctly

**Result**: Balance checking now works for all USD pairs, properly aggregating spot and funding wallet balances.

---

## Buy Order Balance Check Logic Error (2025-10-25)

**Problem**: Dashboard incorrectly checked base asset balance for buy orders.
- Example: ATOMUSD buy order checked ATOM balance (should check USD)
- User had 0 ATOM but plenty of USD → showed "Critical: Insufficient balance"
- Error message: "Insufficient balance for buy orders (0.0000 < 2.4049)" for ATOM

**Root Cause**: `dashboard.py` lines 630-644 in `get_balances_and_risks()`
- Line 636 incorrectly added buy volume to base asset: `assets_needed[base_asset]['buy_volume'] += volume`
- For buy orders, we need quote currency (USD), not base asset (ATOM)
- Risk check at lines 681-684 then flagged insufficient ATOM balance for buy order

**Fix**:
```python
# BEFORE (wrong)
elif direction == 'buy':
    assets_needed[base_asset]['buy_volume'] += volume  # ❌ Wrong!
    assets_needed[base_asset]['pairs'].add(pair)
    
    # For buys, we also need the quote currency
    if quote_asset and pair in prices:
        price = prices[pair]
        quote_needed = volume * price
        assets_needed[quote_asset]['buy_volume'] += quote_needed
        assets_needed[quote_asset]['pairs'].add(pair)

# AFTER (correct)
elif direction == 'buy':
    # Buying base asset - need quote currency balance (not base asset)
    # Track the pair for the base asset but don't require base asset balance
    assets_needed[base_asset]['pairs'].add(pair)  # ✅ Only track pair
    
    # For buys, we need the quote currency (unchanged)
    if quote_asset and pair in prices:
        price = prices[pair]
        quote_needed = volume * price
        assets_needed[quote_asset]['buy_volume'] += quote_needed
        assets_needed[quote_asset]['pairs'].add(pair)
```

**Key Insight**:
- **Buy orders**: Need quote currency (USD to buy ATOM)
- **Sell orders**: Need base asset (ATOM to sell)
- Dashboard now correctly shows:
  - Buy ATOMUSD: Check USD balance (not ATOM)
  - Sell ATOMUSD: Check ATOM balance (not USD)

**Testing**:
- Added 2 comprehensive tests in `test_dashboard_balances.py`
- `test_buy_order_checks_quote_currency_not_base`: Verifies buy logic
- `test_sell_order_checks_base_currency_not_quote`: Verifies sell logic
- Tests handle cache TTL (30s) to avoid cross-test pollution

**Related Files**:
- `dashboard.py`: Lines 630-644 (fix applied)
- `tests/test_dashboard_balances.py`: New tests added

---

## ZUSD vs USD Currency Normalization (2025-10-25)

**Problem**: Dashboard showed two separate balance entries:
- USD: 0 balance (critical warning)
- ZUSD: 155.80 balance (sufficient)

User confused: "Aren't USD and ZUSD the same thing?" Yes!

**Root Cause**:
- Trading pairs have inconsistent suffixes:
  - ATOMUSD, DYDXUSD, FILUSD → extract "USD"
  - XXBTZUSD, XETHZUSD → extract "ZUSD"
- Kraken API returns balances with Z-prefixed fiat codes:
  - `{'ZUSD': '155.80', 'ZEUR': '100.0'}` (NOT `{'USD': ..., 'EUR': ...}`)
- Dashboard's `_extract_quote_asset()` returned raw suffix
- Balance lookup: USD → 0 (not in API), ZUSD → 155.80

**Why Z-prefix?**
Kraken uses Z-prefix for fiat currencies in API responses:
- USD → ZUSD
- EUR → ZEUR  
- GBP → ZGBP
- JPY → ZJPY

Stablecoins (USDT) don't get Z-prefix (they're crypto, not fiat).

**Solution**:
Updated `_extract_quote_asset()` to normalize all fiat to Z-prefix:
```python
if quote == 'USD':
    return 'ZUSD'
elif quote == 'EUR':
    return 'ZEUR'
# ... etc
```

**Result**:
- Dashboard now shows single ZUSD entry
- All USD and ZUSD pairs aggregate correctly
- No more confusion about "sufficient ZUSD but insufficient USD"

**Key Insight**: Always normalize currency codes to match API response format. Check actual API responses to understand the format used.

**Testing**:
- Created `test_zusd_usd_normalization.py` (8 tests)
- Updated `test_dashboard_balances.py` to use ZUSD
- All 354 tests passing

**Related Files**:
- `dashboard.py`: Lines 561-594 (_extract_quote_asset)
- `tests/test_zusd_usd_normalization.py`: Comprehensive test suite
- `tests/test_dashboard_balances.py`: Updated existing tests

---

```

---

## Insufficient Gap Validation Change (2025-10-27)

**Issue**: Validator blocked orders when gap between threshold and current price was less than trailing offset. Users couldn't transact even though they wanted to.

**Examples from Issue**:
- DYDXUSD: Gap 0.96% < trailing 2.00% → Blocked
- PONKEUSD: Gap 1.11% < trailing 2.00% → Blocked  
- ATHUSD: Gap 1.97% < trailing 2.00% → Blocked

**Root Cause**: Validation was too strict, assuming insufficient gap was always wrong. But users might WANT to trigger orders immediately.

**Solution**: Changed insufficient gap from ERROR to WARNING
- Gap < trailing_offset: Now WARNING (was ERROR)
- Allows transactions while still alerting user
- Added actionable suggestions in warning message

**Code Changes**:
1. `validator.py` line 437-443: Changed from conditional ERROR/WARNING to always WARNING
2. Added helpful suggestions: "(1) increase threshold price, (2) reduce trailing offset, or (3) wait for price to move away"
3. Updated 3 existing tests to expect WARNING instead of ERROR
4. Added 3 comprehensive tests in `test_insufficient_gap_fix.py`

**Warning Levels** (unchanged):
- Gap < trailing_offset: "Insufficient gap" WARNING
- Gap >= trailing_offset and < 2×trailing_offset: "Small gap" WARNING  
- Gap >= 2×trailing_offset: No warning

**Key Insights**:
1. **User Intent Matters**: Validation should warn but not block when user wants immediate execution
2. **Actionable Warnings**: Include suggestions on how to fix issues
3. **Minimal Changes**: Simple change from ERROR to WARNING solves the problem
4. **Debug Mode**: Already had mechanism for this (debug_mode), just needed to apply it to normal mode too

**Testing**:
- 3 new tests covering exact examples from issue
- All existing tests updated and passing
- 448 total tests passing

**Related Files**:
- `validator.py`: Lines 437-443 (fix)
- `tests/test_insufficient_gap_fix.py`: New comprehensive tests
- `tests/test_debug_mode_validation.py`: Updated tests
- `tests/test_ttslo.py`: Updated test_config_validator

**User Impact**: Users can now transact with small gaps (with warnings) instead of being completely blocked.

---
