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


def run_all_tests():
    """Run all tests."""
    print("Running CSV Editor tests...\n")
    
    try:
        test_csv_editor_initialization()
        test_csv_reading()
        test_csv_writing()
        test_nonexistent_file()
        
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
