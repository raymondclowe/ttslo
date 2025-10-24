#!/usr/bin/env python3
"""
Demonstration of order fill notification functionality.

This script shows how TTSLO monitors triggered orders and sends
notifications when they are filled.
"""
import os
import sys
import tempfile
from unittest.mock import Mock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ttslo import TTSLO
from config import ConfigManager
from kraken_api import KrakenAPI
from notifications import NotificationManager


def demo_order_fill_notification():
    """Demonstrate order fill notification workflow."""
    print("=" * 70)
    print("DEMONSTRATION: Order Fill Notification")
    print("=" * 70)
    print()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Create config
        print("1. Creating sample configuration...")
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled\n')
            f.write('btc_sell_1,XXBTZUSD,50000,above,sell,0.01,5.0,true\n')
        print("   ✓ Config created: BTC sell when price goes above $50,000")
        print()
        
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, log_file)
        
        # Mock Kraken API
        mock_api_ro = Mock(spec=KrakenAPI)
        mock_api_rw = Mock(spec=KrakenAPI)
        
        # Mock notification manager
        mock_notif = Mock(spec=NotificationManager)
        
        # Create TTSLO instance
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=mock_api_ro,
            kraken_api_readwrite=mock_api_rw,
            dry_run=False,
            verbose=False,
            notification_manager=mock_notif
        )
        
        # Set up configs
        ttslo.configs = [{'id': 'btc_sell_1', 'pair': 'XXBTZUSD'}]
        
        # Scenario 1: Order just created - not filled yet
        print("2. Scenario: Order just created (not filled yet)")
        mock_api_rw.query_closed_orders.return_value = {'closed': {}}
        
        ttslo.state = {
            'btc_sell_1': {
                'id': 'btc_sell_1',
                'triggered': 'true',
                'order_id': 'ORDER-ABC123',
                'trigger_price': '50500.00',
                'fill_notified': 'false'
            }
        }
        
        print("   • Order ID: ORDER-ABC123")
        print("   • Triggered at: $50,500")
        print("   • Status: Open (not filled)")
        print()
        
        is_filled, fill_price, api_pair, filled_volume = ttslo.check_order_filled('btc_sell_1', 'ORDER-ABC123')
        print(f"   → check_order_filled() returns: is_filled={is_filled}, fill_price={fill_price}, api_pair={api_pair}, filled_volume={filled_volume}")
        print("   ✓ Order not in closed orders yet - no notification sent")
        print()
        
        # Scenario 2: Order gets filled
        print("3. Scenario: Order is filled!")
        mock_api_rw.query_closed_orders.return_value = {
            'closed': {
                'ORDER-ABC123': {
                    'status': 'closed',
                    'price': '49750.00',  # Trailing stop triggered at $49,750
                    'descr': {'pair': 'XXBTZUSD', 'type': 'sell'}
                }
            }
        }
        
        print("   • Price dropped to $49,750")
        print("   • Trailing stop order executed")
        print()
        
        is_filled, fill_price, api_pair, filled_volume = ttslo.check_order_filled('btc_sell_1', 'ORDER-ABC123')
        print(f"   → check_order_filled() returns: is_filled={is_filled}, fill_price={fill_price}, api_pair={api_pair}, filled_volume={filled_volume}")
        print()
        
        # Trigger notification
        print("4. Sending notification...")
        ttslo.check_triggered_orders()
        
        # Verify notification was sent
        if mock_notif.notify_tsl_order_filled.called:
            call_args = mock_notif.notify_tsl_order_filled.call_args
            print("   ✓ Telegram notification sent!")
            print()
            print("   Notification details:")
            print(f"     • Config ID: {call_args[1]['config_id']}")
            print(f"     • Order ID: {call_args[1]['order_id']}")
            print(f"     • Pair: {call_args[1]['pair']}")
            print(f"     • Fill Price: ${call_args[1]['fill_price']:,.2f}")
            print()
            print("   Message sent to Telegram:")
            print("   ┌─────────────────────────────────────────────────────┐")
            print("   │ 💰 TTSLO: Trailing Stop Loss order FILLED!         │")
            print("   │                                                     │")
            print(f"   │ Config: {call_args[1]['config_id']:<43} │")
            print(f"   │ Order ID: {call_args[1]['order_id']:<41} │")
            print(f"   │ Pair: {call_args[1]['pair']:<45} │")
            print(f"   │ Fill Price: ${call_args[1]['fill_price']:,.2f}{' ' * 38}│")
            print("   └─────────────────────────────────────────────────────┘")
        else:
            print("   ✗ Notification not sent!")
        print()
        
        # Verify state was updated
        if ttslo.state['btc_sell_1']['fill_notified'] == 'true':
            print("5. State updated:")
            print("   ✓ fill_notified flag set to 'true'")
            print("   → This prevents duplicate notifications")
        print()
        
        # Scenario 3: Check again - no duplicate notification
        print("6. Scenario: Checking again (duplicate prevention)")
        mock_notif.reset_mock()
        
        ttslo.check_triggered_orders()
        
        if not mock_notif.notify_tsl_order_filled.called:
            print("   ✓ No notification sent (already notified)")
            print("   → Duplicate prevention working correctly")
        else:
            print("   ✗ Duplicate notification sent!")
        print()
        
        print("=" * 70)
        print("DEMONSTRATION COMPLETE")
        print("=" * 70)
        print()
        print("Key Features Demonstrated:")
        print("  • Automatic monitoring of triggered orders")
        print("  • Detection of filled orders via Kraken API")
        print("  • Telegram notification with order details")
        print("  • Fill price included in notification")
        print("  • Duplicate prevention via state tracking")
        print()


if __name__ == '__main__':
    demo_order_fill_notification()
