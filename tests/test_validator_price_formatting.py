"""
Tests for validator price formatting improvements.

This ensures that very small cryptocurrency prices are displayed with
appropriate decimal places in log messages.
"""
from decimal import Decimal
from validator import ConfigValidator


def test_format_decimal_very_small_prices():
    """Test formatting of very small prices (< 0.01) with up to 8 decimals."""
    validator = ConfigValidator()
    
    # Very small prices from the issue
    assert validator._format_decimal(Decimal('0.00000768')) == '0.00000768'
    assert validator._format_decimal(Decimal('0.00000694')) == '0.00000694'
    assert validator._format_decimal(Decimal('0.00187083')) == '0.00187083'
    
    # Edge cases
    assert validator._format_decimal(Decimal('0.00000001')) == '0.00000001'
    assert validator._format_decimal(Decimal('0.009')) == '0.009'
    assert validator._format_decimal(Decimal('0.00999999')) == '0.00999999'


def test_format_decimal_small_prices():
    """Test formatting of small prices (0.01 to 1.0) with 4 decimals."""
    validator = ConfigValidator()
    
    assert validator._format_decimal(Decimal('0.17')) == '0.1700'
    assert validator._format_decimal(Decimal('0.5678')) == '0.5678'
    assert validator._format_decimal(Decimal('0.01')) == '0.0100'
    assert validator._format_decimal(Decimal('0.9999')) == '0.9999'


def test_format_decimal_medium_prices():
    """Test formatting of medium prices (1.0 to 100.0) with 2 decimals."""
    validator = ConfigValidator()
    
    assert validator._format_decimal(Decimal('6.48')) == '6.48'
    assert validator._format_decimal(Decimal('2.67')) == '2.67'
    assert validator._format_decimal(Decimal('12.345')) == '12.34'
    assert validator._format_decimal(Decimal('99.999')) == '99.99'


def test_format_decimal_large_prices():
    """Test formatting of large prices (>= 100) with 2 decimals."""
    validator = ConfigValidator()
    
    assert validator._format_decimal(Decimal('1234.567')) == '1234.56'
    assert validator._format_decimal(Decimal('50000')) == '50000.00'
    assert validator._format_decimal(Decimal('100.00')) == '100.00'


def test_format_decimal_trailing_zeros_removed():
    """Test that trailing zeros are removed for very small values."""
    validator = ConfigValidator()
    
    # Very small values should have trailing zeros removed
    assert validator._format_decimal(Decimal('0.00100000')) == '0.001'
    assert validator._format_decimal(Decimal('0.00000100')) == '0.000001'
    
    # Larger values keep their decimal places
    assert validator._format_decimal(Decimal('1.50000000')) == '1.50'
    assert validator._format_decimal(Decimal('100.50000000')) == '100.50'


def test_format_decimal_zero():
    """Test formatting of zero."""
    validator = ConfigValidator()
    
    assert validator._format_decimal(Decimal('0.00')) == '0'
    assert validator._format_decimal(Decimal('0.00000000')) == '0'
    assert validator._format_decimal(Decimal('0')) == '0'


def test_format_decimal_explicit_places():
    """Test formatting with explicit decimal places (percentages)."""
    validator = ConfigValidator()
    
    # When places is specified, use that many places
    assert validator._format_decimal(Decimal('3.49'), 2) == '3.49'
    assert validator._format_decimal(Decimal('2.00'), 2) == '2.00'
    assert validator._format_decimal(Decimal('0.00000768'), 2) == '0.00'
    assert validator._format_decimal(Decimal('0.00000768'), 8) == '0.00000768'
    
    # Edge case: more places than value has
    assert validator._format_decimal(Decimal('5'), 4) == '5.0000'


def test_format_decimal_negative_values():
    """Test formatting of negative values."""
    validator = ConfigValidator()
    
    # Negative very small
    assert validator._format_decimal(Decimal('-0.00000768')) == '-0.00000768'
    
    # Negative small
    assert validator._format_decimal(Decimal('-0.17')) == '-0.1700'
    
    # Negative medium
    assert validator._format_decimal(Decimal('-6.48')) == '-6.48'
    
    # Negative large
    assert validator._format_decimal(Decimal('-1234.56')) == '-1234.56'


def test_price_formatting_in_warning_messages():
    """Test that prices in warning messages are properly formatted."""
    from validator import ValidationResult
    
    validator = ConfigValidator()
    result = ValidationResult()
    
    # Create a mock config with very small price
    config = {
        'id': 'pepe_test',
        'pair': 'PEPEUSDT',
        'threshold_price': '0.00000768',
        'threshold_type': 'below',
        'direction': 'sell',
        'volume': '1000000',
        'trailing_offset_percent': '2.0',
        'enabled': 'true'
    }
    
    # Validate the threshold price field
    validator._validate_threshold_price(config, 'pepe_test', result)
    
    # Should have a warning about very small price
    assert len(result.warnings) == 1
    warning = result.warnings[0]
    
    # The warning message should contain the properly formatted price
    assert '0.00000768' in warning['message']
    # Should NOT show as 0.00
    assert warning['message'].count('0.00') == 0 or '0.00000768' in warning['message']


def test_gap_warning_formatting():
    """Test that gap warnings show prices with appropriate decimals."""
    from unittest.mock import MagicMock
    
    validator = ConfigValidator()
    # Mock the Kraken API to return a current price
    validator.kraken_api = MagicMock()
    validator.kraken_api.get_current_price.return_value = Decimal('0.00000750')
    
    config = {
        'id': 'pepe_sell',
        'pair': 'PEPEUSDT',
        'threshold_price': '0.00000768',
        'threshold_type': 'above',
        'direction': 'sell',
        'volume': '1000000',
        'trailing_offset_percent': '2.0',
        'enabled': 'true'
    }
    
    from validator import ValidationResult
    result = ValidationResult()
    
    # This should trigger validation logic
    configs = [config]
    result = validator.validate_config_file(configs)
    
    # Check that any warnings about gaps contain properly formatted prices
    for warning in result.warnings:
        if 'gap' in warning['message'].lower():
            # Should contain the actual price values, not 0.00
            message = warning['message']
            # Either it contains the proper small numbers or it doesn't mention threshold/current price
            if 'threshold' in message.lower() and 'current price' in message.lower():
                # Should show proper decimals
                assert '0.000007' in message or '0.00000' in message
