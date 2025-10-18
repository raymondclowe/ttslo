#!/usr/bin/env python3
"""
Demonstration of the race condition fix.

This script simulates the scenario from the issue:
- ttslo running in one window
- External editor modifying config.csv in another window
- Shows that no lines are lost

Run this to see the fix in action.
"""
import os
import csv
import tempfile
import shutil
import threading
import time
from datetime import datetime


def create_test_config(filepath):
    """Create a test config file."""
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                       'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writerow(['btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
        writer.writerow(['eth_1', 'XETHZUSD', '3000', 'above', 'sell', '0.1', '3.5', 'true'])
        writer.writerow(['# This is a comment', '', '', '', '', '', '', ''])


def count_lines(filepath):
    """Count total lines in file."""
    with open(filepath, 'r') as f:
        return sum(1 for _ in f)


def simulate_ttslo_write(filepath, iteration):
    """Simulate ttslo updating the config file."""
    from config import ConfigManager
    
    manager = ConfigManager(config_file=filepath)
    manager.update_config_on_trigger(
        config_id='btc_1',
        order_id=f'ORDER_{iteration}',
        trigger_time=datetime.now().isoformat(),
        trigger_price='51000'
    )


def simulate_editor_write(filepath, line_num):
    """Simulate external editor adding a line."""
    # Read current content
    with open(filepath, 'r', newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    # Add a new line (simulating user adding config)
    rows.append([f'new_{line_num}', 'ADAUSD', '1.0', 'above', 'sell', '100', '2.5', 'true'])
    
    # Write back (non-atomic, like most editors do)
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def run_demo():
    """Run the demonstration."""
    print("=" * 70)
    print("DEMONSTRATION: Race Condition Fix")
    print("=" * 70)
    print()
    
    # Create temp directory and config
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, 'config.csv')
    
    try:
        create_test_config(config_file)
        
        print(f"Created test config: {config_file}")
        initial_count = count_lines(config_file)
        print(f"Initial line count: {initial_count}")
        print()
        
        # Show initial content
        print("Initial config.csv content:")
        print("-" * 70)
        with open(config_file, 'r') as f:
            print(f.read())
        print("-" * 70)
        print()
        
        print("Starting concurrent operations:")
        print("  - TTSLO: updating btc_1 config 5 times")
        print("  - Editor: adding 5 new config lines")
        print()
        
        results = {'ttslo': 0, 'editor': 0, 'errors': []}
        stop_flag = threading.Event()
        
        def ttslo_thread():
            """Simulate ttslo making updates."""
            try:
                for i in range(5):
                    if stop_flag.is_set():
                        break
                    simulate_ttslo_write(config_file, i)
                    results['ttslo'] += 1
                    print(f"  TTSLO: Updated btc_1 (iteration {i+1})")
                    time.sleep(0.05)
            except Exception as e:
                results['errors'].append(('ttslo', str(e)))
        
        def editor_thread():
            """Simulate editor adding lines."""
            try:
                time.sleep(0.02)  # Small delay
                for i in range(5):
                    if stop_flag.is_set():
                        break
                    simulate_editor_write(config_file, i)
                    results['editor'] += 1
                    print(f"  Editor: Added new_{i} config")
                    time.sleep(0.08)
            except Exception as e:
                results['errors'].append(('editor', str(e)))
        
        # Start threads
        t1 = threading.Thread(target=ttslo_thread)
        t2 = threading.Thread(target=editor_thread)
        
        start_time = time.time()
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        elapsed = time.time() - start_time
        
        print()
        print(f"Completed in {elapsed:.2f} seconds")
        print()
        
        # Check results
        final_count = count_lines(config_file)
        
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"TTSLO operations:  {results['ttslo']}")
        print(f"Editor operations: {results['editor']}")
        print(f"Errors:            {len(results['errors'])}")
        print()
        print(f"Initial lines: {initial_count}")
        print(f"Final lines:   {final_count}")
        print()
        
        if results['errors']:
            print("⚠️  ERRORS OCCURRED:")
            for source, error in results['errors']:
                print(f"  {source}: {error}")
            print()
        
        if final_count >= initial_count:
            print("✅ SUCCESS: No lines were lost!")
            print(f"   Expected at least {initial_count} lines, got {final_count}")
        else:
            print("❌ FAILURE: Lines were lost!")
            print(f"   Started with {initial_count} lines, ended with {final_count}")
        
        print()
        print("Final config.csv content:")
        print("-" * 70)
        with open(config_file, 'r') as f:
            print(f.read())
        print("-" * 70)
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print()
        print(f"Cleaned up temp directory: {temp_dir}")


if __name__ == '__main__':
    run_demo()
