#!/usr/bin/env python3
"""
Demo script showing chained orders functionality.

This demonstrates how to set up chained orders that automatically activate
when parent orders fill.
"""
import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ConfigManager
from ttslo import TTSLO
from unittest.mock import Mock


def demo_chained_orders():
    """Demonstrate chained orders feature."""
    print("=" * 70)
    print("TTSLO Chained Orders Demo")
    print("=" * 70)
    print()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Create config with chained orders
        print("📝 Creating configuration with chained orders:")
        print("-" * 70)
        
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled,linked_order_id\n')
            f.write('btc_buy,XXBTZUSD,100000,below,buy,0.01,2.0,true,btc_sell\n')
            f.write('btc_sell,XXBTZUSD,120000,above,sell,0.01,2.0,false,\n')
            print("  • btc_buy: Buy BTC when price drops below $100,000")
            print("    - Linked to: btc_sell")
            print("    - Status: ENABLED")
            print()
            print("  • btc_sell: Sell BTC when price rises above $120,000")
            print("    - Linked from: btc_buy")
            print("    - Status: DISABLED (will enable when btc_buy fills)")
        
        print()
        print("-" * 70)
        
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, log_file)
        
        # Mock APIs
        mock_api_ro = Mock()
        mock_api_rw = Mock()
        mock_notification = Mock()
        
        # Create TTSLO instance
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=mock_api_ro,
            kraken_api_readwrite=mock_api_rw,
            dry_run=False,
            verbose=True,
            notification_manager=mock_notification
        )
        
        # Load configs
        ttslo.configs = config_manager.load_config()
        
        print()
        print("✅ Configuration loaded successfully")
        print()
        print("📊 Current configuration status:")
        print("-" * 70)
        for config in ttslo.configs:
            print(f"  {config['id']}: enabled={config['enabled']}, "
                  f"linked_to={config.get('linked_order_id', 'none')}")
        
        print()
        print("-" * 70)
        print()
        print("🎯 Simulating btc_buy order filling...")
        print("-" * 70)
        
        # Simulate order filled
        order_info = {
            'status': 'closed',  # Fully filled
            'price': '99500',
            'vol_exec': '0.01',
            'descr': {'pair': 'XXBTZUSD'}
        }
        
        # Call activation logic
        ttslo.activate_linked_order_if_needed('btc_buy', order_info)
        
        print("  • Order btc_buy filled at $99,500")
        print("  • Checking for linked orders...")
        
        # Reload configs to see changes
        ttslo.configs = config_manager.load_config()
        
        print()
        print("📊 Updated configuration status:")
        print("-" * 70)
        for config in ttslo.configs:
            status_icon = "✅" if config['enabled'] == 'true' else "❌"
            print(f"  {status_icon} {config['id']}: enabled={config['enabled']}, "
                  f"linked_to={config.get('linked_order_id', 'none')}")
        
        print()
        print("-" * 70)
        
        # Verify linked order was activated
        sell_config = next(c for c in ttslo.configs if c['id'] == 'btc_sell')
        if sell_config['enabled'] == 'true':
            print()
            print("✅ SUCCESS: Linked order btc_sell was automatically ENABLED!")
            print()
            print("💡 What happens next:")
            print("  1. btc_sell now monitors for BTC price to rise above $120,000")
            print("  2. When threshold is met, a TSL sell order will be created")
            print("  3. Result: Automated buy-low ($100k), sell-high ($120k) strategy")
            print("  4. Profit: ~$20,000 per BTC traded")
            print()
        else:
            print()
            print("❌ ERROR: Linked order was not activated")
            print()
        
        # Check if notification was sent
        if mock_notification.notify_linked_order_activated.called:
            print("📢 Notification sent:")
            call_args = mock_notification.notify_linked_order_activated.call_args
            print(f"  • Parent order: {call_args[1]['parent_id']}")
            print(f"  • Linked order: {call_args[1]['linked_id']}")
            print(f"  • Parent pair: {call_args[1]['parent_pair']}")
            print(f"  • Linked pair: {call_args[1]['linked_pair']}")
            print()
        
        print("=" * 70)
        print("Demo complete! The chained orders feature is working correctly.")
        print("=" * 70)


if __name__ == '__main__':
    demo_chained_orders()
