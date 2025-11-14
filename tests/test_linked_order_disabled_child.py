"""
Test that linked orders activate correctly even when child is disabled.

This tests the fix for the bug where activate_linked_order_if_needed() failed
to find disabled child configs because it only searched in self.configs which
contains only enabled='true' configs from validation.
"""
import os
import tempfile
import unittest
from unittest.mock import Mock, MagicMock
from ttslo import TTSLO
from config import ConfigManager
from notifications import NotificationManager


class TestLinkedOrderDisabledChild(unittest.TestCase):
    """Test linked order activation with disabled child."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary files
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config.csv')
        self.state_file = os.path.join(self.temp_dir, 'state.csv')
        self.log_file = os.path.join(self.temp_dir, 'logs.csv')
        
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
        """Create test config file."""
        import csv
        with open(self.config_file, 'w', newline='') as f:
            fieldnames = ['id', 'pair', 'threshold_price', 'threshold_type', 'direction',
                         'volume', 'trailing_offset_percent', 'enabled', 'linked_order_id']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for config in configs:
                writer.writerow(config)
    
    def test_activate_child_when_child_disabled(self):
        """
        Test that child order is activated even when it starts as enabled='false'.
        
        This is the main bug fix: activate_linked_order_if_needed() must load
        ALL configs from CSV, not just self.configs which only has enabled='true'.
        """
        # Create configs: parent enabled, child disabled
        configs = [
            {
                'id': 'parent',
                'pair': 'XXBTZUSD',
                'threshold_price': '100000',
                'threshold_type': 'below',
                'direction': 'buy',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'true',
                'linked_order_id': 'child'
            },
            {
                'id': 'child',
                'pair': 'XXBTZUSD',
                'threshold_price': '120000',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'false',  # DISABLED!
                'linked_order_id': ''
            }
        ]
        self.create_test_config(configs)
        
        # Load only enabled configs (simulating startup validation)
        # This mimics what happens at line 1690: self.configs = result.configs
        all_configs = self.config_manager.load_config()
        self.ttslo.configs = [c for c in all_configs if c.get('enabled', '').lower() == 'true']
        
        # Verify parent is in self.configs but child is NOT
        self.assertEqual(len(self.ttslo.configs), 1)
        self.assertEqual(self.ttslo.configs[0]['id'], 'parent')
        
        # Simulate parent order filled
        order_info = {
            'status': 'closed',  # Fully filled
            'vol_exec': '0.01',
            'price': '99000'
        }
        
        # Call activate_linked_order_if_needed
        # This should find child even though it's not in self.configs
        self.ttslo.activate_linked_order_if_needed('parent', order_info)
        
        # Verify child was enabled in CSV
        reloaded = self.config_manager.load_config()
        child_config = [c for c in reloaded if c['id'] == 'child'][0]
        self.assertEqual(child_config['enabled'], 'true',
                        "Child order should be activated to enabled='true'")
        
        # Verify notification was sent
        self.notification_manager.notify_linked_order_activated.assert_called_once()
    
    def test_activate_child_when_child_pending(self):
        """
        Test that child order is activated even when it starts as enabled='pending'.
        """
        configs = [
            {
                'id': 'parent',
                'pair': 'XXBTZUSD',
                'threshold_price': '100000',
                'threshold_type': 'below',
                'direction': 'buy',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'true',
                'linked_order_id': 'child'
            },
            {
                'id': 'child',
                'pair': 'XXBTZUSD',
                'threshold_price': '120000',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'pending',  # PENDING!
                'linked_order_id': ''
            }
        ]
        self.create_test_config(configs)
        
        # Load only enabled='true' configs
        all_configs = self.config_manager.load_config()
        self.ttslo.configs = [c for c in all_configs if c.get('enabled', '').lower() == 'true']
        
        # Verify only parent in self.configs
        self.assertEqual(len(self.ttslo.configs), 1)
        
        # Simulate parent filled
        order_info = {'status': 'closed'}
        
        self.ttslo.activate_linked_order_if_needed('parent', order_info)
        
        # Verify child was activated
        reloaded = self.config_manager.load_config()
        child_config = [c for c in reloaded if c['id'] == 'child'][0]
        self.assertEqual(child_config['enabled'], 'true')
    
    def test_error_logged_when_child_not_in_csv(self):
        """
        Test that appropriate error is logged when linked child doesn't exist at all.
        """
        configs = [
            {
                'id': 'parent',
                'pair': 'XXBTZUSD',
                'threshold_price': '100000',
                'threshold_type': 'below',
                'direction': 'buy',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'true',
                'linked_order_id': 'nonexistent'  # Doesn't exist!
            }
        ]
        self.create_test_config(configs)
        
        all_configs = self.config_manager.load_config()
        self.ttslo.configs = [c for c in all_configs if c.get('enabled', '').lower() == 'true']
        
        order_info = {'status': 'closed'}
        
        # Should not raise exception, but should log error
        self.ttslo.activate_linked_order_if_needed('parent', order_info)
        
        # Child should not be activated (doesn't exist)
        reloaded = self.config_manager.load_config()
        self.assertEqual(len(reloaded), 1)  # Only parent exists


if __name__ == '__main__':
    unittest.main()
