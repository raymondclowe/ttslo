# TTSLO Configuration Validation Rules

This document specifies all validation rules implemented in `validator.py` for TTSLO configuration files.

## Overview

The validator checks configuration entries and produces two types of feedback:
- **ERRORS**: Critical issues that prevent the configuration from running. Must be fixed.
- **WARNINGS**: Non-critical issues or unusual configurations that should be reviewed but don't prevent execution.

## Configuration Structure

Each configuration entry must be enabled (`enabled: true`) to be validated. Disabled configurations are skipped.

### Required Fields

All of the following fields must be present and non-empty:
- `id` - Configuration identifier
- `pair` - Trading pair (e.g., XBTUSDT, ETHUSDT)
- `threshold_price` - Price threshold to trigger the order
- `threshold_type` - Whether to trigger "above" or "below" the threshold
- `direction` - Order direction: "buy" or "sell"
- `volume` - Amount to trade
- `trailing_offset_percent` - Trailing stop loss offset percentage
- `enabled` - Whether this configuration is active

**Error**: If any required field is missing or empty, an error is raised for that field.

---

## Field-Specific Validation

### 1. ID Field (`id`)

#### ERRORS:
- **Missing or Empty**: `Required field "id" is missing or empty`
- **Invalid Characters**: ID contains characters other than letters, numbers, underscores, and hyphens
  - Example: `ID "my config!" contains invalid characters. Use only letters, numbers, underscores, and hyphens`
- **Duplicate ID**: Multiple configurations use the same ID
  - Example: `Duplicate configuration ID: btc_order_1`

#### WARNINGS:
- **Very Long ID**: ID exceeds 50 characters
  - Example: `ID "very_long_configuration_name_that_exceeds_fifty_chars" is very long (54 characters). Consider using a shorter ID`

---

### 2. Trading Pair Field (`pair`)

#### ERRORS:
- **Missing or Empty**: `Required field "pair" is missing or empty`
- **Invalid Format**: Pair contains characters other than uppercase letters and numbers
  - Example: `Trading pair "btc-usd" has invalid format. It should only contain uppercase letters and numbers`
- **Invalid Kraken Pair**: Pair is not recognized as a valid Kraken trading pair (checked against cached pairs list)
  - Example: `Trading pair "INVALID" is NOT a valid Kraken pair. Common examples: XBTUSDT (BTC/USDT), ETHUSDT (ETH/USDT), SOLUSDT (SOL/USDT). Check https://api.kraken.com/0/public/AssetPairs for all valid pairs.`

#### WARNINGS:
- **Pair Verification Failed**: Unable to verify pair against Kraken's list due to network or cache issues
  - Example: `Could not verify pair against Kraken pairs list: [error details]`

---

### 3. Threshold Price Field (`threshold_price`)

#### ERRORS:
- **Missing or Empty**: `Required field "threshold_price" is missing or empty`
- **Invalid Number**: Value cannot be parsed as a valid number
  - Example: `Invalid threshold price: "abc". Must be a valid number (e.g., 50000, 3000.50)`
- **Non-Positive**: Price is zero or negative
  - Example: `Threshold price must be positive, got: -100`
- **Already Met (with market price)**: Current market price has already crossed the threshold
  - For "above" threshold: `Threshold price 50000.00 is already met (current price: 55000.00). For "above" threshold, set price higher than current market price.`
  - For "below" threshold: `Threshold price 30000.00 is already met (current price: 28000.00). For "below" threshold, set price lower than current market price.`
- **Insufficient Gap**: Gap between threshold and current price is less than trailing offset
  - Example: `Insufficient gap between threshold (51000.00) and current price (50000.00). Gap is 2.00% but trailing offset is 5.00%. Order would trigger immediately or not work as intended.`

#### WARNINGS:
- **Very Small Price**: Price is less than 0.01
  - Example: `Threshold price is very small (0.005). Please verify this is correct`
- **Very Large Price**: Price exceeds 1,000,000
  - Example: `Threshold price is very large (2000000). Please verify this is correct`
- **Small Gap**: Gap between threshold and current price is less than 2x the trailing offset
  - Example: `Small gap between threshold (51500.00) and current price (50000.00). Gap is 3.00% but trailing offset is 5.00%. Consider a gap of at least 10.0% for best results.`

---

### 4. Threshold Type Field (`threshold_type`)

#### ERRORS:
- **Missing or Empty**: `Required field "threshold_type" is missing or empty`
- **Invalid Value**: Value is not "above" or "below"
  - Example: `Invalid threshold_type: "over". Must be one of: above, below`

#### WARNINGS:
None (handled by logic validation)

---

### 5. Direction Field (`direction`)

#### ERRORS:
- **Missing or Empty**: `Required field "direction" is missing or empty`
- **Invalid Value**: Value is not "buy" or "sell"
  - Example: `Invalid direction: "purchase". Must be one of: buy, sell`

#### WARNINGS:
None (handled by logic validation)

---

### 6. Volume Field (`volume`)

#### ERRORS:
- **Missing or Empty**: `Required field "volume" is missing or empty`
- **Invalid Number**: Value cannot be parsed as a valid number
  - Example: `Invalid volume: "1.5.3". Must be a valid number (e.g., 0.01, 1.5)`
- **Non-Positive**: Volume is zero or negative
  - Example: `Volume must be positive, got: 0`

#### WARNINGS:
- **Very Small Volume**: Volume is less than 0.0001
  - Example: `Volume is very small (0.00005). This may be below minimum order sizes for some pairs`
- **Very Large Volume**: Volume exceeds 1000
  - Example: `Volume is very large (1500.00). Please verify this is correct and you have sufficient balance`
- **Insufficient Balance** (for sell orders): Available balance is less than required volume
  - Example: `Insufficient XBT balance for sell order. Required: 0.01000000, Available: 0.00500000. You can add funds before the order triggers.`

---

### 7. Trailing Offset Percent Field (`trailing_offset_percent`)

#### ERRORS:
- **Missing or Empty**: `Required field "trailing_offset_percent" is missing or empty`
- **Invalid Number**: Value cannot be parsed as a valid number
  - Example: `Invalid trailing offset: "5%". Must be a valid percentage number (e.g., 5.0, 3.5)`
- **Non-Positive**: Offset is zero or negative
  - Example: `Trailing offset must be positive, got: -5`

#### WARNINGS:
- **Very Small Offset**: Offset is less than 0.1%
  - Example: `Trailing offset is very small (0.05%). This may trigger very quickly on normal price volatility`
- **Large Offset**: Offset is greater than 20% but less than or equal to 50%
  - Example: `Trailing offset is large (25.00%). Consider if this gives enough protection`
- **Very Large Offset**: Offset exceeds 50%
  - Example: `Trailing offset is very large (60.00%). The order may execute immediately or never trigger`

---

### 8. Enabled Field (`enabled`)

#### ERRORS:
- **Missing or Empty**: `Required field "enabled" is missing or empty`
- **Invalid Value**: Value is not one of: true, false, yes, no, 1, 0 (case-insensitive)
  - Example: `Invalid enabled value: "on". Must be one of: true, false, yes, no, 1, 0 (case-insensitive)`

#### WARNINGS:
None

---

## Cross-Field Logic Validation

These warnings check for unusual or potentially unintended combinations of field values.

### Unusual Threshold/Direction Combinations

#### WARNINGS:
- **"Above" + "Buy"**: Buying when price goes up is unusual (typically you'd want to buy when price goes down)
  - Example: `Threshold "above" with direction "buy" is unusual. This will buy when price goes up. Verify this is intended.`

- **"Below" + "Sell"**: Selling when price goes down is unusual (typically you'd want to sell when price goes up)
  - Example: `Threshold "below" with direction "sell" is unusual. This will sell when price goes down. Verify this is intended.`

### Large Trailing Offset with Threshold Direction

#### WARNINGS:
When trailing offset exceeds 30%:

- **Large offset on upward threshold ("above" + "sell")**: May trigger immediately if price has moved significantly
  - Example: `Large trailing offset (35.00%) on an upward threshold. Order may trigger immediately if price has moved significantly`

- **Large offset on downward threshold ("below" + "buy")**: May trigger immediately if price has moved significantly
  - Example: `Large trailing offset (35.00%) on a downward threshold. Order may trigger immediately if price has moved significantly`

---

## Balance Checking (Warnings Only)

When a Kraken API connection is available, the validator checks available balance for sell orders.

### Balance Availability (for sell orders)

#### WARNINGS:
- **Balance Information**: Always shows available balance from all sources (spot and funding wallets)
  - Example: `Available XBT (spot+funding): 0.01069060 (Contributors: XBT.F=0.01069060, XXBT=0.00000000) — sufficient for required volume 0.01000000`

- **Insufficient Balance**: When available balance is less than required volume
  - Example: `Insufficient XBT balance for sell order. Required: 0.01000000, Available: 0.00500000. You can add funds before the order triggers.`

**Note**: Balance checks are warnings only because users can add funds before the order triggers.

---

## General Configuration Validation

### Empty Configuration

#### ERRORS:
- **Empty File**: `Configuration file is empty or contains no valid entries`

---

## Validation Workflow

1. **Skip disabled configs**: If `enabled` is not set to 'true', 'yes', or '1', the configuration is skipped entirely
2. **Required fields check**: All required fields must be present and non-empty
3. **Individual field validation**: Each field is validated according to its specific rules
4. **Duplicate ID check**: Ensures no two enabled configurations have the same ID
5. **Cross-field logic validation**: Checks for unusual combinations and logical consistency
6. **Market price validation** (if API available): Validates threshold against current market price
7. **Balance check** (if API available): Checks if sufficient balance exists for sell orders

---

## Notes on Balance Normalization

The validator normalizes asset keys when checking balances because Kraken returns balances with multiple formats:
- Spot wallet: `XXBT`, `XETH`, etc.
- Funding wallet: `XBT.F`, `ETH.F`, etc.

The validator:
1. Removes `.F` suffix from funding wallet keys
2. Strips leading `X` and `Z` characters
3. Sums all matching balances (spot + funding)
4. Compares total against required volume

Example: For Bitcoin (XBT), both `XXBT` (spot) and `XBT.F` (funding) balances are considered.

---

## Decimal Precision

All price, volume, and percentage calculations use Python's `Decimal` type to avoid floating-point precision issues. The validator uses 28 digits of precision for currency arithmetic.

---

## Exit Codes and Result

The validator returns a `ValidationResult` object with:
- `errors` list: All validation errors
- `warnings` list: All validation warnings
- `configs` list: All enabled configurations
- `is_valid()`: Returns `True` if no errors (warnings are allowed)
- `has_warnings()`: Returns `True` if any warnings exist

**Important**: Configuration with errors cannot be executed. Configuration with warnings can be executed but should be carefully reviewed.
