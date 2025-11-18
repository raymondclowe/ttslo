"""Test that all variants of enabled field are handled correctly."""
import pytest
from validator import ConfigValidator, ValidationResult


class TestEnabledFieldVariants:
    """Test that enabled='true', 'yes', and '1' all work correctly."""
    
    def create_valid_config(self, config_id, enabled_value):
        """Create a valid config with specified enabled value."""
        return {
            'id': config_id,
            'pair': 'XBTUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5',
            'enabled': enabled_value
        }
    
    def test_enabled_true_is_included(self):
        """Test that enabled='true' config is included in result.configs."""
        validator = ConfigValidator(kraken_api=None, debug_mode=False)
        config = self.create_valid_config('test_true', 'true')
        result = validator.validate_config_file([config])
        
        assert len(result.configs) == 1
        assert result.configs[0]['id'] == 'test_true'
    
    def test_enabled_yes_is_included(self):
        """Test that enabled='yes' config is included in result.configs."""
        validator = ConfigValidator(kraken_api=None, debug_mode=False)
        config = self.create_valid_config('test_yes', 'yes')
        result = validator.validate_config_file([config])
        
        assert len(result.configs) == 1
        assert result.configs[0]['id'] == 'test_yes'
    
    def test_enabled_1_is_included(self):
        """Test that enabled='1' config is included in result.configs."""
        validator = ConfigValidator(kraken_api=None, debug_mode=False)
        config = self.create_valid_config('test_1', '1')
        result = validator.validate_config_file([config])
        
        assert len(result.configs) == 1
        assert result.configs[0]['id'] == 'test_1'
    
    def test_enabled_false_is_excluded(self):
        """Test that enabled='false' config is excluded from result.configs."""
        validator = ConfigValidator(kraken_api=None, debug_mode=False)
        config = self.create_valid_config('test_false', 'false')
        result = validator.validate_config_file([config])
        
        assert len(result.configs) == 0
    
    def test_enabled_no_is_excluded(self):
        """Test that enabled='no' config is excluded from result.configs."""
        validator = ConfigValidator(kraken_api=None, debug_mode=False)
        config = self.create_valid_config('test_no', 'no')
        result = validator.validate_config_file([config])
        
        assert len(result.configs) == 0
    
    def test_enabled_0_is_excluded(self):
        """Test that enabled='0' config is excluded from result.configs."""
        validator = ConfigValidator(kraken_api=None, debug_mode=False)
        config = self.create_valid_config('test_0', '0')
        result = validator.validate_config_file([config])
        
        assert len(result.configs) == 0
    
    def test_mixed_enabled_values(self):
        """Test that mix of enabled values are handled correctly."""
        validator = ConfigValidator(kraken_api=None, debug_mode=False)
        configs = [
            self.create_valid_config('test_true', 'true'),
            self.create_valid_config('test_yes', 'yes'),
            self.create_valid_config('test_1', '1'),
            self.create_valid_config('test_false', 'false'),
            self.create_valid_config('test_no', 'no'),
            self.create_valid_config('test_0', '0'),
        ]
        result = validator.validate_config_file(configs)
        
        # Only true, yes, and 1 should be included
        assert len(result.configs) == 3
        config_ids = [c['id'] for c in result.configs]
        assert 'test_true' in config_ids
        assert 'test_yes' in config_ids
        assert 'test_1' in config_ids
        assert 'test_false' not in config_ids
        assert 'test_no' not in config_ids
        assert 'test_0' not in config_ids
    
    def test_enabled_case_insensitive(self):
        """Test that enabled field is case-insensitive."""
        validator = ConfigValidator(kraken_api=None, debug_mode=False)
        configs = [
            self.create_valid_config('test_TRUE', 'TRUE'),
            self.create_valid_config('test_True', 'True'),
            self.create_valid_config('test_YES', 'YES'),
            self.create_valid_config('test_Yes', 'Yes'),
        ]
        result = validator.validate_config_file(configs)
        
        # All should be included (case-insensitive)
        assert len(result.configs) == 4
        config_ids = [c['id'] for c in result.configs]
        assert 'test_TRUE' in config_ids
        assert 'test_True' in config_ids
        assert 'test_YES' in config_ids
        assert 'test_Yes' in config_ids
