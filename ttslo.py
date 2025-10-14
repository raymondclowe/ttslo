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
from validator import ConfigValidator, format_validation_result


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
        
        SECURITY NOTE: This function will return False (do not trigger) if:
        - Any required parameter is missing or invalid
        - The threshold_type is not recognized
        - Any error occurs during comparison
        
        Returns False (safe default) on any uncertainty.
        
        Args:
            config: Configuration dictionary
            current_price: Current price
            
        Returns:
            True if threshold is met, False otherwise (False = do not trigger order)
        """
        # Step 1: Validate config parameter
        if not isinstance(config, dict):
            # SAFETY: Invalid config type - return False (do not trigger)
            self.log('ERROR', 'check_threshold: config is not a dictionary')
            return False
        
        # Step 2: Get config_id for logging
        config_id = config.get('id', 'unknown')
        
        # Step 3: Validate current_price
        if current_price is None:
            # SAFETY: No price data - return False (do not trigger)
            self.log('ERROR', 'check_threshold: current_price is None',
                    config_id=config_id)
            return False
        
        # Step 4: Convert current_price to float and validate
        try:
            current_price_float = float(current_price)
        except (ValueError, TypeError) as e:
            # SAFETY: Cannot convert price to float - return False (do not trigger)
            self.log('ERROR', 
                    f'check_threshold: current_price "{current_price}" is not a valid number',
                    config_id=config_id, error=str(e))
            return False
        
        # Step 5: Validate price is positive
        if current_price_float <= 0:
            # SAFETY: Invalid price - return False (do not trigger)
            self.log('ERROR', 
                    f'check_threshold: current_price must be positive, got {current_price_float}',
                    config_id=config_id)
            return False
        
        # Step 6: Get threshold_price from config
        threshold_price_str = config.get('threshold_price')
        if not threshold_price_str:
            # SAFETY: Missing threshold_price - return False (do not trigger)
            self.log('ERROR', 'check_threshold: threshold_price is missing',
                    config_id=config_id)
            return False
        
        # Step 7: Convert threshold_price to float
        try:
            threshold_price = float(threshold_price_str)
        except (ValueError, TypeError) as e:
            # SAFETY: Cannot convert threshold_price - return False (do not trigger)
            self.log('ERROR', 
                    f'check_threshold: threshold_price "{threshold_price_str}" is not a valid number',
                    config_id=config_id, error=str(e))
            return False
        
        # Step 8: Validate threshold_price is positive
        if threshold_price <= 0:
            # SAFETY: Invalid threshold - return False (do not trigger)
            self.log('ERROR', 
                    f'check_threshold: threshold_price must be positive, got {threshold_price}',
                    config_id=config_id)
            return False
        
        # Step 9: Get threshold_type from config
        threshold_type_raw = config.get('threshold_type')
        if not threshold_type_raw:
            # SAFETY: Missing threshold_type - return False (do not trigger)
            self.log('ERROR', 'check_threshold: threshold_type is missing',
                    config_id=config_id)
            return False
        
        # Step 10: Normalize threshold_type to lowercase
        threshold_type = threshold_type_raw.strip().lower()
        
        # Step 11: Check threshold based on type
        if threshold_type == 'above':
            # For 'above': trigger when current price >= threshold price
            is_met = current_price_float >= threshold_price
            return is_met
        elif threshold_type == 'below':
            # For 'below': trigger when current price <= threshold price
            is_met = current_price_float <= threshold_price
            return is_met
        else:
            # SAFETY: Unknown threshold_type - return False (do not trigger)
            self.log('ERROR', 
                    f'check_threshold: invalid threshold_type "{threshold_type}". '
                    f'Must be "above" or "below"',
                    config_id=config_id)
            return False
    
    def create_tsl_order(self, config, trigger_price):
        """
        Create a trailing stop loss order.
        
        SECURITY NOTE: This function will NEVER create an order if:
        - Any required parameter is missing or invalid
        - We are in dry-run mode (returns dummy ID instead)
        - API credentials are not available
        - Any exception occurs during validation or order creation
        
        Args:
            config: Configuration dictionary
            trigger_price: Price at which threshold was triggered
            
        Returns:
            Order ID if successful, None otherwise (None = no order created)
        """
        # Step 1: Extract and validate config ID
        # We need the config_id for logging, so extract it first
        config_id = config.get('id')
        if not config_id:
            # SAFETY: If we don't have a config ID, we cannot proceed safely
            self.log('ERROR', 'Cannot create order: config ID is missing')
            return None
        
        # Step 2: Validate that config parameter is a dictionary
        if not isinstance(config, dict):
            # SAFETY: Invalid config type - do not create order
            self.log('ERROR', 'Cannot create order: config is not a dictionary',
                    config_id=config_id)
            return None
        
        # Step 3: Extract all required parameters from config
        # Extract each parameter separately with explicit checks
        pair = config.get('pair')
        direction = config.get('direction')
        volume = config.get('volume')
        trailing_offset_str = config.get('trailing_offset_percent')
        
        # Step 4: Validate ALL required parameters are present
        # SAFETY: If any parameter is missing, do not create order
        if not pair:
            self.log('ERROR', 'Cannot create order: pair is missing',
                    config_id=config_id)
            return None
        
        if not direction:
            self.log('ERROR', 'Cannot create order: direction is missing',
                    config_id=config_id)
            return None
        
        if not volume:
            self.log('ERROR', 'Cannot create order: volume is missing',
                    config_id=config_id)
            return None
        
        if not trailing_offset_str:
            self.log('ERROR', 'Cannot create order: trailing_offset_percent is missing',
                    config_id=config_id)
            return None
        
        # Step 5: Validate trailing_offset can be converted to float
        # SAFETY: If conversion fails, do not create order
        try:
            trailing_offset = float(trailing_offset_str)
        except (ValueError, TypeError) as e:
            self.log('ERROR', 
                    f'Cannot create order: trailing_offset_percent "{trailing_offset_str}" is not a valid number',
                    config_id=config_id, error=str(e))
            return None
        
        # Step 6: Validate trailing_offset is positive
        # SAFETY: Negative or zero trailing offset is invalid
        if trailing_offset <= 0:
            self.log('ERROR', 
                    f'Cannot create order: trailing_offset_percent must be positive, got {trailing_offset}',
                    config_id=config_id)
            return None
        
        # Step 7: Validate trigger_price
        # SAFETY: trigger_price must be valid
        if trigger_price is None:
            self.log('ERROR', 'Cannot create order: trigger_price is None',
                    config_id=config_id)
            return None
        
        try:
            trigger_price_float = float(trigger_price)
            if trigger_price_float <= 0:
                self.log('ERROR', 
                        f'Cannot create order: trigger_price must be positive, got {trigger_price_float}',
                        config_id=config_id)
                return None
        except (ValueError, TypeError) as e:
            self.log('ERROR', 
                    f'Cannot create order: trigger_price "{trigger_price}" is not a valid number',
                    config_id=config_id, error=str(e))
            return None
        
        # Step 8: Check if we are in dry-run mode
        # In dry-run mode, we DO NOT create real orders
        if self.dry_run:
            self.log('INFO', 
                    f"[DRY RUN] Would create TSL order: pair={pair}, direction={direction}, "
                    f"volume={volume}, trailing_offset={trailing_offset}%",
                    config_id=config_id, trigger_price=trigger_price)
            # Return dummy ID to indicate dry-run success
            return 'DRY_RUN_ORDER_ID'
        
        # Step 9: Check if we have read-write API credentials
        # SAFETY: Without credentials, we CANNOT create orders
        if not self.kraken_api_readwrite:
            self.log('ERROR', 
                    f"Cannot create TSL order: No read-write API credentials available. "
                    f"Set KRAKEN_API_KEY_RW and KRAKEN_API_SECRET_RW environment variables.",
                    config_id=config_id, trigger_price=trigger_price)
            print(f"ERROR: Cannot create order for {config_id}: Missing read-write API credentials")
            # Return None to indicate no order was created
            return None
        
        # Step 10: Log that we are about to create a real order
        self.log('INFO', 
                f"Creating TSL order: pair={pair}, direction={direction}, "
                f"volume={volume}, trailing_offset={trailing_offset}%",
                config_id=config_id, trigger_price=trigger_price)
        
        # Step 11: Attempt to create the order via API
        # Wrap in try-except to catch ANY errors
        try:
            # Call the Kraken API to create the trailing stop loss order
            result = self.kraken_api_readwrite.add_trailing_stop_loss(
                pair=pair,
                direction=direction,
                volume=volume,
                trailing_offset_percent=trailing_offset
            )
        except Exception as e:
            # SAFETY: If API call raises exception, do not proceed
            error_msg = str(e)
            self.log('ERROR', 
                    f"Exception creating TSL order: {error_msg}",
                    config_id=config_id, error=error_msg)
            
            # Check if error is related to API permissions
            if 'permission' in error_msg.lower() or 'invalid key' in error_msg.lower():
                print(f"ERROR: API credentials may not have proper permissions for creating orders. "
                      f"Check that KRAKEN_API_KEY_RW has 'Create & Modify Orders' permission.")
            
            # Return None to indicate order was NOT created
            return None
        
        # Step 12: Validate the API response
        # SAFETY: Ensure result is a dictionary before accessing
        if not isinstance(result, dict):
            self.log('ERROR', 
                    f"Invalid API response: expected dictionary, got {type(result)}",
                    config_id=config_id)
            return None
        
        # Step 13: Extract order ID from result
        # The txid field should contain a list of transaction IDs
        txid_list = result.get('txid')
        
        # Validate txid_list exists and is a list
        if not txid_list or not isinstance(txid_list, list):
            self.log('ERROR', 
                    f"Failed to create TSL order: no transaction ID in response: {result}",
                    config_id=config_id)
            return None
        
        # Get the first order ID from the list
        if len(txid_list) > 0:
            order_id = txid_list[0]
        else:
            # SAFETY: Empty txid list means no order was created
            self.log('ERROR', 
                    f"Failed to create TSL order: empty transaction ID list: {result}",
                    config_id=config_id)
            return None
        
        # Step 14: Validate order_id is not None or empty
        if not order_id:
            self.log('ERROR', 
                    f"Failed to create TSL order: order ID is empty: {result}",
                    config_id=config_id)
            return None
        
        # Step 15: Order created successfully - log and return
        self.log('INFO', 
                f"TSL order created successfully: order_id={order_id}",
                config_id=config_id, order_id=order_id)
        return order_id
    
    def process_config(self, config):
        """
        Process a single configuration entry.
        
        SECURITY NOTE: This function will NOT create orders if:
        - Config is not a valid dictionary
        - Config ID is missing
        - Config is disabled
        - Config has already been triggered
        - Any error occurs while fetching price or checking threshold
        - Threshold is not met
        - Order creation fails
        
        Args:
            config: Configuration dictionary
        """
        # Step 1: Validate config parameter
        if not isinstance(config, dict):
            # SAFETY: Invalid config - do not process
            self.log('ERROR', 'process_config: config is not a dictionary')
            return
        
        # Step 2: Get and validate config_id
        config_id = config.get('id')
        if not config_id:
            # SAFETY: No config ID - do not process
            self.log('ERROR', 'process_config: config ID is missing')
            return
        
        # Step 3: Check if config is enabled
        # Get the 'enabled' field, defaulting to 'true' if not present
        enabled_value = config.get('enabled', 'true')
        if not enabled_value:
            enabled_value = 'true'
        
        # Normalize to lowercase for comparison
        enabled_normalized = enabled_value.strip().lower()
        
        # Check if config is enabled
        # SAFETY: Only process enabled configs
        if enabled_normalized != 'true':
            self.log('DEBUG', f"Config {config_id} is disabled, skipping")
            # Do not process disabled configs - this is safe
            return
        
        # Step 4: Initialize state if not exists
        if config_id not in self.state:
            # Create initial state for this config
            self.state[config_id] = {
                'id': config_id,
                'triggered': 'false',
                'trigger_price': '',
                'trigger_time': '',
                'order_id': '',
                'last_checked': ''
            }
        
        # Step 5: Check if config has already been triggered
        # SAFETY: Do not trigger twice - this prevents duplicate orders
        triggered_value = self.state[config_id].get('triggered', 'false')
        if triggered_value == 'true':
            self.log('DEBUG', f"Config {config_id} already triggered, skipping")
            # Do not process already triggered configs - this prevents duplicate orders
            return
        
        # Step 6: Get the trading pair
        pair = config.get('pair')
        if not pair:
            # SAFETY: No trading pair - do not process
            self.log('ERROR', f"Config {config_id} has no trading pair, skipping",
                    config_id=config_id)
            return
        
        # Step 7: Attempt to get current price
        # Wrap in try-except to handle any API errors
        try:
            # Use read-only API to get current price
            current_price = self.kraken_api_readonly.get_current_price(pair)
        except Exception as e:
            # SAFETY: Cannot get price - do not process
            self.log('ERROR', 
                    f"Error getting current price for {pair}: {str(e)}",
                    config_id=config_id, pair=pair, error=str(e))
            # Return without creating order - this is safe
            return
        
        # Step 8: Validate current_price
        if current_price is None:
            # SAFETY: No price data - do not process
            self.log('ERROR', 
                    f"Could not get current price for {pair}",
                    config_id=config_id, pair=pair)
            return
        
        # Step 9: Log the current price
        self.log('DEBUG', f"Current price for {pair}: {current_price}", 
                config_id=config_id, pair=pair, price=current_price)
        
        # Step 10: Update last checked time
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            self.state[config_id]['last_checked'] = current_time
        except Exception as e:
            # Log error but continue - this doesn't affect order logic
            self.log('WARNING', 
                    f"Could not update last_checked time: {str(e)}",
                    config_id=config_id, error=str(e))
        
        # Step 11: Check if threshold is met
        # This returns False if anything is wrong, so it's safe
        threshold_is_met = self.check_threshold(config, current_price)
        
        # Step 12: Decide whether to create order
        if threshold_is_met:
            # Threshold is met - log it
            threshold_price = config.get('threshold_price', 'unknown')
            threshold_type = config.get('threshold_type', 'unknown')
            
            self.log('INFO', 
                    f"Threshold met for {config_id}: current_price={current_price}, "
                    f"threshold={threshold_price} ({threshold_type})",
                    config_id=config_id, pair=pair, price=current_price)
            
            # Step 13: Attempt to create TSL order
            order_id = self.create_tsl_order(config, current_price)
            
            # Step 14: Check if order was created successfully
            if order_id:
                # Order created successfully - update state
                try:
                    trigger_time = datetime.now(timezone.utc).isoformat()
                    self.state[config_id]['triggered'] = 'true'
                    self.state[config_id]['trigger_price'] = str(current_price)
                    self.state[config_id]['trigger_time'] = trigger_time
                    self.state[config_id]['order_id'] = order_id
                    
                    self.log('INFO', 
                            f"Successfully triggered config {config_id}",
                            config_id=config_id, order_id=order_id)
                except Exception as e:
                    # Log error updating state, but order was created
                    self.log('ERROR', 
                            f"Order created but failed to update state: {str(e)}",
                            config_id=config_id, order_id=order_id, error=str(e))
            else:
                # Order creation failed - order_id is None
                # Log that order was not created
                self.log('WARNING', 
                        f"Threshold was met but order creation failed for {config_id}",
                        config_id=config_id)
                # Do NOT mark as triggered - allow retry on next iteration
        else:
            # Threshold not met - this is normal, do nothing
            # No need to log at INFO level to reduce noise
            pass
    
    def validate_and_load_config(self) -> bool:
        """
        Validate configuration file and load configs if valid.
        
        Returns:
            True if validation passed, False otherwise
        """
        configs = self.config_manager.load_config()
        
        if not configs:
            self.log('ERROR', 'No configurations found in config file')
            return False
        
        # Validate configuration with market price checks
        validator = ConfigValidator(kraken_api=self.kraken_api_readonly)
        result = validator.validate_config_file(configs)
        
        # Log validation results
        if result.errors:
            for error in result.errors:
                self.log('ERROR', 
                        f"Config validation error [{error['config_id']}] {error['field']}: {error['message']}",
                        config_id=error['config_id'], field=error['field'])
        
        if result.warnings:
            for warning in result.warnings:
                self.log('WARNING', 
                        f"Config validation warning [{warning['config_id']}] {warning['field']}: {warning['message']}",
                        config_id=warning['config_id'], field=warning['field'])
        
        if not result.is_valid():
            self.log('ERROR', 'Configuration validation failed. Please fix errors.')
            return False
        
        if result.has_warnings() and self.verbose:
            print("Configuration has warnings. Review them to ensure they are expected.")
        
        return True
    
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
  # Validate configuration file
  %(prog)s --validate-config
  
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
    parser.add_argument('--validate-config', action='store_true',
                       help='Validate configuration file and exit (shows what will be executed)')
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
    
    # Validate config if requested
    if args.validate_config:
        config_manager = ConfigManager(config_file=args.config)
        configs = config_manager.load_config()
        
        if not configs:
            print("ERROR: No configurations found in config file", file=sys.stderr)
            print(f"Config file: {args.config}", file=sys.stderr)
            sys.exit(1)
        
        # Try to get API credentials for market price validation
        api_key_ro = get_env_var('KRAKEN_API_KEY')
        api_secret_ro = get_env_var('KRAKEN_API_SECRET')
        
        # Create API instance if credentials available
        kraken_api = None
        if api_key_ro and api_secret_ro:
            kraken_api = KrakenAPI(api_key=api_key_ro, api_secret=api_secret_ro)
            print("Note: Validating with current market prices from Kraken API\n")
        else:
            print("Note: API credentials not found. Skipping market price validation.")
            print("      Set KRAKEN_API_KEY and KRAKEN_API_SECRET for complete validation.\n")
        
        validator = ConfigValidator(kraken_api=kraken_api)
        result = validator.validate_config_file(configs)
        
        # Print formatted validation result
        print(format_validation_result(result, verbose=True))
        
        # Exit with appropriate code
        sys.exit(0 if result.is_valid() else 1)
    
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
    
    # Validate configuration before starting
    if not ttslo.validate_and_load_config():
        print("\nConfiguration validation failed. Use --validate-config to see details.", 
              file=sys.stderr)
        sys.exit(1)
    
    if args.verbose:
        print("Configuration validation passed. Starting monitoring...\n")
    
    # Run
    if args.once:
        ttslo.run_once()
    else:
        ttslo.run_continuous(interval=args.interval)


if __name__ == '__main__':
    main()
