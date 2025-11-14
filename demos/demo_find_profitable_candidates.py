#!/usr/bin/env python3
"""
Demo script for find_profitable_candidates tool

This script demonstrates the tool's capabilities with sample data.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.find_profitable_candidates import CandidateAnalyzer, OrderCreator
from kraken_api import KrakenAPI


def demo_volatility_analysis():
    """Demonstrate volatility analysis with sample data."""
    print("=" * 70)
    print("DEMO: Volatility Analysis")
    print("=" * 70)
    
    api = KrakenAPI()
    analyzer = CandidateAnalyzer(api, hours=48, min_oscillation=2.0)
    
    # Create sample OHLC data representing high volatility
    print("\n📊 Sample 1: High Volatility Pair")
    high_volatility_candles = []
    base_price = 100.0
    for i in range(50):
        # Simulate oscillating price
        if i % 2 == 0:
            close = base_price * (1 + 0.05)  # +5%
        else:
            close = base_price * (1 - 0.04)  # -4%
        
        candles = [i * 3600, str(base_price), str(base_price * 1.06), 
                   str(base_price * 0.94), str(close), str(base_price), '100', 1000]
        high_volatility_candles.append(candles)
        base_price = close
    
    stats = analyzer.calculate_oscillations(high_volatility_candles)
    print(f"\nVolatility Metrics:")
    print(f"  Average Oscillation: {stats['avg_oscillation']:.2f}%")
    print(f"  Maximum Oscillation: {stats['max_oscillation']:.2f}%")
    print(f"  Standard Deviation: {stats['std_dev']:.2f}%")
    print(f"  Significant Swings: {stats['significant_swings']}/{stats['total_periods']}")
    print(f"  Direction Changes: {stats['direction_changes']}")
    
    prob = analyzer.calculate_profit_probability(stats, target_profit_pct=3.0)
    print(f"\nProfit Opportunity (Target: 3.0%):")
    print(f"  Historical Hits: {prob['historical_hits']}/{stats['total_periods']}")
    print(f"  Probability: {prob['probability']*100:.1f}%")
    print(f"  Expected Time: {prob['expected_time_hours']:.1f} hours")
    print(f"  Confidence: {prob['confidence'].upper()}")
    
    # Low volatility example
    print("\n\n📊 Sample 2: Low Volatility Pair")
    low_volatility_candles = []
    base_price = 100.0
    for i in range(50):
        # Simulate stable price with small moves
        close = base_price * (1 + (0.002 if i % 2 == 0 else -0.002))  # ±0.2%
        
        candles = [i * 3600, str(base_price), str(base_price * 1.005), 
                   str(base_price * 0.995), str(close), str(base_price), '100', 1000]
        low_volatility_candles.append(candles)
        base_price = close
    
    stats = analyzer.calculate_oscillations(low_volatility_candles)
    print(f"\nVolatility Metrics:")
    print(f"  Average Oscillation: {stats['avg_oscillation']:.2f}%")
    print(f"  Maximum Oscillation: {stats['max_oscillation']:.2f}%")
    print(f"  Standard Deviation: {stats['std_dev']:.2f}%")
    print(f"  Significant Swings: {stats['significant_swings']}/{stats['total_periods']}")
    print(f"  Direction Changes: {stats['direction_changes']}")
    
    prob = analyzer.calculate_profit_probability(stats, target_profit_pct=3.0)
    print(f"\nProfit Opportunity (Target: 3.0%):")
    print(f"  Historical Hits: {prob['historical_hits']}/{stats['total_periods']}")
    print(f"  Probability: {prob['probability']*100:.1f}%")
    print(f"  Expected Time: {prob['expected_time_hours']:.1f} hours")
    print(f"  Confidence: {prob['confidence'].upper()}")


def demo_order_creation():
    """Demonstrate order creation (dry run only)."""
    print("\n\n" + "=" * 70)
    print("DEMO: Order Creation (Dry Run)")
    print("=" * 70)
    
    api = KrakenAPI()
    order_creator = OrderCreator(api)
    
    # Demo bracket orders
    print("\n📊 Creating Bracket Orders:")
    result = order_creator.create_bracket_orders(
        pair='XXBTZUSD',
        current_price=50000.0,
        volume=0.001,
        target_profit_pct=5.0,
        dry_run=True
    )
    
    if result:
        print(f"\n✅ Demo completed successfully!")
        print(f"   Buy order would be placed at: ${result['buy_order']['price']:,.2f}")
        print(f"   Sell order would be placed at: ${result['sell_order']['price']:,.2f}")


def demo_probability_scenarios():
    """Demonstrate probability calculations for various scenarios."""
    print("\n\n" + "=" * 70)
    print("DEMO: Probability Scenarios")
    print("=" * 70)
    
    api = KrakenAPI()
    analyzer = CandidateAnalyzer(api, hours=48)
    
    scenarios = [
        ("Highly Volatile - Frequent Swings", 
         [5.0, -4.5, 5.5, -4.0, 6.0, -5.0] * 8, 3.0),
        ("Moderate - Occasional Swings",
         [1.0, -0.8, 0.9, -1.1, 2.5, -2.0] * 8, 2.0),
        ("Low Volatility - Rare Swings",
         [0.3, -0.2, 0.4, -0.3, 0.5, -0.4] * 8, 2.0),
    ]
    
    for name, oscillations, target in scenarios:
        print(f"\n📊 Scenario: {name}")
        print(f"   Target Profit: {target}%")
        
        stats = {
            'oscillations': oscillations,
            'avg_oscillation': sum(abs(x) for x in oscillations) / len(oscillations),
            'max_oscillation': max(abs(x) for x in oscillations),
            'std_dev': (sum(x**2 for x in oscillations) / len(oscillations)) ** 0.5,
            'significant_swings': sum(1 for x in oscillations if abs(x) >= 2.0),
            'direction_changes': sum(1 for i in range(1, len(oscillations)) 
                                   if (oscillations[i] > 0) != (oscillations[i-1] > 0)),
            'total_periods': len(oscillations),
            'current_price': 100.0
        }
        
        prob = analyzer.calculate_profit_probability(stats, target_profit_pct=target)
        
        print(f"   Average Oscillation: {stats['avg_oscillation']:.2f}%")
        print(f"   Significant Swings: {stats['significant_swings']}/{stats['total_periods']}")
        print(f"   Historical Hits: {prob['historical_hits']}/{stats['total_periods']}")
        print(f"   Probability: {prob['probability']*100:.1f}%")
        print(f"   Expected Time: {prob['expected_time_hours']:.1f} hours")
        
        # Rating
        if prob['probability'] >= 0.3:
            rating = "✅ GOOD CANDIDATE"
        elif prob['probability'] >= 0.2:
            rating = "⚠️  MODERATE CANDIDATE"
        else:
            rating = "❌ POOR CANDIDATE"
        print(f"   Rating: {rating}")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print(" FIND PROFITABLE CANDIDATES - DEMO")
    print("=" * 70)
    print("\nThis demo showcases the tool's analysis capabilities using sample data.")
    print("No actual API calls or orders will be created.\n")
    
    try:
        demo_volatility_analysis()
        demo_probability_scenarios()
        demo_order_creation()
        
        print("\n\n" + "=" * 70)
        print("DEMO COMPLETE")
        print("=" * 70)
        print("\nTo use the tool with real data:")
        print("  uv run python tools/find_profitable_candidates.py")
        print("\nFor interactive mode (dry-run):")
        print("  uv run python tools/find_profitable_candidates.py --interactive --dry-run")
        print("\nFor help:")
        print("  uv run python tools/find_profitable_candidates.py --help")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted.")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
