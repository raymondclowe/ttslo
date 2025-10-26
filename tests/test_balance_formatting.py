"""
Tests for balance formatting in notifications.

Tests the format_balance() function to ensure it formats balances
with appropriate decimal precision, matching the dashboard display.
"""
import pytest
from decimal import Decimal
from notifications import format_balance


class TestBalanceFormatting:
    """Test balance formatting with various decimal values."""
    
    def test_very_small_balance_8_decimals(self):
        """Very small balances (< 0.01) should show up to 8 decimals."""
        # Test cases with trailing zeros removed
        assert format_balance(Decimal('0.00123456')) == '0.00123456'
        assert format_balance(Decimal('0.0000012345')) == '0.00000123'
        assert format_balance(Decimal('0.00000001')) == '0.00000001'
        
    def test_very_small_balance_removes_trailing_zeros(self):
        """Very small balances should remove trailing zeros."""
        assert format_balance(Decimal('0.00100000')) == '0.001'
        assert format_balance(Decimal('0.00001000')) == '0.00001'
    
    def test_concern_balance_000005_not_zero(self):
        """Test @raymondclowe's concern: 0.000005 should NOT show as 0."""
        # This is the specific concern raised in PR comment
        assert format_balance(Decimal('0.000005')) == '0.000005'
        # Also test nearby values
        assert format_balance(Decimal('0.000001')) == '0.000001'
        assert format_balance(Decimal('0.00001')) == '0.00001'
        assert format_balance(Decimal('0.0000001')) == '0.0000001'
        # Only values beyond 8 decimals should show as 0
        assert format_balance(Decimal('1E-9')) == '0'
        
    def test_extremely_small_balance(self):
        """Extremely small balances (< 0.00000001) should show as 0."""
        # This is important - Python's Decimal can represent these but
        # for practical purposes in crypto trading, they're essentially 0
        assert format_balance(Decimal('0.000000001')) == '0'
        assert format_balance(Decimal('1E-9')) == '0'
        
    def test_small_balance_4_decimals(self):
        """Small balances (< 1) should show 4 decimals."""
        assert format_balance(Decimal('0.1234')) == '0.1234'
        assert format_balance(Decimal('0.5678')) == '0.5678'
        assert format_balance(Decimal('0.9999')) == '0.9999'
        
    def test_medium_balance_2_decimals(self):
        """Medium balances (< 100) should show 2 decimals."""
        assert format_balance(Decimal('1.234567')) == '1.23'
        assert format_balance(Decimal('50.5')) == '50.50'
        assert format_balance(Decimal('99.999')) == '100.00'
        
    def test_large_balance_with_separator(self):
        """Large balances (>= 100) should show 2 decimals with thousands separator."""
        assert format_balance(Decimal('100.5')) == '100.50'
        assert format_balance(Decimal('1234.567')) == '1,234.57'
        assert format_balance(Decimal('1000000.99')) == '1,000,000.99'
        
    def test_zero_balance(self):
        """Zero balance should display as '0'."""
        assert format_balance(Decimal('0')) == '0'
        assert format_balance(Decimal('0.0')) == '0'
        assert format_balance(Decimal('0.00000000')) == '0'
        
    def test_none_value(self):
        """None should return 'N/A'."""
        assert format_balance(None) == 'N/A'
        
    def test_na_string(self):
        """'N/A' string should return 'N/A'."""
        assert format_balance('N/A') == 'N/A'
        
    def test_invalid_value(self):
        """Invalid values should return 'N/A'."""
        assert format_balance('invalid') == 'N/A'
        assert format_balance('') == 'N/A'
        
    def test_float_input(self):
        """Function should handle float input."""
        assert format_balance(0.00123456) == '0.00123456'
        assert format_balance(1.234567) == '1.23'
        assert format_balance(100.5) == '100.50'
        
    def test_int_input(self):
        """Function should handle integer input."""
        assert format_balance(0) == '0'
        assert format_balance(5) == '5.00'
        assert format_balance(1000) == '1,000.00'
        
    def test_string_input(self):
        """Function should handle string input."""
        assert format_balance('0.00123456') == '0.00123456'
        assert format_balance('1.234567') == '1.23'
        assert format_balance('100.5') == '100.50'
        
    def test_negative_balance(self):
        """Function should handle negative balances (edge case)."""
        assert format_balance(Decimal('-0.00123456')) == '-0.00123456'
        assert format_balance(Decimal('-1.234567')) == '-1.23'
        assert format_balance(Decimal('-100.5')) == '-100.50'


class TestNotificationBalanceDisplay:
    """Test that notifications display balances correctly."""
    
    def test_insufficient_balance_notification_formatting(self):
        """Test that insufficient balance notifications format balance properly."""
        from notifications import NotificationManager
        
        # Create notification manager without actual config
        nm = NotificationManager('nonexistent.ini')
        nm.enabled = False  # Don't actually send notifications
        
        # Mock the notify_event to capture the message
        messages = []
        original_notify = nm.notify_event
        nm.notify_event = lambda event_type, message: messages.append(message)
        
        # Test with very small balance
        nm.notify_insufficient_balance(
            config_id='test_1',
            pair='XETHZUSD',
            direction='sell',
            volume='0.01',
            available=Decimal('0.00123456'),
            trigger_price=2500.0
        )
        
        assert len(messages) == 1
        assert 'Available Balance: 0.00123456' in messages[0]
        assert '1.23E' not in messages[0]  # Should NOT contain scientific notation
        
    def test_insufficient_balance_with_zero(self):
        """Test notification with zero balance."""
        from notifications import NotificationManager
        
        nm = NotificationManager('nonexistent.ini')
        nm.enabled = False
        
        messages = []
        nm.notify_event = lambda event_type, message: messages.append(message)
        
        nm.notify_insufficient_balance(
            config_id='test_2',
            pair='XETHZUSD',
            direction='sell',
            volume='0.01',
            available=Decimal('0'),
            trigger_price=2500.0
        )
        
        assert len(messages) == 1
        assert 'Available Balance: 0' in messages[0]
        
    def test_insufficient_balance_with_none(self):
        """Test notification with None balance."""
        from notifications import NotificationManager
        
        nm = NotificationManager('nonexistent.ini')
        nm.enabled = False
        
        messages = []
        nm.notify_event = lambda event_type, message: messages.append(message)
        
        nm.notify_insufficient_balance(
            config_id='test_3',
            pair='XETHZUSD',
            direction='sell',
            volume='0.01',
            available=None,
            trigger_price=2500.0
        )
        
        assert len(messages) == 1
        assert 'Available Balance: N/A' in messages[0]
