"""
Tests for chained orders functionality.
"""
import os
import tempfile
import unittest
from unittest.mock import Mock, MagicMock, patch
from ttslo import TTSLO
from config import ConfigManager
from notifications import NotificationManager


class TestChainedOrders(unittest.TestCase):
    """Test chained orders feature."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.csv')
        self.state_file = os.path.join(self.temp_dir, 'test_state.csv')
        self.log_file = os.path.join(self.temp_dir, 'test_logs.csv')
        
        # Create config manager
        self.config_manager = ConfigManager(
            config_file=self.config_file,
            state_file=self.state_file,
            log_file=self.log_file
        )
        
        # Create mock APIs
        self.kraken_api_readonly = Mock()
        self.kraken_api_readwrite = Mock()
        
        # Create notification manager mock
        self.notification_manager = Mock(spec=NotificationManager)
        
        # Create TTSLO instance
        self.ttslo = TTSLO(
            config_manager=self.config_manager,
            kraken_api_readonly=self.kraken_api_readonly,
            kraken_api_readwrite=self.kraken_api_readwrite,
            dry_run=False,
            verbose=True,
            notification_manager=self.notification_manager
        )
        
        # Initialize state
        self.ttslo.state = {}
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_config(self, configs):
        """Create test config file with given configurations."""
        import csv
        with open(self.config_file, 'w', newline='') as f:
            fieldnames = ['id', 'pair', 'threshold_price', 'threshold_type', 'direction',
                         'volume', 'trailing_offset_percent', 'enabled', 'linked_order_id']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for config in configs:
                writer.writerow(config)
    
    def test_linked_order_activated_on_fill(self):
        """Test that linked order is activated when parent order fills."""
        # Create chained configs: buy low -> sell high
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
                'enabled': 'false',  # Starts disabled
                'linked_order_id': ''
            }
        ]
        self.create_test_config(configs)
        self.ttslo.configs = self.config_manager.load_config()
        
        # Simulate parent order filled
        order_info = {
            'status': 'closed',
            'price': '100500',
            'vol_exec': '0.01'
        }
        
        # Call activate_linked_order_if_needed
        self.ttslo.activate_linked_order_if_needed('btc_buy', order_info)
        
        # Verify linked order was activated (enabled set to true)
        updated_configs = self.config_manager.load_config()
        sell_config = next(c for c in updated_configs if c['id'] == 'btc_sell')
        self.assertEqual(sell_config['enabled'], 'true', "Linked order should be enabled")
        
        # Verify notification was sent
        self.notification_manager.notify_linked_order_activated.assert_called_once()
        call_args = self.notification_manager.notify_linked_order_activated.call_args
        self.assertEqual(call_args[1]['parent_id'], 'btc_buy')
        self.assertEqual(call_args[1]['linked_id'], 'btc_sell')
    
    def test_no_activation_on_partial_fill(self):
        """Test that linked order is NOT activated on partial fill (status != closed)."""
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
                'enabled': 'false',
                'linked_order_id': ''
            }
        ]
        self.create_test_config(configs)
        self.ttslo.configs = self.config_manager.load_config()
        
        # Simulate partially filled order
        order_info = {
            'status': 'open',  # Not closed yet
            'price': '100500',
            'vol_exec': '0.005'
        }
        
        # Call activate_linked_order_if_needed
        self.ttslo.activate_linked_order_if_needed('btc_buy', order_info)
        
        # Verify linked order was NOT activated
        updated_configs = self.config_manager.load_config()
        sell_config = next(c for c in updated_configs if c['id'] == 'btc_sell')
        self.assertEqual(sell_config['enabled'], 'false', "Linked order should remain disabled")
        
        # Verify notification was NOT sent
        self.notification_manager.notify_linked_order_activated.assert_not_called()
    
    def test_no_activation_if_no_linked_order(self):
        """Test that nothing happens if config has no linked_order_id."""
        configs = [
            {
                'id': 'btc_sell',
                'pair': 'XXBTZUSD',
                'threshold_price': '120000',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'true',
                'linked_order_id': ''  # No linked order
            }
        ]
        self.create_test_config(configs)
        self.ttslo.configs = self.config_manager.load_config()
        
        # Simulate order filled
        order_info = {
            'status': 'closed',
            'price': '120500'
        }
        
        # Call activate_linked_order_if_needed - should return early
        self.ttslo.activate_linked_order_if_needed('btc_sell', order_info)
        
        # Verify notification was NOT sent
        self.notification_manager.notify_linked_order_activated.assert_not_called()
    
    def test_error_if_linked_order_not_found(self):
        """Test that error is logged if linked order doesn't exist."""
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
                'linked_order_id': 'nonexistent_order'  # Doesn't exist!
            }
        ]
        self.create_test_config(configs)
        self.ttslo.configs = self.config_manager.load_config()
        
        # Simulate order filled
        order_info = {
            'status': 'closed',
            'price': '100500'
        }
        
        # Call activate_linked_order_if_needed - should log error
        self.ttslo.activate_linked_order_if_needed('btc_buy', order_info)
        
        # Verify notification was NOT sent
        self.notification_manager.notify_linked_order_activated.assert_not_called()
        
        # Verify error was logged (check log file)
        with open(self.log_file, 'r') as f:
            content = f.read()
            self.assertIn('ERROR', content)
            self.assertIn('nonexistent_order', content)
            self.assertIn('not found', content)
    
    def test_no_activation_if_already_enabled(self):
        """Test that linked order is not re-activated if already enabled."""
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
                'enabled': 'true',  # Already enabled!
                'linked_order_id': ''
            }
        ]
        self.create_test_config(configs)
        self.ttslo.configs = self.config_manager.load_config()
        
        # Simulate order filled
        order_info = {
            'status': 'closed',
            'price': '100500'
        }
        
        # Call activate_linked_order_if_needed
        self.ttslo.activate_linked_order_if_needed('btc_buy', order_info)
        
        # Verify notification was NOT sent (already enabled)
        self.notification_manager.notify_linked_order_activated.assert_not_called()
    
    def test_no_activation_if_already_triggered(self):
        """Test that linked order is not activated if already triggered."""
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
                'enabled': 'false',
                'linked_order_id': ''
            }
        ]
        self.create_test_config(configs)
        self.ttslo.configs = self.config_manager.load_config()
        
        # Set linked order as already triggered in state
        self.ttslo.state['btc_sell'] = {
            'id': 'btc_sell',
            'triggered': 'true',  # Already triggered!
            'order_id': 'SOME_ORDER_ID'
        }
        
        # Simulate parent order filled
        order_info = {
            'status': 'closed',
            'price': '100500'
        }
        
        # Call activate_linked_order_if_needed
        self.ttslo.activate_linked_order_if_needed('btc_buy', order_info)
        
        # Verify config was NOT updated (already triggered)
        updated_configs = self.config_manager.load_config()
        sell_config = next(c for c in updated_configs if c['id'] == 'btc_sell')
        self.assertEqual(sell_config['enabled'], 'false', 
                        "Config should not be updated if already triggered")
        
        # Verify notification was NOT sent
        self.notification_manager.notify_linked_order_activated.assert_not_called()
    
    def test_three_order_chain(self):
        """Test chain of three orders: A -> B -> C."""
        configs = [
            {
                'id': 'order_a',
                'pair': 'XXBTZUSD',
                'threshold_price': '100000',
                'threshold_type': 'below',
                'direction': 'buy',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'true',
                'linked_order_id': 'order_b'
            },
            {
                'id': 'order_b',
                'pair': 'XXBTZUSD',
                'threshold_price': '110000',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'false',
                'linked_order_id': 'order_c'
            },
            {
                'id': 'order_c',
                'pair': 'XXBTZUSD',
                'threshold_price': '105000',
                'threshold_type': 'below',
                'direction': 'buy',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'false',
                'linked_order_id': ''
            }
        ]
        self.create_test_config(configs)
        self.ttslo.configs = self.config_manager.load_config()
        
        # Simulate order A filled -> should activate B
        order_info_a = {'status': 'closed', 'price': '100500'}
        self.ttslo.activate_linked_order_if_needed('order_a', order_info_a)
        
        # Reload configs to see update
        self.ttslo.configs = self.config_manager.load_config()
        
        # Verify B is now enabled
        order_b = next(c for c in self.ttslo.configs if c['id'] == 'order_b')
        self.assertEqual(order_b['enabled'], 'true', "Order B should be enabled")
        
        # Simulate order B filled -> should activate C
        order_info_b = {'status': 'closed', 'price': '110500'}
        self.ttslo.activate_linked_order_if_needed('order_b', order_info_b)
        
        # Reload configs to see update
        self.ttslo.configs = self.config_manager.load_config()
        
        # Verify C is now enabled
        order_c = next(c for c in self.ttslo.configs if c['id'] == 'order_c')
        self.assertEqual(order_c['enabled'], 'true', "Order C should be enabled")
        
        # Verify notifications sent for both activations
        self.assertEqual(self.notification_manager.notify_linked_order_activated.call_count, 2)


if __name__ == '__main__':
    unittest.main()
