#!/usr/bin/env python3
"""
Demonstration of Available Balance decimal formatting fix.

This script shows the before/after comparison of how balance values
are formatted in notifications.
"""
import sys
from pathlib import Path

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal
from notifications import format_balance


def demo_balance_formatting():
    """Demonstrate balance formatting for various coin balances."""
    
    print("=" * 70)
    print("AVAILABLE BALANCE DECIMAL FORMATTING DEMO")
    print("=" * 70)
    print()
    
    # Test cases simulating different coin balances
    test_cases = [
        {
            'name': 'XETH (Ethereum)',
            'balance': Decimal('0.00123456'),
            'description': 'Small fractional ETH balance'
        },
        {
            'name': 'MEME coin',
            'balance': Decimal('0.000001679'),
            'description': 'Very small meme coin balance'
        },
        {
            'name': 'BTC (Bitcoin)',
            'balance': Decimal('0.0015626064'),
            'description': 'Fractional BTC balance'
        },
        {
            'name': 'DYDX',
            'balance': Decimal('123.1595217414'),
            'description': 'Medium balance'
        },
        {
            'name': 'USD balance',
            'balance': Decimal('1234.56'),
            'description': 'Large fiat balance'
        },
        {
            'name': 'Dust balance',
            'balance': Decimal('1.23E-9'),
            'description': 'Extremely small (scientific notation)'
        },
        {
            'name': 'Zero balance',
            'balance': Decimal('0'),
            'description': 'No balance'
        },
    ]
    
    print("BEFORE (using str()):")
    print("-" * 70)
    for case in test_cases:
        before = str(case['balance'])
        print(f"{case['name']:20} | {before:20} | {case['description']}")
    
    print()
    print("AFTER (using format_balance()):")
    print("-" * 70)
    for case in test_cases:
        after = format_balance(case['balance'])
        print(f"{case['name']:20} | {after:20} | {case['description']}")
    
    print()
    print("=" * 70)
    print("KEY IMPROVEMENTS:")
    print("=" * 70)
    print("1. ✓ No scientific notation (1.23E-9 → 0)")
    print("2. ✓ Appropriate decimal places for coin type")
    print("3. ✓ Trailing zeros removed for cleaner display")
    print("4. ✓ Thousands separator for large amounts")
    print("5. ✓ Consistent with dashboard display")
    print()
    
    # Demonstrate the notification message
    print("=" * 70)
    print("EXAMPLE NOTIFICATION MESSAGE:")
    print("=" * 70)
    print()
    print("⚠️ TTSLO: Cannot create order - Insufficient balance!")
    print()
    print("Config: xeth_sell_1")
    print("Pair: XETHZUSD")
    print("Direction: sell")
    print("Required Volume: 0.01")
    print(f"Available Balance: {format_balance(Decimal('0.00123456'))}")
    print("Trigger Price: 2500.0")
    print()
    print("⚠️ Action needed: Add funds to your account or adjust the order volume.")
    print()


if __name__ == '__main__':
    demo_balance_formatting()
