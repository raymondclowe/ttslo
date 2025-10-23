"""
Tests for fat-finger protection validation.

These tests verify that the validator warns users when prices or volumes
are 10x out of normal range based on:
1. Recent price history (OHLC data)
2. Existing order prices and volumes
"""
from decimal import Decimal
from validator import ConfigValidator


class FakeKrakenAPIWithHistory:
    """Mock Kraken API with historical data and orders."""
    
    def __init__(self, current_price, ohlc_data=None, open_orders=None, closed_orders=None):
        self._current_price = current_price
        self._ohlc_data = ohlc_data or {}
        self._open_orders = open_orders or {}
        self._closed_orders = closed_orders or {}
        self._balance = {}
    
    def get_current_price(self, pair):
        """Return current price for the pair."""
        return self._current_price
    
    def get_ohlc(self, pair, interval=1440, since=None):
        """Return OHLC data for the pair."""
        # Return the data as-is (it should already be in the right format)
        return self._ohlc_data
    
    def query_open_orders(self, trades=False, userref=None):
        """Return open orders."""
        return {'open': self._open_orders}
    
    def query_closed_orders(self, trades=False, userref=None, start=None, end=None, ofs=None, closetime='both'):
        """Return closed orders."""
        return {'closed': self._closed_orders}
    
    def get_balance(self):
        """Return account balance."""
        return self._balance


def test_price_10x_above_recent_high():
    """Test warning when threshold price is 10x above recent 7-day high."""
    # Current price: 50000, Recent high: 52000, Threshold: 600000 (>10x)
    ohlc_data = {
        'XXBTZUSD': [
            # [time, open, high, low, close, vwap, volume, count]
            [1699000000, '48000', '50000', '47000', '49000', '48500', '100', 1000],
            [1699100000, '49000', '51000', '48500', '50000', '49500', '120', 1100],
            [1699200000, '50000', '52000', '49000', '51000', '50500', '110', 1050],
            [1699300000, '51000', '51500', '49500', '50000', '50500', '105', 1020],
            [1699400000, '50000', '50500', '48000', '49000', '49000', '115', 1080],
            [1699500000, '49000', '50000', '48000', '49500', '49200', '108', 1040],
            [1699600000, '49500', '50000', '49000', '50000', '49600', '102', 1030],
        ],
        'last': 1699600000
    }
    
    api = FakeKrakenAPIWithHistory(
        current_price=Decimal('50000'),
        ohlc_data=ohlc_data
    )
    
    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'btc_high',
            'pair': 'XXBTZUSD',
            'threshold_price': '600000',  # 10x above recent high of 52000
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should have a warning about price being 10x above recent high
    price_warnings = [w for w in result.warnings if 'threshold_price' in w['field'] and '10x' in w['message']]
    assert len(price_warnings) >= 1, f"Expected warning about 10x price, got warnings: {result.warnings}"
    assert 'recent 7-day high' in price_warnings[0]['message'].lower()


def test_price_10x_below_recent_low():
    """Test warning when threshold price is 10x below recent 7-day low."""
    # Current price: 50000, Recent low: 47000, Threshold: 4000 (<0.1x)
    ohlc_data = {
        'XXBTZUSD': [
            [1699000000, '48000', '50000', '47000', '49000', '48500', '100', 1000],
            [1699100000, '49000', '51000', '48500', '50000', '49500', '120', 1100],
            [1699200000, '50000', '52000', '49000', '51000', '50500', '110', 1050],
            [1699300000, '51000', '51500', '49500', '50000', '50500', '105', 1020],
            [1699400000, '50000', '50500', '48000', '49000', '49000', '115', 1080],
            [1699500000, '49000', '50000', '48000', '49500', '49200', '108', 1040],
            [1699600000, '49500', '50000', '49000', '50000', '49600', '102', 1030],
        ],
        'last': 1699600000
    }
    
    api = FakeKrakenAPIWithHistory(
        current_price=Decimal('50000'),
        ohlc_data=ohlc_data
    )
    
    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'btc_low',
            'pair': 'XXBTZUSD',
            'threshold_price': '4000',  # 0.1x below recent low of 47000
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should have a warning about price being 10x below recent low
    price_warnings = [w for w in result.warnings if 'threshold_price' in w['field'] and '0.1x' in w['message']]
    assert len(price_warnings) >= 1, f"Expected warning about 0.1x price, got warnings: {result.warnings}"
    assert 'recent 7-day low' in price_warnings[0]['message'].lower()


def test_price_within_normal_range():
    """Test no warning when threshold price is within normal range."""
    # Current price: 50000, Recent high: 52000, low: 47000, Threshold: 55000 (reasonable)
    ohlc_data = {
        'XXBTZUSD': [
            [1699000000, '48000', '50000', '47000', '49000', '48500', '100', 1000],
            [1699100000, '49000', '51000', '48500', '50000', '49500', '120', 1100],
            [1699200000, '50000', '52000', '49000', '51000', '50500', '110', 1050],
            [1699300000, '51000', '51500', '49500', '50000', '50500', '105', 1020],
            [1699400000, '50000', '50500', '48000', '49000', '49000', '115', 1080],
            [1699500000, '49000', '50000', '48000', '49500', '49200', '108', 1040],
            [1699600000, '49500', '50000', '49000', '50000', '49600', '102', 1030],
        ],
        'last': 1699600000
    }
    
    api = FakeKrakenAPIWithHistory(
        current_price=Decimal('50000'),
        ohlc_data=ohlc_data
    )
    
    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'btc_normal',
            'pair': 'XXBTZUSD',
            'threshold_price': '55000',  # Within reasonable range
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should NOT have a warning about 10x price from history check
    price_warnings = [w for w in result.warnings if 'threshold_price' in w['field'] and ('10x' in w['message'] or '0.1x' in w['message']) and 'recent' in w['message'].lower()]
    assert len(price_warnings) == 0, f"Should not warn for normal price range, got warnings: {price_warnings}"


def test_price_10x_above_existing_orders():
    """Test warning when threshold price is 10x above existing order prices."""
    # Existing orders have prices around 50000-52000, threshold: 600000
    open_orders = {
        'order1': {
            'descr': {
                'pair': 'XXBTZUSD',
                'price': '50000'
            },
            'vol': '0.01'
        },
        'order2': {
            'descr': {
                'pair': 'XXBTZUSD',
                'price': '51000'
            },
            'vol': '0.015'
        }
    }
    
    closed_orders = {
        'order3': {
            'descr': {
                'pair': 'XXBTZUSD',
                'price': '52000'
            },
            'vol': '0.01'
        }
    }
    
    api = FakeKrakenAPIWithHistory(
        current_price=Decimal('50000'),
        ohlc_data={},
        open_orders=open_orders,
        closed_orders=closed_orders
    )
    
    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'btc_order_high',
            'pair': 'XXBTZUSD',
            'threshold_price': '600000',  # 10x above max order price
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should have a warning about price being 10x above existing orders
    price_warnings = [w for w in result.warnings if 'threshold_price' in w['field'] and '10x' in w['message'] and 'existing' in w['message'].lower()]
    assert len(price_warnings) >= 1, f"Expected warning about 10x vs existing orders, got warnings: {result.warnings}"


def test_volume_10x_above_existing_orders():
    """Test warning when volume is 10x above existing order volumes."""
    # Existing orders have volumes around 0.01-0.02, configured: 1.0 (>10x)
    open_orders = {
        'order1': {
            'descr': {
                'pair': 'XXBTZUSD',
                'price': '50000'
            },
            'vol': '0.01'
        },
        'order2': {
            'descr': {
                'pair': 'XXBTZUSD',
                'price': '51000'
            },
            'vol': '0.015'
        }
    }
    
    closed_orders = {
        'order3': {
            'descr': {
                'pair': 'XXBTZUSD',
                'price': '52000'
            },
            'vol': '0.02'
        }
    }
    
    api = FakeKrakenAPIWithHistory(
        current_price=Decimal('50000'),
        ohlc_data={},
        open_orders=open_orders,
        closed_orders=closed_orders
    )
    
    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'btc_volume_high',
            'pair': 'XXBTZUSD',
            'threshold_price': '55000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '1.0',  # 10x above max order volume of 0.02
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should have a warning about volume being 10x above existing orders
    volume_warnings = [w for w in result.warnings if 'volume' in w['field'] and '10x' in w['message'] and 'existing' in w['message'].lower()]
    assert len(volume_warnings) >= 1, f"Expected warning about 10x volume vs existing orders, got warnings: {result.warnings}"


def test_volume_10x_below_existing_orders():
    """Test warning when volume is 10x below existing order volumes."""
    # Existing orders have volumes around 0.1-0.2, configured: 0.005 (<0.1x)
    open_orders = {
        'order1': {
            'descr': {
                'pair': 'XXBTZUSD',
                'price': '50000'
            },
            'vol': '0.1'
        },
        'order2': {
            'descr': {
                'pair': 'XXBTZUSD',
                'price': '51000'
            },
            'vol': '0.15'
        }
    }
    
    closed_orders = {
        'order3': {
            'descr': {
                'pair': 'XXBTZUSD',
                'price': '52000'
            },
            'vol': '0.2'
        }
    }
    
    api = FakeKrakenAPIWithHistory(
        current_price=Decimal('50000'),
        ohlc_data={},
        open_orders=open_orders,
        closed_orders=closed_orders
    )
    
    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'btc_volume_low',
            'pair': 'XXBTZUSD',
            'threshold_price': '55000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.005',  # 0.1x below min order volume of 0.1
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should have a warning about volume being 10x below existing orders
    volume_warnings = [w for w in result.warnings if 'volume' in w['field'] and '0.1x' in w['message'] and 'existing' in w['message'].lower()]
    assert len(volume_warnings) >= 1, f"Expected warning about 0.1x volume vs existing orders, got warnings: {result.warnings}"


def test_no_warning_without_api():
    """Test that no fat-finger warnings are generated without API access."""
    # No API provided
    validator = ConfigValidator(kraken_api=None)
    configs = [
        {
            'id': 'btc_no_api',
            'pair': 'XXBTZUSD',
            'threshold_price': '600000',  # Would trigger warning with API
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '10.0',  # Would trigger warning with API
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should NOT have fat-finger warnings without API
    fat_finger_warnings = [w for w in result.warnings if '10x' in w['message'] or '0.1x' in w['message']]
    assert len(fat_finger_warnings) == 0, f"Should not have fat-finger warnings without API, got: {fat_finger_warnings}"


def test_no_warning_with_insufficient_data():
    """Test that no warnings are generated when there's insufficient historical data."""
    # Only 1 candle - not enough for pattern
    ohlc_data = {
        'XXBTZUSD': [
            [1699000000, '48000', '50000', '47000', '49000', '48500', '100', 1000],
        ],
        'last': 1699000000
    }
    
    api = FakeKrakenAPIWithHistory(
        current_price=Decimal('50000'),
        ohlc_data=ohlc_data
    )
    
    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'btc_insufficient',
            'pair': 'XXBTZUSD',
            'threshold_price': '600000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should NOT have warnings from history check due to insufficient data
    history_warnings = [w for w in result.warnings if 'recent' in w['message'].lower() and ('10x' in w['message'] or '0.1x' in w['message'])]
    assert len(history_warnings) == 0, f"Should not warn with insufficient history data, got: {history_warnings}"


def test_different_pair_orders_ignored():
    """Test that orders for different trading pairs are ignored."""
    # Orders are for ETHUSDT, but we're configuring XXBTZUSD
    open_orders = {
        'order1': {
            'descr': {
                'pair': 'ETHUSDT',
                'price': '3000'
            },
            'vol': '1.0'
        }
    }
    
    api = FakeKrakenAPIWithHistory(
        current_price=Decimal('50000'),
        ohlc_data={},
        open_orders=open_orders,
        closed_orders={}
    )
    
    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'btc_different_pair',
            'pair': 'XXBTZUSD',
            'threshold_price': '600000',  # Would trigger if ETH orders were considered
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '10.0',  # Would trigger if ETH orders were considered
            'trailing_offset_percent': '5.0',
            'enabled': 'true',
        }
    ]
    
    result = validator.validate_config_file(configs)
    
    # Should NOT have warnings from order comparison (different pair)
    order_warnings = [w for w in result.warnings if 'existing' in w['message'].lower() and ('10x' in w['message'] or '0.1x' in w['message'])]
    assert len(order_warnings) == 0, f"Should not warn based on orders from different pairs, got: {order_warnings}"
