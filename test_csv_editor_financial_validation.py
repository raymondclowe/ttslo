#!/usr/bin/env python3
"""
Tests for CSV editor financial validation.

This module tests the CSV editor's integration with financial responsibility validation.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from csv_editor import EditCellScreen


class TestCSVEditorFinancialValidation:
    """Test financial validation in CSV editor."""
    
    def test_threshold_type_change_to_above_with_buy_invalid(self):
        """Test changing threshold_type to 'above' with buy direction is invalid."""
        row_data = {
            'pair': 'XXBTZUSD',
            'threshold_type': 'below',
            'direction': 'buy'
        }
        
        screen = EditCellScreen(current_value="below", column_name="threshold_type", row_data=row_data)
        
        # Try to change to 'above' (which would create buy high scenario)
        is_valid, message = screen.validate_value("above")
        
        assert is_valid is False, "Changing to 'above' with buy should be invalid"
        assert "Buying HIGH" in message
        
    def test_threshold_type_change_to_below_with_sell_invalid(self):
        """Test changing threshold_type to 'below' with sell direction is invalid."""
        row_data = {
            'pair': 'ETHUSDT',
            'threshold_type': 'above',
            'direction': 'sell'
        }
        
        screen = EditCellScreen(current_value="above", column_name="threshold_type", row_data=row_data)
        
        # Try to change to 'below' (which would create sell low scenario)
        is_valid, message = screen.validate_value("below")
        
        assert is_valid is False, "Changing to 'below' with sell should be invalid"
        assert "Selling LOW" in message
        
    def test_direction_change_to_buy_with_above_invalid(self):
        """Test changing direction to 'buy' with above threshold is invalid."""
        row_data = {
            'pair': 'XXBTZUSD',
            'threshold_type': 'above',
            'direction': 'sell'
        }
        
        screen = EditCellScreen(current_value="sell", column_name="direction", row_data=row_data)
        
        # Try to change to 'buy' (which would create buy high scenario)
        is_valid, message = screen.validate_value("buy")
        
        assert is_valid is False, "Changing to 'buy' with above threshold should be invalid"
        assert "Buying HIGH" in message
        
    def test_direction_change_to_sell_with_below_invalid(self):
        """Test changing direction to 'sell' with below threshold is invalid."""
        row_data = {
            'pair': 'ETHUSDT',
            'threshold_type': 'below',
            'direction': 'buy'
        }
        
        screen = EditCellScreen(current_value="buy", column_name="direction", row_data=row_data)
        
        # Try to change to 'sell' (which would create sell low scenario)
        is_valid, message = screen.validate_value("sell")
        
        assert is_valid is False, "Changing to 'sell' with below threshold should be invalid"
        assert "Selling LOW" in message
        
    def test_valid_threshold_type_change(self):
        """Test that valid threshold_type changes are allowed."""
        row_data = {
            'pair': 'XXBTZUSD',
            'threshold_type': 'above',
            'direction': 'sell'
        }
        
        screen = EditCellScreen(current_value="above", column_name="threshold_type", row_data=row_data)
        
        # Change to 'below' should still be valid if we're selling
        # (though it would trigger the sell low error, but we're just changing threshold_type)
        # Actually, let's test the opposite - staying with a valid combination
        is_valid, message = screen.validate_value("above")
        
        assert is_valid is True, "Keeping 'above' with sell should be valid"
        
    def test_valid_direction_change(self):
        """Test that valid direction changes are allowed."""
        row_data = {
            'pair': 'XXBTZUSD',
            'threshold_type': 'below',
            'direction': 'buy'
        }
        
        screen = EditCellScreen(current_value="buy", column_name="direction", row_data=row_data)
        
        # Keeping buy with below is valid (buy low)
        is_valid, message = screen.validate_value("buy")
        
        assert is_valid is True, "Keeping 'buy' with below should be valid"
        
    def test_non_stablecoin_pair_not_validated(self):
        """Test that non-stablecoin pairs are not subject to validation."""
        row_data = {
            'pair': 'SOLETH',
            'threshold_type': 'above',
            'direction': 'buy'
        }
        
        screen = EditCellScreen(current_value="buy", column_name="direction", row_data=row_data)
        
        # Should be valid for exotic pairs
        is_valid, message = screen.validate_value("buy")
        
        assert is_valid is True, "Non-stablecoin pairs should not be validated"
        
    def test_btc_pair_validated(self):
        """Test that BTC pairs are validated (BTC treated as stablecoin)."""
        row_data = {
            'pair': 'XETHXXBT',
            'threshold_type': 'above',
            'direction': 'buy'
        }
        
        screen = EditCellScreen(current_value="buy", column_name="direction", row_data=row_data)
        
        # Should be invalid - buying ETH high with BTC
        is_valid, message = screen.validate_value("buy")
        
        assert is_valid is False, "BTC pairs should be validated"
        assert "Buying HIGH" in message
        
    def test_incomplete_data_no_validation(self):
        """Test that incomplete row data doesn't trigger validation errors."""
        row_data = {
            'pair': 'XXBTZUSD',
            # Missing threshold_type and direction
        }
        
        screen = EditCellScreen(current_value="buy", column_name="direction", row_data=row_data)
        
        # Should be valid because we can't validate without complete data
        is_valid, message = screen.validate_value("buy")
        
        assert is_valid is True, "Incomplete data should not trigger validation"


def run_all_tests():
    """Run all tests."""
    print("Running CSV editor financial validation tests...\n")
    
    try:
        test = TestCSVEditorFinancialValidation()
        
        test.test_threshold_type_change_to_above_with_buy_invalid()
        print("✓ test_threshold_type_change_to_above_with_buy_invalid passed")
        
        test.test_threshold_type_change_to_below_with_sell_invalid()
        print("✓ test_threshold_type_change_to_below_with_sell_invalid passed")
        
        test.test_direction_change_to_buy_with_above_invalid()
        print("✓ test_direction_change_to_buy_with_above_invalid passed")
        
        test.test_direction_change_to_sell_with_below_invalid()
        print("✓ test_direction_change_to_sell_with_below_invalid passed")
        
        test.test_valid_threshold_type_change()
        print("✓ test_valid_threshold_type_change passed")
        
        test.test_valid_direction_change()
        print("✓ test_valid_direction_change passed")
        
        test.test_non_stablecoin_pair_not_validated()
        print("✓ test_non_stablecoin_pair_not_validated passed")
        
        test.test_btc_pair_validated()
        print("✓ test_btc_pair_validated passed")
        
        test.test_incomplete_data_no_validation()
        print("✓ test_incomplete_data_no_validation passed")
        
        print("\n✅ All CSV editor financial validation tests passed!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
