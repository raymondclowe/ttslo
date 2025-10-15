#!/usr/bin/env python3
"""
Debug tool for checking Kraken API balance
"""
import os
import sys
from ttslo import get_env_var, load_env_file
from kraken_api import KrakenAPI


def main():
    # Load .env file if it exists
    load_env_file('.env')

    # Get API credentials checking both standard and copilot_ prefixed versions
    api_key = get_env_var('KRAKEN_API_KEY_RW') or get_env_var('KRAKEN_API_KEY')
    api_secret = get_env_var('KRAKEN_API_SECRET_RW') or get_env_var('KRAKEN_API_SECRET')

    if not api_key or not api_secret:
        print('API credentials are not set. Please set KRAKEN_API_KEY and KRAKEN_API_SECRET (or their RW equivalents).')
        sys.exit(1)

    # Instantiate Kraken API client
    api = KrakenAPI(api_key=api_key, api_secret=api_secret)
    
    try:
        print("\nQuerying Kraken API for balance...")
        balance = api.get_balance()
        
        print("\nRaw Kraken API Balance Response:")
        print("=" * 50)
        print(f"{balance}")
        print("=" * 50)
        
        if not balance:
            print("\nERROR: Empty balance response from API")
            sys.exit(1)
            
        print('\nParsed balances:')
        print("=" * 50)
        for asset, amount in balance.items():
            print(f"  {asset}: {amount}")
        print("=" * 50)
        
        # Look for BTC balance under various keys
        btc_keys = ['XXBT', 'XBT', 'BTC']
        btc_balance = None
        btc_key = None
        
        print('\nLooking for BTC balance under known keys:')
        for key in btc_keys:
            print(f"Checking key '{key}'...")
            if key in balance:
                try:
                    btc_balance = float(balance[key])
                    btc_key = key
                    print(f"  ✓ Found BTC balance under '{key}': {btc_balance}")
                    break
                except Exception as e:
                    print(f"  ✗ Error parsing value under '{key}': {e}")
            else:
                print(f"  - Key '{key}' not found")
                
        if btc_balance is None:
            print('\nBTC Balance not found! Available keys:', sorted(list(balance.keys())))
            sys.exit(1)
        
        print(f"\nSuccess! Found BTC balance: {btc_balance} under key '{btc_key}'")
        sys.exit(0)
        
    except Exception as e:
        print(f'\nError while fetching balance: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()