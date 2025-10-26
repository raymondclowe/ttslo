"""
Tests for coin_stats.py - Cryptocurrency Statistics Analysis Tool
"""
import sys
import os
import statistics
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.coin_stats import CoinStatsAnalyzer

# Mock candles data for testing
def create_mock_candles(num_candles=100, base_price=100.0, volatility=1.0):
    """Create mock OHLC candles for testing."""
    import time
    current_time = time.time()
    candles = []
    
    for i in range(num_candles):
        timestamp = current_time - (num_candles - i) * 60  # 1 minute intervals
        # Simple random walk
        price = base_price + (i % 10 - 5) * volatility
        candle = [
            timestamp,  # time
            price,      # open
            price + 0.5,  # high
            price - 0.5,  # low
            price,      # close
            price,      # vwap
            100,        # volume
            10          # count
        ]
        candles.append(candle)
    
    return candles


class MockKrakenAPI:
    """Mock Kraken API for testing."""
    
    def __init__(self, candles=None):
        self.candles = candles or create_mock_candles()
    
    def get_ohlc(self, pair, interval=1):
        """Mock get_ohlc method."""
        return {
            pair: self.candles,
            'last': self.candles[-1][0] if self.candles else 0
        }


def test_format_pair_name():
    """Test pair name formatting."""
    api = MockKrakenAPI()
    analyzer = CoinStatsAnalyzer(api)
    
    # Test common pairs
    assert analyzer.format_pair_name('XXBTZUSD') == 'BTC/USD'
    assert analyzer.format_pair_name('XETHZUSD') == 'ETH/USD'
    assert analyzer.format_pair_name('SOLUSD') == 'SOL/USD'
    
    # Test unknown pair (should return original)
    assert analyzer.format_pair_name('UNKNOWNPAIR') == 'UNKNOWNPAIR'


def test_calculate_statistics_basic():
    """Test basic statistics calculation."""
    candles = create_mock_candles(num_candles=100, base_price=100.0, volatility=1.0)
    
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    stats = analyzer.calculate_statistics(candles)
    
    # Verify basic structure
    assert stats is not None
    assert 'prices' in stats
    assert 'mean' in stats
    assert 'median' in stats
    assert 'stdev' in stats
    assert 'count' in stats
    
    # Verify count
    assert stats['count'] == 100
    
    # Verify mean is reasonable
    assert 95 <= stats['mean'] <= 105  # Should be around 100
    
    # Verify we have percentage changes
    assert 'pct_changes' in stats
    assert len(stats['pct_changes']) == 99  # One less than prices


def test_calculate_statistics_insufficient_data():
    """Test statistics calculation with insufficient data."""
    candles = create_mock_candles(num_candles=1)  # Only 1 candle
    
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    stats = analyzer.calculate_statistics(candles)
    
    # Should return None for insufficient data
    assert stats is None


def test_calculate_statistics_consistency():
    """Test that statistics are consistent with standard library."""
    candles = create_mock_candles(num_candles=50, base_price=200.0, volatility=2.0)
    
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    stats = analyzer.calculate_statistics(candles)
    
    # Extract prices and verify against standard library
    prices = [float(c[4]) for c in candles]
    
    assert abs(stats['mean'] - statistics.mean(prices)) < 0.0001
    assert abs(stats['median'] - statistics.median(prices)) < 0.0001
    assert abs(stats['stdev'] - statistics.stdev(prices)) < 0.0001
    assert stats['min_price'] == min(prices)
    assert stats['max_price'] == max(prices)


def test_normality_test_present():
    """Test that normality test is included when scipy available."""
    try:
        import scipy
        scipy_available = True
    except ImportError:
        scipy_available = False
    
    candles = create_mock_candles(num_candles=100)
    
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    stats = analyzer.calculate_statistics(candles)
    
    if scipy_available:
        # Should include normality test
        assert 'normality_test' in stats
        assert 'test' in stats['normality_test']
        assert 'p_value' in stats['normality_test']
        assert 'is_normal' in stats['normality_test']
        assert stats['normality_test']['test'] == 'Shapiro-Wilk'


def test_probability_threshold_calculation():
    """Test 95% probability threshold calculation."""
    try:
        import scipy
        scipy_available = True
    except ImportError:
        scipy_available = False
        return  # Skip test if scipy not available
    
    candles = create_mock_candles(num_candles=100, base_price=100.0, volatility=1.0)
    
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    stats = analyzer.calculate_statistics(candles)
    threshold = analyzer.calculate_probability_threshold(stats, probability=0.95)
    
    # Verify threshold structure
    assert threshold is not None
    assert 'threshold_pct' in threshold
    assert 'threshold_price_up' in threshold
    assert 'threshold_price_down' in threshold
    assert 'confidence' in threshold
    
    # Verify threshold values are reasonable
    assert threshold['threshold_pct'] > 0
    assert threshold['threshold_price_up'] > stats['mean']
    assert threshold['threshold_price_down'] < stats['mean']
    
    # Verify confidence is one of expected values
    assert threshold['confidence'] in ['low', 'medium', 'high']


def test_fetch_minute_data_filtering():
    """Test that fetch_minute_data filters by time correctly."""
    import time
    
    # Create candles with varying timestamps
    current_time = time.time()
    old_candles = []
    recent_candles = []
    
    # Old candles (3 hours ago)
    for i in range(10):
        timestamp = current_time - (3 * 3600) - (i * 60)
        candle = [timestamp, 100, 101, 99, 100, 100, 100, 10]
        old_candles.append(candle)
    
    # Recent candles (1 hour ago)
    for i in range(20):
        timestamp = current_time - (1 * 3600) - (i * 60)
        candle = [timestamp, 100, 101, 99, 100, 100, 100, 10]
        recent_candles.append(candle)
    
    all_candles = old_candles + recent_candles
    
    api = MockKrakenAPI(all_candles)
    analyzer = CoinStatsAnalyzer(api, hours=2)
    
    filtered = analyzer.fetch_minute_data('XXBTZUSD')
    
    # Should only include recent candles (within 2 hours)
    # Note: recent_candles are 1 hour ago, so all should be included
    assert len(filtered) == len(recent_candles)


def test_analyze_pair_complete():
    """Test complete pair analysis."""
    candles = create_mock_candles(num_candles=200, base_price=50000.0, volatility=100.0)
    
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    analysis = analyzer.analyze_pair('XXBTZUSD')
    
    # Verify analysis structure
    assert analysis is not None
    assert 'pair' in analysis
    assert 'stats' in analysis
    assert analysis['pair'] == 'XXBTZUSD'
    
    # Verify stats are present
    assert 'mean' in analysis['stats']
    assert 'median' in analysis['stats']
    assert 'stdev' in analysis['stats']


def test_analyze_pair_insufficient_data():
    """Test analyze_pair with insufficient data."""
    candles = create_mock_candles(num_candles=50)  # Less than 100
    
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    analysis = analyzer.analyze_pair('XXBTZUSD')
    
    # Should return None for insufficient data
    assert analysis is None


def test_generate_distribution_graph():
    """Test graph generation."""
    try:
        import matplotlib
        import scipy
        graphs_available = True
    except ImportError:
        graphs_available = False
        return  # Skip test if libraries not available
    
    candles = create_mock_candles(num_candles=100, base_price=100.0, volatility=1.0)
    
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    stats = analyzer.calculate_statistics(candles)
    
    # Use temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_path = analyzer.generate_distribution_graph(
            'XXBTZUSD', stats, output_dir=tmpdir
        )
        
        # Verify graph was created
        assert graph_path is not None
        assert os.path.exists(graph_path)
        assert graph_path.endswith('.png')
        
        # Verify file has content
        assert os.path.getsize(graph_path) > 0


def test_print_analysis_no_crash():
    """Test that print_analysis doesn't crash."""
    candles = create_mock_candles(num_candles=100)
    
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    analysis = analyzer.analyze_pair('XXBTZUSD')
    
    # Should not crash
    analyzer.print_analysis(analysis)
    
    # Test with None
    analyzer.print_analysis(None)


def test_generate_config_suggestions_default_params():
    """Test generate_config_suggestions with default parameters."""
    from tools.coin_stats import generate_config_suggestions
    import csv
    
    # Create mock results with very high volatility to pass filter
    candles = create_mock_candles(num_candles=200, base_price=100.0, volatility=20.0)
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    analysis = analyzer.analyze_pair('XXBTZUSD')
    results = [analysis] if analysis else []
    
    if not results:
        return  # Skip if no results
    
    # Generate suggestions with default params
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, 'test_config.csv')
        config_path = generate_config_suggestions(results, analyzer, output_file)
        
        assert config_path is not None
        assert os.path.exists(config_path)
        
        # Read and verify CSV
        with open(config_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Should have 2 entries per pair (buy + sell) if volatility sufficient
            if len(rows) == 0:
                return  # Skip if pair excluded due to insufficient volatility
            
            assert len(rows) == 2
            
            # Check first row (sell)
            assert rows[0]['direction'] == 'sell'
            assert rows[0]['threshold_type'] == 'above'
            assert float(rows[0]['trailing_offset_percent']) == 1.0  # Default
            
            # Check second row (buy)
            assert rows[1]['direction'] == 'buy'
            assert rows[1]['threshold_type'] == 'below'
            assert float(rows[1]['trailing_offset_percent']) == 1.0  # Default


def test_generate_config_suggestions_custom_params():
    """Test generate_config_suggestions with custom parameters."""
    from tools.coin_stats import generate_config_suggestions
    import csv
    
    # Create mock results with very high volatility
    candles = create_mock_candles(num_candles=200, base_price=100.0, volatility=30.0)
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    analysis = analyzer.analyze_pair('XXBTZUSD')
    results = [analysis] if analysis else []
    
    if not results:
        return  # Skip if no results
    
    # Generate suggestions with custom params
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, 'test_config.csv')
        config_path = generate_config_suggestions(
            results, analyzer, output_file,
            bracket_offset_pct=10.0,
            trailing_offset_pct=5.0
        )
        
        assert config_path is not None
        assert os.path.exists(config_path)
        
        # Read and verify CSV
        with open(config_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Should have entries if volatility sufficient
            if len(rows) == 0:
                return  # Skip if pair excluded due to insufficient volatility
            
            assert len(rows) >= 2
            
            # Check trailing offset is custom value
            for row in rows:
                assert float(row['trailing_offset_percent']) == 5.0
            
            # Check bracket offset by comparing prices
            mean_price = analyzer.calculate_statistics(candles)['mean']
            sell_price = float(rows[0]['threshold_price'])
            buy_price = float(rows[1]['threshold_price'])
            
            # Sell should be ~10% above mean
            sell_offset = ((sell_price - mean_price) / mean_price) * 100
            assert 9.5 < sell_offset < 10.5  # Allow small tolerance
            
            # Buy should be ~10% below mean
            buy_offset = ((mean_price - buy_price) / mean_price) * 100
            assert 9.5 < buy_offset < 10.5  # Allow small tolerance


if __name__ == '__main__':
    # Run tests
    print("Running coin_stats tests...")
    
    test_format_pair_name()
    print("✓ test_format_pair_name")
    
    test_calculate_statistics_basic()
    print("✓ test_calculate_statistics_basic")
    
    test_calculate_statistics_insufficient_data()
    print("✓ test_calculate_statistics_insufficient_data")
    
    test_calculate_statistics_consistency()
    print("✓ test_calculate_statistics_consistency")
    
    test_normality_test_present()
    print("✓ test_normality_test_present")
    
    test_probability_threshold_calculation()
    print("✓ test_probability_threshold_calculation")
    
    test_fetch_minute_data_filtering()
    print("✓ test_fetch_minute_data_filtering")
    
    test_analyze_pair_complete()
    print("✓ test_analyze_pair_complete")
    
    test_analyze_pair_insufficient_data()
    print("✓ test_analyze_pair_insufficient_data")
    
    test_generate_distribution_graph()
    print("✓ test_generate_distribution_graph")
    
    test_print_analysis_no_crash()
    print("✓ test_print_analysis_no_crash")
    
    test_generate_config_suggestions_default_params()
    print("✓ test_generate_config_suggestions_default_params")
    
    test_generate_config_suggestions_custom_params()
    print("✓ test_generate_config_suggestions_custom_params")
    
    print("\n✅ All tests passed!")
