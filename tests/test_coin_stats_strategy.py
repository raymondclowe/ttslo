"""
Tests for coin_stats.py strategy parameter (buy-then-sell vs sell-then-buy).
"""
import os
import sys
import tempfile
import csv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.coin_stats import CoinStatsAnalyzer, generate_config_suggestions


class MockKrakenAPI:
    """Mock Kraken API for testing."""
    
    def __init__(self, candles):
        self.candles = candles
        
    def get_ohlc_data(self, pair, interval=1):
        """Return mock OHLC data."""
        return {pair: self.candles}
    
    def get_asset_pair_info(self, pair):
        """Return mock pair info with ordermin."""
        return {'ordermin': '0.001'}


def create_mock_candles(num_candles=100, base_price=100.0, volatility=10.0):
    """Create mock OHLC candles with specified volatility."""
    import random
    random.seed(42)  # For reproducibility
    
    candles = []
    price = base_price
    
    for i in range(num_candles):
        # Random walk with specified volatility
        change = random.gauss(0, volatility)
        price = price * (1 + change / 100)
        
        # Create OHLC candle
        high = price * 1.01
        low = price * 0.99
        open_price = price * (1 + random.uniform(-0.01, 0.01))
        close_price = price * (1 + random.uniform(-0.01, 0.01))
        
        candles.append([
            i,  # timestamp
            open_price,  # open
            high,  # high
            low,  # low
            close_price,  # close
            0,  # vwap (unused)
            0,  # volume (unused)
            0  # count (unused)
        ])
    
    return candles


def test_strategy_buy_then_sell():
    """Test buy-then-sell strategy generates correct order structure."""
    from tools.coin_stats import generate_config_suggestions
    
    # Create mock results with high volatility
    candles = create_mock_candles(num_candles=200, base_price=100.0, volatility=30.0)
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    analysis = analyzer.analyze_pair('XXBTZUSD')
    results = [analysis] if analysis else []
    
    if not results:
        return  # Skip if no results
    
    # Generate suggestions with buy-then-sell strategy
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, 'test_config.csv')
        config_path = generate_config_suggestions(
            results, analyzer, output_file,
            bracket_offset_pct=10.0,
            trailing_offset_pct=5.0,
            strategy='buy-then-sell'
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
            
            assert len(rows) == 2, "Should have exactly 2 orders (buy + sell)"
            
            # Find buy and sell orders
            buy_row = next((r for r in rows if r['direction'] == 'buy'), None)
            sell_row = next((r for r in rows if r['direction'] == 'sell'), None)
            
            assert buy_row is not None, "Should have buy order"
            assert sell_row is not None, "Should have sell order"
            
            # BUY-THEN-SELL strategy:
            # - BUY order should be enabled=true
            # - BUY order should have linked_order_id pointing to SELL
            # - SELL order should be enabled=false
            # - SELL order should have no linked_order_id
            
            assert buy_row['enabled'] == 'true', "Buy order should be enabled"
            assert buy_row['linked_order_id'] == sell_row['id'], "Buy should link to sell"
            
            assert sell_row['enabled'] == 'false', "Sell order should be disabled (linked)"
            assert sell_row['linked_order_id'] == '', "Sell should have no linked order"
            
            # Check threshold types
            assert buy_row['threshold_type'] == 'below', "Buy should trigger below threshold"
            assert sell_row['threshold_type'] == 'above', "Sell should trigger above threshold"


def test_strategy_sell_then_buy():
    """Test sell-then-buy strategy generates correct order structure."""
    from tools.coin_stats import generate_config_suggestions
    
    # Create mock results with high volatility
    candles = create_mock_candles(num_candles=200, base_price=100.0, volatility=30.0)
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    analysis = analyzer.analyze_pair('XXBTZUSD')
    results = [analysis] if analysis else []
    
    if not results:
        return  # Skip if no results
    
    # Generate suggestions with sell-then-buy strategy
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, 'test_config.csv')
        config_path = generate_config_suggestions(
            results, analyzer, output_file,
            bracket_offset_pct=10.0,
            trailing_offset_pct=5.0,
            strategy='sell-then-buy'
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
            
            assert len(rows) == 2, "Should have exactly 2 orders (sell + buy)"
            
            # Find buy and sell orders
            buy_row = next((r for r in rows if r['direction'] == 'buy'), None)
            sell_row = next((r for r in rows if r['direction'] == 'sell'), None)
            
            assert buy_row is not None, "Should have buy order"
            assert sell_row is not None, "Should have sell order"
            
            # SELL-THEN-BUY strategy:
            # - SELL order should be enabled=true
            # - SELL order should have linked_order_id pointing to BUY
            # - BUY order should be enabled=false
            # - BUY order should have no linked_order_id
            
            assert sell_row['enabled'] == 'true', "Sell order should be enabled"
            assert sell_row['linked_order_id'] == buy_row['id'], "Sell should link to buy"
            
            assert buy_row['enabled'] == 'false', "Buy order should be disabled (linked)"
            assert buy_row['linked_order_id'] == '', "Buy should have no linked order"
            
            # Check threshold types
            assert buy_row['threshold_type'] == 'below', "Buy should trigger below threshold"
            assert sell_row['threshold_type'] == 'above', "Sell should trigger above threshold"


def test_strategy_default_is_buy_then_sell():
    """Test that default strategy is buy-then-sell when not specified."""
    from tools.coin_stats import generate_config_suggestions
    
    # Create mock results with high volatility
    candles = create_mock_candles(num_candles=200, base_price=100.0, volatility=30.0)
    api = MockKrakenAPI(candles)
    analyzer = CoinStatsAnalyzer(api)
    
    analysis = analyzer.analyze_pair('XXBTZUSD')
    results = [analysis] if analysis else []
    
    if not results:
        return  # Skip if no results
    
    # Generate suggestions without specifying strategy (should default to buy-then-sell)
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, 'test_config.csv')
        config_path = generate_config_suggestions(
            results, analyzer, output_file,
            bracket_offset_pct=10.0,
            trailing_offset_pct=5.0
            # No strategy parameter - should default to 'buy-then-sell'
        )
        
        assert config_path is not None
        assert os.path.exists(config_path)
        
        # Read and verify CSV
        with open(config_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            if len(rows) == 0:
                return  # Skip if pair excluded
            
            # Find buy and sell orders
            buy_row = next((r for r in rows if r['direction'] == 'buy'), None)
            sell_row = next((r for r in rows if r['direction'] == 'sell'), None)
            
            # Verify default is buy-then-sell (buy enabled, sell linked)
            assert buy_row['enabled'] == 'true', "Default should have buy enabled"
            assert sell_row['enabled'] == 'false', "Default should have sell disabled"
