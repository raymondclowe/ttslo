#!/usr/bin/env python3
"""
Tests for file locking in ConfigManager.
"""
import os
import sys
import tempfile
import fcntl
import csv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ConfigManager


def test_file_lock_detection():
    """Test that ConfigManager can detect locked files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create a test CSV file
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'pair', 'threshold_price'])
            writer.writerow(['test1', 'XXBTZUSD', '50000'])
        
        # Create ConfigManager
        config_manager = ConfigManager(config_file=test_file)
        
        # Test 1: File should not be locked initially
        assert not config_manager.is_file_locked(test_file), \
            "File should not be locked initially"
        print("✓ Unlocked file detection test passed")
        
        # Test 2: Acquire exclusive lock and check detection
        with open(test_file, 'r+') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Now the file should be detected as locked
            assert config_manager.is_file_locked(test_file), \
                "File should be detected as locked"
            print("✓ Locked file detection test passed")
            
            # Release the lock
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        
        # Test 3: After releasing, should not be locked
        assert not config_manager.is_file_locked(test_file), \
            "File should not be locked after release"
        print("✓ Lock release detection test passed")


def test_load_config_with_locked_file():
    """Test that load_config skips locked files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, 'test.csv')
        
        # Create a test CSV file
        with open(test_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled'])
            writer.writerow(['test1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
        
        # Create ConfigManager
        config_manager = ConfigManager(config_file=test_file)
        
        # Test 1: Load config when not locked
        configs = config_manager.load_config()
        assert len(configs) == 1, f"Expected 1 config, got {len(configs)}"
        assert configs[0]['id'] == 'test1', f"Expected id 'test1', got {configs[0]['id']}"
        print("✓ Load unlocked config test passed")
        
        # Test 2: Load config when locked
        with open(test_file, 'r+') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # load_config should return empty list for locked file
            configs = config_manager.load_config()
            assert len(configs) == 0, \
                f"Expected empty list for locked file, got {len(configs)} configs"
            print("✓ Skip locked config test passed")
            
            # Release the lock
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


if __name__ == '__main__':
    print("Running file locking tests...\n")
    test_file_lock_detection()
    test_load_config_with_locked_file()
    print("\nAll tests passed!")
