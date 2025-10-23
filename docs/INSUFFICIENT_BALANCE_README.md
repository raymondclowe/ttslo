# Insufficient Balance Quality Control

## Overview

This feature adds quality control checks to prevent order creation when there is insufficient balance, and sends Telegram notifications when such situations occur.

## Problem Statement

Previously, when a trigger price was reached, the system would attempt to create an order on Kraken without checking if there was sufficient balance. This could lead to:
1. Orders failing on Kraken's side with no immediate notification
2. Silent failures that required manual log review to discover
3. Uncertainty about whether balance issues would be caught and reported

## Solution

The system now implements a two-layer defense:

### Layer 1: Pre-flight Balance Check (Before API Call)

Before sending an order to Kraken, the system:
1. Queries the account balance via `get_balance()` API
2. Normalizes asset keys to handle both spot and funding wallets
3. Sums up all matching balances (e.g., XXBT + XBT.F)
4. Compares available balance to required volume
5. If insufficient, blocks the order and sends a notification

**Benefits:**
- Prevents unnecessary API calls to Kraken
- Provides immediate feedback via Telegram
- Reduces API rate limit usage
- Gives detailed balance information for debugging

### Layer 2: Kraken API Error Handling

If an order passes the pre-flight check but Kraken still rejects it (e.g., due to race conditions, trading fees, or margin requirements), the system:
1. Catches the exception from Kraken API
2. Checks if the error is balance-related
3. Sends a notification via Telegram
4. Logs the full error for debugging

## Balance Checking Details

### Wallet Handling

Kraken has multiple wallet types:
- **Spot Wallet**: Asset keys like `XXBT`, `XETH`
- **Funding Wallet**: Asset keys like `XBT.F`, `ETH.F`

The balance checker:
1. Looks for all variations of an asset
2. Strips the `.F` suffix from funding wallet keys
3. Normalizes asset names (removes leading X/Z characters)
4. Sums all matching balances

Example:
```python
Balance from Kraken:
{
    'XXBT': '0.5',      # Spot wallet
    'XBT.F': '0.6'      # Funding wallet
}

Normalized and summed:
'BT' -> 1.1 BTC total available
```

### Asset Normalization

The `_normalize_asset()` method handles Kraken's asset naming conventions:
- `XXBT` → `BT` (strips leading X)
- `XBT.F` → `BT` (removes .F suffix and leading X)
- `XETH` → `ETH`
- `ZUSD` → `USD`

### Trading Pair Parsing

The `_extract_base_asset()` method extracts the base asset from trading pairs:
- `XXBTZUSD` → `XXBT` (Bitcoin)
- `XETHZUSD` → `XETH` (Ethereum)
- `SOLUSDT` → `SOL` (Solana)

## Notifications

Two new notification event types have been added:

### 1. Insufficient Balance (`notify.insufficient_balance`)

Sent when balance check fails before order creation.

**Message Format:**
```
⚠️ TTSLO: Cannot create order - Insufficient balance!

Config: btc_sell_1
Pair: XXBTZUSD
Direction: sell
Required Volume: 1.0
Available Balance: 0.8
Trigger Price: 50000.0

⚠️ Action needed: Add funds to your account or adjust the order volume.
```

### 2. Order Failed (`notify.order_failed`)

Sent when Kraken API rejects the order.

**Message Format:**
```
❌ TTSLO: Order creation failed!

Config: btc_sell_1
Pair: XXBTZUSD
Direction: sell
Volume: 1.0
Trigger Price: 50000.0

Error: Kraken API error: Insufficient funds

⚠️ Please check your account balance and configuration.
```

## Configuration

### notifications.ini

Add recipients to the new event types:

```ini
[recipients]
alice = 123456789
bob = 987654321

[notify.insufficient_balance]
# Notified when an order cannot be created due to insufficient balance
users = alice, bob

[notify.order_failed]
# Notified when an order fails to be created on Kraken
users = alice
```

### Environment Variables

Ensure your Telegram bot token is set:
```bash
export TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Logging

All balance checks and order creation attempts are logged:

### Successful Balance Check
```
[2025-10-18 03:55:00] INFO: Balance check passed: Sufficient XXBT balance: 1.5 (Contributors: XXBT=1.0, XBT.F=0.5) >= required 0.5
```

### Insufficient Balance
```
[2025-10-18 03:55:00] ERROR: Cannot create TSL order: Insufficient XXBT balance: 0.3 (Contributors: XXBT=0.1, XBT.F=0.2) < required 0.5
```

### Kraken API Error
```
[2025-10-18 03:55:00] ERROR: Exception creating TSL order: Kraken API error: Insufficient funds
```

## Testing

### Running Tests

```bash
# Run all balance-related tests
uv run pytest tests/test_insufficient_balance.py -v

# Run notification tests
uv run pytest tests/test_notifications.py -v

# Run all tests
uv run pytest -v
```

### Test Coverage

The feature includes comprehensive tests:
- Balance checking with spot wallet only
- Balance checking with funding wallet only
- Balance checking with both wallets
- Insufficient balance detection
- Order blocking on insufficient balance
- Order success with sufficient balance
- Kraken API error handling
- Buy order balance check skipping
- Asset normalization
- Base asset extraction
- Notification delivery

## FAQs

### Q: Why are buy orders not balance-checked?

**A:** Checking balance for buy orders is more complex because it requires knowing the quote currency balance (e.g., USD) and the current price to calculate the total cost. The current implementation focuses on sell orders where balance checking is straightforward.

### Q: What if I have balance but it's locked in open orders?

**A:** The balance check uses Kraken's `Balance` endpoint which returns your available balance (not including funds locked in open orders). If you have insufficient available balance, you'll need to cancel some orders or add more funds.

### Q: Will this affect my existing configurations?

**A:** No, existing configurations will continue to work. The balance check is an additional safety feature that runs before order creation. If you have sufficient balance, orders will be created as before.

### Q: What if the balance check passes but Kraken still rejects the order?

**A:** This can happen in rare cases (e.g., trading fees, margin requirements). The second layer of defense catches these errors and sends a notification via `notify.order_failed`.

### Q: Can I disable balance checking?

**A:** No, balance checking is a critical safety feature that runs automatically. However, if you're running in dry-run mode (`--dry-run`), no actual balance checks or order creation occur.

## Implementation Details

### Code Changes

**ttslo.py:**
- `_normalize_asset()`: Normalizes asset keys
- `_extract_base_asset()`: Extracts base asset from trading pair
- `check_sufficient_balance()`: Main balance checking logic
- `create_tsl_order()`: Modified to include balance check before API call

**notifications.py:**
- `notify_insufficient_balance()`: Sends insufficient balance notification
- `notify_order_failed()`: Sends order failure notification

### Performance Impact

The balance check adds one additional API call (`get_balance()`) before order creation. This is a negligible performance impact since:
1. Orders are created infrequently (only when triggers are reached)
2. The `get_balance()` call is fast (typically <200ms)
3. It prevents unnecessary order creation attempts that would fail anyway
4. It reduces overall API usage by catching issues early

## Future Enhancements

Potential improvements for future versions:
1. Add balance checking for buy orders (requires price calculation)
2. Cache balance data with TTL to reduce API calls
3. Add configurable balance margin/buffer
4. Support for margin trading balance checks
5. Balance history tracking and alerting

## Support

For issues or questions:
1. Check the logs in `logs.csv` for detailed error messages
2. Verify your `notifications.ini` is configured correctly
3. Ensure your Telegram bot token is set
4. Run tests to verify your setup: `uv run pytest -v`
