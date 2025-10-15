import pytest
from validator import ConfigValidator, ValidationResult


class DummyKrakenAPI:
    def __init__(self, balance):
        self._balance = balance

    def get_balance(self):
        return self._balance

    def get_current_price(self, pair):
        # Not used in this test
        return None


def test_balance_normalization_sums_spot_and_funding():
    # Balance example from AGENTS.md: funding only has BTC
    balance = {
        'XXBT': '0.0000000000',
        'XBT.F': '0.0106906064'
    }

    api = DummyKrakenAPI(balance)
    validator = ConfigValidator(kraken_api=api)

    # Create a simple config that attempts to sell 0.01 BTC
    configs = [
        {
            'id': 'btc_test',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        }
    ]

    result = validator.validate_config_file(configs)

    # Find balance-related warnings
    balance_warnings = [w for w in result.warnings if w['field'] == 'balance']

    assert balance_warnings, "Expected balance warning to be present"
    # The message should contain the summed BTC approx value
    msg = balance_warnings[0]['message']
    assert '0.01069060' in msg or '0.0106906064' in msg