#!/usr/bin/env python3
"""
TTSLO - Triggered Trailing Stop Loss Orders for Kraken

Monitors cryptocurrency prices and creates trailing stop loss orders
when specified price thresholds are reached.
"""
import argparse
import os
import sys
import time
from datetime import datetime, timezone

from kraken_api import KrakenAPI
from config import ConfigManager


def get_env_var(var_name):
    """
    Get environment variable, checking both standard and copilot_ prefixed versions.
    
    Args:
        var_name: Name of the environment variable
        
    Returns:
        Value of the environment variable or None if not found
    """
    # First check the standard name
    value = os.environ.get(var_name)
    if value:
        return value
    
    # Then check with copilot_ prefix for GitHub Copilot agent environments
    copilot_var_name = f"copilot_{var_name}"
    return os.environ.get(copilot_var_name)


def load_env_file(env_file='.env'):
    """
    Load environment variables from a .env file if it exists.
    
    Args:
        env_file: Path to .env file
    """
    if not os.path.exists(env_file):
        return
    
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}", file=sys.stderr)


class TTSLO:
    """Main application for triggered trailing stop loss orders."""
    
    def __init__(self, config_manager, kraken_api_readonly, kraken_api_readwrite=None, 
                 dry_run=False, verbose=False):
        """
        Initialize TTSLO application.
        
        Args:
            config_manager: ConfigManager instance
            kraken_api_readonly: KrakenAPI instance with read-only credentials
            kraken_api_readwrite: KrakenAPI instance with read-write credentials (optional)
            dry_run: If True, don't actually create orders
            verbose: If True, print verbose output
        """
        self.config_manager = config_manager
        self.kraken_api_readonly = kraken_api_readonly
        self.kraken_api_readwrite = kraken_api_readwrite
        self.dry_run = dry_run
        self.verbose = verbose
        self.state = {}
        
    def log(self, level, message, **kwargs):
        """
        Log a message.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional fields
        """
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {level}: {message}"
        
        if self.verbose or level in ['ERROR', 'WARNING']:
            print(log_msg)
            
        self.config_manager.log(level, message, **kwargs)
    
    def load_state(self):
        """Load state from file."""
        self.state = self.config_manager.load_state()
        self.log('DEBUG', f'Loaded state for {len(self.state)} configurations')
    
    def save_state(self):
        """Save state to file."""
        self.config_manager.save_state(self.state)
        self.log('DEBUG', f'Saved state for {len(self.state)} configurations')
    
    def check_threshold(self, config, current_price):
        """
        Check if price threshold has been met.
        
        Args:
            config: Configuration dictionary
            current_price: Current price
            
        Returns:
            True if threshold is met, False otherwise
        """
        threshold_price = float(config['threshold_price'])
        threshold_type = config['threshold_type'].lower()
        
        if threshold_type == 'above':
            return current_price >= threshold_price
        elif threshold_type == 'below':
            return current_price <= threshold_price
        else:
            self.log('ERROR', f"Invalid threshold_type: {threshold_type}", config_id=config['id'])
            return False
    
    def create_tsl_order(self, config, trigger_price):
        """
        Create a trailing stop loss order.
        
        Args:
            config: Configuration dictionary
            trigger_price: Price at which threshold was triggered
            
        Returns:
            Order ID if successful, None otherwise
        """
        config_id = config['id']
        pair = config['pair']
        direction = config['direction']
        volume = config['volume']
        trailing_offset = float(config['trailing_offset_percent'])
        
        if self.dry_run:
            self.log('INFO', 
                    f"[DRY RUN] Would create TSL order: pair={pair}, direction={direction}, "
                    f"volume={volume}, trailing_offset={trailing_offset}%",
                    config_id=config_id, trigger_price=trigger_price)
            return 'DRY_RUN_ORDER_ID'
        
        # Check if we have read-write API credentials
        if not self.kraken_api_readwrite:
            self.log('ERROR', 
                    f"Cannot create TSL order: No read-write API credentials available. "
                    f"Set KRAKEN_API_KEY_RW and KRAKEN_API_SECRET_RW environment variables.",
                    config_id=config_id, trigger_price=trigger_price)
            print(f"ERROR: Cannot create order for {config_id}: Missing read-write API credentials")
            return None
        
        try:
            self.log('INFO', 
                    f"Creating TSL order: pair={pair}, direction={direction}, "
                    f"volume={volume}, trailing_offset={trailing_offset}%",
                    config_id=config_id, trigger_price=trigger_price)
            
            result = self.kraken_api_readwrite.add_trailing_stop_loss(
                pair=pair,
                direction=direction,
                volume=volume,
                trailing_offset_percent=trailing_offset
            )
            
            order_id = result.get('txid', [None])[0]
            
            if order_id:
                self.log('INFO', 
                        f"TSL order created successfully: order_id={order_id}",
                        config_id=config_id, order_id=order_id)
                return order_id
            else:
                self.log('ERROR', 
                        f"Failed to create TSL order: {result}",
                        config_id=config_id)
                return None
                
        except Exception as e:
            error_msg = str(e)
            self.log('ERROR', 
                    f"Exception creating TSL order: {error_msg}",
                    config_id=config_id, error=error_msg)
            
            # Check if error is related to API permissions
            if 'permission' in error_msg.lower() or 'invalid key' in error_msg.lower():
                print(f"ERROR: API credentials may not have proper permissions for creating orders. "
                      f"Check that KRAKEN_API_KEY_RW has 'Create & Modify Orders' permission.")
            
            return None
    
    def process_config(self, config):
        """
        Process a single configuration entry.
        
        Args:
            config: Configuration dictionary
        """
        config_id = config['id']
        
        # Check if config is enabled
        if config.get('enabled', 'true').lower() != 'true':
            self.log('DEBUG', f"Config {config_id} is disabled, skipping")
            return
        
        # Initialize state if not exists
        if config_id not in self.state:
            self.state[config_id] = {
                'id': config_id,
                'triggered': 'false',
                'trigger_price': '',
                'trigger_time': '',
                'order_id': '',
                'last_checked': ''
            }
        
        # Skip if already triggered
        if self.state[config_id].get('triggered', 'false') == 'true':
            self.log('DEBUG', f"Config {config_id} already triggered, skipping")
            return
        
        pair = config['pair']
        
        try:
            # Get current price using read-only API
            current_price = self.kraken_api_readonly.get_current_price(pair)
            self.log('DEBUG', f"Current price for {pair}: {current_price}", 
                    config_id=config_id, pair=pair, price=current_price)
            
            # Update last checked time
            self.state[config_id]['last_checked'] = datetime.now(timezone.utc).isoformat()
            
            # Check if threshold is met
            if self.check_threshold(config, current_price):
                self.log('INFO', 
                        f"Threshold met for {config_id}: current_price={current_price}, "
                        f"threshold={config['threshold_price']} ({config['threshold_type']})",
                        config_id=config_id, pair=pair, price=current_price)
                
                # Create TSL order
                order_id = self.create_tsl_order(config, current_price)
                
                if order_id:
                    # Update state
                    self.state[config_id]['triggered'] = 'true'
                    self.state[config_id]['trigger_price'] = str(current_price)
                    self.state[config_id]['trigger_time'] = datetime.now(timezone.utc).isoformat()
                    self.state[config_id]['order_id'] = order_id
                    
                    self.log('INFO', 
                            f"Successfully triggered config {config_id}",
                            config_id=config_id, order_id=order_id)
            
        except Exception as e:
            self.log('ERROR', 
                    f"Error processing config {config_id}: {str(e)}",
                    config_id=config_id, error=str(e))
    
    def run_once(self):
        """Run one iteration of checking all configurations."""
        configs = self.config_manager.load_config()
        
        if not configs:
            self.log('WARNING', 'No configurations found in config file')
            return
        
        self.log('INFO', f'Processing {len(configs)} configurations')
        
        for config in configs:
            self.process_config(config)
        
        # Save state after processing all configs
        self.save_state()
    
    def run_continuous(self, interval=60):
        """
        Run continuously, checking configurations at regular intervals.
        
        Args:
            interval: Seconds between checks
        """
        self.log('INFO', f'Starting continuous monitoring (interval: {interval}s)')
        
        try:
            while True:
                self.run_once()
                self.log('DEBUG', f'Sleeping for {interval} seconds')
                time.sleep(interval)
        except KeyboardInterrupt:
            self.log('INFO', 'Interrupted by user, shutting down')
            sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='TTSLO - Triggered Trailing Stop Loss Orders for Kraken',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once in dry-run mode with verbose output
  %(prog)s --dry-run --verbose --once
  
  # Run continuously with 60 second intervals
  %(prog)s --interval 60
  
  # Create sample configuration file
  %(prog)s --create-sample-config
  
Environment variables:
  KRAKEN_API_KEY       Kraken read-only API key
  KRAKEN_API_SECRET    Kraken read-only API secret
  KRAKEN_API_KEY_RW    Kraken read-write API key (for creating orders)
  KRAKEN_API_SECRET_RW Kraken read-write API secret (for creating orders)
  
  Note: Each variable will also be checked with 'copilot_' prefix for 
        GitHub Copilot agent environments (e.g., copilot_KRAKEN_API_KEY)
        """
    )
    
    parser.add_argument('--config', default='config.csv',
                       help='Configuration file (default: config.csv)')
    parser.add_argument('--state', default='state.csv',
                       help='State file (default: state.csv)')
    parser.add_argument('--log', default='logs.csv',
                       help='Log file (default: logs.csv)')
    parser.add_argument('--dry-run', action='store_true',
                       help="Don't actually create orders")
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output')
    parser.add_argument('--once', action='store_true',
                       help='Run once and exit (default: run continuously)')
    parser.add_argument('--interval', type=int, default=60,
                       help='Seconds between checks in continuous mode (default: 60)')
    parser.add_argument('--create-sample-config', action='store_true',
                       help='Create a sample configuration file and exit')
    parser.add_argument('--env-file', default='.env',
                       help='Path to .env file (default: .env)')
    
    args = parser.parse_args()
    
    # Load .env file if it exists
    load_env_file(args.env_file)
    
    # Create sample config if requested
    if args.create_sample_config:
        config_manager = ConfigManager()
        config_manager.create_sample_config()
        print(f"Sample configuration file created: config_sample.csv")
        sys.exit(0)
    
    # Get read-only API credentials (for price monitoring)
    api_key_ro = get_env_var('KRAKEN_API_KEY')
    api_secret_ro = get_env_var('KRAKEN_API_SECRET')
    
    # Get read-write API credentials (for creating orders)
    api_key_rw = get_env_var('KRAKEN_API_KEY_RW')
    api_secret_rw = get_env_var('KRAKEN_API_SECRET_RW')
    
    # Check if we have at least read-only credentials
    if not api_key_ro or not api_secret_ro:
        print("ERROR: Read-only API credentials required. Set KRAKEN_API_KEY and KRAKEN_API_SECRET "
              "environment variables.", 
              file=sys.stderr)
        print("Use --dry-run to test without credentials.", file=sys.stderr)
        sys.exit(1)
    
    # Warn if we don't have read-write credentials and not in dry-run mode
    has_rw_creds = api_key_rw and api_secret_rw
    if not args.dry_run and not has_rw_creds:
        print("WARNING: No read-write API credentials found. Orders cannot be created.", file=sys.stderr)
        print("Set KRAKEN_API_KEY_RW and KRAKEN_API_SECRET_RW to enable order creation.", file=sys.stderr)
        print("Continuing in read-only mode...\n", file=sys.stderr)
    
    # Initialize components
    config_manager = ConfigManager(
        config_file=args.config,
        state_file=args.state,
        log_file=args.log
    )
    
    # Create read-only API instance
    kraken_api_readonly = KrakenAPI(api_key=api_key_ro, api_secret=api_secret_ro)
    
    # Create read-write API instance if credentials are available
    kraken_api_readwrite = None
    if has_rw_creds:
        kraken_api_readwrite = KrakenAPI(api_key=api_key_rw, api_secret=api_secret_rw)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=kraken_api_readonly,
        kraken_api_readwrite=kraken_api_readwrite,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    # Load initial state
    ttslo.load_state()
    
    # Run
    if args.once:
        ttslo.run_once()
    else:
        ttslo.run_continuous(interval=args.interval)


if __name__ == '__main__':
    main()
