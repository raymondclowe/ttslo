# Multi-Account Support Specification

## Overview
Add support for managing two Kraken accounts (Raymond and Winnie) within a single TTSLO instance.

## Design Goals
- Single process, single config.csv
- Minimal code changes (~150 lines)
- Simple configuration: one column to specify account
- Backward compatible (defaults to Raymond's account)

## Account Naming
- **Raymond**: Primary/default account
- **Winnie**: Secondary account

## Configuration Changes

### 1. Environment Variables

Add 4 new environment variables for Winnie's account:

```bash
# Raymond's Account (Primary/Default) - EXISTING
KRAKEN_API_KEY=xxx
KRAKEN_API_SECRET=xxx
KRAKEN_API_KEY_RW=xxx
KRAKEN_API_SECRET_RW=xxx

# Winnie's Account (Secondary) - NEW
KRAKEN_API_KEY_WINNIE=xxx
KRAKEN_API_SECRET_WINNIE=xxx
KRAKEN_API_KEY_RW_WINNIE=xxx
KRAKEN_API_SECRET_RW_WINNIE=xxx
```

**Alternative naming also supported:**
```bash
KRAKEN_API_KEY_RAYMOND=xxx      # Explicit Raymond naming (optional)
KRAKEN_API_SECRET_RAYMOND=xxx
KRAKEN_API_KEY_RW_RAYMOND=xxx
KRAKEN_API_SECRET_RW_RAYMOND=xxx
```

### 2. config.csv Schema

Add new column: `account`

**Column Definition:**
- **Name:** `account`
- **Type:** String
- **Values:** `raymond` (default) or `winnie`
- **Default:** If missing or empty, defaults to `raymond`
- **Case-insensitive:** `Raymond`, `RAYMOND`, `raymond` all valid
- **Position:** After `trailing_offset_percent`, before any optional columns

**Example config.csv:**
```csv
id,enabled,pair,threshold_type,threshold_price,direction,volume,trailing_offset_percent,account,notes
btc_r_sell,true,XXBTZUSD,above,95000,sell,0.01,2.0,raymond,Raymond's BTC sale
eth_w_sell,true,XETHZUSD,above,3500,sell,0.1,2.0,winnie,Winnie's ETH sale
sol_r_buy,true,SOLUSDT,below,150,buy,5.0,3.0,raymond,Raymond's SOL buy
ada_w_buy,true,ADAUSDT,below,0.50,buy,1000,2.5,winnie,Winnie's ADA buy
default_test,true,DOTUSDT,above,8.0,sell,10,2.0,,Defaults to Raymond
```

### 3. state.csv Schema

**No changes required** - state.csv already has config_id which links to config.csv

Account information is implicit through the config_id relationship.

### 4. logs.csv Schema

**Optional enhancement:** Add `account` column to logs for easier filtering

**Column Definition:**
- **Name:** `account`
- **Type:** String
- **Values:** `raymond` or `winnie`
- **Source:** Derived from config at log time

## Code Changes

### 1. creds.py

**Modify `find_kraken_credentials()` function:**

```python
def find_kraken_credentials(readwrite: bool = False, account: str = 'raymond', env_file: str = '.env') -> Tuple[Optional[str], Optional[str]]:
    """
    Find Kraken credentials for specified account.
    
    Args:
        readwrite: If True, look for read-write keys
        account: Account name ('raymond' or 'winnie'), defaults to 'raymond'
        env_file: Path to .env file
        
    Returns:
        (key, secret) or (None, None) if not found
    """
    load_env(env_file)
    
    account_lower = account.lower().strip()
    
    # Normalize account name
    if account_lower not in ('raymond', 'winnie'):
        account_lower = 'raymond'  # Default to raymond for unknown accounts
    
    # Build environment variable names
    if account_lower == 'raymond':
        # For Raymond, support both explicit and default naming
        if readwrite:
            key = get_env_var('KRAKEN_API_KEY_RW_RAYMOND') or get_env_var('KRAKEN_API_KEY_RW')
            secret = get_env_var('KRAKEN_API_SECRET_RW_RAYMOND') or get_env_var('KRAKEN_API_SECRET_RW')
        else:
            key = get_env_var('KRAKEN_API_KEY_RAYMOND') or get_env_var('KRAKEN_API_KEY')
            secret = get_env_var('KRAKEN_API_SECRET_RAYMOND') or get_env_var('KRAKEN_API_SECRET')
    else:  # winnie
        # For Winnie, use explicit naming only
        if readwrite:
            key = get_env_var('KRAKEN_API_KEY_RW_WINNIE')
            secret = get_env_var('KRAKEN_API_SECRET_RW_WINNIE')
        else:
            key = get_env_var('KRAKEN_API_KEY_WINNIE')
            secret = get_env_var('KRAKEN_API_SECRET_WINNIE')
    
    return key, secret
```

### 2. config.py

**Modify `load_config()` to handle account column:**

- Add 'account' to expected columns
- Default to 'raymond' if missing or empty
- Normalize to lowercase
- Validate account name is 'raymond' or 'winnie'

**Modify `create_sample_config()` to include account column example**

### 3. ttslo.py

**3.1 Modify `__init__()` signature:**

```python
def __init__(self, config_manager, 
             kraken_api_readonly, kraken_api_readwrite=None,
             kraken_api_readonly_winnie=None, kraken_api_readwrite_winnie=None,
             dry_run=False, verbose=False, debug=False, 
             notification_manager=None, profit_tracker=None):
    """
    Initialize TTSLO application.
    
    Args:
        config_manager: ConfigManager instance
        kraken_api_readonly: KrakenAPI instance for Raymond (read-only)
        kraken_api_readwrite: KrakenAPI instance for Raymond (read-write)
        kraken_api_readonly_winnie: KrakenAPI instance for Winnie (read-only)
        kraken_api_readwrite_winnie: KrakenAPI instance for Winnie (read-write)
        dry_run: If True, don't actually create orders
        verbose: If True, print verbose output
        debug: If True, enable debug mode
        notification_manager: NotificationManager instance (optional)
        profit_tracker: ProfitTracker instance (optional)
    """
    self.config_manager = config_manager
    
    # Raymond's APIs (default/primary)
    self.kraken_api_readonly = kraken_api_readonly
    self.kraken_api_readwrite = kraken_api_readwrite
    
    # Winnie's APIs (secondary)
    self.kraken_api_readonly_winnie = kraken_api_readonly_winnie
    self.kraken_api_readwrite_winnie = kraken_api_readwrite_winnie
    
    # ... rest of initialization
```

**3.2 Add helper method `_get_api_for_config()`:**

```python
def _get_api_for_config(self, config, readwrite=False):
    """
    Get appropriate API instance based on config's account.
    
    Args:
        config: Configuration dictionary
        readwrite: If True, return read-write API, else read-only API
        
    Returns:
        KrakenAPI instance or None if not available
    """
    account = config.get('account', 'raymond').lower().strip()
    
    # Default to raymond for unknown accounts
    if account not in ('raymond', 'winnie'):
        account = 'raymond'
    
    if account == 'winnie':
        return self.kraken_api_readwrite_winnie if readwrite else self.kraken_api_readonly_winnie
    else:  # raymond
        return self.kraken_api_readwrite if readwrite else self.kraken_api_readonly
```

**3.3 Update methods to use account-specific APIs:**

Methods to modify:
- `process_config()` - use `_get_api_for_config()` for price fetching
- `create_tsl_order()` - use `_get_api_for_config(config, readwrite=True)` for order creation
- `check_sufficient_balance()` - add config parameter, use account-specific API
- `check_order_filled()` - add config parameter or extract from state
- `log()` - optionally add account parameter for logging

**3.4 Update `main()` function:**

```python
def main():
    # ... argument parsing ...
    
    # Load environment
    load_env_file(args.env_file)
    
    # Get Raymond's credentials (primary/default)
    api_key_ro_raymond, api_secret_ro_raymond = find_kraken_credentials(
        readwrite=False, account='raymond', env_file=args.env_file
    )
    api_key_rw_raymond, api_secret_rw_raymond = find_kraken_credentials(
        readwrite=True, account='raymond', env_file=args.env_file
    )
    
    # Get Winnie's credentials (secondary)
    api_key_ro_winnie, api_secret_ro_winnie = find_kraken_credentials(
        readwrite=False, account='winnie', env_file=args.env_file
    )
    api_key_rw_winnie, api_secret_rw_winnie = find_kraken_credentials(
        readwrite=True, account='winnie', env_file=args.env_file
    )
    
    # Validate Raymond's read-only credentials are present (required)
    if not api_key_ro_raymond or not api_secret_ro_raymond:
        print("ERROR: Raymond's read-only API credentials are required.", file=sys.stderr)
        print("Set KRAKEN_API_KEY and KRAKEN_API_SECRET.", file=sys.stderr)
        sys.exit(1)
    
    # Create Raymond's API instances
    kraken_api_readonly_raymond = KrakenAPI(api_key_ro_raymond, api_secret_ro_raymond)
    kraken_api_readwrite_raymond = None
    if api_key_rw_raymond and api_secret_rw_raymond:
        kraken_api_readwrite_raymond = KrakenAPI(api_key_rw_raymond, api_secret_rw_raymond)
    
    # Create Winnie's API instances (optional)
    kraken_api_readonly_winnie = None
    kraken_api_readwrite_winnie = None
    if api_key_ro_winnie and api_secret_ro_winnie:
        kraken_api_readonly_winnie = KrakenAPI(api_key_ro_winnie, api_secret_ro_winnie)
        if api_key_rw_winnie and api_secret_rw_winnie:
            kraken_api_readwrite_winnie = KrakenAPI(api_key_rw_winnie, api_secret_rw_winnie)
    
    # Initialize TTSLO with all APIs
    ttslo = TTSLO(
        config_manager,
        kraken_api_readonly_raymond,
        kraken_api_readwrite_raymond,
        kraken_api_readonly_winnie,
        kraken_api_readwrite_winnie,
        dry_run=args.dry_run,
        verbose=args.verbose,
        debug=args.debug,
        notification_manager=notification_manager,
        profit_tracker=profit_tracker
    )
    
    # ... rest of main ...
```

### 4. dashboard.py

**4.1 Update cached data functions:**

- `get_cached_config()` - no changes needed (already returns full config)
- Display account name in dashboard UI for each order

**4.2 Update templates:**

- Show account name in pending orders table
- Show account name in active orders table
- Show account name in completed orders table

### 5. validator.py

**Add validation for account column:**

- Validate account is 'raymond' or 'winnie' (case-insensitive)
- Warn if account column missing (will default to raymond)
- Error if account specified but no credentials available

### 6. csv_editor.py

**Add account column to editor:**

- Include in column definitions
- Add to smart defaults (default to 'raymond')
- Add validation for valid values

## Validation Rules

### Configuration Validation

1. **Account column missing:** Warning, defaults to 'raymond'
2. **Account column empty:** Info, defaults to 'raymond'
3. **Account value invalid:** Error, must be 'raymond' or 'winnie'
4. **Account 'winnie' but no credentials:** Error, cannot process config
5. **Account case variations:** Normalized to lowercase, no error

### Runtime Validation

1. **Missing API credentials for account:** 
   - Read-only: Error, skip config
   - Read-write: Warning, monitoring only (no orders)

2. **Config specifies winnie but winnie APIs not initialized:**
   - Error logged
   - Config skipped
   - No order created

## Backward Compatibility

### Existing Configurations

Configs without `account` column will:
1. Default to 'raymond'
2. Use existing KRAKEN_API_KEY/KRAKEN_API_SECRET credentials
3. Work exactly as before

### Credential Migration

Existing credentials remain unchanged:
```bash
# Before (still works):
KRAKEN_API_KEY=xxx
KRAKEN_API_SECRET=xxx

# After (backward compatible):
KRAKEN_API_KEY=xxx              # Used for Raymond
KRAKEN_API_SECRET=xxx           # Used for Raymond
KRAKEN_API_KEY_WINNIE=yyy       # New for Winnie
KRAKEN_API_SECRET_WINNIE=yyy    # New for Winnie
```

## Error Handling

### Missing Credentials

**Scenario:** Config specifies 'winnie' but Winnie's credentials not set

**Behavior:**
- Log error: "Cannot process config {config_id}: Winnie's API credentials not available"
- Skip config during processing
- Do NOT create any orders
- Send notification if notification_manager available

### API Errors

**Scenario:** API call fails for specific account

**Behavior:**
- Log error with account name
- Send notification specifying which account failed
- Continue processing other configs
- Retry next iteration

### Invalid Account Name

**Scenario:** Config has account='bob'

**Behavior:**
- Validation error during config load
- Config disabled automatically
- User notified to fix config
- Defaults to 'raymond' if validation skipped

## Testing Requirements

### Unit Tests

1. **creds.py:**
   - Test finding Raymond's credentials (default and explicit)
   - Test finding Winnie's credentials
   - Test fallback to Raymond for invalid account names
   - Test missing credentials return None

2. **config.py:**
   - Test loading config with account column
   - Test loading config without account column (defaults to raymond)
   - Test account normalization (case-insensitive)
   - Test invalid account values

3. **ttslo.py:**
   - Test `_get_api_for_config()` returns correct API
   - Test process_config() uses correct account API
   - Test create_tsl_order() uses correct account API
   - Test error handling when account API not available

### Integration Tests

1. **Multi-account monitoring:**
   - Create configs for both Raymond and Winnie
   - Verify correct APIs used for each
   - Verify orders created on correct accounts

2. **Backward compatibility:**
   - Test config without account column
   - Verify defaults to Raymond
   - Verify works with existing credentials

3. **Error scenarios:**
   - Config specifies Winnie but no credentials
   - API error on Raymond's account only
   - API error on Winnie's account only

## Documentation Updates

### README.md

Add section on multi-account support:
- How to configure multiple accounts
- Environment variable naming
- config.csv account column

### AGENTS.md

Add notes about:
- Multi-account credential lookup
- Account-specific API routing
- Testing with multiple accounts

## Rollout Plan

### Phase 1: Core Implementation
1. Implement creds.py changes
2. Implement config.py changes
3. Implement ttslo.py changes
4. Add basic tests

### Phase 2: UI/Dashboard
1. Update dashboard.py
2. Update templates
3. Update csv_editor.py

### Phase 3: Validation & Testing
1. Add validation rules
2. Complete test coverage
3. Integration testing with test accounts

### Phase 4: Documentation
1. Update README.md
2. Update setup documentation
3. Create migration guide

## Security Considerations

1. **Credential Isolation:** Each account's credentials completely isolated
2. **Order Routing:** Orders can only be created on correct account
3. **Balance Checks:** Balance checked on correct account before order creation
4. **No Cross-Account Operations:** No operations can affect wrong account

## Performance Impact

- **Minimal:** 4 API instances instead of 2 (~5MB more memory)
- **Price Fetching:** Batch operations still work per-account
- **No Additional API Calls:** Same number of calls, just routed differently

## Success Criteria

1. ✅ Can configure Raymond and Winnie accounts separately
2. ✅ Orders created on correct account
3. ✅ Balance checked on correct account
4. ✅ Dashboard shows which account for each order
5. ✅ Backward compatible with existing configs
6. ✅ Clear error messages when credentials missing
7. ✅ All tests pass
8. ✅ Documentation complete
