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

api = FakeKrakenAPI(
    balance={'XBT.F': '0.0106906064', 'XXBT': '0.0'},
    prices={'XXBTZUSD': Decimal('129000')}
)
validator = ConfigValidator(kraken_api=api)
config = {
    'id': 'btc_1',
    'pair': 'XXBTZUSD',
    'threshold_price': '130000',
    'threshold_type': 'above',
    'direction': 'sell',
    'volume': '0.01',
    'trailing_offset_percent': '5.0',
    'enabled': 'true',
}
res = validator.validate_config_file([config])
print('errors:', res.errors)
print('warnings:')
for w in res.warnings:
    print('-', w)
