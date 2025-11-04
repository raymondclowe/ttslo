#!/usr/bin/env python3
"""
Tests for CSV Editor column normalization feature.
"""
import os
import sys
import tempfile
import csv
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from csv_editor import CSVEditor


def test_normalize_columns_reorders_correctly():
    """Test that normalize_columns reorders columns: required left, user-defined right."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create CSV with user-defined columns mixed in
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['worker', 'id', 'notes', 'pair', 'threshold_price', 'tags', 
                           'threshold_type', 'direction', 'volume', 'trailing_offset_percent', 
                           'enabled', 'linked_order_id', 'custom'])
            writer.writerow(['alice', 'btc_1', 'test note', 'XXBTZUSD', '50000', 'urgent',
                           'above', 'sell', '0.01', '5.0', 'true', '', 'data'])
        
        editor = CSVEditor(filename=test_file)
        
        # Read the file
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            editor.data = list(reader)
        
        # Normalize columns
        normalized = editor._normalize_columns()
        
        assert normalized is True, "Should report normalization occurred"
        
        # Check that required columns are first
        headers = editor.data[0]
        required_count = len(editor.REQUIRED_COLUMNS)
        
        # First N columns should be required columns
        for i, req_col in enumerate(editor.REQUIRED_COLUMNS):
            assert headers[i].lower() == req_col.lower(), \
                f"Column {i} should be '{req_col}', got '{headers[i]}'"
        
        # Remaining columns should be user-defined
        user_defined = headers[required_count:]
        expected_user = ['worker', 'notes', 'tags', 'custom']
        assert user_defined == expected_user, \
            f"User-defined columns should be {expected_user}, got {user_defined}"
        
        # Verify data integrity - check first data row
        assert editor.data[1][headers.index('id')] == 'btc_1', "id value should be preserved"
        assert editor.data[1][headers.index('worker')] == 'alice', "worker value should be preserved"
        assert editor.data[1][headers.index('notes')] == 'test note', "notes value should be preserved"
        assert editor.data[1][headers.index('pair')] == 'XXBTZUSD', "pair value should be preserved"
        assert editor.data[1][headers.index('tags')] == 'urgent', "tags value should be preserved"
        assert editor.data[1][headers.index('custom')] == 'data', "custom value should be preserved"
        
        print("✓ Normalize columns reorders correctly test passed")


def test_normalize_columns_preserves_all_data():
    """Test that normalization preserves all cell values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create CSV with multiple rows
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['note1', 'id', 'pair', 'note2', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled', 'linked_order_id'])
            writer.writerow(['n1a', 'btc_1', 'XXBTZUSD', 'n2a', '50000', 'above', 'sell', '0.01', '5.0', 'true', ''])
            writer.writerow(['n1b', 'eth_1', 'XETHZUSD', 'n2b', '3000', 'above', 'sell', '0.1', '3.5', 'true', ''])
        
        editor = CSVEditor(filename=test_file)
        
        # Read the file
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            editor.data = list(reader)
        
        # Store original data for comparison
        original_data = {}
        headers = editor.data[0]
        for row_idx in range(1, len(editor.data)):
            row = editor.data[row_idx]
            original_data[row_idx] = {headers[i]: row[i] for i in range(len(headers))}
        
        # Normalize columns
        editor._normalize_columns()
        
        # Verify all data is preserved
        new_headers = editor.data[0]
        for row_idx in range(1, len(editor.data)):
            new_row = editor.data[row_idx]
            for col_name, expected_value in original_data[row_idx].items():
                new_idx = new_headers.index(col_name)
                actual_value = new_row[new_idx]
                assert actual_value == expected_value, \
                    f"Row {row_idx}, column '{col_name}': expected '{expected_value}', got '{actual_value}'"
        
        print("✓ Normalize columns preserves all data test passed")


def test_normalize_columns_already_normalized():
    """Test that already-normalized files are not modified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create CSV already in correct order
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled', 
                           'linked_order_id', 'notes', 'worker'])
            writer.writerow(['btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true', '', 'test', 'alice'])
        
        editor = CSVEditor(filename=test_file)
        
        # Read the file
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            editor.data = list(reader)
        
        # Store original
        original_headers = editor.data[0][:]
        
        # Normalize columns
        normalized = editor._normalize_columns()
        
        assert normalized is False, "Should report no normalization needed"
        assert editor.data[0] == original_headers, "Headers should not change"
        
        print("✓ Normalize columns already normalized test passed")


def test_normalize_columns_only_required():
    """Test normalization with only required columns (no user-defined)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create CSV with only required columns in wrong order
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['enabled', 'id', 'volume', 'pair', 'threshold_price', 
                           'direction', 'threshold_type', 'trailing_offset_percent', 'linked_order_id'])
            writer.writerow(['true', 'btc_1', '0.01', 'XXBTZUSD', '50000', 'sell', 'above', '5.0', ''])
        
        editor = CSVEditor(filename=test_file)
        
        # Read the file
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            editor.data = list(reader)
        
        # Normalize columns
        normalized = editor._normalize_columns()
        
        # Should normalize to correct order
        headers = editor.data[0]
        for i, req_col in enumerate(editor.REQUIRED_COLUMNS):
            assert headers[i].lower() == req_col.lower(), \
                f"Column {i} should be '{req_col}', got '{headers[i]}'"
        
        # Verify data integrity
        assert editor.data[1][headers.index('id')] == 'btc_1', "id value should be preserved"
        assert editor.data[1][headers.index('enabled')] == 'true', "enabled value should be preserved"
        assert editor.data[1][headers.index('volume')] == '0.01', "volume value should be preserved"
        
        print("✓ Normalize columns only required test passed")


def test_normalize_columns_empty_file():
    """Test normalization handles empty files gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create empty file
        with open(test_file, 'w', newline='') as f:
            pass
        
        editor = CSVEditor(filename=test_file)
        editor.data = []
        
        # Normalize should return False for empty data
        normalized = editor._normalize_columns()
        assert normalized is False, "Empty file should not be normalized"
        
        print("✓ Normalize columns empty file test passed")


def test_normalize_columns_case_insensitive():
    """Test that column matching is case-insensitive."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create CSV with mixed case column names
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'PAIR', 'notes', 'Threshold_Price', 'THRESHOLD_TYPE', 
                           'Direction', 'Volume', 'Trailing_Offset_Percent', 'Enabled', 'Linked_Order_ID'])
            writer.writerow(['btc_1', 'XXBTZUSD', 'test', '50000', 'above', 'sell', '0.01', '5.0', 'true', ''])
        
        editor = CSVEditor(filename=test_file)
        
        # Read the file
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            editor.data = list(reader)
        
        # Normalize columns
        normalized = editor._normalize_columns()
        
        # Should recognize mixed case as required columns
        headers = editor.data[0]
        
        # First 9 should be required columns (case may vary)
        required_count = len(editor.REQUIRED_COLUMNS)
        required_headers_lower = [h.lower() for h in headers[:required_count]]
        expected_lower = [r.lower() for r in editor.REQUIRED_COLUMNS]
        
        assert required_headers_lower == expected_lower, \
            f"Required columns should be first, got {required_headers_lower}"
        
        # Last column should be user-defined
        assert headers[-1] == 'notes', "User column should be last"
        
        print("✓ Normalize columns case insensitive test passed")


def test_normalization_on_load():
    """Test that normalization is applied when loading a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create CSV with wrong column order
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['notes', 'id', 'pair', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled', 'linked_order_id'])
            writer.writerow(['test', 'btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true', ''])
        
        # Initialize editor (without running app)
        editor = CSVEditor(filename=test_file)
        
        # Manually read and process like read_csv_to_table does
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            editor.data = list(reader)
        
        # Normalize
        editor._normalize_columns()
        
        # Verify normalization occurred
        headers = editor.data[0]
        assert headers[0] == 'id', "First column should be 'id' after normalization"
        assert headers[-1] == 'notes', "Last column should be 'notes' (user-defined)"
        
        print("✓ Normalization on load test passed")


def test_normalization_preserves_empty_cells():
    """Test that empty cells are preserved during normalization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create CSV with empty cells
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['notes', 'id', 'pair', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled', 'linked_order_id'])
            writer.writerow(['', 'btc_1', 'XXBTZUSD', '', 'above', '', '0.01', '5.0', 'true', ''])
        
        editor = CSVEditor(filename=test_file)
        
        # Read the file
        with open(test_file, 'r', newline='') as f:
            reader = csv.reader(f)
            editor.data = list(reader)
        
        # Normalize columns
        editor._normalize_columns()
        
        # Verify empty cells are preserved
        headers = editor.data[0]
        row = editor.data[1]
        
        assert row[headers.index('threshold_price')] == '', "Empty threshold_price should be preserved"
        assert row[headers.index('direction')] == '', "Empty direction should be preserved"
        assert row[headers.index('linked_order_id')] == '', "Empty linked_order_id should be preserved"
        assert row[headers.index('notes')] == '', "Empty notes should be preserved"
        
        print("✓ Normalization preserves empty cells test passed")


def run_all_tests():
    """Run all normalization tests."""
    print("Running CSV Column Normalization tests...\n")
    
    try:
        test_normalize_columns_reorders_correctly()
        test_normalize_columns_preserves_all_data()
        test_normalize_columns_already_normalized()
        test_normalize_columns_only_required()
        test_normalize_columns_empty_file()
        test_normalize_columns_case_insensitive()
        test_normalization_on_load()
        test_normalization_preserves_empty_cells()
        
        print("\n✅ All CSV Column Normalization tests passed!")
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
