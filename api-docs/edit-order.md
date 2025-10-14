# Edit Order - Kraken API Documentation

**Endpoint:** `POST https://api.kraken.com/0/private/EditOrder`

**Description:** Sends a request to edit the order parameters of a live order. When an order has been successfully modified, the original order will be cancelled and a new order will be created with the adjusted parameters and a new `txid` will be returned in the response.

**API Key Permissions Required:** `Orders and trades - Create & modify orders`

## Important Notes

- The new `AmendOrder` endpoint is recommended as it resolves caveats and has additional performance gains
- Triggered stop loss or take profit orders are not supported
- This endpoint cancels the original order and creates a new one

## Request Parameters

The EditOrder endpoint accepts parameters to identify the order to edit and the new parameters for the order.

### Required Parameters

- **nonce** (integer<int64>): Nonce used in construction of `API-Sign` header
- **txid** (string): Transaction ID of the order to edit
- **pair** (string): Asset pair

### Optional Parameters (to modify)

Parameters that can be modified (similar to AddOrder):
- **volume** (string): New order volume
- **price** (string): New order price
- **price2** (string): New secondary price
- **ordertype** (string): Order type
- **userref** (integer): User reference ID

## Response

### Success Response (200)

Returns information about the cancelled original order and the new replacement order.

**Fields:**
- **result**: Object containing order modification info
  - **txid**: New transaction ID for the modified order
  - **originaltxid**: Original transaction ID that was cancelled
  - **volume**: New volume
  - **price**: New price
  - **descr**: Order description
- **error**: Array of error messages (empty on success)

## Authentication

Requires API-Key and API-Sign headers for authentication.

## Limitations

- Cannot edit triggered stop-loss or take-profit orders
- The order is cancelled and recreated (not modified in place)
- Consider using the newer AmendOrder endpoint for better performance

## Source

Downloaded from: https://docs.kraken.com/api/docs/rest-api/edit-order
Date: 2025-10-14

## Note

This is a summary based on the official Kraken API documentation. The EditOrder endpoint is being superseded by the AmendOrder endpoint for better functionality.
