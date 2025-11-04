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
import signal
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, getcontext

from kraken_api import (
    KrakenAPI, KrakenAPIError, KrakenAPITimeoutError, 
    KrakenAPIConnectionError, KrakenAPIServerError, KrakenAPIRateLimitError
)
from config import ConfigManager
from validator import ConfigValidator, format_validation_result
from creds import load_env, find_kraken_credentials, get_env_var
from notifications import NotificationManager


# Use centralized creds helpers (load .env and lookup variants)
def load_env_file(env_file='.env'):
    load_env(env_file)


class TTSLO:
    """Main application for triggered trailing stop loss orders."""
    
    def __init__(self, config_manager, kraken_api_readonly, kraken_api_readwrite=None, 
                 dry_run=False, verbose=False, debug=False, notification_manager=None):
        """
        Initialize TTSLO application.
        
        Args:
            config_manager: ConfigManager instance
            kraken_api_readonly: KrakenAPI instance with read-only credentials
            kraken_api_readwrite: KrakenAPI instance with read-write credentials (optional)
            dry_run: If True, don't actually create orders
            verbose: If True, print verbose output
            notification_manager: NotificationManager instance (optional)
        """
        self.config_manager = config_manager
        self.kraken_api_readonly = kraken_api_readonly
        self.kraken_api_readwrite = kraken_api_readwrite
        self.dry_run = dry_run
        self.verbose = verbose
        # debug mode enables very verbose, comparison-focused messages
        self.debug = debug
        self.notification_manager = notification_manager
        self.state = {}
        # Store configs in memory - loaded once at startup, not reloaded during runtime
        self.configs = None
        
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
        
        # Print messages when verbose or debug is enabled, or for warnings/errors
        if self.verbose or self.debug or level in ['ERROR', 'WARNING']:
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
            if self.debug:
                if is_met:
                    self.log('DEBUG', f"{current_price_float} >= {threshold_price} -> threshold met",
                             config_id=config_id)
                else:
                    self.log('DEBUG', f"{current_price_float} is not greater than or equal to {threshold_price} therefore nothing to do",
                             config_id=config_id)
            return is_met
        elif threshold_type == 'below':
            # For 'below': trigger when current price <= threshold price
            is_met = current_price_float <= threshold_price
            if self.debug:
                if is_met:
                    self.log('DEBUG', f"{current_price_float} <= {threshold_price} -> threshold met",
                             config_id=config_id)
                else:
                    self.log('DEBUG', f"{current_price_float} is not less than or equal to {threshold_price} therefore nothing to do",
                             config_id=config_id)
            return is_met
        else:
            # SAFETY: Unknown threshold_type - return False (do not trigger)
            self.log('ERROR', 
                    f'check_threshold: invalid threshold_type "{threshold_type}". '
                    f'Must be "above" or "below"',
                    config_id=config_id)
            return False
    
    def _normalize_asset(self, asset: str) -> str:
        """
        Normalize asset key by removing X prefix and .F suffix.
        
        Examples:
            'XXBT' -> 'BT'
            'XBT.F' -> 'BT'
            
        Args:
            asset: Asset key from Kraken API
            
        Returns:
            Normalized asset key
        """
        if not asset:
            return ''
        asset = asset.upper().strip()
        # Remove funding suffix
        if asset.endswith('.F'):
            asset = asset[:-2]
        # Strip leading X or Z characters commonly used by Kraken
        asset = asset.lstrip('XZ')
        return asset
    
    def _extract_base_asset(self, pair: str) -> str:
        """
        Extract the base asset from a trading pair.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD', 'XETHZUSD', 'DYDXUSD')
            
        Returns:
            Base asset code (e.g., 'XXBT', 'XETH', 'DYDX') or empty string if can't determine
        """
        # Known mappings for common pairs
        pair_mappings = {
            'XBTUSDT': 'XXBT',
            'XBTUSD': 'XXBT',
            'XXBTZEUR': 'XXBT',
            'XXBTZGBP': 'XXBT',
            'XXBTZUSD': 'XXBT',
            'ETHUSDT': 'XETH',
            'ETHUSD': 'XETH',
            'XETHZEUR': 'XETH',
            'XETHZUSD': 'XETH',
            'SOLUSDT': 'SOL',
            'SOLEUR': 'SOL',
            'ADAUSDT': 'ADA',
            'DOTUSDT': 'DOT',
            'AVAXUSDT': 'AVAX',
            'LINKUSDT': 'LINK',
        }
        
        # Check if we have a known mapping
        if pair in pair_mappings:
            return pair_mappings[pair]
        
        # Try to extract from pattern
        # Note: Order matters - check longer suffixes first (e.g., USDT before USD)
        for quote in ['USDT', 'ZUSD', 'ZEUR', 'EUR', 'ZGBP', 'GBP', 'ZJPY', 'JPY', 'USD']:
            if pair.endswith(quote):
                base = pair[:-len(quote)]
                if base:
                    return base
        
        return ''
    
    def check_minimum_volume(self, pair: str, volume: float, config_id: str = None) -> tuple:
        """
        Check if the volume meets Kraken's minimum order size for the pair.
        
        Args:
            pair: Trading pair (e.g., 'NEARUSD')
            volume: Order volume
            config_id: Configuration ID for logging (optional)
            
        Returns:
            Tuple of (is_sufficient: bool, message: str, minimum: str or None)
        """
        try:
            # Fetch pair info from Kraken API
            pair_info = self.kraken_api_readonly.get_asset_pair_info(pair)
            
            if not pair_info:
                # Could not get pair info - allow order to proceed
                # The actual error will be caught when creating the order
                return (True, 'Could not verify minimum volume (pair info unavailable)', None)
            
            # Extract ordermin field
            ordermin_str = pair_info.get('ordermin')
            if not ordermin_str:
                # No minimum specified - allow order
                return (True, 'No minimum volume specified for pair', None)
            
            try:
                # Convert to Decimal for comparison
                ordermin = Decimal(str(ordermin_str))
                volume_decimal = Decimal(str(volume))
                
                # Check if volume meets minimum
                if volume_decimal < ordermin:
                    return (False, 
                            f'Volume {volume} is below minimum {ordermin} for {pair}',
                            str(ordermin))
                else:
                    return (True, 
                            f'Volume {volume} meets minimum {ordermin} for {pair}',
                            str(ordermin))
                            
            except (ValueError, InvalidOperation) as e:
                self.log('WARNING', 
                        f'Could not parse ordermin value "{ordermin_str}" for {pair}: {e}',
                        config_id=config_id, error=str(e))
                # Allow order to proceed if we can't parse
                return (True, 'Could not parse minimum volume', None)
                
        except Exception as e:
            self.log('WARNING',
                    f'Error checking minimum volume for {pair}: {e}',
                    config_id=config_id, error=str(e))
            # On error, allow order to proceed - actual validation happens at Kraken
            return (True, 'Error checking minimum volume', None)
    
    def check_sufficient_balance(self, pair: str, direction: str, volume: float, config_id: str = None) -> tuple:
        """
        Check if there is sufficient balance to create an order.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD')
            direction: Order direction ('buy' or 'sell')
            volume: Order volume
            config_id: Configuration ID for logging (optional)
            
        Returns:
            Tuple of (is_sufficient: bool, message: str, available: Decimal or None)
        """
        # Only check balance for sell orders (we don't check quote currency for buy orders)
        if direction.lower() != 'sell':
            return (True, 'Balance check skipped for buy orders', None)
        
        # Validate we have API access
        if not self.kraken_api_readwrite:
            return (False, 'No API credentials available for balance check', None)
        
        try:
            # Get normalized account balance (spot + funding summed)
            balance = self.kraken_api_readwrite.get_normalized_balances()
            if not balance:
                return (False, 'Could not retrieve account balance', None)
        except KrakenAPIError as e:
            self.log('ERROR', f'Kraken API error checking balance: {str(e)} (type: {e.error_type})',
                    error=str(e), error_type=e.error_type)
            
            # Send notification about API error
            if self.notification_manager:
                self.notification_manager.notify_api_error(
                    error_type=e.error_type,
                    endpoint='Balance',
                    error_message=str(e),
                    details=e.details
                )
            
            return (False, f'API error checking balance: {str(e)}', None)
        except Exception as e:
            return (False, f'Error checking balance: {str(e)}', None)
        
        try:
            
            # Extract base asset from pair
            base_asset = self._extract_base_asset(pair)
            if not base_asset:
                return (False, f'Could not extract base asset from pair: {pair}', None)
            
            # Normalize all balance keys and sum totals for each normalized asset
            # This handles both spot wallet (e.g., 'XXBT') and funding wallet (e.g., 'XBT.F')
            getcontext().prec = 28
            normalized_totals = {}
            contributors = {}
            
            for k, v in balance.items():
                try:
                    amount = Decimal(str(v))
                except (InvalidOperation, Exception):
                    continue
                    
                norm = self._normalize_asset(k)
                if not norm:
                    continue
                    
                normalized_totals.setdefault(norm, Decimal('0'))
                normalized_totals[norm] += amount
                contributors.setdefault(norm, []).append((k, amount))
            
            # Normalize the base_asset for lookup
            canonical_norm = self._normalize_asset(base_asset)
            
            # Get available balance for the asset
            available = normalized_totals.get(canonical_norm, Decimal('0'))
            contrib = contributors.get(canonical_norm, [])
            
            # Convert volume to Decimal
            try:
                volume_dec = Decimal(str(volume))
            except (InvalidOperation, Exception) as e:
                return (False, f'Invalid volume value: {volume}', None)
            
            # Build detailed message with contributors
            contrib_str = ', '.join([f"{k}={amount}" for k, amount in contrib]) if contrib else 'none'
            
            # Check if balance is sufficient
            if available >= volume_dec:
                message = (f'Sufficient {base_asset} balance: {available} '
                          f'(Contributors: {contrib_str}) >= required {volume_dec}')
                return (True, message, available)
            else:
                message = (f'Insufficient {base_asset} balance: {available} '
                          f'(Contributors: {contrib_str}) < required {volume_dec}')
                return (False, message, available)
                
        except Exception as e:
            error_msg = f'Error checking balance: {str(e)}'
            return (False, error_msg, None)
    
    def _handle_order_error_state(self, config_id: str, error_msg: str, notify_type: str = None, notify_args: dict = None):
        """
        Handle order creation errors by updating state and optionally sending notifications.
        
        This method:
        1. Updates last_error in state.csv
        2. Sends notification only if not already notified (prevents spam)
        3. Sets error_notified flag to prevent repeated notifications
        
        Args:
            config_id: Configuration ID
            error_msg: Error message to store
            notify_type: Type of notification ('order_failed', 'insufficient_balance', etc.)
            notify_args: Arguments to pass to notification method
        """
        if config_id not in self.state:
            return
        
        # Update error state
        self.state[config_id]['last_error'] = error_msg
        
        # Send notification only if not already notified for this error
        if not self.state[config_id].get('error_notified') and self.notification_manager and notify_type:
            try:
                if notify_type == 'insufficient_balance' and hasattr(self.notification_manager, 'notify_insufficient_balance'):
                    self.notification_manager.notify_insufficient_balance(**notify_args)
                elif notify_type == 'order_failed' and hasattr(self.notification_manager, 'notify_order_failed'):
                    self.notification_manager.notify_order_failed(**notify_args)
                
                # Mark as notified to prevent repeated notifications
                self.state[config_id]['error_notified'] = True
            except Exception as e:
                self.log('WARNING', f'Failed to send error notification: {str(e)}',
                        config_id=config_id, error=str(e))
    
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
            if config_id in self.state:
                self._handle_order_error_state(config_id, 'Missing read-write API credentials')
            return None
        
        # Step 10: Check if volume meets Kraken's minimum order size for the pair
        # This prevents sending orders that will fail with "volume minimum not met"
        volume_ok, volume_msg, minimum = self.check_minimum_volume(
            pair=pair,
            volume=volume,
            config_id=config_id
        )
        
        if not volume_ok:
            self.log('ERROR',
                    f"Cannot create TSL order: {volume_msg}",
                    config_id=config_id, trigger_price=trigger_price,
                    pair=pair, direction=direction, volume=volume, minimum=minimum)
            print(f"ERROR: Cannot create order for {config_id}: {volume_msg}")
            # Notify user about volume minimum issue (only once via state tracking)
            if config_id in self.state:
                self._handle_order_error_state(config_id, volume_msg, notify_type='order_failed', notify_args={
                    'pair': pair,
                    'direction': direction,
                    'volume': volume,
                    'error': volume_msg,
                    'trigger_price': trigger_price_float
                })
            return None
        else:
            # Log that volume check passed
            self.log('DEBUG',
                    f"Volume check passed: {volume_msg}",
                    config_id=config_id)
        
        # Step 11: Check if we have sufficient balance before creating the order
        # This prevents sending orders to Kraken that will fail due to insufficient funds
        is_sufficient, balance_msg, available = self.check_sufficient_balance(
            pair=pair,
            direction=direction,
            volume=volume,
            config_id=config_id
        )
        
        if not is_sufficient:
            self.log('ERROR', 
                    f"Cannot create TSL order: {balance_msg}",
                    config_id=config_id, trigger_price=trigger_price, 
                    pair=pair, direction=direction, volume=volume)
            print(f"ERROR: Cannot create order for {config_id}: {balance_msg}")
            
            # Send notification about insufficient balance
            # If state exists, use _handle_order_error_state to prevent repeated notifications
            # Otherwise, send notification directly (for cases where create_tsl_order is called standalone)
            if config_id in self.state:
                # Use state-based handling (checks error_notified flag to prevent spam)
                self._handle_order_error_state(config_id, balance_msg, notify_type='insufficient_balance', notify_args={
                    'config_id': config_id,
                    'pair': pair,
                    'direction': direction,
                    'volume': volume,
                    'available': available,  # Pass Decimal directly for proper formatting
                    'trigger_price': trigger_price_float
                })
            else:
                # No state entry - send notification directly (won't prevent repeated sends)
                if self.notification_manager:
                    try:
                        if hasattr(self.notification_manager, 'notify_insufficient_balance'):
                            self.notification_manager.notify_insufficient_balance(
                                config_id=config_id,
                                pair=pair,
                                direction=direction,
                                volume=str(volume),
                                available=available,
                                trigger_price=trigger_price_float
                            )
                        else:
                            self.notification_manager.notify_order_failed(
                                config_id=config_id,
                                pair=pair,
                                direction=direction,
                                volume=volume,
                                error=balance_msg,
                                trigger_price=trigger_price_float
                            )
                    except Exception:
                        pass
            return None
        else:
            # Log that balance check passed
            self.log('INFO', 
                    f"Balance check passed: {balance_msg}",
                    config_id=config_id)
        
        # Step 11: Log that we are about to create a real order
        self.log('INFO', 
                f"Creating TSL order: pair={pair}, direction={direction}, "
                f"volume={volume}, trailing_offset={trailing_offset}%",
                config_id=config_id, trigger_price=trigger_price)
        
        # Step 12: Attempt to create the order via API
        # Wrap in try-except to catch ANY errors
        result = None
        try:
            # Decide best defaults for 'trigger' and 'oflags'
            # Prefer 'index' trigger (use index price) but fall back to 'last' if unavailable
            api_kwargs = {'trigger': 'index'}

            # Determine base asset and prefer NOT to pay fees in BTC (keep BTC)
            try:
                base_asset = self._extract_base_asset(pair)
                canonical_base = self._normalize_asset(base_asset)
            except Exception:
                base_asset = None
                canonical_base = ''

            oflags_choice = None
            # Normalized BTC token in this codebase is 'BT' (from _normalize_asset)
            if canonical_base and canonical_base.upper() == 'BT':
                oflags_choice = 'fciq'  # prefer fee in quote currency (not BTC)

            if oflags_choice:
                api_kwargs['oflags'] = oflags_choice

            # Call the Kraken API to create the trailing stop loss order
            result = self.kraken_api_readwrite.add_trailing_stop_loss(
                pair=pair,
                direction=direction,
                volume=volume,
                trailing_offset_percent=trailing_offset,
                **api_kwargs
            )
        except Exception as e:
            error_msg = str(e)

            # If index price is unavailable, retry with last trade price
            if 'index unavailable' in error_msg.lower():
                self.log('WARNING',
                        f"Index price unavailable for {pair}, retrying with last trade price",
                        config_id=config_id, pair=pair)
                try:
                    api_kwargs['trigger'] = 'last'
                    result = self.kraken_api_readwrite.add_trailing_stop_loss(
                        pair=pair,
                        direction=direction,
                        volume=volume,
                        trailing_offset_percent=trailing_offset,
                        **api_kwargs
                    )
                    self.log('INFO',
                            f"TSL order created successfully using last price trigger for {pair}",
                            config_id=config_id, pair=pair)
                except KrakenAPIError as retry_e:
                    retry_error_msg = str(retry_e)
                    self.log('ERROR',
                            f"Kraken API error creating TSL order (after retry): {retry_error_msg} (type: {retry_e.error_type})",
                            config_id=config_id, error=retry_error_msg, error_type=retry_e.error_type)
                    if self.notification_manager:
                        try:
                            self.notification_manager.notify_api_error(
                                error_type=retry_e.error_type,
                                endpoint='AddOrder/add_trailing_stop_loss',
                                error_message=retry_error_msg,
                                details=retry_e.details
                            )
                        except Exception:
                            pass
                    if 'permission' in retry_error_msg.lower() or 'invalid key' in retry_error_msg.lower():
                        print(f"ERROR: API credentials may not have proper permissions for creating orders. "
                              f"Check that KRAKEN_API_KEY_RW has 'Create & Modify Orders' permission.")
                    return None
                except Exception as retry_e:
                    retry_error_msg = str(retry_e)
                    self.log('ERROR',
                            f"Unexpected exception creating TSL order (after retry): {retry_error_msg}",
                            config_id=config_id, error=retry_error_msg)
                    if 'insufficient' in retry_error_msg.lower() or 'balance' in retry_error_msg.lower():
                        if self.notification_manager:
                            try:
                                self.notification_manager.notify_order_failed(
                                    config_id=config_id,
                                    pair=pair,
                                    direction=direction,
                                    volume=volume,
                                    error=retry_error_msg,
                                    trigger_price=trigger_price_float
                                )
                            except Exception as notify_error:
                                self.log('WARNING', f'Failed to send order failure notification: {str(notify_error)}',
                                        config_id=config_id)
                    return None

            # If we already recovered via retry, don't run the subsequent error handling
            if result is not None:
                # We have a valid result from the retry path; fall through to normal validation
                pass
            else:
                # KrakenAPIError handling: log, notify, update state
                if isinstance(e, KrakenAPIError):
                    self.log('ERROR',
                            f"Kraken API error creating TSL order: {error_msg} (type: {e.error_type})",
                            config_id=config_id, error=error_msg, error_type=e.error_type)
                    if self.notification_manager:
                        try:
                            self.notification_manager.notify_api_error(
                                error_type=e.error_type,
                                endpoint='AddOrder/add_trailing_stop_loss',
                                error_message=error_msg,
                                details=e.details
                            )
                        except Exception:
                            pass
                    if config_id in self.state:
                        try:
                            self._handle_order_error_state(config_id, error_msg, notify_type='order_failed', notify_args={
                                'pair': pair,
                                'direction': direction,
                                'volume': volume,
                                'error': error_msg,
                                'trigger_price': trigger_price_float
                            })
                        except Exception:
                            pass
                    return None

                # Generic exception handling: log, possibly notify, update state
                self.log('ERROR',
                        f"Unexpected exception creating TSL order: {error_msg}",
                        config_id=config_id, error=error_msg)
                if 'permission' in error_msg.lower() or 'invalid key' in error_msg.lower():
                    print(f"ERROR: API credentials may not have proper permissions for creating orders. "
                          f"Check that KRAKEN_API_KEY_RW has 'Create & Modify Orders' permission.")
                if 'insufficient' in error_msg.lower() or 'balance' in error_msg.lower():
                    if self.notification_manager:
                        try:
                            self.notification_manager.notify_order_failed(
                                config_id=config_id,
                                pair=pair,
                                direction=direction,
                                volume=volume,
                                error=error_msg,
                                trigger_price=trigger_price_float
                            )
                        except Exception as notify_error:
                            self.log('WARNING', f'Failed to send order failure notification: {str(notify_error)}',
                                    config_id=config_id)
                if config_id in self.state:
                    try:
                        self._handle_order_error_state(config_id, error_msg, notify_type='order_failed', notify_args={
                            'pair': pair,
                            'direction': direction,
                            'volume': volume,
                            'error': error_msg,
                            'trigger_price': trigger_price_float
                        })
                    except Exception:
                        pass
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
        
        # Send notification about TSL order created
        if self.notification_manager:
            try:
                # Get linked order ID if present
                linked_order_id = config.get('linked_order_id', '').strip() or None
                self.notification_manager.notify_tsl_order_created(
                    config_id, order_id, pair, direction, volume,
                    trailing_offset, trigger_price_float, linked_order_id
                )
            except Exception as e:
                self.log('WARNING', f'Failed to send TSL created notification: {str(e)}',
                        config_id=config_id, error=str(e))
        
        return order_id
    
    def check_order_filled(self, config_id, order_id):
        """
        Check if a specific order has been filled.
        
        Efficiently queries only the specific order ID instead of fetching ALL closed orders.
        
        Args:
            config_id: Configuration ID for logging
            order_id: Kraken order ID to check
            
        Returns:
            Tuple of (is_filled: bool, fill_price: float or None, api_pair: str or None, 
                     filled_volume: str or None, order_info: dict or None)
        """
        if not order_id or order_id == 'DRY_RUN_ORDER_ID':
            # Dry-run orders are never filled
            return False, None, None, None, None

        if not self.kraken_api_readwrite:
            self.log('WARNING', 'Cannot check order status: No read-write API credentials',
                    config_id=config_id, order_id=order_id)
            return False, None, None, None, None

        try:
            # Query the specific order by ID (much more efficient than querying ALL closed orders)
            order_result = self.kraken_api_readwrite.query_orders(order_id)

            if not order_result:
                # Order not found - might still be open or doesn't exist
                return False, None, None, None, None
                
        except KrakenAPIError as e:
            self.log('ERROR', f'Kraken API error checking order status: {str(e)} (type: {e.error_type})',
                    config_id=config_id, order_id=order_id, error=str(e), error_type=e.error_type)

            # Send notification about API error
            if self.notification_manager:
                self.notification_manager.notify_api_error(
                    error_type=e.error_type,
                    endpoint='QueryOrders/query_orders',
                    error_message=str(e),
                    details=e.details
                )

            return False, None, None, None, None
        except Exception as e:
            self.log('ERROR', f'Unexpected error checking order status: {str(e)}',
                    config_id=config_id, order_id=order_id, error=str(e))
            return False, None, None, None, None

        try:
            # Check if our order is in the result
            if order_id in order_result:
                order_info = order_result[order_id]
                status = order_info.get('status', '')

                # Order is filled/closed
                self.log('INFO', f'Order {order_id} status: {status}',
                        config_id=config_id, order_id=order_id)

                # Try to get the fill price and other useful metadata from the
                # closed order record so notifications can be informative.
                fill_price = None
                api_pair = None
                filled_volume = None
                fill_time = None
                try:
                    # Kraken returns price as a string
                    price_str = order_info.get('price', '')
                    fill_price = float(price_str) if price_str else None
                except (ValueError, TypeError):
                    pass

                # Try to extract pair and executed volume from the order description
                try:
                    descr = order_info.get('descr', {}) or {}
                    api_pair = descr.get('pair') or None
                except Exception:
                    api_pair = None

                try:
                    filled_volume = order_info.get('vol_exec') or order_info.get('vol') or None
                except Exception:
                    filled_volume = None

                try:
                    # closetm is Kraken's close timestamp in epoch seconds
                    closetm = order_info.get('closetm')
                    if closetm:
                        fill_time = float(closetm)
                except Exception:
                    filled_volume = None
                    fill_time = None
                # Consider order filled if status is 'closed'
                is_filled = status == 'closed'
                # Return pair, volume, and full order_info so caller can use it
                return is_filled, fill_price, api_pair, filled_volume, order_info

            # Order not in closed orders yet
            return False, None, None, None, None

        except Exception as e:
            self.log('WARNING', f'Error checking order status: {str(e)}',
                    config_id=config_id, order_id=order_id, error=str(e))
            return False, None, None, None, None
    
    def activate_linked_order_if_needed(self, config_id, order_info):
        """
        When order fills successfully, activate any linked order.
        
        This enables chained orders: Buy low → automatically activates Sell high.
        
        Args:
            config_id: ID of the config whose order just filled
            order_info: Order information from Kraken API
        """
        # Step 1: Only activate on FULL fill, not partial or canceled
        status = order_info.get('status', '')
        if status != 'closed':
            self.log('DEBUG', f'Order {config_id} status is {status}, not activating linked order',
                    config_id=config_id, status=status)
            return
        
        # Step 2: Find config for this order to check if it has a linked order
        config = None
        if self.configs:
            for cfg in self.configs:
                if cfg.get('id') == config_id:
                    config = cfg
                    break
        
        if not config:
            self.log('DEBUG', f'Config {config_id} not found in current configs',
                    config_id=config_id)
            return
        
        # Step 3: Check if config has a linked order
        linked_id = config.get('linked_order_id', '').strip()
        if not linked_id:
            # No linked order - this is normal, not an error
            return
        
        self.log('INFO', f'Order {config_id} filled, checking linked order: {linked_id}',
                config_id=config_id, linked_id=linked_id)
        
        # Step 4: Find the linked config
        linked_config = None
        if self.configs:
            for cfg in self.configs:
                if cfg.get('id') == linked_id:
                    linked_config = cfg
                    break
        
        if not linked_config:
            self.log('ERROR', f'Linked order {linked_id} not found in config for {config_id}',
                    config_id=config_id, linked_id=linked_id)
            return
        
        # Step 5: Check if linked order is already enabled
        linked_enabled = linked_config.get('enabled', '').strip().lower()
        if linked_enabled == 'true':
            self.log('INFO', f'Linked order {linked_id} already enabled, skipping activation',
                    config_id=config_id, linked_id=linked_id)
            return
        
        # Step 6: Check if linked order was already triggered (safety check)
        linked_state = self.state.get(linked_id, {})
        if isinstance(linked_state, dict) and linked_state.get('triggered') == 'true':
            self.log('WARNING', f'Linked order {linked_id} already triggered, not activating again',
                    config_id=config_id, linked_id=linked_id)
            return
        
        # Step 7: Activate the linked order by setting enabled='true'
        try:
            self.config_manager.update_config_enabled(linked_id, 'true')
            self.log('INFO', f'Successfully activated linked order {linked_id} after {config_id} filled',
                    config_id=config_id, linked_id=linked_id,
                    parent_pair=config.get('pair'), linked_pair=linked_config.get('pair'))
            
            # Step 8: Send notification about the activation
            if self.notification_manager:
                try:
                    self.notification_manager.notify_linked_order_activated(
                        parent_id=config_id,
                        linked_id=linked_id,
                        parent_pair=config.get('pair', 'Unknown'),
                        linked_pair=linked_config.get('pair', 'Unknown')
                    )
                except Exception as e:
                    self.log('WARNING', f'Failed to send linked order notification: {str(e)}',
                            config_id=config_id, linked_id=linked_id, error=str(e))
        
        except Exception as e:
            self.log('ERROR', f'Failed to activate linked order {linked_id}: {str(e)}',
                    config_id=config_id, linked_id=linked_id, error=str(e))
    
    def check_triggered_orders(self):
        """
        Check status of all triggered orders to see if they've been filled.
        Send notification when an order is filled.
        """
        # Skip if in dry-run mode
        if self.dry_run:
            return
        
        # Find all triggered orders that haven't been notified as filled yet
        for config_id, state_data in self.state.items():
            if not isinstance(state_data, dict):
                continue
            
            # Check if this config has a triggered order
            if state_data.get('triggered') != 'true':
                continue
            
            order_id = state_data.get('order_id')
            if not order_id:
                continue
            
            # Check if we've already notified about this fill
            fill_notified = state_data.get('fill_notified', 'false')
            if fill_notified == 'true':
                continue
            
            # Check if the order is filled. The helper now returns additional
            # metadata (pair, filled_volume, order_info) when available from Kraken.
            is_filled, fill_price, api_pair, filled_volume, order_info = self.check_order_filled(config_id, order_id)
            
            if is_filled:
                self.log('INFO', f'Order {order_id} for config {config_id} has been filled',
                        config_id=config_id, order_id=order_id)
                
                # Find the config to get pair and linked order information
                pair = None
                linked_order_id = None
                if self.configs:
                    for config in self.configs:
                        if config.get('id') == config_id:
                            pair = config.get('pair')
                            linked_order_id = config.get('linked_order_id', '').strip() or None
                            break
                
                # Gather additional context we can provide in the notification.
                trigger_price = state_data.get('trigger_price')
                trigger_time = state_data.get('trigger_time')
                offset = state_data.get('offset') or state_data.get('trailing_offset_percent')

                # If we couldn't find the pair in validated configs, fall back
                # to the pair reported by Kraken's closed order record.
                notify_pair = pair or api_pair or 'Unknown'

                # Send notification with richer context
                if self.notification_manager:
                    try:
                        self.notification_manager.notify_tsl_order_filled(
                            config_id=config_id,
                            order_id=order_id,
                            pair=notify_pair,
                            fill_price=fill_price,
                            volume=filled_volume,
                            trigger_price=trigger_price,
                            trigger_time=trigger_time,
                            offset=offset,
                            linked_order_id=linked_order_id,
                        )
                        self.log('INFO', f'Sent fill notification for order {order_id}',
                                config_id=config_id, order_id=order_id)
                    except Exception as e:
                        self.log('WARNING', f'Failed to send fill notification: {str(e)}',
                                config_id=config_id, order_id=order_id, error=str(e))
                
                # Mark as notified in state
                self.state[config_id]['fill_notified'] = 'true'
                
                # Activate linked order if configured (must happen BEFORE reload)
                # Pass order_info so it can check status is 'closed'
                if order_info:
                    try:
                        self.activate_linked_order_if_needed(config_id, order_info)
                    except Exception as e:
                        self.log('ERROR', f'Error activating linked order: {str(e)}',
                                config_id=config_id, error=str(e))
                
                # Reload configs so linked order is visible in next cycle
                # NOTE: This causes configs to be reloaded, so linked order will be processed
                try:
                    self.configs = self.config_manager.load_config()
                except Exception as e:
                    self.log('ERROR', f'Failed to reload config after activating linked order: {str(e)}',
                            config_id=config_id, error=str(e))
                
                # Save state immediately so we don't re-notify
                try:
                    self.save_state()
                except Exception as e:
                    self.log('ERROR', f'Failed to save state after fill notification: {str(e)}',
                            config_id=config_id, error=str(e))
    
    def process_config(self, config, current_price=None):
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
        # Get the 'enabled' field, defaulting to 'false' if not present
        enabled_value = config.get('enabled', 'true')
        if not enabled_value:
            enabled_value = 'false'
        
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
                'last_checked': '',
                'last_error': '',
                'error_notified': False,
                'trigger_notified': False,  # Track if we've sent "trigger price reached" notification
                'initial_price': ''  # Will be populated on first run
            }
        
        # Step 5: Check if config has already been triggered
        # SAFETY: Do not trigger twice - this prevents duplicate orders
        triggered_value = self.state[config_id].get('triggered', 'false')
        if triggered_value == 'true':
            self.log('DEBUG', f"Config {config_id} already triggered, skipping")
            # Do not process already triggered configs - this prevents duplicate orders
            return
        
        # Note: To retry after fixing an error (e.g., adding balance), user should:
        # 1. Disable the config (set enabled=false)  
        # 2. Fix the issue (add balance, adjust volume, etc.)
        # 3. Re-enable the config (set enabled=true)
        # This will create a fresh state entry when processed, clearing all error flags.
        
        # Step 6: Get the trading pair
        pair = config.get('pair')
        if not pair:
            # SAFETY: No trading pair - do not process
            self.log('ERROR', f"Config {config_id} has no trading pair, skipping",
                    config_id=config_id)
            return
        
        # Step 7: Attempt to get current price if not provided by caller
        # Wrap in try-except to handle any API errors
        if current_price is None:
            try:
                # Use read-only API to get current price
                current_price = self.kraken_api_readonly.get_current_price(pair)
            except KrakenAPIError as e:
                # SAFETY: Cannot get price - do not process
                self.log('ERROR', 
                        f"Kraken API error getting current price for {pair}: {str(e)} (type: {e.error_type})",
                        config_id=config_id, pair=pair, error=str(e), error_type=e.error_type)
                
                # Send notification about API error
                if self.notification_manager:
                    self.notification_manager.notify_api_error(
                        error_type=e.error_type,
                        endpoint='Ticker/get_current_price',
                        error_message=str(e),
                        details=e.details
                    )
                
                # Return without creating order - this is safe
                return
            except Exception as e:
                # SAFETY: Cannot get price - do not process
                self.log('ERROR', 
                        f"Unexpected error getting current price for {pair}: {str(e)}",
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
        
        # Step 10: Populate initial_price if it's blank (first run for this config)
        # This tracks the price when the user first created/enabled the config
        # Used to calculate the true benefit of the TSL system (initial vs executed price)
        if not self.state[config_id].get('initial_price'):
            try:
                self.state[config_id]['initial_price'] = str(current_price)
                self.log('INFO', 
                        f"Set initial price for {config_id}: {current_price}",
                        config_id=config_id, pair=pair, initial_price=current_price)
            except Exception as e:
                # Log error but continue - this doesn't affect order logic
                self.log('WARNING', 
                        f"Could not set initial_price: {str(e)}",
                        config_id=config_id, error=str(e))
        
        # Step 11: Update last checked time
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            self.state[config_id]['last_checked'] = current_time
        except Exception as e:
            # Log error but continue - this doesn't affect order logic
            self.log('WARNING', 
                    f"Could not update last_checked time: {str(e)}",
                    config_id=config_id, error=str(e))
        
        # Step 12: Check if threshold is met
        # This returns False if anything is wrong, so it's safe
        threshold_is_met = self.check_threshold(config, current_price)
        
        # Step 13: Decide whether to create order
        if threshold_is_met:
            # Threshold is met - log it
            threshold_price = config.get('threshold_price', 'unknown')
            threshold_type = config.get('threshold_type', 'unknown')
            
            self.log('INFO', 
                    f"Threshold met for {config_id}: current_price={current_price}, "
                    f"threshold={threshold_price} ({threshold_type})",
                    config_id=config_id, pair=pair, price=current_price)
            
            # Send notification about trigger price reached (only once)
            # Check if we've already notified about this trigger to prevent spam
            if self.notification_manager and not self.state[config_id].get('trigger_notified'):
                try:
                    threshold_price_float = float(threshold_price) if threshold_price != 'unknown' else 0
                    # Get linked order ID if present
                    linked_order_id = config.get('linked_order_id', '').strip() or None
                    self.notification_manager.notify_trigger_price_reached(
                        config_id, pair, float(current_price), 
                        threshold_price_float, str(threshold_type), linked_order_id
                    )
                    # Mark that we've sent the trigger notification
                    self.state[config_id]['trigger_notified'] = True
                except Exception as e:
                    self.log('WARNING', f'Failed to send trigger notification: {str(e)}',
                            config_id=config_id, error=str(e))
            
            # Step 14: Attempt to create TSL order
            order_id = self.create_tsl_order(config, current_price)
            
            # Step 15: Check if order was created successfully
            if order_id:
                # SAFETY: In dry-run mode, do not update state
                # This ensures dry-run doesn't modify state.csv
                if not self.dry_run:
                    # Order created successfully - update state
                    try:
                        trigger_time = datetime.now(timezone.utc).isoformat()
                        self.state[config_id]['triggered'] = 'true'
                        self.state[config_id]['trigger_price'] = str(current_price)
                        self.state[config_id]['trigger_time'] = trigger_time
                        self.state[config_id]['order_id'] = order_id
                        self.state[config_id]['activated_on'] = trigger_time  # Record when rule was activated
                        
                        self.log('INFO', 
                                f"Successfully triggered config {config_id}",
                                config_id=config_id, order_id=order_id)
                    except Exception as e:
                        # Log error updating state, but order was created
                        self.log('ERROR', 
                                f"Order created but failed to update state: {str(e)}",
                                config_id=config_id, order_id=order_id, error=str(e))
                    
                    # Update config.csv with trigger information
                    try:
                        self.config_manager.update_config_on_trigger(
                            config_id=config_id,
                            order_id=order_id,
                            trigger_time=trigger_time,
                            trigger_price=str(current_price)
                        )
                        self.log('INFO', 
                                f"Updated config.csv for triggered config {config_id}",
                                config_id=config_id)
                    except Exception as e:
                        # Log error but don't fail - state was updated successfully
                        self.log('ERROR', 
                                f"Failed to update config.csv for {config_id}: {str(e)}",
                                config_id=config_id, error=str(e))
                else:
                    # In dry-run mode, just log what would happen
                    self.log('INFO', 
                            f"[DRY RUN] Would mark config {config_id} as triggered",
                            config_id=config_id, order_id=order_id)
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
        
        SECURITY NOTE: This function will return False (prevent operation) if:
        - Config file cannot be loaded
        - No configurations are found
        - Any configuration has validation errors
        - Read-only API is not available for price checks
        
        Returns:
            True if validation passed, False otherwise (False = do not proceed)
        """
        # Step 1: Validate config_manager exists
        if not self.config_manager:
            self.log('ERROR', 'Configuration manager is not initialized')
            return False
        
        # Step 2: Attempt to load configurations from file
        try:
            configs = self.config_manager.load_config()
        except Exception as e:
            # SAFETY: Cannot load config - do not proceed
            self.log('ERROR', f'Failed to load configuration file: {str(e)}',
                    error=str(e))
            return False
        
        # Step 3: Check if any configurations were loaded
        if not configs:
            # SAFETY: No configs means nothing to monitor - do not proceed
            self.log('ERROR', 'No configurations found in config file')
            return False
        
        # Step 4: Validate we have read-only API for price checks
        if not self.kraken_api_readonly:
            # SAFETY: Cannot validate against market prices - do not proceed
            self.log('ERROR', 'Read-only API is required for configuration validation')
            return False
        
        # Step 5: Create validator with API for market price checks
        try:
            validator = ConfigValidator(kraken_api=self.kraken_api_readonly, debug_mode=self.debug)
        except Exception as e:
            # SAFETY: Cannot create validator - do not proceed
            self.log('ERROR', f'Failed to create configuration validator: {str(e)}',
                    error=str(e))
            return False
        
        # Step 6: Validate all configurations
        try:
            result = validator.validate_config_file(configs)
        except Exception as e:
            # SAFETY: Validation failed with exception - do not proceed
            self.log('ERROR', f'Configuration validation failed with exception: {str(e)}',
                    error=str(e))
            return False
        
        # Step 7: Log all validation errors
        if result.errors:
            # Log each error individually
            for error in result.errors:
                self.log('ERROR', 
                        f"Config validation error [{error['config_id']}] {error['field']}: {error['message']}",
                        config_id=error['config_id'], field=error['field'])
            # Send notification about validation errors
            if self.notification_manager:
                self.notification_manager.notify_validation_errors(result.errors)
        
        # Step 8: Log all validation warnings
        if result.warnings:
            # Log each warning individually
            for warning in result.warnings:
                self.log('WARNING', 
                        f"Config validation warning [{warning['config_id']}] {warning['field']}: {warning['message']}",
                        config_id=warning['config_id'], field=warning['field'])
        
        # Step 8b: Log all validation info messages (only in verbose/debug mode)
        if hasattr(result, 'infos') and result.infos:
            # Log each info individually (only shown in verbose/debug mode)
            for info in result.infos:
                self.log('INFO', 
                        f"Config validation info [{info['config_id']}] {info['field']}: {info['message']}",
                        config_id=info['config_id'], field=info['field'])
        
        # Step 9: Disable configs with validation errors
        config_ids_with_errors = result.get_config_ids_with_errors()
        if config_ids_with_errors and not self.dry_run:
            try:
                self.config_manager.disable_configs(config_ids_with_errors)
                # Print to console about disabled configs
                print(f"\nThe following configs had validation errors and have been disabled:")
                for config_id in sorted(config_ids_with_errors):
                    # Get all errors for this config
                    config_errors = [e for e in result.errors if e['config_id'] == config_id]
                    print(f"  [{config_id}]:")
                    for error in config_errors:
                        print(f"    - {error['field']}: {error['message']}")
                print("\nThese configs have been set to enabled=false in the configuration file.")
                print("Fix the errors and set enabled=true to re-enable them.\n")
            except Exception as e:
                self.log('ERROR', f'Failed to disable configs with errors: {str(e)}',
                        error=str(e))
        elif config_ids_with_errors and self.dry_run:
            # In dry-run mode, just report errors but don't modify the CSV
            print(f"\n[DRY RUN] The following configs have validation errors (not modifying CSV in dry-run mode):")
            for config_id in sorted(config_ids_with_errors):
                config_errors = [e for e in result.errors if e['config_id'] == config_id]
                print(f"  [{config_id}]:")
                for error in config_errors:
                    print(f"    - {error['field']}: {error['message']}")
            print()
        
        # Step 10: Check if we have any valid enabled configs left
        # Count configs that are enabled and don't have errors
        valid_enabled_configs = 0
        for config in result.configs:
            config_id = config.get('id', '')
            if config_id not in config_ids_with_errors:
                valid_enabled_configs += 1
        
        if valid_enabled_configs == 0:
            # SAFETY: No valid configs left - do not proceed
            self.log('ERROR', 'All configurations have validation errors. Cannot proceed.')
            return False
        
        # Step 11: Warn about warnings if in verbose mode
        if result.has_warnings() and self.verbose:
            print("Configuration has warnings. Review them to ensure they are expected.")
        
        # Step 12: Store validated configs in memory for use during runtime
        # This prevents automatic reloading - configs are only loaded once at startup
        self.configs = result.configs
        
        # Step 13: Validation passed for at least some configs - safe to proceed
        return True
    
    def run_once(self):
        """
        Run one iteration of checking all configurations.
        
        SECURITY NOTE: This function will not create orders if:
        - Configuration cannot be loaded
        - No configurations are found
        - Any error occurs during processing
        """
        # Step 1: Validate config_manager exists
        if not self.config_manager:
            self.log('ERROR', 'Configuration manager is not initialized')
            return
        
        # Step 2: Use in-memory configurations (loaded once at startup)
        # Do NOT reload from disk - this prevents automatic config reloading
        configs = self.configs
        
        # Step 3: Check if configurations were loaded at startup
        if not configs:
            # SAFETY: No configs loaded at startup - do not process
            self.log('WARNING', 'No configurations loaded at startup')
            return
        
        # Step 4: Log how many configs we are processing
        num_configs = len(configs)
        self.log('INFO', f'Processing {num_configs} configurations')
        
        # Step 5: Deduplicate price requests per-iteration
        prices = {}
        pairs_to_fetch = set()

        # Determine which pairs actually need fetching:
        for config in configs:
            try:
                if not isinstance(config, dict):
                    continue

                # Check enabled flag similar to process_config to avoid fetching for disabled configs
                enabled_value = config.get('enabled', 'true')
                if not enabled_value:
                    enabled_value = 'false'
                if enabled_value.strip().lower() != 'true':
                    continue

                config_id = config.get('id')
                # Skip already triggered configs
                if config_id and self.state.get(config_id, {}).get('triggered') == 'true':
                    continue

                pair = config.get('pair')
                if pair:
                    pairs_to_fetch.add(pair)
            except Exception:
                # Ignore config parsing errors here; process_config will log them if needed
                continue

        # Fetch prices in a single batch API call (much more efficient than N individual calls)
        if pairs_to_fetch:
            try:
                # Try batch fetch first (most efficient)
                prices_result = self.kraken_api_readonly.get_current_prices_batch(pairs_to_fetch)
                
                # Handle case where batch method returns empty or invalid result
                if prices_result and isinstance(prices_result, dict):
                    prices = prices_result
                    self.log('DEBUG', f'Batch fetched prices for {len(prices)} pairs')
                    
                    # Check for any pairs that failed to return a price
                    pairs_without_prices = pairs_to_fetch - set(prices.keys())
                    if pairs_without_prices:
                        self.log('WARNING', f'Batch fetch did not return prices for {len(pairs_without_prices)} pairs: {pairs_without_prices}')
                        # Set missing pairs to None so we don't try to process them
                        for pair in pairs_without_prices:
                            prices[pair] = None
                else:
                    # Batch method returned invalid result, fall back to individual fetches
                    self.log('WARNING', 'Batch fetch returned invalid result, falling back to individual price fetches')
                    for pair in pairs_to_fetch:
                        try:
                            prices[pair] = self.kraken_api_readonly.get_current_price(pair)
                        except Exception:
                            prices[pair] = None
                        
            except KrakenAPIError as e:
                # Batch fetch failed entirely - log error and set all prices to None
                self.log('ERROR', f'Kraken API error batch fetching prices: {str(e)} (type: {e.error_type})', 
                        error=str(e), error_type=e.error_type)
                
                # Send notification about API error
                if self.notification_manager:
                    self.notification_manager.notify_api_error(
                        error_type=e.error_type,
                        endpoint='Ticker/get_current_prices_batch',
                        error_message=str(e),
                        details=e.details
                    )
                
                # Set all pairs to None so processing can continue (without creating orders)
                for pair in pairs_to_fetch:
                    prices[pair] = None
                    
            except Exception as e:
                # Fallback to individual fetches for non-API errors
                # This handles cases like:
                # - Batch method not implemented (test mocks)
                # - Unexpected return types
                # Note: Other exceptions should have been caught by specific handlers above
                self.log('WARNING', f'Batch fetch not available or failed unexpectedly, falling back to individual price fetches: {str(e)}')
                for pair in pairs_to_fetch:
                    try:
                        prices[pair] = self.kraken_api_readonly.get_current_price(pair)
                    except Exception:
                        prices[pair] = None

        # Step 6: Process each configuration using the cached prices where possible
        for config in configs:
            try:
                pair = config.get('pair') if isinstance(config, dict) else None
                cached_price = prices.get(pair) if pair else None
                self.process_config(config, current_price=cached_price)
            except Exception as e:
                config_id = config.get('id', 'unknown') if isinstance(config, dict) else 'unknown'
                self.log('ERROR', 
                        f'Unexpected exception processing config {config_id}: {str(e)}',
                        config_id=config_id, error=str(e))
        
        # Step 6b: Check status of triggered orders to see if they've been filled
        self.check_triggered_orders()
        
        # Step 7: Save state after processing all configs
        # SAFETY: In dry-run mode, do not save state to disk
        if not self.dry_run:
            try:
                self.save_state()
            except Exception as e:
                # Log error but don't crash - state will be saved next iteration
                self.log('ERROR', f'Failed to save state: {str(e)}',
                        error=str(e))
        else:
            self.log('DEBUG', '[DRY RUN] Not saving state to disk')
    
    def run_continuous(self, interval=60):
        """
        Run continuously, checking configurations at regular intervals.
        
        SECURITY NOTE: This function continues running even if individual
        iterations fail, but errors are logged and do not result in orders.
        
        Args:
            interval: Seconds between checks (default: 60)
        """
        # Step 1: Validate interval parameter
        if interval is None:
            self.log('ERROR', 'Interval cannot be None, using default of 60 seconds')
            interval = 60
        
        # Convert to int if needed
        try:
            interval_int = int(interval)
        except (ValueError, TypeError) as e:
            self.log('ERROR', f'Invalid interval "{interval}", using default of 60 seconds',
                    error=str(e))
            interval_int = 60
        
        # Validate interval is positive
        if interval_int <= 0:
            self.log('ERROR', f'Interval must be positive, got {interval_int}, using default of 60 seconds')
            interval_int = 60
        
        # Step 2: Log startup
        self.log('INFO', f'Starting continuous monitoring (interval: {interval_int}s)')
        
        # Step 3: Main monitoring loop
        try:
            while True:
                # Run one iteration
                # Any errors in run_once() are handled there and logged
                self.run_once()
                
                # Sleep until next iteration, but in 1s increments so interrupts like Ctrl-C
                # are handled promptly instead of blocking for the full interval.
                self.log('DEBUG', f'Sleeping for {interval_int} seconds (1s increments)')
                for _ in range(interval_int):
                    time.sleep(1)
                
        except KeyboardInterrupt:
            # User pressed Ctrl+C - shutdown gracefully
            self.log('INFO', 'Interrupted by user, shutting down')
            if self.notification_manager:
                self.notification_manager.notify_application_exit('User interrupted (Ctrl+C)')
            sys.exit(0)
        except Exception as e:
            # Unexpected exception in main loop
            # Log it and exit to prevent unknown state
            self.log('ERROR', f'Unexpected exception in main loop: {str(e)}',
                    error=str(e))
            if self.notification_manager:
                self.notification_manager.notify_application_exit(f'Exception: {str(e)}')
            sys.exit(1)


def main():
    """Main entry point."""
    # Global variable to hold notification_manager for signal handlers
    global notification_manager_global
    notification_manager_global = None
    
    def signal_handler(signum, frame):
        """Handle termination signals gracefully."""
        sig_name = signal.Signals(signum).name
        print(f"\nReceived signal {sig_name} ({signum}). Shutting down gracefully...")
        if notification_manager_global and notification_manager_global.enabled:
            notification_manager_global.notify_service_stopped(
                service_name="TTSLO Monitor",
                reason=f"Received {sig_name} signal (systemctl stop/restart or kill)"
            )
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)  # systemctl stop/restart
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGHUP, signal_handler)   # Terminal closed
    
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
    
    parser.add_argument('--config', default=os.getenv('TTSLO_CONFIG_FILE', 'config.csv'),
                       help='Configuration file (env TTSLO_CONFIG_FILE; default: config.csv)')
    parser.add_argument('--state', default=os.getenv('TTSLO_STATE_FILE', 'state.csv'),
                       help='State file (env TTSLO_STATE_FILE; default: state.csv)')
    parser.add_argument('--log', default=os.getenv('TTSLO_LOG_FILE', 'logs.csv'),
                       help='Log file (env TTSLO_LOG_FILE; default: logs.csv)')
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
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output (very verbose)')
    
    args = parser.parse_args()
    
    # Load .env file if it exists (creds module will not override existing env vars)
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
        
        # Try to get API credentials for market price validation (check env/.env/copilot secrets)
        api_key_ro, api_secret_ro = find_kraken_credentials(readwrite=False, env_file=args.env_file)

        # Create API instance if credentials available
        kraken_api = None
        if api_key_ro and api_secret_ro:
            kraken_api = KrakenAPI(api_key=api_key_ro, api_secret=api_secret_ro, debug=args.debug)
            print("Note: Validating with current market prices from Kraken API\n")
        else:
            print("Note: API credentials not found. Skipping market price validation.")
            print("      Set KRAKEN_API_KEY and KRAKEN_API_SECRET for complete validation.\n")
        
        validator = ConfigValidator(kraken_api=kraken_api, debug_mode=args.debug)
        result = validator.validate_config_file(configs)
        
        # Print formatted validation result
        print(format_validation_result(result, verbose=True))
        
        # Exit with appropriate code
        sys.exit(0 if result.is_valid() else 1)
    
    # Step 1: Get read-only API credentials (for price monitoring)
    # These are required for all operations except dry-run
    api_key_ro, api_secret_ro = find_kraken_credentials(readwrite=False, env_file=args.env_file)

    # Step 2: Get read-write API credentials (for creating orders)
    # These are only required for actual order creation
    api_key_rw, api_secret_rw = find_kraken_credentials(readwrite=True, env_file=args.env_file)
    
    # Step 3: Validate read-only credentials are present
    # SAFETY: Without read-only credentials, we cannot monitor prices
    if not api_key_ro:
        print("ERROR: Read-only API key (KRAKEN_API_KEY) is required but not set.", 
              file=sys.stderr)
        print("Use --dry-run to test without credentials.", file=sys.stderr)
        sys.exit(1)
    
    if not api_secret_ro:
        print("ERROR: Read-only API secret (KRAKEN_API_SECRET) is required but not set.", 
              file=sys.stderr)
        print("Use --dry-run to test without credentials.", file=sys.stderr)
        sys.exit(1)
    
    # Step 4: Check read-write credentials status
    has_rw_key = api_key_rw is not None and api_key_rw.strip() != ''
    has_rw_secret = api_secret_rw is not None and api_secret_rw.strip() != ''
    has_rw_creds = has_rw_key and has_rw_secret
    
    # Step 5: Warn if no read-write credentials and not in dry-run mode
    # SAFETY: Without read-write credentials, orders CANNOT be created
    if not args.dry_run and not has_rw_creds:
        print("WARNING: No read-write API credentials found. Orders CANNOT be created.", file=sys.stderr)
        print("Set KRAKEN_API_KEY_RW and KRAKEN_API_SECRET_RW to enable order creation.", file=sys.stderr)
        print("Continuing in read-only mode (monitoring only)...\n", file=sys.stderr)
    
    # Step 6: Validate configuration file path exists
    if not os.path.exists(args.config):
        print(f"ERROR: Configuration file not found: {args.config}", file=sys.stderr)
        print("Use --create-sample-config to create a sample configuration file.", file=sys.stderr)
        sys.exit(1)

    # Write a small, world-readable 'clue' file so interactive helpers (like
    # csv_editor.py) running under different users can discover the active
    # configuration path. This is optional and best-effort; failures are
    # non-fatal.
    try:
        clue_paths = [
            '/var/lib/ttslo/config_path',
            '/run/ttslo/config_path',
        ]

        for clue in clue_paths:
            try:
                clue_dir = os.path.dirname(clue)
                if not os.path.exists(clue_dir):
                    os.makedirs(clue_dir, exist_ok=True)

                # Write the config path (single line) and set permissive read
                # permissions so non-service users can read it.
                with open(clue, 'w', encoding='utf-8') as f:
                    f.write(args.config.rstrip() + '\n')
                try:
                    os.chmod(clue, 0o644)
                except Exception:
                    # Ignore chmod failures (maybe running on a platform
                    # without POSIX permissions), this is best-effort.
                    pass
            except Exception:
                # Ignore failures for individual clue files and continue
                pass
    except Exception:
        # Don't allow clue-writing to break service startup
        pass
    
    # Step 7: Initialize configuration manager
    try:
        config_manager = ConfigManager(
            config_file=args.config,
            state_file=args.state,
            log_file=args.log
        )
    except Exception as e:
        print(f"ERROR: Failed to initialize configuration manager: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Step 8: Create read-only API instance
    try:
        # Use explicit constructor if we have creds, otherwise use from_env to try discover
        if api_key_ro and api_secret_ro:
            kraken_api_readonly = KrakenAPI(api_key=api_key_ro, api_secret=api_secret_ro, debug=args.debug)
        else:
            kraken_api_readonly = KrakenAPI.from_env(readwrite=False, env_file=args.env_file, debug=args.debug)
    except Exception as e:
        print(f"ERROR: Failed to initialize read-only API: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Step 9: Create read-write API instance if credentials are available
    kraken_api_readwrite = None
    if has_rw_creds:
        try:
            # Prefer explicit credentials but allow discovery as fallback
            if api_key_rw and api_secret_rw:
                kraken_api_readwrite = KrakenAPI(api_key=api_key_rw, api_secret=api_secret_rw, debug=args.debug)
            else:
                kraken_api_readwrite = KrakenAPI.from_env(readwrite=True, env_file=args.env_file, debug=args.debug)
        except Exception as e:
            print(f"ERROR: Failed to initialize read-write API: {str(e)}", file=sys.stderr)
            # This is not fatal - we can still run in read-only mode
            print("Continuing without read-write API (orders cannot be created).", file=sys.stderr)
            kraken_api_readwrite = None
    
    # Step 10: Initialize notification manager
    # Search for notifications.ini in multiple locations
    def find_notifications_ini():
        """Find notifications.ini in order: current dir, /var/lib/ttslo, script dir."""
        search_paths = [
            'notifications.ini',  # Current working directory
            '/var/lib/ttslo/notifications.ini',  # State directory
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notifications.ini')  # Script directory
        ]
        for path in search_paths:
            if os.path.exists(path):
                return path
        return 'notifications.ini'  # Default, will fail gracefully
    
    notification_ini = find_notifications_ini()
    notification_manager = None
    try:
        notification_manager = NotificationManager(notification_ini)
        notification_manager_global = notification_manager  # Make available to signal handler
        if notification_manager.enabled:
            if args.verbose:
                print(f"Telegram notifications enabled for {len(notification_manager.recipients)} recipients (using {notification_ini})")
    except Exception as e:
        if args.verbose:
            print(f"Warning: Failed to initialize notifications: {str(e)}", file=sys.stderr)
    
    # Step 11: Initialize TTSLO application
    try:
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=kraken_api_readonly,
            kraken_api_readwrite=kraken_api_readwrite,
            dry_run=args.dry_run,
            verbose=args.verbose,
            debug=args.debug,
            notification_manager=notification_manager
        )
    except Exception as e:
        print(f"ERROR: Failed to initialize TTSLO application: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Step 12: Load initial state from file
    try:
        ttslo.load_state()
    except Exception as e:
        print(f"WARNING: Failed to load state file: {str(e)}", file=sys.stderr)
        print("Starting with empty state.", file=sys.stderr)
        # Not fatal - we can continue with empty state
    
    # Step 13: Validate configuration before starting
    # SAFETY: Do not start if configuration is invalid
    validation_passed = False
    try:
        validation_passed = ttslo.validate_and_load_config()
    except Exception as e:
        print(f"\nERROR: Configuration validation failed with exception: {str(e)}", 
              file=sys.stderr)
        sys.exit(1)
    
    if not validation_passed:
        print("\nConfiguration validation failed. Use --validate-config to see details.", 
              file=sys.stderr)
        sys.exit(1)
    
    # Step 14: Configuration is valid - log success
    if args.verbose:
        print("Configuration validation passed. Starting monitoring...\n")
    
    # Step 14.5: Send service started notification
    if notification_manager and notification_manager.enabled:
        notification_manager.notify_service_started(
            service_name="TTSLO Monitor",
            host=None,
            port=None
        )
    
    # Step 15: Run the application
    try:
        if args.once:
            # Run once and exit
            ttslo.run_once()
        else:
            # Run continuously
            ttslo.run_continuous(interval=args.interval)
    except Exception as e:
        # Catch any unexpected exceptions in main execution
        print(f"\nERROR: Unexpected exception in main execution: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        if notification_manager:
            notification_manager.notify_service_stopped(
                service_name="TTSLO Monitor",
                reason=f"Unexpected exception: {str(e)}"
            )
            notification_manager.notify_application_exit(f'Unexpected exception: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
