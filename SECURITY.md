# Security and Safety Guarantees

## Overview

TTSLO is designed with a **fail-safe** approach to order handling. The system prioritizes safety over liveness, meaning:

- **NO ORDER** is always better than a **WRONG ORDER**
- The system will refuse to create orders if anything is uncertain or abnormal
- All validation errors prevent order creation
- All exceptions prevent order creation

## Core Safety Principles

### 1. Explicit Validation

Every parameter is explicitly validated before any order is created:

- **Configuration parameters** must be present and valid
- **Prices** must be positive numbers
- **API credentials** must be available
- **Threshold conditions** must be correctly configured

### 2. Fail-Safe Defaults

The system defaults to the safest behavior:

- Missing data → **NO ORDER**
- Invalid data → **NO ORDER**
- API errors → **NO ORDER**
- Exceptions → **NO ORDER**
- Uncertain conditions → **NO ORDER**

### 3. No Silent Failures

All errors are logged and visible:

- Parameter validation failures are logged with details
- API errors are logged with error messages
- Exceptions are caught and logged
- State changes are tracked in logs

## Order Creation Safety

### Order Creation Will NEVER Happen If:

1. **Configuration Issues:**
   - Config ID is missing or invalid
   - Trading pair is missing or invalid
   - Direction is missing or not 'buy'/'sell'
   - Volume is missing, negative, or invalid
   - Trailing offset is missing, negative, zero, or invalid

2. **Price Issues:**
   - Current price is unavailable
   - Current price is invalid (not a number, negative, or zero)
   - Trigger price is invalid
   - Threshold price is invalid

3. **API Issues:**
   - Read-write API credentials are not available
   - API call raises an exception
   - API returns an error
   - API response is invalid or missing order ID

4. **System Issues:**
   - Configuration file cannot be loaded
   - Configuration validation fails
   - Any unexpected exception occurs

5. **State Issues:**
   - Configuration is disabled
   - Configuration has already been triggered
   - Threshold condition is not met

## Code Review Guidelines

The code has been refactored for **beginner-level readability**:

### Simple, Linear Code

- All functions use clear step-by-step logic
- Each step is numbered and commented
- Complex operations are broken into small steps
- No advanced Python idioms or syntax

### Explicit Checking

Every check follows this pattern:

```python
# Step X: Validate parameter
if not parameter:
    # SAFETY: Explain why we return/fail
    log_error("Descriptive message")
    return None  # or False
```

### Example: Order Creation Flow

```python
def create_tsl_order(self, config, trigger_price):
    # Step 1: Check config_id exists
    if not config_id:
        return None  # NO ORDER
    
    # Step 2: Check pair exists
    if not pair:
        return None  # NO ORDER
    
    # Step 3: Check direction exists
    if not direction:
        return None  # NO ORDER
    
    # ... (15 total validation steps)
    
    # Only create order if ALL steps pass
    return order_id
```

## Testing Safety Guarantees

The test suite includes comprehensive safety tests:

### Test Categories

1. **Parameter Validation Tests**
   - Missing parameters
   - Invalid types
   - Out-of-range values
   - Malformed data

2. **Exception Handling Tests**
   - API exceptions
   - Parsing errors
   - Network failures

3. **Edge Case Tests**
   - Zero values
   - Negative values
   - None/null values
   - Empty strings

### Running Safety Tests

```bash
python test_ttslo.py
```

All tests must pass before any code changes are deployed.

## Configuration Validation

Before any monitoring begins, all configurations are validated:

### Pre-Flight Checks

1. **Syntax validation**: All required fields present and correct format
2. **Logic validation**: No contradictory or unusual settings
3. **Market validation**: Threshold vs. current price checks
4. **Gap validation**: Ensure sufficient gap for trailing offset

### Validation Failures

If validation fails:
- System will NOT start
- All errors are displayed
- Exit code 1 is returned
- No orders can be created

## Dry-Run Mode

For testing without real orders:

```bash
python ttslo.py --dry-run --verbose
```

In dry-run mode:
- All validation is performed
- Thresholds are checked
- NO real orders are created
- Dummy order IDs are returned for testing

## Monitoring and Logging

All operations are logged to `logs.csv`:

- **DEBUG**: Detailed operation information
- **INFO**: Normal operations (price checks, order creation)
- **WARNING**: Unusual but non-fatal conditions
- **ERROR**: Validation failures, API errors, exceptions

### Critical Events Logged

- Every order creation attempt (success or failure)
- Every validation failure
- Every API error
- Every exception caught

## Credential Safety

### Read-Only Credentials (Required)

- Used for price monitoring only
- Cannot create or modify orders
- Lower risk if compromised

### Read-Write Credentials (Optional)

- Only used for order creation
- Can be omitted to run in monitoring-only mode
- Should have minimal permissions (only "Create & Modify Orders")

### Credential Validation

The system validates credentials before operation:

```bash
# Step 1: Check read-only credentials exist
if not api_key_ro or not api_secret_ro:
    exit(1)  # FAIL SAFE - do not proceed

# Step 2: Check read-write credentials if not dry-run
if not dry_run and not has_rw_creds:
    warn("Orders cannot be created")
```

## Recovery from Failures

### Graceful Degradation

- One bad configuration does NOT crash the system
- API errors do NOT crash the system
- Network issues do NOT crash the system
- System continues monitoring other configurations

### State Preservation

- State is saved after each iteration
- Already-triggered configs are never re-triggered
- State file prevents duplicate orders

### Manual Intervention

All order creation can be reviewed:

1. Check `logs.csv` for order creation events
2. Check `state.csv` for triggered configurations
3. Verify orders in Kraken interface
4. Disable configurations by setting `enabled=false`

## Security Review Checklist

For any code changes, verify:

- [ ] All parameters are explicitly validated
- [ ] Invalid inputs result in no order
- [ ] Exceptions are caught and logged
- [ ] Errors prevent order creation
- [ ] Code is simple and readable
- [ ] Each step has a comment
- [ ] Safety notes are present
- [ ] Tests cover the change
- [ ] All tests pass

## Known Limitations

### Not Guaranteed

- **Network reliability**: Orders may fail due to network issues
- **API availability**: Kraken API must be operational
- **Timing precision**: Prices may change between check and order
- **Market conditions**: Orders may execute at unexpected prices

### User Responsibility

Users must:
- Understand trailing stop loss mechanics
- Test thoroughly in dry-run mode
- Start with small volumes
- Monitor the system regularly
- Have backup plans if the system fails
- Understand cryptocurrency trading risks

## Contact

For security concerns or questions:
- Open an issue on GitHub
- Include detailed description
- Do NOT include credentials or sensitive data

## Version

This document describes safety guarantees as of the current version. Future versions may add additional safety features.
