#!/usr/bin/env python3
"""
Demo script to show debug mode validation behavior.

This script creates two configurations:
1. One with threshold already met (would normally be an ERROR)
2. One with insufficient gap (would normally be an ERROR)

Then runs validation in both normal and debug mode to show the difference.
"""
import tempfile
import csv
from decimal import Decimal
from validator import ConfigValidator


class FakeKrakenAPI:
    """Mock Kraken API for demo."""
    
    def __init__(self, current_price):
        self._current_price = current_price
    
    def get_current_price(self, pair):
        """Return current price for the pair."""
        return self._current_price
    
    def get_ohlc(self, pair, interval=1440, since=None):
        """Return empty OHLC data."""
        return {}
    
    def query_open_orders(self, trades=False, userref=None):
        """Return empty open orders."""
        return {'open': {}}
    
    def query_closed_orders(self, trades=False, userref=None, start=None, end=None, ofs=None, closetime='both'):
        """Return empty closed orders."""
        return {'closed': {}}
    
    def get_balance(self):
        """Return account balance."""
        return {}


def demo_validation_modes():
    """Demonstrate the difference between normal and debug mode validation."""
    
    # Create test configurations
    # Current BTC price is $50,000
    configs = [
        {
            'id': 'already_met',
            'pair': 'XBTUSDT',
            'threshold_price': '45000',  # Already met (current: 50000)
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        },
        {
            'id': 'insufficient_gap',
            'pair': 'XBTUSDT',
            'threshold_price': '50500',  # Only 1% gap, but needs 5%
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    # Create fake API with current price of 50000
    api = FakeKrakenAPI(current_price=Decimal('50000'))
    
    print("=" * 80)
    print("DEBUG MODE VALIDATION DEMO")
    print("=" * 80)
    print()
    print("Current BTC price: $50,000")
    print()
    print("Test configurations:")
    print("  1. Threshold: $45,000 (ABOVE) - Already met (ERROR in normal mode)")
    print("  2. Threshold: $50,500 (ABOVE) - Insufficient gap (ERROR in normal mode)")
    print()
    
    # Test 1: Normal mode (errors)
    print("=" * 80)
    print("NORMAL MODE (without --debug flag)")
    print("=" * 80)
    print()
    
    validator = ConfigValidator(kraken_api=api, debug_mode=False)
    result = validator.validate_config_file(configs)
    
    print(f"Validation result: {'PASSED ✓' if result.is_valid() else 'FAILED ✗'}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    print()
    
    if result.errors:
        print("ERRORS (prevent execution):")
        for error in result.errors:
            print(f"  [{error['config_id']}] {error['message']}")
        print()
    
    # Test 2: Debug mode (warnings)
    print("=" * 80)
    print("DEBUG MODE (with --debug flag)")
    print("=" * 80)
    print()
    
    validator = ConfigValidator(kraken_api=api, debug_mode=True)
    result = validator.validate_config_file(configs)
    
    print(f"Validation result: {'PASSED ✓' if result.is_valid() else 'FAILED ✗'}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    print()
    
    if result.warnings:
        print("WARNINGS (execution allowed, but review recommended):")
        for warning in result.warnings:
            if 'DEBUG MODE' in warning['message']:
                print(f"  [{warning['config_id']}] {warning['message'][:80]}...")
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("• Normal mode: Validation FAILS with ERRORS")
    print("  → Configuration cannot be executed")
    print("  → Orders will NOT be placed")
    print()
    print("• Debug mode: Validation PASSES with WARNINGS")
    print("  → Configuration can be executed for live testing")
    print("  → Orders WILL be placed (use small volumes!)")
    print("  → Warnings are prefixed with [DEBUG MODE]")
    print()
    print("Use debug mode for:")
    print("  • Testing configurations with small volumes")
    print("  • Live testing before committing to larger trades")
    print("  • Debugging configuration issues")
    print()
    print("=" * 80)


if __name__ == '__main__':
    demo_validation_modes()
