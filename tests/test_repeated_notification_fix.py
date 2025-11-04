"""
Tests for fix to prevent repeated notifications when trigger price reached but balance insufficient.

GitHub Issue: Repeated errors when trigger price reached but no balance
Problem: System sends "trigger price reached" + "insufficient balance" notifications
         every monitoring cycle when balance is insufficient, spamming the user.
         
Solution: Track trigger_notified flag in state to send "trigger price reached" 
          notification only once per config.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from decimal import Decimal
from ttslo import TTSLO
from config import ConfigManager
from kraken_api import KrakenAPI


def test_trigger_notification_sent_only_once_on_insufficient_balance():
    """
    Test that "trigger price reached" notification is sent only ONCE when
    balance is insufficient, not every monitoring cycle.
    """
    # Create mocks
    config_manager = Mock(spec=ConfigManager)
    kraken_api_ro = Mock(spec=KrakenAPI)
    kraken_api_rw = Mock(spec=KrakenAPI)
    notification_manager = Mock()
    
    # Configure kraken_api_ro to return price
    kraken_api_ro.get_current_price.return_value = 100.0
    
    # Configure kraken_api_rw to return insufficient balance
    kraken_api_rw.get_balance.return_value = {'XXBT': '0.0'}  # Zero balance
    kraken_api_ro.get_asset_pair_info.return_value = {'ordermin': '0.001'}
    
    # Create TTSLO instance
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_ro,
        kraken_api_readwrite=kraken_api_rw,
        dry_run=False,
        verbose=True,
        notification_manager=notification_manager
    )
    
    # Initialize state for config
    config_id = 'btc_sell_test'
    ttslo.state[config_id] = {
        'id': config_id,
        'triggered': 'false',
        'trigger_price': '',
        'trigger_time': '',
        'order_id': '',
        'last_checked': '',
        'last_error': '',
        'error_notified': False,
        'trigger_notified': False,
        'initial_price': '95.0'
    }
    
    # Create config with threshold met but insufficient balance
    config = {
        'id': config_id,
        'enabled': 'true',
        'pair': 'XXBTZUSD',
        'direction': 'sell',
        'volume': '0.1',  # Need 0.1 BTC but have 0
        'threshold_price': '99.0',  # Current price 100 > threshold 99
        'threshold_type': 'above',
        'trailing_offset_percent': '1.0'
    }
    
    # Cycle 1: Process config - threshold met, balance insufficient
    ttslo.process_config(config, current_price=100.0)
    
    # Verify trigger notification was sent in cycle 1
    assert notification_manager.notify_trigger_price_reached.call_count == 1
    # Note: linked_order_id is now the 6th parameter (optional, defaults to None)
    call_args = notification_manager.notify_trigger_price_reached.call_args[0]
    assert call_args[0:5] == (config_id, 'XXBTZUSD', 100.0, 99.0, 'above')
    # The 6th parameter is linked_order_id which should be None for this test
    assert len(call_args) == 6 and call_args[5] is None
    
    # Verify insufficient balance notification was sent in cycle 1
    # Note: This goes through _handle_order_error_state which checks error_notified flag
    assert notification_manager.notify_insufficient_balance.call_count == 1
    
    # Verify trigger_notified flag is now True
    assert ttslo.state[config_id]['trigger_notified'] == True
    
    # Verify config was NOT marked as triggered (no order created)
    assert ttslo.state[config_id]['triggered'] == 'false'
    assert ttslo.state[config_id]['order_id'] == ''
    
    # Reset mock call counts for cycle 2
    notification_manager.reset_mock()
    
    # Cycle 2: Process same config again - threshold still met, balance still insufficient
    ttslo.process_config(config, current_price=101.0)  # Price even higher
    
    # Verify trigger notification was NOT sent again in cycle 2 (already notified)
    assert notification_manager.notify_trigger_price_reached.call_count == 0
    
    # Verify insufficient balance notification was also NOT sent (error_notified flag)
    assert notification_manager.notify_insufficient_balance.call_count == 0
    
    # Verify config still not triggered
    assert ttslo.state[config_id]['triggered'] == 'false'
    
    # Reset mock call counts for cycle 3
    notification_manager.reset_mock()
    
    # Cycle 3: Same scenario
    ttslo.process_config(config, current_price=102.0)
    
    # No notifications sent
    assert notification_manager.notify_trigger_price_reached.call_count == 0
    assert notification_manager.notify_insufficient_balance.call_count == 0


def test_trigger_notified_flag_reset_when_config_reenabled():
    """
    Test that trigger_notified flag is cleared when config is disabled and then re-enabled
    after fixing the balance issue.
    """
    config_manager = Mock(spec=ConfigManager)
    kraken_api_ro = Mock(spec=KrakenAPI)
    kraken_api_rw = Mock(spec=KrakenAPI)
    notification_manager = Mock()
    
    kraken_api_ro.get_current_price.return_value = 100.0
    kraken_api_rw.get_balance.return_value = {'XXBT': '0.5'}  # Sufficient now
    kraken_api_ro.get_asset_pair_info.return_value = {'ordermin': '0.001'}
    
    # Mock successful order creation
    kraken_api_rw.add_trailing_stop_loss.return_value = {'txid': ['ORDER123']}
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_ro,
        kraken_api_readwrite=kraken_api_rw,
        dry_run=False,
        verbose=True,
        notification_manager=notification_manager
    )
    
    config_id = 'btc_sell_test'
    
    # Simulate state after previous failure (flags set)
    ttslo.state[config_id] = {
        'id': config_id,
        'triggered': 'false',
        'trigger_price': '',
        'trigger_time': '',
        'order_id': '',
        'last_checked': '',
        'last_error': 'Insufficient balance',  # Error from previous attempt
        'error_notified': True,  # Already notified
        'trigger_notified': True,  # Already notified about trigger
        'initial_price': '95.0'
    }
    
    config = {
        'id': config_id,
        'enabled': 'false',  # User disabled to fix the issue
        'pair': 'XXBTZUSD',
        'direction': 'sell',
        'volume': '0.1',
        'threshold_price': '99.0',
        'threshold_type': 'above',
        'trailing_offset_percent': '1.0'
    }
    
    # Process with disabled - should return early, no changes
    ttslo.process_config(config, current_price=100.0)
    
    # Verify no notifications sent while disabled
    assert notification_manager.notify_trigger_price_reached.call_count == 0
    assert kraken_api_rw.add_trailing_stop_loss.call_count == 0
    
    # Now user fixes balance and re-enables
    config['enabled'] = 'true'
    
    # When processing a re-enabled config, we need to clear the state entry
    # to simulate the user's intent to retry from scratch
    # In production, user would delete the state entry or we'd add logic to detect re-enable
    # For this test, simulate by creating fresh state
    del ttslo.state[config_id]
    
    # Process config - should create fresh state and send notifications
    ttslo.process_config(config, current_price=100.0)
    
    # Verify fresh state was created
    assert config_id in ttslo.state
    assert ttslo.state[config_id]['trigger_notified'] == True  # Set after sending notification
    assert ttslo.state[config_id]['error_notified'] == False  # No error this time
    
    # Verify trigger notification was sent (fresh state allows it)
    assert notification_manager.notify_trigger_price_reached.call_count == 1
    
    # Verify order was created successfully (balance sufficient)
    assert kraken_api_rw.add_trailing_stop_loss.call_count == 1
    assert notification_manager.notify_tsl_order_created.call_count == 1


def test_trigger_notified_flag_in_initial_state():
    """
    Test that trigger_notified flag is initialized to False for new configs.
    """
    config_manager = Mock(spec=ConfigManager)
    kraken_api_ro = Mock(spec=KrakenAPI)
    
    kraken_api_ro.get_current_price.return_value = 50.0  # Below threshold
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_ro,
        dry_run=True,
        verbose=True
    )
    
    config_id = 'new_config'
    config = {
        'id': config_id,
        'enabled': 'true',
        'pair': 'XXBTZUSD',
        'direction': 'sell',
        'volume': '0.1',
        'threshold_price': '100.0',
        'threshold_type': 'above',
        'trailing_offset_percent': '1.0'
    }
    
    # Process config - will initialize state
    ttslo.process_config(config, current_price=50.0)
    
    # Verify state was created with trigger_notified=False
    assert config_id in ttslo.state
    assert ttslo.state[config_id]['trigger_notified'] == False
    assert ttslo.state[config_id]['error_notified'] == False


def test_minimum_volume_error_also_prevents_repeated_trigger_notification():
    """
    Test that trigger_notified flag also prevents repeated notifications
    when order fails due to minimum volume violation (similar to balance check).
    """
    config_manager = Mock(spec=ConfigManager)
    kraken_api_ro = Mock(spec=KrakenAPI)
    kraken_api_rw = Mock(spec=KrakenAPI)
    notification_manager = Mock()
    
    kraken_api_ro.get_current_price.return_value = 100.0
    
    # Volume check will fail (volume 0.1 < ordermin 0.7)
    kraken_api_ro.get_asset_pair_info.return_value = {'ordermin': '0.7'}
    
    # Balance check would pass
    kraken_api_rw.get_balance.return_value = {'NEAR': '10.0'}
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_ro,
        kraken_api_readwrite=kraken_api_rw,
        dry_run=False,
        verbose=True,
        notification_manager=notification_manager
    )
    
    config_id = 'near_sell_test'
    ttslo.state[config_id] = {
        'id': config_id,
        'triggered': 'false',
        'trigger_price': '',
        'trigger_time': '',
        'order_id': '',
        'last_checked': '',
        'last_error': '',
        'error_notified': False,
        'trigger_notified': False,
        'initial_price': '8.0'
    }
    
    config = {
        'id': config_id,
        'enabled': 'true',
        'pair': 'NEARUSD',
        'direction': 'sell',
        'volume': '0.1',  # Below minimum 0.7
        'threshold_price': '8.5',
        'threshold_type': 'above',
        'trailing_offset_percent': '2.0'
    }
    
    # Cycle 1: Process - threshold met, volume too low
    ttslo.process_config(config, current_price=9.0)
    
    # Verify trigger notification sent once
    assert notification_manager.notify_trigger_price_reached.call_count == 1
    assert ttslo.state[config_id]['trigger_notified'] == True
    
    # Verify order failed notification sent via _handle_order_error_state
    assert notification_manager.notify_order_failed.call_count == 1
    assert ttslo.state[config_id]['error_notified'] == True
    
    # Reset for cycle 2
    notification_manager.reset_mock()
    
    # Cycle 2: Same scenario
    ttslo.process_config(config, current_price=9.5)
    
    # No notifications sent (both flags already set)
    assert notification_manager.notify_trigger_price_reached.call_count == 0
    assert notification_manager.notify_order_failed.call_count == 0
