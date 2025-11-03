"""
Tests for chained orders validation.
"""
import unittest
from validator import ConfigValidator


class TestChainedOrdersValidation(unittest.TestCase):
    """Test validation of linked_order_id field."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator(kraken_api=None, debug_mode=False)
    
    def test_valid_linked_order(self):
        """Test that valid linked order passes validation."""
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
        
        result = self.validator.validate_config_file(configs)
        
        # Should have no errors related to linked_order_id
        linked_errors = [e for e in result.errors 
                        if e['field'] == 'linked_order_id']
        self.assertEqual(len(linked_errors), 0, 
                        f"Should have no linked_order_id errors, but got: {linked_errors}")
    
    def test_linked_order_not_found(self):
        """Test that error is raised if linked order doesn't exist."""
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
                'linked_order_id': 'nonexistent'
            }
        ]
        
        result = self.validator.validate_config_file(configs)
        
        # Should have error about nonexistent linked order
        linked_errors = [e for e in result.errors 
                        if e['field'] == 'linked_order_id']
        self.assertEqual(len(linked_errors), 1)
        self.assertIn('does not exist', linked_errors[0]['message'])
        self.assertIn('nonexistent', linked_errors[0]['message'])
    
    def test_self_reference_error(self):
        """Test that error is raised if order links to itself."""
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
                'linked_order_id': 'btc_buy'  # Links to itself!
            }
        ]
        
        result = self.validator.validate_config_file(configs)
        
        # Should have error about self-reference
        linked_errors = [e for e in result.errors 
                        if e['field'] == 'linked_order_id']
        self.assertEqual(len(linked_errors), 1)
        self.assertIn('Cannot link order to itself', linked_errors[0]['message'])
    
    def test_circular_reference_two_orders(self):
        """Test that circular reference is detected (A->B->A)."""
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
                'threshold_price': '120000',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'false',
                'linked_order_id': 'order_a'  # Circular!
            }
        ]
        
        result = self.validator.validate_config_file(configs)
        
        # Should have error about circular reference
        linked_errors = [e for e in result.errors 
                        if e['field'] == 'linked_order_id']
        self.assertGreaterEqual(len(linked_errors), 1, 
                               "Should detect circular reference")
        self.assertTrue(any('Circular reference' in e['message'] 
                           for e in linked_errors))
    
    def test_circular_reference_three_orders(self):
        """Test that circular reference is detected (A->B->C->A)."""
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
                'linked_order_id': 'order_a'  # Circular!
            }
        ]
        
        result = self.validator.validate_config_file(configs)
        
        # Should have error about circular reference
        linked_errors = [e for e in result.errors 
                        if e['field'] == 'linked_order_id']
        self.assertGreaterEqual(len(linked_errors), 1,
                               "Should detect circular reference in chain")
        self.assertTrue(any('Circular reference' in e['message'] 
                           for e in linked_errors))
    
    def test_valid_long_chain(self):
        """Test that valid long chain (A->B->C->D) is allowed."""
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
                'linked_order_id': 'order_d'
            },
            {
                'id': 'order_d',
                'pair': 'XXBTZUSD',
                'threshold_price': '115000',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'false',
                'linked_order_id': ''
            }
        ]
        
        result = self.validator.validate_config_file(configs)
        
        # Should have no errors for valid chain
        linked_errors = [e for e in result.errors 
                        if e['field'] == 'linked_order_id']
        self.assertEqual(len(linked_errors), 0,
                        f"Valid chain should have no errors, but got: {linked_errors}")
    
    def test_very_long_chain_warning(self):
        """Test that warning is raised for very long chains (>5 orders)."""
        # Create chain of 7 orders
        configs = []
        for i in range(7):
            order_id = f'order_{i}'
            linked_id = f'order_{i+1}' if i < 6 else ''
            configs.append({
                'id': order_id,
                'pair': 'XXBTZUSD',
                'threshold_price': str(100000 + i * 1000),
                'threshold_type': 'above' if i % 2 == 0 else 'below',
                'direction': 'sell' if i % 2 == 0 else 'buy',
                'volume': '0.01',
                'trailing_offset_percent': '2.0',
                'enabled': 'true' if i == 0 else 'false',
                'linked_order_id': linked_id
            })
        
        result = self.validator.validate_config_file(configs)
        
        # Should have warning about long chain
        linked_warnings = [w for w in result.warnings 
                          if w['field'] == 'linked_order_id']
        self.assertGreaterEqual(len(linked_warnings), 1,
                               "Should warn about very long chain")
        self.assertTrue(any('long order chain' in w['message'].lower() 
                           for w in linked_warnings))


if __name__ == '__main__':
    unittest.main()
