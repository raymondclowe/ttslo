"""
Tests for minimum cost (purchase threshold) validation feature.

This ensures that:
1. Order cost is checked against Kraken's costmin before allowing Force button
2. Dashboard shows warning when order_cost < costmin
3. Force button is disabled when cost is below minimum
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal


def test_cost_check_passes_when_cost_sufficient():
    """Test that cost check passes when order cost meets minimum."""
    # Import here to avoid issues with circular imports
    import dashboard
    
    # Mock kraken_api
    mock_api = Mock()
    mock_api.get_asset_pair_info.return_value = {
        'ordermin': '0.1',
        'costmin': '5.0'  # Minimum order cost is $5
    }
    mock_api.get_balance.return_value = {'NEAR': '10.0', 'ZUSD': '100.0'}
    
    # Patch kraken_api in dashboard module
    with patch.object(dashboard, 'kraken_api', mock_api):
        # Mock configs and state
        with patch.object(dashboard, 'get_cached_config') as mock_config:
            with patch.object(dashboard, 'get_cached_state') as mock_state:
                with patch.object(dashboard, 'get_current_prices') as mock_prices:
                    mock_config.return_value = [{
                        'id': 'test_config',
                        'pair': 'NEARUSD',
                        'enabled': 'true',
                        'threshold_price': '10.0',
                        'threshold_type': 'above',
                        'direction': 'sell',
                        'volume': '1.0',  # 1.0 NEAR
                        'trailing_offset_percent': '1.0'
                    }]
                    mock_state.return_value = {}
                    mock_prices.return_value = {'NEARUSD': 8.0}  # Current price $8
                    
                    # Order cost = 1.0 * 8.0 = $8, which is >= $5 (costmin)
                    result = dashboard.get_pending_orders.__wrapped__()
                    
                    assert len(result) == 1
                    order = result[0]
                    assert order['cost_too_low'] is False
                    assert order['cost_message'] is None


def test_cost_check_fails_when_cost_too_low():
    """Test that cost check fails when order cost is below minimum."""
    import dashboard
    
    # Mock kraken_api
    mock_api = Mock()
    mock_api.get_asset_pair_info.return_value = {
        'ordermin': '0.1',
        'costmin': '5.0'  # Minimum order cost is $5
    }
    mock_api.get_balance.return_value = {'NEAR': '10.0', 'ZUSD': '100.0'}
    
    # Patch kraken_api in dashboard module
    with patch.object(dashboard, 'kraken_api', mock_api):
        with patch.object(dashboard, 'get_cached_config') as mock_config:
            with patch.object(dashboard, 'get_cached_state') as mock_state:
                with patch.object(dashboard, 'get_current_prices') as mock_prices:
                    mock_config.return_value = [{
                        'id': 'test_config',
                        'pair': 'NEARUSD',
                        'enabled': 'true',
                        'threshold_price': '10.0',
                        'threshold_type': 'above',
                        'direction': 'sell',
                        'volume': '0.5',  # 0.5 NEAR
                        'trailing_offset_percent': '1.0'
                    }]
                    mock_state.return_value = {}
                    mock_prices.return_value = {'NEARUSD': 8.0}  # Current price $8
                    
                    # Order cost = 0.5 * 8.0 = $4, which is < $5 (costmin)
                    result = dashboard.get_pending_orders.__wrapped__()
                    
                    assert len(result) == 1
                    order = result[0]
                    assert order['cost_too_low'] is True
                    assert order['cost_message'] is not None
                    assert 'below minimum' in order['cost_message']
                    assert '$4.00' in order['cost_message']
                    assert '$5.00' in order['cost_message']


def test_cost_check_handles_missing_costmin():
    """Test that missing costmin doesn't cause errors."""
    import dashboard
    
    # Mock kraken_api - pair info without costmin
    mock_api = Mock()
    mock_api.get_asset_pair_info.return_value = {
        'ordermin': '0.1'
        # No costmin field
    }
    mock_api.get_balance.return_value = {'NEAR': '10.0', 'ZUSD': '100.0'}
    
    with patch.object(dashboard, 'kraken_api', mock_api):
        with patch.object(dashboard, 'get_cached_config') as mock_config:
            with patch.object(dashboard, 'get_cached_state') as mock_state:
                with patch.object(dashboard, 'get_current_prices') as mock_prices:
                    mock_config.return_value = [{
                        'id': 'test_config',
                        'pair': 'NEARUSD',
                        'enabled': 'true',
                        'threshold_price': '10.0',
                        'threshold_type': 'above',
                        'direction': 'sell',
                        'volume': '0.5',
                        'trailing_offset_percent': '1.0'
                    }]
                    mock_state.return_value = {}
                    mock_prices.return_value = {'NEARUSD': 8.0}
                    
                    # Should not crash, should set cost_too_low = False
                    result = dashboard.get_pending_orders.__wrapped__()
                    
                    assert len(result) == 1
                    order = result[0]
                    assert order['cost_too_low'] is False


def test_cost_check_handles_missing_current_price():
    """Test that missing current price doesn't cause errors."""
    import dashboard
    
    # Mock kraken_api
    mock_api = Mock()
    mock_api.get_asset_pair_info.return_value = {
        'ordermin': '0.1',
        'costmin': '5.0'
    }
    mock_api.get_balance.return_value = {'NEAR': '10.0', 'ZUSD': '100.0'}
    
    with patch.object(dashboard, 'kraken_api', mock_api):
        with patch.object(dashboard, 'get_cached_config') as mock_config:
            with patch.object(dashboard, 'get_cached_state') as mock_state:
                with patch.object(dashboard, 'get_current_prices') as mock_prices:
                    mock_config.return_value = [{
                        'id': 'test_config',
                        'pair': 'NEARUSD',
                        'enabled': 'true',
                        'threshold_price': '10.0',
                        'threshold_type': 'above',
                        'direction': 'sell',
                        'volume': '0.5',
                        'trailing_offset_percent': '1.0'
                    }]
                    mock_state.return_value = {}
                    mock_prices.return_value = {}  # No price for NEARUSD
                    
                    # Should not crash, should set cost_too_low = False
                    result = dashboard.get_pending_orders.__wrapped__()
                    
                    assert len(result) == 1
                    order = result[0]
                    assert order['cost_too_low'] is False


def test_cost_check_with_buy_order():
    """Test cost check works correctly for buy orders."""
    import dashboard
    
    # Mock kraken_api
    mock_api = Mock()
    mock_api.get_asset_pair_info.return_value = {
        'ordermin': '0.1',
        'costmin': '10.0'  # Minimum order cost is $10
    }
    mock_api.get_balance.return_value = {'NEAR': '1.0', 'ZUSD': '100.0'}
    
    with patch.object(dashboard, 'kraken_api', mock_api):
        with patch.object(dashboard, 'get_cached_config') as mock_config:
            with patch.object(dashboard, 'get_cached_state') as mock_state:
                with patch.object(dashboard, 'get_current_prices') as mock_prices:
                    mock_config.return_value = [{
                        'id': 'test_buy',
                        'pair': 'NEARUSD',
                        'enabled': 'true',
                        'threshold_price': '5.0',
                        'threshold_type': 'below',
                        'direction': 'buy',
                        'volume': '1.0',  # Buy 1.0 NEAR
                        'trailing_offset_percent': '1.0'
                    }]
                    mock_state.return_value = {}
                    mock_prices.return_value = {'NEARUSD': 8.0}  # Current price $8
                    
                    # Order cost = 1.0 * 8.0 = $8, which is < $10 (costmin)
                    result = dashboard.get_pending_orders.__wrapped__()
                    
                    assert len(result) == 1
                    order = result[0]
                    assert order['cost_too_low'] is True
                    assert '$8.00' in order['cost_message']
                    assert '$10.00' in order['cost_message']


def test_cost_and_volume_both_too_low():
    """Test when both volume and cost are below minimum."""
    import dashboard
    
    # Mock kraken_api
    mock_api = Mock()
    mock_api.get_asset_pair_info.return_value = {
        'ordermin': '1.0',  # Minimum 1.0 NEAR
        'costmin': '10.0'   # Minimum $10
    }
    mock_api.get_balance.return_value = {'NEAR': '10.0', 'ZUSD': '100.0'}
    
    with patch.object(dashboard, 'kraken_api', mock_api):
        with patch.object(dashboard, 'get_cached_config') as mock_config:
            with patch.object(dashboard, 'get_cached_state') as mock_state:
                with patch.object(dashboard, 'get_current_prices') as mock_prices:
                    mock_config.return_value = [{
                        'id': 'test_config',
                        'pair': 'NEARUSD',
                        'enabled': 'true',
                        'threshold_price': '10.0',
                        'threshold_type': 'above',
                        'direction': 'sell',
                        'volume': '0.5',  # Below ordermin (1.0)
                        'trailing_offset_percent': '1.0'
                    }]
                    mock_state.return_value = {}
                    mock_prices.return_value = {'NEARUSD': 8.0}
                    
                    # Volume = 0.5 < 1.0 (ordermin)
                    # Cost = 0.5 * 8.0 = $4 < $10 (costmin)
                    result = dashboard.get_pending_orders.__wrapped__()
                    
                    assert len(result) == 1
                    order = result[0]
                    assert order['volume_too_low'] is True
                    assert order['cost_too_low'] is True
                    # Both flags should be set independently
