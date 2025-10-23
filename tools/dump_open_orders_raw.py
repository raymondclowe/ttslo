#!/usr/bin/env python3
"""
Dump the full raw HTTP response for Kraken OpenOrders to stdout.

This is a small utility used during testing to confirm field names and
full response structure returned by Kraken for open orders.

Usage examples:
  # Run using the project's virtualenv helper (preferred):
  uv run dump_open_orders_raw.py

  # Use read-write keys (if you need to inspect orders tied to RW key):
  KRAKEN_API_KEY=/path/to/key KRAKEN_API_SECRET=/path/to/secret uv run dump_open_orders_raw.py --readwrite

Production/test environment access:
  - The script prefers credentials from environment variables (KRAKEN_API_KEY / KRAKEN_API_SECRET).
  - If you need to supply production keys from a file in CI/test lab, set
    KRAKEN_PROD_KEYS_FILE to a file that contains lines KRAKEN_API_KEY=... and KRAKEN_API_SECRET=...
    The script will load that file (without overwriting any existing env vars) before resolving credentials.

Notes:
  - This tool prints the raw HTTP response body (unparsed) and then a pretty-printed
    JSON parsed form when possible.
  - It does not modify or cancel orders. Use read-only keys where possible.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Optional

import requests

from kraken_api import KrakenAPI
from creds import load_env


def load_keys_from_file(path: str) -> None:
    """Load KEY=VALUE pairs from a file into environment if missing.

    This is a conservative loader used for test environments where a file
    containing production keys is made available. Existing environment
    variables are not overwritten.
    """
    if not os.path.exists(path):
        print(f"Prod keys file not found: {path}", file=sys.stderr)
        return

    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v
    except Exception as e:
        print(f"Warning: failed to load prod keys file {path}: {e}", file=sys.stderr)


def build_signed_request(api: KrakenAPI, method: str, params: Optional[dict] = None) -> requests.Response:
    """Make a signed private API request and return the raw requests.Response.

    We intentionally build the request here to capture the raw response body
    for debugging. This mirrors KrakenAPI._query_private behaviour.
    """
    if not api.api_key or not api.api_secret:
        raise ValueError("API key and secret required for private endpoints")

    urlpath = f"/0/private/{method}"
    url = f"{api.base_url}{urlpath}"

    data = params or {}
    nonce = str(int(time.time() * 1000))
    data['nonce'] = nonce

    # Convert to JSON string for the request body (same as KrakenAPI)
    json_data = json.dumps(data)

    signature = api._get_kraken_signature(urlpath, json_data, nonce)

    headers = {
        'API-Key': api.api_key,
        'API-Sign': signature,
        'Content-Type': 'application/json'
    }

    # Use requests.post directly so we can return the Response object
    resp = requests.post(url, headers=headers, data=json_data)
    return resp


def main() -> int:
    p = argparse.ArgumentParser(description='Dump raw Kraken OpenOrders HTTP response')
    p.add_argument('--env-file', default='.env', help='Path to .env file to load (default: .env)')
    p.add_argument('--prod-keys-file', default=os.environ.get('KRAKEN_PROD_KEYS_FILE'),
                   help='Path to a file with production keys (KRAKEN_API_KEY=..., KRAKEN_API_SECRET=...)')
    p.add_argument('--readwrite', action='store_true', help='Use read-write credentials (KRAKEN_API_KEY_RW)')
    p.add_argument('--trades', action='store_true', help='Include trades in OpenOrders output')
    args = p.parse_args()

    # Load local .env without overwriting env vars
    if args.env_file:
        load_env(args.env_file)

    # If provided, load prod keys file (conservative: do not overwrite existing env vars)
    if args.prod_keys_file:
        load_keys_from_file(args.prod_keys_file)

    # Decide whether to use RW keys
    use_rw = args.readwrite

    # Create API client using explicit creds from env resolution path implemented in KrakenAPI.from_env
    api = KrakenAPI.from_env(readwrite=use_rw, env_file=args.env_file)

    # Make the signed request and print raw response
    try:
        resp = build_signed_request(api, 'OpenOrders', params={'trades': bool(args.trades)})
    except Exception as e:
        print(f"Error building/sending request: {e}", file=sys.stderr)
        return 2

    # Print raw HTTP response (status + headers + body)
    print(f"HTTP/{resp.raw.version if hasattr(resp, 'raw') and hasattr(resp.raw, 'version') else ''} Status: {resp.status_code}")
    print('--- Response headers ---')
    for k, v in resp.headers.items():
        print(f"{k}: {v}")
    print('--- Response body (raw) ---')
    # resp.text may raise on binary content, but Kraken returns JSON
    try:
        body = resp.text
    except Exception:
        body = resp.content.decode('utf-8', errors='replace')
    print(body)

    # Also attempt to pretty-print parsed JSON for convenience
    print('\n--- Parsed JSON (pretty) ---')
    try:
        parsed = resp.json()
        print(json.dumps(parsed, indent=2, sort_keys=True))
    except Exception as e:
        print(f"(Failed to parse JSON: {e})", file=sys.stderr)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
