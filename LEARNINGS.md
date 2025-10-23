# LEARNINGS

Key learnings and gotchas discovered during TTSLO development.

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

*Add new learnings here as we discover them*

