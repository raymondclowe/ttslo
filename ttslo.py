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


class TTSLO:
    """Main application for triggered trailing stop loss orders."""
    
    def __init__(self, config_manager, kraken_api, dry_run=False, verbose=False):
        """
        Initialize TTSLO application.
        
        Args:
            config_manager: ConfigManager instance
            kraken_api: KrakenAPI instance
            dry_run: If True, don't actually create orders
            verbose: If True, print verbose output
        """
        self.config_manager = config_manager
        self.kraken_api = kraken_api
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
        
        try:
            self.log('INFO', 
                    f"Creating TSL order: pair={pair}, direction={direction}, "
                    f"volume={volume}, trailing_offset={trailing_offset}%",
                    config_id=config_id, trigger_price=trigger_price)
            
            result = self.kraken_api.add_trailing_stop_loss(
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
            self.log('ERROR', 
                    f"Exception creating TSL order: {str(e)}",
                    config_id=config_id, error=str(e))
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
            # Get current price
            current_price = self.kraken_api.get_current_price(pair)
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
  KRAKEN_API_KEY      Kraken API key
  KRAKEN_API_SECRET   Kraken API secret
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
    parser.add_argument('--api-key', 
                       help='Kraken API key (or set KRAKEN_API_KEY env var)')
    parser.add_argument('--api-secret',
                       help='Kraken API secret (or set KRAKEN_API_SECRET env var)')
    
    args = parser.parse_args()
    
    # Create sample config if requested
    if args.create_sample_config:
        config_manager = ConfigManager()
        config_manager.create_sample_config()
        print(f"Sample configuration file created: config_sample.csv")
        sys.exit(0)
    
    # Get API credentials
    api_key = args.api_key or os.environ.get('KRAKEN_API_KEY')
    api_secret = args.api_secret or os.environ.get('KRAKEN_API_SECRET')
    
    if not args.dry_run and (not api_key or not api_secret):
        print("ERROR: API credentials required. Set KRAKEN_API_KEY and KRAKEN_API_SECRET "
              "environment variables or use --api-key and --api-secret options.", 
              file=sys.stderr)
        print("Use --dry-run to test without credentials.", file=sys.stderr)
        sys.exit(1)
    
    # Initialize components
    config_manager = ConfigManager(
        config_file=args.config,
        state_file=args.state,
        log_file=args.log
    )
    
    kraken_api = KrakenAPI(api_key=api_key, api_secret=api_secret)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api=kraken_api,
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
