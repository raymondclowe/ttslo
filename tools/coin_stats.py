#!/usr/bin/env python3
"""
Cryptocurrency Statistics Analysis Tool

Analyzes minute-by-minute price data for ~30 asset pairs to:
1. Calculate statistical metrics (mean, median, stdevp)
2. Test for normal distribution
3. Generate distribution graphs
4. Create summary table with probability thresholds

Goal: Predict with 95% probability that an asset will exceed a threshold within 24 hours
"""
import sys
import os
import argparse
import time
from datetime import datetime, timezone
import statistics
from pathlib import Path
import json
import csv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kraken_api import KrakenAPI
from creds import load_env

try:
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    from scipy import stats as scipy_stats
    STATS_AVAILABLE = True
except ImportError:
    STATS_AVAILABLE = False
    print("⚠️  Warning: numpy, matplotlib, or scipy not installed.")
    print("   Install with: pip install numpy matplotlib scipy")
    print("   Graphing and advanced statistics will be disabled.\n")


class CoinStatsAnalyzer:
    """Analyzes cryptocurrency price statistics."""
    
    def __init__(self, api, hours=48):
        """
        Initialize analyzer.
        
        Args:
            api: KrakenAPI instance
            hours: Number of hours of historical data to analyze (default: 48)
        """
        self.api = api
        self.hours = hours
    
    def format_pair_name(self, pair):
        """Convert Kraken pair format to readable format."""
        # Common conversions (from find_profitable_candidates.py)
        conversions = {
            # Major cryptocurrencies
            'XXBTZUSD': 'BTC/USD',
            'XXBTZEUR': 'BTC/EUR',
            'XETHZUSD': 'ETH/USD',
            'XXBTZUSDT': 'BTC/USDT',
            'XETHZUSDT': 'ETH/USDT',
            'SOLUSD': 'SOL/USD',
            'XLTCZUSD': 'LTC/USD',
            'XXRPZUSD': 'XRP/USD',
            'XXMRZUSD': 'XMR/USD',
            # DeFi and Smart Contract platforms
            'AAVEUSD': 'AAVE/USD',
            'ATOMUSD': 'ATOM/USD',
            'COMPUSD': 'COMP/USD',
            'DYDXUSD': 'DYDX/USD',
            'EGLDUSD': 'EGLD/USD',
            'ENSUSD': 'ENS/USD',
            'FILUSD': 'FIL/USD',
            'INJUSD': 'INJ/USD',
            'NEARUSD': 'NEAR/USD',
            # Meme coins and trending tokens
            'BONKUSD': 'BONK/USD',
            'DOGSUSD': 'DOGE/USD',
            'MEMEUSD': 'MEME/USD',
            'MEWUSD': 'MEW/USD',
            'PEPEUSD': 'PEPE/USD',
            'PONKEUSD': 'PONKE/USD',
            'POPCATUSD': 'POPCAT/USD',
            'TRUMPUSD': 'TRUMP/USD',
            # Other popular coins
            'ATHUSD': 'ATH/USD',
            'NANOUSD': 'NANO/USD',
            'RAYUSD': 'RAY/USD',
            'RENDERUSD': 'RENDER/USD',
            'SUPERUSD': 'SUPER/USD',
            'TONUSD': 'TON/USD',
            'TRXUSD': 'TRX/USD',
            'WALUSD': 'WAL/USD',
            # Legacy pairs
            'ADAUSD': 'ADA/USD',
            'DOTUSD': 'DOT/USD',
            'MATICUSD': 'MATIC/USD',
            # Fiat pairs
            'GBPUSD': 'GBP/USD',
        }
        return conversions.get(pair, pair)
    
    def fetch_minute_data(self, pair):
        """
        Fetch minute-by-minute OHLC data for a pair.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD')
            
        Returns:
            List of OHLC candles: [[time, open, high, low, close, vwap, volume, count], ...]
        """
        result = self.api.get_ohlc(pair, interval=1)  # 1 minute intervals
        
        # Find the pair key (not 'last')
        pair_keys = [k for k in result.keys() if k != 'last']
        if not pair_keys:
            return []
        
        candles = result[pair_keys[0]]
        
        # Filter to only include recent data (last N hours)
        cutoff_time = time.time() - (self.hours * 3600)
        recent_candles = [c for c in candles if c[0] >= cutoff_time]
        
        return recent_candles
    
    def calculate_statistics(self, candles):
        """
        Calculate statistical metrics from OHLC data.
        
        Args:
            candles: List of OHLC candles
            
        Returns:
            dict with statistics:
            - prices: List of close prices
            - mean: Mean price
            - median: Median price
            - stdev: Standard deviation
            - min_price: Minimum price
            - max_price: Maximum price
            - range: Price range
            - count: Number of data points
            - normality_test: Result of normality test (if available)
        """
        if len(candles) < 2:
            return None
        
        # Extract close prices
        prices = [float(c[4]) for c in candles]
        
        # Basic statistics
        mean = statistics.mean(prices)
        median = statistics.median(prices)
        stdev = statistics.stdev(prices) if len(prices) > 1 else 0
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        
        # Calculate percentage changes
        pct_changes = []
        for i in range(1, len(prices)):
            pct_change = ((prices[i] - prices[i-1]) / prices[i-1]) * 100
            pct_changes.append(pct_change)
        
        result = {
            'prices': prices,
            'mean': mean,
            'median': median,
            'stdev': stdev,
            'min_price': min_price,
            'max_price': max_price,
            'range': price_range,
            'count': len(prices),
            'pct_changes': pct_changes
        }
        
        # Normality test (if scipy available)
        if STATS_AVAILABLE and len(pct_changes) >= 8:
            # Shapiro-Wilk test for normality
            # Returns (test_statistic, p_value)
            # p_value > 0.05 suggests normal distribution
            statistic, p_value = scipy_stats.shapiro(pct_changes)
            result['normality_test'] = {
                'test': 'Shapiro-Wilk',
                'statistic': statistic,
                'p_value': p_value,
                'is_normal': p_value > 0.05
            }
            
            # Calculate additional distribution metrics
            if len(pct_changes) > 0:
                result['pct_mean'] = statistics.mean(pct_changes)
                result['pct_median'] = statistics.median(pct_changes)
                result['pct_stdev'] = statistics.stdev(pct_changes) if len(pct_changes) > 1 else 0
        
        return result
    
    def calculate_probability_threshold(self, stats, probability=0.95, time_horizon_minutes=1440, use_fat_tails=True):
        """
        Calculate price threshold for a given probability over a time horizon.
        
        Uses random walk theory: cumulative volatility over n steps = σ_minute × sqrt(n)
        For 24 hours (1440 minutes): σ_24h = σ_minute × sqrt(1440) ≈ σ_minute × 37.95
        
        Accounts for fat tails using Student's t-distribution when normality test fails.
        Crypto markets typically show fat tails (more extreme events than normal distribution).
        
        This correctly models how minute-to-minute changes accumulate over time to
        produce larger daily price movements.
        
        Args:
            stats: Statistics from calculate_statistics
            probability: Desired probability (0.95 = 95%)
            time_horizon_minutes: Time horizon in minutes (default 1440 = 24 hours)
            use_fat_tails: Use t-distribution for non-normal data (default True)
            
        Returns:
            dict with threshold information:
            - threshold_pct: Percentage change threshold over time horizon
            - threshold_price_up: Upper price threshold
            - threshold_price_down: Lower price threshold
            - confidence: Confidence in calculation
        """
        if not stats or not STATS_AVAILABLE:
            return None
        
        # Use percentage changes for calculation
        if 'pct_stdev' not in stats:
            return None
        
        pct_mean = stats.get('pct_mean', 0)
        pct_stdev_minute = stats.get('pct_stdev', 0)
        
        if pct_stdev_minute == 0:
            return None
        
        # Calculate cumulative volatility over time horizon using random walk
        # σ_total = σ_minute × sqrt(n)
        import math
        pct_stdev_horizon = pct_stdev_minute * math.sqrt(time_horizon_minutes)
        
        # Calculate quantile for the probability
        # For 95% probability of exceeding, we want the 5th percentile (lower tail)
        # Use t-distribution for fat tails (crypto typical) or normal distribution
        is_normal = stats.get('normality_test', {}).get('is_normal', False)
        
        if use_fat_tails and not is_normal:
            # Use Student's t-distribution with df=5 for fat tails
            # df=5 is typical for crypto markets - heavier tails than normal
            # More conservative for extreme events
            df = 5
            quantile = scipy_stats.t.ppf(1 - (1 - probability), df)
            distribution_used = 't-dist (df=5)'
        else:
            # Use normal distribution
            quantile = scipy_stats.norm.ppf(1 - (1 - probability))
            distribution_used = 'normal'
        
        # Calculate threshold (absolute value)
        # We're interested in the magnitude of movement from starting point
        threshold_pct = abs(quantile * pct_stdev_horizon)
        
        # Calculate actual price thresholds
        current_mean = stats['mean']
        threshold_price_up = current_mean * (1 + threshold_pct / 100)
        threshold_price_down = current_mean * (1 - threshold_pct / 100)
        
        # Determine confidence based on normality test
        confidence = 'medium'
        if 'normality_test' in stats:
            if stats['normality_test']['is_normal']:
                confidence = 'high'
            elif stats['normality_test']['p_value'] > 0.01:
                confidence = 'medium'
            else:
                confidence = 'low'
        
        return {
            'threshold_pct': threshold_pct,
            'threshold_price_up': threshold_price_up,
            'threshold_price_down': threshold_price_down,
            'confidence': confidence,
            'quantile': quantile,
            'distribution': distribution_used,
            'pct_stdev_minute': pct_stdev_minute,
            'pct_stdev_horizon': pct_stdev_horizon,
            'time_horizon_minutes': time_horizon_minutes
        }
    
    def generate_distribution_graph(self, pair, stats, output_dir='./graphs'):
        """
        Generate distribution graph for price data.
        
        Args:
            pair: Trading pair
            stats: Statistics from calculate_statistics
            output_dir: Directory to save graphs
            
        Returns:
            Path to saved graph or None if failed
        """
        if not STATS_AVAILABLE or not stats:
            return None
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Plot 1: Price distribution
        prices = stats['prices']
        ax1.hist(prices, bins=50, edgecolor='black', alpha=0.7, color='blue')
        ax1.axvline(stats['mean'], color='red', linestyle='--', label=f'Mean: ${stats["mean"]:.2f}')
        ax1.axvline(stats['median'], color='green', linestyle='--', label=f'Median: ${stats["median"]:.2f}')
        ax1.set_xlabel('Price (USD)')
        ax1.set_ylabel('Frequency')
        ax1.set_title(f'{self.format_pair_name(pair)} - Price Distribution')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Percentage change distribution
        pct_changes = stats.get('pct_changes', [])
        if pct_changes:
            ax2.hist(pct_changes, bins=50, edgecolor='black', alpha=0.7, color='orange')
            if 'pct_mean' in stats:
                ax2.axvline(stats['pct_mean'], color='red', linestyle='--', 
                           label=f'Mean: {stats["pct_mean"]:.4f}%')
            if 'pct_median' in stats:
                ax2.axvline(stats['pct_median'], color='green', linestyle='--',
                           label=f'Median: {stats["pct_median"]:.4f}%')
            
            # Add normal distribution overlay if normality test passed
            if stats.get('normality_test', {}).get('is_normal', False):
                pct_mean = stats['pct_mean']
                pct_stdev = stats['pct_stdev']
                x = np.linspace(min(pct_changes), max(pct_changes), 100)
                # Scale normal distribution to match histogram
                scale = len(pct_changes) * (max(pct_changes) - min(pct_changes)) / 50
                y = scale * scipy_stats.norm.pdf(x, pct_mean, pct_stdev)
                ax2.plot(x, y, 'r-', linewidth=2, label='Normal Distribution')
            
            ax2.set_xlabel('Price Change (%)')
            ax2.set_ylabel('Frequency')
            ax2.set_title(f'{self.format_pair_name(pair)} - Percentage Change Distribution')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # Add overall stats as text
        textstr = f'Data Points: {stats["count"]}\n'
        textstr += f'Price Range: ${stats["min_price"]:.2f} - ${stats["max_price"]:.2f}\n'
        textstr += f'Std Dev: ${stats["stdev"]:.2f}'
        if 'normality_test' in stats:
            textstr += f'\nNormality p-value: {stats["normality_test"]["p_value"]:.4f}'
            textstr += f'\nNormal: {"Yes" if stats["normality_test"]["is_normal"] else "No"}'
        
        fig.text(0.5, 0.02, textstr, ha='center', fontsize=9, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout(rect=[0, 0.08, 1, 1])
        
        # Save figure
        filename = f"{pair}_distribution.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def analyze_pair(self, pair):
        """
        Perform complete analysis on a trading pair.
        
        Args:
            pair: Trading pair to analyze
            
        Returns:
            dict with complete analysis or None if insufficient data
        """
        try:
            candles = self.fetch_minute_data(pair)
            if len(candles) < 100:  # Need reasonable amount of data
                return None
            
            stats = self.calculate_statistics(candles)
            if not stats:
                return None
            
            # Calculate 95% probability threshold
            threshold_95 = self.calculate_probability_threshold(stats, probability=0.95)
            
            return {
                'pair': pair,
                'stats': stats,
                'threshold_95': threshold_95
            }
        except Exception as e:
            print(f"Error analyzing {pair}: {e}")
            return None
    
    def print_analysis(self, analysis):
        """Print analysis results in readable format."""
        if not analysis:
            return
        
        pair = self.format_pair_name(analysis['pair'])
        stats = analysis['stats']
        
        print(f"\n{'='*70}")
        print(f"Pair: {pair}")
        print(f"{'='*70}")
        
        print(f"\nPrice Statistics:")
        print(f"  Count: {stats['count']} minute samples")
        print(f"  Mean: ${stats['mean']:,.4f}")
        print(f"  Median: ${stats['median']:,.4f}")
        print(f"  Std Dev: ${stats['stdev']:,.4f}")
        print(f"  Min: ${stats['min_price']:,.4f}")
        print(f"  Max: ${stats['max_price']:,.4f}")
        print(f"  Range: ${stats['range']:,.4f}")
        
        if 'pct_mean' in stats:
            print(f"\nPercentage Change Statistics:")
            print(f"  Mean: {stats['pct_mean']:.6f}%")
            print(f"  Median: {stats['pct_median']:.6f}%")
            print(f"  Std Dev: {stats['pct_stdev']:.6f}%")
        
        if 'normality_test' in stats:
            nt = stats['normality_test']
            print(f"\nNormality Test ({nt['test']}):")
            print(f"  Test Statistic: {nt['statistic']:.4f}")
            print(f"  P-value: {nt['p_value']:.6f}")
            print(f"  Is Normal: {'✓ YES' if nt['is_normal'] else '✗ NO'} (p > 0.05)")
            
            if nt['is_normal']:
                print(f"  → Distribution follows normal pattern")
            else:
                print(f"  → Distribution does NOT follow normal pattern")
        
        threshold = analysis.get('threshold_95')
        if threshold:
            print(f"\n95% Probability Threshold (24 hours):")
            print(f"  Threshold: ±{threshold['threshold_pct']:.4f}%")
            print(f"  Upper Price: ${threshold['threshold_price_up']:,.4f}")
            print(f"  Lower Price: ${threshold['threshold_price_down']:,.4f}")
            print(f"  Confidence: {threshold['confidence'].upper()}")
            print(f"\n  → 95% probability price will move beyond ±{threshold['threshold_pct']:.2f}% within 24h")


def print_summary_table(results):
    """Print summary table of all analyses."""
    if not results:
        print("\n❌ No results to display")
        return
    
    print(f"\n\n{'#'*70}")
    print(f"# SUMMARY TABLE")
    print(f"{'#'*70}\n")
    
    # Table header
    header = f"{'Pair':<15} {'Mean':<12} {'Median':<12} {'StdDev':<12} {'Normal?':<8} {'95% Threshold':<15} {'Confidence':<10}"
    print(header)
    print("=" * len(header))
    
    for analysis in results:
        pair = analysis['pair']
        stats = analysis['stats']
        threshold = analysis.get('threshold_95')
        
        # Format values
        mean = f"${stats['mean']:,.2f}"
        median = f"${stats['median']:,.2f}"
        stdev = f"${stats['stdev']:,.4f}"
        
        # Normality indicator
        if 'normality_test' in stats:
            is_normal = '✓' if stats['normality_test']['is_normal'] else '✗'
        else:
            is_normal = 'N/A'
        
        # Threshold
        if threshold:
            thresh_str = f"±{threshold['threshold_pct']:.2f}%"
            conf = threshold['confidence'][:4].upper()  # First 4 chars
        else:
            thresh_str = 'N/A'
            conf = 'N/A'
        
        row = f"{pair:<15} {mean:<12} {median:<12} {stdev:<12} {is_normal:<8} {thresh_str:<15} {conf:<10}"
        print(row)
    
    print("\n")
    
    # Additional summary stats
    normal_count = sum(1 for r in results 
                      if r['stats'].get('normality_test', {}).get('is_normal', False))
    total_count = len(results)
    
    print(f"Total pairs analyzed: {total_count}")
    print(f"Normal distributions: {normal_count}/{total_count} ({normal_count/total_count*100:.1f}%)")
    print(f"Non-normal distributions: {total_count - normal_count}/{total_count} ({(total_count-normal_count)/total_count*100:.1f}%)")


def save_summary_csv(results, analyzer, output_file='summary_stats.csv'):
    """
    Save summary table to CSV file for spreadsheet analysis.
    
    Args:
        results: List of analysis results
        analyzer: CoinStatsAnalyzer instance
        output_file: Path to CSV file
    """
    if not results:
        return None
    
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = [
            'Pair', 'Pair_Name', 'Mean', 'Median', 'StdDev', 'Min', 'Max', 'Range',
            'Pct_Mean', 'Pct_Median', 'Pct_StdDev',
            'Normal_Distribution', 'Normality_PValue', 
            'Threshold_95_Pct', 'Threshold_Price_Up', 'Threshold_Price_Down',
            'Confidence', 'Data_Points'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for analysis in results:
            pair = analysis['pair']
            stats = analysis['stats']
            threshold = analysis.get('threshold_95')
            
            row = {
                'Pair': pair,
                'Pair_Name': analyzer.format_pair_name(pair),
                'Mean': stats['mean'],
                'Median': stats['median'],
                'StdDev': stats['stdev'],
                'Min': stats['min_price'],
                'Max': stats['max_price'],
                'Range': stats['range'],
                'Pct_Mean': stats.get('pct_mean', 0),
                'Pct_Median': stats.get('pct_median', 0),
                'Pct_StdDev': stats.get('pct_stdev', 0),
                'Normal_Distribution': stats.get('normality_test', {}).get('is_normal', False),
                'Normality_PValue': stats.get('normality_test', {}).get('p_value', 0),
                'Threshold_95_Pct': threshold['threshold_pct'] if threshold else 0,
                'Threshold_Price_Up': threshold['threshold_price_up'] if threshold else 0,
                'Threshold_Price_Down': threshold['threshold_price_down'] if threshold else 0,
                'Confidence': threshold['confidence'] if threshold else 'N/A',
                'Data_Points': stats['count']
            }
            writer.writerow(row)
    
    return output_file


def generate_html_viewer(results, analyzer, output_dir='./graphs', html_file='index.html'):
    """
    Generate HTML file for viewing all distribution graphs in browser.
    
    Args:
        results: List of analysis results
        analyzer: CoinStatsAnalyzer instance
        output_dir: Directory containing PNG graphs
        html_file: Output HTML filename
    """
    if not results:
        return None
    
    html_path = os.path.join(output_dir, html_file)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cryptocurrency Statistics Analysis</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .info {{
            background-color: #e7f3fe;
            border-left: 6px solid #2196F3;
            padding: 10px;
            margin-bottom: 20px;
        }}
        .graph-container {{
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .graph-header {{
            background-color: #4CAF50;
            color: white;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }}
        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
        }}
        .stats-table th, .stats-table td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        .stats-table th {{
            background-color: #4CAF50;
            color: white;
        }}
        .stats-table tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .normal-yes {{
            color: green;
            font-weight: bold;
        }}
        .normal-no {{
            color: red;
            font-weight: bold;
        }}
        .timestamp {{
            color: #666;
            font-size: 0.9em;
            text-align: right;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1>📊 Cryptocurrency Statistics Analysis</h1>
    
    <div class="info">
        <strong>Analysis Summary:</strong><br>
        Total pairs analyzed: {len(results)}<br>
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
"""
    
    for analysis in results:
        pair = analysis['pair']
        pair_name = analyzer.format_pair_name(pair)
        stats = analysis['stats']
        threshold = analysis.get('threshold_95')
        
        # Check if normality test exists
        is_normal = stats.get('normality_test', {}).get('is_normal', False)
        normal_class = 'normal-yes' if is_normal else 'normal-no'
        normal_text = '✓ YES' if is_normal else '✗ NO'
        
        graph_filename = f"{pair}_distribution.png"
        
        html_content += f"""
    <div class="graph-container">
        <div class="graph-header">
            <h2>{pair_name} ({pair})</h2>
        </div>
        
        <table class="stats-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Mean Price</td>
                <td>${stats['mean']:,.4f}</td>
            </tr>
            <tr>
                <td>Median Price</td>
                <td>${stats['median']:,.4f}</td>
            </tr>
            <tr>
                <td>Standard Deviation</td>
                <td>${stats['stdev']:,.4f}</td>
            </tr>
            <tr>
                <td>Min / Max Price</td>
                <td>${stats['min_price']:,.4f} / ${stats['max_price']:,.4f}</td>
            </tr>
            <tr>
                <td>Data Points</td>
                <td>{stats['count']} minutes</td>
            </tr>
            <tr>
                <td>Normal Distribution?</td>
                <td class="{normal_class}">{normal_text}</td>
            </tr>
"""
        
        if threshold:
            html_content += f"""
            <tr>
                <td>95% Threshold</td>
                <td>±{threshold['threshold_pct']:.2f}%</td>
            </tr>
            <tr>
                <td>Upper Price Target</td>
                <td>${threshold['threshold_price_up']:,.4f}</td>
            </tr>
            <tr>
                <td>Lower Price Target</td>
                <td>${threshold['threshold_price_down']:,.4f}</td>
            </tr>
            <tr>
                <td>Confidence</td>
                <td>{threshold['confidence'].upper()}</td>
            </tr>
"""
        
        html_content += f"""
        </table>
        
        <img src="{graph_filename}" alt="{pair_name} Distribution">
    </div>
"""
    
    html_content += f"""
    <div class="timestamp">
        Generated by coin_stats.py on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>
"""
    
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    return html_path


def calculate_volume_for_pair(api, pair, current_price, target_usd_volume=1.0):
    """
    Calculate appropriate volume for a trading pair.
    
    Uses either:
    1. Target USD volume converted to coin units (volume = target_usd / price)
    2. Kraken's minimum order volume (ordermin from AssetPairs API)
    
    Returns the maximum of the two to ensure Kraken requirements are met.
    
    Args:
        api: KrakenAPI instance
        pair: Trading pair (e.g., 'XXBTZUSD')
        current_price: Current price of the asset
        target_usd_volume: Target volume in USD (default: 1.0)
    
    Returns:
        Calculated volume in coin units
    """
    import random
    
    # Calculate volume based on target USD value
    # Add +/- 25% variance for diversity
    variance = random.uniform(-0.25, 0.25)
    adjusted_target = target_usd_volume * (1 + variance)
    calculated_volume = adjusted_target / current_price
    
    # Get minimum order volume from Kraken API
    try:
        pair_info = api.get_asset_pair_info(pair)
        if pair_info and 'ordermin' in pair_info:
            ordermin = float(pair_info['ordermin'])
            # Use the maximum of calculated volume and minimum required
            volume = max(calculated_volume, ordermin)
        else:
            # If we can't get ordermin, use calculated volume
            volume = calculated_volume
    except Exception as e:
        print(f"  Warning: Could not fetch ordermin for {pair}: {e}")
        volume = calculated_volume
    
    return volume


def generate_config_suggestions(results, analyzer, output_file='suggested_config.csv', 
                               bracket_offset_pct=2.0, trailing_offset_pct=1.0,
                               target_usd_volume=1.0):
    """
    Generate suggested config.csv entries using bracket strategy.
    
    BRACKET STRATEGY:
    - Each pair gets TWO entries: buy bracket below and sell bracket above
    - Configurable bracket offset from current price (default 2%)
    - Configurable trailing offset (default 1%, TTSLO minimum)
    - Only includes pairs where movement has reasonable probability within 24h
    
    PORTFOLIO OPTIMIZATION:
    - Target 95% probability that at least ONE entry triggers in portfolio
    - For n entries: per_entry_prob = 1 - (0.05)^(1/n)
    - Validates each pair can achieve this probability based on 24h volatility
    
    VOLUME CALCULATION:
    - Converts target USD volume to coin units (volume = USD / price)
    - Adds +/- 25% variance for diversity
    - Ensures Kraken minimum order volume (ordermin) is met
    - Uses max(calculated, ordermin) for final volume
    
    Args:
        results: List of analysis results
        analyzer: CoinStatsAnalyzer instance
        output_file: Path to suggested config CSV file
        bracket_offset_pct: Percentage offset for brackets (default: 2.0)
        trailing_offset_pct: Trailing offset percentage (default: 1.0)
        target_usd_volume: Target volume in USD (default: 1.0)
    """
    if not results:
        return None
    
    # Filter for results with valid statistics
    valid_results = [r for r in results if r.get('stats')]
    
    if not valid_results:
        return None
    
    # Calculate required per-entry probability for 95% portfolio probability
    # Each pair contributes 2 entries (buy + sell bracket)
    n_total_entries = len(valid_results) * 2
    # Portfolio probability: 1 - (1-p)^n = 0.95
    # Solving for p: p = 1 - (0.05)^(1/n)
    import math
    per_entry_probability = 1 - math.pow(0.05, 1.0 / n_total_entries)
    
    # Convert to "probability of exceeding threshold" (1 - tail_prob)
    tail_probability = 1 - per_entry_probability
    
    print(f"\n{'='*70}")
    print(f"BRACKET STRATEGY CONFIG GENERATION")
    print(f"{'='*70}")
    print(f"Total pairs analyzed: {len(valid_results)}")
    print(f"Total entries (2 per pair): {n_total_entries}")
    print(f"Per-entry probability: {per_entry_probability*100:.2f}%")
    print(f"Portfolio probability (at least one triggers): 95.0%")
    print(f"Bracket offset: ±{bracket_offset_pct:.1f}% from current price")
    print(f"Trailing offset: {trailing_offset_pct:.1f}%")
    print(f"Target USD volume: ${target_usd_volume:.2f} +/- 25%")
    print(f"{'='*70}\n")
    
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['id', 'pair', 'threshold_price', 'threshold_type', 
                     'direction', 'volume', 'trailing_offset_percent', 'enabled']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        entry_count = 0
        pairs_included = 0
        pairs_excluded = 0
        
        for analysis in valid_results:
            pair = analysis['pair']
            stats = analysis['stats']
            
            # Get current mean price
            current_price = stats['mean']
            
            # Calculate threshold prices for brackets
            upper_bracket = current_price * (1 + bracket_offset_pct / 100)
            lower_bracket = current_price * (1 - bracket_offset_pct / 100)
            
            # Check if movement is achievable with required probability
            # Calculate what probability the pair can achieve for the bracket offset
            threshold = analyzer.calculate_probability_threshold(stats, probability=tail_probability)
            
            if not threshold:
                pairs_excluded += 1
                continue
            
            # Check if the pair's volatility can achieve bracket offset with required probability
            # If threshold_pct >= bracket_offset_pct, then movement is achievable with this probability
            if threshold['threshold_pct'] < bracket_offset_pct:
                # This pair's volatility is too low for the bracket offset to be probable enough
                pairs_excluded += 1
                continue
            
            pairs_included += 1
            
            # Determine decimal places based on price magnitude
            if current_price >= 1000:
                price_format = '.2f'
            elif current_price >= 10:
                price_format = '.4f'
            elif current_price >= 0.01:
                price_format = '.6f'
            else:
                price_format = '.8f'
            
            # Calculate volume based on target USD value and Kraken minimums
            volume = calculate_volume_for_pair(analyzer.api, pair, current_price, target_usd_volume)
            
            # Determine volume decimal places based on volume magnitude
            if volume >= 1:
                volume_format = '.4f'
            elif volume >= 0.01:
                volume_format = '.6f'
            else:
                volume_format = '.8f'
            
            # Create SELL bracket entry (price goes above +2%)
            entry_count += 1
            pair_short = analyzer.format_pair_name(pair).replace('/', '_').lower()
            writer.writerow({
                'id': f"{pair_short}_sell_{entry_count}",
                'pair': pair,
                'threshold_price': f"{upper_bracket:{price_format}}",
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': f"{volume:{volume_format}}",
                'trailing_offset_percent': f"{trailing_offset_pct:.2f}",
                'enabled': 'true'
            })
            
            # Create BUY bracket entry (price goes below)
            entry_count += 1
            writer.writerow({
                'id': f"{pair_short}_buy_{entry_count}",
                'pair': pair,
                'threshold_price': f"{lower_bracket:{price_format}}",
                'threshold_type': 'below',
                'direction': 'buy',
                'volume': f"{volume:{volume_format}}",
                'trailing_offset_percent': f"{trailing_offset_pct:.2f}",
                'enabled': 'true'
            })
    
    print(f"Config generation complete:")
    print(f"  Pairs included: {pairs_included}")
    print(f"  Pairs excluded (insufficient volatility): {pairs_excluded}")
    print(f"  Total entries generated: {entry_count}\n")
    
    return output_file


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze cryptocurrency price statistics and distributions'
    )
    parser.add_argument(
        '--pairs',
        nargs='+',
        default=[
            # Major cryptocurrencies
            'XXBTZUSD', 'XXBTZEUR', 'XETHZUSD', 'SOLUSD',
            'XLTCZUSD', 'XXRPZUSD', 'XXMRZUSD',
            # DeFi and Smart Contract platforms
            'AAVEUSD', 'ATOMUSD', 'COMPUSD', 'DYDXUSD', 'EGLDUSD', 'ENSUSD',
            'FILUSD', 'INJUSD', 'NEARUSD',
            # Meme coins and trending tokens
            'BONKUSD', 'DOGSUSD', 'MEMEUSD', 'MEWUSD', 'PEPEUSD', 
            'PONKEUSD', 'POPCATUSD', 'TRUMPUSD',
            # Other popular coins
            'ATHUSD', 'NANOUSD', 'RAYUSD', 'RENDERUSD', 'SUPERUSD', 
            'TONUSD', 'TRXUSD', 'WALUSD',
            # Fiat pairs
            'GBPUSD',
        ],
        help='Trading pairs to analyze (default: 32 popular pairs including BTC/EUR and GBP/USD)'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=48,
        help='Hours of historical data to analyze (default: 48)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./graphs',
        help='Directory to save distribution graphs (default: ./graphs)'
    )
    parser.add_argument(
        '--no-graphs',
        action='store_true',
        help='Skip generating graphs'
    )
    parser.add_argument(
        '--json-output',
        type=str,
        help='Save results to JSON file'
    )
    parser.add_argument(
        '--csv-output',
        type=str,
        default='summary_stats.csv',
        help='Save summary table to CSV file (default: summary_stats.csv)'
    )
    parser.add_argument(
        '--html-output',
        type=str,
        default='index.html',
        help='HTML filename for graph viewer (default: index.html, saved in output-dir)'
    )
    parser.add_argument(
        '--config-output',
        type=str,
        default='suggested_config.csv',
        help='Generate suggested config.csv for TTSLO (default: suggested_config.csv)'
    )
    parser.add_argument(
        '--suggestbracket',
        type=float,
        default=2.0,
        help='Bracket offset percentage for suggestions (default: 2.0)'
    )
    parser.add_argument(
        '--suggestoffset',
        type=float,
        default=1.0,
        help='Trailing offset percentage for suggestions (default: 1.0)'
    )
    parser.add_argument(
        '--target-usd-volume',
        type=float,
        default=1.0,
        help='Target volume in USD for suggested config (default: 1.0). Adds +/- 25%% variance and ensures Kraken minimums are met.'
    )
    
    args = parser.parse_args()
    
    if not STATS_AVAILABLE and not args.no_graphs:
        print("\n⚠️  scipy/numpy/matplotlib not available - graphs will be skipped")
        print("   Install with: pip install numpy matplotlib scipy\n")
        args.no_graphs = True
    
    # Load environment and create API client
    load_env()
    api = KrakenAPI()
    
    # Create analyzer
    analyzer = CoinStatsAnalyzer(api, hours=args.hours)
    
    print(f"Analyzing {len(args.pairs)} trading pairs...")
    print(f"Historical data: {args.hours} hours (minute-by-minute)")
    print(f"Expected data points per pair: ~{args.hours * 60}")
    
    # Analyze all pairs
    results = []
    for pair in args.pairs:
        print(f"\nFetching data for {analyzer.format_pair_name(pair)}...", end=' ')
        analysis = analyzer.analyze_pair(pair)
        if analysis:
            results.append(analysis)
            print("✓")
            
            # Generate graph if requested
            if not args.no_graphs:
                graph_path = analyzer.generate_distribution_graph(
                    pair, analysis['stats'], args.output_dir
                )
                if graph_path:
                    print(f"  Graph saved: {graph_path}")
        else:
            print("✗ (insufficient data)")
    
    if not results:
        print("\n❌ No pairs analyzed successfully.")
        return 1
    
    # Print individual analyses
    print(f"\n\n{'#'*70}")
    print(f"# DETAILED ANALYSIS")
    print(f"{'#'*70}")
    
    for analysis in results:
        analyzer.print_analysis(analysis)
    
    # Print summary table
    print_summary_table(results)
    
    # Save CSV summary
    csv_path = save_summary_csv(results, analyzer, args.csv_output)
    if csv_path:
        print(f"\n✓ Summary table saved to {csv_path}")
    
    # Generate HTML viewer for graphs
    if not args.no_graphs:
        html_path = generate_html_viewer(results, analyzer, args.output_dir, args.html_output)
        if html_path:
            print(f"✓ HTML graph viewer saved to {html_path}")
            print(f"  Open in browser: file://{os.path.abspath(html_path)}")
    
    # Generate suggested config.csv entries with bracket strategy
    config_path = generate_config_suggestions(results, analyzer, args.config_output,
                                              bracket_offset_pct=args.suggestbracket,
                                              trailing_offset_pct=args.suggestoffset,
                                              target_usd_volume=args.target_usd_volume)
    if config_path:
        print(f"\n{'='*70}")
        print(f"SUGGESTED CONFIG WITH BRACKET STRATEGY")
        print(f"{'='*70}")
        print(f"\nIn order to create items that have a high chance of triggering")
        print(f"in the next 24 hours, add these lines to your config.csv:")
        print(f"\n✓ Suggested config saved to {config_path}")
        
        print(f"\nBracket Strategy Details:")
        print(f"  - Each pair gets TWO entries: buy bracket (-{args.suggestbracket}%) and sell bracket (+{args.suggestbracket}%)")
        print(f"  - Trailing offset: {args.suggestoffset}%")
        print(f"  - Target USD volume: ${args.target_usd_volume:.2f} +/- 25%")
        print(f"  - Volumes ensure Kraken minimum order requirements (ordermin) are met")
        print(f"  - Portfolio optimized for 95% chance at least ONE entry triggers")
        print(f"  - Uses Student's t-distribution to account for fat tails")
        print(f"  - Random walk model: 24h volatility = minute volatility × sqrt(1440)")
        print(f"  - Decimal places adjusted based on coin value (more for low-value coins)")
        print(f"  - Each pair has up to two entries (above/below thresholds)")
        print(f"\n⚠️  WARNING: These are suggestions based on statistical analysis.")
        print(f"   Review and adjust volumes before using in production!")
    
    # Save JSON if requested
    if args.json_output:
        # Convert numpy types to native Python for JSON serialization
        def convert_value(val):
            """Convert numpy/scipy types to native Python types."""
            if isinstance(val, (np.integer, np.floating)):
                return float(val)
            elif isinstance(val, np.bool_):
                return bool(val)
            elif isinstance(val, dict):
                return {k: convert_value(v) for k, v in val.items()}
            elif isinstance(val, (list, tuple)):
                return [convert_value(v) for v in val]
            else:
                return val
        
        json_results = []
        for r in results:
            result_copy = {
                'pair': r['pair'],
                'stats': {}
            }
            
            # Copy stats, excluding non-serializable fields
            for key, value in r['stats'].items():
                if key in ['prices', 'pct_changes']:
                    continue  # Skip large arrays
                else:
                    result_copy['stats'][key] = convert_value(value)
            
            if r.get('threshold_95'):
                result_copy['threshold_95'] = convert_value(r['threshold_95'])
            
            json_results.append(result_copy)
        
        with open(args.json_output, 'w') as f:
            json.dump(json_results, f, indent=2)
        print(f"\n✓ Results saved to {args.json_output}")
    
    print("\n✅ Analysis complete!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
