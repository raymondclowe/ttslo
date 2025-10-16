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
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Set

CACHE_FILE = '.kraken_pairs_cache.json'
CACHE_DURATION = timedelta(days=1)

def fetch_kraken_pairs() -> Dict:
    """Fetch all valid Kraken trading pairs from the public API."""
    url = "https://api.kraken.com/0/public/AssetPairs"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "result" not in data:
        raise Exception("No result in Kraken AssetPairs response")
    return data["result"]

def get_cached_pairs() -> Set[str]:
    """
    Get Kraken trading pair codes from cache, or fetch from API if cache is stale/missing.
    Cache is stored in .kraken_pairs_cache.json and refreshed once per day.
    
    Returns:
        Set of valid Kraken pair codes (e.g., {'XBTUSDT', 'ETHUSDT', ...})
    """
    # Check if cache exists and is fresh
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            
            # Check cache timestamp
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_time < CACHE_DURATION:
                # Cache is fresh, use it
                return set(cache_data['pairs'])
        except (json.JSONDecodeError, KeyError, ValueError):
            # Cache is corrupted, will re-fetch
            pass
    
    # Cache is missing or stale, fetch from API
    try:
        pairs_data = fetch_kraken_pairs()
        pair_codes = set(pairs_data.keys())
        
        # Save to cache
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'pairs': list(pair_codes)
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
        
        return pair_codes
    except Exception as e:
        # If API fetch fails and we have stale cache, use it anyway
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    cache_data = json.load(f)
                return set(cache_data['pairs'])
            except:
                pass
        # No cache available, re-raise the error
        raise Exception(f"Failed to fetch Kraken pairs and no cache available: {e}")

def find_kraken_pair_code(base: str, quote: str) -> str:
    """
    Given base and quote asset symbols (e.g., 'BTC', 'USDT'), return the Kraken pair code (e.g., 'XBTUSDT').
    Looks up the live Kraken AssetPairs list (cached).
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
