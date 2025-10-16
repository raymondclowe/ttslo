#!/usr/bin/env python3
"""
Basic tests for TTSLO functionality.
"""
import os
import sys
import tempfile
import csv
import json
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ttslo import TTSLO
from config import ConfigManager
from kraken_api import KrakenAPI
from validator import ConfigValidator, format_validation_result


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
    nonce = '1234567890'
    data = json.dumps({'nonce': nonce})
    
    # Just verify it doesn't crash
    signature = api._get_kraken_signature(urlpath, data, nonce)
    assert isinstance(signature, str), "Signature should be a string"
    assert len(signature) > 0, "Signature should not be empty"
    
    print("✓ Kraken API signature tests passed")


def test_config_validator():
    """Test configuration validation."""
    validator = ConfigValidator()
    
    # Test valid config
    valid_configs = [
        {
            'id': 'test1',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        }
    ]
    
    result = validator.validate_config_file(valid_configs)
    assert result.is_valid(), "Valid config should pass validation"
    assert len(result.errors) == 0, "Valid config should have no errors"
    
    # Test invalid threshold price
    invalid_configs = [
        {
            'id': 'test2',
            'pair': 'XXBTZUSD',
            'threshold_price': 'not_a_number',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        }
    ]
    
    result = validator.validate_config_file(invalid_configs)
    assert not result.is_valid(), "Invalid config should fail validation"
    assert len(result.errors) > 0, "Invalid config should have errors"
    
    # Test missing required field
    missing_field_configs = [
        {
            'id': 'test3',
            'pair': 'XXBTZUSD',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        }
    ]
    
    result = validator.validate_config_file(missing_field_configs)
    assert not result.is_valid(), "Config with missing field should fail"
    
    # Test warnings (unusual logic)
    warning_configs = [
        {
            'id': 'test4',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'buy',  # Unusual: buy when price goes up
            'volume': '0.1',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        }
    ]
    
    result = validator.validate_config_file(warning_configs)
    assert result.is_valid(), "Config with warnings should still be valid"
    assert result.has_warnings(), "Should have warnings for unusual logic"
    
    # Test market price validation with mock API
    mock_api = Mock(spec=KrakenAPI)
    mock_api.get_current_price.return_value = 60000.0  # Current BTC price
    
    validator_with_api = ConfigValidator(kraken_api=mock_api)
    
    # Test threshold already met (error)
    already_met_configs = [
        {
            'id': 'test5',
            'pair': 'XXBTZUSD',
            'threshold_price': '55000',  # Below current price for "above" threshold
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        }
    ]
    
    result = validator_with_api.validate_config_file(already_met_configs)
    assert not result.is_valid(), "Threshold already met should be an error"
    
    # Test insufficient gap (error)
    insufficient_gap_configs = [
        {
            'id': 'test6',
            'pair': 'XXBTZUSD',
            'threshold_price': '61000',  # Only 1.67% gap, but 5% trailing offset
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        }
    ]
    
    result = validator_with_api.validate_config_file(insufficient_gap_configs)
    assert not result.is_valid(), "Insufficient gap should be an error"
    
    print("✓ Config validator tests passed")


def test_fail_safe_order_creation():
    """Test that order creation fails safely with invalid inputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'log.csv')
        
        cm = ConfigManager(config_file, state_file, log_file)
        api_ro = Mock(spec=KrakenAPI)
        api_rw = Mock(spec=KrakenAPI)
        
        # Mock successful API response
        api_rw.add_trailing_stop_loss.return_value = {'txid': ['ORDER123']}
        
        ttslo = TTSLO(cm, api_ro, kraken_api_readwrite=api_rw, dry_run=False, verbose=False)
        
        # Test 1: Missing config ID - should return None
        config_no_id = {
            'pair': 'XXBTZUSD',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0'
        }
        result = ttslo.create_tsl_order(config_no_id, 50000)
        assert result is None, "Should return None when config_id is missing"
        assert not api_rw.add_trailing_stop_loss.called, "API should not be called"
        
        # Test 2: Missing pair - should return None
        api_rw.reset_mock()
        config_no_pair = {
            'id': 'test1',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0'
        }
        result = ttslo.create_tsl_order(config_no_pair, 50000)
        assert result is None, "Should return None when pair is missing"
        assert not api_rw.add_trailing_stop_loss.called, "API should not be called"
        
        # Test 3: Invalid trailing offset - should return None
        api_rw.reset_mock()
        config_invalid_offset = {
            'id': 'test1',
            'pair': 'XXBTZUSD',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': 'invalid'
        }
        result = ttslo.create_tsl_order(config_invalid_offset, 50000)
        assert result is None, "Should return None when trailing_offset is invalid"
        assert not api_rw.add_trailing_stop_loss.called, "API should not be called"
        
        # Test 4: Negative trailing offset - should return None
        api_rw.reset_mock()
        config_negative_offset = {
            'id': 'test1',
            'pair': 'XXBTZUSD',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '-5.0'
        }
        result = ttslo.create_tsl_order(config_negative_offset, 50000)
        assert result is None, "Should return None when trailing_offset is negative"
        assert not api_rw.add_trailing_stop_loss.called, "API should not be called"
        
        # Test 5: None trigger price - should return None
        api_rw.reset_mock()
        config_valid = {
            'id': 'test1',
            'pair': 'XXBTZUSD',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0'
        }
        result = ttslo.create_tsl_order(config_valid, None)
        assert result is None, "Should return None when trigger_price is None"
        assert not api_rw.add_trailing_stop_loss.called, "API should not be called"
        
        # Test 6: Invalid trigger price - should return None
        api_rw.reset_mock()
        result = ttslo.create_tsl_order(config_valid, 'invalid')
        assert result is None, "Should return None when trigger_price is invalid"
        assert not api_rw.add_trailing_stop_loss.called, "API should not be called"
        
        # Test 7: API exception - should return None
        api_rw.reset_mock()
        api_rw.add_trailing_stop_loss.side_effect = Exception("API Error")
        result = ttslo.create_tsl_order(config_valid, 50000)
        assert result is None, "Should return None when API raises exception"
        
        # Test 8: Valid config - should create order
        api_rw.reset_mock()
        api_rw.add_trailing_stop_loss.side_effect = None
        api_rw.add_trailing_stop_loss.return_value = {'txid': ['ORDER123']}
        result = ttslo.create_tsl_order(config_valid, 50000)
        assert result == 'ORDER123', "Should return order ID when successful"
        assert api_rw.add_trailing_stop_loss.called, "API should be called for valid config"
        
        print("✓ Fail-safe order creation tests passed")


def test_fail_safe_threshold_checking():
    """Test that threshold checking fails safely with invalid inputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'log.csv')
        
        cm = ConfigManager(config_file, state_file, log_file)
        api_ro = Mock(spec=KrakenAPI)
        
        ttslo = TTSLO(cm, api_ro, kraken_api_readwrite=None, dry_run=True, verbose=False)
        
        # Test 1: None current_price - should return False
        config = {
            'id': 'test1',
            'threshold_price': '50000',
            'threshold_type': 'above'
        }
        result = ttslo.check_threshold(config, None)
        assert result is False, "Should return False when current_price is None"
        
        # Test 2: Invalid current_price - should return False
        result = ttslo.check_threshold(config, 'invalid')
        assert result is False, "Should return False when current_price is invalid"
        
        # Test 3: Negative current_price - should return False
        result = ttslo.check_threshold(config, -100)
        assert result is False, "Should return False when current_price is negative"
        
        # Test 4: Missing threshold_price - should return False
        config_no_threshold = {
            'id': 'test1',
            'threshold_type': 'above'
        }
        result = ttslo.check_threshold(config_no_threshold, 50000)
        assert result is False, "Should return False when threshold_price is missing"
        
        # Test 5: Invalid threshold_type - should return False
        config_invalid_type = {
            'id': 'test1',
            'threshold_price': '50000',
            'threshold_type': 'invalid'
        }
        result = ttslo.check_threshold(config_invalid_type, 50000)
        assert result is False, "Should return False when threshold_type is invalid"
        
        # Test 6: Not a dict config - should return False
        result = ttslo.check_threshold("not a dict", 50000)
        assert result is False, "Should return False when config is not a dict"
        
        # Test 7: Valid above threshold met - should return True
        result = ttslo.check_threshold(config, 51000)
        assert result is True, "Should return True when above threshold is met"
        
        # Test 8: Valid above threshold not met - should return False
        result = ttslo.check_threshold(config, 49000)
        assert result is False, "Should return False when above threshold is not met"
        
        print("✓ Fail-safe threshold checking tests passed")


def test_kraken_api_parameter_validation():
    """Test that Kraken API validates parameters before making calls."""
    api = KrakenAPI(api_key='test_key', api_secret='dGVzdF9zZWNyZXQ=')
    
    # Test add_trailing_stop_loss parameter validation
    
    # Test 1: Missing pair - should raise ValueError
    try:
        api.add_trailing_stop_loss(None, 'sell', '0.01', 5.0)
        assert False, "Should raise ValueError for None pair"
    except ValueError as e:
        assert 'pair' in str(e).lower(), "Error should mention pair"
    
    # Test 2: Missing direction - should raise ValueError
    try:
        api.add_trailing_stop_loss('XXBTZUSD', None, '0.01', 5.0)
        assert False, "Should raise ValueError for None direction"
    except ValueError as e:
        assert 'direction' in str(e).lower(), "Error should mention direction"
    
    # Test 3: Invalid direction - should raise ValueError
    try:
        api.add_trailing_stop_loss('XXBTZUSD', 'invalid', '0.01', 5.0)
        assert False, "Should raise ValueError for invalid direction"
    except ValueError as e:
        assert 'direction' in str(e).lower(), "Error should mention direction"
    
    # Test 4: None volume - should raise ValueError
    try:
        api.add_trailing_stop_loss('XXBTZUSD', 'sell', None, 5.0)
        assert False, "Should raise ValueError for None volume"
    except ValueError as e:
        assert 'volume' in str(e).lower(), "Error should mention volume"
    
    # Test 5: Negative volume - should raise ValueError
    try:
        api.add_trailing_stop_loss('XXBTZUSD', 'sell', '-0.01', 5.0)
        assert False, "Should raise ValueError for negative volume"
    except ValueError as e:
        assert 'volume' in str(e).lower(), "Error should mention volume"
    
    # Test 6: None trailing_offset - should raise ValueError
    try:
        api.add_trailing_stop_loss('XXBTZUSD', 'sell', '0.01', None)
        assert False, "Should raise ValueError for None trailing_offset"
    except ValueError as e:
        assert 'trailing_offset' in str(e).lower(), "Error should mention trailing_offset"
    
    # Test 7: Negative trailing_offset - should raise ValueError
    try:
        api.add_trailing_stop_loss('XXBTZUSD', 'sell', '0.01', -5.0)
        assert False, "Should raise ValueError for negative trailing_offset"
    except ValueError as e:
        assert 'trailing_offset' in str(e).lower(), "Error should mention trailing_offset"
    
    # Test get_current_price parameter validation
    
    # Test 8: None pair - should raise ValueError
    try:
        api.get_current_price(None)
        assert False, "Should raise ValueError for None pair"
    except ValueError as e:
        assert 'pair' in str(e).lower(), "Error should mention pair"
    
    # Test 9: Empty pair - should raise ValueError
    try:
        api.get_current_price('')
        assert False, "Should raise ValueError for empty pair"
    except ValueError as e:
        assert 'pair' in str(e).lower(), "Error should mention pair"
    
    print("✓ Kraken API parameter validation tests passed")


def test_activated_on_state_recording():
    """Test that activated_on is recorded in state when rule triggers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'test_config.csv')
        state_file = os.path.join(tmpdir, 'test_state.csv')
        log_file = os.path.join(tmpdir, 'test_log.csv')
        
        # Mock Kraken API
        api_ro = Mock(spec=KrakenAPI)
        api_rw = Mock(spec=KrakenAPI)
        api_ro.get_current_price.return_value = 51000  # Above threshold
        api_rw.add_trailing_stop_loss.return_value = {'txid': ['ORDER123']}
        
        # Create ConfigManager and TTSLO instance
        cm = ConfigManager(config_file, state_file, log_file)
        ttslo = TTSLO(
            config_manager=cm,
            kraken_api_readonly=api_ro,
            kraken_api_readwrite=api_rw,
            dry_run=False,
            verbose=False
        )
        
        # Load state (empty initially)
        ttslo.load_state()
        
        # Create a test config
        config = {
            'id': 'test1',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        }
        
        # Process config (should trigger and create order)
        ttslo.process_config(config)
        
        # Check that activated_on was recorded in state
        assert 'test1' in ttslo.state, "Config should be in state"
        assert ttslo.state['test1'].get('triggered') == 'true', "Config should be triggered"
        assert ttslo.state['test1'].get('activated_on'), "activated_on should be recorded"
        
        # Verify activated_on is a valid timestamp
        activated_on = ttslo.state['test1'].get('activated_on')
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(activated_on)
            assert dt is not None, "activated_on should be a valid datetime"
        except (ValueError, TypeError):
            assert False, f"activated_on '{activated_on}' should be a valid ISO format datetime"
        
        # Save state and verify it persists
        ttslo.save_state()
        
        # Load state again and verify activated_on is still there
        loaded_state = cm.load_state()
        assert 'test1' in loaded_state, "Config should be in loaded state"
        assert loaded_state['test1'].get('activated_on') == activated_on, "activated_on should persist"
        
        print("✓ activated_on state recording tests passed")


def run_all_tests():
    """Run all tests."""
    print("Running TTSLO tests...\n")
    
    try:
        test_config_manager()
        test_threshold_checking()
        test_dry_run_mode()
        test_missing_readwrite_credentials()
        test_kraken_api_signature()
        test_config_validator()
        test_fail_safe_order_creation()
        test_fail_safe_threshold_checking()
        test_kraken_api_parameter_validation()
        test_activated_on_state_recording()
        
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
