"""
Test that configs with validation errors are automatically disabled.
"""
import os
import tempfile
import csv
from config import ConfigManager
from validator import ConfigValidator


class FakeKrakenAPI:
    """Mock Kraken API for testing."""
    def __init__(self, prices=None):
        self._prices = prices or {}
    
    def get_current_price(self, pair):
        return self._prices.get(pair)
    
    def get_balance(self):
        return {}


def test_disable_configs_with_errors():
    """Test that configs with validation errors are disabled in the CSV."""
    # Create a temporary config file with one valid and one invalid config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        config_file = f.name
        writer = csv.writer(f)
        writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                        'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writerow(['good_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
        writer.writerow(['bad_1', 'XXBTZUSD', 'invalid', 'above', 'sell', '0.01', '5.0', 'true'])
        writer.writerow(['good_2', 'XETHZUSD', '3000', 'above', 'sell', '0.1', '3.5', 'true'])
    
    try:
        # Load configs
        config_manager = ConfigManager(config_file=config_file)
        configs = config_manager.load_config()
        
        # Verify we have 3 configs
        assert len(configs) == 3
        
        # Create validator (no API, so no price validation)
        validator = ConfigValidator(kraken_api=None)
        
        # Validate configs
        result = validator.validate_config_file(configs)
        
        # Should have validation error for bad_1
        assert not result.is_valid()
        assert len(result.errors) > 0
        
        # Check that bad_1 is in the error list
        config_ids_with_errors = result.get_config_ids_with_errors()
        assert 'bad_1' in config_ids_with_errors
        assert 'good_1' not in config_ids_with_errors
        assert 'good_2' not in config_ids_with_errors
        
        # Disable configs with errors
        config_manager.disable_configs(config_ids_with_errors)
        
        # Reload configs
        configs = config_manager.load_config()
        
        # Find the bad_1 config and verify it's disabled
        bad_config = None
        for config in configs:
            if config['id'] == 'bad_1':
                bad_config = config
                break
        
        assert bad_config is not None
        assert bad_config['enabled'].lower() == 'false'
        
        # Verify good configs are still enabled
        for config in configs:
            if config['id'] in ['good_1', 'good_2']:
                assert config['enabled'].lower() == 'true'
        
    finally:
        # Clean up temp file
        if os.path.exists(config_file):
            os.unlink(config_file)


def test_disable_multiple_configs():
    """Test that multiple configs with errors are all disabled."""
    # Create a temporary config file with multiple invalid configs
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        config_file = f.name
        writer = csv.writer(f)
        writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                        'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writerow(['bad_1', 'XXBTZUSD', 'invalid', 'above', 'sell', '0.01', '5.0', 'true'])
        writer.writerow(['bad_2', 'XETHZUSD', '3000', 'invalid_type', 'sell', '0.1', '3.5', 'true'])
        writer.writerow(['good_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
    
    try:
        # Load configs
        config_manager = ConfigManager(config_file=config_file)
        configs = config_manager.load_config()
        
        # Create validator
        validator = ConfigValidator(kraken_api=None)
        
        # Validate configs
        result = validator.validate_config_file(configs)
        
        # Should have validation errors
        assert not result.is_valid()
        
        # Get configs with errors
        config_ids_with_errors = result.get_config_ids_with_errors()
        assert 'bad_1' in config_ids_with_errors
        assert 'bad_2' in config_ids_with_errors
        assert 'good_1' not in config_ids_with_errors
        
        # Disable configs with errors
        config_manager.disable_configs(config_ids_with_errors)
        
        # Reload configs
        configs = config_manager.load_config()
        
        # Verify bad configs are disabled
        for config in configs:
            if config['id'] in ['bad_1', 'bad_2']:
                assert config['enabled'].lower() == 'false', f"Config {config['id']} should be disabled"
            elif config['id'] == 'good_1':
                assert config['enabled'].lower() == 'true', f"Config {config['id']} should remain enabled"
        
    finally:
        # Clean up temp file
        if os.path.exists(config_file):
            os.unlink(config_file)


def test_no_disable_when_no_errors():
    """Test that configs are not modified when there are no errors."""
    # Create a temporary config file with all valid configs
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        config_file = f.name
        writer = csv.writer(f)
        writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                        'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writerow(['good_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
        writer.writerow(['good_2', 'XETHZUSD', '3000', 'above', 'sell', '0.1', '3.5', 'true'])
    
    try:
        # Load configs
        config_manager = ConfigManager(config_file=config_file)
        configs = config_manager.load_config()
        
        # Create validator
        validator = ConfigValidator(kraken_api=None)
        
        # Validate configs
        result = validator.validate_config_file(configs)
        
        # Should have no validation errors (without API, basic validation should pass)
        assert result.is_valid()
        
        # Get configs with errors (should be empty)
        config_ids_with_errors = result.get_config_ids_with_errors()
        assert len(config_ids_with_errors) == 0
        
        # Try to disable (should do nothing)
        config_manager.disable_configs(config_ids_with_errors)
        
        # Reload configs
        configs = config_manager.load_config()
        
        # Verify all configs are still enabled
        for config in configs:
            assert config['enabled'].lower() == 'true', f"Config {config['id']} should remain enabled"
        
    finally:
        # Clean up temp file
        if os.path.exists(config_file):
            os.unlink(config_file)


if __name__ == '__main__':
    test_disable_configs_with_errors()
    test_disable_multiple_configs()
    test_no_disable_when_no_errors()
    print("All tests passed!")
