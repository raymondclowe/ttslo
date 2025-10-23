#!/usr/bin/env python3
"""
Find Profitable Trading Candidates

Analyzes recent hourly price data to identify volatile pairs with repeated
oscillations that could be profitable for bracketing strategies.
"""
import sys
import os
import argparse
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import statistics

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kraken_api import KrakenAPI
from creds import load_env


class CandidateAnalyzer:
    """Analyzes trading pairs for profitable bracketing opportunities."""
    
    def __init__(self, api, hours=48, min_oscillation=2.0):
        """
        Initialize analyzer.
        
        Args:
            api: KrakenAPI instance
            hours: Number of hours of historical data to analyze (default: 48)
            min_oscillation: Minimum oscillation percentage to consider (default: 2.0%)
        """
        self.api = api
        self.hours = hours
        self.min_oscillation = min_oscillation
    
    def fetch_ohlc_data(self, pair, interval=60):
        """
        Fetch OHLC data for a pair.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD')
            interval: Interval in minutes (default: 60 for hourly)
            
        Returns:
            List of OHLC candles: [[time, open, high, low, close, vwap, volume, count], ...]
        """
        result = self.api.get_ohlc(pair, interval=interval)
        
        # Find the pair key (not 'last')
        pair_keys = [k for k in result.keys() if k != 'last']
        if not pair_keys:
            return []
        
        candles = result[pair_keys[0]]
        
        # Filter to only include recent data (last N hours)
        cutoff_time = time.time() - (self.hours * 3600)
        recent_candles = [c for c in candles if c[0] >= cutoff_time]
        
        return recent_candles
    
    def calculate_oscillations(self, candles):
        """
        Calculate price oscillations from OHLC data.
        
        Args:
            candles: List of OHLC candles
            
        Returns:
            dict with analysis results:
            - oscillations: List of % moves between consecutive closes
            - avg_oscillation: Average absolute oscillation
            - max_oscillation: Maximum oscillation
            - std_dev: Standard deviation of oscillations
            - significant_swings: Count of swings > min_oscillation
        """
        if len(candles) < 2:
            return None
        
        # Extract close prices
        closes = [float(c[4]) for c in candles]
        
        # Calculate percentage changes between consecutive closes
        oscillations = []
        for i in range(1, len(closes)):
            pct_change = ((closes[i] - closes[i-1]) / closes[i-1]) * 100
            oscillations.append(pct_change)
        
        # Calculate statistics
        abs_oscillations = [abs(x) for x in oscillations]
        avg_oscillation = statistics.mean(abs_oscillations)
        max_oscillation = max(abs_oscillations)
        std_dev = statistics.stdev(oscillations) if len(oscillations) > 1 else 0
        
        # Count significant swings (absolute moves > min_oscillation)
        significant_swings = sum(1 for x in abs_oscillations if x >= self.min_oscillation)
        
        # Count directional changes (up/down alternations)
        direction_changes = 0
        for i in range(1, len(oscillations)):
            if (oscillations[i] > 0) != (oscillations[i-1] > 0):
                direction_changes += 1
        
        return {
            'oscillations': oscillations,
            'avg_oscillation': avg_oscillation,
            'max_oscillation': max_oscillation,
            'std_dev': std_dev,
            'significant_swings': significant_swings,
            'direction_changes': direction_changes,
            'total_periods': len(oscillations),
            'current_price': closes[-1]
        }
    
    def calculate_profit_probability(self, stats, target_profit_pct=5.0):
        """
        Estimate probability of achieving target profit using bracketing.
        
        Uses historical oscillation data to estimate likelihood that price will
        move by target amount within reasonable timeframe.
        
        Args:
            stats: Statistics from calculate_oscillations
            target_profit_pct: Target profit percentage (default: 5%)
            
        Returns:
            dict with probability estimates:
            - probability: Estimated probability of hitting target (0-1)
            - expected_time_hours: Expected time to hit target
            - confidence: Confidence level based on data quality
        """
        if not stats or stats['total_periods'] < 10:
            return {'probability': 0, 'expected_time_hours': 0, 'confidence': 'low'}
        
        std_dev = stats['std_dev']
        avg_osc = stats['avg_oscillation']
        max_osc = stats['max_oscillation']
        
        # Count how many times we exceeded the target in either direction
        exceeds_target = sum(1 for osc in stats['oscillations'] if abs(osc) >= target_profit_pct)
        
        # Base probability on historical frequency
        historical_prob = exceeds_target / stats['total_periods']
        
        # If we've never hit the target but max_osc came close, estimate probability
        if exceeds_target == 0:
            if max_osc >= target_profit_pct * 0.8:
                # Came close, use std dev model
                # Probability of exceeding target in a normal distribution
                # If target < 2*std_dev, there's reasonable probability
                if target_profit_pct <= std_dev:
                    historical_prob = 0.35
                elif target_profit_pct <= 2 * std_dev:
                    historical_prob = 0.20
                else:
                    historical_prob = 0.05
            else:
                # Never came close, very low probability
                historical_prob = 0.02
        
        # Adjust for consistency of oscillations (direction changes)
        # More oscillations = better for bracketing strategy
        oscillation_frequency = stats['direction_changes'] / stats['total_periods']
        consistency_factor = 1.0 + (oscillation_frequency * 0.5)  # Up to 1.5x boost
        
        # Final probability
        probability = historical_prob * consistency_factor
        probability = min(probability, 0.95)  # Cap at 95%
        
        # Expected time calculation
        if exceeds_target > 0:
            # Average periods between target hits
            periods_between_hits = stats['total_periods'] / exceeds_target
            expected_time_hours = periods_between_hits
        elif historical_prob > 0.15:
            # Estimate based on probability
            expected_time_hours = 1.0 / max(historical_prob, 0.01)
        else:
            expected_time_hours = self.hours * 2  # Longer than observed period
        
        # Confidence based on data points and consistency
        if stats['total_periods'] >= 40 and exceeds_target >= 3:
            confidence = 'high'
        elif stats['total_periods'] >= 20 and exceeds_target >= 1:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        return {
            'probability': probability,
            'expected_time_hours': expected_time_hours,
            'confidence': confidence,
            'historical_hits': exceeds_target
        }
    
    def analyze_pair(self, pair, target_profit_pct=5.0):
        """
        Analyze a trading pair for profitability.
        
        Args:
            pair: Trading pair to analyze
            target_profit_pct: Target profit percentage
            
        Returns:
            dict with complete analysis or None if insufficient data
        """
        try:
            candles = self.fetch_ohlc_data(pair)
            if len(candles) < 10:
                return None
            
            stats = self.calculate_oscillations(candles)
            if not stats:
                return None
            
            prob_info = self.calculate_profit_probability(stats, target_profit_pct)
            
            return {
                'pair': pair,
                'stats': stats,
                'probability': prob_info,
                'target_profit_pct': target_profit_pct
            }
        except Exception as e:
            print(f"Error analyzing {pair}: {e}")
            return None
    
    def format_pair_name(self, pair):
        """Convert Kraken pair format to readable format."""
        # Common conversions
        conversions = {
            'XXBTZUSD': 'BTC/USD',
            'XETHZUSD': 'ETH/USD',
            'XXBTZUSDT': 'BTC/USDT',
            'XETHZUSDT': 'ETH/USDT',
            'XXRPZUSD': 'XRP/USD',
            'XLTCZUSD': 'LTC/USD',
            'ADAUSD': 'ADA/USD',
            'SOLUSD': 'SOL/USD',
            'DOTUSD': 'DOT/USD',
            'MATICUSD': 'MATIC/USD',
        }
        return conversions.get(pair, pair)
    
    def print_analysis(self, analysis):
        """Print analysis results in readable format."""
        if not analysis:
            return
        
        pair = self.format_pair_name(analysis['pair'])
        stats = analysis['stats']
        prob = analysis['probability']
        target = analysis['target_profit_pct']
        
        print(f"\n{'='*70}")
        print(f"Pair: {pair}")
        print(f"Current Price: ${stats['current_price']:,.2f}")
        print(f"{'='*70}")
        
        print(f"\nVolatility Metrics:")
        print(f"  Average Oscillation: {stats['avg_oscillation']:.2f}%")
        print(f"  Maximum Oscillation: {stats['max_oscillation']:.2f}%")
        print(f"  Standard Deviation: {stats['std_dev']:.2f}%")
        print(f"  Significant Swings (>{self.min_oscillation}%): {stats['significant_swings']}/{stats['total_periods']} periods")
        print(f"  Direction Changes: {stats['direction_changes']}")
        
        print(f"\nProfit Opportunity (Target: {target}%):")
        print(f"  Historical Hits: {prob.get('historical_hits', 0)}/{stats['total_periods']} periods")
        print(f"  Probability: {prob['probability']*100:.1f}%")
        print(f"  Expected Time: {prob['expected_time_hours']:.1f} hours")
        print(f"  Confidence: {prob['confidence'].upper()}")
        
        # Recommendation
        if prob['probability'] >= 0.3 and stats['significant_swings'] >= 5:
            print(f"\n✅ GOOD CANDIDATE - High volatility with frequent oscillations")
        elif prob['probability'] >= 0.2:
            print(f"\n⚠️  MODERATE CANDIDATE - Some potential but lower probability")
        else:
            print(f"\n❌ POOR CANDIDATE - Low volatility or insufficient oscillations")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Find profitable trading candidates based on volatility analysis'
    )
    parser.add_argument(
        '--pairs',
        nargs='+',
        default=['XXBTZUSD', 'XETHZUSD', 'XXBTZUSDT', 'XETHZUSDT'],
        help='Trading pairs to analyze (default: BTC/USD, ETH/USD, BTC/USDT, ETH/USDT)'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=48,
        help='Hours of historical data to analyze (default: 48)'
    )
    parser.add_argument(
        '--target-profit',
        type=float,
        default=5.0,
        help='Target profit percentage (default: 5.0)'
    )
    parser.add_argument(
        '--min-oscillation',
        type=float,
        default=2.0,
        help='Minimum oscillation to consider significant (default: 2.0%%)'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=None,
        help='Show only top N candidates (default: all)'
    )
    
    args = parser.parse_args()
    
    # Load environment and create API client
    load_env()
    api = KrakenAPI()
    
    # Create analyzer
    analyzer = CandidateAnalyzer(api, hours=args.hours, min_oscillation=args.min_oscillation)
    
    print(f"Analyzing {len(args.pairs)} trading pairs...")
    print(f"Historical data: {args.hours} hours")
    print(f"Target profit: {args.target_profit}%")
    print(f"Min significant oscillation: {args.min_oscillation}%")
    
    # Analyze all pairs
    results = []
    for pair in args.pairs:
        print(f"\nFetching data for {analyzer.format_pair_name(pair)}...", end=' ')
        analysis = analyzer.analyze_pair(pair, target_profit_pct=args.target_profit)
        if analysis:
            results.append(analysis)
            print("✓")
        else:
            print("✗ (insufficient data)")
    
    if not results:
        print("\n❌ No candidates found with sufficient data.")
        return 1
    
    # Sort by probability (descending)
    results.sort(key=lambda x: x['probability']['probability'], reverse=True)
    
    # Limit to top N if specified
    if args.top:
        results = results[:args.top]
    
    # Print results
    print(f"\n\n{'#'*70}")
    print(f"# ANALYSIS RESULTS")
    print(f"{'#'*70}")
    
    for i, analysis in enumerate(results, 1):
        analyzer.print_analysis(analysis)
    
    # Summary
    print(f"\n\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total pairs analyzed: {len(args.pairs)}")
    print(f"Pairs with sufficient data: {len(results)}")
    
    good_candidates = [r for r in results if r['probability']['probability'] >= 0.3]
    moderate_candidates = [r for r in results if 0.2 <= r['probability']['probability'] < 0.3]
    poor_candidates = [r for r in results if r['probability']['probability'] < 0.2]
    
    print(f"\nGood candidates (≥30% probability): {len(good_candidates)}")
    print(f"Moderate candidates (20-30% probability): {len(moderate_candidates)}")
    print(f"Poor candidates (<20% probability): {len(poor_candidates)}")
    
    if good_candidates:
        print(f"\n🎯 Top recommendation:")
        top = good_candidates[0]
        pair = analyzer.format_pair_name(top['pair'])
        prob = top['probability']['probability'] * 100
        profit = top['target_profit_pct']
        hours = top['probability']['expected_time_hours']
        print(f"   {pair} has a {prob:.1f}% probability of making a {profit}% profit in ~{hours:.0f} hours")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
