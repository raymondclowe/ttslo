import requests

def fetch_kraken_pairs():
    """Fetch all valid Kraken trading pairs from the public API."""
    url = "https://api.kraken.com/0/public/AssetPairs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    if "result" not in data:
        raise Exception("No result in Kraken AssetPairs response")
    return set(data["result"].keys())
