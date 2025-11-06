"""
Test that pending linked order status changes correctly after parent fills.

GitHub Issue: "Status of pending link orders should change after the order is filled"

Problem: When a parent order fills and enables its linked child order, the child
order's status should change from "Waiting for [parent] to be filled" to normal
pending status (no longer showing waiting message).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from dashboard import get_pending_orders


def test_linked_order_shows_waiting_when_parent_active_not_filled():
    """
    Test that linked order shows "waiting for parent" status when:
    - Parent has triggered (is active)
    - Parent has NOT filled yet
    - Child is disabled (enabled='false')
    """
    # Mock config with parent->child link
    configs = [
        {
            'id': 'parent_buy',
            'pair': 'XXBTZUSD',
            'threshold_price': '100000',
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.1',
            'trailing_offset_percent': '2',
            'enabled': 'true',
            'linked_order_id': 'child_sell'  # Links to child
        },
        {
            'id': 'child_sell',
            'pair': 'XXBTZUSD',
            'threshold_price': '120000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '2',
            'enabled': 'false',  # Disabled, waiting for parent
            'linked_order_id': ''
        }
    ]
    
    # State: parent is active (triggered, has order_id) but NOT filled
    state = {
        'parent_buy': {
            'triggered': 'true',
            'order_id': 'OABC123',
            'fill_notified': 'false'  # NOT filled yet
        }
    }
    
    prices = {'XXBTZUSD': 102000}  # Current price
    
    with patch('dashboard.get_cached_config', return_value=configs), \
         patch('dashboard.get_cached_state', return_value=state), \
         patch('dashboard.kraken_api') as mock_api:
        
        mock_api.get_normalized_balances.return_value = {}
        mock_api.get_current_prices_batch.return_value = prices
        
        result = get_pending_orders.__wrapped__()  # Bypass cache
        
        # Should have 1 pending order (child_sell)
        assert len(result) == 1
        child = result[0]
        
        # Verify waiting status is set correctly
        assert child['id'] == 'child_sell'
        assert child['waiting_for_parent'] == 'parent_buy'
        assert child['parent_is_active'] == True  # Parent active but not filled
        assert child['enabled'] == False


def test_linked_order_no_waiting_status_after_parent_fills():
    """
    Test that linked order NO LONGER shows "waiting for parent" status when:
    - Parent has filled (fill_notified='true')
    - Child has been enabled (enabled='true')
    - Child is now a normal pending order
    """
    # Mock config with parent->child link
    configs = [
        {
            'id': 'parent_buy',
            'pair': 'XXBTZUSD',
            'threshold_price': '100000',
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.1',
            'trailing_offset_percent': '2',
            'enabled': 'true',
            'linked_order_id': 'child_sell'
        },
        {
            'id': 'child_sell',
            'pair': 'XXBTZUSD',
            'threshold_price': '120000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '2',
            'enabled': 'true',  # NOW ENABLED after parent filled
            'linked_order_id': ''
        }
    ]
    
    # State: parent is filled (triggered, has order_id, fill_notified='true')
    state = {
        'parent_buy': {
            'triggered': 'true',
            'order_id': 'OABC123',
            'fill_notified': 'true'  # FILLED
        }
    }
    
    prices = {'XXBTZUSD': 102000}
    
    with patch('dashboard.get_cached_config', return_value=configs), \
         patch('dashboard.get_cached_state', return_value=state), \
         patch('dashboard.kraken_api') as mock_api:
        
        mock_api.get_normalized_balances.return_value = {}
        mock_api.get_current_prices_batch.return_value = prices
        
        result = get_pending_orders.__wrapped__()
        
        # Should have 1 pending order (child_sell)
        assert len(result) == 1
        child = result[0]
        
        # Verify NO waiting status (child is now normal pending order)
        assert child['id'] == 'child_sell'
        assert child['waiting_for_parent'] is None  # No longer waiting
        assert child['parent_is_active'] == False
        assert child['enabled'] == True  # Now enabled


def test_linked_order_shows_not_triggered_when_parent_not_active():
    """
    Test that linked order shows "linked to parent (not triggered yet)" when:
    - Parent has NOT triggered yet
    - Child is disabled
    """
    configs = [
        {
            'id': 'parent_buy',
            'pair': 'XXBTZUSD',
            'threshold_price': '100000',
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.1',
            'trailing_offset_percent': '2',
            'enabled': 'true',
            'linked_order_id': 'child_sell'
        },
        {
            'id': 'child_sell',
            'pair': 'XXBTZUSD',
            'threshold_price': '120000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '2',
            'enabled': 'false',
            'linked_order_id': ''
        }
    ]
    
    # State: parent NOT triggered yet (no state entry)
    state = {}
    
    prices = {'XXBTZUSD': 105000}  # Price above threshold
    
    with patch('dashboard.get_cached_config', return_value=configs), \
         patch('dashboard.get_cached_state', return_value=state), \
         patch('dashboard.kraken_api') as mock_api:
        
        mock_api.get_normalized_balances.return_value = {}
        mock_api.get_current_prices_batch.return_value = prices
        
        result = get_pending_orders.__wrapped__()
        
        # Should have 2 pending orders (both parent and child)
        assert len(result) == 2
        
        # Find the child order
        child = [o for o in result if o['id'] == 'child_sell'][0]
        
        # Verify status shows parent not triggered
        assert child['id'] == 'child_sell'
        assert child['waiting_for_parent'] == 'parent_buy'
        assert child['parent_is_active'] == False  # Parent not active yet
        assert child['enabled'] == False


def test_normal_order_no_waiting_status():
    """
    Test that normal orders (not linked) don't show waiting status.
    """
    configs = [
        {
            'id': 'normal_sell',
            'pair': 'XXBTZUSD',
            'threshold_price': '120000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '2',
            'enabled': 'true',
            'linked_order_id': ''  # Not linked
        }
    ]
    
    state = {}
    prices = {'XXBTZUSD': 102000}
    
    with patch('dashboard.get_cached_config', return_value=configs), \
         patch('dashboard.get_cached_state', return_value=state), \
         patch('dashboard.kraken_api') as mock_api:
        
        mock_api.get_normalized_balances.return_value = {}
        mock_api.get_current_prices_batch.return_value = prices
        
        result = get_pending_orders.__wrapped__()
        
        assert len(result) == 1
        order = result[0]
        
        # No waiting status
        assert order['waiting_for_parent'] is None
        assert order['parent_is_active'] == False
        assert order['enabled'] == True
