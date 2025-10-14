# Get Trade Balance - Kraken API Documentation

**Endpoint:** `POST https://api.kraken.com/0/private/TradeBalance`

**Description:** Retrieve a summary of collateral balances, margin position valuations, equity and margin level.

**API Key Permissions Required:** `Query funds` or `Query open orders & trades`

## Request Parameters

### Required Parameters

- **nonce** (integer<int64>): Nonce used in construction of `API-Sign` header

### Optional Parameters

- **asset** (string): Base asset used to determine balance (default: `ZUSD`)
  - Example: `ZUSD`, `XXBT`, `XETH`
- **rebase_multiplier** (string, nullable): Optional parameter to view xstocks data
  - Possible values: `rebased` (default), `base`

## Response

### Success Response (200)

```json
{
  "error": [],
  "result": {
    "eb": "1234.5678",
    "tb": "1234.5678",
    "m": "0.0000",
    "n": "0.0000",
    "c": "0.0000",
    "v": "0.0000",
    "e": "1234.5678",
    "mf": "1234.5678",
    "ml": "100.00",
    "uv": "0.0000"
  }
}
```

**Response Fields:**

- **eb** (string): Equivalent balance (combined balance of all currencies)
- **tb** (string): Trade balance (combined balance of all equity currencies)
- **m** (string): Margin amount of open positions
- **n** (string): Unrealized net profit/loss of open positions
- **c** (string): Cost basis of open positions
- **v** (string): Current floating valuation of open positions
- **e** (string): Equity = trade balance + unrealized net profit/loss
- **mf** (string): Free margin = equity - initial margin (maximum margin available to open new positions)
- **ml** (string): Margin level = (equity / initial margin) * 100
- **uv** (string): Unexecuted value (value of unfilled and partially filled orders)
- **error** (array): Array of error messages (empty on success)

## Authentication

Requires API-Key and API-Sign headers for authentication.

## Use Cases

1. **Balance Verification**: Check available funds before placing orders
2. **Margin Monitoring**: Monitor margin levels to avoid liquidation
3. **Position Management**: Track unrealized P&L of open positions
4. **Risk Management**: Calculate free margin for new positions

## Important Notes

- The **mf** (free margin) field indicates how much margin is available for new positions
- Monitor **ml** (margin level) to ensure it stays above liquidation thresholds
- The **eb** (equivalent balance) includes all currencies converted to the base asset
- Default base asset is ZUSD (US Dollar) if not specified

## Example Request

```bash
curl -L 'https://api.kraken.com/0/private/TradeBalance' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H 'API-Key: <API-Key>' \
  -H 'API-Sign: <API-Sign>' \
  -d '{
    "nonce": 1695828490,
    "asset": "ZUSD"
  }'
```

## Related Endpoints

- **Get Account Balance** - `/0/private/Balance` - Get raw balances of individual assets
- **Get Open Positions** - `/0/private/OpenPositions` - Get details of open margin positions
- **Get Trade Volume** - `/0/private/TradeVolume` - Get trading volume and fees

## Source

Documentation based on:
- https://docs.kraken.com/api/docs/rest-api/get-trade-balance
- https://docs.kraken.com/api/docs/rest-api/get-account-balance

Downloaded: 2025-10-14
