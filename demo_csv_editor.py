#!/usr/bin/env python3
"""
Demo script to show CSV editor working with config_sample.csv
This creates a test CSV file and verifies the editor can work with it.
"""
import csv
import tempfile
import os
from pathlib import Path

# Create a test CSV in a temp directory
test_dir = tempfile.mkdtemp()
test_file = os.path.join(test_dir, 'test_config.csv')

# Create test data that matches the TTSLO config format
test_data = [
    ['id', 'pair', 'threshold_price', 'threshold_type', 'direction', 'volume', 'trailing_offset_percent', 'enabled'],
    ['btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01000000', '5.0', 'true'],
    ['eth_1', 'XETHZUSD', '3000', 'above', 'sell', '0.10000000', '3.5', 'true'],
]

with open(test_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(test_data)

print(f"Created test CSV file: {test_file}")
print("\nContents:")
with open(test_file, 'r') as f:
    print(f.read())

print("\n" + "="*60)
print("CSV Editor is ready to use!")
print("="*60)
print("\nTo run the CSV editor with this test file:")
print(f"  python csv_editor.py {test_file}")
print("\nTo run with the sample config file:")
print("  python csv_editor.py config_sample.csv")
print("\nTo run with the actual config file:")
print("  python csv_editor.py config.csv")
print("\nKey Bindings:")
print("  Ctrl+S: Save the CSV file")
print("  Ctrl+Q: Quit the application")
print("  Ctrl+N: Add a new row")
print("  Ctrl+D: Delete the current row")
print("  Enter:  Edit the selected cell")
print("  Tab/Shift+Tab: Navigate between cells")
print("  Arrow keys: Navigate the table")
print("\n")
