# Fix: Balance Checking for USD Pairs

## Issue Summary

A DYDXUSD sell order was failing with:
```
⚠️ TTSLO: Cannot create order - Insufficient balance!

Config: dydx_usd_sell_19
Pair: DYDXUSD
Direction: sell
Required Volume: 18.4712445
Available Balance: unknown
Trigger Price: 0.3266
```

The Kraken web interface showed sufficient DYDX balance, but the system reported "Available Balance: unknown".

## Root Causes

### 1. Credential Discovery Issue

**Problem**: The GitHub Copilot agent sets credentials as:
- `COPILOT_KRAKEN_API_KEY`
- `COPILOT_KRAKEN_API_SECRET`

But `creds.py` was only checking for the lowercase prefix:
- `copilot_KRAKEN_API_KEY`

**Result**: Credentials were not found, so balance API calls failed.

### 2. USD Pair Suffix Not Supported

**Problem**: The `_extract_base_asset()` method only checked for these quote currency suffixes:
- USDT, ZUSD, ZEUR, EUR, ZGBP, GBP, ZJPY, JPY

It didn't check for plain 'USD', so pairs like:
- DYDXUSD
- ATOMUSD
- SOLUSD

Could not have their base asset extracted.

**Result**: Base asset extraction returned empty string, balance lookup failed completely.

## Fixes Applied

### Fix 1: Support Uppercase COPILOT_ Prefix

Updated `creds.py::get_env_var()` to check in this order:
1. Exact environment variable name
2. `COPILOT_` prefix (uppercase) - **NEW**
3. `copilot_` prefix (lowercase) - existing
4. `COPILOT_W_*` mappings - existing

```python
def get_env_var(name: str) -> Optional[str]:
    # ... exact match ...
    
    # Try uppercase COPILOT_ prefix (GitHub Copilot agent style)
    copilot_upper_name = f"COPILOT_{name}"
    val = os.environ.get(copilot_upper_name)
    if val:
        return val
    
    # Try lowercase copilot_ prefix (legacy style)
    # ...
```

### Fix 2: Add USD to Quote Currency Suffixes

Updated `ttslo.py::_extract_base_asset()` to include 'USD':

```python
# Note: Order matters - check longer suffixes first (e.g., USDT before USD)
for quote in ['USDT', 'ZUSD', 'ZEUR', 'EUR', 'ZGBP', 'GBP', 'ZJPY', 'JPY', 'USD']:
    if pair.endswith(quote):
        base = pair[:-len(quote)]
        if base:
            return base
```

**Why order matters**: We check USDT before USD to ensure the most specific match. For example, if a pair theoretically ended in "USDT", we want to match the full "USDT" suffix (4 chars) rather than just "USD" (3 chars).

## Verification

### Test 1: Credential Discovery

```bash
$ python3 tools/test_balance_copilot.py
```

**Result**: ✓ Credentials found and balance API works
- Found 27 asset entries
- DYDX balance: 123.16 (123.16 in DYDX.F funding wallet)

### Test 2: DYDX Balance Check

```bash
$ python3 tools/test_dydx_balance.py
```

**Result**: ✓ Balance check for DYDXUSD works correctly
- Extracted base asset: DYDX
- Normalized balance keys: DYDX and DYDX.F both normalize to DYDX
- Total available: 123.16 (0.00 + 123.16)
- Required: 18.47
- Status: SUFFICIENT ✓

### Test 3: Unit Tests

```bash
$ python3 tests/test_balance_fix.py
```

**Result**: All 3 tests pass
- ✓ COPILOT credentials discovery
- ✓ USD pair extraction (DYDXUSD, ATOMUSD, SOLUSD, etc.)
- ✓ Balance normalization and summing

## Files Changed

1. **creds.py**: Added uppercase COPILOT_ prefix support
2. **ttslo.py**: Added 'USD' to quote currency suffixes
3. **tools/test_balance_copilot.py**: Test tool for credential verification
4. **tools/test_dydx_balance.py**: Test tool for DYDXUSD balance checking
5. **tests/test_balance_fix.py**: Unit tests for the fixes
6. **LEARNINGS.md**: Documentation of the issue and fix

## Expected Behavior After Fix

When a DYDXUSD sell order is triggered:

1. System finds `COPILOT_KRAKEN_API_KEY` credentials ✓
2. System extracts base asset "DYDX" from "DYDXUSD" ✓
3. System normalizes "DYDX" and "DYDX.F" to "DYDX" ✓
4. System sums balances: 0.00 + 123.16 = 123.16 ✓
5. System checks: 123.16 >= 18.47 = SUFFICIENT ✓
6. System creates TSL order successfully ✓

Instead of the previous error:
```
Available Balance: unknown
```

The system will now show:
```
Available Balance: 123.16
```

## Notes

- The fix preserves all existing functionality
- All existing tests continue to pass
- The fix is minimal and surgical
- Balance checking now properly aggregates spot and funding wallet balances for all assets
