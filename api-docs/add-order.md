# Add Order - Kraken API Documentation

**Endpoint:** `POST https://api.kraken.com/0/private/AddOrder`

**Description:** Place a new order.

**API Key Permissions Required:** `Orders and trades - Create & modify orders`

## Request Parameters

### Required Parameters

- **nonce** (integer<int64>): Nonce used in construction of `API-Sign` header
- **ordertype** (string): The execution model of the order
  - Possible values: `market`, `limit`, `iceberg`, `stop-loss`, `take-profit`, `stop-loss-limit`, `take-profit-limit`, `trailing-stop`, `trailing-stop-limit`, `settle-position`
  - Example: `limit`
- **type** (string): Order direction (buy/sell)
  - Possible values: `buy`, `sell`
- **volume** (string): Order quantity in terms of the base asset
  - Example: `1.25`
  - Note: Volume can be specified as `0` for closing margin orders to automatically fill the requisite quantity
- **pair** (string): Asset pair `id` or `altname`
  - Example: `XBTUSD`

### Optional Parameters

- **userref** (integer<int32>): Optional non-unique, numeric identifier which can be associated with a number of orders by the client. This field is mutually exclusive with `cl_ord_id` parameter.
- **cl_ord_id** (string): Alphanumeric client order identifier which uniquely identifies an open order for each client. This field is mutually exclusive with `userref` parameter.
  - Formats:
    - Long UUID: `6d1b345e-2821-40e2-ad83-4ecb18a06876` (32 hex characters separated with 4 dashes)
    - Short UUID: `da8e4ad59b78481c93e589746b0cf91f` (32 hex characters with no dashes)
    - Free text: `arb-20240509-00010` (Free format ascii text up to 18 characters)
- **displayvol** (string): For `iceberg` orders only, defines the quantity to show in the book while the rest of order quantity remains hidden. Minimum value is 1/15 of `volume`.
- **asset_class** (string): Required on requests for non-crypto pairs (use `tokenized_asset` for xstocks)
  - Possible values: `tokenized_asset`
- **price** (string): Price
  - Limit price for `limit` and `iceberg` orders
  - Trigger price for `stop-loss`, `stop-loss-limit`, `take-profit`, `take-profit-limit`, `trailing-stop` and `trailing-stop-limit` orders
  - Example: `40000.0`
  - Notes:
    - Relative Prices: Either `price` or `price2` can be preceded by `+`, `-`, or `#` to specify the order price as an offset relative to the last traded price
    - Trailing Stops: Must use a relative price for this field, namely the `+` prefix, from which the direction will be automatic based on if the original order is a buy or sell
    - The `%` suffix works for these order types to use a relative percentage price
- **price2** (string): Secondary Price
  - Limit price for `stop-loss-limit`, `take-profit-limit` and `trailing-stop-limit` orders
  - Trailing Stops: Must use a relative price for this field, namely one of the `+` or `-` prefixes
- **trigger** (string): Price signal used to trigger stop/take-profit orders
  - Possible values: `index`, `last`
  - Default value: `last`
- **leverage** (string): Amount of leverage desired (default: none)
  - Example: `5`
- **reduce_only** (boolean): If `true`, order will only reduce a currently open position, not increase it or open a new position
  - Default value: `false`
- **stptype** (string): Self Trade Prevention (STP) mode
  - Possible values: `cancel-newest`, `cancel-oldest`, `cancel-both`
  - Default value: `cancel-newest`
- **oflags** (string): Comma delimited list of order flags
  - `post`: post-only order (available when ordertype = limit)
  - `fcib`: prefer fee in base currency (default if selling)
  - `fciq`: prefer fee in quote currency (default if buying, mutually exclusive with `fcib`)
  - `nompp`: disable market price protection for market orders
  - `viqc`: order volume expressed in quote currency (supported only for buy market orders)
- **timeinforce** (string): Time-in-force of the order
  - Possible values: `GTC`, `IOC`, `GTD`
  - Default value: `GTC`
- **starttm** (string): Scheduled start time
  - `0`: now (default)
  - `<n>`: unix timestamp of start time
  - `+<n>`: schedule start time `<n>` seconds from now
- **expiretm** (string): Expiry time (for GTD orders)
  - `0`: no expiration (default)
  - `<n>`: unix timestamp of expiration time
  - `+<n>`: expire `<n>` seconds from now, minimum 5 seconds
- **close[ordertype]** (string): Conditional close order type
  - Possible values: `limit`, `iceberg`, `stop-loss`, `take-profit`, `stop-loss-limit`, `take-profit-limit`, `trailing-stop`, `trailing-stop-limit`
- **close[price]** (string): Conditional close order `price`
- **close[price2]** (string): Conditional close order `price2`
- **deadline** (string): RFC3339 timestamp after which the matching engine should reject the new order request
- **validate** (boolean): If set to `true` the order will be validated only, it will not trade in the matching engine
  - Default value: `false`

## Response

### Success Response (200)

```json
{
  "error": [],
  "result": {
    "descr": {
      "order": "buy 2.12340000 XBTUSD @ limit 25000.1 with 2:1 leverage",
      "close": "close position @ stop loss 22000.0 -> limit 21000.0"
    },
    "txid": [
      "OUF4EM-FRGI2-MQMWZD"
    ]
  }
}
```

**Fields:**
- **result.descr**: Object containing order description info
  - **order**: Order description
  - **close**: Conditional close order description, if applicable
- **result.txid**: Array of transaction IDs for order (if order was added successfully)
- **error**: Array of error messages (empty on success)

## Authentication

Requires API-Key and API-Sign headers for authentication.

## Important Notes for Trailing Stop Orders

For `trailing-stop` orders:
- **ordertype** must be set to `trailing-stop`
- **price** or a trailing offset parameter must be specified
- The trigger price is relative using the `+` prefix
- Direction is automatic based on buy or sell
- The `%` suffix can be used for relative percentage prices

## Source

Downloaded from: https://docs.kraken.com/api/docs/rest-api/add-order
Date: 2025-10-14
