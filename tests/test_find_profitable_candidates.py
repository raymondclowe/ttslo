#!/usr/bin/env python3
"""
Tests for find_profitable_candidates tool
"""
import sys
import os
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

from find_profitable_candidates import CandidateAnalyzer
from kraken_api import KrakenAPI


class TestCandidateAnalyzer:
    """Test CandidateAnalyzer class."""
    
    def test_calculate_oscillations_basic(self):
        """Test basic oscillation calculation."""
        api = KrakenAPI()
        analyzer = CandidateAnalyzer(api, hours=48)
        
        # Create test candles with known oscillations
        # Format: [time, open, high, low, close, vwap, volume, count]
        candles = [
            [1000, '100.0', '105.0', '95.0', '100.0', '100.0', '10', 100],
            [2000, '100.0', '110.0', '90.0', '102.0', '100.0', '10', 100],  # +2%
            [3000, '102.0', '108.0', '96.0', '98.0', '100.0', '10', 100],   # -3.92%
            [4000, '98.0', '105.0', '92.0', '100.0', '100.0', '10', 100],   # +2.04%
        ]
        
        stats = analyzer.calculate_oscillations(candles)
        
        assert stats is not None
        assert len(stats['oscillations']) == 3
        assert stats['total_periods'] == 3
        assert stats['current_price'] == 100.0
        assert stats['avg_oscillation'] > 0
        assert stats['max_oscillation'] > 0
        assert stats['std_dev'] > 0
    
    def test_calculate_oscillations_single_candle(self):
        """Test oscillation calculation with single candle (should return None)."""
        api = KrakenAPI()
        analyzer = CandidateAnalyzer(api, hours=48)
        
        candles = [
            [1000, '100.0', '105.0', '95.0', '100.0', '100.0', '10', 100],
        ]
        
        stats = analyzer.calculate_oscillations(candles)
        assert stats is None
    
    def test_calculate_oscillations_no_candles(self):
        """Test oscillation calculation with no candles."""
        api = KrakenAPI()
        analyzer = CandidateAnalyzer(api, hours=48)
        
        stats = analyzer.calculate_oscillations([])
        assert stats is None
    
    def test_significant_swings_detection(self):
        """Test detection of significant swings."""
        api = KrakenAPI()
        analyzer = CandidateAnalyzer(api, hours=48, min_oscillation=2.0)
        
        # Create candles with some significant moves
        candles = [
            [1000, '100.0', '105.0', '95.0', '100.0', '100.0', '10', 100],
            [2000, '100.0', '110.0', '90.0', '103.0', '100.0', '10', 100],  # +3% (significant)
            [3000, '103.0', '108.0', '96.0', '104.0', '100.0', '10', 100],  # +0.97%
            [4000, '104.0', '108.0', '98.0', '102.0', '100.0', '10', 100],  # -1.92%
            [5000, '102.0', '108.0', '95.0', '98.0', '100.0', '10', 100],   # -3.92% (significant)
        ]
        
        stats = analyzer.calculate_oscillations(candles)
        
        assert stats['significant_swings'] == 2
        assert stats['total_periods'] == 4
    
    def test_direction_changes(self):
        """Test counting of direction changes."""
        api = KrakenAPI()
        analyzer = CandidateAnalyzer(api, hours=48)
        
        # Create alternating up/down pattern
        candles = [
            [1000, '100.0', '105.0', '95.0', '100.0', '100.0', '10', 100],
            [2000, '100.0', '110.0', '90.0', '102.0', '100.0', '10', 100],  # up
            [3000, '102.0', '108.0', '96.0', '98.0', '100.0', '10', 100],   # down (change)
            [4000, '98.0', '105.0', '92.0', '100.0', '100.0', '10', 100],   # up (change)
            [5000, '100.0', '105.0', '95.0', '98.0', '100.0', '10', 100],   # down (change)
        ]
        
        stats = analyzer.calculate_oscillations(candles)
        
        assert stats['direction_changes'] == 3
    
    def test_probability_calculation_high_volatility(self):
        """Test probability calculation with high volatility."""
        api = KrakenAPI()
        analyzer = CandidateAnalyzer(api, hours=48)
        
        # High volatility scenario - many target hits
        # We need at least 10 periods for the probability calculation to work
        oscillations = [5.0, -4.0, 6.0, -5.5, 4.5, -3.0, 5.0, -4.5, 5.5, -4.0, 6.0]
        stats = {
            'oscillations': oscillations,
            'avg_oscillation': 4.8,
            'max_oscillation': 6.0,
            'std_dev': 0.9,
            'significant_swings': 11,
            'direction_changes': 10,
            'total_periods': len(oscillations),
            'current_price': 100.0
        }
        
        prob = analyzer.calculate_profit_probability(stats, target_profit_pct=3.0)
        
        assert prob['probability'] > 0.5  # Should be high probability
        assert prob['confidence'] in ['low', 'medium']  # 11 periods = low to medium
        assert prob['historical_hits'] == 11  # All exceed 3%
    
    def test_probability_calculation_low_volatility(self):
        """Test probability calculation with low volatility."""
        api = KrakenAPI()
        analyzer = CandidateAnalyzer(api, hours=48)
        
        # Low volatility scenario - no target hits
        oscillations = [0.5, -0.3, 0.4, -0.6, 0.3, -0.4, 0.5, -0.3] * 6
        stats = {
            'oscillations': oscillations,
            'avg_oscillation': 0.4,
            'max_oscillation': 0.6,
            'std_dev': 0.1,
            'significant_swings': 0,
            'direction_changes': 23,
            'total_periods': len(oscillations),
            'current_price': 100.0
        }
        
        prob = analyzer.calculate_profit_probability(stats, target_profit_pct=5.0)
        
        assert prob['probability'] < 0.1  # Should be low probability
        assert prob['confidence'] == 'low'  # Low because no historical hits
        assert prob['historical_hits'] == 0
    
    def test_probability_calculation_moderate(self):
        """Test probability calculation with moderate volatility."""
        api = KrakenAPI()
        analyzer = CandidateAnalyzer(api, hours=48)
        
        # Moderate volatility - occasional target hits
        oscillations = []
        for _ in range(10):
            oscillations.extend([1.0, -0.8, 0.9, -1.1])  # Small moves
        oscillations.extend([3.0, -2.5, 3.5])  # A few larger moves
        
        stats = {
            'oscillations': oscillations,
            'avg_oscillation': 1.2,
            'max_oscillation': 3.5,
            'std_dev': 1.0,
            'significant_swings': 3,
            'direction_changes': 30,
            'total_periods': len(oscillations),
            'current_price': 100.0
        }
        
        prob = analyzer.calculate_profit_probability(stats, target_profit_pct=2.5)
        
        assert 0.05 < prob['probability'] < 0.3  # Moderate probability
        assert prob['confidence'] in ['medium', 'high']
        assert prob['historical_hits'] >= 1
    
    def test_format_pair_name(self):
        """Test pair name formatting."""
        api = KrakenAPI()
        analyzer = CandidateAnalyzer(api, hours=48)
        
        # Test major cryptocurrencies
        assert analyzer.format_pair_name('XXBTZUSD') == 'BTC/USD'
        assert analyzer.format_pair_name('XETHZUSD') == 'ETH/USD'
        assert analyzer.format_pair_name('SOLUSD') == 'SOL/USD'
        assert analyzer.format_pair_name('XLTCZUSD') == 'LTC/USD'
        assert analyzer.format_pair_name('XXRPZUSD') == 'XRP/USD'
        assert analyzer.format_pair_name('XXMRZUSD') == 'XMR/USD'
        
        # Test DeFi and smart contract platforms
        assert analyzer.format_pair_name('AAVEUSD') == 'AAVE/USD'
        assert analyzer.format_pair_name('ATOMUSD') == 'ATOM/USD'
        assert analyzer.format_pair_name('NEARUSD') == 'NEAR/USD'
        
        # Test meme coins
        assert analyzer.format_pair_name('BONKUSD') == 'BONK/USD'
        assert analyzer.format_pair_name('DOGSUSD') == 'DOGE/USD'
        assert analyzer.format_pair_name('PEPEUSD') == 'PEPE/USD'
        assert analyzer.format_pair_name('TRUMPUSD') == 'TRUMP/USD'
        
        # Test other popular coins
        assert analyzer.format_pair_name('RENDERUSD') == 'RENDER/USD'
        assert analyzer.format_pair_name('TONUSD') == 'TON/USD'
        
        # Test unknown pair (should return as-is)
        assert analyzer.format_pair_name('UNKNOWN') == 'UNKNOWN'
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient data."""
        api = KrakenAPI()
        analyzer = CandidateAnalyzer(api, hours=48)
        
        # Too few periods
        stats = {
            'oscillations': [1.0, -0.5],
            'avg_oscillation': 0.75,
            'max_oscillation': 1.0,
            'std_dev': 0.5,
            'significant_swings': 0,
            'direction_changes': 1,
            'total_periods': 2,
            'current_price': 100.0
        }
        
        prob = analyzer.calculate_profit_probability(stats, target_profit_pct=2.0)
        
        assert prob['probability'] == 0
        assert prob['confidence'] == 'low'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
