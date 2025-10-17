# Validation Error Handling Fix

## Summary

This fix addresses the issue where validation errors on individual configuration lines would cause warnings but not prevent those invalid configurations from being processed during continuous operation.

## Problem

Previously, when the CSV configuration file was edited and reloaded during a continuous run:
1. If validation failed on an individual line, the system would log an error
2. The invalid configuration would still be processed potentially leading to execution attempts
3. No automatic mitigation was applied to prevent the problematic config from being used

## Solution

The fix implements automatic disabling of configurations with validation errors:

1. **Tracking**: The `ValidationResult` class now tracks which config IDs have errors using a `configs_with_errors` set
2. **Auto-disable**: When validation fails, configs with errors are automatically set to `enabled=false` in the CSV file
3. **Console output**: Clear error messages are displayed showing:
   - Which configs were disabled
   - What errors were found for each config
   - Instructions to fix and re-enable
4. **Dry-run protection**: In dry-run mode, the CSV file is NOT modified (validation errors are reported but configs remain unchanged)

## Changes Made

### validator.py
- Added `configs_with_errors` set to `ValidationResult` class to track which configs have errors
- Added `get_config_ids_with_errors()` method to retrieve the set of configs with errors
- Modified `add_error()` to automatically add config IDs to the tracking set

### config.py
- Added `disable_configs()` method to `ConfigManager` class
- This method updates the CSV file to set `enabled=false` for specified config IDs

### ttslo.py
- Modified `validate_and_load_config()` to:
  - Get the list of configs with errors after validation
  - Disable those configs in the CSV file (unless in dry-run mode)
  - Print detailed error messages to console
  - In dry-run mode: report errors but don't modify the CSV

## Testing

Three comprehensive test suites were added:

### 1. test_validation_disable.py
Unit tests for the disabling mechanism:
- `test_disable_configs_with_errors` - Verifies single config disabling
- `test_disable_multiple_configs` - Verifies multiple configs disabling
- `test_no_disable_when_no_errors` - Verifies no changes when validation passes

### 2. test_integration_validation.py
Integration tests with the TTSLO class:
- `test_validation_error_disables_config` - Full integration test with single error
- `test_validation_with_multiple_errors` - Full integration test with multiple errors

### 3. Existing tests
All existing tests continue to pass:
- test_validator_decimal.py - Balance validation tests
- test_ttslo.py - Core TTSLO functionality tests

## Example Output

When validation fails, users see:
```
ERROR: Validation failed for the following configs. They have been disabled:
  [invalid_price]:
    - threshold_price: Invalid threshold price: "not_a_number". Must be a valid number (e.g., 50000, 3000.50)
  [invalid_type]:
    - threshold_type: Invalid threshold_type: "wrong_type". Must be one of: above, below

These configs have been set to enabled=false in the configuration file.
Fix the errors and set enabled=true to re-enable them.
```

## Security Benefits

This change enhances the fail-safe design of TTSLO:
- Invalid configurations cannot accidentally trigger order creation
- Users are immediately notified of validation errors
- The system continues running with valid configurations only
- Clear remediation path is provided

## Backward Compatibility

This change is backward compatible:
- Existing valid configurations continue to work without modification
- The `enabled` field already exists in the config schema
- No changes to the API or command-line interface
- Dry-run mode preserves the non-destructive testing behavior
