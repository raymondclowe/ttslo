"""
Configuration and state management using CSV files.
"""
import csv
import os
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
        
    def load_config(self):
        """
        Load configuration from CSV file.
        
        Returns:
            List of configuration dictionaries
        """
        if not os.path.exists(self.config_file):
            return []
            
        configs = []
        with open(self.config_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip comment lines or empty rows
                if not row or row.get('pair', '').startswith('#'):
                    continue
                configs.append(row)
        return configs
    
    def load_state(self):
        """
        Load state from CSV file.
        
        Returns:
            Dictionary mapping config IDs to their state
        """
        if not os.path.exists(self.state_file):
            return {}
            
        state = {}
        with open(self.state_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('id'):
                    state[row['id']] = row
        return state
    
    def save_state(self, state):
        """
        Save state to CSV file.
        
        Args:
            state: Dictionary mapping config IDs to their state
        """
        if not state:
            return
            
        fieldnames = ['id', 'triggered', 'trigger_price', 'trigger_time', 'order_id', 'last_checked']
        
        with open(self.state_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for config_id, config_state in state.items():
                writer.writerow(config_state)
    
    def log(self, level, message, **kwargs):
        """
        Log a message to the CSV log file.
        
        Args:
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Log message
            **kwargs: Additional fields to include in log
        """
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
                           'volume', 'trailing_offset_percent', 'enabled', 'activate_on'])
            
            # Write example rows
            writer.writerow(['btc_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true', ''])
            writer.writerow(['eth_1', 'XETHZUSD', '3000', 'above', 'sell', '0.1', '3.5', 'true', ''])
            writer.writerow(['# Example: Trigger sell TSL when BTC goes above $50k with 5% trailing offset', '', '', '', '', '', '', '', ''])
            writer.writerow(['# id: Unique identifier for this configuration', '', '', '', '', '', '', '', ''])
            writer.writerow(['# pair: Kraken trading pair (XXBTZUSD for BTC/USD, XETHZUSD for ETH/USD)', '', '', '', '', '', '', '', ''])
            writer.writerow(['# threshold_price: Price threshold that triggers the TSL order', '', '', '', '', '', '', '', ''])
            writer.writerow(['# threshold_type: "above" or "below" - condition for threshold', '', '', '', '', '', '', '', ''])
            writer.writerow(['# direction: "buy" or "sell" - direction of TSL order', '', '', '', '', '', '', '', ''])
            writer.writerow(['# volume: Amount to trade', '', '', '', '', '', '', '', ''])
            writer.writerow(['# trailing_offset_percent: Trailing stop offset as percentage (e.g., 5.0 for 5%)', '', '', '', '', '', '', '', ''])
            writer.writerow(['# enabled: "true" or "false" - whether this config is active', '', '', '', '', '', '', '', ''])
            writer.writerow(['# activate_on: Optional ISO datetime (YYYY-MM-DDTHH:MM:SS) - only activate after this time', '', '', '', '', '', '', '', ''])
    
    def initialize_state_file(self):
        """Initialize an empty state file with headers."""
        fieldnames = ['id', 'triggered', 'trigger_price', 'trigger_time', 'order_id', 'last_checked']
        
        with open(self.state_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
