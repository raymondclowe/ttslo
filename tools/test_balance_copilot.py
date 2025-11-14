#!/usr/bin/env python3
"""
Test balance retrieval with Copilot credentials.

This tool tests the balance retrieval functionality using the read-only
Kraken API credentials available in the Copilot environment.
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from creds import find_kraken_credentials
from kraken_api import KrakenAPI


def test_balance_retrieval():
    """Test retrieving balance from Kraken API."""
    print("=" * 60)
    print("Testing Balance Retrieval with Copilot Credentials")
    print("=" * 60)
    
    # Find credentials
    print("\n1. Looking for credentials...")
    key, secret = find_kraken_credentials(readwrite=False)
    
    if not key or not secret:
        print("❌ ERROR: Could not find Kraken API credentials")
        print("   Expected: COPILOT_KRAKEN_API_KEY and COPILOT_KRAKEN_API_SECRET")
        return False
    
    print(f"✓ Found credentials:")
    print(f"  Key: {key[:10]}...")
    print(f"  Secret: {secret[:10]}...")
    
    # Create API instance
    print("\n2. Creating Kraken API instance...")
    try:
        api = KrakenAPI(key, secret)
        print("✓ API instance created")
    except Exception as e:
        print(f"❌ ERROR: Failed to create API instance: {e}")
        return False
    
    # Test balance retrieval
    print("\n3. Retrieving account balance...")
    try:
        balance = api.get_balance()
        print("✓ Balance retrieved successfully")
        
        if not balance:
            print("⚠️  WARNING: Balance is empty")
            return True
        
        print(f"\n4. Balance details:")
        print(f"   Found {len(balance)} asset entries:")
        
        # Show all balance entries
        for asset, amount in sorted(balance.items()):
            try:
                amount_float = float(amount)
                if amount_float > 0:
                    print(f"   - {asset}: {amount}")
            except (ValueError, TypeError):
                print(f"   - {asset}: {amount} (could not parse)")
        
        # Test DYDX specifically since that's mentioned in the issue
        print(f"\n5. Checking for DYDX-related balances:")
        dydx_found = False
        for asset in balance.keys():
            if 'DYDX' in asset.upper():
                print(f"   ✓ Found: {asset} = {balance[asset]}")
                dydx_found = True
        
        if not dydx_found:
            print("   ℹ️  No DYDX balances found (this is OK if you don't hold DYDX)")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to retrieve balance: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    success = test_balance_retrieval()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ Test completed successfully")
        sys.exit(0)
    else:
        print("❌ Test failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
