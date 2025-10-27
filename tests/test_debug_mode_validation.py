"""
Tests for debug mode validation behavior.

These tests verify that in debug mode, certain validation errors are converted
to warnings to allow live testing with small transactions.
"""
from decimal import Decimal
from validator import ConfigValidator


class FakeKrakenAPI:
    """Mock Kraken API for testing."""
    
    def __init__(self, current_price):
        self._current_price = current_price
        self._balance = {}
    
    def get_current_price(self, pair):
        """Return current price for the pair."""
        return self._current_price
    
    def get_ohlc(self, pair, interval=1440, since=None):
        """Return empty OHLC data."""
        return {}
    
    def query_open_orders(self, trades=False, userref=None):
        """Return empty open orders."""
        return {'open': {}}
    
    def query_closed_orders(self, trades=False, userref=None, start=None, end=None, ofs=None, closetime='both'):
        """Return empty closed orders."""
        return {'closed': {}}
    
    def get_balance(self):
        """Return account balance."""
        return self._balance


def test_threshold_already_met_error_in_normal_mode():
    """Test that threshold already met is an ERROR in normal mode."""
    # Current price: 50000, Threshold: 45000 (below current for 'above' threshold)
    api = FakeKrakenAPI(current_price=Decimal('50000'))
    
    validator = ConfigValidator(kraken_api=api, debug_mode=False)
    configs = [
        {
            'id': 'test_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '45000',  # Already met (current is 50000)
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should have an ERROR for threshold already met
    assert not result.is_valid(), "Expected validation to fail"
    assert len(result.errors) > 0, "Expected at least one error"
    
    # Check that the error is about threshold already met
    threshold_errors = [e for e in result.errors if 'already met' in e['message']]
    assert len(threshold_errors) >= 1, f"Expected error about threshold already met, got errors: {result.errors}"


def test_threshold_already_met_warning_in_debug_mode():
    """Test that threshold already met is a WARNING in debug mode."""
    # Current price: 50000, Threshold: 45000 (below current for 'above' threshold)
    api = FakeKrakenAPI(current_price=Decimal('50000'))
    
    validator = ConfigValidator(kraken_api=api, debug_mode=True)
    configs = [
        {
            'id': 'test_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '45000',  # Already met (current is 50000)
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should be VALID (no errors, only warnings)
    assert result.is_valid(), f"Expected validation to pass in debug mode, got errors: {result.errors}"
    
    # Should have a WARNING for threshold already met
    assert len(result.warnings) > 0, "Expected at least one warning"
    
    # Check that the warning is about threshold already met and mentions DEBUG MODE
    threshold_warnings = [w for w in result.warnings if 'already met' in w['message'] and 'DEBUG MODE' in w['message']]
    assert len(threshold_warnings) >= 1, f"Expected warning about threshold already met with DEBUG MODE tag, got warnings: {result.warnings}"


def test_insufficient_gap_warning_in_normal_mode():
    """Test that insufficient gap is a WARNING in normal mode (changed from ERROR to allow transactions)."""
    # Current price: 50000, Threshold: 50500 (1% gap), Trailing offset: 5% (needs at least 5% gap)
    api = FakeKrakenAPI(current_price=Decimal('50000'))
    
    validator = ConfigValidator(kraken_api=api, debug_mode=False)
    configs = [
        {
            'id': 'test_2',
            'pair': 'XXBTZUSD',
            'threshold_price': '50500',  # Only 1% gap
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',  # Needs at least 5% gap
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should be VALID (no errors, only warnings) - changed to allow users to transact
    assert result.is_valid(), f"Expected validation to pass (WARNING not ERROR), got errors: {result.errors}"
    assert len(result.warnings) > 0, "Expected at least one warning"
    
    # Check that the warning is about insufficient gap
    gap_warnings = [w for w in result.warnings if 'Insufficient gap' in w['message']]
    assert len(gap_warnings) >= 1, f"Expected warning about insufficient gap, got warnings: {result.warnings}"


def test_insufficient_gap_warning_in_debug_mode():
    """Test that insufficient gap is a WARNING in debug mode (same behavior as normal mode now)."""
    # Current price: 50000, Threshold: 50500 (1% gap), Trailing offset: 5% (needs at least 5% gap)
    api = FakeKrakenAPI(current_price=Decimal('50000'))
    
    validator = ConfigValidator(kraken_api=api, debug_mode=True)
    configs = [
        {
            'id': 'test_2',
            'pair': 'XXBTZUSD',
            'threshold_price': '50500',  # Only 1% gap
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',  # Needs at least 5% gap
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should be VALID (no errors, only warnings)
    assert result.is_valid(), f"Expected validation to pass in debug mode, got errors: {result.errors}"
    
    # Should have a WARNING for insufficient gap
    assert len(result.warnings) > 0, "Expected at least one warning"
    
    # Check that the warning is about insufficient gap (no longer needs DEBUG MODE tag)
    gap_warnings = [w for w in result.warnings if 'Insufficient gap' in w['message']]
    assert len(gap_warnings) >= 1, f"Expected warning about insufficient gap, got warnings: {result.warnings}"


def test_below_threshold_already_met_error_in_normal_mode():
    """Test that 'below' threshold already met is an ERROR in normal mode."""
    # Current price: 50000, Threshold: 55000 (above current for 'below' threshold)
    api = FakeKrakenAPI(current_price=Decimal('50000'))
    
    validator = ConfigValidator(kraken_api=api, debug_mode=False)
    configs = [
        {
            'id': 'test_3',
            'pair': 'XXBTZUSD',
            'threshold_price': '55000',  # Already met (current is 50000, below 55000)
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should have an ERROR for threshold already met
    assert not result.is_valid(), "Expected validation to fail"
    assert len(result.errors) > 0, "Expected at least one error"
    
    # Check that the error is about threshold already met
    threshold_errors = [e for e in result.errors if 'already met' in e['message']]
    assert len(threshold_errors) >= 1, f"Expected error about threshold already met, got errors: {result.errors}"


def test_below_threshold_already_met_warning_in_debug_mode():
    """Test that 'below' threshold already met is a WARNING in debug mode."""
    # Current price: 50000, Threshold: 55000 (above current for 'below' threshold)
    api = FakeKrakenAPI(current_price=Decimal('50000'))
    
    validator = ConfigValidator(kraken_api=api, debug_mode=True)
    configs = [
        {
            'id': 'test_3',
            'pair': 'XXBTZUSD',
            'threshold_price': '55000',  # Already met (current is 50000, below 55000)
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should be VALID (no errors, only warnings)
    assert result.is_valid(), f"Expected validation to pass in debug mode, got errors: {result.errors}"
    
    # Should have a WARNING for threshold already met
    assert len(result.warnings) > 0, "Expected at least one warning"
    
    # Check that the warning is about threshold already met and mentions DEBUG MODE
    threshold_warnings = [w for w in result.warnings if 'already met' in w['message'] and 'DEBUG MODE' in w['message']]
    assert len(threshold_warnings) >= 1, f"Expected warning about threshold already met with DEBUG MODE tag, got warnings: {result.warnings}"


def test_multiple_configs_debug_mode():
    """Test that multiple configs with issues all get warnings in debug mode."""
    # Current price: 50000
    api = FakeKrakenAPI(current_price=Decimal('50000'))
    
    validator = ConfigValidator(kraken_api=api, debug_mode=True)
    configs = [
        {
            'id': 'test_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '45000',  # Already met
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        },
        {
            'id': 'test_2',
            'pair': 'XXBTZUSD',
            'threshold_price': '50500',  # Insufficient gap
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        },
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should be VALID (no errors, only warnings)
    assert result.is_valid(), f"Expected validation to pass in debug mode, got errors: {result.errors}"
    
    # Should have warnings for both configs
    assert len(result.warnings) >= 2, f"Expected at least 2 warnings, got: {len(result.warnings)}"
    
    # First config (threshold already met) should have DEBUG MODE tag in debug mode
    already_met_warnings = [w for w in result.warnings if 'already met' in w['message']]
    assert len(already_met_warnings) >= 1, "Expected warning about threshold already met"
    assert 'DEBUG MODE' in already_met_warnings[0]['message'], "Threshold already met should have DEBUG MODE tag in debug mode"
    
    # Second config (insufficient gap) should have warning (no DEBUG MODE tag anymore)
    gap_warnings = [w for w in result.warnings if 'Insufficient gap' in w['message']]
    assert len(gap_warnings) >= 1, "Expected warning about insufficient gap"


if __name__ == '__main__':
    test_threshold_already_met_error_in_normal_mode()
    print("✓ test_threshold_already_met_error_in_normal_mode passed")
    
    test_threshold_already_met_warning_in_debug_mode()
    print("✓ test_threshold_already_met_warning_in_debug_mode passed")
    
    test_insufficient_gap_warning_in_normal_mode()
    print("✓ test_insufficient_gap_warning_in_normal_mode passed")
    
    test_insufficient_gap_warning_in_debug_mode()
    print("✓ test_insufficient_gap_warning_in_debug_mode passed")
    
    test_below_threshold_already_met_error_in_normal_mode()
    print("✓ test_below_threshold_already_met_error_in_normal_mode passed")
    
    test_below_threshold_already_met_warning_in_debug_mode()
    print("✓ test_below_threshold_already_met_warning_in_debug_mode passed")
    
    test_multiple_configs_debug_mode()
    print("✓ test_multiple_configs_debug_mode passed")
    
    print("\nAll tests passed!")
