"""
Tests for minimum volume validation feature.

This ensures that:
1. Volume is checked against Kraken's ordermin before creating orders
2. Dashboard shows warning when volume < ordermin
3. Only one notification is sent for volume errors (not repeated)
4. State tracking prevents repeated order attempts
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from ttslo import TTSLO
from kraken_api import KrakenAPI
from config import ConfigManager


def test_check_minimum_volume_passes_when_volume_sufficient():
    """Test that volume check passes when volume meets minimum."""
    # Setup
    config_manager = Mock(spec=ConfigManager)
    kraken_api_readonly = Mock(spec=KrakenAPI)
    
    # Mock pair info with ordermin of 0.7
    kraken_api_readonly.get_asset_pair_info.return_value = {
        'ordermin': '0.7',
        'costmin': '0.5'
    }
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_readonly,
        kraken_api_readwrite=None,
        dry_run=True
    )
    
    # Test volume that meets minimum
    is_ok, message, minimum = ttslo.check_minimum_volume('NEARUSD', 1.0, 'test_config')
    
    assert is_ok is True
    assert 'meets minimum' in message
    assert minimum == '0.7'


def test_check_minimum_volume_fails_when_volume_too_low():
    """Test that volume check fails when volume is below minimum."""
    # Setup
    config_manager = Mock(spec=ConfigManager)
    kraken_api_readonly = Mock(spec=KrakenAPI)
    
    # Mock pair info with ordermin of 0.7
    kraken_api_readonly.get_asset_pair_info.return_value = {
        'ordermin': '0.7',
        'costmin': '0.5'
    }
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_readonly,
        kraken_api_readwrite=None,
        dry_run=True
    )
    
    # Test volume below minimum (0.1 < 0.7)
    is_ok, message, minimum = ttslo.check_minimum_volume('NEARUSD', 0.1, 'test_config')
    
    assert is_ok is False
    assert 'below minimum' in message
    assert '0.1' in message
    assert '0.7' in message
    assert minimum == '0.7'


def test_check_minimum_volume_handles_missing_pair_info():
    """Test graceful handling when pair info is unavailable."""
    # Setup
    config_manager = Mock(spec=ConfigManager)
    kraken_api_readonly = Mock(spec=KrakenAPI)
    
    # Mock API returns None (pair not found)
    kraken_api_readonly.get_asset_pair_info.return_value = None
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_readonly,
        kraken_api_readwrite=None,
        dry_run=True
    )
    
    # Should allow order to proceed when info unavailable
    is_ok, message, minimum = ttslo.check_minimum_volume('INVALIDPAIR', 0.1, 'test_config')
    
    assert is_ok is True
    assert 'pair info unavailable' in message
    assert minimum is None


def test_check_minimum_volume_handles_missing_ordermin():
    """Test handling when pair info exists but ordermin field is missing."""
    # Setup
    config_manager = Mock(spec=ConfigManager)
    kraken_api_readonly = Mock(spec=KrakenAPI)
    
    # Mock pair info without ordermin
    kraken_api_readonly.get_asset_pair_info.return_value = {
        'costmin': '0.5'
        # ordermin missing
    }
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_readonly,
        kraken_api_readwrite=None,
        dry_run=True
    )
    
    # Should allow order to proceed
    is_ok, message, minimum = ttslo.check_minimum_volume('SOMEPAIR', 0.1, 'test_config')
    
    assert is_ok is True
    assert 'No minimum volume specified' in message
    assert minimum is None


def test_volume_check_prevents_order_creation():
    """Test that order creation is prevented when volume is too low."""
    # Setup
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    kraken_api_readonly = Mock(spec=KrakenAPI)
    kraken_api_readwrite = Mock(spec=KrakenAPI)
    
    # Mock pair info with minimum volume
    kraken_api_readonly.get_asset_pair_info.return_value = {
        'ordermin': '0.7'
    }
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_readonly,
        kraken_api_readwrite=kraken_api_readwrite,
        dry_run=False
    )
    
    # Initialize state
    ttslo.state = {
        'test_config': {
            'triggered': 'false',
            'last_error': '',
            'error_notified': False
        }
    }
    
    # Config with volume below minimum
    config = {
        'id': 'test_config',
        'pair': 'NEARUSD',
        'direction': 'sell',
        'volume': '0.1',  # Below minimum of 0.7
        'trailing_offset_percent': '2.0'
    }
    
    # Attempt to create order
    order_id = ttslo.create_tsl_order(config, trigger_price=2.5)
    
    # Should return None (no order created)
    assert order_id is None
    
    # Should update state with error
    assert 'below minimum' in ttslo.state['test_config']['last_error']


def test_error_notification_sent_only_once():
    """Test that error notification is sent only once, not repeatedly."""
    # Setup
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    kraken_api_readonly = Mock(spec=KrakenAPI)
    kraken_api_readwrite = Mock(spec=KrakenAPI)
    notification_manager = Mock()
    
    # Mock pair info
    kraken_api_readonly.get_asset_pair_info.return_value = {
        'ordermin': '0.7'
    }
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_readonly,
        kraken_api_readwrite=kraken_api_readwrite,
        notification_manager=notification_manager,
        dry_run=False
    )
    
    # Initialize state
    ttslo.state = {
        'test_config': {
            'triggered': 'false',
            'last_error': '',
            'error_notified': False
        }
    }
    
    config = {
        'id': 'test_config',
        'pair': 'NEARUSD',
        'direction': 'sell',
        'volume': '0.1',
        'trailing_offset_percent': '2.0'
    }
    
    # First attempt - should send notification
    ttslo.create_tsl_order(config, trigger_price=2.5)
    assert notification_manager.notify_order_failed.call_count == 1
    assert ttslo.state['test_config']['error_notified'] is True
    
    # Second attempt - should NOT send notification again
    ttslo.create_tsl_order(config, trigger_price=2.5)
    assert notification_manager.notify_order_failed.call_count == 1  # Still 1, not 2


def test_error_state_cleared_when_config_reenabled():
    """Test that error state is cleared when config is re-enabled."""
    # This is tested in process_config flow
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    kraken_api_readonly = Mock(spec=KrakenAPI)
    kraken_api_readonly.get_current_price.return_value = 2.5
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_readonly,
        kraken_api_readwrite=None,
        dry_run=True
    )
    
    # Initialize state with previous error
    ttslo.state = {
        'test_config': {
            'triggered': 'false',
            'last_error': 'Previous error',
            'error_notified': True,
            'initial_price': ''
        }
    }
    
    config = {
        'id': 'test_config',
        'enabled': 'true',
        'pair': 'NEARUSD',
        'threshold_price': '3.0',
        'threshold_type': 'above'
    }
    
    # Process config (which should clear error state)
    ttslo.process_config(config)
    
    # Error state should be cleared
    assert ttslo.state['test_config']['last_error'] == ''
    assert ttslo.state['test_config']['error_notified'] is False


def test_dashboard_shows_volume_warning():
    """Test that dashboard includes volume_too_low flag in pending orders."""
    # This test would require importing dashboard module
    # For now, we verify the logic is in place by checking the data structure
    from dashboard import get_pending_orders
    
    # We'll need to mock the dependencies
    with patch('dashboard.get_cached_config') as mock_config, \
         patch('dashboard.get_cached_state') as mock_state, \
         patch('dashboard.get_current_prices') as mock_prices, \
         patch('dashboard.kraken_api') as mock_api:
        
        # Setup mocks
        mock_config.return_value = [{
            'id': 'test_config',
            'enabled': 'true',
            'pair': 'NEARUSD',
            'direction': 'sell',
            'volume': '0.1',
            'threshold_price': '3.0',
            'threshold_type': 'above',
            'trailing_offset_percent': '2.0'
        }]
        
        mock_state.return_value = {}
        mock_prices.return_value = {'NEARUSD': 2.5}
        
        # Mock pair info with ordermin
        mock_api.get_asset_pair_info.return_value = {
            'ordermin': '0.7'
        }
        mock_api.get_balance.return_value = {}
        
        # Get pending orders
        pending = get_pending_orders.__wrapped__()  # Bypass cache
        
        # Should have one order with volume_too_low flag
        assert len(pending) == 1
        assert pending[0]['volume_too_low'] is True
        assert 'below minimum' in pending[0]['volume_message']
