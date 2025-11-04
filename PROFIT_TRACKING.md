# Profit Tracking and Reporting

TTSLO now includes comprehensive profit tracking to monitor and report on trading performance.

## Overview

The profit tracking system automatically records every trade from trigger to fill, calculating profit/loss based on entry and exit prices. This provides visibility into trading performance without manual tracking.

## Features

### Automatic Tracking
- **Order Triggers**: Recorded when TTSLO creates an order
- **Order Fills**: Updated when Kraken reports order completion
- **Profit Calculation**: Automatic based on direction and prices
- **CSV Storage**: All trades stored in `trades.csv`

### Profit Calculation

**For SELL orders** (sell high, buy back low):
```
Profit = (Entry Price - Exit Price) × Volume
```
Example: Sell BTC at $50,000, buy back at $49,000
- Profit = ($50,000 - $49,000) × 0.01 = $10

**For BUY orders** (buy low, sell high):
```
Profit = (Exit Price - Entry Price) × Volume
```
Example: Buy BTC at $49,000, sell at $50,000
- Profit = ($50,000 - $49,000) × 0.01 = $10

## Usage

### View Profit Summary
```bash
uv run python tools/profit_report.py
```

Output:
```
======================================================================
PROFIT SUMMARY REPORT
======================================================================
Total Trades: 10
  - Completed: 8
  - Triggered (Pending): 2

Total P&L: $127.50

Profitable Trades: 6
Losing Trades: 2
Win Rate: 75.0%

Average Profit: $25.50
Average Loss: $12.50
Largest Win: $45.00
Largest Loss: $20.00
======================================================================
```

### Detailed Trade History
```bash
uv run python tools/profit_report.py --detailed
```

Shows individual trade details:
- Trade ID
- Trading pair
- Direction (buy/sell)
- Entry/exit prices
- Profit/loss amount and percentage
- Status

### Profit by Trading Pair
```bash
uv run python tools/profit_report.py --by-pair
```

Groups profits by trading pair to identify which assets are most profitable.

### Performance Metrics
```bash
uv run python tools/profit_report.py --metrics
```

Advanced metrics:
- Win rate
- Profit factor (ratio of gross profit to gross loss)
- Expected value per trade
- Risk/reward ratio

### All Reports Combined
```bash
uv run python tools/profit_report.py --all
```

## Data Structure

### trades.csv Columns

| Column | Description |
|--------|-------------|
| `trade_id` | Unique identifier for the trade |
| `config_id` | Configuration ID from config.csv |
| `pair` | Trading pair (e.g., XXBTZUSD) |
| `direction` | Order direction (buy/sell) |
| `volume` | Trade volume |
| `entry_price` | Price when order triggered |
| `exit_price` | Price when order filled |
| `entry_time` | Timestamp when triggered |
| `exit_time` | Timestamp when filled |
| `profit_loss` | Profit/loss amount |
| `profit_loss_pct` | Profit/loss percentage |
| `status` | Trade status (triggered/completed/filled_only) |
| `notes` | Additional information |

### Trade Status

- **triggered**: Order created, awaiting fill
- **completed**: Order filled, profit calculated
- **filled_only**: Order filled without tracked entry (unusual case)

## Integration with Issue #195

The profit tracking system addresses the requirements from issue #195:

1. **Profits Attempted**: `triggered` status shows pending opportunities
2. **Profits Made**: `completed` trades with calculated P&L
3. **Potential**: Pending trades show what might be realized
4. **Executive Summary**: Comprehensive reports at multiple levels

## Example Workflow

1. TTSLO monitors price and threshold is met
2. Order created → **ProfitTracker** records entry:
   - Entry price
   - Volume
   - Timestamp
   - Status: `triggered`

3. Order fills on Kraken → **ProfitTracker** updates:
   - Exit price
   - Exit timestamp
   - Calculates profit/loss
   - Status: `completed`

4. Generate report anytime:
   ```bash
   uv run python tools/profit_report.py --all
   ```

## File Location

Trades are stored in `trades.csv` in the same directory as `state.csv` (default: current directory).

Custom location:
```bash
uv run python tools/profit_report.py --trades-file /path/to/trades.csv
```

## Tips

- Run reports regularly to track performance trends
- Use `--by-pair` to identify best performing assets
- Monitor win rate to assess strategy effectiveness
- Compare average profit vs average loss for risk management
- Use `--detailed` to review specific trades for patterns

## Privacy & Security

- trades.csv contains only aggregated trade data
- No API keys or sensitive credentials stored
- CSV format allows easy backup and analysis
- Can be excluded from git with `.gitignore` if desired
