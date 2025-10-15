import os

from kraken_api import KrakenAPI


def main():
    # Get API credentials from environment variables
    api_key = os.environ.get('KRAKEN_API_KEY_RW') or os.environ.get('KRAKEN_API_KEY')
    api_secret = os.environ.get('KRAKEN_API_SECRET_RW') or os.environ.get('KRAKEN_API_SECRET')

    if not api_key or not api_secret:
        print('API credentials are not set. Please set KRAKEN_API_KEY and KRAKEN_API_SECRET (or their RW equivalents).')
        return

    # Instantiate Kraken API client
    api = KrakenAPI(api_key=api_key, api_secret=api_secret)
    
    try:
        balance = api.get_balance()
    except Exception as e:
        print(f'Error while fetching balance: {e}')
        return
    
    print('Kraken API Balance:')
    for asset, amount in balance.items():
        print(f'  {asset}: {amount}')
        
    # Attempt to find the BTC balance using canonical asset key
    # Kraken typically returns BTC balance under 'XXBT'
    btc_keys = ['XXBT', 'XBT']
    btc_balance = None
    for key in btc_keys:
        if key in balance:
            try:
                btc_balance = float(balance[key])
                break
            except Exception:
                continue
    if btc_balance is not None:
        print(f'BTC Balance (using key {key}): {btc_balance}')
    else:
        print('BTC Balance not found in the returned balance.')


if __name__ == '__main__':
    main()
