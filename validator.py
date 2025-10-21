"""
Configuration validation for TTSLO.
"""
import re
from typing import List, Dict, Tuple, Optional
from decimal import Decimal, InvalidOperation, getcontext, ROUND_DOWN


class ValidationResult:
    """Result of configuration validation."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.infos = []
        self.configs = []
        self.configs_with_errors = set()  # Track which configs have errors
        
    def add_error(self, config_id: str, field: str, message: str):
        """Add a validation error."""
        self.errors.append({
            'config_id': config_id,
            'field': field,
            'message': message,
            'type': 'ERROR'
        })
        # Track this config as having errors
        self.configs_with_errors.add(config_id)
    
    def add_warning(self, config_id: str, field: str, message: str):
        """Add a validation warning."""
        self.warnings.append({
            'config_id': config_id,
            'field': field,
            'message': message,
            'type': 'WARNING'
        })
    
    def add_info(self, config_id: str, field: str, message: str):
        """Add a validation info message."""
        self.infos.append({
            'config_id': config_id,
            'field': field,
            'message': message,
            'type': 'INFO'
        })
    
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    def get_config_ids_with_errors(self) -> set:
        """Get set of config IDs that have validation errors."""
        return self.configs_with_errors.copy()


class ConfigValidator:
    """Validates TTSLO configuration files."""
    
    # Required fields in configuration
    REQUIRED_FIELDS = ['id', 'pair', 'threshold_price', 'threshold_type', 
                       'direction', 'volume', 'trailing_offset_percent', 'enabled']
    
    # Optional fields in configuration
    OPTIONAL_FIELDS = []
    
    # Valid values for certain fields
    VALID_THRESHOLD_TYPES = ['above', 'below']
    VALID_DIRECTIONS = ['buy', 'sell']
    VALID_ENABLED_VALUES = ['true', 'false', 'yes', 'no', '1', '0']
    
    def __init__(self, kraken_api=None, debug_mode=False):
        """
        Initialize the validator.
        
        Args:
            kraken_api: Optional KrakenAPI instance for fetching current prices
            debug_mode: If True, convert certain errors to warnings to allow live testing with small transactions
        """
        self.kraken_api = kraken_api
        self.debug_mode = debug_mode
        self.price_cache = {}  # Cache prices to avoid repeated API calls
        self._known_pairs_cache = None  # Cache for Kraken pairs list
    
    def validate_config_file(self, configs: List[Dict]) -> ValidationResult:
        """
        Validate a list of configuration entries.
        
        Args:
            configs: List of configuration dictionaries
            
        Returns:
            ValidationResult object with errors and warnings
        """
        result = ValidationResult()
        seen_ids = set()
        
        if not configs:
            result.add_error('general', 'config_file', 
                           'Configuration file is empty or contains no valid entries')
            return result
        
        for idx, config in enumerate(configs):
            config_id = config.get('id', f'row_{idx+1}')

            # only use enabled configs for summary
            if config.get('enabled', 'false').lower() == 'true':
                result.configs.append(config)

            # if disabled skip to next item
            if config.get('enabled', 'false').lower() not in ['true', 'yes', '1']:
                continue

            # Validate required fields
            self._validate_required_fields(config, config_id, result)
            
            # Check for duplicate IDs
            if config_id in seen_ids:
                result.add_error(config_id, 'id', 
                               f'Duplicate configuration ID: {config_id}')
            seen_ids.add(config_id)
            
            # Validate individual fields
            self._validate_id(config, config_id, result)
            self._validate_pair(config, config_id, result)
            self._validate_threshold_price(config, config_id, result)
            self._validate_threshold_type(config, config_id, result)
            self._validate_direction(config, config_id, result)
            self._validate_volume(config, config_id, result)
            self._validate_trailing_offset(config, config_id, result)
            self._validate_enabled(config, config_id, result)
            
            # Cross-field validation (warnings)
            self._validate_logic(config, config_id, result)
        
        return result
    
    def _validate_required_fields(self, config: Dict, config_id: str, 
                                  result: ValidationResult):
        """Check that all required fields are present."""
        for field in self.REQUIRED_FIELDS:
            if field not in config or not config[field] or not config[field].strip():
                result.add_error(config_id, field, 
                               f'Required field "{field}" is missing or empty')
    
    def _validate_id(self, config: Dict, config_id: str, result: ValidationResult):
        """Validate the configuration ID."""
        id_value = config.get('id', '').strip()
        if not id_value:
            return  # Already caught by required fields
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', id_value):
            result.add_error(config_id, 'id', 
                           f'ID "{id_value}" contains invalid characters. '
                           'Use only letters, numbers, underscores, and hyphens')
        
        # Check length
        if len(id_value) > 50:
            result.add_warning(config_id, 'id', 
                             f'ID "{id_value}" is very long ({len(id_value)} characters). '
                             'Consider using a shorter ID')
    
    def _get_known_pairs(self) -> set:
        """Get the set of known Kraken pairs from cache (refreshed daily)."""
        if self._known_pairs_cache is None:
            try:
                from kraken_pairs_util import get_cached_pairs
                self._known_pairs_cache = get_cached_pairs()
            except Exception:
                # If we can't fetch pairs, return empty set (validation will still work with live check)
                self._known_pairs_cache = set()
        return self._known_pairs_cache
    
    def _validate_pair(self, config: Dict, config_id: str, result: ValidationResult):
        """Validate the trading pair, including live Kraken pair check."""
        pair = config.get('pair', '').strip().upper()
        if not pair:
            return  # Already caught by required fields

        # Check format
        if not re.match(r'^[A-Z0-9]+$', pair):
            result.add_error(config_id, 'pair',
                f'Trading pair "{pair}" has invalid format. '
                'It should only contain uppercase letters and numbers')
            return

        # Check against cached Kraken pairs (refreshed daily)
        try:
            known_pairs = self._get_known_pairs()
            if known_pairs and pair not in known_pairs:
                result.add_error(
                    config_id, 'pair',
                    f'Trading pair "{pair}" is NOT a valid Kraken pair. '
                    f'Common examples: XBTUSDT (BTC/USDT), ETHUSDT (ETH/USDT), SOLUSDT (SOL/USDT). '
                    f'Check https://api.kraken.com/0/public/AssetPairs for all valid pairs.')
        except Exception as e:
            # If cached check fails, add a warning but don't fail validation
            result.add_warning(
                config_id, 'pair',
                f'Could not verify pair against Kraken pairs list: {e}')
    
    def _validate_threshold_price(self, config: Dict, config_id: str, 
                                  result: ValidationResult):
        """Validate the threshold price."""
        price_str = config.get('threshold_price', '').strip()
        if not price_str:
            return  # Already caught by required fields
        
        try:
            price = Decimal(price_str)
            if price <= 0:
                result.add_error(config_id, 'threshold_price', 
                               f'Threshold price must be positive, got: {price}')
            elif price < Decimal('0.01'):
                result.add_warning(config_id, 'threshold_price', 
                                 f'Threshold price is very small ({price}). '
                                 'Please verify this is correct')
            elif price > Decimal('1000000'):
                result.add_warning(config_id, 'threshold_price', 
                                 f'Threshold price is very large ({price}). '
                                 'Please verify this is correct')
        except (ValueError, InvalidOperation):
            result.add_error(config_id, 'threshold_price', 
                           f'Invalid threshold price: "{price_str}". '
                           'Must be a valid number (e.g., 50000, 3000.50)')
    
    def _validate_threshold_type(self, config: Dict, config_id: str, 
                                 result: ValidationResult):
        """Validate the threshold type."""
        threshold_type = config.get('threshold_type', '').strip().lower()
        if not threshold_type:
            return  # Already caught by required fields
        
        if threshold_type not in self.VALID_THRESHOLD_TYPES:
            result.add_error(config_id, 'threshold_type', 
                           f'Invalid threshold_type: "{threshold_type}". '
                           f'Must be one of: {", ".join(self.VALID_THRESHOLD_TYPES)}')
    
    def _validate_direction(self, config: Dict, config_id: str, 
                           result: ValidationResult):
        """Validate the order direction."""
        direction = config.get('direction', '').strip().lower()
        if not direction:
            return  # Already caught by required fields
        
        if direction not in self.VALID_DIRECTIONS:
            result.add_error(config_id, 'direction', 
                           f'Invalid direction: "{direction}". '
                           f'Must be one of: {", ".join(self.VALID_DIRECTIONS)}')
    
    def _validate_volume(self, config: Dict, config_id: str, result: ValidationResult):
        """Validate the trade volume."""
        volume_str = config.get('volume', '').strip()
        if not volume_str:
            return  # Already caught by required fields
        
        try:
            volume = Decimal(volume_str)
            if volume <= 0:
                result.add_error(config_id, 'volume', 
                               f'Volume must be positive, got: {volume}')
            elif volume < Decimal('0.0001'):
                result.add_warning(config_id, 'volume', 
                                 f'Volume is very small ({volume}). '
                                 'This may be below minimum order sizes for some pairs')
            elif volume > Decimal('1000'):
                result.add_warning(config_id, 'volume', 
                                 f'Volume is very large ({volume}). '
                                 'Please verify this is correct and you have sufficient balance')
        except (ValueError, InvalidOperation):
            result.add_error(config_id, 'volume', 
                           f'Invalid volume: "{volume_str}". '
                           'Must be a valid number (e.g., 0.01, 1.5)')
    
    def _validate_trailing_offset(self, config: Dict, config_id: str, 
                                  result: ValidationResult):
        """Validate the trailing offset percentage."""
        offset_str = config.get('trailing_offset_percent', '').strip()
        if not offset_str:
            return  # Already caught by required fields
        
        try:
            offset = Decimal(offset_str)
            if offset <= 0:
                result.add_error(config_id, 'trailing_offset_percent', 
                               f'Trailing offset must be positive, got: {offset}')
            elif offset < Decimal('0.1'):
                result.add_warning(config_id, 'trailing_offset_percent', 
                                 f'Trailing offset is very small ({offset}%). '
                                 'This may trigger very quickly on normal price volatility')
            elif offset > Decimal('50'):
                result.add_warning(config_id, 'trailing_offset_percent', 
                                 f'Trailing offset is very large ({offset}%). '
                                 'The order may execute immediately or never trigger')
            elif offset > Decimal('20'):
                result.add_warning(config_id, 'trailing_offset_percent', 
                                 f'Trailing offset is large ({offset}%). '
                                 'Consider if this gives enough protection')
        except (ValueError, InvalidOperation):
            result.add_error(config_id, 'trailing_offset_percent', 
                           f'Invalid trailing offset: "{offset_str}". '
                           'Must be a valid percentage number (e.g., 5.0, 3.5)')
    
    def _validate_enabled(self, config: Dict, config_id: str, 
                         result: ValidationResult):
        """Validate the enabled flag."""
        enabled = config.get('enabled', '').strip().lower()
        if not enabled:
            return  # Already caught by required fields
        
        if enabled not in self.VALID_ENABLED_VALUES:
            result.add_error(config_id, 'enabled', 
                           f'Invalid enabled value: "{enabled}". '
                           f'Must be one of: {", ".join(self.VALID_ENABLED_VALUES)} '
                           '(case-insensitive)')
    

    
    def _get_current_price(self, pair: str) -> Optional[float]:
        """
        Get current price for a trading pair.
        
        Args:
            pair: Trading pair
            
        Returns:
            Current price or None if unavailable
        """
        if not self.kraken_api:
            return None
        
        # Check cache first
        if pair in self.price_cache:
            return self.price_cache[pair]
        
        try:
            price = self.kraken_api.get_current_price(pair)
            # Store as Decimal for consistent arithmetic
            try:
                price_dec = Decimal(str(price))
            except Exception:
                return None
            self.price_cache[pair] = price_dec
            return price_dec
        except Exception:
            # If we can't get price, return None (don't fail validation)
            return None
    
    def _validate_logic(self, config: Dict, config_id: str, result: ValidationResult):
        """Validate the logical consistency of the configuration."""
        # Get values (already validated individually)
        try:
            threshold_price = Decimal(str(config.get('threshold_price', '0')))
            threshold_type = config.get('threshold_type', '').strip().lower()
            direction = config.get('direction', '').strip().lower()
            trailing_offset = Decimal(str(config.get('trailing_offset_percent', '0')))
            pair = config.get('pair', '').strip().upper()
            volume = Decimal(str(config.get('volume', '0')))
        except (InvalidOperation, ValueError, TypeError):
            return  # Skip logic validation if values are invalid
        
        # Validate financially responsible order direction
        self._validate_financially_responsible_order(config_id, pair, threshold_type, direction, result)
        
        
        # Check if trailing offset could trigger immediately
        if trailing_offset > 30:
            if threshold_type == 'above' and direction == 'sell':
                result.add_warning(config_id, 'trailing_offset_percent', 
                                 f'Large trailing offset ({trailing_offset}%) on an upward threshold. '
                                 'Order may trigger immediately if price has moved significantly')
            elif threshold_type == 'below' and direction == 'buy':
                result.add_warning(config_id, 'trailing_offset_percent', 
                                 f'Large trailing offset ({trailing_offset}%) on a downward threshold. '
                                 'Order may trigger immediately if price has moved significantly')
        
        # Validate against current market price if available
        current_price = self._get_current_price(pair)
        if current_price is not None:
            self._validate_market_price(config, config_id, threshold_price, threshold_type, 
                                       direction, trailing_offset, volume, current_price, result)
        
        # Check if sufficient balance is available (warning only)
        self._check_balance_availability(config, config_id, pair, direction, volume, result)
    
    def _validate_market_price(self, config: Dict, config_id: str, threshold_price: float,
                               threshold_type: str, direction: str, trailing_offset: float,
                               volume: float, current_price: float, result: ValidationResult):
        """
        Validate threshold price against current market price.
        
        Args:
            config: Configuration dictionary
            config_id: Configuration ID
            threshold_price: Configured threshold price
            threshold_type: 'above' or 'below'
            direction: 'buy' or 'sell'
            trailing_offset: Trailing offset percentage
            volume: Configured volume
            current_price: Current market price
            result: ValidationResult to add errors/warnings to
        """
        pair = config.get('pair', 'unknown')
        
        # Check if threshold already met (trigger would fire immediately)
        if threshold_type == 'above' and current_price >= threshold_price:
            msg = (f'Threshold price {self._format_decimal(threshold_price, 2)} is already met (current price: {self._format_decimal(current_price, 2)}). '
                   f'For "above" threshold, set price higher than current market price.')
            if self.debug_mode:
                result.add_warning(config_id, 'threshold_price', f'[DEBUG MODE] {msg}')
            else:
                result.add_error(config_id, 'threshold_price', msg)

        if threshold_type == 'below' and current_price <= threshold_price:
            msg = (f'Threshold price {self._format_decimal(threshold_price, 2)} is already met (current price: {self._format_decimal(current_price, 2)}). '
                   f'For "below" threshold, set price lower than current market price.')
            if self.debug_mode:
                result.add_warning(config_id, 'threshold_price', f'[DEBUG MODE] {msg}')
            else:
                result.add_error(config_id, 'threshold_price', msg)

        # Check for insufficient gap between threshold and current price
        # The gap should be at least large enough to accommodate the trailing offset
        try:
            price_diff_percent = abs((threshold_price - current_price) / current_price * Decimal('100'))
        except Exception:
            return

        # For reasonable operation, gap should be at least 2x the trailing offset
        min_gap_percent = trailing_offset * Decimal('2')

        if price_diff_percent < trailing_offset:
            msg = (f'Insufficient gap between threshold ({self._format_decimal(threshold_price, 2)}) and current price ({self._format_decimal(current_price, 2)}). '
                   f'Gap is {self._format_decimal(price_diff_percent, 2)}% but trailing offset is {self._format_decimal(trailing_offset, 2)}%. '
                   f'Order would trigger immediately or not work as intended.')
            if self.debug_mode:
                result.add_warning(config_id, 'threshold_price', f'[DEBUG MODE] {msg}')
            else:
                result.add_error(config_id, 'threshold_price', msg)
        elif price_diff_percent < min_gap_percent:
            result.add_warning(config_id, 'threshold_price',
                             f'Small gap between threshold ({self._format_decimal(threshold_price, 2)}) and current price ({self._format_decimal(current_price, 2)}). '
                             f'Gap is {self._format_decimal(price_diff_percent, 2)}% but trailing offset is {self._format_decimal(trailing_offset, 2)}%. '
                             f'Consider a gap of at least {self._format_decimal(min_gap_percent, 1)}% for best results.')
        
        # Check for fat-finger errors (values 10x out of normal range)
        self._check_fat_finger_protection(config, config_id, threshold_price, volume, 
                                          pair, current_price, result)
    
    def _check_fat_finger_protection(self, config: Dict, config_id: str, 
                                     threshold_price: Decimal, volume: Decimal,
                                     pair: str, current_price: Decimal, 
                                     result: ValidationResult):
        """
        Check for fat-finger errors: values that are 10x out of normal range.
        
        This validation helps prevent mistakes like:
        - Missing decimal points (0.1 typed as 01 or 1)
        - Extra zeros (0.001 typed as 0.0001)
        - Misplaced decimal points
        
        Args:
            config: Configuration dictionary
            config_id: Configuration ID
            threshold_price: Configured threshold price
            volume: Configured volume
            pair: Trading pair
            current_price: Current market price
            result: ValidationResult to add warnings to
        """
        if not self.kraken_api:
            return  # Can't check without API access
        
        # Check threshold price against recent price range
        self._check_price_against_history(config_id, threshold_price, pair, current_price, result)
        
        # Check threshold price and volume against existing orders
        self._check_against_existing_orders(config_id, threshold_price, volume, pair, result)
    
    def _check_price_against_history(self, config_id: str, threshold_price: Decimal,
                                     pair: str, current_price: Decimal,
                                     result: ValidationResult):
        """
        Check if threshold price is within reasonable range based on recent price history.
        
        Warns if price is more than 10x the recent high or less than 0.1x the recent low.
        """
        try:
            # Get recent OHLC data (last 7 days with daily candles)
            ohlc_data = self.kraken_api.get_ohlc(pair, interval=1440)
            
            if not ohlc_data:
                return  # No data available
            
            # Extract the OHLC array (skip the 'last' timestamp field)
            candles = None
            for key, value in ohlc_data.items():
                if key != 'last' and isinstance(value, list):
                    candles = value
                    break
            
            if not candles or len(candles) < 2:
                return  # Not enough data
            
            # Get highs and lows from recent candles (last 7 days)
            recent_candles = candles[-7:] if len(candles) >= 7 else candles
            highs = [Decimal(str(candle[2])) for candle in recent_candles]  # High is index 2
            lows = [Decimal(str(candle[3])) for candle in recent_candles]   # Low is index 3
            
            recent_high = max(highs)
            recent_low = min(lows)
            
            # Check if threshold is 10x above recent high
            if threshold_price > recent_high * Decimal('10'):
                result.add_warning(config_id, 'threshold_price',
                                 f'Threshold price {self._format_decimal(threshold_price, 2)} is more than 10x the recent 7-day high '
                                 f'({self._format_decimal(recent_high, 2)}). This may indicate a typo (extra zero or misplaced decimal). '
                                 f'Current price: {self._format_decimal(current_price, 2)}')
            
            # Check if threshold is 0.1x (10x less than) below recent low
            elif threshold_price < recent_low * Decimal('0.1'):
                result.add_warning(config_id, 'threshold_price',
                                 f'Threshold price {self._format_decimal(threshold_price, 2)} is less than 0.1x the recent 7-day low '
                                 f'({self._format_decimal(recent_low, 2)}). This may indicate a typo (missing zero or misplaced decimal). '
                                 f'Current price: {self._format_decimal(current_price, 2)}')
        
        except Exception:
            # Don't fail validation if historical data check fails
            # This is just a helpful warning
            pass
    
    def _check_against_existing_orders(self, config_id: str, threshold_price: Decimal,
                                       volume: Decimal, pair: str, result: ValidationResult):
        """
        Check if threshold price and volume are within reasonable range compared to existing orders.
        
        Warns if values are 10x different from existing order ranges.
        """
        try:
            # Get open orders
            open_orders_result = self.kraken_api.query_open_orders()
            open_orders = open_orders_result.get('open', {})
            
            # Also get recent closed orders (last 50)
            closed_orders_result = self.kraken_api.query_closed_orders(ofs=0)
            closed_orders = closed_orders_result.get('closed', {})
            
            # Combine all orders for this pair
            all_orders = {}
            all_orders.update(open_orders)
            all_orders.update(closed_orders)
            
            # Filter orders for the same pair
            pair_orders = []
            for order_id, order_data in all_orders.items():
                if isinstance(order_data, dict):
                    order_pair = order_data.get('descr', {}).get('pair', '')
                    if order_pair == pair:
                        pair_orders.append(order_data)
            
            if len(pair_orders) < 2:
                return  # Not enough orders to establish a pattern
            
            # Extract prices and volumes from existing orders
            prices = []
            volumes = []
            for order in pair_orders:
                descr = order.get('descr', {})
                # Get price from order description
                order_price = descr.get('price')
                if order_price and order_price != '0':
                    try:
                        prices.append(Decimal(str(order_price)))
                    except (InvalidOperation, ValueError):
                        pass
                
                # Get volume
                order_volume = order.get('vol')
                if order_volume:
                    try:
                        volumes.append(Decimal(str(order_volume)))
                    except (InvalidOperation, ValueError):
                        pass
            
            # Check threshold price against existing order prices
            if len(prices) >= 2:
                max_price = max(prices)
                min_price = min(prices)
                
                # Warn if threshold is 10x above max existing order price
                if threshold_price > max_price * Decimal('10'):
                    result.add_warning(config_id, 'threshold_price',
                                     f'Threshold price {self._format_decimal(threshold_price, 2)} is more than 10x the highest '
                                     f'price in your existing {pair} orders ({self._format_decimal(max_price, 2)}). '
                                     f'This may indicate a typo.')
                
                # Warn if threshold is 0.1x (10x less) below min existing order price
                elif min_price > 0 and threshold_price < min_price * Decimal('0.1'):
                    result.add_warning(config_id, 'threshold_price',
                                     f'Threshold price {self._format_decimal(threshold_price, 2)} is less than 0.1x the lowest '
                                     f'price in your existing {pair} orders ({self._format_decimal(min_price, 2)}). '
                                     f'This may indicate a typo.')
            
            # Check volume against existing order volumes
            if len(volumes) >= 2:
                max_volume = max(volumes)
                min_volume = min(volumes)
                
                # Warn if volume is 10x above max existing order volume
                if volume > max_volume * Decimal('10'):
                    result.add_warning(config_id, 'volume',
                                     f'Volume {self._format_decimal(volume)} is more than 10x the highest '
                                     f'volume in your existing {pair} orders ({self._format_decimal(max_volume)}). '
                                     f'This may indicate a typo.')
                
                # Warn if volume is 0.1x (10x less) below min existing order volume
                elif min_volume > 0 and volume < min_volume * Decimal('0.1'):
                    result.add_warning(config_id, 'volume',
                                     f'Volume {self._format_decimal(volume)} is less than 0.1x the lowest '
                                     f'volume in your existing {pair} orders ({self._format_decimal(min_volume)}). '
                                     f'This may indicate a typo.')
        
        except Exception:
            # Don't fail validation if order check fails
            # This is just a helpful warning
            pass
    
    def _is_stablecoin_pair(self, pair: str) -> bool:
        """
        Determine if a trading pair involves a stablecoin as the quote currency.
        
        This includes:
        - USD, USDT, USDC (traditional stablecoins)
        - EUR, GBP, JPY (fiat currencies, treated as stable)
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD', 'ETHUSDT', 'XETHZEUR')
            
        Returns:
            True if the pair quotes against a stablecoin/fiat, False otherwise
        """
        if not pair:
            return False
        
        pair_upper = pair.upper()
        
        # List of stablecoin and fiat quote currencies
        stablecoin_quotes = [
            'USDT',   # Tether
            'USDC',   # USD Coin
            'ZUSD',   # Kraken's USD notation
            'USD',    # Direct USD
            'ZEUR',   # Kraken's EUR notation
            'EUR',    # Direct EUR
            'ZGBP',   # Kraken's GBP notation
            'GBP',    # Direct GBP
            'ZJPY',   # Kraken's JPY notation
            'JPY',    # Direct JPY
            'DAI',    # DAI stablecoin
            'BUSD',   # Binance USD
        ]
        
        # Check if pair ends with any stablecoin quote currency
        for quote in stablecoin_quotes:
            if pair_upper.endswith(quote):
                return True
        
        return False
    
    def _is_btc_pair(self, pair: str) -> bool:
        """
        Determine if a trading pair involves Bitcoin (treating it as a stablecoin for other cryptos).
        
        Args:
            pair: Trading pair (e.g., 'ETHXBT', 'SOLXBT')
            
        Returns:
            True if the pair quotes against BTC, False otherwise
        """
        if not pair:
            return False
        
        pair_upper = pair.upper()
        
        # List of BTC quote notations
        btc_quotes = [
            'XBT',    # Kraken's BTC notation
            'XXBT',   # Kraken's extended BTC notation
            'BTC',    # Direct BTC
        ]
        
        # Check if pair ends with any BTC quote currency
        for quote in btc_quotes:
            if pair_upper.endswith(quote):
                return True
        
        return False
    
    def _validate_financially_responsible_order(self, config_id: str, pair: str, 
                                                threshold_type: str, direction: str,
                                                result: ValidationResult):
        """
        Validate that the order is financially responsible to prevent buying high and selling low.
        
        Rules:
        - For stablecoin pairs (BTC/USD, ETH/USDT, etc.):
          - Buy orders should follow price down: threshold_type="below", direction="buy"
          - Sell orders should follow price up: threshold_type="above", direction="sell"
        - For BTC pairs (treating BTC as stable for other cryptos like ETH/BTC):
          - Same rules apply
        
        Invalid (financially irresponsible) combinations:
        - Buying high: threshold_type="above" + direction="buy"
        - Selling low: threshold_type="below" + direction="sell"
        
        Args:
            config_id: Configuration ID
            pair: Trading pair
            threshold_type: 'above' or 'below'
            direction: 'buy' or 'sell'
            result: ValidationResult to add errors to
        """
        # Check if this is a stablecoin or BTC pair
        is_stable_pair = self._is_stablecoin_pair(pair) or self._is_btc_pair(pair)
        
        if not is_stable_pair:
            # For non-stablecoin pairs, we don't enforce this validation
            # (user might have specific strategies for exotic pairs)
            return
        
        # Check for financially irresponsible combinations
        if threshold_type == 'above' and direction == 'buy':
            # Buying when price goes up = buying high
            result.add_error(
                config_id, 'logic',
                f'Financially irresponsible order: Buying HIGH is not allowed. '
                f'For pair "{pair}", buy orders should use threshold_type="below" to buy when '
                f'price goes down (buying low). Current config would buy when price rises above '
                f'threshold, which means buying at a higher price. This could lead to financial loss.'
            )
        
        if threshold_type == 'below' and direction == 'sell':
            # Selling when price goes down = selling low
            result.add_error(
                config_id, 'logic',
                f'Financially irresponsible order: Selling LOW is not allowed. '
                f'For pair "{pair}", sell orders should use threshold_type="above" to sell when '
                f'price goes up (selling high). Current config would sell when price falls below '
                f'threshold, which means selling at a lower price. This could lead to financial loss.'
            )
    
    def _normalize_asset(self, asset: str) -> str:
        """Normalize asset key by removing X prefix and .F suffix.

        Examples:
            'XXBT' -> 'XBT' -> 'BT' (strip leading 'X' characters then return core)
            'XBT.F' -> 'XBT' -> 'BT'
        We normalize to the shortest meaningful token for matching (e.g., 'BT' for BTC/XBT).
        """
        if not asset:
            return ''
        asset = asset.upper().strip()
        # Remove funding suffix
        if asset.endswith('.F'):
            asset = asset[:-2]
        # Strip leading X or Z characters commonly used by Kraken (e.g., 'XXBT', 'XETH')
        asset = asset.lstrip('XZ')
        return asset

    def _format_decimal(self, value: Decimal, places: int = 8) -> str:
        """Format a Decimal to a fixed number of decimal places as a string."""
        try:
            quant = Decimal(f'1e-{places}')
            q = value.quantize(quant, rounding=ROUND_DOWN)
            return format(q, 'f')
        except Exception:
            # Fallback to plain string conversion
            return format(value, 'f')

    def _check_balance_availability(self, config: Dict, config_id: str, pair: str, 
                                    direction: str, volume: float, result: ValidationResult):
        """
        Check if sufficient balance is available for the trade.
        This is a WARNING only, not an error, as users can add coins later.
        
        Args:
            config: Configuration dictionary
            config_id: Configuration ID
            pair: Trading pair (e.g., 'XXBTZUSD')
            direction: 'buy' or 'sell'
            volume: Volume to trade
            result: ValidationResult to add warnings to
        """
        # Only check balance if we have a KrakenAPI instance with credentials
        if not self.kraken_api:
            return

        # Use Decimal for currency and volume arithmetic to avoid floating point issues
        getcontext().prec = 28
        try:
            # Get account balance
            balance = self.kraken_api.get_balance()
            if not balance:
                return  # Can't validate without balance data

            # Extract base asset from pair
            base_asset = self._extract_base_asset(pair)
            if not base_asset:
                return  # Can't determine asset

            # For sell orders, check if we have enough of the base asset
            if direction == 'sell':
                # Normalize all balance keys and sum totals for each normalized asset
                normalized_totals = {}
                contributors = {}
                for k, v in balance.items():
                    try:
                        # Kraken returns strings for balances; coerce to Decimal safely
                        amount = Decimal(str(v))
                    except (InvalidOperation, Exception):
                        # Skip unparsable entries
                        continue
                    norm = self._normalize_asset(k)
                    if not norm:
                        continue
                    normalized_totals.setdefault(norm, Decimal('0'))
                    normalized_totals[norm] += amount
                    contributors.setdefault(norm, []).append((k, amount))

                # Normalize the base_asset for lookup
                canonical_norm = self._normalize_asset(base_asset)

                available = normalized_totals.get(canonical_norm, Decimal('0'))
                contrib = contributors.get(canonical_norm, [])

                # Convert configured volume to Decimal for correct comparison
                try:
                    volume_dec = Decimal(str(volume)) if not isinstance(volume, Decimal) else volume
                except (InvalidOperation, Exception):
                    # If we can't parse the configured volume, skip balance check
                    return

                # Add balance information - INFO when sufficient, WARNING when insufficient
                if contrib:
                    contrib_str = ', '.join([f"{k}={self._format_decimal(amt)}" for k, amt in contrib])
                    
                    if available >= volume_dec:
                        # Sufficient balance - add as INFO (only shown in verbose/debug mode)
                        result.add_info(
                            config_id,
                            'balance',
                            f'Available {base_asset} (spot+funding): {self._format_decimal(available)} (Contributors: {contrib_str}) — sufficient for required volume {self._format_decimal(volume_dec)}'
                        )
                    else:
                        # Insufficient balance - add as WARNING
                        result.add_warning(
                            config_id,
                            'balance',
                            f'Available {base_asset} (spot+funding): {self._format_decimal(available)} (Contributors: {contrib_str}) — insufficient for required volume {self._format_decimal(volume_dec)}'
                        )
                        # Also add a specific volume warning
                        result.add_warning(
                            config_id,
                            'volume',
                            f'Insufficient {base_asset} balance for sell order. '
                            f'Required: {self._format_decimal(volume_dec)}, Available: {self._format_decimal(available)}. '
                            f'You can add funds before the order triggers.'
                        )
            # For buy orders, we would need to check quote currency (e.g., USD)
            # but this is more complex as we need the price, so we'll skip for now
            # and focus on the more common sell case

        except Exception as e:
            # Don't fail validation if balance check fails
            # This is just a helpful warning, not critical
            pass
    
    def _extract_base_asset(self, pair: str) -> Optional[str]:
        """
        Extract the base asset from a trading pair.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD', 'XETHZUSD', 'SOLUSD')
            
        Returns:
            Base asset code (e.g., 'XBT', 'XETH', 'SOL') or None if can't determine
        """
        # Known mappings for common pairs
        pair_mappings = {
            'XBTUSDT': 'XXBT',
            'XBTUSD': 'XXBT',
            'XXBTZEUR': 'XXBT',
            'XXBTZGBP': 'XXBT',
            'ETHUSDT': 'XETH',
            'ETHUSD': 'XETH',
            'XETHZEUR': 'XETH',
            'SOLUSDT': 'SOL',
            'SOLEUR': 'SOL',
            'ADAUSDT': 'ADA',
            'DOTUSDT': 'DOT',
            'AVAXUSDT': 'AVAX',
            'LINKUSDT': 'LINK',
            'USDTZUSD': 'USDT',
            'USDCUSDT': 'USDC',
        }
        
        # Check if we have a known mapping
        if pair in pair_mappings:
            return pair_mappings[pair]
        
        # Try to extract from pattern
        # Most pairs end with 'USDT', 'EUR', 'GBP', 'JPY', etc.
        for quote in ['USDT', 'ZUSD', 'ZEUR', 'EUR', 'ZGBP', 'GBP', 'ZJPY', 'JPY']:
            if pair.endswith(quote):
                base = pair[:-len(quote)]
                if base:
                    return base
        
        # Couldn't determine base asset
        return None


def format_validation_result(result: ValidationResult, verbose: bool = False) -> str:
    """
    Format validation result as human-readable text.
    
    Args:
        result: ValidationResult object
        verbose: If True, include detailed information
        
    Returns:
        Formatted string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("CONFIGURATION VALIDATION REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    # Summary
    total_configs = len(result.configs)
    error_count = len(result.errors)
    warning_count = len(result.warnings)
    
    if result.is_valid():
        lines.append(f"✓ VALIDATION PASSED")
    else:
        lines.append(f"✗ VALIDATION FAILED")
    
    lines.append("")
    lines.append(f"Configurations checked: {total_configs}")
    lines.append(f"Errors found: {error_count}")
    lines.append(f"Warnings found: {warning_count}")
    lines.append("")
    
    # Errors
    if result.errors:
        lines.append("=" * 80)
        lines.append("ERRORS (must be fixed)")
        lines.append("=" * 80)
        for error in result.errors:
            lines.append(f"  [{error['config_id']}] {error['field']}")
            lines.append(f"    ✗ {error['message']}")
            lines.append("")
    
    # Warnings
    if result.warnings:
        lines.append("=" * 80)
        lines.append("WARNINGS (please review)")
        lines.append("=" * 80)
        for warning in result.warnings:
            lines.append(f"  [{warning['config_id']}] {warning['field']}")
            lines.append(f"    ⚠ {warning['message']}")
            lines.append("")
    
    # Info messages (only shown in verbose mode)
    if verbose and hasattr(result, 'infos') and result.infos:
        lines.append("=" * 80)
        lines.append("INFO (verbose mode)")
        lines.append("=" * 80)
        for info in result.infos:
            lines.append(f"  [{info['config_id']}] {info['field']}")
            lines.append(f"    ℹ {info['message']}")
            lines.append("")
    
    # Show what will be executed (if valid or verbose)
    if (result.is_valid() or verbose) and result.configs:
        lines.append("=" * 80)
        lines.append("CONFIGURATION SUMMARY")
        lines.append("=" * 80)
        lines.append("")
        
        for config in result.configs:
            config_id = config.get('id', 'unknown')
            enabled = config.get('enabled', 'unknown').lower()
            
            status = "✓ ACTIVE" if enabled in ['true', 'yes', '1'] else "⊘ DISABLED"
            
            lines.append(f"[{config_id}] {status}")
            lines.append(f"  Pair: {config.get('pair', 'N/A')}")
            lines.append(f"  Trigger: When price goes {config.get('threshold_type', 'N/A')} "
                        f"{config.get('threshold_price', 'N/A')}")
            lines.append(f"  Action: Create {config.get('direction', 'N/A').upper()} trailing stop loss")
            lines.append(f"  Volume: {config.get('volume', 'N/A')}")
            lines.append(f"  Trailing offset: {config.get('trailing_offset_percent', 'N/A')}%")
            lines.append("")
    
    lines.append("=" * 80)
    
    if result.is_valid() and not result.has_warnings():
        lines.append("✓ Configuration is ready to use!")
    elif result.is_valid() and result.has_warnings():
        lines.append("⚠ Configuration is valid but has warnings. Please review.")
    else:
        lines.append("✗ Please fix errors before running.")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)


def _cli_main():
    """
    Minimal CLI for validator.py so it can be executed directly under a debugger.

    This module is primarily a library (provides ConfigValidator and helpers).
    The CLI here is intentionally lightweight: it shows help and provides a
    convenience "--dry-run" switch so launching the module from the VSCode
    debugger or direct `python validator.py` produces visible output.
    """
    import argparse
    parser = argparse.ArgumentParser(
        description='validator.py - library module for configuration validation (lightweight CLI)'
    )
    parser.add_argument('--dry-run', action='store_true', help="No-op run (useful when launching under a debugger)")
    parser.add_argument('--verbose', action='store_true', help='Show an informational message')

    args = parser.parse_args()

    print("validator.py is a library module. Use ttslo.py as the application entry point (see README).")
    if args.verbose:
        print("You ran validator.py with --verbose; this is a lightweight CLI for debugging.")
    if args.dry_run:
        print("Dry run: exiting without performing validation.")


if __name__ == '__main__':
    _cli_main()
