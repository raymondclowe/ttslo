# TTSLO Usage Examples

This document provides real-world examples and scenarios for using TTSLO.

## Example 1: Bitcoin Profit Protection

**Scenario:** You bought Bitcoin at $45,000 and want to lock in profits when it reaches $55,000, but still give it room to grow with a trailing stop.

**Configuration:**
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_profit_55k,XXBTZUSD,55000,above,sell,0.5,5.0,true
```

**What happens:**
1. TTSLO monitors BTC price (Kraken pair `XXBTZUSD`) every 60 seconds (default)
2. When BTC reaches $55,000, a trailing stop-loss sell order is created
3. The TSL order trails the price by 5% (follows price up, sells if it drops 5%)
4. If BTC goes to $60,000, the stop follows to $57,000 (5% below)
5. If BTC then drops to $57,000, your position is sold automatically

## Example 2: Ethereum Accumulation on Dips

**Scenario:** You want to buy more ETH when it dips below $3,000, but you want to catch it at the best price during the dip.

**Configuration:**
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
eth_accumulate,XETHZUSD,3000,below,buy,2.0,3.0,true
```

**What happens:**
1. When ETH drops below $3,000, a trailing stop-loss buy order is created
2. The TSL follows the price down by 3%
3. If ETH drops to $2,900, the stop follows to $2,987 (3% above)
4. If ETH bounces back to $2,987, your buy order executes
5. You bought at nearly the bottom of the dip!

## Example 3: Multiple Take-Profit Levels

**Scenario:** You have 1 BTC and want to take profits at different levels.

**Configuration:**
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_tp1,XXBTZUSD,55000,above,sell,0.25,4.0,true
btc_tp2,XXBTZUSD,60000,above,sell,0.25,5.0,true
btc_tp3,XXBTZUSD,70000,above,sell,0.25,6.0,true
btc_tp4,XXBTZUSD,80000,above,sell,0.25,7.0,true
```

**What happens:**
1. At $55k, 25% sells with 4% trailing stop
2. At $60k, another 25% sells with 5% trailing stop
3. At $70k, another 25% sells with 6% trailing stop
4. At $80k, final 25% sells with 7% trailing stop
5. Each level has increasingly loose trailing stops for bigger moves

## Example 4: Buy the Crash, Sell the Rally

**Scenario:** Prepare for both bull and bear scenarios on Solana.

**Configuration:**
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
sol_crash_buy,SOLUSD,100,below,buy,50,5.0,true
sol_rally_sell,SOLUSD,180,above,sell,50,5.0,true
```

**What happens:**
- If SOL crashes below $100, catches the bounce with 5% trailing buy
- If SOL rallies above $180, sells the top with 5% trailing sell
- Covers both market conditions

## Example 5: Altcoin Swing Trading

**Scenario:** Multiple altcoins with different strategies.

**Configuration:**
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
ada_breakout,ADAUSD,0.50,above,sell,1000,4.0,true
dot_dip,DOTUSD,6.00,below,buy,100,3.5,true
link_profit,LINKUSD,15.00,above,sell,50,5.5,true
avax_accumulate,AVAXUSD,25.00,below,buy,20,4.5,true
```

## Example 6: Conservative Risk Management

**Scenario:** You're risk-averse and want tight stops.

**Configuration:**
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_conservative,XXBTZUSD,52000,above,sell,0.1,2.0,true
eth_conservative,XETHZUSD,3100,above,sell,1.0,2.5,true
```

**Benefits:**
- Small trailing offsets (2-2.5%) lock in profits quickly
- Less room for pullbacks
- Better for volatile markets or uncertain conditions

## Example 7: Aggressive Profit Maximization

**Scenario:** You believe in strong trend and want maximum gains.

**Configuration:**
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_moonshot,XXBTZUSD,50000,above,sell,0.5,10.0,true
eth_moonshot,XETHZUSD,3000,above,sell,5.0,8.0,true
```

**Benefits:**
- Large trailing offsets (8-10%) let profits run
- More room for pullbacks in strong trends
- Risk: Larger potential loss if trend reverses sharply

## Example 8: Testing Strategy

**Scenario:** You want to test your configuration without risk.

**Commands:**
```bash
# Create test config
cat > test_config.csv << EOF
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
test_btc,XXBTZUSD,50000,above,sell,0.01,5.0,true
EOF

# Run in dry-run mode
uv run ttslo.py --config test_config.csv --dry-run --verbose --once

# Check what would happen
cat logs.csv
```

## Example 9: Monitoring Multiple Exchanges (Same Tool)

**Note:** This requires separate instances.

**Setup:**
```bash
# Terminal 1 - Main strategy
uv run ttslo.py --config strategy1.csv --state state1.csv --log log1.csv

# Terminal 2 - Alternative strategy
uv run ttslo.py --config strategy2.csv --state state2.csv --log log2.csv
```

## Example 10: Scheduled Checks (Cron)

**Scenario:** You don't want continuous monitoring, just hourly checks.

**Crontab entry:**
```cron
# Check every hour
0 * * * * cd /path/to/ttslo && uv run ttslo.py --once >> cron.log 2>&1

# Check every 15 minutes
*/15 * * * * cd /path/to/ttslo && uv run ttslo.py --once >> cron.log 2>&1
```

## Pro Tips

### Tip 1: Graduated Trailing Stops
Use tighter stops at lower prices, looser stops at higher prices:
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_50k,XXBTZUSD,50000,above,sell,0.1,3.0,true
btc_60k,XXBTZUSD,60000,above,sell,0.1,5.0,true
btc_70k,XXBTZUSD,70000,above,sell,0.1,7.0,true
```

### Tip 2: Symmetrical Strategy
Buy dips and sell rallies at symmetrical levels:
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
eth_buy_2800,XETHZUSD,2800,below,buy,1.0,4.0,true
eth_sell_3200,XETHZUSD,3200,above,sell,1.0,4.0,true
```

### Tip 3: Disable After Trigger
Once a trigger fires, it's marked in state.csv and won't fire again. To reset:
```bash
# Edit state.csv, change triggered from "true" to "false"
nano state.csv
```

### Tip 4: Start Small
Always test with minimal volumes first:
```csv
# Test with tiny amount
test_btc,XXBTZUSD,50000,above,sell,0.0001,5.0,true
```

### Tip 5: Monitor Regularly
```bash
# Watch logs in real-time
tail -f logs.csv

# Check for triggers
grep "triggered" state.csv

# Count active configurations
grep "true" config.csv | wc -l
```

## Common Pitfalls

### Pitfall 1: Wrong Pair Format
❌ Wrong: `BTC/USD`, `BTCUSD`
✅ Correct: `XXBTZUSD`

Check Kraken's documentation for exact pair names.

### Pitfall 2: Insufficient Balance
Make sure you have enough balance for the volumes specified.

### Pitfall 3: Too Tight Trailing Stops
2% trailing stop might trigger on normal volatility. Consider market conditions.

### Pitfall 4: Forgetting to Set enabled=true
Configuration won't run if enabled is false or missing.

### Pitfall 5: Not Testing First
Always run `--dry-run --verbose --once` before live trading.

## Need More Help?

- See [README.md](README.md) for detailed documentation
- See [QUICKSTART.md](QUICKSTART.md) for setup guide
- Check logs.csv for detailed execution logs
- Review state.csv to see what has triggered

---

**Disclaimer:** These are examples for educational purposes. Always do your own research and understand the risks before trading.
