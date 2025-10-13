"""
Configuration validation for TTSLO.
"""
import re
from typing import List, Dict, Tuple, Optional


class ValidationResult:
    """Result of configuration validation."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.configs = []
        
    def add_error(self, config_id: str, field: str, message: str):
        """Add a validation error."""
        self.errors.append({
            'config_id': config_id,
            'field': field,
            'message': message,
            'type': 'ERROR'
        })
    
    def add_warning(self, config_id: str, field: str, message: str):
        """Add a validation warning."""
        self.warnings.append({
            'config_id': config_id,
            'field': field,
            'message': message,
            'type': 'WARNING'
        })
    
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class ConfigValidator:
    """Validates TTSLO configuration files."""
    
    # Known Kraken trading pairs (common ones)
    KNOWN_PAIRS = {
        # Bitcoin
        'XXBTZUSD', 'XBTCUSD', 'XXBTZEUR', 'XXBTZGBP', 'XXBTZJPY',
        # Ethereum
        'XETHZUSD', 'ETHCUSD', 'XETHZEUR', 'XETHZGBP', 'XETHZJPY',
        # Solana
        'SOLUSD', 'SOLEUR', 'SOLGBP',
        # Cardano
        'ADAUSD', 'ADAEUR', 'ADAGBP',
        # Polkadot
        'DOTUSD', 'DOTEUR', 'DOTGBP',
        # Avalanche
        'AVAXUSD', 'AVAXEUR',
        # Chainlink
        'LINKUSD', 'LINKEUR',
        # Other major pairs
        'USDTUSD', 'USDCUSD', 'DAIUSD',
        # Legacy format
        'XBTCZUSD', 'ETHZUSD',
    }
    
    # Required fields in configuration
    REQUIRED_FIELDS = ['id', 'pair', 'threshold_price', 'threshold_type', 
                       'direction', 'volume', 'trailing_offset_percent', 'enabled']
    
    # Valid values for certain fields
    VALID_THRESHOLD_TYPES = ['above', 'below']
    VALID_DIRECTIONS = ['buy', 'sell']
    VALID_ENABLED_VALUES = ['true', 'false', 'yes', 'no', '1', '0']
    
    def __init__(self):
        """Initialize the validator."""
        pass
    
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
            result.configs.append(config)
            
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
    
    def _validate_pair(self, config: Dict, config_id: str, result: ValidationResult):
        """Validate the trading pair."""
        pair = config.get('pair', '').strip().upper()
        if not pair:
            return  # Already caught by required fields
        
        # Check if it's a known pair
        if pair not in self.KNOWN_PAIRS:
            result.add_warning(config_id, 'pair', 
                             f'Trading pair "{pair}" is not in the list of known pairs. '
                             f'Please verify this is a valid Kraken pair. '
                             f'Common examples: XXBTZUSD (BTC/USD), XETHZUSD (ETH/USD), SOLUSD (SOL/USD)')
        
        # Check format
        if not re.match(r'^[A-Z0-9]+$', pair):
            result.add_error(config_id, 'pair', 
                           f'Trading pair "{pair}" has invalid format. '
                           'It should only contain uppercase letters and numbers')
    
    def _validate_threshold_price(self, config: Dict, config_id: str, 
                                  result: ValidationResult):
        """Validate the threshold price."""
        price_str = config.get('threshold_price', '').strip()
        if not price_str:
            return  # Already caught by required fields
        
        try:
            price = float(price_str)
            if price <= 0:
                result.add_error(config_id, 'threshold_price', 
                               f'Threshold price must be positive, got: {price}')
            elif price < 0.01:
                result.add_warning(config_id, 'threshold_price', 
                                 f'Threshold price is very small ({price}). '
                                 'Please verify this is correct')
            elif price > 1000000:
                result.add_warning(config_id, 'threshold_price', 
                                 f'Threshold price is very large ({price}). '
                                 'Please verify this is correct')
        except ValueError:
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
            volume = float(volume_str)
            if volume <= 0:
                result.add_error(config_id, 'volume', 
                               f'Volume must be positive, got: {volume}')
            elif volume < 0.0001:
                result.add_warning(config_id, 'volume', 
                                 f'Volume is very small ({volume}). '
                                 'This may be below minimum order sizes for some pairs')
            elif volume > 1000:
                result.add_warning(config_id, 'volume', 
                                 f'Volume is very large ({volume}). '
                                 'Please verify this is correct and you have sufficient balance')
        except ValueError:
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
            offset = float(offset_str)
            if offset <= 0:
                result.add_error(config_id, 'trailing_offset_percent', 
                               f'Trailing offset must be positive, got: {offset}')
            elif offset < 0.1:
                result.add_warning(config_id, 'trailing_offset_percent', 
                                 f'Trailing offset is very small ({offset}%). '
                                 'This may trigger very quickly on normal price volatility')
            elif offset > 50:
                result.add_warning(config_id, 'trailing_offset_percent', 
                                 f'Trailing offset is very large ({offset}%). '
                                 'The order may execute immediately or never trigger')
            elif offset > 20:
                result.add_warning(config_id, 'trailing_offset_percent', 
                                 f'Trailing offset is large ({offset}%). '
                                 'Consider if this gives enough protection')
        except ValueError:
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
    
    def _validate_logic(self, config: Dict, config_id: str, result: ValidationResult):
        """Validate the logical consistency of the configuration."""
        # Get values (already validated individually)
        try:
            threshold_price = float(config.get('threshold_price', 0))
            threshold_type = config.get('threshold_type', '').strip().lower()
            direction = config.get('direction', '').strip().lower()
            trailing_offset = float(config.get('trailing_offset_percent', 0))
        except (ValueError, TypeError):
            return  # Skip logic validation if values are invalid
        
        # Check for nonsensical combinations
        if threshold_type == 'above' and direction == 'buy':
            result.add_warning(config_id, 'logic', 
                             'Threshold "above" with direction "buy" is unusual. '
                             'This will buy when price goes up. Verify this is intended.')
        
        if threshold_type == 'below' and direction == 'sell':
            result.add_warning(config_id, 'logic', 
                             'Threshold "below" with direction "sell" is unusual. '
                             'This will sell when price goes down. Verify this is intended.')
        
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
