# LEARNINGS

Key learnings and gotchas discovered during TTSLO development.

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

*Add new learnings here as we discover them*

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

## Copilot Credential Discovery Fix (2025-10-24)

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
    # ... calculate quote currency ...

# AFTER (correct)
elif direction == 'buy':
    # Buying base asset - need quote currency balance (not base asset)
    # Track the pair for the base asset but don't require base asset balance
    assets_needed[base_asset]['pairs'].add(pair)  # ✅ Only track pair
    # ... calculate quote currency ... (unchanged)
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

```
