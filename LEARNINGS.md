# LEARNINGS

Key learnings and gotchas discovered during TTSLO development.

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

*Add new learnings here as we discover them*
