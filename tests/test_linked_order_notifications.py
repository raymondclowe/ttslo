#!/usr/bin/env python3
"""
Tests for linked order notification functionality.

Validates that Telegram notifications include linked order information
when orders are triggered or filled.
"""
import os
import sys
import tempfile
from unittest.mock import Mock, patch, call

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ttslo import TTSLO
from config import ConfigManager
from kraken_api import KrakenAPI
from notifications import NotificationManager


def test_notify_trigger_price_with_linked_order():
    """Test that trigger notification includes linked order info when present."""
    nm = NotificationManager()
    nm.enabled = True
    nm.recipients = {'test_user': '12345'}
    nm.subscriptions = {'trigger_reached': ['test_user']}
    
    with patch.object(nm, 'send_message') as mock_send:
        nm.notify_trigger_price_reached(
            config_id='test_order',
            pair='XXBTZUSD',
            current_price=50000.0,
            threshold_price=49000.0,
            threshold_type='above',
            linked_order_id='sell_order'
        )
        
        # Verify notification was sent
        assert mock_send.called
        call_args = mock_send.call_args
        message = call_args[0][1]  # Second argument is the message
        
        # Verify linked order is mentioned
        assert '🔗 Linked Order: sell_order' in message
        assert 'Will be activated when this order fills' in message
        
        print("✓ Trigger notification with linked order test passed")


def test_notify_trigger_price_without_linked_order():
    """Test that trigger notification works without linked order info."""
    nm = NotificationManager()
    nm.enabled = True
    nm.recipients = {'test_user': '12345'}
    nm.subscriptions = {'trigger_reached': ['test_user']}
    
    with patch.object(nm, 'send_message') as mock_send:
        nm.notify_trigger_price_reached(
            config_id='test_order',
            pair='XXBTZUSD',
            current_price=50000.0,
            threshold_price=49000.0,
            threshold_type='above'
        )
        
        # Verify notification was sent
        assert mock_send.called
        call_args = mock_send.call_args
        message = call_args[0][1]
        
        # Verify no linked order mentioned
        assert '🔗 Linked Order' not in message
        
        print("✓ Trigger notification without linked order test passed")


def test_notify_tsl_created_with_linked_order():
    """Test that TSL created notification includes linked order info when present."""
    nm = NotificationManager()
    nm.enabled = True
    nm.recipients = {'test_user': '12345'}
    nm.subscriptions = {'tsl_created': ['test_user']}
    
    with patch.object(nm, 'send_message') as mock_send:
        nm.notify_tsl_order_created(
            config_id='test_order',
            order_id='ORDER123',
            pair='XXBTZUSD',
            direction='sell',
            volume='0.01',
            trailing_offset=5.0,
            trigger_price=50000.0,
            linked_order_id='sell_order'
        )
        
        # Verify notification was sent
        assert mock_send.called
        call_args = mock_send.call_args
        message = call_args[0][1]
        
        # Verify linked order is mentioned
        assert '🔗 Linked Order: sell_order' in message
        assert 'Will be activated when this order fills' in message
        
        print("✓ TSL created notification with linked order test passed")


def test_notify_tsl_created_without_linked_order():
    """Test that TSL created notification works without linked order info."""
    nm = NotificationManager()
    nm.enabled = True
    nm.recipients = {'test_user': '12345'}
    nm.subscriptions = {'tsl_created': ['test_user']}
    
    with patch.object(nm, 'send_message') as mock_send:
        nm.notify_tsl_order_created(
            config_id='test_order',
            order_id='ORDER123',
            pair='XXBTZUSD',
            direction='sell',
            volume='0.01',
            trailing_offset=5.0,
            trigger_price=50000.0
        )
        
        # Verify notification was sent
        assert mock_send.called
        call_args = mock_send.call_args
        message = call_args[0][1]
        
        # Verify no linked order mentioned
        assert '🔗 Linked Order' not in message
        
        print("✓ TSL created notification without linked order test passed")


def test_notify_tsl_filled_with_linked_order():
    """Test that TSL filled notification includes linked order info when present."""
    nm = NotificationManager()
    nm.enabled = True
    nm.recipients = {'test_user': '12345'}
    nm.subscriptions = {'tsl_filled': ['test_user']}
    
    with patch.object(nm, 'send_message') as mock_send:
        nm.notify_tsl_order_filled(
            config_id='test_order',
            order_id='ORDER123',
            pair='XXBTZUSD',
            fill_price=50000.0,
            volume='0.01',
            linked_order_id='sell_order'
        )
        
        # Verify notification was sent
        assert mock_send.called
        call_args = mock_send.call_args
        message = call_args[0][1]
        
        # Verify linked order is mentioned
        assert '🔗 Linked Order: sell_order' in message
        assert 'Now being activated' in message
        
        print("✓ TSL filled notification with linked order test passed")


def test_notify_tsl_filled_without_linked_order():
    """Test that TSL filled notification works without linked order info."""
    nm = NotificationManager()
    nm.enabled = True
    nm.recipients = {'test_user': '12345'}
    nm.subscriptions = {'tsl_filled': ['test_user']}
    
    with patch.object(nm, 'send_message') as mock_send:
        nm.notify_tsl_order_filled(
            config_id='test_order',
            order_id='ORDER123',
            pair='XXBTZUSD',
            fill_price=50000.0,
            volume='0.01'
        )
        
        # Verify notification was sent
        assert mock_send.called
        call_args = mock_send.call_args
        message = call_args[0][1]
        
        # Verify no linked order mentioned
        assert '🔗 Linked Order' not in message
        
        print("✓ TSL filled notification without linked order test passed")


def test_ttslo_passes_linked_order_to_notifications():
    """Test that TTSLO properly passes linked order info to notifications."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Create config with linked order
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled,linked_order_id\n')
            f.write('buy_order,XXBTZUSD,49000,below,buy,0.01,5.0,true,sell_order\n')
            f.write('sell_order,XXBTZUSD,51000,above,sell,0.01,5.0,false,\n')
        
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, log_file)
        
        # Create mock notification manager
        mock_nm = Mock(spec=NotificationManager)
        
        # Mock API with read-write access
        mock_api_ro = Mock(spec=KrakenAPI)
        mock_api_ro.get_normalized_balances.return_value = {'XXBT': '1.0', 'ZUSD': '10000.0'}
        mock_api_ro.get_asset_pair_info.return_value = {'ordermin': '0.0001'}
        mock_api_ro._normalize_asset_key.side_effect = lambda x: x
        mock_api_rw = Mock(spec=KrakenAPI)
        mock_api_rw.get_normalized_balances.return_value = {'XXBT': '1.0', 'ZUSD': '10000.0'}
        mock_api_rw.get_asset_pair_info.return_value = {'ordermin': '0.0001'}
        mock_api_rw._normalize_asset_key.side_effect = lambda x: x
        mock_api_rw.add_trailing_stop_loss.return_value = {'txid': ['ORDER123']}
        
        # Create TTSLO instance
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=mock_api_ro,
            kraken_api_readwrite=mock_api_rw,
            dry_run=False,
            verbose=True,
            notification_manager=mock_nm
        )
        
        # Load configs
        ttslo.configs = config_manager.load_config()
        ttslo.load_state()
        
        # Get the config
        config = ttslo.configs[0]
        
        # Call create_tsl_order directly
        order_id = ttslo.create_tsl_order(config, 48000.0)
        
        # Verify that notify_tsl_order_created was called with linked_order_id
        assert mock_nm.notify_tsl_order_created.called
        call_args = mock_nm.notify_tsl_order_created.call_args[0]
        # The 8th positional argument (index 7) should be linked_order_id
        assert len(call_args) >= 8, f"Expected at least 8 arguments, got {len(call_args)}"
        assert call_args[7] == 'sell_order', f"Expected linked_order_id='sell_order', got {call_args[7]}"
        
        print("✓ TTSLO passes linked order to notifications test passed")


if __name__ == '__main__':
    test_notify_trigger_price_with_linked_order()
    test_notify_trigger_price_without_linked_order()
    test_notify_tsl_created_with_linked_order()
    test_notify_tsl_created_without_linked_order()
    test_notify_tsl_filled_with_linked_order()
    test_notify_tsl_filled_without_linked_order()
    test_ttslo_passes_linked_order_to_notifications()
    print("\n✓ All linked order notification tests passed!")
