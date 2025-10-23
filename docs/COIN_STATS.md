# Cryptocurrency Statistics Analysis Tool

## Overview

The `coin_stats.py` tool analyzes minute-by-minute price data for cryptocurrency trading pairs to:
1. Calculate comprehensive statistical metrics
2. Test for normal distribution patterns
3. Generate visual distribution graphs
4. Predict probability thresholds for price movements

**Goal**: Determine with 95% confidence that an asset will exceed a certain price threshold within 24 hours.

## Features

### Statistical Analysis
- **Basic Statistics**: Mean, median, standard deviation, min/max prices
- **Percentage Changes**: Mean, median, and standard deviation of minute-to-minute price changes
- **Distribution Testing**: Shapiro-Wilk normality test to determine if price changes follow a normal distribution
- **Data Points**: Analyzes up to 2,880 data points (48 hours × 60 minutes)

### Visual Analytics
- **Price Distribution Histogram**: Shows frequency distribution of prices
- **Percentage Change Distribution**: Shows frequency distribution of price changes
- **Normal Distribution Overlay**: Compares actual distribution to theoretical normal distribution
- **Statistical Annotations**: Mean, median, and normality test results displayed on graphs

### Probability Predictions
- **95% Confidence Threshold**: Calculates price movement threshold with 95% probability
- **Confidence Levels**: Assesses prediction reliability (High/Medium/Low) based on normality test
- **24-Hour Predictions**: Estimates likely price range for the next day

### Export Capabilities
- **CSV Export**: Summary table exported to CSV for spreadsheet analysis
- **HTML Viewer**: Auto-generated HTML page for viewing all graphs in browser
- **Config Suggestions**: Generates suggested config.csv entries for TTSLO based on probability thresholds
- **JSON Export**: Complete analysis results in JSON format

## Installation

The tool requires additional Python packages for full functionality:

```bash
pip install numpy matplotlib scipy
```

For basic statistics only (without graphs or normality tests):
```bash
# Tool will run with reduced functionality
python3 tools/coin_stats.py --no-graphs
```

## Usage

### Basic Usage

Analyze default set of ~30 popular cryptocurrency pairs:

```bash
python3 tools/coin_stats.py
```

This will:
- Fetch 48 hours of minute-by-minute data
- Generate distribution graphs in `./graphs/`
- Display detailed analysis for each pair
- Show summary table with key metrics

### Custom Pair Selection

Analyze specific trading pairs:

```bash
python3 tools/coin_stats.py --pairs XXBTZUSD XETHZUSD SOLUSD
```

### Adjust Time Period

Analyze different time periods:

```bash
# Analyze last 24 hours
python3 tools/coin_stats.py --hours 24

# Analyze last 7 days (might be limited by API)
python3 tools/coin_stats.py --hours 168
```

### Save Results

Export results in multiple formats:

```bash
# Export to JSON
python3 tools/coin_stats.py --json-output results.json

# Export summary to CSV (default: summary_stats.csv)
python3 tools/coin_stats.py --csv-output my_summary.csv

# Generate HTML viewer for graphs (default: index.html in output-dir)
python3 tools/coin_stats.py --html-output viewer.html

# Generate suggested config.csv for TTSLO (default: suggested_config.csv)
python3 tools/coin_stats.py --config-output my_config.csv
```

### Complete Analysis with All Exports

```bash
python3 tools/coin_stats.py \
  --pairs XXBTZUSD XETHZUSD SOLUSD \
  --hours 48 \
  --output-dir ./analysis_results \
  --csv-output summary.csv \
  --html-output index.html \
  --config-output suggested_triggers.csv \
  --json-output full_data.json
```

This will create:
- Distribution graphs in `./analysis_results/`
- HTML viewer at `./analysis_results/index.html`
- CSV summary table at `summary.csv`
- Suggested config entries at `suggested_triggers.csv`
- Complete JSON data at `full_data.json`

### Skip Graph Generation

For faster analysis or when graphing libraries aren't available:

```bash
python3 tools/coin_stats.py --no-graphs
```

### Custom Output Directory

Specify where to save graphs:

```bash
python3 tools/coin_stats.py --output-dir /path/to/graphs
```

## Command Line Options

```
--pairs PAIRS [PAIRS ...]
    Trading pairs to analyze (default: 30 popular pairs)
    Examples: XXBTZUSD XETHZUSD SOLUSD

--hours HOURS
    Hours of historical data to analyze (default: 48)
    
--output-dir OUTPUT_DIR
    Directory to save distribution graphs (default: ./graphs)
    
--no-graphs
    Skip generating graphs (useful for quick analysis)
    
--csv-output CSV_OUTPUT
    Save summary table to CSV file (default: summary_stats.csv)
    
--html-output HTML_OUTPUT
    HTML filename for graph viewer (default: index.html, saved in output-dir)
    
--config-output CONFIG_OUTPUT
    Generate suggested config.csv for TTSLO (default: suggested_config.csv)
    
--json-output JSON_OUTPUT
    Save complete results to JSON file for further processing
```

## Output Files

### CSV Summary Table (`summary_stats.csv`)

Spreadsheet-friendly export with columns:
- Pair, Pair_Name, Mean, Median, StdDev, Min, Max, Range
- Pct_Mean, Pct_Median, Pct_StdDev
- Normal_Distribution, Normality_PValue
- Threshold_95_Pct, Threshold_Price_Up, Threshold_Price_Down
- Confidence, Data_Points

**Use cases:**
- Import into Excel/Google Sheets for further analysis
- Create custom charts and visualizations
- Compare results across multiple runs
- Filter and sort by volatility or other metrics

### HTML Graph Viewer (`index.html`)

Interactive HTML page with:
- All distribution graphs embedded
- Statistical summary tables for each pair
- Color-coded normality indicators
- Responsive design for mobile/desktop viewing

**How to use:**
1. Open `graphs/index.html` in any web browser
2. Scroll through all pairs and their graphs
3. Click graphs to view full size
4. Print or save page for documentation

### Suggested Config (`suggested_config.csv`)

Ready-to-use config.csv entries for TTSLO with:
- High-probability trigger thresholds (based on 95% analysis)
- Both above and below entries for each pair
- Conservative volumes suitable for testing
- Trailing offsets calculated from volatility

**Format (compatible with TTSLO config.csv):**
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_usd_above_1,XXBTZUSD,109958.73,above,sell,0.0010,1.00,true
btc_usd_below_2,XXBTZUSD,109834.91,below,buy,0.0010,1.00,true
```

**How to use:**
1. Review suggested entries carefully
2. Adjust volumes based on your risk tolerance
3. Copy entries to your main config.csv
4. Run TTSLO to monitor triggers

**⚠️ WARNING:** These are statistical predictions, not guarantees. Always:
- Start with small volumes for testing
- Monitor market conditions
- Adjust based on your strategy
- Review before enabling in production

## Output Explanation

### Detailed Analysis

For each pair, the tool displays:

```
======================================================================
Pair: BTC/USD
======================================================================

Price Statistics:
  Count: 2880 minute samples
  Mean: $109,848.15
  Median: $109,890.00
  Std Dev: $200.19
  Min: $109,481.00
  Max: $110,130.10
  Range: $649.10

Percentage Change Statistics:
  Mean: 0.002485%
  Median: 0.000000%
  Std Dev: 0.034437%

Normality Test (Shapiro-Wilk):
  Test Statistic: 0.7324
  P-value: 0.000000
  Is Normal: ✗ NO (p > 0.05)
  → Distribution does NOT follow normal pattern

95% Probability Threshold (24 hours):
  Threshold: ±0.0566%
  Upper Price: $109,910.38
  Lower Price: $109,785.93
  Confidence: LOW

  → 95% probability price will move beyond ±0.06% within 24h
```

### Understanding the Normality Test

The **Shapiro-Wilk test** determines if price changes follow a normal (bell curve) distribution:
- **P-value > 0.05**: Distribution is likely normal (✓ YES)
- **P-value ≤ 0.05**: Distribution is not normal (✗ NO)

**Why it matters**: 
- Normal distributions allow for more reliable probability predictions
- Non-normal distributions (common in crypto) may have "fat tails" - more extreme events than predicted
- Confidence levels adjust based on normality test results

### Interpreting the 95% Threshold

The 95% probability threshold tells you:
- **What movement to expect**: Price will likely move beyond this percentage
- **Time frame**: Within the next 24 hours
- **Confidence**: How reliable the prediction is

**Example**:
```
95% Probability Threshold (24 hours):
  Threshold: ±2.50%
  Upper Price: $51,250.00
  Lower Price: $48,750.00
  Confidence: HIGH
```

This means:
- 95% chance price will move more than ±2.50% in 24 hours
- Price likely to go above $51,250 or below $48,750
- High confidence due to normal distribution

### Summary Table

The summary table provides a quick comparison:

```
Pair            Mean         Median       StdDev       Normal?  95% Threshold   Confidence
==========================================================================================
XXBTZUSD        $109,848.15  $109,890.00  $200.1931    ✗        ±0.06%          LOW       
XETHZUSD        $3,841.64    $3,842.86    $9.7981      ✗        ±0.10%          LOW       
SOLUSD          $256.34      $256.45      $1.2345      ✓        ±1.20%          HIGH      
```

## Graph Interpretation

Each pair generates a PNG file with two histograms:

### Left: Price Distribution
- Shows how often the price was at different levels
- Red line: Mean price
- Green line: Median price
- Shape indicates price volatility

### Right: Percentage Change Distribution
- Shows frequency of price movements
- Orange bars: Actual distribution
- Red curve: Theoretical normal distribution (if applicable)
- Centered around zero for stable assets

## Use Cases

### Trading Strategy Development
1. **Identify Volatile Assets**: High standard deviation indicates trading opportunities
2. **Set Price Targets**: Use 95% threshold to set realistic profit targets
3. **Risk Assessment**: Non-normal distributions suggest higher tail risk

### Portfolio Management
1. **Diversification**: Compare volatility across different assets
2. **Rebalancing**: Use median/mean comparison to identify trending assets
3. **Entry/Exit Points**: Set alerts based on probability thresholds

### Academic Research
1. **Market Efficiency**: Test if crypto markets follow normal distributions
2. **Volatility Studies**: Compare volatility patterns across coins
3. **Behavioral Finance**: Identify deviations from expected distributions

## Technical Details

### Data Source
- Uses Kraken's public OHLC (Open/High/Low/Close) API
- 1-minute intervals for maximum granularity
- No authentication required (read-only public data)

### Statistical Methods
- **Mean/Median**: Standard arithmetic calculations
- **Standard Deviation**: Population standard deviation (stdevp)
- **Normality Test**: Shapiro-Wilk test (scipy.stats.shapiro)
- **Threshold Calculation**: Normal distribution inverse CDF (ppf)

### Limitations
1. **Historical Data**: Predictions based on past performance
2. **Market Conditions**: Sudden news/events not reflected in statistics
3. **Sample Size**: 48 hours may not capture weekly/monthly patterns
4. **API Limits**: Kraken may limit historical data range
5. **Normal Assumption**: Many crypto assets don't follow normal distributions

## Example Workflow

### Finding Trading Opportunities

```bash
# 1. Analyze popular pairs
python3 tools/coin_stats.py --hours 48 --output-dir analysis

# 2. Review summary table for high volatility pairs
# Look for: High StdDev, Normal distribution, High confidence

# 3. Examine graphs for visual confirmation
# Check: Symmetric distribution, clear mean/median

# 4. Export results for further analysis
python3 tools/coin_stats.py --json-output results.json

# 5. Use threshold data to set trading alerts
# Example: Set alert when BTC moves ±2% from mean
```

## Supported Trading Pairs

The tool includes ~30 popular pairs by default:

**Major Cryptocurrencies**:
- XXBTZUSD (Bitcoin)
- XETHZUSD (Ethereum)
- SOLUSD (Solana)
- XLTCZUSD (Litecoin)
- XXRPZUSD (Ripple)
- XXMRZUSD (Monero)

**DeFi & Smart Contracts**:
- AAVEUSD, ATOMUSD, COMPUSD, DYDXUSD, EGLDUSD, ENSUSD, FILUSD, INJUSD, NEARUSD

**Meme Coins**:
- BONKUSD, DOGSUSD, MEMEUSD, MEWUSD, PEPEUSD, PONKEUSD, POPCATUSD, TRUMPUSD

**Others**:
- ATHUSD, NANOUSD, RAYUSD, RENDERUSD, SUPERUSD, TONUSD, TRXUSD, WALUSD

## Troubleshooting

### "scipy not available" warning
Install required packages:
```bash
pip install numpy matplotlib scipy
```

### "Insufficient data" errors
- Pair may not have 48 hours of minute data on Kraken
- Try reducing `--hours` parameter
- Check if pair is actively traded

### Graphs not generating
- Ensure matplotlib is installed
- Check write permissions on output directory
- Use `--no-graphs` for analysis without visualization

### API errors
- Check internet connection
- Kraken API may be experiencing issues
- Try reducing number of pairs analyzed simultaneously

## Future Enhancements

Potential improvements:
1. **Multiple Timeframes**: Analyze 1m, 5m, 1h simultaneously
2. **Correlation Analysis**: Compare movement between pairs
3. **Backtesting**: Validate predictions against historical data
4. **Volatility Forecasting**: Predict future volatility trends
5. **Risk Metrics**: Add VaR (Value at Risk) calculations
6. **Machine Learning**: Use LSTM/ARIMA for time series prediction

## Related Tools

- `find_profitable_candidates.py`: Analyzes pairs for bracketing strategies
- `realtime_price_monitor.py`: Live price monitoring with alerts
- `price_update_frequency_test.py`: Tests API data freshness

## References

- [Kraken API Documentation](https://docs.kraken.com/api/)
- [Shapiro-Wilk Test](https://en.wikipedia.org/wiki/Shapiro%E2%80%93Wilk_test)
- [Normal Distribution](https://en.wikipedia.org/wiki/Normal_distribution)
- [Financial Statistics](https://en.wikipedia.org/wiki/Financial_statistics)
