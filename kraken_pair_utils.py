"""
Kraken Asset Pair Utility
------------------------

This module provides functions to help users map common asset symbols (BTC, ETH, USDT, etc.) to Kraken's confusing pair codes.

Kraken's conventions:
- The pair code for BTC/USDT is 'XBTUSDT'
- The base asset for BTC is 'XXBT', but the pair code drops the extra 'X'
- The quote asset for USDT is 'USDT' (no prefix)

Common asset code mapping:
| Common | Kraken Asset | Pair Code Example |
|--------|-------------|------------------|
| BTC    | XXBT        | XBTUSDT          |
| ETH    | XETH        | ETHUSDT          |
| USDT   | USDT        | XBTUSDT          |
| USD    | ZUSD        | XBTUSD           |

Use the function `find_kraken_pair_code(base, quote)` to get the correct pair code for any base/quote asset.
"""
import requests

def fetch_kraken_pairs():
    """Fetch all valid Kraken trading pairs from the public API."""
    url = "https://api.kraken.com/0/public/AssetPairs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    if "result" not in data:
        raise Exception("No result in Kraken AssetPairs response")
    return data["result"]

def find_kraken_pair_code(base: str, quote: str) -> str:
    """
    Given base and quote asset symbols (e.g., 'BTC', 'USDT'), return the Kraken pair code (e.g., 'XBTUSDT').
    Looks up the live Kraken AssetPairs list.
    """
    base = base.upper().replace('BTC', 'XBT')  # Kraken uses XBT for BTC
    quote = quote.upper()
    pairs = fetch_kraken_pairs()
    for key, val in pairs.items():
        if val.get('wsname') == f"{base}/{quote}":
            return key
    raise ValueError(f"No Kraken pair found for {base}/{quote}. Check https://api.kraken.com/0/public/AssetPairs")

# Example usage:
# pair_code = find_kraken_pair_code('BTC', 'USDT')  # returns 'XBTUSDT'
