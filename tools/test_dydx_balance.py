#!/usr/bin/env python3
"""
Test DYDXUSD balance checking with actual Kraken API.

This tool simulates the balance check that would happen when a DYDXUSD
sell order is triggered, using the live Kraken API with Copilot credentials.
"""
import os
import sys
from decimal import Decimal, getcontext

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from creds import find_kraken_credentials
from kraken_api import KrakenAPI


def normalize_asset(asset: str) -> str:
    """Normalize asset key by removing X prefix and .F suffix."""
    if not asset:
        return ''
    asset = asset.upper().strip()
    # Remove funding suffix
    if asset.endswith('.F'):
        asset = asset[:-2]
    # Strip leading X or Z characters commonly used by Kraken
    asset = asset.lstrip('XZ')
    return asset


def extract_base_asset(pair: str) -> str:
    """Extract the base asset from a trading pair."""
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


def check_balance_for_pair(api, pair, volume):
    """Check if there is sufficient balance to sell the specified volume."""
    print(f"\n{'='*60}")
    print(f"Checking balance for {pair}")
    print(f"{'='*60}")
    
    # Step 1: Extract base asset
    print(f"\n1. Extracting base asset from pair '{pair}'...")
    base_asset = extract_base_asset(pair)
    if not base_asset:
        print(f"   ❌ ERROR: Could not extract base asset from pair: {pair}")
        return False
    print(f"   ✓ Base asset: {base_asset}")
    
    # Step 2: Normalize base asset
    canonical_norm = normalize_asset(base_asset)
    print(f"   ✓ Normalized: {canonical_norm}")
    
    # Step 3: Get balance
    print(f"\n2. Retrieving account balance...")
    try:
        balance = api.get_balance()
        if not balance:
            print(f"   ❌ ERROR: Could not retrieve account balance")
            return False
        print(f"   ✓ Retrieved {len(balance)} asset entries")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False
    
    # Step 4: Normalize all balance keys and sum totals
    print(f"\n3. Processing balance entries...")
    getcontext().prec = 28
    normalized_totals = {}
    contributors = {}
    
    for k, v in balance.items():
        try:
            amount = Decimal(str(v))
        except Exception:
            continue
            
        norm = normalize_asset(k)
        if not norm:
            continue
            
        normalized_totals.setdefault(norm, Decimal('0'))
        normalized_totals[norm] += amount
        contributors.setdefault(norm, []).append((k, amount))
    
    # Step 5: Get available balance for the asset
    available = normalized_totals.get(canonical_norm, Decimal('0'))
    contrib = contributors.get(canonical_norm, [])
    
    print(f"   Asset: {canonical_norm}")
    print(f"   Contributors:")
    for k, amount in contrib:
        print(f"     - {k}: {amount}")
    print(f"   Total available: {available}")
    
    # Step 6: Check if sufficient
    try:
        volume_dec = Decimal(str(volume))
    except Exception as e:
        print(f"   ❌ ERROR: Invalid volume value: {volume}")
        return False
    
    print(f"\n4. Checking sufficiency...")
    print(f"   Required: {volume_dec}")
    print(f"   Available: {available}")
    
    if available >= volume_dec:
        print(f"   ✓ SUFFICIENT: {available} >= {volume_dec}")
        return True
    else:
        print(f"   ❌ INSUFFICIENT: {available} < {volume_dec}")
        return False


def main():
    """Main entry point."""
    print("=" * 60)
    print("DYDXUSD Balance Check Test")
    print("=" * 60)
    
    # Find credentials
    print("\n1. Looking for credentials...")
    key, secret = find_kraken_credentials(readwrite=False)
    
    if not key or not secret:
        print("❌ ERROR: Could not find Kraken API credentials")
        return 1
    
    print(f"✓ Found credentials")
    
    # Create API instance
    print("\n2. Creating Kraken API instance...")
    try:
        api = KrakenAPI(key, secret)
        print("✓ API instance created")
    except Exception as e:
        print(f"❌ ERROR: Failed to create API instance: {e}")
        return 1
    
    # Test DYDXUSD with the volume from the error message
    pair = 'DYDXUSD'
    volume = 18.4712445
    
    success = check_balance_for_pair(api, pair, volume)
    
    # Also test a few other common pairs to ensure USD suffix works
    print(f"\n\n{'='*60}")
    print("Testing other USD pairs...")
    print(f"{'='*60}")
    
    other_tests = [
        ('SOLUSD', 1.0),
        ('ATOMUSD', 1.0),
    ]
    
    for test_pair, test_volume in other_tests:
        check_balance_for_pair(api, test_pair, test_volume)
    
    print("\n" + "=" * 60)
    if success:
        print("✓ DYDXUSD balance check: PASSED")
        print("  Balance is sufficient for the requested sell order")
        return 0
    else:
        print("⚠️  DYDXUSD balance check: INSUFFICIENT")
        print("  You need to add more DYDX or reduce the order volume")
        return 0  # Not an error - just informational


if __name__ == '__main__':
    sys.exit(main())
