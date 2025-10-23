#!/usr/bin/env python3
"""
Tests for CSV editor coordination protocol with the service.

This tests the handshake mechanism that prevents race conditions
when the editor requests exclusive access to the config file.
"""
import os
import sys
import tempfile
import csv
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ConfigManager


def test_editor_coordination_protocol():
    """Test that the coordination protocol works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        
        # Create test config file
        with open(config_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled'])
            writer.writerow(['btc1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
        
        # Create ConfigManager
        cm = ConfigManager(config_file=config_file, state_file=state_file)
        
        # Test 1: Normal operation (no coordination)
        print("Test 1: Normal operation (no coordination)")
        configs = cm.load_config()
        assert len(configs) == 1, f"Expected 1 config, got {len(configs)}"
        assert not cm.editor_coordination_active, "Coordination should not be active"
        print("  ✓ Service loads config normally")
        
        # Test 2: Editor signals intent to lock
        print("\nTest 2: Editor signals intent to lock")
        intent_file = config_file + '.editor_wants_lock'
        Path(intent_file).touch()
        print("  → Editor created .editor_wants_lock file")
        
        # Service checks for coordination
        is_coordinating = cm.check_editor_coordination()
        assert is_coordinating, "Coordination should be active"
        assert cm.editor_coordination_active, "Internal flag should be set"
        print("  ✓ Service detected editor intent")
        
        # Check that service created idle signal
        idle_file = config_file + '.service_idle'
        assert os.path.exists(idle_file), "Service should create .service_idle file"
        print("  ✓ Service created .service_idle signal")
        
        # Test 3: Service skips operations during coordination
        print("\nTest 3: Service pauses operations during coordination")
        configs = cm.load_config()
        assert len(configs) == 0, "Service should skip loading config during coordination"
        print("  ✓ Service skipped config load")
        
        # Test save_state is also skipped
        test_state = {'btc1': {'id': 'btc1', 'triggered': 'true'}}
        cm.save_state(test_state)
        # State file should not exist (or not be updated)
        if os.path.exists(state_file):
            # If it exists, it should be empty or from before
            with open(state_file, 'r') as f:
                content = f.read()
                # Should be empty or just headers
                assert 'triggered' not in content or content.strip() == '', \
                    "State should not be written during coordination"
        print("  ✓ Service skipped state save")
        
        # Test 4: Editor releases lock
        print("\nTest 4: Editor releases lock")
        os.unlink(intent_file)
        print("  → Editor removed .editor_wants_lock file")
        
        # Service should detect release
        is_coordinating = cm.check_editor_coordination()
        assert not is_coordinating, "Coordination should be inactive"
        assert not cm.editor_coordination_active, "Internal flag should be cleared"
        print("  ✓ Service detected lock release")
        
        # Idle file should be cleaned up
        assert not os.path.exists(idle_file), "Service should remove .service_idle file"
        print("  ✓ Service cleaned up .service_idle file")
        
        # Test 5: Service resumes normal operation
        print("\nTest 5: Service resumes normal operation")
        configs = cm.load_config()
        assert len(configs) == 1, f"Expected 1 config, got {len(configs)}"
        print("  ✓ Service resumed normal operation")


def test_coordination_timeout_behavior():
    """Test behavior when editor coordination files are stale."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        
        # Create test config file
        with open(config_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled'])
            writer.writerow(['btc1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
        
        cm = ConfigManager(config_file=config_file)
        
        # Simulate stale coordination file (editor crashed)
        intent_file = config_file + '.editor_wants_lock'
        Path(intent_file).touch()
        
        print("Test: Coordination file exists (simulating editor request)")
        is_coordinating = cm.check_editor_coordination()
        assert is_coordinating, "Should detect coordination request"
        print("  ✓ Service detected coordination request")
        
        # Service should still be able to clean up
        os.unlink(intent_file)
        is_coordinating = cm.check_editor_coordination()
        assert not is_coordinating, "Should clear coordination when file removed"
        print("  ✓ Service cleared coordination state")


def test_multiple_coordination_cycles():
    """Test multiple editor open/close cycles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        
        # Create test config file
        with open(config_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                           'direction', 'volume', 'trailing_offset_percent', 'enabled'])
            writer.writerow(['btc1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
        
        cm = ConfigManager(config_file=config_file)
        intent_file = config_file + '.editor_wants_lock'
        
        print("Test: Multiple coordination cycles")
        for i in range(3):
            print(f"\n  Cycle {i+1}:")
            
            # Editor requests lock
            Path(intent_file).touch()
            is_coordinating = cm.check_editor_coordination()
            assert is_coordinating, f"Cycle {i+1}: Should activate coordination"
            print(f"    ✓ Coordination activated")
            
            # Editor releases lock
            os.unlink(intent_file)
            is_coordinating = cm.check_editor_coordination()
            assert not is_coordinating, f"Cycle {i+1}: Should deactivate coordination"
            print(f"    ✓ Coordination released")
        
        print("\n  ✓ All cycles completed successfully")


if __name__ == '__main__':
    print("=" * 70)
    print("CSV Editor Coordination Protocol Tests")
    print("=" * 70)
    print()
    
    test_editor_coordination_protocol()
    print("\n" + "=" * 70)
    test_coordination_timeout_behavior()
    print("\n" + "=" * 70)
    test_multiple_coordination_cycles()
    
    print("\n" + "=" * 70)
    print("All coordination tests passed!")
    print("=" * 70)
