# Financially Responsible Order Validation

This document describes the new validation logic that prevents users from creating orders that could result in buying high and selling low.

## Overview

The TTSLO system now includes validation to protect against financially irresponsible orders. This validation ensures that:

- **Buy orders** are configured to buy when the price goes DOWN (buying low)
- **Sell orders** are configured to sell when the price goes UP (selling high)

This prevents accidental mistakes that could lead to financial loss.

## How It Works

### Valid Configurations

For stablecoin and BTC pairs, only these combinations are allowed:

✅ **Buy Low**: `threshold_type="below"` + `direction="buy"`
- Example: Buy BTC when price goes below $40,000
- Reasoning: Following the price down to buy at a lower price

✅ **Sell High**: `threshold_type="above"` + `direction="sell"`
- Example: Sell BTC when price goes above $60,000
- Reasoning: Following the price up to sell at a higher price

### Invalid Configurations (Blocked)

These combinations will generate an **ERROR** and prevent the order:

❌ **Buy High**: `threshold_type="above"` + `direction="buy"`
- This would buy when price goes UP, resulting in buying at a higher price
- Error message: "Financially irresponsible order: Buying HIGH is not allowed..."

❌ **Sell Low**: `threshold_type="below"` + `direction="sell"`
- This would sell when price goes DOWN, resulting in selling at a lower price
- Error message: "Financially irresponsible order: Selling LOW is not allowed..."

## Which Pairs Are Validated?

### Stablecoin Pairs (Validated ✓)

Pairs trading against stablecoins or fiat currencies:
- **USD variants**: USD, ZUSD, USDT (Tether), USDC (USD Coin)
- **Euro**: EUR, ZEUR
- **British Pound**: GBP, ZGBP
- **Japanese Yen**: JPY, ZJPY

Examples:
- `XXBTZUSD` - Bitcoin to USD
- `ETHUSDT` - Ethereum to Tether
- `SOLEUR` - Solana to Euro
- `ADAGBP` - Cardano to British Pound

### BTC Pairs (Validated ✓)

Pairs trading other cryptocurrencies against Bitcoin:
- `XETHXXBT` - Ethereum to Bitcoin
- `SOLXXBT` - Solana to Bitcoin
- `ADAXXBT` - Cardano to Bitcoin

**Note**: For these pairs, Bitcoin is treated as a stablecoin/reference currency. The same buy low/sell high rules apply.

### Exotic Pairs (NOT Validated ⊘)

Pairs trading one cryptocurrency against another (excluding BTC):
- `SOLETH` - Solana to Ethereum
- `ADAETH` - Cardano to Ethereum

These pairs are **not** subject to financial validation, as users may have specific trading strategies for these exotic pairs.

## Where Is Validation Enforced?

### 1. CSV Editor

When editing the CSV configuration file using the TUI editor (`csv_editor.py`):

```bash
uv run python csv_editor.py config.csv
```

The editor will block you from:
- Changing `threshold_type` to create an invalid combination
- Changing `direction` to create an invalid combination

You'll see a clear error message explaining why the combination is not allowed.

### 2. Configuration Validation

When validating your configuration file:

```bash
uv run ttslo.py --validate-config
```

The validator will report errors for any financially irresponsible orders.

### 3. Runtime

When the TTSLO service loads the configuration, it will refuse to process orders with financially irresponsible configurations.

## Error Messages

When you try to create an invalid order, you'll see one of these error messages:

### Buy High Error

```
❌ Financially irresponsible: Buying HIGH is not allowed.
Buy orders should use threshold_type='below' to buy when price goes DOWN (buy low).
```

### Sell Low Error

```
❌ Financially irresponsible: Selling LOW is not allowed.
Sell orders should use threshold_type='above' to sell when price goes UP (sell high).
```

## Examples

### Example 1: Valid BTC Buy Order

```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_buy,XXBTZUSD,40000,below,buy,0.01,5.0,true
```

✅ **Valid**: This will buy BTC when the price drops below $40,000 (buying low)

### Example 2: Valid ETH Sell Order

```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
eth_sell,ETHUSDT,3500,above,sell,0.1,3.0,true
```

✅ **Valid**: This will sell ETH when the price rises above $3,500 (selling high)

### Example 3: Invalid BTC Buy Order

```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_buy_bad,XXBTZUSD,60000,above,buy,0.01,5.0,true
```

❌ **Invalid**: This would buy BTC when the price rises above $60,000 (buying high)
- **Error**: Financially irresponsible order: Buying HIGH is not allowed...

### Example 4: Invalid SOL Sell Order

```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
sol_sell_bad,SOLEUR,100,below,sell,10,5.0,true
```

❌ **Invalid**: This would sell SOL when the price drops below €100 (selling low)
- **Error**: Financially irresponsible order: Selling LOW is not allowed...

## Testing

To see the validation in action, run the demo script:

```bash
uv run python demo_financial_validation.py
```

This will show examples of valid and invalid configurations with explanations.

## Why This Matters

This validation protects you from:

1. **Accidental mistakes**: Confusing "above" and "below" when setting up orders
2. **Financial loss**: Buying at higher prices or selling at lower prices
3. **Logic errors**: Setting up orders that work opposite to your intention

The validation is particularly important for:
- Users new to trading or the TTSLO system
- Complex configurations with multiple orders
- Quickly setting up orders under time pressure

## Disabling Validation

The validation is **always enabled** for stablecoin and BTC pairs. This is a safety feature that cannot be disabled.

If you have a specific use case that requires an unusual configuration:
- Consider using exotic cryptocurrency pairs (which are not validated)
- Or manually place orders through the Kraken web interface

## See Also

- [validation-rules.md](validation-rules.md) - Complete validation rules documentation
- [test_financial_validation.py](test_financial_validation.py) - Unit tests
- [demo_financial_validation.py](demo_financial_validation.py) - Demo script
