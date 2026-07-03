#!/usr/bin/env python3
"""
Tests for the date-triggered DCA (dollar-cost-averaging) line type.

DCA lines use trigger_type=date with a trigger_datetime and a fixed
fiat_amount. At trigger time, volume = fiat_amount / current_price and the
existing trailing stop loss creation path is reused.
"""
import os
import sys
import tempfile
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ttslo import TTSLO
from config import ConfigManager
from kraken_api import KrakenAPI
from validator import ConfigValidator


def _make_ttslo(tmpdir, dry_run=True, api_ro=None, api_rw=None):
    config_file = os.path.join(tmpdir, 'config.csv')
    state_file = os.path.join(tmpdir, 'state.csv')
    log_file = os.path.join(tmpdir, 'log.csv')
    cm = ConfigManager(config_file, state_file, log_file)
    if api_ro is None:
        api_ro = Mock(spec=KrakenAPI)
    return TTSLO(cm, api_ro, kraken_api_readwrite=api_rw, dry_run=dry_run, verbose=False)


# ---------------------------------------------------------------------------
# get_trigger_type
# ---------------------------------------------------------------------------

def test_get_trigger_type_default_price():
    assert TTSLO.get_trigger_type({}) == 'price'
    assert TTSLO.get_trigger_type({'trigger_type': ''}) == 'price'
    assert TTSLO.get_trigger_type({'trigger_type': None}) == 'price'
    assert TTSLO.get_trigger_type({'trigger_type': 'price'}) == 'price'


def test_get_trigger_type_date():
    assert TTSLO.get_trigger_type({'trigger_type': 'date'}) == 'date'
    assert TTSLO.get_trigger_type({'trigger_type': ' Date '}) == 'date'


# ---------------------------------------------------------------------------
# check_date_trigger (before / at / after)
# ---------------------------------------------------------------------------

def test_check_date_trigger_before_at_after():
    with tempfile.TemporaryDirectory() as tmpdir:
        t = _make_ttslo(tmpdir)
        trigger = '2026-07-03T00:00:00Z'
        cfg = {'id': 'd', 'trigger_datetime': trigger}

        before = datetime(2026, 7, 2, 23, 59, 59, tzinfo=timezone.utc)
        at = datetime(2026, 7, 3, 0, 0, 0, tzinfo=timezone.utc)
        after = datetime(2026, 7, 3, 0, 0, 1, tzinfo=timezone.utc)

        assert t.check_date_trigger(cfg, now=before) is False
        assert t.check_date_trigger(cfg, now=at) is True
        assert t.check_date_trigger(cfg, now=after) is True


def test_check_date_trigger_naive_treated_as_utc():
    with tempfile.TemporaryDirectory() as tmpdir:
        t = _make_ttslo(tmpdir)
        cfg = {'id': 'd', 'trigger_datetime': '2026-07-03T00:00:00'}
        at = datetime(2026, 7, 3, 0, 0, 0, tzinfo=timezone.utc)
        assert t.check_date_trigger(cfg, now=at) is True


def test_check_date_trigger_past_triggers_immediately():
    with tempfile.TemporaryDirectory() as tmpdir:
        t = _make_ttslo(tmpdir)
        cfg = {'id': 'd', 'trigger_datetime': '2000-01-01T00:00:00Z'}
        assert t.check_date_trigger(cfg) is True


def test_check_date_trigger_invalid_never_triggers():
    with tempfile.TemporaryDirectory() as tmpdir:
        t = _make_ttslo(tmpdir)
        assert t.check_date_trigger({'id': 'd', 'trigger_datetime': 'notadate'}) is False
        assert t.check_date_trigger({'id': 'd', 'trigger_datetime': ''}) is False
        assert t.check_date_trigger({'id': 'd'}) is False


# ---------------------------------------------------------------------------
# compute_dca_volume (math, precision rounding, below-minimum)
# ---------------------------------------------------------------------------

def test_compute_dca_volume_math_and_precision():
    with tempfile.TemporaryDirectory() as tmpdir:
        api_ro = Mock(spec=KrakenAPI)
        api_ro.get_asset_pair_info = Mock(return_value={'lot_decimals': '8'})
        t = _make_ttslo(tmpdir, api_ro=api_ro)
        cfg = {'id': 'd', 'pair': 'XXBTZUSD', 'fiat_amount': '100'}
        volume, msg = t.compute_dca_volume(cfg, 30000)
        # 100 / 30000 = 0.0033333... rounded down to 8 decimals
        assert volume == Decimal('0.00333333')


def test_compute_dca_volume_rounds_down():
    with tempfile.TemporaryDirectory() as tmpdir:
        api_ro = Mock(spec=KrakenAPI)
        api_ro.get_asset_pair_info = Mock(return_value={'lot_decimals': '2'})
        t = _make_ttslo(tmpdir, api_ro=api_ro)
        cfg = {'id': 'd', 'pair': 'XETHZUSD', 'fiat_amount': '100'}
        volume, msg = t.compute_dca_volume(cfg, 3000)
        # 100 / 3000 = 0.0333 -> rounds DOWN to 2 decimals = 0.03
        assert volume == Decimal('0.03')


def test_compute_dca_volume_no_pair_info():
    with tempfile.TemporaryDirectory() as tmpdir:
        api_ro = Mock(spec=KrakenAPI)
        api_ro.get_asset_pair_info = Mock(return_value=None)
        t = _make_ttslo(tmpdir, api_ro=api_ro)
        cfg = {'id': 'd', 'pair': 'XXBTZUSD', 'fiat_amount': '100'}
        volume, msg = t.compute_dca_volume(cfg, 40000)
        assert volume == Decimal('100') / Decimal('40000')


def test_compute_dca_volume_below_minimum_precision_zero():
    """Very small fiat_amount producing sub-minimum volume -> zero after rounding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        api_ro = Mock(spec=KrakenAPI)
        api_ro.get_asset_pair_info = Mock(return_value={'lot_decimals': '2'})
        t = _make_ttslo(tmpdir, api_ro=api_ro)
        cfg = {'id': 'd', 'pair': 'XXBTZUSD', 'fiat_amount': '0.01'}
        # 0.01 / 40000 = tiny; rounds down to 0.00 at 2 decimals -> None
        volume, msg = t.compute_dca_volume(cfg, 40000)
        assert volume is None


def test_compute_dca_volume_invalid_inputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        api_ro = Mock(spec=KrakenAPI)
        api_ro.get_asset_pair_info = Mock(return_value={'lot_decimals': '8'})
        t = _make_ttslo(tmpdir, api_ro=api_ro)
        assert t.compute_dca_volume({'id': 'd', 'pair': 'X'}, 30000)[0] is None  # no fiat
        assert t.compute_dca_volume({'id': 'd', 'pair': 'X', 'fiat_amount': '0'}, 30000)[0] is None
        assert t.compute_dca_volume({'id': 'd', 'pair': 'X', 'fiat_amount': '-5'}, 30000)[0] is None
        assert t.compute_dca_volume({'id': 'd', 'pair': 'X', 'fiat_amount': 'abc'}, 30000)[0] is None
        assert t.compute_dca_volume({'id': 'd', 'pair': 'X', 'fiat_amount': '100'}, 0)[0] is None


# ---------------------------------------------------------------------------
# process_config integration (date trigger path)
# ---------------------------------------------------------------------------

def test_process_config_date_trigger_creates_order_with_computed_volume():
    with tempfile.TemporaryDirectory() as tmpdir:
        api_ro = Mock(spec=KrakenAPI)
        api_ro.get_current_price = Mock(return_value=30000.0)
        api_ro.get_asset_pair_info = Mock(return_value={'lot_decimals': '8'})
        t = _make_ttslo(tmpdir, dry_run=True, api_ro=api_ro)

        captured = {}

        def fake_create(order_config, price):
            captured['config'] = order_config
            captured['price'] = price
            return 'DRY_RUN_ORDER_ID'

        t.create_tsl_order = fake_create

        config = {
            'id': 'btc_dca',
            'pair': 'XXBTZUSD',
            'direction': 'buy',
            'trailing_offset_percent': '2.0',
            'enabled': 'true',
            'trigger_type': 'date',
            'trigger_datetime': '2000-01-01T00:00:00Z',  # past -> triggers now
            'fiat_amount': '100',
        }
        t.process_config(config)

        assert 'config' in captured, "create_tsl_order should have been called"
        assert captured['config']['volume'] == '0.00333333'
        # original config must not be mutated
        assert 'volume' not in config


def test_process_config_date_trigger_not_yet_due():
    with tempfile.TemporaryDirectory() as tmpdir:
        api_ro = Mock(spec=KrakenAPI)
        api_ro.get_current_price = Mock(return_value=30000.0)
        api_ro.get_asset_pair_info = Mock(return_value={'lot_decimals': '8'})
        t = _make_ttslo(tmpdir, dry_run=True, api_ro=api_ro)

        called = {'v': False}

        def fake_create(order_config, price):
            called['v'] = True
            return 'DRY_RUN_ORDER_ID'

        t.create_tsl_order = fake_create

        config = {
            'id': 'btc_dca',
            'pair': 'XXBTZUSD',
            'direction': 'buy',
            'trailing_offset_percent': '2.0',
            'enabled': 'true',
            'trigger_type': 'date',
            'trigger_datetime': '2999-01-01T00:00:00Z',  # far future
            'fiat_amount': '100',
        }
        t.process_config(config)
        assert called['v'] is False, "Order must not be created before trigger_datetime"


def test_process_config_price_path_unchanged():
    """Regression: a price line still triggers on threshold, unaffected by DCA code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        api_ro = Mock(spec=KrakenAPI)
        api_ro.get_current_price = Mock(return_value=51000.0)
        t = _make_ttslo(tmpdir, dry_run=True, api_ro=api_ro)

        captured = {}

        def fake_create(order_config, price):
            captured['config'] = order_config
            return 'DRY_RUN_ORDER_ID'

        t.create_tsl_order = fake_create

        config = {
            'id': 'btc_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
        t.process_config(config)
        assert captured.get('config') is config, \
            "Price line should pass the original config unchanged to create_tsl_order"


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------

def _dca_config(**overrides):
    cfg = {
        'id': 'btc_dca',
        'pair': 'XXBTZUSD',
        'threshold_price': '',
        'threshold_type': '',
        'direction': 'buy',
        'volume': '',
        'trailing_offset_percent': '2.0',
        'enabled': 'true',
        'trigger_type': 'date',
        'trigger_datetime': '2025-01-01T00:00:00Z',
        'fiat_amount': '100',
    }
    cfg.update(overrides)
    return cfg


def test_validator_valid_dca_line():
    validator = ConfigValidator()
    result = validator.validate_config_file([_dca_config()])
    assert result.is_valid(), f"Expected valid, got errors: {result.errors}"


def test_validator_dca_missing_trigger_datetime():
    validator = ConfigValidator()
    result = validator.validate_config_file([_dca_config(trigger_datetime='')])
    assert not result.is_valid()
    assert any(e['field'] == 'trigger_datetime' for e in result.errors)


def test_validator_dca_invalid_trigger_datetime():
    validator = ConfigValidator()
    result = validator.validate_config_file([_dca_config(trigger_datetime='not-a-date')])
    assert not result.is_valid()
    assert any(e['field'] == 'trigger_datetime' for e in result.errors)


def test_validator_dca_fiat_amount_not_positive():
    validator = ConfigValidator()
    result = validator.validate_config_file([_dca_config(fiat_amount='0')])
    assert not result.is_valid()
    assert any(e['field'] == 'fiat_amount' for e in result.errors)


def test_validator_dca_missing_fiat_amount():
    validator = ConfigValidator()
    result = validator.validate_config_file([_dca_config(fiat_amount='')])
    assert not result.is_valid()
    assert any(e['field'] == 'fiat_amount' for e in result.errors)


def test_validator_mutual_exclusivity_volume_and_fiat():
    validator = ConfigValidator()
    result = validator.validate_config_file([_dca_config(volume='0.01')])
    assert not result.is_valid()
    assert any(e['field'] == 'fiat_amount' for e in result.errors)


def test_validator_invalid_trigger_type():
    validator = ConfigValidator()
    result = validator.validate_config_file([_dca_config(trigger_type='weekly')])
    assert not result.is_valid()
    assert any(e['field'] == 'trigger_type' for e in result.errors)


def test_validator_fiat_amount_on_price_line_warns():
    validator = ConfigValidator()
    price_cfg = {
        'id': 'btc_1',
        'pair': 'XXBTZUSD',
        'threshold_price': '50000',
        'threshold_type': 'above',
        'direction': 'sell',
        'volume': '0.01',
        'trailing_offset_percent': '5.0',
        'enabled': 'true',
        'trigger_type': 'price',
        'fiat_amount': '100',
    }
    result = validator.validate_config_file([price_cfg])
    # mutual exclusivity fires because both volume and fiat_amount set
    assert any(e['field'] == 'fiat_amount' for e in result.errors)


def test_validator_price_line_still_valid():
    """Regression: existing price-only config (no new columns) still validates."""
    validator = ConfigValidator()
    price_cfg = {
        'id': 'btc_1',
        'pair': 'XXBTZUSD',
        'threshold_price': '50000',
        'threshold_type': 'above',
        'direction': 'sell',
        'volume': '0.01',
        'trailing_offset_percent': '5.0',
        'enabled': 'true',
    }
    result = validator.validate_config_file([price_cfg])
    assert result.is_valid(), f"Expected valid, got errors: {result.errors}"


if __name__ == '__main__':
    import pytest
    sys.exit(pytest.main([__file__, '-v']))
