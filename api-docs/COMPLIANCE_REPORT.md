# Kraken API Compliance Report

**Date:** 2025-10-14  
**Repository:** raymondclowe/ttslo  
**Analyzed File:** `kraken_api.py`

## Executive Summary

This report compares the implementation in `kraken_api.py` against the official Kraken REST API documentation for order management endpoints.

### Documentation Sources

1. **Add Order:** https://docs.kraken.com/api/docs/rest-api/add-order
2. **Cancel Order:** https://docs.kraken.com/api/docs/rest-api/cancel-order
3. **Edit Order:** https://docs.kraken.com/api/docs/rest-api/edit-order

All documentation has been downloaded and saved in the `api-docs/` directory.

## Findings

### ✅ Compliant Implementations

#### 1. `add_order()` Method

**Location:** `kraken_api.py` lines 186-213

**Compliance Status:** ✅ **COMPLIANT**

**Analysis:**
- ✅ Uses correct endpoint: `AddOrder` via `_query_private()`
- ✅ Correctly maps parameters:
  - `pair` → API parameter `pair`
  - `direction` → API parameter `type` (buy/sell)
  - `order_type` → API parameter `ordertype`
  - `volume` → API parameter `volume` (converted to string)
- ✅ Supports additional parameters via `**kwargs`
- ✅ Properly handles error responses from API
- ✅ Returns the result dictionary from API response

**Official API Parameters Supported:**
- Required: `pair`, `type`, `ordertype`, `volume` ✅
- Optional: All optional parameters can be passed via `**kwargs` ✅

**Recommendations:**
- Consider adding validation for `ordertype` values (market, limit, iceberg, stop-loss, take-profit, stop-loss-limit, take-profit-limit, trailing-stop, trailing-stop-limit, settle-position)
- Consider adding validation for `direction` values (buy, sell)
- Consider adding `nonce` generation if not handled by `_query_private()`

---

#### 2. `add_trailing_stop_loss()` Method

**Location:** `kraken_api.py` lines 215-333

**Compliance Status:** ✅ **COMPLIANT**

**Analysis:**
- ✅ Uses correct endpoint: `AddOrder` via `_query_private()`
- ✅ Correctly sets `ordertype` to `trailing-stop`
- ✅ Properly formats trailing offset with `+` prefix and `%` suffix (e.g., `+5.0%`)
- ✅ Validates all required parameters (pair, direction, volume, trailing_offset_percent)
- ✅ Properly handles error responses
- ✅ Extensive parameter validation (10 validation steps)

**Official API Requirements:**
According to the documentation, for `trailing-stop` orders:
- `ordertype` must be `trailing-stop` ✅
- `price` field should use relative price with `+` prefix ✅ (implemented as `trailingoffset`)
- Direction is automatic based on buy/sell ✅
- The `%` suffix can be used for relative percentage ✅

**Parameter Mapping:**
- `pair` → API parameter `pair` ✅
- `direction` → API parameter `type` (normalized to lowercase) ✅
- `volume` → API parameter `volume` (converted to string) ✅
- `trailing_offset_percent` → API parameter `trailingoffset` (formatted as `+X.X%`) ✅

**Recommendations:**
- Implementation exceeds compliance with extensive validation
- Consider documenting that `trailingoffset` parameter is used instead of `price` for trailing stops

---

### ⚠️ Missing Implementations

#### 3. `cancel_order()` Method

**Status:** ❌ **NOT IMPLEMENTED**

**Official API Endpoint:** `POST /0/private/CancelOrder`

**Required Functionality:**
- Cancel orders by `txid`, `userref`, or `cl_ord_id`
- Return count of cancelled orders and pending status

**Impact:**
- Users cannot programmatically cancel orders through this library
- Must use Kraken web interface or other tools to cancel orders
- Limits automation capabilities for order management

**Recommendation:** **HIGH PRIORITY**
- Implement `cancel_order()` method to allow cancelling orders
- Add support for cancelling by `txid`, `userref`, or `cl_ord_id`
- Include proper error handling and validation

**Suggested Implementation:**
```python
def cancel_order(self, txid=None, userref=None, cl_ord_id=None):
    """
    Cancel a particular open order by txid, userref or cl_ord_id.
    
    Args:
        txid: Kraken transaction ID (string) or user reference (integer)
        userref: User reference ID
        cl_ord_id: Client order ID
        
    Returns:
        Cancellation result dictionary
    """
    if not any([txid, userref, cl_ord_id]):
        raise ValueError("Must provide txid, userref, or cl_ord_id")
    
    params = {}
    if txid is not None:
        params['txid'] = txid
    if cl_ord_id is not None:
        params['cl_ord_id'] = cl_ord_id
        
    result = self._query_private('CancelOrder', params)
    
    if result.get('error'):
        raise Exception(f"Kraken API error: {result['error']}")
        
    return result.get('result', {})
```

---

#### 4. `edit_order()` Method

**Status:** ❌ **NOT IMPLEMENTED**

**Official API Endpoint:** `POST /0/private/EditOrder`

**Required Functionality:**
- Edit parameters of a live order
- Cancels original order and creates new one with updated parameters
- Returns new `txid` and original `txid`

**Impact:**
- Users cannot modify existing orders programmatically
- Must cancel and recreate orders manually
- Reduces flexibility in order management strategies

**Recommendation:** **MEDIUM PRIORITY**
- Consider implementing `edit_order()` method
- Note: Kraken recommends using newer `AmendOrder` endpoint instead
- May want to implement `amend_order()` instead of or in addition to `edit_order()`

**Note:** The official documentation indicates that `EditOrder` has limitations:
- Cannot edit triggered stop-loss or take-profit orders
- The newer `AmendOrder` endpoint is recommended

**Suggested Implementation:**
```python
def edit_order(self, txid, pair, volume=None, price=None, price2=None, 
               ordertype=None, userref=None):
    """
    Edit an existing order (cancels and recreates with new parameters).
    
    Note: Consider using amend_order() instead for better performance.
    
    Args:
        txid: Transaction ID of order to edit
        pair: Asset pair
        volume: New volume (optional)
        price: New price (optional)
        price2: New secondary price (optional)
        ordertype: New order type (optional)
        userref: User reference (optional)
        
    Returns:
        Edit result with new txid
    """
    params = {
        'txid': txid,
        'pair': pair
    }
    
    if volume is not None:
        params['volume'] = str(volume)
    if price is not None:
        params['price'] = str(price)
    if price2 is not None:
        params['price2'] = str(price2)
    if ordertype is not None:
        params['ordertype'] = ordertype
    if userref is not None:
        params['userref'] = userref
        
    result = self._query_private('EditOrder', params)
    
    if result.get('error'):
        raise Exception(f"Kraken API error: {result['error']}")
        
    return result.get('result', {})
```

---

## Additional Compliance Considerations

### API Authentication
✅ The code properly implements Kraken API authentication:
- Uses `API-Key` and `API-Sign` headers
- Generates signatures with `_get_kraken_signature()` method
- Includes nonce in requests

### Error Handling
✅ The code properly checks for errors in API responses:
- Checks `result.get('error')` field
- Raises exceptions with error messages
- Validates response structure

### Parameter Formatting
✅ Parameters are correctly formatted:
- Volume converted to string
- Direction normalized to lowercase
- Trailing offset formatted with sign and percentage

---

## Summary of Compliance Issues

| Feature | Status | Priority | Notes |
|---------|--------|----------|-------|
| `add_order()` | ✅ Compliant | - | Fully functional |
| `add_trailing_stop_loss()` | ✅ Compliant | - | Exceeds requirements with validation |
| `cancel_order()` | ❌ Missing | HIGH | Essential for order management |
| `edit_order()` | ❌ Missing | MEDIUM | Limited by API, consider `amend_order()` |

---

## Recommendations

### Immediate Actions (High Priority)

1. **Implement `cancel_order()` method**
   - Essential for complete order lifecycle management
   - Users currently cannot cancel orders programmatically
   - Relatively simple implementation

### Future Enhancements (Medium Priority)

2. **Implement `edit_order()` or `amend_order()` method**
   - Provides order modification capabilities
   - Consider implementing `amend_order()` instead (newer API)
   - Check if `amend_order()` is available in Kraken REST API

3. **Add parameter validation to `add_order()`**
   - Validate `ordertype` against allowed values
   - Validate `direction` is 'buy' or 'sell'
   - Match the extensive validation in `add_trailing_stop_loss()`

4. **Consider implementing additional order-related methods**
   - `cancel_all_orders()` - Cancel all open orders
   - `cancel_all_orders_after()` - Dead man's switch
   - `get_open_orders()` - Query open orders
   - `get_closed_orders()` - Query closed orders

### Documentation Updates

5. **Update README.md**
   - Document that `cancel_order()` is not yet implemented
   - Provide workarounds for cancelling orders
   - List supported order management features

6. **Update API documentation references**
   - Add links to official Kraken API documentation
   - Reference the saved documentation in `api-docs/`

---

## Testing Recommendations

1. **Add tests for `cancel_order()` once implemented**
   - Test cancellation by txid
   - Test cancellation by userref
   - Test cancellation by cl_ord_id
   - Test error handling

2. **Validate existing implementations**
   - Verify `add_order()` with different order types
   - Verify `add_trailing_stop_loss()` with various parameters
   - Test error conditions and edge cases

---

## Conclusion

The existing order creation functionality (`add_order()` and `add_trailing_stop_loss()`) is **fully compliant** with the official Kraken API documentation and implements proper error handling and validation.

However, the library is **missing critical order management functionality**:
- ❌ Cannot cancel orders programmatically
- ❌ Cannot edit/amend orders programmatically

**Recommended Next Steps:**
1. Implement `cancel_order()` method (HIGH PRIORITY)
2. Consider implementing `edit_order()` or `amend_order()` (MEDIUM PRIORITY)
3. Add comprehensive tests for new functionality
4. Update documentation to reflect capabilities and limitations

---

## Appendix: API Documentation Files

All official Kraken API documentation has been saved in the `api-docs/` directory:

- `add-order.md` - Complete documentation for AddOrder endpoint
- `cancel-order.md` - Complete documentation for CancelOrder endpoint
- `edit-order.md` - Complete documentation for EditOrder endpoint
- `edit-order.html` - Raw HTML backup of EditOrder documentation
- `COMPLIANCE_REPORT.md` - This compliance report

These files provide a reference for future development and maintenance of the Kraken API client.
