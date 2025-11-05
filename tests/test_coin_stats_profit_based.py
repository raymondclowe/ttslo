"""
Tests for coin_stats.py profit-based config generation.
"""
import sys
import os
from unittest.mock import MagicMock, patch
import math

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.coin_stats import calculate_profit_based_params, CoinStatsAnalyzer


def test_calculate_profit_based_params_achievable():
    """Test that calculate_profit_based_params correctly identifies achievable targets."""
    # Create mock stats with good volatility
    stats = {
        'pct_stdev': 0.5,  # 0.5% per minute
        'distribution_fit': {
            'best_fit': 'normal',
            'df': None
        }
    }
    
    # Mock analyzer
    analyzer = MagicMock()
    
    # Calculate for 5% profit over 7 days
    result = calculate_profit_based_params(stats, analyzer, target_profit_pct=5.0, profit_days=7)
    
    # Should be achievable with this volatility
    assert result is not None
    assert 'achievable' in result
    assert result['trigger_offset_pct'] > 0
    assert result['trailing_offset_pct'] >= 1.0  # Minimum TTSLO requirement
    assert result['plausible_profit_pct'] >= 0
    

def test_calculate_profit_based_params_insufficient_volatility():
    """Test that low volatility pairs are correctly identified as unsuitable."""
    # Create mock stats with very low volatility
    stats = {
        'pct_stdev': 0.01,  # Very low: 0.01% per minute
        'distribution_fit': {
            'best_fit': 'normal',
            'df': None
        }
    }
    
    # Mock analyzer
    analyzer = MagicMock()
    
    # Try to achieve 10% profit over 7 days (likely impossible)
    result = calculate_profit_based_params(stats, analyzer, target_profit_pct=10.0, profit_days=7)
    
    # Should identify as not achievable
    assert result is not None
    assert 'achievable' in result
    # Low volatility means plausible profit should be lower than target
    assert result['plausible_profit_pct'] < 10.0


def test_calculate_profit_based_params_zero_volatility():
    """Test handling of zero volatility (edge case)."""
    stats = {
        'pct_stdev': 0.0,  # Zero volatility
        'distribution_fit': {
            'best_fit': 'normal',
            'df': None
        }
    }
    
    analyzer = MagicMock()
    
    result = calculate_profit_based_params(stats, analyzer, target_profit_pct=5.0, profit_days=7)
    
    # Should return not achievable
    assert result is not None
    assert result['achievable'] == False
    assert result['plausible_profit_pct'] == 0
    assert 'reason' in result


def test_calculate_profit_based_params_missing_stats():
    """Test handling of missing statistics."""
    stats = {}  # Empty stats
    
    analyzer = MagicMock()
    
    result = calculate_profit_based_params(stats, analyzer, target_profit_pct=5.0, profit_days=7)
    
    # Should return not achievable with reason
    assert result is not None
    assert result['achievable'] == False
    assert 'reason' in result


def test_profit_includes_trailing_offset_slippage():
    """Test that profit calculation includes trailing offset slippage."""
    # High volatility stats
    stats = {
        'pct_stdev': 1.0,  # 1% per minute (high volatility)
        'distribution_fit': {
            'best_fit': 'normal',
            'df': None
        }
    }
    
    analyzer = MagicMock()
    
    # Request 5% profit
    result = calculate_profit_based_params(stats, analyzer, target_profit_pct=5.0, profit_days=7)
    
    # Total movement should be profit + trailing offset
    # total_movement = profit + trailing_offset
    expected_min_movement = 5.0 + result['trailing_offset_pct']
    assert result['total_movement_needed_pct'] >= expected_min_movement


def test_minimum_trailing_offset_respected():
    """Test that minimum trailing offset (1.0%) is always respected."""
    # Very high volatility
    stats = {
        'pct_stdev': 2.0,  # Very high volatility
        'distribution_fit': {
            'best_fit': 'normal',
            'df': None
        }
    }
    
    analyzer = MagicMock()
    
    result = calculate_profit_based_params(
        stats, analyzer, target_profit_pct=5.0, profit_days=7, min_trailing_offset_pct=1.0
    )
    
    # Even with high volatility, trailing offset should be at least 1.0%
    assert result['trailing_offset_pct'] >= 1.0


def test_student_t_distribution_handling():
    """Test that Student's t-distribution is handled correctly."""
    stats = {
        'pct_stdev': 0.5,
        'distribution_fit': {
            'best_fit': 'student_t',
            'df': 4  # Fat tails with df=4
        }
    }
    
    analyzer = MagicMock()
    
    result = calculate_profit_based_params(stats, analyzer, target_profit_pct=5.0, profit_days=7)
    
    # Should handle student_t distribution
    assert result is not None
    # Fat tails mean wider distribution, may need higher trigger offset
    assert result['trigger_offset_pct'] > 0


def test_probability_greater_than_50_percent():
    """Test that achievable configs have >50% probability."""
    # Moderate volatility
    stats = {
        'pct_stdev': 0.3,
        'distribution_fit': {
            'best_fit': 'normal',
            'df': None
        }
    }
    
    analyzer = MagicMock()
    
    # Request modest profit
    result = calculate_profit_based_params(stats, analyzer, target_profit_pct=3.0, profit_days=7)
    
    if result['achievable']:
        # If achievable, probability should be > 50%
        assert result['probability'] >= 0.50


def test_longer_profit_window_more_achievable():
    """Test that longer profit windows make targets more achievable."""
    stats = {
        'pct_stdev': 0.2,
        'distribution_fit': {
            'best_fit': 'normal',
            'df': None
        }
    }
    
    analyzer = MagicMock()
    
    # Try 7 days
    result_7d = calculate_profit_based_params(stats, analyzer, target_profit_pct=5.0, profit_days=7)
    
    # Try 14 days (should be more achievable)
    result_14d = calculate_profit_based_params(stats, analyzer, target_profit_pct=5.0, profit_days=14)
    
    # Longer window should have higher plausible profit
    # (or same target should have higher probability)
    if result_7d['achievable'] and result_14d['achievable']:
        # With longer window, either probability increases or trailing offset can decrease
        assert (result_14d['probability'] >= result_7d['probability'] or
                result_14d['trailing_offset_pct'] <= result_7d['trailing_offset_pct'])


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
