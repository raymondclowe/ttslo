import json
from pathlib import Path

import pytest

from tools import fix_config_volumes as fcv
from kraken_api import KrakenAPI


def mock_assetpairs_response():
    # Simulate Kraken API response structure
    return {
        'error': [],
        'result': {
            'XXBTZUSD': {'ordermin': '0.001'},
            'XETHZUSD': {'ordermin': '0.01'},
            'XRPZUSD': {'ordermin': '1.0'},
        }
    }


def test_csv_fix(tmp_path, monkeypatch):
    # Create a sample CSV with two rows, one below ordermin
    p = tmp_path / 'config.sys'
    p.write_text('pair,volume\nXXBTZUSD,0.0005\nXETHZUSD,0.05\n')

    # Monkeypatch KrakenAPI._query_public
    def fake_query(self, method, params=None, timeout=30):
        assert method == 'AssetPairs'
        return mock_assetpairs_response()

    monkeypatch.setattr(KrakenAPI, '_query_public', fake_query)

    res = fcv.fix_volumes_in_file(str(p), dry_run=False)

    # One change expected (XXBTZUSD 0.0005 -> 0.001)
    assert len(res['changed']) == 1
    assert res['changed'][0]['pair'] == 'XXBTZUSD'

    # File updated: check content
    txt = p.read_text()
    assert 'XXBTZUSD,0.001' in txt


def test_kv_fix(tmp_path, monkeypatch):
    p = tmp_path / 'config_kv.sys'
    p.write_text('XXBTZUSD=0.0002\nXRPZUSD=2.0\n')

    def fake_query(self, method, params=None, timeout=30):
        return mock_assetpairs_response()

    monkeypatch.setattr(KrakenAPI, '_query_public', fake_query)

    res = fcv.fix_volumes_in_file(str(p), dry_run=False)
    # One change for XXBTZUSD
    assert any(c['pair'] == 'XXBTZUSD' for c in res['changed'])
    txt = p.read_text()
    assert 'XXBTZUSD=0.001' in txt
