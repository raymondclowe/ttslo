# State.csv Reconciliation Tool

## Problem
Issue #88: State.csv file may not update if there is an exception when creating orders. This leads to orders being incorrectly marked as 'manual' when they were actually created by ttslo.py.

## Solution
This tool reconciles state.csv with:
1. Actual open orders from Kraken API
2. Order creation history from logs.csv

## Files

### 1. `reconcile_state.py` (Production Script)
Main reconciliation tool that can be run on production to fix state.csv.

**Usage:**
```bash
# Dry run (shows what would be changed without making changes):
python3 reconcile_state.py --dry-run

# Apply changes to production state.csv:
python3 reconcile_state.py

# Use custom file locations:
python3 reconcile_state.py --state-file /path/to/state.csv --logs-file /path/to/logs.csv
```

**Features:**
- Fetches current open orders from Kraken
- Parses logs.csv to find orders created by ttslo.py
- Identifies missing or incorrect state entries
- Creates backups before modifying state.csv
- Supports dry-run mode for safety

### 2. `state_fix.csv` (Manual Fix Data)
Pre-generated state entries for the 3 orders that need fixing based on current production data.

**Orders identified:**
- `near_usd_sell_29` - Order: OIZXVF-N5TQ5-DHTPIR
- `dydx_usd_sell_19` - Order: O2VLNP-DNSKF-LAFIJP
- `eth_usd_sell_3` - Order: OGMFI4-MABOV-YGJDWI

### 3. `state_fix_summary.txt`
Human-readable summary of the issues found and what needs to be fixed.

## Validation Results

### Current Kraken Open Orders (3 orders):
1. **OIZXVF-N5TQ5-DHTPIR** (NEARUSD, sell, trailing-stop)
2. **O2VLNP-DNSKF-LAFIJP** (DYDXUSD, sell, trailing-stop)
3. **OGMFI4-MABOV-YGJDWI** (ETHUSD, sell, trailing-stop)

### Evidence from logs.csv:
All 3 orders were created by ttslo.py:
- Created on 2025-10-24 between 04:33 and 05:15 UTC
- Each has a corresponding "TSL order created successfully" log entry
- Config IDs: eth_usd_sell_3, dydx_usd_sell_19, near_usd_sell_29

### Conclusion:
✓ **VALIDATED**: All 3 open orders were created by ttslo.py (not manual)
✓ These should be properly tracked in state.csv with triggered=true

## How to Apply the Fix

### Option 1: Automatic (Recommended)
```bash
# Review what will change (dry-run)
python3 reconcile_state.py --dry-run

# Apply the fix
python3 reconcile_state.py
```

### Option 2: Manual
1. Review `state_fix.csv`
2. Add/update the 3 entries in your production state.csv
3. Ensure each entry has:
   - triggered=true
   - correct order_id
   - trigger_time
   - trigger_price
   - offset (trailing offset percentage)

## Safety Features
- Automatic backup created before any changes (state.csv.backup.TIMESTAMP)
- Dry-run mode to preview changes
- Read-only Kraken API access
- No order modifications (only state tracking)

## Future Prevention
The reconcile_state.py tool can be run periodically (e.g., daily via cron) to ensure state.csv stays synchronized with Kraken orders, preventing this issue from recurring.

Suggested cron entry:
```cron
# Run state reconciliation daily at 3 AM
0 3 * * * cd /path/to/ttslo && python3 reconcile_state.py >> reconcile.log 2>&1
```
