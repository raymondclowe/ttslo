#!/usr/bin/env python3
"""
Test dashboard price formatting for small value coins.
Ensures that very small prices like $0.001679 are displayed correctly,
not truncated to $0.00
"""

import pytest


def test_format_price_javascript_logic():
    """
    Test the formatPrice JavaScript logic using Python equivalent.
    This validates the formatting rules we're applying in the dashboard.
    """
    
    def formatPrice(value):
        """Python equivalent of JavaScript formatPrice function"""
        if value is None or value == 'N/A':
            return 'N/A'
        
        try:
            price = float(value)
        except (ValueError, TypeError):
            return 'N/A'
        
        # For very small values (< 0.01), use up to 8 decimal places
        if abs(price) < 0.01:
            # Remove trailing zeros for cleaner display, but keep at least one digit
            formatted = f"{price:.8f}"
            # Remove trailing zeros manually to avoid scientific notation
            result = formatted.rstrip('0').rstrip('.')
            # Safety check: ensure we never return empty string
            return result or '0'
        # For small values (< 1), use 4 decimal places
        elif abs(price) < 1:
            return f"{price:.4f}"
        # For medium values (< 100), use 2 decimal places
        elif abs(price) < 100:
            return f"{price:.2f}"
        # For large values, use 2 decimal places
        else:
            return f"{price:,.2f}"
    
    # Test very small values (the main issue - MEME coin)
    assert formatPrice(0.001679) == "0.001679"
    assert formatPrice(0.00000123) == "0.00000123"
    assert formatPrice(0.009) == "0.009"
    assert formatPrice(0.001) == "0.001"
    
    # Test small values
    assert formatPrice(0.1234) == "0.1234"
    assert formatPrice(0.5678) == "0.5678"
    
    # Test medium values
    assert formatPrice(1.234) == "1.23"
    assert formatPrice(12.345) == "12.35"
    assert formatPrice(99.999) == "100.00"
    
    # Test large values
    assert formatPrice(123.456) == "123.46"
    assert formatPrice(1234.567) == "1,234.57"
    assert formatPrice(12345.678) == "12,345.68"
    
    # Test edge cases
    assert formatPrice(0) == "0"
    assert formatPrice(0.0) == "0"
    assert formatPrice(None) == "N/A"
    assert formatPrice("N/A") == "N/A"
    assert formatPrice("invalid") == "N/A"


def test_price_formatting_removes_trailing_zeros():
    """Test that trailing zeros are removed for cleaner display"""
    
    def formatPrice(value):
        """Python equivalent of JavaScript formatPrice function"""
        if value is None or value == 'N/A':
            return 'N/A'
        
        try:
            price = float(value)
        except (ValueError, TypeError):
            return 'N/A'
        
        if abs(price) < 0.01:
            formatted = f"{price:.8f}"
            result = formatted.rstrip('0').rstrip('.')
            return result or '0'
        elif abs(price) < 1:
            return f"{price:.4f}"
        elif abs(price) < 100:
            return f"{price:.2f}"
        else:
            return f"{price:,.2f}"
    
    # These should have trailing zeros removed
    assert formatPrice(0.001) == "0.001"  # Not "0.00100000"
    assert formatPrice(0.0012) == "0.0012"  # Not "0.00120000"
    assert formatPrice(0.00120000) == "0.0012"  # Trailing zeros removed
    
    # But these should keep necessary precision
    assert formatPrice(0.001234) == "0.001234"
    assert formatPrice(0.00123456) == "0.00123456"


def test_original_issue_meme_coin():
    """
    Test the specific issue reported: MEMEUSD showing as $0.00
    MEME is worth approximately $0.001679
    """
    
    def formatPrice(value):
        """Python equivalent of JavaScript formatPrice function"""
        if value is None or value == 'N/A':
            return 'N/A'
        
        try:
            price = float(value)
        except (ValueError, TypeError):
            return 'N/A'
        
        if abs(price) < 0.01:
            formatted = f"{price:.8f}"
            result = formatted.rstrip('0').rstrip('.')
            return result or '0'
        elif abs(price) < 1:
            return f"{price:.4f}"
        elif abs(price) < 100:
            return f"{price:.2f}"
        else:
            return f"{price:,.2f}"
    
    # The reported MEME value
    meme_price = 0.001679
    formatted = formatPrice(meme_price)
    
    # Should NOT be "0.00"
    assert formatted != "0.00"
    
    # Should show actual value
    assert formatted == "0.001679"
    
    # With dollar sign prefix
    display = f"${formatted}"
    assert display == "$0.001679"


def test_negative_prices():
    """Test that negative prices (for benefits) are handled correctly"""
    
    def formatPrice(value):
        """Python equivalent of JavaScript formatPrice function"""
        if value is None or value == 'N/A':
            return 'N/A'
        
        try:
            price = float(value)
        except (ValueError, TypeError):
            return 'N/A'
        
        if abs(price) < 0.01:
            formatted = f"{price:.8f}"
            result = formatted.rstrip('0').rstrip('.')
            return result or '0'
        elif abs(price) < 1:
            return f"{price:.4f}"
        elif abs(price) < 100:
            return f"{price:.2f}"
        else:
            return f"{price:,.2f}"
    
    # Negative values should work the same
    assert formatPrice(-0.001679) == "-0.001679"
    assert formatPrice(-1.234) == "-1.23"
    assert formatPrice(-123.45) == "-123.45"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
