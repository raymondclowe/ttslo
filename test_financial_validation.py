#!/usr/bin/env python3
"""
Tests for financially responsible order validation.

This module tests the validation logic that prevents users from creating
orders that would result in buying high and selling low.
"""
import os
import sys
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validator import ConfigValidator, ValidationResult


class TestStablecoinDetection:
    """Test detection of stablecoin and BTC pairs."""
    
    def test_usd_pairs_detected_as_stablecoin(self):
        """Test that USD pairs are detected as stablecoin pairs."""
        validator = ConfigValidator()
        
        # USD variants
        assert validator._is_stablecoin_pair('XXBTZUSD') is True
        assert validator._is_stablecoin_pair('XETHZUSD') is True
        assert validator._is_stablecoin_pair('SOLUSD') is True
        
    def test_usdt_pairs_detected_as_stablecoin(self):
        """Test that USDT pairs are detected as stablecoin pairs."""
        validator = ConfigValidator()
        
        assert validator._is_stablecoin_pair('XBTUSDT') is True
        assert validator._is_stablecoin_pair('ETHUSDT') is True
        assert validator._is_stablecoin_pair('SOLUSDT') is True
        assert validator._is_stablecoin_pair('ADAUSDT') is True
        
    def test_usdc_pairs_detected_as_stablecoin(self):
        """Test that USDC pairs are detected as stablecoin pairs."""
        validator = ConfigValidator()
        
        assert validator._is_stablecoin_pair('XBTUSDC') is True
        assert validator._is_stablecoin_pair('ETHUSDC') is True
        
    def test_eur_pairs_detected_as_stablecoin(self):
        """Test that EUR pairs are detected as stablecoin pairs."""
        validator = ConfigValidator()
        
        assert validator._is_stablecoin_pair('XXBTZEUR') is True
        assert validator._is_stablecoin_pair('XETHZEUR') is True
        assert validator._is_stablecoin_pair('SOLEUR') is True
        
    def test_other_fiat_pairs_detected_as_stablecoin(self):
        """Test that GBP, JPY pairs are detected as stablecoin pairs."""
        validator = ConfigValidator()
        
        assert validator._is_stablecoin_pair('XXBTZGBP') is True
        assert validator._is_stablecoin_pair('XETHZGBP') is True
        assert validator._is_stablecoin_pair('XXBTZJPY') is True
        
    def test_btc_pairs_detected_correctly(self):
        """Test that BTC pairs are detected (for crypto-to-BTC trading)."""
        validator = ConfigValidator()
        
        assert validator._is_btc_pair('ETHXBT') is True
        assert validator._is_btc_pair('SOLXBT') is True
        assert validator._is_btc_pair('ADAXBT') is True
        assert validator._is_btc_pair('ETHXXBT') is True
        
    def test_non_stablecoin_pairs_not_detected(self):
        """Test that non-stablecoin pairs are not detected."""
        validator = ConfigValidator()
        
        # ETH-to-other-crypto pairs (not stablecoins)
        assert validator._is_stablecoin_pair('SOLETH') is False
        assert validator._is_stablecoin_pair('ADAETH') is False
        
        # Empty or invalid
        assert validator._is_stablecoin_pair('') is False
        assert validator._is_stablecoin_pair(None) is False


class TestFinanciallyResponsibleValidation:
    """Test validation of financially responsible orders."""
    
    def test_buy_low_is_valid(self):
        """Test that buy orders with 'below' threshold are valid (buy low)."""
        validator = ConfigValidator()
        result = ValidationResult()
        
        configs = [
            {
                'id': 'btc_buy_low',
                'pair': 'XXBTZUSD',
                'threshold_price': '40000',
                'threshold_type': 'below',
                'direction': 'buy',
                'volume': '0.01',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        
        # Should have no errors for this valid configuration
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) == 0, "Buy low (below + buy) should be valid"
        
    def test_sell_high_is_valid(self):
        """Test that sell orders with 'above' threshold are valid (sell high)."""
        validator = ConfigValidator()
        result = ValidationResult()
        
        configs = [
            {
                'id': 'btc_sell_high',
                'pair': 'XXBTZUSD',
                'threshold_price': '60000',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.01',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        
        # Should have no errors for this valid configuration
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) == 0, "Sell high (above + sell) should be valid"
        
    def test_buy_high_is_invalid(self):
        """Test that buy orders with 'above' threshold are invalid (buy high)."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'btc_buy_high',
                'pair': 'XXBTZUSD',
                'threshold_price': '60000',
                'threshold_type': 'above',
                'direction': 'buy',
                'volume': '0.01',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        
        # Should have an error for buying high
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) > 0, "Buy high (above + buy) should be invalid"
        assert 'Buying HIGH' in logic_errors[0]['message']
        
    def test_sell_low_is_invalid(self):
        """Test that sell orders with 'below' threshold are invalid (sell low)."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'btc_sell_low',
                'pair': 'XXBTZUSD',
                'threshold_price': '40000',
                'threshold_type': 'below',
                'direction': 'sell',
                'volume': '0.01',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        
        # Should have an error for selling low
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) > 0, "Sell low (below + sell) should be invalid"
        assert 'Selling LOW' in logic_errors[0]['message']


class TestCryptocurrencyPairs:
    """Test validation for various cryptocurrency pairs."""
    
    def test_eth_usdt_buy_low_valid(self):
        """Test ETH/USDT buy low is valid."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'eth_buy',
                'pair': 'ETHUSDT',
                'threshold_price': '2500',
                'threshold_type': 'below',
                'direction': 'buy',
                'volume': '0.1',
                'trailing_offset_percent': '3.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) == 0
        
    def test_eth_usdt_sell_high_valid(self):
        """Test ETH/USDT sell high is valid."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'eth_sell',
                'pair': 'ETHUSDT',
                'threshold_price': '3500',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.1',
                'trailing_offset_percent': '3.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) == 0
        
    def test_sol_eur_buy_high_invalid(self):
        """Test SOL/EUR buy high is invalid."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'sol_buy',
                'pair': 'SOLEUR',
                'threshold_price': '150',
                'threshold_type': 'above',
                'direction': 'buy',
                'volume': '10',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) > 0
        assert 'Buying HIGH' in logic_errors[0]['message']
        
    def test_ada_gbp_sell_low_invalid(self):
        """Test ADA/GBP sell low is invalid."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'ada_sell',
                'pair': 'ADAGBP',
                'threshold_price': '0.5',
                'threshold_type': 'below',
                'direction': 'sell',
                'volume': '100',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) > 0
        assert 'Selling LOW' in logic_errors[0]['message']


class TestBTCAsStablecoin:
    """Test that BTC is treated as a stablecoin for other crypto pairs."""
    
    def test_eth_btc_buy_low_valid(self):
        """Test ETH/BTC buy low is valid (buying ETH cheap with BTC)."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'eth_btc_buy',
                'pair': 'XETHXXBT',
                'threshold_price': '0.05',
                'threshold_type': 'below',
                'direction': 'buy',
                'volume': '0.5',
                'trailing_offset_percent': '3.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) == 0
        
    def test_eth_btc_sell_high_valid(self):
        """Test ETH/BTC sell high is valid (selling ETH expensive to BTC)."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'eth_btc_sell',
                'pair': 'XETHXXBT',
                'threshold_price': '0.08',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.5',
                'trailing_offset_percent': '3.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) == 0
        
    def test_eth_btc_buy_high_invalid(self):
        """Test ETH/BTC buy high is invalid."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'eth_btc_buy_high',
                'pair': 'XETHXXBT',
                'threshold_price': '0.08',
                'threshold_type': 'above',
                'direction': 'buy',
                'volume': '0.5',
                'trailing_offset_percent': '3.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) > 0
        assert 'Buying HIGH' in logic_errors[0]['message']
        
    def test_sol_btc_sell_low_invalid(self):
        """Test SOL/BTC sell low is invalid."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'sol_btc_sell_low',
                'pair': 'SOLXXBT',
                'threshold_price': '0.002',
                'threshold_type': 'below',
                'direction': 'sell',
                'volume': '10',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) > 0
        assert 'Selling LOW' in logic_errors[0]['message']


class TestNonStablecoinPairs:
    """Test that non-stablecoin pairs are not subject to the same validation."""
    
    def test_exotic_pairs_not_validated(self):
        """Test that exotic pairs (e.g., SOL/ETH) don't trigger validation."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'exotic_pair',
                'pair': 'SOLETH',
                'threshold_price': '0.05',
                'threshold_type': 'above',
                'direction': 'buy',
                'volume': '10',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        
        # Should not have financial responsibility errors for exotic pairs
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) == 0, "Exotic pairs should not be subject to financial validation"


class TestMultipleConfigurations:
    """Test validation of multiple configurations."""
    
    def test_mixed_valid_and_invalid(self):
        """Test that validator correctly identifies mix of valid and invalid configs."""
        validator = ConfigValidator()
        
        configs = [
            {
                'id': 'valid_buy_low',
                'pair': 'XXBTZUSD',
                'threshold_price': '40000',
                'threshold_type': 'below',
                'direction': 'buy',
                'volume': '0.01',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            },
            {
                'id': 'invalid_buy_high',
                'pair': 'ETHUSDT',
                'threshold_price': '3500',
                'threshold_type': 'above',
                'direction': 'buy',
                'volume': '0.1',
                'trailing_offset_percent': '3.0',
                'enabled': 'true'
            },
            {
                'id': 'valid_sell_high',
                'pair': 'SOLUSDT',
                'threshold_price': '150',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '10',
                'trailing_offset_percent': '5.0',
                'enabled': 'true'
            }
        ]
        
        result = validator.validate_config_file(configs)
        
        # Should have exactly 1 error for the invalid config
        logic_errors = [e for e in result.errors if e['field'] == 'logic']
        assert len(logic_errors) == 1
        assert logic_errors[0]['config_id'] == 'invalid_buy_high'
        assert 'Buying HIGH' in logic_errors[0]['message']


def run_all_tests():
    """Run all tests."""
    print("Running financial validation tests...\n")
    
    # Use pytest to run the tests
    exit_code = pytest.main([__file__, '-v'])
    return exit_code


if __name__ == "__main__":
    sys.exit(run_all_tests())
