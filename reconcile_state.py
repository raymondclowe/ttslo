#!/usr/bin/env python3
"""
State.csv reconciliation tool for TTSLO

This tool reconciles state.csv with actual open orders from Kraken and logs.csv
to ensure that orders created by ttslo.py are correctly tracked in state.csv.

Usage:
    # Dry run (shows what would be changed):
    python3 reconcile_state.py --dry-run
    
    # Apply changes:
    python3 reconcile_state.py
    
    # Use with custom files:
    python3 reconcile_state.py --state-file /path/to/state.csv --logs-file /path/to/logs.csv

This addresses issue #88 where state.csv may not update if there's an exception
during order creation, leading to orders being incorrectly marked as 'manual'.
"""
import sys
import os
import csv
import argparse
import shutil
from datetime import datetime
from typing import Dict, List, Tuple

# Import from the ttslo package
from kraken_api import KrakenAPI
from creds import find_kraken_credentials
from config import ConfigManager


def fetch_open_orders(api: KrakenAPI) -> Dict:
    """Fetch open orders from Kraken"""
    try:
        result = api.query_open_orders()
        return result.get('open', {})
    except Exception as e:
        print(f"ERROR fetching open orders: {e}", file=sys.stderr)
        return {}


def parse_logs_for_order_creation(logs_file: str) -> Dict[str, Dict]:
    """
    Parse logs.csv to extract order creation information.
    
    Returns:
        Dict mapping order_id to order info (config_id, timestamps, etc.)
    """
    order_info = {}
    pending_creates = {}  # Track "Creating TSL order" messages
    
    if not os.path.exists(logs_file):
        print(f"WARNING: Logs file not found: {logs_file}", file=sys.stderr)
        return order_info
    
    with open(logs_file, 'r') as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return order_info
        
        for row in reader:
            if len(row) < 4:
                continue
            
            timestamp = row[0]
            message = row[2]
            config_id = row[3] if len(row) > 3 else ''
            
            # Look for "Creating TSL order" entries to capture trailing offset
            if 'Creating TSL order:' in message and config_id:
                info = {
                    'config_id': config_id,
                    'create_timestamp': timestamp,
                }
                
                # Parse trailing offset
                if 'trailing_offset=' in message:
                    offset_str = message.split('trailing_offset=')[1]
                    offset_str = offset_str.split('%')[0] + '%'
                    info['trailing_offset'] = offset_str
                
                # Parse trigger price (5th column)
                if len(row) > 4:
                    info['trigger_price'] = row[4]
                
                pending_creates[config_id] = info
            
            # Look for "TSL order created successfully" entries
            elif 'TSL order created successfully: order_id=' in message:
                order_id = row[4] if len(row) > 4 else ''
                
                if order_id and config_id:
                    # Match with pending create
                    if config_id in pending_creates:
                        info = pending_creates[config_id]
                        info['order_id'] = order_id
                        info['success_timestamp'] = timestamp
                        order_info[order_id] = info
                        del pending_creates[config_id]
                    else:
                        # Fallback if we didn't see the create message
                        order_info[order_id] = {
                            'config_id': config_id,
                            'order_id': order_id,
                            'success_timestamp': timestamp,
                        }
    
    return order_info


def load_state_file(state_file: str) -> Dict[str, Dict]:
    """Load current state.csv"""
    state = {}
    
    if not os.path.exists(state_file):
        return state
    
    with open(state_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('id'):
                state[row['id']] = row
    
    return state


def reconcile_state(state: Dict, open_orders: Dict, order_info: Dict) -> Tuple[Dict, List[str]]:
    """
    Reconcile state.csv with open orders from Kraken and logs.
    
    Returns:
        Tuple of (updated_state, list of changes made)
    """
    changes = []
    updated_state = state.copy()
    
    # Find orders from logs that are still open on Kraken
    for order_id, kraken_order in open_orders.items():
        if order_id in order_info:
            info = order_info[order_id]
            config_id = info['config_id']
            
            # Check if state entry exists and is correct
            if config_id in updated_state:
                current_entry = updated_state[config_id]
                
                # Check if order_id matches
                if current_entry.get('order_id') != order_id:
                    # State exists but order_id is wrong or missing
                    changes.append(f"Config {config_id}: Updating order_id from '{current_entry.get('order_id')}' to '{order_id}'")
                    current_entry['order_id'] = order_id
                    current_entry['triggered'] = 'true'
                    
                    # Update other fields if available
                    if 'trigger_price' in info:
                        current_entry['trigger_price'] = info['trigger_price']
                    if 'success_timestamp' in info:
                        current_entry['trigger_time'] = info['success_timestamp']
                    if 'trailing_offset' in info:
                        current_entry['offset'] = info['trailing_offset']
                    
                    updated_state[config_id] = current_entry
            else:
                # State entry doesn't exist - create it
                changes.append(f"Config {config_id}: Creating new state entry for order {order_id}")
                
                new_entry = {
                    'id': config_id,
                    'triggered': 'true',
                    'trigger_price': info.get('trigger_price', ''),
                    'trigger_time': info.get('success_timestamp', ''),
                    'order_id': order_id,
                    'activated_on': '',
                    'last_checked': '',
                    'offset': info.get('trailing_offset', ''),
                    'fill_notified': '',
                    'last_error': '',
                    'error_notified': ''
                }
                
                updated_state[config_id] = new_entry
    
    return updated_state, changes


def save_state_file(state_file: str, state: Dict):
    """Save state.csv with proper backup"""
    # Create backup
    if os.path.exists(state_file):
        backup_file = f"{state_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(state_file, backup_file)
        print(f"Created backup: {backup_file}")
    
    # Write state file
    fieldnames = ['id', 'triggered', 'trigger_price', 'trigger_time', 'order_id', 
                  'activated_on', 'last_checked', 'offset', 'fill_notified', 
                  'last_error', 'error_notified']
    
    with open(state_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for config_id, config_state in state.items():
            writer.writerow(config_state)


def main():
    parser = argparse.ArgumentParser(
        description='Reconcile state.csv with Kraken open orders and logs.csv'
    )
    parser.add_argument('--state-file', default='state.csv',
                        help='Path to state.csv (default: state.csv)')
    parser.add_argument('--logs-file', default='logs.csv',
                        help='Path to logs.csv (default: logs.csv)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be changed without making changes')
    parser.add_argument('--env-file', default='.env',
                        help='Path to .env file (default: .env)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("STATE.CSV RECONCILIATION TOOL")
    print("=" * 80)
    print()
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print()
    
    # Get Kraken credentials
    key, secret = find_kraken_credentials(readwrite=False, env_file=args.env_file)
    if not key or not secret:
        print("ERROR: Kraken credentials not found", file=sys.stderr)
        return 1
    
    api = KrakenAPI(key, secret)
    
    # Step 1: Fetch open orders
    print("Step 1: Fetching open orders from Kraken...")
    open_orders = fetch_open_orders(api)
    print(f"Found {len(open_orders)} open orders")
    print()
    
    # Step 2: Parse logs
    print("Step 2: Parsing logs.csv for order creation history...")
    order_info = parse_logs_for_order_creation(args.logs_file)
    print(f"Found {len(order_info)} order creations in logs")
    print()
    
    # Step 3: Load current state
    print("Step 3: Loading current state.csv...")
    state = load_state_file(args.state_file)
    print(f"Loaded {len(state)} state entries")
    print()
    
    # Step 4: Reconcile
    print("Step 4: Reconciling state with open orders...")
    updated_state, changes = reconcile_state(state, open_orders, order_info)
    print()
    
    if not changes:
        print("✓ No changes needed - state.csv is already correct!")
        return 0
    
    print(f"Found {len(changes)} changes needed:")
    print("-" * 80)
    for change in changes:
        print(f"  {change}")
    print()
    
    if args.dry_run:
        print("DRY RUN MODE - No changes were made")
        print("Run without --dry-run to apply these changes")
        return 0
    
    # Step 5: Save updated state
    print("Step 5: Saving updated state.csv...")
    save_state_file(args.state_file, updated_state)
    print("✓ State.csv updated successfully!")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
