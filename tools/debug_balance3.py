#!/usr/bin/env python3
"""
More comprehensive debug tool for checking Kraken API balance
"""
import os
import sys
from ttslo import get_env_var, load_env_file
from kraken_api import KrakenAPI


def normalize_asset(asset):
    """Normalize asset key by removing X prefix and .F suffix"""
    asset = asset.upper()
    if asset.endswith('.F'):
        asset = asset[:-2]
    return asset.strip('X')


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
            
        print('\nParsed balances (with normalization):')
        print("=" * 50)
        normalized_totals = {}
        
        # First pass: collect all balances
        for asset, amount in balance.items():
            norm_asset = normalize_asset(asset)
            try:
                float_amount = float(amount)
                if norm_asset not in normalized_totals:
                    normalized_totals[norm_asset] = 0.0
                normalized_totals[norm_asset] += float_amount
            except ValueError:
                print(f"Warning: Could not parse amount for {asset}: {amount}")

        # Display normalized totals
        for norm_asset, total in normalized_totals.items():
            print(f"  {norm_asset}: {total:.8f}")
            # Show which keys contributed
            contributors = [k for k in balance.keys() if normalize_asset(k) == norm_asset]
            if len(contributors) > 1:
                print(f"    (Combined from: {', '.join(contributors)})")
        print("=" * 50)
        
        # Look for BTC balance
        btc_norm = 'BT'  # normalized form of XBT/BTC
        if btc_norm in normalized_totals:
            btc_balance = normalized_totals[btc_norm]
            print(f"\nSuccess! Found total BTC balance: {btc_balance:.8f}")
            contributors = [f"{k}: {balance[k]}" for k in balance.keys() if normalize_asset(k) == btc_norm]
            print("Contributing accounts:", contributors)
            sys.exit(0)
        else:
            print('\nBTC Balance not found! Available normalized keys:', sorted(list(normalized_totals.keys())))
            sys.exit(1)
        
    except Exception as e:
        print(f'\nError while fetching balance: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()