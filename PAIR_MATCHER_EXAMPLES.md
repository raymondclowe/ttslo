# Visual Examples - Pair Matcher in CSV Editor

## Example 1: User Types "BTC/USD"

### Input:
```
User opens CSV editor and edits the "pair" field
User types: BTC/USD
User presses Enter
```

### What Happens:
```
┌─────────────────────────────────────────────────┐
│ Edit Cell Value: pair                          │
│ ┌─────────────────────────────────────────────┐ │
│ │ BTC/USD                                      │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ✓ Resolved to: XXBTZUSD                        │
│                                                 │
│ [Save]  [Cancel]                                │
└─────────────────────────────────────────────────┘
```

### Result in CSV:
```csv
id,pair,threshold_price,threshold_type,direction,volume,enabled
btc_1,XXBTZUSD,50000,above,sell,0.01000000,true
```

## Example 2: User Types "eth/usdt" (lowercase)

### Input:
```
User types: eth/usdt
```

### What Happens:
```
┌─────────────────────────────────────────────────┐
│ Edit Cell Value: pair                          │
│ ┌─────────────────────────────────────────────┐ │
│ │ eth/usdt                                     │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ✓ Resolved to: ETHUSDT                         │
│                                                 │
│ [Save]  [Cancel]                                │
└─────────────────────────────────────────────────┘
```

### Result in CSV:
```csv
id,pair,threshold_price,threshold_type,direction,volume,enabled
eth_1,ETHUSDT,3000,above,sell,0.10000000,true
```

## Example 3: User Types Official Code "XXBTZUSD"

### Input:
```
User types: XXBTZUSD
```

### What Happens:
```
┌─────────────────────────────────────────────────┐
│ Edit Cell Value: pair                          │
│ ┌─────────────────────────────────────────────┐ │
│ │ XXBTZUSD                                     │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│                                                 │
│                                                 │
│ [Save]  [Cancel]                                │
└─────────────────────────────────────────────────┘
```

No resolution needed - already the official code!

### Result in CSV:
```csv
id,pair,threshold_price,threshold_type,direction,volume,enabled
btc_1,XXBTZUSD,50000,above,sell,0.01000000,true
```

## Example 4: Invalid Pair

### Input:
```
User types: NOTAREALPAIR
```

### What Happens:
```
┌─────────────────────────────────────────────────┐
│ Edit Cell Value: pair                          │
│ ┌─────────────────────────────────────────────┐ │
│ │ NOTAREALPAIR                                 │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ Unknown trading pair: 'NOTAREALPAIR'.          │
│ Try formats like BTC/USD, ETH/USDT, or use     │
│ official Kraken codes.                          │
│                                                 │
│ [Save]  [Cancel]                                │
└─────────────────────────────────────────────────┘
```

Save button would be disabled or show error.

## Example 5: Common Input Formats (All Work!)

All these inputs resolve to **XXBTZUSD**:

| Input Format | Description | Result |
|--------------|-------------|--------|
| `BTC/USD` | Slash separator | XXBTZUSD ✓ |
| `btc/usd` | Lowercase | XXBTZUSD ✓ |
| `BTCUSD` | No separator | XXBTZUSD ✓ |
| `BTC-USD` | Hyphen separator | XXBTZUSD ✓ |
| `btc usd` | Space separator | XXBTZUSD ✓ |
| `Btc/Usd` | Mixed case | XXBTZUSD ✓ |

## Example 6: Before and After

### Before (Without Pair Matcher):
```
User must know that Bitcoin/USD is: XXBTZUSD
User must know that Ethereum/USDT is: ETHUSDT
User must remember BTC = XBT in Kraken
❌ Difficult to remember and easy to make mistakes!
```

### After (With Pair Matcher):
```
User types natural names: BTC/USD, ETH/USDT, etc.
System automatically resolves to Kraken codes
Clear feedback shows what it resolved to
✓ Easy to use and prevents mistakes!
```

## Technical Flow

```
User Input              Pair Matcher              CSV Storage
─────────               ────────────              ───────────
                                                  
"BTC/USD"      ──>     [Normalize]        ──>   XXBTZUSD
                       ├─ Remove '/'
                       ├─ Convert to UPPER
                       └─ Replace BTC→XBT
                                                  
                       [Match Strategy]
                       ├─ Check exact match
                       ├─ Check altnames
                       ├─ Check normalized
                       └─ Fuzzy if needed
                                                  
                       [Return Result]
                       ├─ Pair: XXBTZUSD
                       ├─ Confidence: 100%
                       └─ Type: normalized
                                                  
                       [Display to User]
                       "✓ Resolved to: XXBTZUSD"
```

## Confidence Indicators

### High Confidence (90-100%)
```
✓ Resolved to: XXBTZUSD
```
**Meaning:** System is very confident this is correct
**Action:** Automatically saved to CSV

### Medium Confidence (70-89%)
```
⚠️ Fuzzy match: 'input' → 'XBTUSDT' (confidence: 75%)
Verify this is correct!
```
**Meaning:** System found a match but less certain
**Action:** User should verify before saving

### Low Confidence (<70%)
```
Unknown trading pair: 'input'
```
**Meaning:** System couldn't find a reasonable match
**Action:** Save is blocked, user must correct input

## Common Trading Pairs Reference

For quick reference when using the CSV editor:

| Human Input | Kraken Code | Kraken wsname |
|-------------|-------------|---------------|
| BTC/USD | XXBTZUSD | XBT/USD |
| BTC/EUR | XXBTZEUR | XBT/EUR |
| BTC/USDT | XBTUSDT | XBT/USDT |
| ETH/USD | XETHZUSD | ETH/USD |
| ETH/EUR | XETHZEUR | ETH/EUR |
| ETH/USDT | ETHUSDT | ETH/USDT |
| SOL/USD | SOLUSD | SOL/USD |
| ADA/USD | ADAUSD | ADA/USD |
| DOT/USD | DOTUSD | DOT/USD |
| LINK/USD | LINKUSD | LINK/USD |

All these pairs can be entered in any format:
- With or without separators
- Upper or lowercase
- Different separator types (/, -, _, space)
