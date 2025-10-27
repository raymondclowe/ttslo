"""
Test to verify the fix for insufficient gap validation issue.

This test demonstrates that configs with insufficient gap now produce
WARNINGS instead of ERRORS, allowing transactions to proceed.
"""
from decimal import Decimal
from validator import ConfigValidator


class FakeKrakenAPI:
    """Mock Kraken API for testing."""
    
    def __init__(self, prices):
        """Initialize with a dict of pair -> price mappings."""
        self._prices = prices
    
    def get_current_price(self, pair):
        """Return current price for the pair."""
        return self._prices.get(pair, Decimal('0'))
    
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
        return {}


def test_issue_examples_now_allowed():
    """
    Test the exact examples from the GitHub issue.
    
    These configs were previously blocked with ERROR but should now
    produce WARNING to allow transactions.
    
    Examples from issue:
    1. dydx_usd_buy_20251027_18: threshold 0.3332, current 0.3365, gap 0.96% < trailing 2.00%
    2. ponke_usd_buy_20251027_40: threshold 0.0633, current 0.0641, gap 1.11% < trailing 2.00%
    3. ath_usd_buy_20251027_46: threshold 0.0293, current 0.0299, gap 1.97% < trailing 2.00%
    """
    # Setup API with current prices from the issue
    api = FakeKrakenAPI({
        'DYDXUSD': Decimal('0.3365'),
        'PONKEUSD': Decimal('0.0641'),
        'ATHUSD': Decimal('0.0299'),
    })
    
    validator = ConfigValidator(kraken_api=api, debug_mode=False)
    
    configs = [
        {
            'id': 'dydx_usd_buy_20251027_18',
            'pair': 'DYDXUSD',
            'threshold_price': '0.3332',  # Gap: 0.96%
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '100',
            'trailing_offset_percent': '2.00',
            'enabled': 'true',
        },
        {
            'id': 'ponke_usd_buy_20251027_40',
            'pair': 'PONKEUSD',
            'threshold_price': '0.0633',  # Gap: 1.11%
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '1000',
            'trailing_offset_percent': '2.00',
            'enabled': 'true',
        },
        {
            'id': 'ath_usd_buy_20251027_46',
            'pair': 'ATHUSD',
            'threshold_price': '0.0293',  # Gap: 1.97%
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '500',
            'trailing_offset_percent': '2.00',
            'enabled': 'true',
        },
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should be VALID - the main fix!
    assert result.is_valid(), (
        f"Validation should pass (configs should be allowed). "
        f"Errors: {result.errors}"
    )
    
    # Should have warnings (not errors) for all three configs
    assert len(result.warnings) >= 3, (
        f"Expected at least 3 warnings (one for each config). "
        f"Got {len(result.warnings)} warnings: {result.warnings}"
    )
    
    # Check that warnings are about gap issues (either insufficient or small gap)
    gap_warnings = [w for w in result.warnings if 'gap' in w['message'].lower()]
    assert len(gap_warnings) >= 3, (
        f"Expected 3 gap-related warnings. "
        f"Got {len(gap_warnings)} gap warnings from {len(result.warnings)} total warnings. "
        f"Warnings: {result.warnings}"
    )
    
    # Verify warning messages contain helpful suggestions
    for warning in gap_warnings:
        assert 'Consider' in warning['message'] or 'may trigger immediately' in warning['message'], (
            f"Warning should contain helpful suggestions. Got: {warning['message']}"
        )
    
    print("✓ Issue examples test passed - all configs now allowed with warnings")


def test_small_gap_warning_has_suggestions():
    """Test that insufficient gap warnings include actionable suggestions."""
    api = FakeKrakenAPI({'XXBTZUSD': Decimal('50000')})
    validator = ConfigValidator(kraken_api=api, debug_mode=False)
    
    configs = [
        {
            'id': 'btc_small_gap',
            'pair': 'XXBTZUSD',
            'threshold_price': '50500',  # Only 1% gap
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',  # Needs 5% gap
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should be valid with warnings
    assert result.is_valid(), "Config should be allowed"
    assert len(result.warnings) > 0, "Should have warnings"
    
    # Check warning message contains suggestions
    gap_warning = [w for w in result.warnings if 'Insufficient gap' in w['message']][0]
    message = gap_warning['message']
    
    # Should suggest at least one action
    suggestions = [
        'increase threshold price' in message,
        'reduce trailing offset' in message,
        'wait for price to move' in message,
    ]
    assert any(suggestions), f"Warning should contain suggestions. Got: {message}"
    
    print("✓ Warning suggestions test passed")


def test_gap_warnings_vs_errors_boundary():
    """
    Test the boundaries between different warning levels.
    
    - Gap < trailing_offset: WARNING (insufficient gap)
    - Gap >= trailing_offset and < 2×trailing_offset: WARNING (small gap)
    - Gap >= 2×trailing_offset: No warning
    """
    api = FakeKrakenAPI({'XXBTZUSD': Decimal('50000')})
    validator = ConfigValidator(kraken_api=api, debug_mode=False)
    
    # Test 1: Gap < trailing_offset (1% gap, 5% trailing) = Insufficient gap WARNING
    config_insufficient = [
        {
            'id': 'insufficient_gap',
            'pair': 'XXBTZUSD',
            'threshold_price': '50500',  # 1% gap
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    result = validator.validate_config_file(config_insufficient)
    assert result.is_valid(), "Insufficient gap should be WARNING, not ERROR"
    gap_warnings = [w for w in result.warnings if 'Insufficient gap' in w['message']]
    assert len(gap_warnings) == 1, "Should have insufficient gap warning"
    
    # Test 2: Gap between trailing and 2×trailing (7% gap, 5% trailing) = Small gap WARNING
    config_small = [
        {
            'id': 'small_gap',
            'pair': 'XXBTZUSD',
            'threshold_price': '53500',  # 7% gap
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    result = validator.validate_config_file(config_small)
    assert result.is_valid(), "Small gap should be WARNING, not ERROR"
    small_warnings = [w for w in result.warnings if 'Small gap' in w['message']]
    assert len(small_warnings) == 1, "Should have small gap warning"
    
    # Test 3: Gap >= 2×trailing (11% gap, 5% trailing) = No warning
    config_good = [
        {
            'id': 'good_gap',
            'pair': 'XXBTZUSD',
            'threshold_price': '55500',  # 11% gap
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    result = validator.validate_config_file(config_good)
    assert result.is_valid(), "Good gap should pass validation"
    gap_warnings = [w for w in result.warnings if 'gap' in w['message'].lower()]
    assert len(gap_warnings) == 0, "Should have no gap warnings for sufficient gap"
    
    print("✓ Boundary test passed")


if __name__ == '__main__':
    test_issue_examples_now_allowed()
    test_small_gap_warning_has_suggestions()
    test_gap_warnings_vs_errors_boundary()
    print("\n✅ All insufficient gap fix tests passed!")
