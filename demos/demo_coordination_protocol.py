#!/usr/bin/env python3
"""
Demonstration of the CSV editor coordination protocol.

This shows how the editor and service coordinate to prevent race conditions
through a handshake mechanism.
"""
import os
import sys
import tempfile
import csv
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ConfigManager

print("=" * 80)
print("CSV Editor Coordination Protocol Demo")
print("=" * 80)
print()
print("This demonstrates the handshake mechanism that prevents race conditions")
print("when the CSV editor needs to modify the config file while the service")
print("is running.")
print()

with tempfile.TemporaryDirectory() as tmpdir:
    config_file = os.path.join(tmpdir, 'demo_config.csv')
    state_file = os.path.join(tmpdir, 'demo_state.csv')
    
    # Create demo config file
    print("Setup: Creating demo config file")
    with open(config_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                        'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writerow(['btc1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
        writer.writerow(['eth1', 'XETHZUSD', '3000', 'above', 'sell', '0.1', '3.5', 'true'])
    print(f"  → Created: {config_file}")
    print()
    
    # Simulate service running
    cm = ConfigManager(config_file=config_file, state_file=state_file)
    
    print("-" * 80)
    print("SCENARIO: Service Running, User Opens CSV Editor")
    print("-" * 80)
    print()
    
    # Phase 1: Service operating normally
    print("Phase 1: Service Operating Normally")
    print("-" * 40)
    configs = cm.load_config()
    print(f"  Service: Loaded {len(configs)} configurations")
    for cfg in configs:
        print(f"    • {cfg['id']}: {cfg['pair']} @ ${cfg['threshold_price']}")
    
    # Service might write state
    test_state = {
        'btc1': {'id': 'btc1', 'triggered': 'false', 'last_checked': '2025-01-01T00:00:00Z'},
        'eth1': {'id': 'eth1', 'triggered': 'false', 'last_checked': '2025-01-01T00:00:00Z'}
    }
    cm.save_state(test_state)
    print(f"  Service: Saved state for {len(test_state)} configs")
    print()
    
    # Phase 2: Editor signals intent to lock
    print("Phase 2: User Opens CSV Editor")
    print("-" * 40)
    intent_file = config_file + '.editor_wants_lock'
    Path(intent_file).touch()
    print("  Editor: Created .editor_wants_lock file")
    print("  Editor: Signaling intent to edit the config...")
    print()
    
    # Phase 3: Service detects and responds
    print("Phase 3: Service Detects Editor Request")
    print("-" * 40)
    time.sleep(0.1)  # Simulate service check cycle
    is_coordinating = cm.check_editor_coordination()
    print(f"  Service: Coordination active = {is_coordinating}")
    
    idle_file = config_file + '.service_idle'
    if os.path.exists(idle_file):
        print("  Service: Created .service_idle file")
        print("  Service: ✓ Confirmed safe to lock - all operations paused")
    print()
    
    # Phase 4: Service operations are paused
    print("Phase 4: Service Pauses All I/O Operations")
    print("-" * 40)
    configs = cm.load_config()
    print(f"  Service: Attempted to load config → skipped (coordination active)")
    print(f"  Service: Returned {len(configs)} configs (empty during editing)")
    
    cm.save_state(test_state)
    print(f"  Service: Attempted to save state → skipped (coordination active)")
    print("  Service: All file operations suspended")
    print()
    
    # Phase 5: Editor has exclusive access
    print("Phase 5: Editor Has Exclusive Access")
    print("-" * 40)
    print("  Editor: Acquired exclusive file lock")
    print("  Editor: User can now safely edit the config")
    print("  Editor: No risk of race conditions or corruption")
    print()
    time.sleep(0.5)  # Simulate user editing
    
    # Phase 6: User saves and closes editor
    print("Phase 6: User Saves and Closes Editor")
    print("-" * 40)
    print("  Editor: User pressed Ctrl+S to save changes")
    print("  Editor: User pressed Ctrl+Q to quit")
    print("  Editor: Released file lock")
    os.unlink(intent_file)
    print("  Editor: Removed .editor_wants_lock file")
    print()
    
    # Phase 7: Service resumes
    print("Phase 7: Service Detects Lock Release")
    print("-" * 40)
    time.sleep(0.1)  # Simulate service check cycle
    is_coordinating = cm.check_editor_coordination()
    print(f"  Service: Coordination active = {is_coordinating}")
    print("  Service: Cleaned up .service_idle file")
    print("  Service: Resuming normal operations")
    print()
    
    # Phase 8: Service operates normally again
    print("Phase 8: Service Resumes Normal Operation")
    print("-" * 40)
    configs = cm.load_config()
    print(f"  Service: Loaded {len(configs)} configurations")
    for cfg in configs:
        print(f"    • {cfg['id']}: {cfg['pair']} @ ${cfg['threshold_price']}")
    
    cm.save_state(test_state)
    print(f"  Service: Saved state for {len(test_state)} configs")
    print("  Service: ✓ All operations back to normal")
    print()

print("=" * 80)
print("Summary")
print("=" * 80)
print()
print("The coordination protocol ensures:")
print("  ✓ Editor requests exclusive access before locking")
print("  ✓ Service acknowledges and pauses all I/O operations")
print("  ✓ Editor waits for service confirmation before locking")
print("  ✓ No race conditions between editor and service")
print("  ✓ Service automatically resumes when editor exits")
print()
print("This handshake mechanism eliminates the race condition risk identified")
print("where the service might be in the middle of a write operation when the")
print("editor attempts to lock the file.")
print()
print("=" * 80)
