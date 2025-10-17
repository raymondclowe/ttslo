from validator import ConfigValidator

class DummyKrakenAPI:
    def __init__(self, balance):
        self._balance = balance

    def get_balance(self):
        return self._balance

    def get_current_price(self, pair):
        return None
    
    def get_ohlc(self, pair, interval=1440, since=None):
        return {}
    
    def query_open_orders(self, trades=False, userref=None):
        return {'open': {}}
    
    def query_closed_orders(self, trades=False, userref=None, start=None, end=None, ofs=None, closetime='both'):
        return {'closed': {}}

balance = {
    'XXBT': '0.0000000000',
    'XBT.F': '0.0106906064'
}

api = DummyKrakenAPI(balance)
validator = ConfigValidator(kraken_api=api)

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

print(f"Errors: {result.errors}")
print(f"Warnings: {result.warnings}")
print(f"Infos: {result.infos}")
