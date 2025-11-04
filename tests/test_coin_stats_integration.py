"""
Integration tests for coin_stats.py profit-based config generation.
Tests the complete workflow from statistics to config generation.
"""
import sys
import os
import tempfile
import csv
from unittest.mock import MagicMock, patch
import math

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.coin_stats import (
    CoinStatsAnalyzer, 
    generate_config_suggestions,
    calculate_profit_based_params
)


def create_mock_analyzer():
    """Create a mock CoinStatsAnalyzer with necessary methods."""
    analyzer = MagicMock(spec=CoinStatsAnalyzer)
    analyzer.format_pair_name.side_effect = lambda x: x.replace('USD', '/USD')
    
    # Mock calculate_probability_threshold for legacy mode
    analyzer.calculate_probability_threshold.return_value = {
        'threshold_pct': 5.0,  # Higher than typical bracket offset
        'threshold_price_up': 105.0,
        'threshold_price_down': 95.0,
        'confidence': 'high'
    }
    
    # Mock API with get_asset_pair_info
    mock_api = MagicMock()
    mock_api.get_asset_pair_info.return_value = {'ordermin': '0.0001'}
    analyzer.api = mock_api
    
    return analyzer


def create_high_volatility_stats():
    """Create stats for a high volatility coin."""
    return {
        'mean': 100.0,
        'median': 100.0,
        'stdev': 5.0,
        'min_price': 90.0,
        'max_price': 110.0,
        'range': 20.0,
        'count': 2880,  # 2 days of minute data
        'pct_mean': 0.0,
        'pct_median': 0.0,
        'pct_stdev': 0.5,  # 0.5% per minute (high volatility)
        'distribution_fit': {
            'best_fit': 'normal',
            'df': None,
            'distribution': 'normal',
            'fit_quality': 'good',
            'p_value': 0.15
        }
    }


def create_low_volatility_stats():
    """Create stats for a low volatility coin."""
    return {
        'mean': 50.0,
        'median': 50.0,
        'stdev': 0.5,
        'min_price': 49.5,
        'max_price': 50.5,
        'range': 1.0,
        'count': 2880,
        'pct_mean': 0.0,
        'pct_median': 0.0,
        'pct_stdev': 0.05,  # 0.05% per minute (low volatility)
        'distribution_fit': {
            'best_fit': 'normal',
            'df': None,
            'distribution': 'normal',
            'fit_quality': 'good',
            'p_value': 0.12
        }
    }


def test_profit_based_config_generation_integration():
    """Test complete profit-based config generation workflow."""
    # Create mock data
    results = [
        {'pair': 'BTCUSD', 'stats': create_high_volatility_stats()},
        {'pair': 'ETHUSD', 'stats': create_low_volatility_stats()},
    ]
    
    analyzer = create_mock_analyzer()
    
    # Generate config in profit-based mode
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        output_file = f.name
    
    try:
        result = generate_config_suggestions(
            results, analyzer, output_file,
            target_profit_pct=5.0,
            profit_days=7,
            target_usd_volume=1.0
        )
        
        assert result == output_file
        
        # Read generated config
        with open(output_file, 'r') as f:
            reader = csv.DictReader(f)
            entries = list(reader)
        
        # Should have entries for high volatility coin
        # Low volatility coin should be excluded
        assert len(entries) > 0, "Should generate at least some entries"
        
        # Check that entries have proper fields
        for entry in entries:
            assert 'id' in entry
            assert 'pair' in entry
            assert 'threshold_price' in entry
            assert 'threshold_type' in entry
            assert 'direction' in entry
            assert 'volume' in entry
            assert 'trailing_offset_percent' in entry
            assert 'enabled' in entry
            
            # Check trailing offset is >= 1.0
            trailing_offset = float(entry['trailing_offset_percent'])
            assert trailing_offset >= 1.0, "Trailing offset must be >= 1.0%"
            
            # Check threshold type is valid
            assert entry['threshold_type'] in ['above', 'below']
            
            # Check direction matches threshold type
            if entry['threshold_type'] == 'above':
                assert entry['direction'] == 'sell'
            else:
                assert entry['direction'] == 'buy'
    
    finally:
        if os.path.exists(output_file):
            os.unlink(output_file)


def test_legacy_mode_still_works():
    """Test that legacy mode (without target_profit_pct) still works."""
    results = [
        {'pair': 'BTCUSD', 'stats': create_high_volatility_stats()},
    ]
    
    analyzer = create_mock_analyzer()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        output_file = f.name
    
    try:
        # Call without target_profit_pct (legacy mode)
        result = generate_config_suggestions(
            results, analyzer, output_file,
            bracket_offset_pct=2.0,
            trailing_offset_pct=1.0,
            target_usd_volume=1.0,
            target_profit_pct=None  # Legacy mode
        )
        
        assert result == output_file
        
        # Read generated config
        with open(output_file, 'r') as f:
            reader = csv.DictReader(f)
            entries = list(reader)
        
        # Should generate entries for high volatility coin
        assert len(entries) == 2, "Should generate 2 entries (buy + sell) in legacy mode"
        
        # Check trailing offset matches requested value
        for entry in entries:
            assert float(entry['trailing_offset_percent']) == 1.0
    
    finally:
        if os.path.exists(output_file):
            os.unlink(output_file)


def test_unsuitable_pairs_reported():
    """Test that unsuitable pairs are properly reported."""
    # All low volatility
    results = [
        {'pair': 'STABLE1USD', 'stats': create_low_volatility_stats()},
        {'pair': 'STABLE2USD', 'stats': create_low_volatility_stats()},
    ]
    
    analyzer = create_mock_analyzer()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        output_file = f.name
    
    try:
        # Request high profit (10%) with low volatility coins
        with patch('builtins.print') as mock_print:
            result = generate_config_suggestions(
                results, analyzer, output_file,
                target_profit_pct=10.0,
                profit_days=7,
                target_usd_volume=1.0
            )
        
        # Check that unsuitable pairs message was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        unsuitable_message_found = any('UNSUITABLE PAIRS' in str(call) for call in print_calls)
        assert unsuitable_message_found, "Should print unsuitable pairs message"
        
        # Config file should have few or no entries
        with open(output_file, 'r') as f:
            reader = csv.DictReader(f)
            entries = list(reader)
        
        # With very low volatility and high profit target, should have no entries
        assert len(entries) == 0, "Should generate no entries for unsuitable pairs"
    
    finally:
        if os.path.exists(output_file):
            os.unlink(output_file)


def test_profit_calculation_accuracy():
    """Test that profit calculation properly accounts for trailing offset."""
    stats = create_high_volatility_stats()
    analyzer = create_mock_analyzer()
    
    # Request 5% profit
    result = calculate_profit_based_params(
        stats, analyzer, target_profit_pct=5.0, profit_days=7
    )
    
    if result['achievable']:
        # Total movement should be profit + trailing offset
        expected_movement = 5.0 + result['trailing_offset_pct']
        # Allow small tolerance for floating point
        assert abs(result['total_movement_needed_pct'] - expected_movement) < 0.1, \
            f"Movement {result['total_movement_needed_pct']} should equal profit + trailing offset {expected_movement}"


def test_different_profit_days_affects_results():
    """Test that different profit_days values affect calculations."""
    stats = create_high_volatility_stats()
    analyzer = create_mock_analyzer()
    
    # Try with 3 days
    result_3d = calculate_profit_based_params(
        stats, analyzer, target_profit_pct=5.0, profit_days=3
    )
    
    # Try with 14 days
    result_14d = calculate_profit_based_params(
        stats, analyzer, target_profit_pct=5.0, profit_days=14
    )
    
    # With more days, volatility accumulates: σ_14d = σ_minute × sqrt(14*1440)
    # So longer window should make same profit target more achievable
    # (either higher probability or lower trailing offset needed)
    if result_3d['achievable'] and result_14d['achievable']:
        # 14 days should be more favorable
        assert (result_14d['probability'] >= result_3d['probability'] or
                result_14d['trailing_offset_pct'] <= result_3d['trailing_offset_pct']), \
            "Longer profit window should be more favorable"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
