from decimal import Decimal
from validator import ConfigValidator


class FakeKrakenAPI:
    def __init__(self, balance, prices):
        self._balance = balance
        self._prices = prices

    def get_balance(self):
        return self._balance

    def get_current_price(self, pair):
        return self._prices.get(pair)


def test_balance_sufficiency_message():
    api = FakeKrakenAPI(
        balance={
            'XBT.F': '0.0106906064',
            'XXBT': '0.0'
        },
    prices={'XXBTZUSD': Decimal('120000')}
    )

    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'btc_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '130000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]

    result = validator.validate_config_file(configs)
    # Expect one warning for balance stating "sufficient"
    assert result.is_valid()
    assert result.has_warnings()
    balance_warnings = [w for w in result.warnings if w['field'] == 'balance']
    assert len(balance_warnings) == 1
    assert 'sufficient' in balance_warnings[0]['message']


def test_balance_insufficient_triggers_volume_warning():
    api = FakeKrakenAPI(
        balance={
            'XBT.F': '0.005',
        },
    prices={'XXBTZUSD': Decimal('120000')}
    )

    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'btc_2',
            'pair': 'XXBTZUSD',
            'threshold_price': '130000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]

    result = validator.validate_config_file(configs)
    assert result.is_valid()
    # Should have both balance and volume warnings when insufficient
    balance_warnings = [w for w in result.warnings if w['field'] == 'balance']
    volume_warnings = [w for w in result.warnings if w['field'] == 'volume']
    assert len(balance_warnings) == 1
    assert len(volume_warnings) == 1
    assert 'insufficient' in balance_warnings[0]['message']
    assert 'Insufficient' in volume_warnings[0]['message']
