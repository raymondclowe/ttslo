#!/usr/bin/env python3
"""
Demonstration of CSV editor default path detection and file locking.

This script demonstrates how the CSV editor automatically finds the service's
config file and uses file locking to prevent conflicts.
"""
import os
import sys
import tempfile
import csv
import time

print("=" * 70)
print("CSV Editor Smart Defaults & File Locking Demo")
print("=" * 70)
print()

# Demo 1: Default path detection
print("DEMO 1: Smart Config File Detection")
print("-" * 70)

# Define the function inline to avoid importing textual
def get_default_config_path() -> str:
    """Determine the default config file path."""
    env_config = os.getenv('TTSLO_CONFIG_FILE')
    if env_config:
        return env_config
    
    try:
        import pwd
        current_user = pwd.getpwuid(os.getuid()).pw_name
        if current_user == 'ttslo':
            return '/var/lib/ttslo/config.csv'
    except (ImportError, KeyError):
        pass
    
    return 'config.csv'

print("\nScenario 1: No environment variable set")
if 'TTSLO_CONFIG_FILE' in os.environ:
    del os.environ['TTSLO_CONFIG_FILE']
path = get_default_config_path()
print(f"  → Default path: {path}")

print("\nScenario 2: TTSLO_CONFIG_FILE environment variable set")
os.environ['TTSLO_CONFIG_FILE'] = '/var/lib/ttslo/config.csv'
path = get_default_config_path()
print(f"  → Path from env var: {path}")

print("\nScenario 3: Running as ttslo user (simulated)")
try:
    import pwd
    current_user = pwd.getpwuid(os.getuid()).pw_name
    print(f"  → Current user: {current_user}")
    if current_user == 'ttslo':
        print(f"  → Would use: /var/lib/ttslo/config.csv")
    else:
        print(f"  → Would use: config.csv (not ttslo user)")
except ImportError:
    print("  → pwd module not available (Windows)")

print("\n✓ The CSV editor automatically finds the right config file!")
print()

# Demo 2: File locking
print("DEMO 2: File Locking to Prevent Conflicts")
print("-" * 70)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ConfigManager

with tempfile.TemporaryDirectory() as tmpdir:
    config_file = os.path.join(tmpdir, 'demo_config.csv')
    
    # Create a demo config file
    print(f"\nCreating demo config file: {config_file}")
    with open(config_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                        'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writerow(['btc1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01000000', '5.0', 'true'])
        writer.writerow(['eth1', 'XETHZUSD', '3000', 'above', 'sell', '0.10000000', '3.5', 'true'])
    
    print("✓ Demo config created with 2 configurations")
    
    # Show normal loading
    print("\n1. Service loads config (no lock):")
    cm = ConfigManager(config_file=config_file)
    configs = cm.load_config()
    print(f"   → Loaded {len(configs)} configurations")
    for cfg in configs:
        print(f"      • {cfg['id']}: {cfg['pair']} @ ${cfg['threshold_price']}")
    
    # Simulate CSV editor opening the file
    print("\n2. User opens CSV editor (file gets locked):")
    print("   → CSV editor acquires exclusive lock")
    import fcntl
    lock_file = open(config_file, 'r+')
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    print("   ✓ File is now locked for editing")
    
    # Show service behavior with locked file
    print("\n3. Service tries to load config while editor is open:")
    configs = cm.load_config()
    print(f"   → Service skips this check cycle (returned {len(configs)} configs)")
    print("   → This prevents conflicts and race conditions!")
    
    # Release lock
    print("\n4. User saves and closes CSV editor:")
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    lock_file.close()
    print("   → Lock released")
    
    # Show service resumes normal operation
    print("\n5. Service loads config on next check:")
    configs = cm.load_config()
    print(f"   → Loaded {len(configs)} configurations")
    print("   ✓ Service resumes normal operation")

print()
print("=" * 70)
print("Summary:")
print("=" * 70)
print("✓ CSV editor automatically detects the service's config file")
print("✓ File locking prevents edit conflicts with running service")
print("✓ Service gracefully skips check cycles during editing")
print("✓ No need to stop the service to edit config!")
print()
print("For full details, see CSV_EDITOR_README.md")
print("=" * 70)
