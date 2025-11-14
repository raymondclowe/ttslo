#!/usr/bin/env python3
"""
Demo: Cryptocurrency Statistics Analysis Tool

This demo showcases the coin_stats.py tool with various examples.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

print("""
╔═══════════════════════════════════════════════════════════════════╗
║     Cryptocurrency Statistics Analysis Tool - Demo               ║
╚═══════════════════════════════════════════════════════════════════╝

This demo shows various use cases for coin_stats.py

FEATURE OVERVIEW:
─────────────────
1. Minute-by-minute price data analysis (up to 2,880 data points)
2. Statistical metrics: mean, median, standard deviation
3. Normal distribution testing (Shapiro-Wilk test)
4. Visual distribution graphs (histograms + overlays)
5. 95% probability threshold predictions
6. JSON export for further analysis

""")

print("=" * 70)
print("EXAMPLE 1: Quick Analysis of Bitcoin")
print("=" * 70)
print("""
Command:
  python3 tools/coin_stats.py --pairs XXBTZUSD --hours 24 --no-graphs

Output:
  - 1,440 minute samples analyzed
  - Mean, median, standard deviation calculated
  - Normality test result (likely non-normal for crypto)
  - 95% threshold: probability of price movement beyond X% in 24h
  
Use Case:
  - Quick check of Bitcoin volatility
  - Determine if price follows normal distribution
  - Set realistic price targets based on statistics
""")

print("\n" + "=" * 70)
print("EXAMPLE 2: Compare Multiple Coins")
print("=" * 70)
print("""
Command:
  python3 tools/coin_stats.py \\
    --pairs XXBTZUSD XETHZUSD SOLUSD \\
    --hours 48

Output:
  - Analysis for all 3 pairs
  - Distribution graphs saved to ./graphs/
  - Summary table comparing volatility
  - Normality test results for each
  
Use Case:
  - Portfolio diversification analysis
  - Compare volatility across different assets
  - Identify which coins are more stable/volatile
""")

print("\n" + "=" * 70)
print("EXAMPLE 3: Deep Analysis with JSON Export")
print("=" * 70)
print("""
Command:
  python3 tools/coin_stats.py \\
    --pairs XXBTZUSD XETHZUSD SOLUSD ADAUSD DOTUSD \\
    --hours 72 \\
    --json-output analysis.json

Output:
  - Complete statistical analysis
  - All graphs generated
  - Results exported to JSON file for:
    * Further processing
    * Custom visualizations
    * Integration with other tools
  
Use Case:
  - Research and analysis
  - Building trading strategies
  - Creating custom reports
""")

print("\n" + "=" * 70)
print("UNDERSTANDING NORMALITY TESTS")
print("=" * 70)
print("""
What is a Normal Distribution?
  - Bell curve shape
  - Symmetric around mean
  - 68% within 1 std dev, 95% within 2 std devs
  - Predictable probability distributions

Shapiro-Wilk Test:
  - Tests if data follows normal distribution
  - P-value > 0.05: Likely normal (✓)
  - P-value ≤ 0.05: Not normal (✗)

Why It Matters for Crypto:
  - Normal = predictable probability models work well
  - Non-normal = "fat tails" - more extreme events than expected
  - Affects reliability of threshold predictions
  - Most crypto assets are NOT normally distributed

Example:
  Normal Distribution (rare in crypto):
    Mean: $50,000, StdDev: $500
    95% confident: price between $49,000 - $51,000
    
  Non-Normal (typical in crypto):
    Mean: $50,000, StdDev: $500
    BUT: More extreme moves than predicted
    Actual range might be $48,000 - $52,000
""")

print("\n" + "=" * 70)
print("INTERPRETING 95% PROBABILITY THRESHOLDS")
print("=" * 70)
print("""
What It Means:
  "95% probability price will move beyond ±X% within 24h"
  
  This tells you:
  1. Expected magnitude of price movement
  2. Time frame (24 hours)
  3. Confidence level

Example 1 - High Volatility:
  95% Threshold: ±5.0%
  Current Price: $100
  → 95% chance price goes above $105 OR below $95 in 24h
  → Good for: Trading opportunities, wide profit targets
  
Example 2 - Low Volatility:
  95% Threshold: ±0.5%
  Current Price: $100
  → 95% chance price goes above $100.50 OR below $99.50 in 24h
  → Good for: Stable holdings, tight stop losses

Confidence Levels:
  - HIGH: Normal distribution, reliable predictions
  - MEDIUM: Somewhat normal, use with caution
  - LOW: Non-normal, predictions less reliable
""")

print("\n" + "=" * 70)
print("PRACTICAL TRADING APPLICATIONS")
print("=" * 70)
print("""
1. Set Price Alerts:
   - Use threshold to set realistic alerts
   - Example: BTC at $100k, threshold ±2%
   - Set alert at $98k (support) and $102k (resistance)

2. Position Sizing:
   - Higher StdDev = higher risk = smaller position
   - Lower StdDev = lower risk = larger position
   
3. Stop Loss Placement:
   - Use 95% threshold to avoid premature stops
   - Example: threshold ±3%, set stop at -4% for buffer

4. Profit Targets:
   - Use threshold for realistic targets
   - Example: threshold ±2%, set target at 3% for conservative

5. Portfolio Rebalancing:
   - Compare volatility across holdings
   - Reduce exposure to high StdDev assets
   - Increase stable assets during volatile markets
""")

print("\n" + "=" * 70)
print("GRAPH INTERPRETATION GUIDE")
print("=" * 70)
print("""
Left Graph: Price Distribution
  - X-axis: Price levels
  - Y-axis: Frequency (how often price was at that level)
  - Red line: Mean (average price)
  - Green line: Median (middle value)
  
  What to look for:
  - Symmetric shape = stable, predictable
  - Skewed shape = trending (left/right)
  - Multiple peaks = trading ranges
  - Wide distribution = high volatility

Right Graph: Percentage Change Distribution
  - X-axis: % change from previous minute
  - Y-axis: Frequency of that change
  - Red curve: Expected normal distribution
  
  What to look for:
  - Centered at 0 = no trend
  - Matches red curve = normal distribution
  - "Fat tails" = more extreme moves than normal
  - Asymmetric = directional bias
""")

print("\n" + "=" * 70)
print("LIMITATIONS AND WARNINGS")
print("=" * 70)
print("""
⚠️  IMPORTANT LIMITATIONS:

1. Past Performance ≠ Future Results
   - Statistics based on historical data
   - Market conditions can change rapidly
   - Black swan events not captured

2. Sample Size Matters
   - 48 hours may not capture weekly patterns
   - Weekend vs weekday volatility differs
   - Major events can skew results

3. Non-Normal Distributions
   - Most crypto is NOT normally distributed
   - Predictions less reliable than traditional assets
   - Fat tails = more extreme events

4. External Factors
   - News, regulations, hacks not in statistics
   - Sudden moves can exceed any threshold
   - Market manipulation affects patterns

5. API Limitations
   - Kraken may limit historical data
   - Minute data may have gaps
   - Different exchanges may differ

BEST PRACTICES:
✓ Use multiple time frames (24h, 48h, 7d)
✓ Combine with other analysis (TA, FA)
✓ Always use stop losses
✓ Never risk more than you can afford to lose
✓ Update analysis regularly (markets change)
""")

print("\n" + "=" * 70)
print("ADVANCED USE CASES")
print("=" * 70)
print("""
1. Volatility Arbitrage:
   - Compare same asset across exchanges
   - Look for volatility differences
   - Trade on exchange with lower volatility

2. Correlation Analysis:
   - Run analysis on multiple pairs
   - Export to JSON and compare
   - Identify correlated movements

3. Time Series Prediction:
   - Use statistics as baseline
   - Combine with ARIMA/LSTM models
   - Improve prediction accuracy

4. Risk Management:
   - Calculate Value at Risk (VaR)
   - Use StdDev for position sizing
   - Set portfolio-wide risk limits

5. Market Regime Detection:
   - Track changes in volatility over time
   - Detect regime changes (calm → volatile)
   - Adjust strategy accordingly
""")

print("\n" + "=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
Try it yourself:

1. Basic Analysis:
   python3 tools/coin_stats.py --pairs XXBTZUSD --hours 24 --no-graphs

2. Visual Analysis:
   python3 tools/coin_stats.py --pairs XXBTZUSD XETHZUSD --hours 48

3. Full Analysis:
   python3 tools/coin_stats.py --hours 48 --json-output results.json

4. Custom Pairs:
   python3 tools/coin_stats.py --pairs SOLUSD ADAUSD DOTUSD

For more information:
  - Read: docs/COIN_STATS.md
  - Tests: tests/test_coin_stats.py
  - Related: tools/find_profitable_candidates.py
""")

print("\n" + "=" * 70)
print("Demo complete! Try running the commands above.")
print("=" * 70)
