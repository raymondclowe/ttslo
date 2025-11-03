# Chained Pending Orders Feature

## Overview

The chained pending orders feature allows you to automatically link pending orders so that when one order fills successfully, it activates another order. This enables automated buy-low/sell-high strategies.

## Use Case

**Scenario**: You want to buy BTC when it drops to $100k, then automatically sell it when it rises to $120k.

**Without Chaining**: 
1. Create buy order at $100k
2. Wait for it to fill
3. Manually enable sell order at $120k
4. Wait for it to trigger

**With Chaining**:
1. Create both orders in config.csv with linked_order_id
2. System automatically enables sell order when buy fills
3. Completely automated!

## Configuration

### Basic Example

```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled,linked_order_id
btc_buy,XXBTZUSD,100000,below,buy,0.01,2.0,true,btc_sell
btc_sell,XXBTZUSD,120000,above,sell,0.01,2.0,false,
```

### Field Description

- `linked_order_id`: (Optional) The ID of another order in config.csv that will be automatically enabled when THIS order fills successfully.
- Leave empty (``) if no linked order
- Can chain multiple orders: A→B→C→D

### Complex Chain Example

```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled,linked_order_id
step1,XXBTZUSD,100000,below,buy,0.01,2.0,true,step2
step2,XXBTZUSD,105000,above,sell,0.01,2.0,false,step3
step3,XXBTZUSD,103000,below,buy,0.01,2.0,false,step4
step4,XXBTZUSD,108000,above,sell,0.01,2.0,false,
```

This creates a 4-order chain that executes in sequence.

## How It Works

### Order Lifecycle

1. **Parent Order Enabled**: The first order (e.g., btc_buy) is enabled and monitoring
2. **Threshold Reached**: Price crosses the threshold
3. **TSL Order Created**: Trailing stop loss order created on Kraken
4. **Order Fills**: Order executes and fills completely (status='closed')
5. **Linked Order Activated**: System automatically sets enabled='true' for linked order
6. **Notification Sent**: Telegram notification informs you of activation
7. **Cycle Repeats**: Linked order now monitors and can trigger its own linked order

### Activation Conditions

Linked order is activated ONLY when:
- ✅ Parent order status is 'closed' (fully filled)
- ✅ Linked order exists in config.csv
- ✅ Linked order is not already enabled
- ✅ Linked order is not already triggered

Linked order is NOT activated when:
- ❌ Parent order is partially filled (status='open')
- ❌ Parent order is canceled
- ❌ Linked order doesn't exist
- ❌ Linked order is already enabled
- ❌ Linked order was already triggered

## Validation

The validator automatically checks:

### 1. Linked Order Exists
```
ERROR: Linked order "btc_sell" does not exist in configuration
```

### 2. No Self-References
```
ERROR: Cannot link order to itself
```

### 3. No Circular References
```
ERROR: Circular reference detected in chain: order_a -> order_b -> order_a
```

### 4. Long Chain Warning
```
WARNING: Very long order chain detected (7 orders). Please verify this is intentional
```

Run validation before starting:
```bash
uv run ttslo.py --validate-config
```

## Testing

### Run All Chained Order Tests
```bash
uv run pytest tests/test_chained_orders.py tests/test_chained_orders_validation.py -v
```

### Run Demo
```bash
uv run python demos/demo_chained_orders.py
```

## Monitoring

### Check Logs
```bash
tail -f logs.csv | grep "linked"
```

Look for:
- `Order {id} filled, checking linked order: {linked_id}`
- `Successfully activated linked order {linked_id} after {parent_id} filled`
- `Linked order {linked_id} already enabled, skipping activation`

### Telegram Notifications

If configured, you'll receive:
```
🔗 TTSLO: Linked order activated!

Parent Order: btc_buy
Parent Pair: XXBTZUSD
Status: Filled ✓

→ Activated Linked Order:
Order ID: btc_sell
Pair: XXBTZUSD
Status: Now enabled and monitoring

💡 The linked order will trigger when its threshold is met.
```

## Troubleshooting

### Problem: Linked order not activating

**Check 1**: Is parent order fully filled?
```bash
# Check state.csv
grep "parent_order_id" state.csv
# Look for: triggered='true', order_id='ORDERID', fill_notified='true'
```

**Check 2**: Does linked order exist?
```bash
# Check config.csv
grep "linked_order_id" config.csv
```

**Check 3**: Check logs
```bash
grep "ERROR.*linked" logs.csv
```

### Problem: Circular reference error

**Solution**: Review your chain:
```
A -> B -> C -> A  ❌ Circular!
A -> B -> C -> D  ✅ Linear chain OK
```

Fix by removing the circular link:
```csv
order_a,XXBTZUSD,100000,below,buy,0.01,2.0,true,order_b
order_b,XXBTZUSD,110000,above,sell,0.01,2.0,false,order_c
order_c,XXBTZUSD,105000,below,buy,0.01,2.0,false,   <-- Remove link to order_a
```

### Problem: Parent order partially filled but linked didn't activate

**This is correct behavior!** Linked orders only activate on FULL fills (status='closed'), not partial fills. Wait for the order to fully complete.

## Best Practices

1. **Test in Dry-Run First**
   ```bash
   uv run ttslo.py --dry-run --verbose --once
   ```

2. **Start Simple**: Begin with 2-order chains before attempting complex multi-order strategies

3. **Validate Config**: Always run `--validate-config` after editing

4. **Monitor Carefully**: Watch logs and notifications during first few cycles

5. **Use Appropriate Thresholds**: Ensure there's enough price movement between chained orders

6. **Consider Market Volatility**: Long chains may not execute fully in low-volatility markets

## Security & Safety

✅ **Validated Changes**: All config updates are atomic (no data loss)
✅ **Fail-Safe**: If anything goes wrong, system logs error and continues
✅ **No Auto-Enable Loops**: Circular references detected and blocked
✅ **No Partial Fill Activation**: Only full fills trigger linked orders
✅ **Comprehensive Logging**: All activations logged for audit trail

## Technical Details

### Files Modified
- `config.py` - Added linked_order_id field
- `ttslo.py` - Activation logic
- `validator.py` - Validation logic
- `notifications.py` - Notification method

### Key Methods
- `ttslo.activate_linked_order_if_needed(config_id, order_info)`
- `validator._validate_linked_order_ids(configs, result)`
- `notifications.notify_linked_order_activated(parent_id, linked_id, parent_pair, linked_pair)`

### State Changes
When linked order activates:
1. Config CSV: `enabled` field changed from 'false' to 'true'
2. Logs CSV: Activation logged with timestamp
3. Telegram: Notification sent to configured users

## Future Enhancements

Potential future additions (not implemented):
- Dashboard visualization showing chain relationships
- CSV editor dropdown for selecting linked orders
- Chain execution history/statistics
- Conditional chains (activate only if profit threshold met)

## Questions?

See full documentation in README.md and LEARNINGS.md, or run the demo:
```bash
uv run python demos/demo_chained_orders.py
```
