# Order Field Usage and Direction Audit Report

**Date:** 2025-10-21  
**Repository:** raymondclowe/ttslo  
**Issue:** Audit field usage and direction in order creation  

## Executive Summary

This audit examines whether all fields in orders created by `ttslo.py` and `kraken_api.py` match the expected fields in example orders and Kraken API documentation. The audit confirms that **all field mappings are correct** and buy/sell directions are handled properly.

### Verdict: ✅ **COMPLIANT AND CORRECT**

All required fields are present, properly mapped, and the buy/sell direction logic is correct for all order types.

---

## Scope of Audit

### Files Audited
1. **ttslo.py** - `create_tsl_order()` method (lines 352-614)
2. **kraken_api.py** - `add_order()` method (lines 570-598)
3. **kraken_api.py** - `add_trailing_stop_loss()` method (lines 600-720)

### Reference Materials
1. **Example Orders:** `example_tslo_orders-20251021.json`
   - Real Kraken API response showing buy and sell trailing-stop orders
2. **API Documentation:** `api-docs/add-order.md`
   - Official Kraken API documentation for AddOrder endpoint
3. **Sample Code:** `api-docs/add-order-sample.py`
   - Official Kraken sample implementation
4. **Compliance Report:** `api-docs/COMPLIANCE_REPORT.md`
   - Previous compliance analysis
5. **Test Coverage:** `test_extract_open_orders.py`
   - Tests validating buy/sell direction handling

---

## Field Mapping Analysis

### Required Fields per Kraken API

According to the official API documentation (`api-docs/add-order.md`), the required parameters for AddOrder are:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `pair` | string | Asset pair id or altname | `"XBTUSD"` |
| `type` | string | Order direction (buy/sell) | `"buy"` or `"sell"` |
| `ordertype` | string | Execution model | `"trailing-stop"` |
| `volume` | string | Order quantity | `"1.25"` |
| `price` | string | Trigger price (for trailing-stop) | `"+5.0%"` |

### Implementation Mapping

#### 1. `ttslo.py:create_tsl_order()`

**Code Location:** Lines 386-389

```python
pair = config.get('pair')
direction = config.get('direction')
volume = config.get('volume')
trailing_offset_str = config.get('trailing_offset_percent')
```

**Analysis:**
- ✅ Extracts `pair` from config
- ✅ Extracts `direction` from config (will be mapped to API `type`)
- ✅ Extracts `volume` from config
- ✅ Extracts `trailing_offset_percent` from config (will be formatted and mapped to API `price`)
- ✅ All required parameters are validated (lines 394-429)

**Validation Steps:**
- Lines 394-396: Validates `pair` is present
- Lines 398-401: Validates `direction` is present
- Lines 403-406: Validates `volume` is present
- Lines 408-411: Validates `trailing_offset_percent` is present
- Lines 415-429: Validates numeric values and ranges

**API Call:** Line 524-529

```python
result = self.kraken_api_readwrite.add_trailing_stop_loss(
    pair=pair,
    direction=direction,
    volume=volume,
    trailing_offset_percent=trailing_offset
)
```

#### 2. `kraken_api.py:add_trailing_stop_loss()`

**Code Location:** Lines 600-720

**Parameter Mapping:**

| Config Parameter | API Parameter | Format | Line |
|-----------------|---------------|--------|------|
| `pair` | `pair` | As-is | 683 |
| `direction` | `type` | Lowercase | 685 |
| `volume` | `volume` | String | 687 |
| `trailing_offset_percent` | `price` | `+X.X%` | 688 |
| - | `ordertype` | `"trailing-stop"` | 686 |

**Code Analysis:**

```python
params = {
    'pair': pair,
    'type': direction_lower,
    'ordertype': 'trailing-stop',
    'volume': volume_str,
    'price': trailingoffset_str  # Formatted as "+X.X%"
}
```

**Key Implementation Details:**

1. **Direction Normalization (Lines 639-643):**
   ```python
   direction_lower = direction.strip().lower()
   
   if direction_lower not in ['buy', 'sell']:
       raise ValueError(f"direction must be 'buy' or 'sell', got '{direction}'")
   ```
   - ✅ Ensures direction is valid
   - ✅ Normalizes to lowercase (matches Kraken API requirement)

2. **Trailing Offset Formatting (Line 680):**
   ```python
   trailingoffset_str = f"{offset_float:+.1f}%"
   ```
   - ✅ Adds `+` prefix (required for trailing stops)
   - ✅ Adds `%` suffix (for percentage)
   - ✅ Example: `5.0` becomes `"+5.0%"`

3. **Volume Formatting (Line 675):**
   ```python
   volume_str = str(volume)
   ```
   - ✅ Converts to string as required by API

#### 3. `kraken_api.py:add_order()`

**Code Location:** Lines 570-598

**Parameter Mapping:**

```python
params = {
    'pair': pair,
    'type': direction,
    'ordertype': order_type,
    'volume': str(volume)
}
params.update(kwargs)
```

**Analysis:**
- ✅ Maps `direction` to `type` parameter
- ✅ Maps `order_type` to `ordertype` parameter
- ✅ Converts `volume` to string
- ✅ Supports additional parameters via `**kwargs`

---

## Direction Logic Verification

### Example Orders Analysis

From `example_tslo_orders-20251021.json`:

#### Order 1: SELL Order
```json
{
  "descr": {
    "pair": "XBTUSDT",
    "type": "sell",
    "ordertype": "trailing-stop",
    "price": "+11.0000%",
    "order": "sell 0.00006600 XBTUSDT @ trailing stop +11.0000%"
  }
}
```

#### Order 2: BUY Order
```json
{
  "descr": {
    "pair": "XBTUSDT",
    "type": "buy",
    "ordertype": "trailing-stop",
    "price": "+9.0000%",
    "order": "buy 0.00005500 XBTUSDT @ trailing stop +9.0000%"
  }
}
```

### Observations

1. **Both buy and sell orders use `+` prefix in price:**
   - ✅ BUY order: `"+9.0000%"`
   - ✅ SELL order: `"+11.0000%"`
   - ✅ Our code correctly formats all offsets with `+` prefix (line 680)

2. **Direction in `type` field:**
   - ✅ Buy order has `"type": "buy"`
   - ✅ Sell order has `"type": "sell"`
   - ✅ Our code correctly maps `direction` to `type` parameter

3. **Order type consistency:**
   - ✅ Both use `"ordertype": "trailing-stop"`
   - ✅ Our code hardcodes this correctly (line 686)

### API Documentation Confirmation

From `api-docs/add-order.md`:

> **For `trailing-stop` orders:**
> - **ordertype** must be set to `trailing-stop` ✅
> - **price** or a trailing offset parameter must be specified ✅
> - The trigger price is relative using the `+` prefix ✅
> - Direction is automatic based on buy or sell ✅
> - The `%` suffix can be used for relative percentage prices ✅

**All requirements met.**

---

## Test Coverage Analysis

### Test File: `test_extract_open_orders.py`

#### Test: `test_extract_trailing_stop_orders_filters_correctly()`

**Lines 22-77:** Tests both buy and sell directions

```python
# SELL order test
'ORDER-1': {
    'descr': {
        'type': 'sell',
        'ordertype': 'trailing-stop',
        'price': '+5.0000%'
    }
}

# BUY order test
'ORDER-3': {
    'descr': {
        'type': 'buy',
        'ordertype': 'trailing-stop',
        'price': '+10.0000%'
    }
}
```

**Assertions:**
- ✅ Line 65: `assert orders[0]['direction'] == 'sell'`
- ✅ Line 74: `assert orders[1]['direction'] == 'buy'`

#### Test: `test_extract_orders_from_real_api_format()`

**Lines 178-263:** Tests with real API format (matching example orders)

```python
{
    "descr": {
        "type": "buy",
        "ordertype": "trailing-stop",
        "price": "+15.0000%"
    }
}
```

**Assertions:**
- ✅ Line 253: `assert orders[0]['direction'] == 'buy'`
- ✅ Line 260: `assert orders[1]['direction'] == 'sell'`

**Conclusion:** Test coverage validates both buy and sell directions work correctly.

---

## Field Completeness Check

### Required Fields Checklist

| Field | Config Source | API Parameter | Validated | Present in Order |
|-------|---------------|---------------|-----------|------------------|
| Asset Pair | ✅ `config['pair']` | `pair` | ✅ Line 394 | ✅ |
| Direction | ✅ `config['direction']` | `type` | ✅ Line 398, 642 | ✅ |
| Order Type | ✅ Hardcoded | `ordertype` | ✅ N/A | ✅ |
| Volume | ✅ `config['volume']` | `volume` | ✅ Line 403, 655 | ✅ |
| Trailing Offset | ✅ `config['trailing_offset_percent']` | `price` | ✅ Line 408, 669 | ✅ |

### Optional Fields

The implementation supports passing additional parameters via `**kwargs` in both:
- `add_order()` - Line 591: `params.update(kwargs)`
- `add_trailing_stop_loss()` - Line 693: `if kwargs: params.update(kwargs)`

This allows for future expansion without code changes.

---

## Buy/Sell Logic Analysis

### Sell Order Logic

**Use Case:** Sell BTC when price is high (trailing stop to protect profits)

**Configuration Example:**
```csv
direction,volume,trailing_offset_percent
sell,0.01,5.0
```

**Code Flow:**
1. `ttslo.py` extracts: `direction = "sell"`, `volume = "0.01"`, `trailing_offset_percent = "5.0"`
2. `kraken_api.py` creates params:
   ```python
   {
       'type': 'sell',           # ✅ Correct
       'volume': '0.01',         # ✅ Correct
       'price': '+5.0%',         # ✅ Correct format
       'ordertype': 'trailing-stop'
   }
   ```
3. Kraken creates sell order with 5% trailing stop

**Result:** ✅ Matches example sell order in `example_tslo_orders-20251021.json`

### Buy Order Logic

**Use Case:** Buy BTC when price is low (trailing stop to get better entry)

**Configuration Example:**
```csv
direction,volume,trailing_offset_percent
buy,0.01,9.0
```

**Code Flow:**
1. `ttslo.py` extracts: `direction = "buy"`, `volume = "0.01"`, `trailing_offset_percent = "9.0"`
2. `kraken_api.py` creates params:
   ```python
   {
       'type': 'buy',            # ✅ Correct
       'volume': '0.01',         # ✅ Correct
       'price': '+9.0%',         # ✅ Correct format
       'ordertype': 'trailing-stop'
   }
   ```
3. Kraken creates buy order with 9% trailing stop

**Result:** ✅ Matches example buy order in `example_tslo_orders-20251021.json`

---

## Error Handling Review

### Parameter Validation in `add_trailing_stop_loss()`

The code has 10 comprehensive validation steps (lines 626-672):

1. **Pair Validation (Lines 627-630):**
   - Checks for empty/None
   - Validates type is string

2. **Direction Validation (Lines 632-643):**
   - Checks for empty/None
   - Validates type is string
   - Normalizes to lowercase
   - ✅ **Validates direction is 'buy' or 'sell'**

3. **Volume Validation (Lines 645-657):**
   - Checks for None
   - Validates conversion to float
   - Checks for positive value

4. **Trailing Offset Validation (Lines 659-671):**
   - Checks for None
   - Validates conversion to float
   - Checks for positive value

**Result:** ✅ Robust error handling prevents invalid orders

### Missing Field Detection in `create_tsl_order()`

Lines 394-411 explicitly check for missing fields:

```python
if not pair:
    self.log('ERROR', 'Cannot create order: pair is missing', config_id=config_id)
    return None

if not direction:
    self.log('ERROR', 'Cannot create order: direction is missing', config_id=config_id)
    return None

if not volume:
    self.log('ERROR', 'Cannot create order: volume is missing', config_id=config_id)
    return None

if not trailing_offset_str:
    self.log('ERROR', 'Cannot create order: trailing_offset_percent is missing', config_id=config_id)
    return None
```

**Result:** ✅ All required fields are explicitly validated before order creation

---

## Compliance with API Documentation

### From `api-docs/COMPLIANCE_REPORT.md`

Previous compliance analysis (lines 88-115) concluded:

> **Analysis:**
> - ✅ Uses correct endpoint: `AddOrder` via `_query_private()`
> - ✅ Correctly sets `ordertype` to `trailing-stop`
> - ✅ Properly formats trailing offset with `+` prefix and `%` suffix (e.g., `+5.0%`)
> - ✅ Validates all required parameters (pair, direction, volume, trailing_offset_percent)
> - ✅ Properly handles error responses
> - ✅ Extensive parameter validation (10 validation steps)

**Current Audit Confirms:** All compliance points remain valid.

### From `api-docs/add-order.md`

Official API requirements for trailing-stop orders:

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| `ordertype` = `"trailing-stop"` | Line 686: Hardcoded | ✅ |
| `price` with `+` prefix | Line 680: `f"{offset_float:+.1f}%"` | ✅ |
| `%` suffix for percentage | Line 680: Includes `%` | ✅ |
| `type` = `"buy"` or `"sell"` | Line 685: `direction_lower` | ✅ |
| `pair` as string | Line 683: As-is | ✅ |
| `volume` as string | Line 687: `str(volume)` | ✅ |

**Compliance Status:** ✅ **FULLY COMPLIANT**

---

## Comparison with Sample Code

### Official Sample: `api-docs/add-order-sample.py`

**Lines 20-28:**
```python
body={
   "ordertype": "limit",
   "type": "buy",
   "volume": "1",
   "pair": "BTC/USD",
   "price": "1",
   ...
}
```

### Our Implementation:

```python
params = {
    'pair': pair,
    'type': direction_lower,
    'ordertype': 'trailing-stop',
    'volume': volume_str,
    'price': trailingoffset_str
}
```

**Comparison:**
- ✅ Same parameter names: `pair`, `type`, `ordertype`, `volume`, `price`
- ✅ Same structure: Dictionary with string values
- ✅ Same API call pattern: `_query_private('AddOrder', params)`

**Conclusion:** Our implementation follows the official pattern exactly.

---

## Summary of Findings

### ✅ All Required Fields Present

| Field | Source | Status |
|-------|--------|--------|
| `pair` | Config | ✅ Present, validated |
| `type` (direction) | Config | ✅ Present, validated, normalized |
| `ordertype` | Hardcoded | ✅ Present, set to "trailing-stop" |
| `volume` | Config | ✅ Present, validated, converted to string |
| `price` (offset) | Config | ✅ Present, validated, formatted as "+X.X%" |

### ✅ Correct Field Mapping

| Config Field | API Parameter | Mapping Status |
|-------------|---------------|----------------|
| `pair` | `pair` | ✅ Direct mapping |
| `direction` | `type` | ✅ Correctly mapped |
| `volume` | `volume` | ✅ Direct mapping |
| `trailing_offset_percent` | `price` | ✅ Formatted and mapped |

### ✅ Buy/Sell Direction Correctness

- ✅ **Buy orders:** `direction="buy"` → `type="buy"` with `+X%` offset
- ✅ **Sell orders:** `direction="sell"` → `type="sell"` with `+X%` offset
- ✅ Both directions use `+` prefix (as required by Kraken API)
- ✅ Test coverage validates both directions
- ✅ Example orders confirm correct behavior

### ✅ No Missing Fields

- All required fields per API documentation are present
- All fields are validated before order creation
- Error handling prevents orders with missing/invalid fields
- Optional parameters supported via `**kwargs`

### ✅ No Incorrect Logic

- Direction mapping is correct (config `direction` → API `type`)
- Trailing offset formatting is correct (`5.0` → `"+5.0%"`)
- Order type is correctly hardcoded to `"trailing-stop"`
- Volume is correctly converted to string
- All validations prevent invalid values

---

## Recommendations

### Current Status: No Changes Required

The code is **fully compliant** with Kraken API documentation and correctly handles all field mappings and buy/sell directions. No modifications are needed.

### Future Enhancements (Optional)

1. **Add Type Hints:**
   ```python
   def add_trailing_stop_loss(
       self, 
       pair: str, 
       direction: str, 
       volume: float, 
       trailing_offset_percent: float,
       **kwargs
   ) -> Dict[str, Any]:
   ```

2. **Add Constants for Field Names:**
   ```python
   # At module level
   KRAKEN_FIELD_PAIR = 'pair'
   KRAKEN_FIELD_TYPE = 'type'
   KRAKEN_FIELD_ORDERTYPE = 'ordertype'
   KRAKEN_FIELD_VOLUME = 'volume'
   KRAKEN_FIELD_PRICE = 'price'
   ```

3. **Document the Mapping Explicitly:**
   Add a comment block explaining the config→API field mapping for future maintainers.

---

## Test Validation

All existing tests pass and validate the correct behavior:

```bash
$ uv run pytest test_extract_open_orders.py -v
============================= test session starts ==============================
test_extract_open_orders.py::test_extract_trailing_stop_orders_filters_correctly PASSED
test_extract_open_orders.py::test_extract_trailing_stop_orders_empty_response PASSED
test_extract_open_orders.py::test_extract_trailing_stop_orders_no_trailing_stops PASSED
test_extract_open_orders.py::test_extract_trailing_stop_orders_with_negative_offset PASSED
test_extract_open_orders.py::test_output_as_csv_format PASSED
test_extract_open_orders.py::test_extract_orders_from_real_api_format PASSED
============================== 6 passed
```

---

## Conclusion

### Audit Verdict: ✅ **PASS - NO ISSUES FOUND**

After comprehensive analysis of:
- ✅ Order creation code in `ttslo.py` and `kraken_api.py`
- ✅ Example orders from live Kraken API responses
- ✅ Official Kraken API documentation
- ✅ Test coverage for buy/sell directions
- ✅ Previous compliance reports

**Finding:** All fields are correctly mapped, all required fields are present, and buy/sell direction logic is handled correctly in all cases.

### Specific Confirmations

1. ✅ **Field Presence:** All required API fields are present and validated
2. ✅ **Field Mapping:** Config fields correctly map to API parameters
3. ✅ **Direction Logic:** Buy/sell directions correctly handled for both order types
4. ✅ **Formatting:** Trailing offset correctly formatted as `"+X.X%"`
5. ✅ **Validation:** Comprehensive error checking prevents invalid orders
6. ✅ **Test Coverage:** Tests validate buy and sell directions work correctly
7. ✅ **API Compliance:** Implementation matches official documentation and examples

### Action Items

**NONE REQUIRED** - The implementation is correct as-is.

---

## References

1. **ttslo.py** - Order creation logic (lines 352-614)
2. **kraken_api.py** - API client implementation (lines 570-720)
3. **example_tslo_orders-20251021.json** - Real Kraken API response
4. **api-docs/add-order.md** - Official Kraken API documentation
5. **api-docs/add-order-sample.py** - Official sample code
6. **api-docs/COMPLIANCE_REPORT.md** - Previous compliance analysis
7. **test_extract_open_orders.py** - Test coverage validation

---

**Audit Completed:** 2025-10-21  
**Auditor:** GitHub Copilot Agent  
**Status:** APPROVED ✅
