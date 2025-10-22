"""
Configuration and state management using CSV files.
"""
import csv
import os
import tempfile
import shutil
import time
import fcntl
from datetime import datetime, timezone


class ConfigManager:
    """Manages configuration, state, and logging using CSV files."""
    
    def __init__(self, config_file='config.csv', state_file='state.csv', log_file='logs.csv'):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration CSV file
            state_file: Path to state CSV file
            log_file: Path to log CSV file
        """
        self.config_file = config_file
        self.state_file = state_file
        self.log_file = log_file
        self.editor_coordination_active = False  # Flag to pause operations when editor requests lock
        # TTL (seconds) after which an editor intent file is considered stale.
        # If an intent file is older than this, the service will remove it and
        # ignore the coordination request. Default: 5 minutes (300s).
        self.editor_intent_ttl = 300
    
    def is_file_locked(self, filepath):
        """
        Check if a file is locked by another process (e.g., CSV editor).
        
        This performs a non-blocking check for an exclusive lock.
        If the file is locked, returns True. Otherwise returns False.
        
        Args:
            filepath: Path to file to check
            
        Returns:
            bool: True if file is locked, False otherwise
        """
        if not os.path.exists(filepath):
            return False
        
        try:
            # Try to open and acquire a shared lock (non-blocking)
            with open(filepath, 'r') as f:
                try:
                    # Try to acquire shared lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    # If we got the lock, release it immediately
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    return False  # File is not locked
                except IOError:
                    # Could not acquire lock - file is locked
                    return True
        except Exception:
            # If we can't check, assume not locked
            return False
    
    def check_editor_coordination(self):
        """
        Check if CSV editor is requesting lock and respond appropriately.
        
        This implements the service side of the coordination protocol:
        1. Check for .editor_wants_lock file
        2. If found, set coordination flag and create .service_idle file
        3. Service will pause operations until editor releases lock
        
        Returns:
            bool: True if editor coordination is active, False otherwise
        """
        intent_file = self.config_file + '.editor_wants_lock'
        idle_file = self.config_file + '.service_idle'
        
        # Check if editor wants to edit
        # Primary check: intent file next to the config file (created by editor)
        now = time.time()
        if os.path.exists(intent_file):
            try:
                mtime = os.path.getmtime(intent_file)
                age = now - mtime
                if self.editor_intent_ttl and age > self.editor_intent_ttl:
                    # Stale intent file: remove and ignore
                    try:
                        os.unlink(intent_file)
                        print(f"WARNING: Removed stale editor intent file: {intent_file} (age={age:.0f}s)")
                    except Exception:
                        pass
                    # Ensure coordination flag cleared
                    if self.editor_coordination_active:
                        self.editor_coordination_active = False
                    return False
            except Exception:
                # If we can't stat the file, proceed to treat it as present
                pass
        if os.path.exists(intent_file):
            if not self.editor_coordination_active:
                # First time seeing the request - signal we're idle
                self.editor_coordination_active = True
                try:
                    # Create idle signal file
                    with open(idle_file, 'w') as f:
                        f.write(str(os.getpid()))
                    print(f"INFO: CSV editor requesting lock. Service pausing config operations.")
                except Exception as e:
                    print(f"WARNING: Could not create idle file: {e}")
            return True
        # Secondary check: per-user fallback intent files in the system temp dir.
        # Editors running as non-service users may not be able to write into
        # the service-owned directory. They can instead create a file in
        # /tmp named like `ttslo_editor_wants_lock.<uid>.<user>.<basename>`
        # containing the canonical path to the config file they intend to edit.
        try:
            import glob, tempfile
            tmpdir = tempfile.gettempdir()
            pattern = os.path.join(tmpdir, 'ttslo_editor_wants_lock.*')
            for path in glob.glob(pattern):
                try:
                    # Stale detection for fallback files
                    try:
                        mtime = os.path.getmtime(path)
                        age = now - mtime
                        if self.editor_intent_ttl and age > self.editor_intent_ttl:
                            try:
                                os.unlink(path)
                                print(f"WARNING: Removed stale fallback intent file: {path} (age={age:.0f}s)")
                            except Exception:
                                pass
                            continue
                    except Exception:
                        # If we can't stat the file, proceed to reading it
                        pass

                    with open(path, 'r') as f:
                        content = f.read().strip()
                    if not content:
                        continue
                    # If the fallback file references this config file, treat it
                    # as an intent signal for coordination.
                    if os.path.abspath(content) == os.path.abspath(self.config_file):
                        if not self.editor_coordination_active:
                            self.editor_coordination_active = True
                            try:
                                with open(idle_file, 'w') as f:
                                    f.write(str(os.getpid()))
                                print(f"INFO: CSV editor requesting lock via fallback file {path}. Service pausing config operations.")
                            except Exception as e:
                                print(f"WARNING: Could not create idle file: {e}")
                        return True
                except Exception:
                    # Ignore unreadable fallback files
                    continue
        except Exception:
            # If glob/tempdir not available or other issue, ignore secondary check
            pass
        else:
            # Editor is done, clean up
            if self.editor_coordination_active:
                self.editor_coordination_active = False
                try:
                    if os.path.exists(idle_file):
                        os.unlink(idle_file)
                    print(f"INFO: CSV editor released lock. Service resuming normal operations.")
                except Exception:
                    pass
            return False
    
    def _atomic_write_csv(self, filepath, fieldnames, rows, max_retries=3, retry_delay=0.1):
        """
        Atomically write CSV data to file using write-to-temp-then-rename pattern.
        
        This prevents partial writes and data corruption when multiple processes
        access the file simultaneously.
        
        Args:
            filepath: Target file path
            fieldnames: List of CSV column names
            rows: List of row dictionaries
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Raises:
            Exception: If write fails after all retries
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Create a temporary file in the same directory as the target
                # This ensures atomic rename on the same filesystem
                target_dir = os.path.dirname(filepath) or '.'
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=target_dir,
                    prefix='.tmp_',
                    suffix=os.path.basename(filepath)
                )
                
                try:
                    # Write to temporary file
                    with os.fdopen(temp_fd, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                    
                    # Atomically replace the target file
                    # On Unix/Linux, this is atomic. On Windows, it's mostly atomic.
                    shutil.move(temp_path, filepath)
                    return  # Success!
                    
                except Exception as e:
                    # Clean up temp file if it exists
                    try:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                    except Exception:
                        pass  # Ignore cleanup errors
                    raise e
                    
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Wait before retry
                    time.sleep(retry_delay)
                    continue
        
        # All retries failed
        raise last_error
    
    def _read_csv_preserving_all_lines(self, filepath):
        """
        Read CSV file and preserve ALL lines including comments and empty rows.
        
        Returns a tuple of (fieldnames, rows) where rows includes all lines
        in their original form.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            Tuple of (fieldnames, all_rows) where all_rows preserves everything
        """
        if not os.path.exists(filepath):
            return None, []
        
        with open(filepath, 'r', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            all_rows = []
            
            for row in reader:
                # Keep ALL rows - don't filter anything
                all_rows.append(row)
        
        return fieldnames, all_rows
        
    def load_config(self):
        """
        Load configuration from CSV file.
        
        Returns:
            List of configuration dictionaries
        """
        start_time = time.time()
        if not os.path.exists(self.config_file):
            print(f"[PERF] load_config: file not found, elapsed {time.time() - start_time:.3f}s")
            return []
        
        # Check for editor coordination request
        if self.check_editor_coordination():
            # Editor is requesting lock - skip this cycle
            return []
        
        # Check if file is being edited (backup check)
        if self.is_file_locked(self.config_file):
            print(f"WARNING: {self.config_file} is locked (being edited). Skipping this check cycle.")
            return []
        
        configs = []
        with open(self.config_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                if not row or all((v is None or str(v).strip() == '') for v in row.values()):
                    continue
                # Skip comment lines (id or pair starts with #, or all fields are comments)
                id_val = row.get('id', '').strip()
                pair_val = row.get('pair', '').strip()
                if id_val.startswith('#') or pair_val.startswith('#'):
                    continue
                # Also skip if all fields start with # (extra safety)
                if all(str(v).strip().startswith('#') for v in row.values() if v is not None and str(v).strip() != ''):
                    continue
                configs.append(row)
        elapsed = time.time() - start_time
        print(f"[PERF] load_config: loaded {len(configs)} configs in {elapsed:.3f}s")
        return configs
    
    def load_state(self):
        """
        Load state from CSV file.
        
        Returns:
            Dictionary mapping config IDs to their state
        """
        start_time = time.time()
        if not os.path.exists(self.state_file):
            print(f"[PERF] load_state: file not found, elapsed {time.time() - start_time:.3f}s")
            return {}
            
        state = {}
        with open(self.state_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('id'):
                    state[row['id']] = row
        elapsed = time.time() - start_time
        print(f"[PERF] load_state: loaded {len(state)} state entries in {elapsed:.3f}s")
        return state
    
    def save_state(self, state):
        """
        Save state to CSV file.
        
        Args:
            state: Dictionary mapping config IDs to their state
        """
        if not state:
            return
        
        # Check for editor coordination - skip write if editor has lock
        if self.check_editor_coordination():
            # Editor is requesting/has lock - skip this write
            return
            
        # Added 'offset' to capture the trailing offset specified when order was created
        # Added 'fill_notified' to track if we've sent notification about order being filled
        fieldnames = ['id', 'triggered', 'trigger_price', 'trigger_time', 'order_id', 'activated_on', 'last_checked', 'offset', 'fill_notified']

        with open(self.state_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for config_id, config_state in state.items():
                # Ensure offset key exists so CSV stays consistent even if older state lacks it
                if 'offset' not in config_state:
                    # Try common backup keys that might contain offset info
                    # Keep empty string if not present
                    config_state['offset'] = config_state.get('trailing_offset_percent', '')
                writer.writerow(config_state)
    
    def log(self, level, message, **kwargs):
        """
        Log a message to the CSV log file.
        
        Args:
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Log message
            **kwargs: Additional fields to include in log
        """
        # Check for editor coordination - skip log if editor has lock
        # (logs are in a separate file, but we pause all I/O during coordination)
        if self.editor_coordination_active:
            return
            
        timestamp = datetime.now(timezone.utc).isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message
        }
        log_entry.update(kwargs)
        
        # Check if log file exists to determine if we need to write header
        file_exists = os.path.exists(self.log_file)
        
        with open(self.log_file, 'a', newline='') as f:
            fieldnames = list(log_entry.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            writer.writerow(log_entry)
    
    def create_sample_config(self, filename='config_sample.csv'):
        """
        Create a sample configuration file with examples and comments.
        
        Args:
            filename: Name of sample config file to create
        """
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 'direction', 
                           'volume', 'trailing_offset_percent', 'enabled'])
            
            # Write example rows
            writer.writerow(['btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
            writer.writerow(['eth_1', 'XETHZUSD', '3000', 'above', 'sell', '0.1', '3.5', 'true'])
            writer.writerow(['# Example: Trigger sell TSL when BTC goes above $50k with 5% trailing offset', '', '', '', '', '', '', ''])
            writer.writerow(['# id: Unique identifier for this configuration', '', '', '', '', '', '', ''])
            writer.writerow(['# pair: Kraken trading pair (XXBTZUSD for BTC/USD, XETHZUSD for ETH/USD)', '', '', '', '', '', '', ''])
            writer.writerow(['# threshold_price: Price threshold that triggers the TSL order', '', '', '', '', '', '', ''])
            writer.writerow(['# threshold_type: "above" or "below" - condition for threshold', '', '', '', '', '', '', ''])
            writer.writerow(['# direction: "buy" or "sell" - direction of TSL order', '', '', '', '', '', '', ''])
            writer.writerow(['# volume: Amount to trade', '', '', '', '', '', '', ''])
            writer.writerow(['# trailing_offset_percent: Trailing stop offset as percentage (e.g., 5.0 for 5%)', '', '', '', '', '', '', ''])
            writer.writerow(['# enabled: "true" or "false" - whether this config is active', '', '', '', '', '', '', ''])
    
    def initialize_state_file(self):
        """Initialize an empty state file with headers."""
        # Include 'offset' column to record trailing offset specified when order created
        fieldnames = ['id', 'triggered', 'trigger_price', 'trigger_time', 'order_id', 'activated_on', 'last_checked', 'offset']
        
        with open(self.state_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
    
    def update_config_on_trigger(self, config_id, order_id, trigger_time, trigger_price):
        """
        Update configuration file when a config is triggered.
        
        Updates the row with the given config_id to:
        - Set enabled='false'
        - Add/update order_id
        - Add/update trigger_time
        - Add/update trigger_price
        
        SAFETY: Uses atomic write to prevent data loss during concurrent access.
        Preserves ALL lines including comments and empty rows.
        
        Args:
            config_id: ID of the configuration to update
            order_id: Kraken order ID from the triggered order
            trigger_time: ISO format timestamp when trigger occurred
            trigger_price: Price at which the trigger occurred
        """
        if not os.path.exists(self.config_file):
            return
        
        # Read all rows using the preserving method
        fieldnames, all_rows = self._read_csv_preserving_all_lines(self.config_file)
        
        if not fieldnames:
            return
        
        # Ensure we have the new columns in fieldnames
        fieldnames = list(fieldnames)
        if 'order_id' not in fieldnames:
            fieldnames.append('order_id')
        if 'trigger_time' not in fieldnames:
            fieldnames.append('trigger_time')
        if 'trigger_price' not in fieldnames:
            fieldnames.append('trigger_price')
        
        # Update matching row while preserving all others (including comments/empty)
        for row in all_rows:
            if row.get('id') == config_id:
                row['enabled'] = 'false'
                row['order_id'] = order_id
                row['trigger_time'] = trigger_time
                row['trigger_price'] = trigger_price
        
        # Write atomically to prevent data loss
        self._atomic_write_csv(self.config_file, fieldnames, all_rows)
    
    def disable_configs(self, config_ids):
        """
        Disable configurations by setting their enabled field to 'false'.
        
        SAFETY: Uses atomic write to prevent data loss during concurrent access.
        Preserves ALL lines including comments and empty rows.
        
        Args:
            config_ids: Set or list of config IDs to disable
        """
        if not os.path.exists(self.config_file):
            return
        
        if not config_ids:
            return
        
        # Convert to set for efficient lookup
        config_ids_set = set(config_ids)
        
        # Read all rows using the preserving method
        fieldnames, all_rows = self._read_csv_preserving_all_lines(self.config_file)
        
        if not fieldnames:
            return
        
        # Disable matching rows while preserving all others
        for row in all_rows:
            if row.get('id') in config_ids_set:
                row['enabled'] = 'false'
        
        # Write atomically to prevent data loss
        self._atomic_write_csv(self.config_file, fieldnames, all_rows)
