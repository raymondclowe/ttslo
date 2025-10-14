# Kraken API Documentation Archive

This directory contains official Kraken REST API documentation for reference and compliance checking.

## Contents

### Account & Balance Endpoints

1. **get-trade-balance.md** - Complete documentation for the TradeBalance endpoint
   - Source: https://docs.kraken.com/api/docs/rest-api/get-trade-balance
   - Endpoint: `POST /0/private/TradeBalance`
   - Purpose: Get trade balance, margin info, equity, and available funds

### Order Management Endpoints

2. **add-order.md** - Complete documentation for the AddOrder endpoint
   - Source: https://docs.kraken.com/api/docs/rest-api/add-order
   - Endpoint: `POST /0/private/AddOrder`
   - Purpose: Place new orders (market, limit, trailing-stop, etc.)

3. **cancel-order.md** - Complete documentation for the CancelOrder endpoint
   - Source: https://docs.kraken.com/api/docs/rest-api/cancel-order
   - Endpoint: `POST /0/private/CancelOrder`
   - Purpose: Cancel open orders by txid, userref, or cl_ord_id

4. **edit-order.md** - Complete documentation for the EditOrder endpoint
   - Source: https://docs.kraken.com/api/docs/rest-api/edit-order
   - Endpoint: `POST /0/private/EditOrder`
   - Purpose: Edit parameters of live orders (cancels and recreates)

5. **edit-order.html** - Raw HTML backup of EditOrder documentation

### Compliance Report

**COMPLIANCE_REPORT.md** - Detailed analysis comparing the code implementation in `kraken_api.py` and `validator.py` against official Kraken API specifications.

Key findings:
- ✅ `get_trade_balance()` method: Fully compliant
- ✅ `add_order()` method: Fully compliant
- ✅ `add_trailing_stop_loss()` method: Fully compliant with extensive validation
- ✅ Balance validation: Warns if insufficient funds (non-blocking)
- ❌ `cancel_order()` method: Not implemented (HIGH PRIORITY)
- ❌ `edit_order()` method: Not implemented (MEDIUM PRIORITY)

See the full report for detailed analysis and recommendations.

## Download Date

All documentation was downloaded on: **2025-10-14**

## Purpose

This documentation archive serves multiple purposes:

1. **Reference**: Provides official API specifications for developers
2. **Compliance**: Enables verification that code follows official standards
3. **Testing**: Helps ensure API client behavior matches expectations
4. **Maintenance**: Assists with future updates and feature additions
5. **Offline Access**: Available when internet connectivity is limited

## Updating Documentation

To update the documentation with the latest versions from Kraken:

```bash
# Using curl or wget
curl -L 'https://docs.kraken.com/api/docs/rest-api/add-order' > add-order.html
curl -L 'https://docs.kraken.com/api/docs/rest-api/cancel-order' > cancel-order.html
curl -L 'https://docs.kraken.com/api/docs/rest-api/edit-order' > edit-order.html

# Or use the Tavily tool for better extraction
```

## Related Links

- [Kraken API Documentation](https://docs.kraken.com/api/)
- [Kraken REST API Guide](https://docs.kraken.com/api/docs/guides/spot-rest-auth)
- [Kraken Support](https://support.kraken.com/)

## Notes

- The Kraken API is continuously evolving - check official documentation for latest updates
- Some endpoints may have rate limits - see official documentation for details
- API authentication requires API-Key and API-Sign headers
- The EditOrder endpoint is being superseded by the AmendOrder endpoint
