# Understanding "Benefit" in TTSLO Dashboard

## What Does "Benefit" Mean?

The "Benefit" shown in the Completed Orders section measures **slippage** - the difference between when your order triggered and when it actually executed.

### Simple Explanation

Think of it like this:
- You set a trigger price (the price where you want to sell/buy)
- The market hits that price and your trailing stop loss order activates
- But then the price keeps moving a bit before your order fills
- **Benefit = how much the price moved while your order was executing**

## Why Is Benefit Often Negative?

**This is normal and expected for Trailing Stop Loss (TSL) orders!** Here's why:

### For SELL Orders (selling your crypto):
- Your order triggers at $2.53 (trigger price)
- The TSL "trails" the price by 1% 
- Price starts dropping, and your order executes at $2.50
- **Result: -1.23% benefit** (you got $0.03 less per coin than the trigger price)

### For BUY Orders (buying crypto):
- Your order triggers at $2.41 (trigger price)
- The TSL trails the price by 1%
- Price starts rising, and your order executes at $2.42
- **Result: -0.50% benefit** (you paid $0.01 more per coin than the trigger price)

### The Key Point

**Negative benefit is the COST of using trailing stop loss protection.** It's like insurance:
- You pay a small cost (the slippage)
- In exchange, you get protection from the price moving too far against you
- The trailing mechanism ensures you don't get a terrible fill price

## Is This Really a Loss?

**No! This is NOT a net loss on your trade.** Here's what matters:

### What "Benefit" Measures:
✗ NOT your total profit/loss on the trade
✗ NOT whether the trade was successful
✓ ONLY the execution slippage (trigger vs fill price)

### What Actually Matters:
✓ **Your total return**: Did you buy low and sell high overall?
✓ **The bracket strategy**: Are you profiting from price oscillations?
✓ **Trading fees**: Kraken charges fees (typically 0.16-0.26%)

### Example Calculation

Let's say you bought RENDER at $2.30 and sold it at $2.50:

1. **Buy order**: 
   - Trigger: $2.30, Execute: $2.31
   - Benefit: -$0.01 (-0.43%)
   - Fee: $0.006 (0.26%)
   
2. **Sell order**:
   - Trigger: $2.53, Execute: $2.50
   - Benefit: -$0.03 (-1.23%)
   - Fee: $0.006 (0.26%)

3. **Total result**:
   - Net price difference: $2.50 - $2.31 = $0.19 per coin
   - Total fees: ~$0.012 per coin
   - Slippage: ~$0.04 per coin
   - **Your actual profit: ~$0.14 per coin** (still profitable!)

## When Should I Be Concerned?

Negative benefit is fine, but watch for these warning signs:

### 🟢 Normal (Don't Worry)
- Benefit between -0.5% and -2.0%
- Roughly matches your trailing offset %
- Consistent across different orders

### 🟡 Pay Attention
- Benefit worse than -3%
- Much worse than your trailing offset
- Happens during high volatility periods

### 🔴 Investigate
- Benefit worse than -5%
- Consistent pattern of extreme slippage
- May indicate:
  - Low liquidity pairs (not enough buyers/sellers)
  - Market moving too fast
  - Trailing offset too tight

## How to Reduce Negative Benefit

### 1. Use Wider Trailing Offsets
- Current: 1.0% trailing offset
- Try: 1.5% or 2.0%
- **Trade-off**: More slippage protection, but less precise fills

### 2. Trade High-Liquidity Pairs
- Stick to major coins (BTC, ETH, SOL)
- Avoid obscure/low-volume altcoins
- **Why**: More buyers/sellers = faster execution = less slippage

### 3. Avoid Peak Volatility
- Don't trade during major news events
- Avoid orders during low-volume hours
- **Why**: Volatile markets = bigger price swings = more slippage

### 4. Use Limit Orders Instead
- Pro: No slippage, you control the exact price
- Con: Order might not fill if price moves away
- **When**: Use for less time-sensitive trades

## About the Bracket Strategy

The `tools/coin_stats.py` script uses a **bracket strategy**:

### What It Does:
- Places TWO orders per coin:
  1. **Sell bracket**: Triggers if price goes UP 2%
  2. **Buy bracket**: Triggers if price goes DOWN 2%

### Expected Benefit:
- Each order will have ~-1% to -2% benefit (from trailing offset + slippage)
- But you're profiting from the 2% price swing
- **Net result**: ~0% to +1% profit per complete cycle (buy low → sell high)

### Is the Strategy Working?

Looking at your actual results:
- render_usd: Bought at $2.42, sold at $2.50 = +$0.08 gross
- Slippage: -$0.01 (buy) + -$0.03 (sell) = -$0.04
- **Net: +$0.04 per coin** ✓ Strategy working!

The strategy is designed for:
- Volatile coins that oscillate (go up and down)
- Small consistent gains over time
- NOT get-rich-quick, but steady profit accumulation

### Should You Adjust the Strategy?

The default bracket strategy uses:
- **Bracket spacing**: ±2% from current price (trigger thresholds)
- **Trailing offset**: 1% (TTSLO minimum)

**When the strategy is working well:**
- ✅ You see both buy and sell orders completing
- ✅ Net profit positive after fees + slippage
- ✅ Orders trigger within reasonable timeframes (hours to days)

**Signs you might need adjustment:**

1. **Too much slippage** (worse than -3%):
   - Increase trailing offset to 1.5% or 2%
   - Trade-off: Better protection, but less profit per cycle

2. **Orders never trigger**:
   - Bracket spacing too wide for the coin's volatility
   - Run `tools/coin_stats.py` to analyze actual volatility
   - Adjust brackets to match the coin's typical movement

3. **Orders trigger too often**:
   - You're capturing tiny movements but paying fees repeatedly
   - Widen bracket spacing to 3% or 4%
   - Trade-off: Less frequent trades, but better profit margins

4. **Consistent losses**:
   - Check if fees + slippage exceed bracket spacing
   - Example: 2% bracket - 1% trailing - 0.5% fees = 0.5% profit margin
   - Need at least 1.5-2% profit margin for safety
   - Consider wider brackets (3-4%) or tighter trailing (if supported)

### Optimizing Your Strategy

**Use the coin_stats tool to analyze:**
```bash
# Analyze your coins to see typical volatility
python3 tools/coin_stats.py --pairs RENDERUSD RAYUSD FILUSD --hours 48

# Generate optimized bracket suggestions
python3 tools/coin_stats.py --config-output suggested_config.csv
```

The tool will:
- Show you typical price movements over 24-48 hours
- Suggest bracket spacings that match volatility
- Calculate probability of triggers within 24 hours
- Recommend only pairs with sufficient movement

**Key insight:** 
- Low volatility coins: Need wider brackets (3-5%) but fewer triggers
- High volatility coins: Can use tighter brackets (1-2%) with frequent triggers
- Match your strategy to each coin's actual behavior!

## Key Takeaways

1. **Negative benefit is normal** - it's the cost of using trailing stop loss protection
2. **Don't panic** - focus on your overall buy-low-sell-high profit, not the slippage
3. **Expect -1% to -2%** - roughly matching your trailing offset percentage
4. **The bracket strategy works** - you're capturing price swings despite the slippage
5. **Total return matters** - calculate: (sell price - buy price - fees - slippage)

## Further Reading

- [Trailing Stop Loss Explained](https://www.investopedia.com/terms/t/trailingstop.asp)
- [Understanding Slippage](https://www.investopedia.com/terms/s/slippage.asp)
- [Bracket Orders Strategy](https://www.investopedia.com/terms/b/bracketedbuyorder.asp)
- `tools/coin_stats.py` - Statistical analysis for picking good bracket candidates
- `README.md` - TTSLO documentation and setup guide
