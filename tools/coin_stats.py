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
    
    def calculate_probability_threshold(self, stats, probability=0.95):
        """
        Calculate price threshold for a given probability.
        
        Using normal distribution assumption, calculate the price change
        that has X% probability of being exceeded within 24 hours.
        
        Args:
            stats: Statistics from calculate_statistics
            probability: Desired probability (0.95 = 95%)
            
        Returns:
            dict with threshold information:
            - threshold_pct: Percentage change threshold
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
        pct_stdev = stats.get('pct_stdev', 0)
        
        if pct_stdev == 0:
            return None
        
        # For normal distribution, 95% of values are within ~1.96 standard deviations
        # But we want to know what threshold will be exceeded
        # Use inverse CDF (ppf - percent point function)
        
        # Calculate z-score for the probability
        # For 95% probability of exceeding, we want the 5th percentile (lower tail)
        z_score = scipy_stats.norm.ppf(1 - probability)
        
        # Calculate threshold (absolute value)
        # We're interested in the magnitude of movement
        threshold_pct = abs(z_score * pct_stdev)
        
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
            'z_score': z_score,
            'pct_stdev': pct_stdev
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
            'XXBTZUSD', 'XETHZUSD', 'SOLUSD', 'XLTCZUSD', 'XXRPZUSD', 'XXMRZUSD',
            # DeFi and Smart Contract platforms
            'AAVEUSD', 'ATOMUSD', 'COMPUSD', 'DYDXUSD', 'EGLDUSD', 'ENSUSD',
            'FILUSD', 'INJUSD', 'NEARUSD',
            # Meme coins and trending tokens
            'BONKUSD', 'DOGSUSD', 'MEMEUSD', 'MEWUSD', 'PEPEUSD', 
            'PONKEUSD', 'POPCATUSD', 'TRUMPUSD',
            # Other popular coins
            'ATHUSD', 'NANOUSD', 'RAYUSD', 'RENDERUSD', 'SUPERUSD', 
            'TONUSD', 'TRXUSD', 'WALUSD',
        ],
        help='Trading pairs to analyze (default: 30 popular pairs)'
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
