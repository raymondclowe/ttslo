#!/usr/bin/env python3
"""
Tool: fix_config_volumes

Reads a config.sys file, finds volume values for asset pairs and ensures
every volume is at least the exchange minimum (ordermin) from Kraken's
AssetPairs API. If a volume is below the minimum it will be raised to the
minimum and the file will be written back (with a timestamped backup).

Supported input formats (auto-detected):
 - JSON (dict or list of objects)
 - CSV (header with 'pair' and 'volume' or two columns pair,volume)
 - simple key=value lines (pair=volume)

Usage:
  python tools/fix_config_volumes.py /path/to/config.sys [--dry-run]

This script intentionally tries to be conservative about detecting the
pair string and will attempt to match human-friendly pair strings like
"XBT/USD" or Kraken internal keys like "XXBTZUSD" by normalizing
AssetPairs keys.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Ensure project root is on sys.path so scripts run via `uv run tools/...` can
# import project modules like `kraken_api`.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from kraken_api import KrakenAPI


def backup_file(path: str) -> str:
    ts = int(time.time())
    bak = f"{path}.bak.{ts}"
    shutil.copy2(path, bak)
    return bak


def normalize_pair_readable(pair: str) -> str:
    """Convert Kraken AssetPair key (e.g. 'XXBTZUSD') into human-readable 'XBT/USD'.

    This is a lightweight conversion to improve matching between various
    pair formats used in configs and Kraken API keys.
    """
    p = pair
    if not p:
        return p

    # If already human-looking like 'XBT/USD'
    if '/' in p:
        return p.upper()

    # If there's a 'Z' separator (common Kraken style), split on the first Z
    if 'Z' in p:
        left, right = p.split('Z', 1)
        # For left part: if it begins with a double prefix like 'XX' or 'ZZ',
        # strip a single leading character so 'XXBT' -> 'XBT'. Do NOT strip
        # a single leading 'X' as that would turn 'XRP' -> 'RP'.
        if left.startswith(('XX', 'ZZ')):
            left = left[1:]
        return f"{left}/{right}".upper()

    # Fallback heuristics: try last 3 or 4 chars as quote
    cleaned = p
    for cur_len in (4, 3):
        if len(cleaned) > cur_len:
            return f"{cleaned[:-cur_len]}/{cleaned[-cur_len:]}".upper()

    return pair.upper()


def build_assetpair_lookup(api: KrakenAPI) -> Dict[str, Dict[str, Any]]:
    """Query AssetPairs from Kraken and return lookup mapping.

    Returns a mapping from several canonical forms -> assetpair info.
    """
    resp = api._query_public('AssetPairs')
    if not isinstance(resp, dict):
        raise RuntimeError('Unexpected AssetPairs response')

    result = resp.get('result') if resp.get('result') is not None else {}

    lookup: Dict[str, Dict[str, Any]] = {}
    for key, info in result.items():
        # canonical key
        lookup[key.upper()] = info

        # readable form
        rd = normalize_pair_readable(key)
        lookup[rd.upper()] = info

        # also add a slashless readable (XBTUSD) for broader match
        lookup[rd.replace('/', '').upper()] = info

    return lookup


def detect_and_load(path: str) -> Tuple[str, Any]:
    """Attempt to detect file format and load data.

    Returns: (fmt, data)
     - fmt in {'json','csv','kv'}
    """
    text = open(path, 'r', encoding='utf-8').read()

    # Try JSON
    try:
        data = json.loads(text)
        return 'json', data
    except Exception:
        pass

    # If file looks like key=value per-line prefer kv parsing (avoid CSV sniffer
    # confusing lines like 'XXBTZUSD=0.001' into two columns).
    nonblank = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith('#')]
    if nonblank and all('=' in ln for ln in nonblank):
        kvs = []
        for ln in nonblank:
            k, v = ln.split('=', 1)
            kvs.append((k.strip(), v.strip()))
        return 'kv', kvs

    # Try CSV
    try:
        # Use csv.Sniffer to detect dialect
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(text)
        reader = csv.reader(text.splitlines(), dialect)
        rows = list(reader)
        if rows and len(rows[0]) >= 2:
            # treat as CSV with pair,volume columns
            # If header looks like 'pair' or 'volume', return as csv
            hdr = [c.strip().lower() for c in rows[0]]
            if 'pair' in hdr or 'volume' in hdr or len(rows) > 1:
                return 'csv', rows
    except Exception:
        pass

    # Fallback: key=value lines
    kvs = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        if '=' in ln:
            k, v = ln.split('=', 1)
            kvs.append((k.strip(), v.strip()))

    if kvs:
        return 'kv', kvs

    raise RuntimeError('Unable to detect config.sys format')


def write_back(path: str, fmt: str, data: Any) -> None:
    if fmt == 'json':
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=2)
    elif fmt == 'csv':
        # data is list of rows
        with open(path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.writer(fh)
            for row in data:
                writer.writerow(row)
    elif fmt == 'kv':
        with open(path, 'w', encoding='utf-8') as fh:
            for k, v in data:
                fh.write(f"{k}={v}\n")
    else:
        raise RuntimeError('Unsupported format for write_back')


def find_pair_in_row(row: Iterable[str]) -> Optional[Tuple[int, int]]:
    """Given a CSV row (headers), find indices for pair and volume columns.

    Returns (pair_idx, volume_idx) or None.
    """
    headers = [c.strip().lower() for c in row]
    pair_idx = None
    vol_idx = None
    for i, h in enumerate(headers):
        if h in ('pair', 'assetpair', 'symbol'):
            pair_idx = i
        if h in ('volume', 'vol', 'size'):
            vol_idx = i

    if pair_idx is None and len(headers) >= 1:
        # assume first column is pair
        pair_idx = 0
    if vol_idx is None and len(headers) >= 2:
        vol_idx = 1

    if pair_idx is not None and vol_idx is not None:
        return pair_idx, vol_idx
    return None


def coerce_number(x: str) -> float:
    try:
        return float(str(x).strip())
    except Exception:
        return 0.0


def fix_volumes_in_file(path: str, dry_run: bool = False, outfile: Optional[str] = None) -> Dict[str, Any]:
    api = KrakenAPI()  # no creds needed for public AssetPairs
    lookup = build_assetpair_lookup(api)

    fmt, data = detect_and_load(path)

    changed = []
    if fmt == 'json':
        # data could be dict or list
        # normalize to list of dicts with keys 'pair' and 'volume'
        items = []
        if isinstance(data, dict):
            # Try dict mapping pair->volume
            simple = True
            for k, v in data.items():
                if isinstance(v, (int, float, str)):
                    items.append({'pair': k, 'volume': v})
                else:
                    simple = False
                    break
            if not simple:
                # maybe dict has objects
                for k, v in data.items():
                    if isinstance(v, dict) and ('volume' in v or 'vol' in v):
                        vol = v.get('volume') or v.get('vol')
                        items.append({'pair': k, 'volume': vol})
        elif isinstance(data, list):
            for obj in data:
                if isinstance(obj, dict) and ('pair' in obj and 'volume' in obj):
                    items.append(obj)

        # mutate items
        for obj in items:
            pair = str(obj.get('pair'))
            if not pair:
                continue
            key = pair.strip().upper()
            api_info = lookup.get(key) or lookup.get(normalize_pair_readable(key).upper())
            if not api_info:
                # try more fuzzy match
                api_info = lookup.get(key.replace('/', '').upper())
            if not api_info:
                print(f"[warn] no assetpair match for {pair}")
                continue
            minstr = api_info.get('ordermin')
            if minstr is None:
                continue
            minv = coerce_number(minstr)
            cur = coerce_number(obj.get('volume'))
            if cur < minv:
                changed.append({'pair': pair, 'old': cur, 'new': minv})
                obj['volume'] = str(minv)

        if changed and not dry_run:
            # write back - try to preserve original top-level structure
            # If original was dict mapping pair->volume, rebuild dict
            try:
                orig = json.load(open(path, 'r', encoding='utf-8'))
                if isinstance(orig, dict):
                    out = {}
                    for it in items:
                        out[it['pair']] = it['volume']
                    # write
                    if outfile:
                        write_back(outfile, 'json', out)
                        print(f"[info] wrote updated JSON to {outfile}")
                    else:
                        bak = backup_file(path)
                        write_back(path, 'json', out)
                        print(f"[info] overwrote {path} and backup saved to {bak}")
                else:
                    if outfile:
                        write_back(outfile, 'json', items)
                        print(f"[info] wrote updated JSON list to {outfile}")
                    else:
                        bak = backup_file(path)
                        write_back(path, 'json', items)
                        print(f"[info] overwrote {path} and backup saved to {bak}")
            except Exception:
                # fallback
                if outfile:
                    write_back(outfile, 'json', items)
                    print(f"[info] wrote updated JSON (fallback) to {outfile}")
                else:
                    bak = backup_file(path)
                    write_back(path, 'json', items)
                    print(f"[info] wrote updated JSON (fallback) and backup saved to {bak}")

    elif fmt == 'csv':
        rows: List[List[str]] = [list(r) for r in data]
        if not rows:
            return {'changed': changed}

        header = rows[0]
        idxs = find_pair_in_row(header)
        # if header looks like data (no header), treat row0 as data
        start_row = 1 if idxs else 0
        if not idxs and len(rows[0]) >= 2:
            idxs = (0, 1)

        pair_idx, vol_idx = idxs if idxs else (0, 1)

        for i in range(start_row, len(rows)):
            r = rows[i]
            if len(r) <= max(pair_idx, vol_idx):
                continue
            pair = r[pair_idx].strip()
            cur = coerce_number(r[vol_idx])
            key = pair.strip().upper()
            api_info = lookup.get(key) or lookup.get(normalize_pair_readable(key).upper())
            if not api_info:
                api_info = lookup.get(key.replace('/', '').upper())
            if not api_info:
                print(f"[warn] no assetpair match for {pair}")
                continue
            minstr = api_info.get('ordermin')
            if minstr is None:
                continue
            minv = coerce_number(minstr)
            if cur < minv:
                changed.append({'pair': pair, 'old': cur, 'new': minv, 'row': i})
                rows[i][vol_idx] = str(minv)

        if changed and not dry_run:
            if outfile:
                write_back(outfile, 'csv', rows)
                print(f"[info] wrote updated CSV to {outfile}")
            else:
                bak = backup_file(path)
                write_back(path, 'csv', rows)
                print(f"[info] overwrote {path} and backup saved to {bak}")

    elif fmt == 'kv':
        kvs: List[Tuple[str, str]] = list(data)
        for idx, (k, v) in enumerate(kvs):
            pair = k.strip()
            cur = coerce_number(v)
            key = pair.strip().upper()
            api_info = lookup.get(key) or lookup.get(normalize_pair_readable(key).upper())
            if not api_info:
                api_info = lookup.get(key.replace('/', '').upper())
            if not api_info:
                print(f"[warn] no assetpair match for {pair}")
                continue
            minstr = api_info.get('ordermin')
            if minstr is None:
                continue
            minv = coerce_number(minstr)
            if cur < minv:
                changed.append({'pair': pair, 'old': cur, 'new': minv})
                kvs[idx] = (k, str(minv))

        if changed and not dry_run:
            if outfile:
                write_back(outfile, 'kv', kvs)
                print(f"[info] wrote updated key=value file to {outfile}")
            else:
                bak = backup_file(path)
                write_back(path, 'kv', kvs)
                print(f"[info] overwrote {path} and backup saved to {bak}")

    else:
        raise RuntimeError('Unhandled format')

    return {'changed': changed, 'dry_run': dry_run}


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description='Ensure volumes in config.sys meet Kraken ordermin')
    p.add_argument('--file', '-f', dest='path', help='Path to config.sys file', required=False)
    p.add_argument('--outfile', '-o', dest='outfile', help='Optional output path; if omitted, prompts before overwriting input file')
    p.add_argument('--dry-run', action='store_true', help="Don't write anything, just report")
    p.add_argument('--yes', '-y', action='store_true', help='Assume yes to overwrite prompt')
    # Backwards-compatible positional path
    p.add_argument('positional_path', nargs='?', help=argparse.SUPPRESS)

    args = p.parse_args(argv)

    path = args.path or args.positional_path
    if not path:
        p.print_help()
        return 2

    if not os.path.exists(path):
        print(f"Path not found: {path}")
        return 2

    # If no outfile provided, and not dry-run, prompt unless --yes
    if not args.outfile and not args.dry_run and not args.yes:
        try:
            resp = input(f"Overwrite {path}? [y/N]: ")
        except KeyboardInterrupt:
            print('\nAborted')
            return 1
        if resp.strip().lower() not in ('y', 'yes'):
            print('No changes made.')
            return 0

    try:
        res = fix_volumes_in_file(path, dry_run=args.dry_run, outfile=args.outfile)
        if res.get('changed'):
            print('[result] changed entries:')
            for c in res['changed']:
                print(f"  {c['pair']}: {c['old']} -> {c['new']}")
            return 0
        else:
            print('[result] nothing to change')
            return 0
    except Exception as e:
        print(f"[error] {e}")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
