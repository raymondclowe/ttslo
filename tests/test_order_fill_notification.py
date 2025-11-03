#!/usr/bin/env python3
"""
Tests for order fill notification functionality.
"""
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ttslo import TTSLO
from config import ConfigManager
from kraken_api import KrakenAPI
from notifications import NotificationManager


def test_check_order_filled_when_filled():
    """Test checking order status when order is filled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Create minimal config
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled\n')
            f.write('test1,XXBTZUSD,50000,above,sell,0.01,5.0,true\n')
        
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, log_file)
        
        # Mock API with read-write access
        mock_api_rw = Mock(spec=KrakenAPI)
        # Updated to use query_orders instead of query_closed_orders
        mock_api_rw.query_orders.return_value = {
            'ORDER123': {
                'status': 'closed',
                'price': '51000.00',
                'descr': {'pair': 'XXBTZUSD'}
            }
        }
        
        # Create TTSLO instance
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=Mock(spec=KrakenAPI),
            kraken_api_readwrite=mock_api_rw,
            dry_run=False,
            verbose=True
        )
        
        # Check order filled (now returns 5 values including order_info)
        is_filled, fill_price, api_pair, filled_volume, order_info = ttslo.check_order_filled('test1', 'ORDER123')
        
        assert is_filled == True, "Order should be marked as filled"
        assert fill_price == 51000.00, f"Fill price should be 51000.00, got {fill_price}"
        assert order_info is not None, "Order info should be returned"
        assert order_info['status'] == 'closed', "Order status should be closed"
        assert mock_api_rw.query_orders.called, "Should call query_orders"
        
        print("✓ Check order filled test passed")


def test_check_order_filled_when_not_filled():
    """Test checking order status when order is not filled yet."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Create minimal config
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled\n')
            f.write('test1,XXBTZUSD,50000,above,sell,0.01,5.0,true\n')
        
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, log_file)
        
        # Mock API - order not in closed orders
        mock_api_rw = Mock(spec=KrakenAPI)
        # Updated to use query_orders instead of query_closed_orders
        mock_api_rw.query_orders.return_value = {}
        
        # Create TTSLO instance
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=Mock(spec=KrakenAPI),
            kraken_api_readwrite=mock_api_rw,
            dry_run=False,
            verbose=True
        )
        
        # Check order filled (now returns 5 values including order_info)
        is_filled, fill_price, api_pair, filled_volume, order_info = ttslo.check_order_filled('test1', 'ORDER123')
        
        assert is_filled == False, "Order should not be marked as filled"
        assert fill_price is None, "Fill price should be None"
        assert api_pair is None, "API pair should be None"
        assert filled_volume is None, "Filled volume should be None"
        assert order_info is None, "Order info should be None when not filled"
        
        print("✓ Check order not filled test passed")


def test_check_order_filled_dry_run():
    """Test that dry-run orders are never considered filled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Create minimal config
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled\n')
            f.write('test1,XXBTZUSD,50000,above,sell,0.01,5.0,true\n')
        
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, log_file)
        
        # Mock API
        mock_api_rw = Mock(spec=KrakenAPI)
        
        # Create TTSLO instance
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=Mock(spec=KrakenAPI),
            kraken_api_readwrite=mock_api_rw,
            dry_run=False,
            verbose=True
        )
        
        # Check dry-run order (now returns 5 values including order_info)
        is_filled, fill_price, api_pair, filled_volume, order_info = ttslo.check_order_filled('test1', 'DRY_RUN_ORDER_ID')
        
        assert is_filled == False, "Dry-run order should never be filled"
        assert fill_price is None, "Dry-run order should have no fill price"
        assert api_pair is None, "Dry-run order should have no API pair"
        assert filled_volume is None, "Dry-run order should have no filled volume"
        assert order_info is None, "Dry-run order should have no order info"
        assert not mock_api_rw.query_orders.called, "Should not query API for dry-run orders"
        
        print("✓ Dry-run order check test passed")


def test_check_triggered_orders_sends_notification():
    """Test that notification is sent when triggered order is filled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Create config
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled\n')
            f.write('test1,XXBTZUSD,50000,above,sell,0.01,5.0,true\n')
        
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, log_file)
        
        # Mock API
        mock_api_rw = Mock(spec=KrakenAPI)
        # Updated to use query_orders instead of query_closed_orders
        mock_api_rw.query_orders.return_value = {
            'ORDER123': {
                'status': 'closed',
                'price': '51000.00',
                'descr': {'pair': 'XXBTZUSD'}
            }
        }
        
        # Mock notification manager
        mock_notif = Mock(spec=NotificationManager)
        
        # Create TTSLO instance
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=Mock(spec=KrakenAPI),
            kraken_api_readwrite=mock_api_rw,
            dry_run=False,
            verbose=True,
            notification_manager=mock_notif
        )
        
        # Set up configs
        ttslo.configs = [{'id': 'test1', 'pair': 'XXBTZUSD'}]
        
        # Set up state with triggered order
        ttslo.state = {
            'test1': {
                'id': 'test1',
                'triggered': 'true',
                'order_id': 'ORDER123',
                'fill_notified': 'false'
            }
        }
        
        # Check triggered orders
        ttslo.check_triggered_orders()
        
        # Verify notification was sent
        assert mock_notif.notify_tsl_order_filled.called, "Should send notification"
        call_args = mock_notif.notify_tsl_order_filled.call_args
        assert call_args[1]['config_id'] == 'test1', "Should notify for correct config"
        assert call_args[1]['order_id'] == 'ORDER123', "Should notify with correct order ID"
        assert call_args[1]['pair'] == 'XXBTZUSD', "Should include pair"
        assert call_args[1]['fill_price'] == 51000.00, "Should include fill price"
        
        # Verify state was updated
        assert ttslo.state['test1']['fill_notified'] == 'true', "Should mark as notified"
        
        print("✓ Notification sent for filled order test passed")


def test_check_triggered_orders_no_duplicate_notification():
    """Test that notification is not sent twice for the same order."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Create config
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled\n')
            f.write('test1,XXBTZUSD,50000,above,sell,0.01,5.0,true\n')
        
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, log_file)
        
        # Mock API
        mock_api_rw = Mock(spec=KrakenAPI)
        # Updated to use query_orders instead of query_closed_orders
        mock_api_rw.query_orders.return_value = {
            'ORDER123': {
                'status': 'closed',
                'price': '51000.00'
            }
        }
        
        # Mock notification manager
        mock_notif = Mock(spec=NotificationManager)
        
        # Create TTSLO instance
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=Mock(spec=KrakenAPI),
            kraken_api_readwrite=mock_api_rw,
            dry_run=False,
            verbose=True,
            notification_manager=mock_notif
        )
        
        # Set up configs
        ttslo.configs = [{'id': 'test1', 'pair': 'XXBTZUSD'}]
        
        # Set up state - already notified
        ttslo.state = {
            'test1': {
                'id': 'test1',
                'triggered': 'true',
                'order_id': 'ORDER123',
                'fill_notified': 'true'  # Already notified
            }
        }
        
        # Check triggered orders
        ttslo.check_triggered_orders()
        
        # Verify notification was NOT sent
        assert not mock_notif.notify_tsl_order_filled.called, "Should not send duplicate notification"
        
        print("✓ No duplicate notification test passed")


def test_check_triggered_orders_skips_dry_run():
    """Test that order monitoring is skipped in dry-run mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Create config
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled\n')
            f.write('test1,XXBTZUSD,50000,above,sell,0.01,5.0,true\n')
        
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, log_file)
        
        # Mock API
        mock_api_rw = Mock(spec=KrakenAPI)
        
        # Create TTSLO instance in dry-run mode
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=Mock(spec=KrakenAPI),
            kraken_api_readwrite=mock_api_rw,
            dry_run=True,  # Dry-run mode
            verbose=True
        )
        
        # Set up state
        ttslo.state = {
            'test1': {
                'triggered': 'true',
                'order_id': 'ORDER123'
            }
        }
        
        # Check triggered orders
        ttslo.check_triggered_orders()
        
        # Verify API was not called in dry-run mode
        assert not mock_api_rw.query_orders.called, "Should not query orders in dry-run mode"
        
        print("✓ Dry-run mode skips order monitoring test passed")


if __name__ == '__main__':
    print("Running order fill notification tests...\n")
    test_check_order_filled_when_filled()
    test_check_order_filled_when_not_filled()
    test_check_order_filled_dry_run()
    test_check_triggered_orders_sends_notification()
    test_check_triggered_orders_no_duplicate_notification()
    test_check_triggered_orders_skips_dry_run()
    print("\nAll tests passed!")
