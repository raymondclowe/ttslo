# Find Profitable Candidates Tool

This tool analyzes recent hourly price data to identify volatile trading pairs that could be profitable for bracketing strategies.

## Overview

The tool:
1. Fetches hourly OHLC (Open/High/Low/Close) data for specified pairs
2. Calculates volatility metrics (oscillations, standard deviation)
3. Estimates probability of achieving target profit
4. Ranks candidates by profitability
5. Optionally creates bracketing orders (buy low, sell high)

## Usage

### Basic Analysis

Analyze default pairs (BTC/USD, ETH/USD):
```bash
uv run python tools/find_profitable_candidates.py
```

### Custom Pairs and Parameters

```bash
uv run python tools/find_profitable_candidates.py \
  --pairs XXBTZUSD XETHZUSD SOLUSD ADAUSD \
  --hours 48 \
  --target-profit 5.0 \
  --min-oscillation 2.0 \
  --top 3
```

### Interactive Mode

Analyze pairs and create bracketing orders interactively:
```bash
uv run python tools/find_profitable_candidates.py \
  --pairs XXBTZUSD XETHZUSD \
  --interactive \
  --dry-run
```

Remove `--dry-run` to create actual orders.

## Arguments

- `--pairs`: Trading pairs to analyze (space-separated)
  - Default: `XXBTZUSD XETHZUSD XXBTZUSDT XETHZUSDT`
  - Examples: `XXBTZUSD`, `XETHZUSD`, `SOLUSD`, `ADAUSD`

- `--hours`: Hours of historical data to analyze
  - Default: `48` (2 days)
  - Range: `12` to `168` (1 week)

- `--target-profit`: Target profit percentage
  - Default: `5.0`
  - Example: `3.0` for 3% profit target

- `--min-oscillation`: Minimum oscillation to consider significant
  - Default: `2.0`
  - Used to count "significant swings"

- `--top`: Show only top N candidates
  - Default: All candidates
  - Example: `--top 3` shows best 3 candidates

- `--interactive`: Enable interactive mode
  - Allows selection and order creation

- `--dry-run`: Dry run mode (with `--interactive`)
  - Shows what would be done without creating orders

## Output

The tool provides:

### Volatility Metrics
- **Average Oscillation**: Average absolute % change per hour
- **Maximum Oscillation**: Largest % move observed
- **Standard Deviation**: Measure of price volatility
- **Significant Swings**: Count of moves > min-oscillation
- **Direction Changes**: How often price direction reverses

### Profit Opportunity
- **Historical Hits**: Times the target was reached in observed period
- **Probability**: Estimated % chance of hitting target
- **Expected Time**: Estimated hours until target hit
- **Confidence**: Data quality (low/medium/high)

### Candidate Rating
- ✅ **Good Candidate**: ≥30% probability, high volatility
- ⚠️ **Moderate Candidate**: 20-30% probability
- ❌ **Poor Candidate**: <20% probability

## Example Output

```
======================================================================
Pair: BTC/USD
Current Price: $110,273.00
======================================================================

Volatility Metrics:
  Average Oscillation: 0.41%
  Maximum Oscillation: 3.44%
  Standard Deviation: 0.70%
  Significant Swings (>2.0%): 1/47 periods
  Direction Changes: 19

Profit Opportunity (Target: 5.0%):
  Historical Hits: 0/47 periods
  Probability: 20.0%
  Expected Time: 96.0 hours
  Confidence: HIGH

⚠️  MODERATE CANDIDATE - Some potential but lower probability
```

## Bracketing Strategy

When you create bracketing orders, the tool:

1. Places a **buy limit order** below current price (at current - target%)
2. Places a **sell limit order** above current price (at current + target%)
3. One order will fill when price oscillates
4. You profit when price returns and fills the other order

### Example

Current BTC price: $110,000
Target profit: 3%

- Buy order: $106,700 (if price drops 3%)
- Sell order: $113,300 (if price rises 3%)

If price drops to $106,700:
- Buy order fills, you own BTC at $106,700
- When price rises back to $113,300, sell order fills
- Profit: $6,600 per BTC (minus fees)

## Important Notes

1. **Market Conditions**: Tool analyzes historical data only. Past performance doesn't guarantee future results.

2. **Fees**: Kraken charges trading fees (typically 0.16-0.26%). Factor these into your target profit.

3. **Balance Requirements**: You need:
   - Fiat currency for buy orders
   - Cryptocurrency for sell orders
   
4. **Order Management**: Monitor your orders. Cancel if market conditions change significantly.

5. **Risk**: Both orders are active. If both fill, you'll have made two trades (one buy, one sell).

## Statistics Background

The probability calculation is based on:

- **Historical Frequency**: How often the target was reached
- **Volatility**: Standard deviation of price changes
- **Oscillation Pattern**: Frequency of direction changes
- **Consistency Factor**: Rewards consistent back-and-forth movement

Formula:
```
probability = (historical_hits / periods) × (1 + oscillation_frequency × 0.5)
```

## Requirements

- Python 3.12+
- Kraken API credentials (read-only for analysis, read-write for orders)
- Network access to Kraken API

## See Also

- [Kraken API Documentation](https://docs.kraken.com/rest/)
- [TTSLO Main Tool](../README.md)
- [Kraken Trading Fees](https://www.kraken.com/features/fee-schedule)
