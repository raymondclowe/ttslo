#!/usr/bin/env python3
"""
Demo script to show financially responsible order validation in action.

This script demonstrates the new validation that prevents users from
creating orders that would result in buying high and selling low.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validator import ConfigValidator


def demo_validation():
    """Demonstrate the validation with various scenarios."""
    
    print("=" * 80)
    print("FINANCIALLY RESPONSIBLE ORDER VALIDATION DEMO")
    print("=" * 80)
    print()
    
    validator = ConfigValidator()
    
    # Scenario 1: Valid - Buy Low (BTC/USD)
    print("Scenario 1: BTC/USD - Buy Low (VALID)")
    print("-" * 80)
    configs = [{
        'id': 'btc_buy_low',
        'pair': 'XXBTZUSD',
        'threshold_price': '40000',
        'threshold_type': 'below',
        'direction': 'buy',
        'volume': '0.01',
        'trailing_offset_percent': '5.0',
        'enabled': 'true'
    }]
    result = validator.validate_config_file(configs)
    print(f"✅ Valid: {result.is_valid()}")
    print(f"Explanation: Buying BTC when price goes BELOW $40k = buying low (smart!)")
    print()
    
    # Scenario 2: Valid - Sell High (BTC/USD)
    print("Scenario 2: BTC/USD - Sell High (VALID)")
    print("-" * 80)
    configs = [{
        'id': 'btc_sell_high',
        'pair': 'XXBTZUSD',
        'threshold_price': '60000',
        'threshold_type': 'above',
        'direction': 'sell',
        'volume': '0.01',
        'trailing_offset_percent': '5.0',
        'enabled': 'true'
    }]
    result = validator.validate_config_file(configs)
    print(f"✅ Valid: {result.is_valid()}")
    print(f"Explanation: Selling BTC when price goes ABOVE $60k = selling high (smart!)")
    print()
    
    # Scenario 3: Invalid - Buy High (BTC/USD)
    print("Scenario 3: BTC/USD - Buy High (INVALID)")
    print("-" * 80)
    configs = [{
        'id': 'btc_buy_high',
        'pair': 'XXBTZUSD',
        'threshold_price': '60000',
        'threshold_type': 'above',
        'direction': 'buy',
        'volume': '0.01',
        'trailing_offset_percent': '5.0',
        'enabled': 'true'
    }]
    result = validator.validate_config_file(configs)
    print(f"❌ Valid: {result.is_valid()}")
    print(f"Errors: {len(result.errors)}")
    if result.errors:
        print(f"Error message: {result.errors[0]['message']}")
    print(f"Explanation: Buying BTC when price goes ABOVE $60k = buying high (dangerous!)")
    print()
    
    # Scenario 4: Invalid - Sell Low (ETH/USDT)
    print("Scenario 4: ETH/USDT - Sell Low (INVALID)")
    print("-" * 80)
    configs = [{
        'id': 'eth_sell_low',
        'pair': 'ETHUSDT',
        'threshold_price': '2500',
        'threshold_type': 'below',
        'direction': 'sell',
        'volume': '0.1',
        'trailing_offset_percent': '3.0',
        'enabled': 'true'
    }]
    result = validator.validate_config_file(configs)
    print(f"❌ Valid: {result.is_valid()}")
    print(f"Errors: {len(result.errors)}")
    if result.errors:
        print(f"Error message: {result.errors[0]['message']}")
    print(f"Explanation: Selling ETH when price goes BELOW $2500 = selling low (dangerous!)")
    print()
    
    # Scenario 5: Valid - ETH/BTC Buy Low (BTC treated as stablecoin)
    print("Scenario 5: ETH/BTC - Buy Low (VALID)")
    print("-" * 80)
    configs = [{
        'id': 'eth_btc_buy',
        'pair': 'XETHXXBT',
        'threshold_price': '0.05',
        'threshold_type': 'below',
        'direction': 'buy',
        'volume': '0.5',
        'trailing_offset_percent': '3.0',
        'enabled': 'true'
    }]
    result = validator.validate_config_file(configs)
    print(f"✅ Valid: {result.is_valid()}")
    print(f"Explanation: Buying ETH cheap with BTC (when ETH/BTC ratio goes below 0.05)")
    print()
    
    # Scenario 6: Not validated - Exotic pair (SOL/ETH)
    print("Scenario 6: SOL/ETH - Exotic Pair (NOT VALIDATED)")
    print("-" * 80)
    configs = [{
        'id': 'exotic_pair',
        'pair': 'SOLETH',
        'threshold_price': '0.05',
        'threshold_type': 'above',
        'direction': 'buy',
        'volume': '10',
        'trailing_offset_percent': '5.0',
        'enabled': 'true'
    }]
    result = validator.validate_config_file(configs)
    print(f"✅ Valid: {result.is_valid()}")
    print(f"Explanation: Exotic pairs are not subject to financial validation")
    print(f"(user may have specific trading strategies)")
    print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("The validator enforces financially responsible orders for:")
    print("• Stablecoin pairs: USD, USDT, USDC, EUR, GBP, JPY")
    print("• BTC pairs: ETH/BTC, SOL/BTC, etc. (BTC treated as stable)")
    print()
    print("Valid combinations:")
    print("✅ Buy Low:  threshold_type='below' + direction='buy'")
    print("✅ Sell High: threshold_type='above' + direction='sell'")
    print()
    print("Invalid combinations (blocked with ERROR):")
    print("❌ Buy High:  threshold_type='above' + direction='buy'")
    print("❌ Sell Low:  threshold_type='below' + direction='sell'")
    print("=" * 80)


if __name__ == "__main__":
    demo_validation()
