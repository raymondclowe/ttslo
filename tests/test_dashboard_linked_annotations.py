"""Test dashboard linked order annotations."""

def test_pending_orders_show_waiting_status():
    """Test that pending orders show 'waiting for parent' when linked."""
    from dashboard import app, get_pending_orders
    from kraken_api import KrakenAPI
    
    # Mock config: btc_buy will enable btc_sell when it fills
    configs = [
        {
            'id': 'btc_buy',
            'pair': 'XXBTZUSD',
            'threshold_price': '100000',
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.01',
            'trailing_offset_percent': '2.0',
            'enabled': 'true',
            'linked_order_id': 'btc_sell'
        },
        {
            'id': 'btc_sell',
            'pair': 'XXBTZUSD',
            'threshold_price': '120000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '2.0',
            'enabled': 'false',  # Disabled, waiting for btc_buy
            'linked_order_id': ''
        }
    ]
    
    # Mock state: btc_buy not triggered yet
    state = {
        'btc_buy': {'triggered': 'false'},
        'btc_sell': {'triggered': 'false'}
    }
    
    # Mock get_cached functions
    import dashboard
    dashboard.get_cached_config = lambda: configs
    dashboard.get_cached_state = lambda: state
    dashboard.get_current_prices = lambda: {'XXBTZUSD': 105000}
    
    pending = get_pending_orders.__wrapped__()  # Bypass cache
    
    # Should show btc_buy (enabled=true)
    btc_buy = [o for o in pending if o['id'] == 'btc_buy']
    assert len(btc_buy) == 1
    assert btc_buy[0]['linked_order_id'] == 'btc_sell'
    assert btc_buy[0]['waiting_for_parent'] is None
    
    # Should show btc_sell (enabled=false but waiting for parent)
    btc_sell = [o for o in pending if o['id'] == 'btc_sell']
    assert len(btc_sell) == 1
    assert btc_sell[0]['waiting_for_parent'] == 'btc_buy'
    assert btc_sell[0]['parent_is_active'] is False


def test_pending_orders_show_parent_active_status():
    """Test that pending orders show when parent is active."""
    from dashboard import app, get_pending_orders
    from kraken_api import KrakenAPI
    
    configs = [
        {
            'id': 'btc_buy',
            'pair': 'XXBTZUSD',
            'threshold_price': '100000',
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.01',
            'trailing_offset_percent': '2.0',
            'enabled': 'true',
            'linked_order_id': 'btc_sell'
        },
        {
            'id': 'btc_sell',
            'pair': 'XXBTZUSD',
            'threshold_price': '120000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '2.0',
            'enabled': 'false',  # Disabled, waiting for btc_buy to fill
            'linked_order_id': ''
        }
    ]
    
    # Mock state: btc_buy HAS triggered (is active)
    state = {
        'btc_buy': {
            'triggered': 'true',
            'order_id': 'OTEST-123',
            'trigger_price': '100000',
            'trigger_time': '2025-11-04T00:00:00Z'
        },
        'btc_sell': {'triggered': 'false'}
    }
    
    import dashboard
    dashboard.get_cached_config = lambda: configs
    dashboard.get_cached_state = lambda: state
    dashboard.get_current_prices = lambda: {'XXBTZUSD': 105000}
    
    pending = get_pending_orders.__wrapped__()
    
    # btc_buy should NOT be in pending (it's triggered/active)
    btc_buy = [o for o in pending if o['id'] == 'btc_buy']
    assert len(btc_buy) == 0
    
    # btc_sell should be in pending, waiting for parent to fill
    btc_sell = [o for o in pending if o['id'] == 'btc_sell']
    assert len(btc_sell) == 1
    assert btc_sell[0]['waiting_for_parent'] == 'btc_buy'
    assert btc_sell[0]['parent_is_active'] is True  # Parent has triggered!


def test_active_orders_include_linked_order_id():
    """Test that active orders include linked_order_id."""
    from dashboard import app, get_active_orders
    from kraken_api import KrakenAPI
    
    configs = [
        {
            'id': 'btc_buy',
            'pair': 'XXBTZUSD',
            'threshold_price': '100000',
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.01',
            'trailing_offset_percent': '2.0',
            'enabled': 'true',
            'linked_order_id': 'btc_sell'  # Will enable btc_sell when filled
        }
    ]
    
    state = {
        'btc_buy': {
            'triggered': 'true',
            'order_id': 'OTEST-123',
            'trigger_price': '100000',
            'trigger_time': '2025-11-04T00:00:00Z'
        }
    }
    
    open_orders = {
        'OTEST-123': {
            'descr': {'ordertype': 'trailing-stop', 'pair': 'XXBTZUSD', 'price': '+2.0%'},
            'vol': '0.01',
            'vol_exec': '0',
            'status': 'open'
        }
    }
    
    import dashboard
    dashboard.get_cached_config = lambda: configs
    dashboard.get_cached_state = lambda: state
    dashboard.get_cached_open_orders = lambda: open_orders
    # Mock kraken_api for test
    dashboard.kraken_api = type('obj', (object,), {})()  # Dummy object
    
    active = get_active_orders.__wrapped__()
    
    assert len(active) == 1
    assert active[0]['id'] == 'btc_buy'
    assert active[0]['linked_order_id'] == 'btc_sell'


def test_pending_disabled_orders_not_linked_are_hidden():
    """Test that disabled orders without parent are hidden."""
    from dashboard import app, get_pending_orders
    from kraken_api import KrakenAPI
    
    configs = [
        {
            'id': 'btc_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '100000',
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.01',
            'trailing_offset_percent': '2.0',
            'enabled': 'false',  # Disabled by user, not linked
            'linked_order_id': ''
        }
    ]
    
    state = {
        'btc_1': {'triggered': 'false'}
    }
    
    import dashboard
    dashboard.get_cached_config = lambda: configs
    dashboard.get_cached_state = lambda: state
    dashboard.get_current_prices = lambda: {'XXBTZUSD': 105000}
    
    pending = get_pending_orders.__wrapped__()
    
    # Should NOT show disabled order that's not waiting for parent
    assert len(pending) == 0
