"""
Integration test for validation error handling during continuous run.
Tests that configs with validation errors are automatically disabled.
"""
import os
import tempfile
import csv
from config import ConfigManager
from validator import ConfigValidator
from ttslo import TTSLO


class MockKrakenAPI:
    """Mock Kraken API for testing."""
    def __init__(self, prices=None):
        self._prices = prices or {}
    
    def get_current_price(self, pair):
        return self._prices.get(pair, 50000)
    
    def get_balance(self):
        return {}


def test_validation_error_disables_config():
    """
    Test that when a config has validation errors during reload,
    it gets disabled and an error message is displayed.
    """
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        config_file = f.name
        writer = csv.writer(f)
        writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                        'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        # Good config: threshold is well above current price (60000 > 50000)
        writer.writerow(['good_1', 'XXBTZUSD', '60000', 'above', 'sell', '0.01', '5.0', 'true'])
        # Bad config: invalid threshold price
        writer.writerow(['bad_1', 'XXBTZUSD', 'invalid', 'above', 'sell', '0.01', '5.0', 'true'])
    
    # Create temp state and log files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        state_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        log_file = f.name
    
    try:
        # Create config manager
        config_manager = ConfigManager(
            config_file=config_file,
            state_file=state_file,
            log_file=log_file
        )
        
        # Create mock API
        mock_api = MockKrakenAPI(prices={'XXBTZUSD': 50000, 'XETHZUSD': 3000})
        
        # Create TTSLO instance (NOT in dry-run mode so configs get disabled)
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=mock_api,
            kraken_api_readwrite=None,
            dry_run=False,  # Must be False to actually disable configs
            verbose=True,
            debug=False
        )
        
        # Attempt to validate and load config
        # This should fail due to bad_1 having invalid threshold_price
        validation_passed = ttslo.validate_and_load_config()
        
        # Validation should fail
        assert not validation_passed, "Validation should fail with invalid config"
        
        # Reload the config file to check if bad_1 was disabled
        configs = config_manager.load_config()
        
        # Find configs
        good_config = None
        bad_config = None
        for config in configs:
            if config['id'] == 'good_1':
                good_config = config
            elif config['id'] == 'bad_1':
                bad_config = config
        
        # Verify bad_1 is disabled
        assert bad_config is not None, "bad_1 config should exist"
        assert bad_config['enabled'].lower() == 'false', "bad_1 should be disabled"
        
        # Verify good_1 is still enabled
        assert good_config is not None, "good_1 config should exist"
        assert good_config['enabled'].lower() == 'true', "good_1 should remain enabled"
        
        print("✓ Test passed: Config with validation error was automatically disabled")
        
    finally:
        # Clean up temp files
        for filepath in [config_file, state_file, log_file]:
            if os.path.exists(filepath):
                os.unlink(filepath)


def test_validation_with_multiple_errors():
    """
    Test that multiple configs with validation errors are all disabled.
    """
    # Create temporary config file with multiple errors
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        config_file = f.name
        writer = csv.writer(f)
        writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                        'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        # Good config: threshold well above current price (60000 > 50000)
        writer.writerow(['good_1', 'XXBTZUSD', '60000', 'above', 'sell', '0.01', '5.0', 'true'])
        # Bad config 1: invalid price
        writer.writerow(['bad_1', 'XXBTZUSD', 'invalid', 'above', 'sell', '0.01', '5.0', 'true'])
        # Bad config 2: invalid threshold type
        writer.writerow(['bad_2', 'XETHZUSD', '3500', 'bad_type', 'sell', '0.1', '3.5', 'true'])
        # Good config 2: threshold well below current price (2000 < 3000)
        writer.writerow(['good_2', 'XETHZUSD', '2000', 'below', 'buy', '0.1', '3.5', 'true'])
    
    # Create temp state and log files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        state_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        log_file = f.name
    
    try:
        # Create config manager
        config_manager = ConfigManager(
            config_file=config_file,
            state_file=state_file,
            log_file=log_file
        )
        
        # Create mock API
        mock_api = MockKrakenAPI(prices={'XXBTZUSD': 50000, 'XETHZUSD': 3000})
        
        # Create TTSLO instance (NOT in dry-run mode so configs get disabled)
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=mock_api,
            kraken_api_readwrite=None,
            dry_run=False,  # Must be False to actually disable configs
            verbose=True,
            debug=False
        )
        
        # Attempt to validate and load config
        validation_passed = ttslo.validate_and_load_config()
        
        # Validation should fail
        assert not validation_passed, "Validation should fail with invalid configs"
        
        # Reload the config file to check disabled configs
        configs = config_manager.load_config()
        
        # Check each config
        for config in configs:
            if config['id'] in ['bad_1', 'bad_2']:
                assert config['enabled'].lower() == 'false', f"{config['id']} should be disabled"
            elif config['id'] in ['good_1', 'good_2']:
                assert config['enabled'].lower() == 'true', f"{config['id']} should remain enabled"
        
        print("✓ Test passed: Multiple configs with validation errors were all disabled")
        
    finally:
        # Clean up temp files
        for filepath in [config_file, state_file, log_file]:
            if os.path.exists(filepath):
                os.unlink(filepath)


if __name__ == '__main__':
    test_validation_error_disables_config()
    test_validation_with_multiple_errors()
    print("\n✓ All integration tests passed!")
