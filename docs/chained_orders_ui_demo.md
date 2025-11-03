# Chained Orders UI Demo

## Dashboard Display

### Example: Buy Low → Sell High Chain

**Parent Order (Enabled, Monitoring):**
```
┌─────────────────────────────────────────────────┐
│ btc_buy                         XXBTZUSD        │
├─────────────────────────────────────────────────┤
│ Threshold: $100,000 (below)                     │
│ Current: $105,000                               │
│ Direction: Buy 0.01 BTC with 500 ZUSD          │
│ Volume: 0.01                                    │
│ Trailing Offset: 2.0%                           │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ 🔗 Linked Order: btc_sell ○                     │
│    ↑ Gray circle = Will enable when this fills  │
├─────────────────────────────────────────────────┤
│ [Cancel] [Force]                                │
└─────────────────────────────────────────────────┘
```

**Linked Order (Disabled, Waiting):**
```
(Not shown in pending orders - disabled)
Will appear after btc_buy fills
```

### Status Indicators

| Icon | Color | Meaning | When Shown |
|------|-------|---------|------------|
| ○ | Gray | Linked order disabled, will enable on fill | Most common for chained orders |
| ✓ | Green | Linked order already enabled | Manual override or already activated |
| ⚠️ | Red | Linked order not found in config | Configuration error |

### After Parent Order Fills

**Parent Order:**
```
(Moves to "Completed Orders" section)
```

**Linked Order (Now Enabled):**
```
┌─────────────────────────────────────────────────┐
│ btc_sell                        XXBTZUSD        │
├─────────────────────────────────────────────────┤
│ Threshold: $120,000 (above)                     │
│ Current: $105,000                               │
│ Direction: Sell 0.01 BTC for 1,050 ZUSD        │
│ Volume: 0.01                                    │
│ Trailing Offset: 2.0%                           │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ (No linked order)                               │
├─────────────────────────────────────────────────┤
│ [Cancel] [Force]                                │
└─────────────────────────────────────────────────┘
```

## CSV Editor Display

### Editing Config with Linked Orders

```
┌──────────────┬──────────┬────────────┬───────┬─────────────┐
│ id           │ pair     │ enabled    │ ...   │ linked_id   │
├──────────────┼──────────┼────────────┼───────┼─────────────┤
│ btc_buy      │ XXBTZUSD │ true       │ ...   │ btc_sell    │
│ btc_sell     │ XXBTZUSD │ false      │ ...   │             │
└──────────────┴──────────┴────────────┴───────┴─────────────┘
```

### Validation Examples

**Valid:**
```
linked_order_id: btc_sell
✓ Valid (order exists in config)
```

**Invalid - Missing Order:**
```
linked_order_id: nonexistent
✗ Linked order 'nonexistent' not found in config
```

**Invalid - Self Reference:**
```
id: btc_buy
linked_order_id: btc_buy
✗ Cannot link order to itself
```

## Multi-Order Chain Example

### 4-Step Chain

```
Step 1: Buy BTC at $100k
┌─────────────────────────────┐
│ buy_1 🔗→ sell_1 ○          │
│ Buy at $100k                │
└─────────────────────────────┘

Step 2: Sell BTC at $105k (5% profit)
┌─────────────────────────────┐
│ sell_1 🔗→ buy_2 ○          │
│ Sell at $105k               │
└─────────────────────────────┘

Step 3: Buy BTC at $103k (wait for dip)
┌─────────────────────────────┐
│ buy_2 🔗→ sell_2 ○          │
│ Buy at $103k                │
└─────────────────────────────┘

Step 4: Sell BTC at $108k (5% profit)
┌─────────────────────────────┐
│ sell_2 (no link)            │
│ Sell at $108k               │
└─────────────────────────────┘
```

## Tooltips

Hover over status indicators for explanations:

- **○ (Gray Circle):** "Linked order disabled (will enable when this order fills)"
- **✓ (Green Check):** "Linked order is enabled"
- **⚠️ (Red Warning):** "Linked order not found in config"

## Benefits

1. **Visual Clarity:** Instantly see order relationships
2. **Status at a Glance:** Color-coded indicators show state
3. **Safe Editing:** CSV editor prevents invalid configurations
4. **User Confidence:** Know exactly what will happen next
