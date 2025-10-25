# Dashboard Cancel Buttons - Visual Guide

## Overview
This document shows the visual changes made to the TTSLO Dashboard to support cancel functionality.

## 1. Pending Orders Pane - Cancel Button

Each pending order card now has a **red "Cancel" button** at the bottom:

```
┌────────────────────────────────────────┐
│ test_1                      XXBTZUSD   │
├────────────────────────────────────────┤
│ Threshold: $50000 (above)              │
│ Current: $48500                        │
│ Direction: sell                        │
│ Volume: 0.01                           │
│ Trailing Offset: 5.00%                 │
├────────────────────────────────────────┤
│ ▓▓▓▓▓▓▓▓▓░░░░░ 60% 3.09%              │
│ $1500 below threshold                  │
├────────────────────────────────────────┤
│ [ Cancel ] <-- RED BUTTON              │
└────────────────────────────────────────┘
```

**Action**: Sets `enabled` field to "canceled" in config.csv

**Confirmation**: User must confirm before canceling

## 2. Active Orders Pane - Cancel Order Button

Each active order card now has a **red "Cancel Order" button**:

```
┌────────────────────────────────────────┐
│ test_1                      XXBTZUSD   │
├────────────────────────────────────────┤
│ Order ID: OIZXVF-N5TQ5...              │
│ Trigger Price: $50123.45               │
│ Volume: 0.01                           │
│ Status: open                           │
│ Trailing Offset: 5.00%                 │
│ Triggered: 10/25/2025, 2:15:09 AM      │
├────────────────────────────────────────┤
│ [ Cancel Order ] <-- RED BUTTON        │
└────────────────────────────────────────┘
```

**Action**: Cancels the live order on Kraken immediately

**Confirmation**: User must confirm before canceling

## 3. Cancel All Button - Bottom of Dashboard

At the bottom of the dashboard, below all panes, there's a **large red "Cancel All" button**:

```
┌──────────────────────────────────────────┐
│                                          │
│   🛑 Cancel All Active Orders            │
│                                          │
│   This will immediately cancel all       │
│   open orders on Kraken                  │
│                                          │
└──────────────────────────────────────────┘
```

**Action**: Cancels ALL open orders on Kraken

**Confirmation**: Double confirmation (two dialogs) before executing

## Visual Design

### Colors
- **Red buttons** (`#e74c3c`) - Indicates destructive action
- **Darker red on hover** (`#c0392b`) - Visual feedback
- **Even darker on click** (`#a93226`) - Pressed state

### Button Sizes
- **Small buttons** on cards - `padding: 4px 10px; font-size: 12px`
- **Large Cancel All button** - `padding: 12px 24px; font-size: 16px`

### Layout
- Buttons appear below order details
- Clear separation with spacing
- Centered Cancel All button

## User Flow

### Canceling a Pending Order
1. User clicks red "Cancel" button on pending order card
2. Confirmation dialog appears: "Cancel pending order test_1?"
3. User clicks OK
4. Config file updated (enabled = "canceled")
5. Success message shown
6. Dashboard refreshes automatically

### Canceling an Active Order
1. User clicks red "Cancel Order" button on active order card
2. Confirmation dialog appears: "Cancel active order OIZXVF...?"
3. User clicks OK
4. Kraken API called to cancel order
5. Success message shown
6. Dashboard refreshes automatically

### Canceling All Orders
1. User clicks large red "🛑 Cancel All Active Orders" button
2. First confirmation: "WARNING: Cancel ALL active orders?"
3. User clicks OK
4. Second confirmation: "Are you absolutely sure?"
5. User clicks OK
6. All open orders canceled on Kraken
7. Summary shown (e.g., "Successfully canceled 3 orders")
8. Dashboard refreshes automatically

## Error Handling

### Kraken API Unavailable
- Button click shows: "Error: Kraken API not available"
- Order remains unchanged

### Order Already Canceled
- Kraken returns error
- User sees: "Error canceling order: [Kraken error message]"

### Partial Failure (Cancel All)
- Some orders canceled, some failed
- User sees: "Canceled 2 orders, but 1 failed: [error details]"

## Technical Details

### Endpoints
- `POST /api/pending/<id>/cancel` - Cancel pending order
- `POST /api/active/<order_id>/cancel` - Cancel active order
- `POST /api/cancel-all` - Cancel all orders

### Request Format
```json
// Pending cancel
POST /api/pending/test_1/cancel
{
  "status": "canceled"  // or "paused", "false"
}

// Active cancel
POST /api/active/ORDER123/cancel
(no body)

// Cancel all
POST /api/cancel-all
(no body)
```

### Response Format
```json
// Success
{
  "success": true,
  "config_id": "test_1",
  "new_status": "canceled"
}

// Error
{
  "success": false,
  "error": "Config ID not found"
}
```

## Testing

All functionality is covered by automated tests:
- 13 new tests in `tests/test_dashboard_cancel.py`
- Tests cover success, errors, edge cases
- All tests passing

## Configuration

The `enabled` field in config.csv now supports:
- `true` - Active, will trigger
- `false` - Disabled permanently
- `paused` - Temporarily disabled
- `canceled` - Canceled by user

This allows future enhancements like re-enabling paused orders.
