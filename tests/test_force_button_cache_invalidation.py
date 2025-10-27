"""Tests for cache invalidation after force button action."""
import tempfile
import csv
from unittest.mock import patch
import dashboard
from config import ConfigManager


def test_force_button_invalidates_caches():
    """
    Test that forcing a pending order invalidates all relevant caches.
    
    This ensures the "Manual" tag doesn't appear after force button,
    which was the bug reported in the issue.
    """
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        config_file = f.name
        writer = csv.DictWriter(f, fieldnames=['id', 'pair', 'threshold_price', 'threshold_type', 'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writeheader()
        writer.writerow({
            'id': 'btc_test',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        })
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        state_file = f.name
        # Empty state initially
    
    try:
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, 'logs.csv')
        
        # Mock Kraken API and cache invalidation tracking
        with patch.object(dashboard, 'kraken_api') as mock_api:
            mock_api.get_current_price.return_value = 51000.0
            mock_api.add_trailing_stop_loss.return_value = {
                'txid': ['OTEST-12345-ABCDE']
            }
            mock_api.query_open_orders.return_value = {
                'open': {
                    'OTEST-12345-ABCDE': {
                        'status': 'open',
                        'vol': '0.01',
                        'vol_exec': '0',
                        'descr': {
                            'ordertype': 'trailing-stop',
                            'pair': 'XXBTZUSD',
                            'price': '+5.0000%'
                        }
                    }
                }
            }
            
            # Patch config manager
            with patch.object(dashboard, 'config_manager', config_manager):
                # Patch get_cached_config to return our config
                with patch.object(dashboard, 'get_cached_config') as mock_get_config:
                    mock_get_config.return_value = [{
                        'id': 'btc_test',
                        'pair': 'XXBTZUSD',
                        'threshold_price': '50000',
                        'threshold_type': 'above',
                        'direction': 'sell',
                        'volume': '0.01',
                        'trailing_offset_percent': '5.0',
                        'enabled': 'true'
                    }]
                    
                    # Track invalidation calls
                    state_invalidate_called = False
                    active_invalidate_called = False
                    config_invalidate_called = False
                    
                    original_state_invalidate = dashboard.get_cached_state.invalidate
                    original_active_invalidate = dashboard.get_active_orders.invalidate
                    original_config_invalidate = dashboard.get_cached_config.invalidate
                    
                    def track_state_invalidate():
                        nonlocal state_invalidate_called
                        state_invalidate_called = True
                        original_state_invalidate()
                    
                    def track_active_invalidate():
                        nonlocal active_invalidate_called
                        active_invalidate_called = True
                        original_active_invalidate()
                    
                    def track_config_invalidate():
                        nonlocal config_invalidate_called
                        config_invalidate_called = True
                        original_config_invalidate()
                    
                    # Patch invalidate methods
                    with patch.object(dashboard.get_cached_state, 'invalidate', side_effect=track_state_invalidate):
                        with patch.object(dashboard.get_active_orders, 'invalidate', side_effect=track_active_invalidate):
                            with patch.object(dashboard.get_cached_config, 'invalidate', side_effect=track_config_invalidate):
                                # Create test client and force the order
                                with dashboard.app.test_client() as client:
                                    response = client.post('/api/pending/btc_test/force')
                                    
                                    # Check response
                                    assert response.status_code == 200
                                    data = response.get_json()
                                    assert data['success'] is True
                                    assert data['order_id'] == 'OTEST-12345-ABCDE'
                                    
                                    # CRITICAL: Verify all caches were invalidated
                                    assert state_invalidate_called, \
                                        "get_cached_state.invalidate() must be called after force"
                                    assert active_invalidate_called, \
                                        "get_active_orders.invalidate() must be called after force"
                                    assert config_invalidate_called, \
                                        "get_cached_config.invalidate() must be called after force"
                                    
                                    print("✓ All caches invalidated after force button")
        
        # Verify state was updated with order_id
        state = config_manager.load_state()
        assert 'btc_test' in state
        assert state['btc_test'].get('order_id') == 'OTEST-12345-ABCDE'
        assert state['btc_test'].get('triggered') == 'true'
        
        print("✓ State correctly updated with order_id")
        
    finally:
        import os
        try:
            os.unlink(config_file)
            os.unlink(state_file)
        except:
            pass

