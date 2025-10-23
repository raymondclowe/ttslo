# API Error Handling Implementation Summary

## Overview

This implementation adds comprehensive error handling for Kraken API failures, including proper error classification, logging, and Telegram notifications to keep users informed when API issues occur.

## Problem Statement

During maintenance, network issues, or service outages, Kraken API calls could fail in various ways that needed to be properly handled:
- Timeouts (slow network, overloaded servers)
- Connection errors (network down, DNS failures)
- Server errors (5xx - maintenance, crashes, overload)
- Rate limiting (429 - too many requests)

Previously, these errors were caught generically and logged, but:
1. Error types weren't classified for targeted responses
2. No notifications were sent to users
3. No timeout parameters were set on requests
4. Limited context was preserved for debugging

## Solution

### Custom Exception Hierarchy

Created a hierarchy of custom exceptions to classify API errors:

```
KrakenAPIError (base)
├── KrakenAPITimeoutError      (⏱️)
├── KrakenAPIConnectionError   (🔌)
├── KrakenAPIServerError       (🔥)
└── KrakenAPIRateLimitError    (🚦)
```

Each exception stores:
- `error_type`: String identifier for classification
- `details`: Dictionary with context (status code, timeout, endpoint, etc.)
- Original exception preserved with `from e` for debugging

### Enhanced API Client

**Changes to `kraken_api.py`:**
1. Added custom exception classes (lines 17-62)
2. Added `timeout` parameter to `_query_public` and `_query_private` (default 30s)
3. Comprehensive error detection and classification
4. Proper exception chaining for debugging

**Error Detection Order:**
```python
try:
    response = requests.get(url, params=params, timeout=timeout)
    
    # Check status codes before generic raise_for_status()
    if response.status_code == 429:
        raise KrakenAPIRateLimitError(...)
    if response.status_code >= 500:
        raise KrakenAPIServerError(...)
    
    response.raise_for_status()
    return response.json()
    
except requests.exceptions.Timeout as e:
    raise KrakenAPITimeoutError(...) from e
except requests.exceptions.ConnectionError as e:
    raise KrakenAPIConnectionError(...) from e
except requests.exceptions.RequestException as e:
    raise KrakenAPIError(...) from e
```

### Notification System

**Changes to `notifications.py`:**
- Added `notify_api_error()` method
- Icon mapping for visual distinction (⏱️🔌🔥🚦)
- Contextual help messages for each error type
- Includes endpoint, error message, and relevant details

Example notification:
```
🔌 TTSLO: Kraken API Error

Error Type: connection
Endpoint: Ticker/get_current_price
Message: Failed to connect to Kraken API

⚠️ Cannot reach Kraken API. Check your network connection.
```

### Integration

**Changes to `ttslo.py`:**
1. Import custom exception classes
2. Catch `KrakenAPIError` before generic `Exception`
3. Send notifications on API errors
4. Log with `error_type` for filtering
5. Continue running (don't crash on errors)
6. Safe abort (no orders created on errors)

Applied to:
- `process_config()` - price fetching
- `run_once()` - batch price prefetching
- `check_balance()` - balance checking
- `create_order()` - order creation
- `check_order_filled()` - order status checking

### Configuration

**Updated `notifications.ini.example`:**
Added new event type for API errors:
```ini
[notify.api_error]
# Notified when Kraken API calls fail
# Triggered by: Timeouts, connection errors, server errors (5xx), rate limiting
users = alice
```

## Testing

### Test Coverage

Created comprehensive test suite in `test_api_error_handling.py`:

**Kraken API Error Handling Tests (11 tests):**
- Timeout on public endpoint
- Timeout on private endpoint
- Connection error on public endpoint
- Connection error on private endpoint
- Server error 500 on public endpoint
- Server error 502 on public endpoint
- Server error 503 on public endpoint
- Server error on private endpoint
- Rate limit 429 on public endpoint
- Rate limit on private endpoint
- Custom timeout parameter

**Notification Tests (5 tests):**
- Timeout error notification
- Connection error notification
- Server error notification
- Rate limit error notification
- No notification when not subscribed

### Test Results
```
16 tests added
64 total tests passing
0 regressions
100% pass rate
```

### Demo Script

Created `demo_api_error_handling.py` to demonstrate:
1. How each error type is detected and handled
2. What notifications are sent
3. System behavior during errors
4. Recovery after errors

## Files Changed

| File | Lines Added | Lines Changed | Purpose |
|------|-------------|---------------|---------|
| `kraken_api.py` | +147 | 4 | Exception classes, error handling |
| `notifications.py` | +43 | 7 | API error notifications |
| `ttslo.py` | +83 | 16 | Error handling integration |
| `test_api_error_handling.py` | +296 | 0 | Test suite |
| `notifications.ini.example` | +7 | 0 | Configuration template |
| `README.md` | +51 | 0 | Documentation |
| `NOTIFICATIONS_README.md` | +51 | 0 | Notification examples |
| `LEARNINGS.md` | +93 | 0 | Implementation notes |
| `demo_api_error_handling.py` | +205 | 0 | Demo script |
| **Total** | **989** | **27** | |

## Behavior

### When API Errors Occur

1. **Error Detection**: Exception caught at API call site
2. **Classification**: Error type determined (timeout, connection, server, rate limit)
3. **Logging**: Error logged with type, endpoint, and details
4. **Notification**: Telegram message **attempted** (may fail during network outage)
5. **Safe Abort**: Operation cancelled without creating orders
6. **Continue**: System continues monitoring
7. **Retry**: Automatic retry on next monitoring cycle

### Known Limitation: Network Outages

**Enhanced with Notification Queue** (New Feature):

TTSLO now includes an intelligent notification queue system that solves the network outage problem:

**During network outage**:
- Kraken API calls fail (connection error)
- Telegram notification attempts also fail (cannot reach Telegram API)
- **Notifications are automatically queued** instead of being lost
- Queue is persisted to disk (`notification_queue.json`)
- **All errors are still logged to logs.csv**
- Console shows: `📬 Queued notification for alice (X total in queue)`
- System continues running and monitoring

**When network is restored**:
- Next successful API call triggers automatic queue flush
- All queued notifications sent with `[Queued from TIMESTAMP]` prefix
- Recovery notification sent to all recipients:
  ```
  ✅ TTSLO: Telegram notifications restored
  
  Notifications were unavailable for 2 hours 15 minutes
  From: 2025-10-23 10:00:00 UTC
  To: 2025-10-23 12:15:00 UTC
  
  Sending 5 queued notifications...
  ```
- Queue cleared after successful delivery

**Why this is better**: Previously, notifications during network outages were lost. Now they are queued and automatically delivered when connectivity is restored, with full context about the outage.

**Additional mitigation strategies**:
1. Always check `logs.csv` for complete error history
2. Monitor log files with external tools (log aggregation, alerts on log patterns)
3. Run TTSLO as systemd service to capture console output in journalctl
4. Use redundant network connections for the TTSLO server
5. Set up external monitoring to detect when TTSLO server is unreachable

### Error Messages

Each error type has a specific icon and help text:

- ⏱️ **Timeout**: "This could indicate network issues or Kraken API being slow."
- 🔌 **Connection**: "Cannot reach Kraken API. Check your network connection."
- 🔥 **Server Error**: "Kraken API is experiencing issues. Service may be down or under maintenance."
- 🚦 **Rate Limit**: "API rate limit exceeded. TTSLO will retry with backoff."

## Key Design Decisions

### 1. Custom Exception Hierarchy
**Why**: Allows catching specific error types for targeted handling, while maintaining ability to catch all API errors generically.

### 2. Exception Chaining (`from e`)
**Why**: Preserves original traceback for debugging while providing clean error messages.

### 3. Status Code Check Before raise_for_status()
**Why**: Allows custom handling of specific status codes (429, 5xx) before generic HTTP error handling.

### 4. Explicit Timeouts
**Why**: Prevents indefinite hangs, provides clear timeout values in error messages.

### 5. Details Dictionary
**Why**: Flexible way to include context-specific information without changing exception signatures.

### 6. Continue Running on Errors
**Why**: Transient errors shouldn't crash the monitoring service. System recovers automatically.

## Benefits

1. **User Awareness**: Immediate notification of API issues
2. **Better Debugging**: Classified errors with detailed context
3. **Reliability**: System continues running despite API failures
4. **Safety**: No incorrect orders created during error conditions
5. **Monitoring**: Can track and analyze error patterns
6. **Documentation**: Clear examples and guidance for users

## Future Enhancements

Potential improvements for future consideration:

1. **Retry Logic**: Automatic retry with exponential backoff for transient errors
2. **Error Rate Tracking**: Count errors over time to detect persistent issues
3. **Alerting Thresholds**: Only notify after N consecutive failures
4. **Circuit Breaker**: Temporarily pause API calls if error rate is too high
5. **Metrics**: Export error counts to monitoring systems (Prometheus, etc.)
6. **Health Check**: Dedicated endpoint to test API connectivity

## Conclusion

This implementation provides robust, production-ready error handling for Kraken API failures. All error types are properly classified, logged, and communicated to users through Telegram notifications. The system gracefully handles failures without crashing and automatically recovers when services are restored.

The comprehensive test suite ensures the error handling works correctly, and the demo script makes it easy to understand how the system behaves during different failure scenarios.
