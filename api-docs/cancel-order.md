# Cancel Order - Kraken API Documentation

**Endpoint:** `POST https://api.kraken.com/0/private/CancelOrder`

**Description:** Cancel a particular open order (or set of open orders) by `txid`, `userref` or `cl_ord_id`

**API Key Permissions Required:** `Orders and trades - Create & modify orders` or `Orders and trades - Cancel & close orders`

## Request Parameters

### Required Parameters

- **nonce** (integer<int64>): Nonce used in construction of `API-Sign` header

### Order Identification (at least one required)

- **txid** (string or integer): Kraken order identifier (txid) or user reference (userref)
  - Can be either:
    - string: Transaction ID
    - integer: User reference
- **cl_ord_id** (string): An alphanumeric client order identifier which uniquely identifies an open order for each client

## Response

### Success Response (200)

```json
{
  "error": [],
  "result": {
    "count": 1,
    "pending": false
  }
}
```

**Fields:**
- **result.count** (integer<int32>): Number of orders cancelled
- **result.pending** (boolean): If true, orders are pending cancellation
- **error**: Array of error messages (empty on success)

## Authentication

Requires API-Key and API-Sign headers for authentication.

## Example Request

```bash
curl -L 'https://api.kraken.com/0/private/CancelOrder' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H 'API-Key: <API-Key>' \
  -H 'API-Sign: <API-Sign>' \
  -d '{
    "nonce": 1695828490,
    "pair": "XBTUSD",
    "txid": "OHYO67-6LP66-HMQ437"
  }'
```

## Source

Downloaded from: https://docs.kraken.com/api/docs/rest-api/cancel-order
Date: 2025-10-14
