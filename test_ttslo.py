#!/usr/bin/env python3
"""
Basic tests for TTSLO functionality.
"""
import os
import sys
import tempfile
import csv
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ttslo import TTSLO
from config import ConfigManager
from kraken_api import KrakenAPI


def test_config_manager():
    """Test configuration manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'test_config.csv')
        state_file = os.path.join(tmpdir, 'test_state.csv')
        log_file = os.path.join(tmpdir, 'test_log.csv')
        
        # Create config manager
        cm = ConfigManager(config_file, state_file, log_file)
        
        # Test creating sample config
        sample_config = os.path.join(tmpdir, 'sample.csv')
        cm.create_sample_config(sample_config)
        assert os.path.exists(sample_config), "Sample config should be created"
        
        # Test loading empty config
        configs = cm.load_config()
        assert configs == [], "Empty config should return empty list"
        
        # Create a test config
        with open(config_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'pair', 'threshold_price', 
                                                    'threshold_type', 'direction', 'volume',
                                                    'trailing_offset_percent', 'enabled'])
            writer.writeheader()
            writer.writerow({
                'id': 'test1',
                'pair': 'XXBTZUSD',
                'threshold_price': '50000',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.01',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            })
        
        # Test loading config
        configs = cm.load_config()
        assert len(configs) == 1, "Should load one config"
        assert configs[0]['id'] == 'test1', "Config ID should match"
        
        # Test state management
        state = {'test1': {'id': 'test1', 'triggered': 'false', 'trigger_price': '', 
                          'trigger_time': '', 'order_id': '', 'last_checked': ''}}
        cm.save_state(state)
        assert os.path.exists(state_file), "State file should be created"
        
        loaded_state = cm.load_state()
        assert 'test1' in loaded_state, "State should be loaded"
        
        # Test logging
        cm.log('INFO', 'Test message', test_key='test_value')
        assert os.path.exists(log_file), "Log file should be created"
        
        print("✓ ConfigManager tests passed")


def test_threshold_checking():
    """Test threshold checking logic."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'log.csv')
        
        cm = ConfigManager(config_file, state_file, log_file)
        api_ro = KrakenAPI()  # No credentials needed for testing
        
        ttslo = TTSLO(cm, api_ro, kraken_api_readwrite=None, dry_run=True, verbose=False)
        
        # Test "above" threshold
        config_above = {
            'id': 'test_above',
            'threshold_price': '50000',
            'threshold_type': 'above'
        }
        
        assert ttslo.check_threshold(config_above, 51000) == True, "Should trigger when above"
        assert ttslo.check_threshold(config_above, 50000) == True, "Should trigger at threshold"
        assert ttslo.check_threshold(config_above, 49000) == False, "Should not trigger when below"
        
        # Test "below" threshold
        config_below = {
            'id': 'test_below',
            'threshold_price': '3000',
            'threshold_type': 'below'
        }
        
        assert ttslo.check_threshold(config_below, 2999) == True, "Should trigger when below"
        assert ttslo.check_threshold(config_below, 3000) == True, "Should trigger at threshold"
        assert ttslo.check_threshold(config_below, 3001) == False, "Should not trigger when above"
        
        print("✓ Threshold checking tests passed")


def test_dry_run_mode():
    """Test dry-run mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'log.csv')
        
        cm = ConfigManager(config_file, state_file, log_file)
        api_ro = Mock(spec=KrakenAPI)
        api_rw = Mock(spec=KrakenAPI)
        
        ttslo = TTSLO(cm, api_ro, kraken_api_readwrite=api_rw, dry_run=True, verbose=False)
        
        config = {
            'id': 'test1',
            'pair': 'XXBTZUSD',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0'
        }
        
        # In dry-run mode, should return dummy order ID without calling API
        order_id = ttslo.create_tsl_order(config, 50000)
        
        assert order_id == 'DRY_RUN_ORDER_ID', "Dry run should return dummy order ID"
        assert not api_rw.add_trailing_stop_loss.called, "API should not be called in dry-run"
        
        print("✓ Dry-run mode tests passed")


def test_missing_readwrite_credentials():
    """Test behavior when read-write credentials are missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'log.csv')
        
        cm = ConfigManager(config_file, state_file, log_file)
        api_ro = Mock(spec=KrakenAPI)
        
        # Create TTSLO without read-write credentials
        ttslo = TTSLO(cm, api_ro, kraken_api_readwrite=None, dry_run=False, verbose=False)
        
        config = {
            'id': 'test1',
            'pair': 'XXBTZUSD',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0'
        }
        
        # Should return None and log error
        order_id = ttslo.create_tsl_order(config, 50000)
        
        assert order_id is None, "Should return None when no read-write credentials"
        
        print("✓ Missing read-write credentials tests passed")


def test_kraken_api_signature():
    """Test Kraken API signature generation."""
    # Test with known values to ensure signature generation works
    api = KrakenAPI(api_key='test_key', api_secret='dGVzdF9zZWNyZXQ=')  # base64 of 'test_secret'
    
    urlpath = '/0/private/Balance'
    data = {'nonce': '1234567890'}
    
    # Just verify it doesn't crash
    signature = api._get_kraken_signature(urlpath, data)
    assert isinstance(signature, str), "Signature should be a string"
    assert len(signature) > 0, "Signature should not be empty"
    
    print("✓ Kraken API signature tests passed")


def run_all_tests():
    """Run all tests."""
    print("Running TTSLO tests...\n")
    
    try:
        test_config_manager()
        test_threshold_checking()
        test_dry_run_mode()
        test_missing_readwrite_credentials()
        test_kraken_api_signature()
        
        print("\n✅ All tests passed!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
