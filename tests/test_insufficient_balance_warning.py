"""
Tests for insufficient balance warning icons in pending orders.
"""
import pytest
from unittest.mock import patch, MagicMock
import dashboard


@pytest.fixture
def mock_configs_sell():
    """Mock config data for sell orders."""
    return [
        {
            'id': 'sol_sell_1',
            'pair': 'SOLUSD',
            'enabled': 'true',
            'direction': 'sell',
            'volume': '10.0',  # Need 10 SOL, have 5 - insufficient
            'threshold_price': '100.0',
            'threshold_type': 'below',
            'trailing_offset_percent': '1.0'
        },
        {
            'id': 'sol_sell_2',
            'pair': 'SOLUSD',
            'enabled': 'true',
            'direction': 'sell',
            'volume': '2.0',   # Need 2 SOL, have 5 - sufficient
            'threshold_price': '100.0',
            'threshold_type': 'below',
            'trailing_offset_percent': '1.0'
        }
    ]


@pytest.fixture
def mock_configs_buy():
    """Mock config data for buy orders."""
    return [
        {
            'id': 'sol_buy_1',
            'pair': 'SOLUSD',
            'enabled': 'true',
            'direction': 'buy',
            'volume': '5.0',   # Need 5 * 100 = $500 USD, have $100 - insufficient
            'threshold_price': '100.0',
            'threshold_type': 'above',
            'trailing_offset_percent': '1.0'
        },
        {
            'id': 'sol_buy_2',
            'pair': 'SOLUSD',
            'enabled': 'true',
            'direction': 'buy',
            'volume': '0.5',   # Need 0.5 * 100 = $50 USD, have $100 - sufficient
            'threshold_price': '100.0',
            'threshold_type': 'above',
            'trailing_offset_percent': '1.0'
        }
    ]


@pytest.fixture
def mock_state():
    """Mock state data."""
    return {}


@pytest.fixture
def mock_prices():
    """Mock price data."""
    return {
        'SOLUSD': 100.0,
        'XXBTZUSD': 50000.0
    }


def test_insufficient_balance_sell_order(mock_configs_sell, mock_state, mock_prices):
    """Test that insufficient balance is detected for sell orders."""
    mock_api = MagicMock()
    mock_api.get_balance.return_value = {
        'ZUSD': '100.0',  # $100 USD
        'SOL': '5.0',      # 5 SOL
        'XXBT': '0.001'    # 0.001 BTC
    }
    
    # Patch at the module level to bypass cache
    with patch.object(dashboard, 'get_cached_config', return_value=mock_configs_sell), \
         patch.object(dashboard, 'get_cached_state', return_value=mock_state), \
         patch.object(dashboard, 'get_current_prices', return_value=mock_prices), \
         patch.object(dashboard, 'kraken_api', mock_api):
        
        # Call the wrapped function directly to bypass cache
        orders = dashboard.get_pending_orders.__wrapped__()
        
        # First order should have insufficient balance (need 10 SOL, have 5)
        assert len(orders) == 2
        assert orders[0]['id'] == 'sol_sell_1'
        assert orders[0]['insufficient_balance'] is True
        assert 'need 10.0000 SOL' in orders[0]['balance_message']
        assert 'have 5.0000 SOL' in orders[0]['balance_message']
        
        # Second order should have sufficient balance (need 2 SOL, have 5)
        assert orders[1]['id'] == 'sol_sell_2'
        assert orders[1]['insufficient_balance'] is False
        assert orders[1]['balance_message'] is None


def test_insufficient_balance_buy_order(mock_configs_buy, mock_state, mock_prices):
    """Test that insufficient balance is detected for buy orders."""
    mock_api = MagicMock()
    mock_api.get_balance.return_value = {
        'ZUSD': '100.0',  # $100 USD
        'SOL': '5.0',      # 5 SOL
        'XXBT': '0.001'    # 0.001 BTC
    }
    
    with patch.object(dashboard, 'get_cached_config', return_value=mock_configs_buy), \
         patch.object(dashboard, 'get_cached_state', return_value=mock_state), \
         patch.object(dashboard, 'get_current_prices', return_value=mock_prices), \
         patch.object(dashboard, 'kraken_api', mock_api):
        
        # Call the wrapped function directly to bypass cache
        orders = dashboard.get_pending_orders.__wrapped__()
        
        # First order should have insufficient balance (need $500 USD, have $100)
        assert len(orders) == 2
        assert orders[0]['id'] == 'sol_buy_1'
        assert orders[0]['insufficient_balance'] is True
        assert 'need 500.0000 ZUSD' in orders[0]['balance_message']
        assert 'have 100.0000 ZUSD' in orders[0]['balance_message']
        
        # Second order should have sufficient balance (need $50 USD, have $100)
        assert orders[1]['id'] == 'sol_buy_2'
        assert orders[1]['insufficient_balance'] is False
        assert orders[1]['balance_message'] is None


def test_no_kraken_api_no_balance_warning():
    """Test that no balance warnings appear when kraken_api is not available."""
    mock_configs = [{
        'id': 'sol_sell_only',
        'pair': 'SOLUSD',
        'enabled': 'true',
        'direction': 'sell',
        'volume': '10.0',
        'threshold_price': '100.0',
        'threshold_type': 'below',
        'trailing_offset_percent': '1.0'
    }]
    
    with patch.object(dashboard, 'get_cached_config', return_value=mock_configs), \
         patch.object(dashboard, 'get_cached_state', return_value={}), \
         patch.object(dashboard, 'get_current_prices', return_value={'SOLUSD': 100.0}), \
         patch.object(dashboard, 'kraken_api', None):
        
        orders = dashboard.get_pending_orders.__wrapped__()
        
        # Should not have balance warnings when API is not available
        assert len(orders) == 1
        assert orders[0]['insufficient_balance'] is False
        assert orders[0]['balance_message'] is None


def test_balance_check_error_handling():
    """Test that balance check errors are handled gracefully."""
    mock_configs = [{
        'id': 'sol_sell_error',
        'pair': 'SOLUSD',
        'enabled': 'true',
        'direction': 'sell',
        'volume': '10.0',
        'threshold_price': '100.0',
        'threshold_type': 'below',
        'trailing_offset_percent': '1.0'
    }]
    
    mock_api = MagicMock()
    mock_api.get_balance.side_effect = Exception("API error")
    
    with patch.object(dashboard, 'get_cached_config', return_value=mock_configs), \
         patch.object(dashboard, 'get_cached_state', return_value={}), \
         patch.object(dashboard, 'get_current_prices', return_value={'SOLUSD': 100.0}), \
         patch.object(dashboard, 'kraken_api', mock_api):
        
        orders = dashboard.get_pending_orders.__wrapped__()
        
        # Should not crash, should return orders without balance warnings
        assert len(orders) == 1
        assert orders[0]['insufficient_balance'] is False
        assert orders[0]['balance_message'] is None


def test_extract_assets_for_balance_check():
    """Test that asset extraction works correctly for balance checks."""
    # Test base asset extraction
    assert dashboard._extract_base_asset('SOLUSD') == 'SOL'
    assert dashboard._extract_base_asset('XXBTZUSD') == 'XXBT'
    assert dashboard._extract_base_asset('DYDXUSD') == 'DYDX'
    
    # Test quote asset extraction (normalized to Z-prefix)
    assert dashboard._extract_quote_asset('SOLUSD') == 'ZUSD'
    assert dashboard._extract_quote_asset('XXBTZUSD') == 'ZUSD'
    assert dashboard._extract_quote_asset('SOLUSDT') == 'USDT'


def test_disabled_orders_not_checked():
    """Test that disabled orders are not included in balance checks."""
    mock_configs = [{
        'id': 'sol_sell_disabled',
        'pair': 'SOLUSD',
        'enabled': 'false',  # Disabled
        'direction': 'sell',
        'volume': '10.0',
        'threshold_price': '100.0',
        'threshold_type': 'below',
        'trailing_offset_percent': '1.0'
    }]
    
    mock_api = MagicMock()
    mock_api.get_balance.return_value = {'SOL': '5.0'}
    
    with patch.object(dashboard, 'get_cached_config', return_value=mock_configs), \
         patch.object(dashboard, 'get_cached_state', return_value={}), \
         patch.object(dashboard, 'get_current_prices', return_value={'SOLUSD': 100.0}), \
         patch.object(dashboard, 'kraken_api', mock_api):
        
        orders = dashboard.get_pending_orders.__wrapped__()
        
        # Disabled order should not be returned
        assert len(orders) == 0


def test_triggered_orders_not_checked():
    """Test that already triggered orders are not included."""
    mock_configs = [{
        'id': 'sol_sell_triggered',
        'pair': 'SOLUSD',
        'enabled': 'true',
        'direction': 'sell',
        'volume': '10.0',
        'threshold_price': '100.0',
        'threshold_type': 'below',
        'trailing_offset_percent': '1.0'
    }]
    
    mock_state = {
        'sol_sell_triggered': {'triggered': 'true'}
    }
    
    mock_api = MagicMock()
    mock_api.get_balance.return_value = {'SOL': '5.0'}
    
    with patch.object(dashboard, 'get_cached_config', return_value=mock_configs), \
         patch.object(dashboard, 'get_cached_state', return_value=mock_state), \
         patch.object(dashboard, 'get_current_prices', return_value={'SOLUSD': 100.0}), \
         patch.object(dashboard, 'kraken_api', mock_api):
        
        orders = dashboard.get_pending_orders.__wrapped__()
        
        # Triggered order should not be returned
        assert len(orders) == 0
