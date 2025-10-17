#!/usr/bin/env python3
"""
Tests for the CSV Editor TUI.
"""
import os
import sys
import tempfile
import csv
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from csv_editor import CSVEditor


def test_csv_editor_initialization():
    """Test that CSV editor can be initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create a test CSV file
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'value'])
            writer.writerow(['1', 'test1', '100'])
            writer.writerow(['2', 'test2', '200'])
        
        # Initialize the editor (don't run it)
        editor = CSVEditor(filename=test_file)
        
        assert editor.filename == Path(test_file), "Filename should be set"
        assert editor.data == [], "Data should be empty before loading"
        assert editor.modified == False, "Modified flag should be False"
        
        print("✓ CSV Editor initialization test passed")


def test_csv_reading():
    """Test that CSV files can be read correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create a test CSV file
        test_data = [
            ['id', 'pair', 'threshold_price', 'enabled'],
            ['btc_1', 'XXBTZUSD', '50000', 'true'],
            ['eth_1', 'XETHZUSD', '3000', 'true'],
        ]
        
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(test_data)
        
        # Read the file with the editor
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            data = list(reader)
        
        assert len(data) == 3, "Should have 3 rows"
        assert data[0] == test_data[0], "Headers should match"
        assert data[1] == test_data[1], "First data row should match"
        assert data[2] == test_data[2], "Second data row should match"
        
        print("✓ CSV reading test passed")


def test_csv_writing():
    """Test that CSV files can be written correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create test data
        test_data = [
            ['id', 'pair', 'threshold_price', 'enabled'],
            ['btc_1', 'XXBTZUSD', '50000', 'true'],
            ['eth_1', 'XETHZUSD', '3000', 'false'],
        ]
        
        # Write the CSV file
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(test_data)
        
        # Read it back
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            data = list(reader)
        
        assert data == test_data, "Written data should match read data"
        
        print("✓ CSV writing test passed")


def test_nonexistent_file():
    """Test handling of non-existent files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'nonexistent.csv')
        
        # Initialize editor with non-existent file
        editor = CSVEditor(filename=test_file)
        
        assert editor.filename == Path(test_file), "Filename should be set"
        assert not editor.filename.exists(), "File should not exist"
        
        print("✓ Non-existent file test passed")


def test_volume_formatting():
    """Test that volume values are formatted with 8 decimal places."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create a test CSV file with various volume formats
        test_data = [
            ['id', 'pair', 'volume', 'enabled'],
            ['test1', 'XXBTZUSD', '0.01', 'true'],
            ['test2', 'XETHZUSD', '0.1', 'true'],
            ['test3', 'XXBTZUSD', '0.00123456', 'true'],
            ['test4', 'XXBTZUSD', '1.23456789', 'true'],
        ]
        
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(test_data)
        
        # Read the file back
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            data = list(reader)
        
        # Verify data was written correctly
        assert len(data) == 5, "Should have 5 rows"
        assert data[1][2] == '0.01', "First volume should be '0.01'"
        assert data[2][2] == '0.1', "Second volume should be '0.1'"
        assert data[3][2] == '0.00123456', "Third volume should be '0.00123456'"
        assert data[4][2] == '1.23456789', "Fourth volume should be '1.23456789'"
        
        print("✓ Volume formatting test passed")


def test_sample_data_volume_format():
    """Test that sample data uses 8 decimal places for volume."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'sample.csv')
        
        # Create sample data like csv_editor.py does
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled'])
            writer.writerow(['btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01000000', '5.0', 'true'])
            writer.writerow(['eth_1', 'XETHZUSD', '3000', 'above', 'sell', '0.10000000', '3.5', 'true'])
        
        # Read the file back
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            data = list(reader)
        
        # Verify volumes have 8 decimal places
        assert data[1][5] == '0.01000000', "BTC volume should have 8 decimal places"
        assert data[2][5] == '0.10000000', "ETH volume should have 8 decimal places"
        
        # Count decimal places
        btc_volume = data[1][5]
        eth_volume = data[2][5]
        
        # Check that they have exactly 8 decimal places
        assert '.' in btc_volume, "BTC volume should have decimal point"
        assert '.' in eth_volume, "ETH volume should have decimal point"
        
        btc_decimals = len(btc_volume.split('.')[1])
        eth_decimals = len(eth_volume.split('.')[1])
        
        assert btc_decimals == 8, f"BTC volume should have 8 decimal places, got {btc_decimals}"
        assert eth_decimals == 8, f"ETH volume should have 8 decimal places, got {eth_decimals}"
        
        print("✓ Sample data volume format test passed")


def test_volume_validation_formatting():
    """Test that volume validation formats values to 8 decimal places."""
    from csv_editor import EditCellScreen
    
    # Create a mock EditCellScreen to test validation
    screen = EditCellScreen(current_value="0.01", column_name="volume")
    
    # Test various volume inputs
    test_cases = [
        ("0.01", True, "0.01000000"),  # Should format to 8 decimals
        ("0.1", True, "0.10000000"),   # Should format to 8 decimals
        ("1", True, "1.00000000"),     # Should format to 8 decimals
        ("0.12345678", True, "0.12345678"),  # Already 8 decimals
        ("0.123456789", True, "0.12345679"),  # More than 8, should round
        ("0", False, None),            # Zero should fail
        ("-0.01", False, None),        # Negative should fail
        ("abc", False, None),          # Invalid text should fail
        ("", False, None),             # Empty should fail
    ]
    
    for value, expected_valid, expected_formatted in test_cases:
        is_valid, message = screen.validate_value(value)
        assert is_valid == expected_valid, f"Validation of '{value}' should return {expected_valid}, got {is_valid}"
        
        if expected_valid and expected_formatted:
            assert message == expected_formatted, f"Volume '{value}' should format to '{expected_formatted}', got '{message}'"
        elif not expected_valid:
            assert message != "", f"Invalid volume '{value}' should have an error message"
    
    print("✓ Volume validation formatting test passed")


def test_pair_validation_with_human_readable_names():
    """Test that pair validation resolves human-readable names to Kraken codes."""
    from csv_editor import EditCellScreen
    
    # Create a mock EditCellScreen to test pair validation
    screen = EditCellScreen(current_value="", column_name="pair")
    
    # Test various pair inputs
    test_cases = [
        # (input, should_be_valid, expected_resolved_code)
        ("BTC/USD", True, "XXBTZUSD"),
        ("btc/usd", True, "XXBTZUSD"),
        ("ETH/USDT", True, "ETHUSDT"),
        ("eth-usdt", True, "ETHUSDT"),
        ("SOL/EUR", True, "SOLEUR"),
        ("XXBTZUSD", True, None),  # Already correct code - no resolution needed
        ("ada/usd", True, "ADAUSD"),
        ("NOTAREALPAIR", False, None),  # Invalid pair
    ]
    
    for value, expected_valid, expected_code in test_cases:
        is_valid, message = screen.validate_value(value)
        assert is_valid == expected_valid, f"Validation of '{value}' should return {expected_valid}, got {is_valid}"
        
        if expected_valid and expected_code:
            # Check if message contains the expected code (may have warning appended)
            if "|" in message:
                resolved_code = message.split("|")[0]
            else:
                resolved_code = message if message else value
            assert resolved_code == expected_code, \
                f"Pair '{value}' should resolve to '{expected_code}', got '{resolved_code}'"
        elif not expected_valid:
            assert message != "", f"Invalid pair '{value}' should have an error message"
    
    print("✓ Pair validation with human-readable names test passed")


def test_pair_exact_match():
    """Test that exact pair code matches don't trigger resolution."""
    from csv_editor import EditCellScreen
    
    screen = EditCellScreen(current_value="XXBTZUSD", column_name="pair")
    is_valid, message = screen.validate_value("XXBTZUSD")
    
    assert is_valid is True, "Exact pair code should be valid"
    assert message == "", "Exact match should not have a resolution message"
    
    print("✓ Pair exact match test passed")


def run_all_tests():
    """Run all tests."""
    print("Running CSV Editor tests...\n")
    
    try:
        test_csv_editor_initialization()
        test_csv_reading()
        test_csv_writing()
        test_nonexistent_file()
        test_volume_formatting()
        test_sample_data_volume_format()
        test_volume_validation_formatting()
        test_pair_validation_with_human_readable_names()
        test_pair_exact_match()
        
        print("\n✅ All CSV Editor tests passed!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
