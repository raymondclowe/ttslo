# Kraken API Live Testing Guide

## Overview

The live integration tests (`test_kraken_api_live.py`) run against the real Kraken API to verify the client implementation works correctly in production. These tests are designed to be safe and non-disruptive.

## Safety Features

### 1. Prerequisites Check
- **Only runs after local tests pass**: Live tests will not run unless all unit tests in `test_kraken_api.py` pass first
- **Requires explicit credentials**: Tests are skipped if environment variables are not set

### 2. Safe Order Design
All orders created during testing are designed to **never execute**:

- **Sell orders**: Placed at 10% above market price (too high to execute)  
- **Trailing stops**: Set with 10% offset (won't trigger immediately)

**Note**: Tests use sell orders to avoid needing USD balance - only BTC is required.

### 3. Minimal Volumes
All orders use minimal volumes close to the minimum order size:

- **Base volume**: 0.0001 BTC (typical minimum for BTC/USD pair)
- **Incremental variation**: Each order uses 5% more volume than the previous
- **Examples**: 0.0001, 0.000105, 0.00011025, 0.00011576...

This ensures minimal fees even if an order unexpectedly executes.

### 4. Complete Cleanup
All orders are cancelled at the end of each test:

- Each test verifies cancellation succeeded
- Queries confirm orders are removed from open orders
- No orders are left hanging after test completion

### 5. Comprehensive Logging
Every API operation is logged with full details:

- **Request parameters**: All inputs to API calls
- **Response data**: Complete API responses
- **Errors**: Any failures encountered
- **Log file**: Saved as `kraken_live_test_YYYYMMDD_HHMMSS.log`

## Environment Setup

### Required Environment Variables

```bash
export COPILOT_W_KR_RW_PUBLIC="your_kraken_api_key"
export COPILOT_W_KR_RW_SECRET="your_kraken_api_secret"
```

**Security Note**: These credentials must have "Orders and trades - Create & modify orders" permission.

### API Key Permissions Required

The API key must have the following permissions enabled:
- ✓ Query open orders & trades
- ✓ Create & modify orders
- ✓ Cancel/close orders

## Running Live Tests

### Method 1: Run All Tests (Recommended)

This runs local tests first, then live tests only if local tests pass:

```bash
cd /home/runner/work/ttslo/ttslo
uv run python test_kraken_api_live.py
```

Output:
```
Running local tests first...
========================= 25 passed in 0.30s ==========================
LOCAL TESTS PASSED - Proceeding with live tests
...
```

### Method 2: Run Live Tests Directly with pytest

If you want to run live tests directly (skips local test check):

```bash
uv run pytest test_kraken_api_live.py -v -s
```

The `-s` flag shows detailed logging output during test execution.

### Method 3: Run Specific Live Test

To run a single test:

```bash
uv run pytest test_kraken_api_live.py::TestKrakenAPILive::test_01_live_add_query_modify_cancel_limit_order -v -s
```

## Test Scenarios

The test suite includes **6 comprehensive tests**: 3 for sell orders and 3 equivalent buy order tests.

### Sell Order Tests (BTC/USD)

### Test 1: Complete Sell Order Lifecycle

**test_01_live_add_query_modify_cancel_limit_order**

Tests the full lifecycle of a limit sell order:

1. **Add** limit sell order at 10% above market
2. **Query** to verify order was created
3. **Modify** order (change volume)
4. **Query** to verify modification
5. **Cancel** order
6. **Query** to verify cancellation

**Order Details**:
- Pair: BTC/USD
- Type: Limit sell
- Volume: 0.0001 BTC
- Price: Current market + 10%

### Test 2: Trailing Stop Order

**test_02_live_add_trailing_stop_and_cancel**

Tests trailing stop loss orders:

1. **Add** trailing stop sell order with 10% offset
2. **Query** to verify order was created
3. **Cancel** order
4. **Query** to verify cancellation

**Order Details**:
- Pair: BTC/USD
- Type: Trailing stop sell
- Volume: 0.000105 BTC
- Offset: +10%

### Test 3: Multiple Orders

**test_03_live_multiple_orders_batch_cancel**

Tests handling multiple orders:

1. **Add** 3 limit sell orders with different volumes
2. **Query** to verify all were created
3. **Cancel** all orders one by one
4. **Query** to verify all were cancelled

**Order Details**:
- Pair: BTC/USD
- Type: Limit sell (all orders)
- Volumes: 0.00011025, 0.00011576, 0.00012155 BTC
- Price: Current market + 10%

### Buy Order Tests (BTC/USDT)

### Test 4: Complete Buy Order Lifecycle

**test_04_live_buy_limit_order_lifecycle**

Tests the full lifecycle of a limit buy order:

1. **Add** limit buy order at 10% below market
2. **Query** to verify order was created
3. **Modify** order (change volume)
4. **Query** to verify modification
5. **Cancel** order
6. **Query** to verify cancellation

**Order Details**:
- Pair: BTC/USDT
- Type: Limit buy
- Volume: 0.000134 BTC
- Price: Current market - 10%

**Note**: Uses BTC/USDT pair since account has USDT balance for buy orders.

### Test 5: Buy Trailing Stop Order

**test_05_live_buy_trailing_stop_and_cancel**

Tests buy trailing stop orders:

1. **Add** trailing stop buy order with 10% offset
2. **Query** to verify order was created
3. **Cancel** order
4. **Query** to verify cancellation

**Order Details**:
- Pair: BTC/USDT
- Type: Trailing stop buy
- Volume: 0.000141 BTC
- Offset: +10%

### Test 6: Multiple Buy Orders

**test_06_live_multiple_buy_orders_batch_cancel**

Tests handling multiple buy orders:

1. **Add** 3 limit buy orders with different volumes
2. **Query** to verify all were created
3. **Cancel** all orders one by one
4. **Query** to verify all were cancelled

**Order Details**:
- Pair: BTC/USDT
- Type: Limit buy (all orders)
- Volumes: 0.000148, 0.000155, 0.000163 BTC
- Price: Current market - 10%

## Log File Format

The test creates a JSON log file with detailed information:

```json
{
  "timestamp": "2025-10-16T03:15:30.123456",
  "operation": "add_order",
  "params": {
    "pair": "XXBTZUSD",
    "order_type": "limit",
    "direction": "buy",
    "volume": 0.0001,
    "price": "90000.0"
  },
  "response": {
    "error": [],
    "result": {
      "descr": {
        "order": "buy 0.0001 XXBTZUSD @ limit 90000.0"
      },
      "txid": ["ORDERID-123"]
    }
  },
  "error": null
}
```

Each operation includes:
- **timestamp**: ISO format timestamp
- **operation**: API method name
- **params**: All input parameters
- **response**: Complete API response
- **error**: Error message if operation failed

## Troubleshooting

### Tests are Skipped

**Symptom**: Tests show as "skipped" with message about credentials

**Solution**: Set environment variables:
```bash
export COPILOT_W_KR_RW_PUBLIC="your_api_key"
export COPILOT_W_KR_RW_SECRET="your_api_secret"
```

### API Error: Invalid Key

**Symptom**: `EAPI:Invalid key` error

**Solutions**:
1. Verify API key is correct
2. Check API key has not expired
3. Ensure API key has required permissions

### API Error: Insufficient Funds

**Symptom**: `EGeneral:Insufficient funds` error

**Solutions**:
1. Ensure account has at least 0.0001 BTC available
2. Check if funds are locked in other orders
3. Verify account is not in margin call

### Order Edit Failed

**Symptom**: Edit order operation fails

**Note**: Order editing may not be supported for all order types or may have restrictions. The test logs a warning but continues to cancellation if edit fails.

**This is expected behavior** - the test will still pass as long as add/query/cancel work.

### Test Hangs on Query

**Symptom**: Test appears to hang during query operation

**Solutions**:
1. Check internet connection to Kraken API
2. Verify Kraken API is not experiencing downtime
3. Check for rate limiting (tests include 2-second delays)

### Local Tests Must Pass First

**Symptom**: Live tests don't run when using `python test_kraken_api_live.py`

**Expected**: This is by design! Local tests must pass first.

**To bypass**: Use pytest directly:
```bash
uv run pytest test_kraken_api_live.py -v -s
```

## Best Practices

### 1. Review Logs After Each Run

Always check the log file after running live tests:
```bash
cat kraken_live_test_*.log | jq .
```

### 2. Monitor Account During Tests

Keep Kraken web interface open to monitor:
- Orders being created
- Orders being modified  
- Orders being cancelled

### 3. Test During Low Volatility

Run tests during periods of lower market volatility to ensure prices don't move significantly during test execution.

### 4. Check Account Balance First

Ensure account has sufficient balances before running tests:
- **BTC**: Minimum 0.0001 BTC + margin for fees (for sell order tests)
- **USDT**: Minimum ~15 USDT (for buy order tests at ~$100k BTC price)
- Recommended: 0.001 BTC and 150 USDT for safety

### 5. Don't Run Concurrently

Don't run multiple instances of live tests simultaneously - they may interfere with each other.

## Cost Estimate

Each test run creates and cancels multiple orders:

**Sell Order Tests:**
- **Test 1**: 1 sell order (add, modify, cancel)
- **Test 2**: 1 sell order (add, cancel)  
- **Test 3**: 3 sell orders (add, cancel)

**Buy Order Tests:**
- **Test 4**: 1 buy order (add, modify, cancel)
- **Test 5**: 1 buy order (add, cancel)  
- **Test 6**: 3 buy orders (add, cancel)

**Total**: ~10 orders per full test run (5 sell + 5 buy)

**Cost**: Zero if no orders execute (by design). Minimal fees (< $0.20) if an order unexpectedly executes due to extreme price movement.

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Kraken API Live Tests

on:
  workflow_dispatch:  # Manual trigger only
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sundays

jobs:
  live-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      
      - name: Run Live Tests
        env:
          COPILOT_W_KR_RW_PUBLIC: ${{ secrets.KRAKEN_API_KEY }}
          COPILOT_W_KR_RW_SECRET: ${{ secrets.KRAKEN_API_SECRET }}
        run: |
          uv run python test_kraken_api_live.py
      
      - name: Upload Logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: live-test-logs
          path: kraken_live_test_*.log
```

**Important**: Only run on manual triggers or scheduled runs, not on every PR.

## Extending the Tests

To add new test scenarios:

1. **Follow the naming convention**: `test_XX_live_description`
2. **Use varying volumes**: Call `self.get_next_volume(iteration)` with unique iteration numbers
3. **Use unreasonable prices**: Call `get_unreasonable_buy_price()` or `get_unreasonable_sell_price()`
4. **Log all operations**: Use `test_logger.log_operation()`
5. **Clean up**: Always cancel orders at the end
6. **Verify cleanup**: Query to confirm orders are cancelled

Example template:

```python
def test_04_live_my_new_test(self, live_api, test_logger, btc_current_price):
    """Test description here."""
    volume = self.get_next_volume(6)  # Use unique iteration
    price = self.get_unreasonable_buy_price(btc_current_price)
    
    # Add order
    result = live_api.add_order(...)
    test_logger.log_operation('add_order', params, result)
    txid = result['txid'][0]
    
    # ... test logic ...
    
    # Always clean up
    live_api.cancel_order(txid)
    test_logger.log_operation('cancel_order', {'txid': txid}, cancel_result)
```

## Related Documentation

- [Kraken API Testing Guide](KRAKEN_API_TESTING.md) - Local/mocked testing
- [Kraken REST API Documentation](https://docs.kraken.com/api/)
- [Kraken API Rate Limits](https://docs.kraken.com/api/docs/guides/global-intro/rate-limiting)

## Support

If you encounter issues with live tests:

1. Check the log file for detailed error messages
2. Verify environment variables are set correctly
3. Ensure API key has required permissions
4. Review Kraken API status page for outages
5. Check account balance and available funds
