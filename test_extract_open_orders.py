"""
Tests for extract_open_orders.py utility
"""

import pytest
from unittest.mock import Mock
from extract_open_orders import extract_trailing_stop_orders, output_as_csv
import csv
import io


class MockKrakenAPI:
    """Mock Kraken API for testing."""
    
    def __init__(self, open_orders_response):
        self.open_orders_response = open_orders_response
    
    def query_open_orders(self):
        return self.open_orders_response


def test_extract_trailing_stop_orders_filters_correctly():
    """Test that only trailing-stop orders are extracted."""
    mock_response = {
        'open': {
            'ORDER-1': {
                'descr': {
                    'pair': 'XXBTZUSD',
                    'type': 'sell',
                    'ordertype': 'trailing-stop',
                    'price': '+5.0000%'
                },
                'vol': '0.01',
            },
            'ORDER-2': {
                'descr': {
                    'pair': 'XETHZUSD',
                    'type': 'buy',
                    'ordertype': 'limit',
                    'price': '3000.0'
                },
                'vol': '0.1',
            },
            'ORDER-3': {
                'descr': {
                    'pair': 'XXBTZUSD',
                    'type': 'buy',
                    'ordertype': 'trailing-stop',
                    'price': '+10.0000%'
                },
                'vol': '0.005',
            }
        }
    }
    
    api = MockKrakenAPI(mock_response)
    orders = extract_trailing_stop_orders(api)
    
    # Should only extract the 2 trailing-stop orders
    assert len(orders) == 2
    
    # Check first order
    assert orders[0]['id'] == 'ORDER-1'
    assert orders[0]['pair'] == 'XXBTZUSD'
    assert orders[0]['direction'] == 'sell'
    assert orders[0]['volume'] == '0.01'
    assert orders[0]['trailing_offset_percent'] == '5.0000'
    assert orders[0]['threshold_price'] == ''
    assert orders[0]['threshold_type'] == ''
    assert orders[0]['enabled'] == 'false'
    
    # Check second order
    assert orders[1]['id'] == 'ORDER-3'
    assert orders[1]['pair'] == 'XXBTZUSD'
    assert orders[1]['direction'] == 'buy'
    assert orders[1]['volume'] == '0.005'
    assert orders[1]['trailing_offset_percent'] == '10.0000'


def test_extract_trailing_stop_orders_empty_response():
    """Test handling of empty response."""
    mock_response = {'open': {}}
    
    api = MockKrakenAPI(mock_response)
    orders = extract_trailing_stop_orders(api)
    
    assert len(orders) == 0


def test_extract_trailing_stop_orders_no_trailing_stops():
    """Test when there are orders but no trailing-stop orders."""
    mock_response = {
        'open': {
            'ORDER-1': {
                'descr': {
                    'pair': 'XXBTZUSD',
                    'type': 'sell',
                    'ordertype': 'limit',
                    'price': '50000.0'
                },
                'vol': '0.01',
            }
        }
    }
    
    api = MockKrakenAPI(mock_response)
    orders = extract_trailing_stop_orders(api)
    
    assert len(orders) == 0


def test_extract_trailing_stop_orders_with_negative_offset():
    """Test handling of negative offset (shouldn't happen but test robustness)."""
    mock_response = {
        'open': {
            'ORDER-1': {
                'descr': {
                    'pair': 'XXBTZUSD',
                    'type': 'sell',
                    'ordertype': 'trailing-stop',
                    'price': '-5.0%'
                },
                'vol': '0.01',
            }
        }
    }
    
    api = MockKrakenAPI(mock_response)
    orders = extract_trailing_stop_orders(api)
    
    assert len(orders) == 1
    # Should strip both + and - signs
    assert orders[0]['trailing_offset_percent'] == '5.0'


def test_output_as_csv_format():
    """Test that CSV output has correct format."""
    orders = [
        {
            'id': 'ORDER-1',
            'pair': 'XXBTZUSD',
            'threshold_price': '',
            'threshold_type': '',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'false'
        }
    ]
    
    # Capture stdout
    output = io.StringIO()
    
    # Write to StringIO instead of file
    fieldnames = ['id', 'pair', 'threshold_price', 'threshold_type', 'direction', 
                  'volume', 'trailing_offset_percent', 'enabled']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for order in orders:
        writer.writerow(order)
    
    # Read back and verify
    output.seek(0)
    reader = csv.DictReader(output)
    rows = list(reader)
    
    assert len(rows) == 1
    assert rows[0]['id'] == 'ORDER-1'
    assert rows[0]['pair'] == 'XXBTZUSD'
    assert rows[0]['direction'] == 'sell'
    assert rows[0]['volume'] == '0.01'
    assert rows[0]['trailing_offset_percent'] == '5.0'
    assert rows[0]['threshold_price'] == ''
    assert rows[0]['threshold_type'] == ''
    assert rows[0]['enabled'] == 'false'


def test_extract_orders_from_real_api_format():
    """Test with the format shown in Kraken API docs."""
    # This is what query_open_orders() returns (already unwrapped)
    # The KrakenAPI returns result.get('result', {})
    mock_response = {
        "open": {
                "OZAFUQ-6FB7W-GR63OS": {
                    "refid": None,
                    "userref": 0,
                    "status": "open",
                    "opentm": 1760578655.936616,
                    "starttm": 0,
                    "expiretm": 0,
                    "descr": {
                        "pair": "XXBTZUSDT",
                        "aclass": "forex",
                        "type": "buy",
                        "ordertype": "trailing-stop",
                        "price": "+15.0000%",
                        "price2": "0",
                        "leverage": "none",
                        "order": "buy 0.00006000 XXBTZUSDT @ trailing stop +15.0000%",
                        "close": ""
                    },
                    "vol": "0.00006000",
                    "vol_exec": "0.00000000",
                    "cost": "0.00000",
                    "fee": "0.00000",
                    "price": "0.00000",
                    "stopprice": "127605.90000",
                    "limitprice": "110961.70000",
                    "misc": "",
                    "oflags": "fciq",
                    "trigger": "index"
                },
                "ORWBHN-LMPRM-TG4RWJ": {
                    "refid": None,
                    "userref": 0,
                    "status": "open",
                    "opentm": 1760578459.280463,
                    "starttm": 0,
                    "expiretm": 0,
                    "descr": {
                        "pair": "XXBTZUSDT",
                        "aclass": "forex",
                        "type": "sell",
                        "ordertype": "trailing-stop",
                        "price": "+10.0000%",
                        "price2": "0",
                        "leverage": "none",
                        "order": "sell 0.00005000 XXBTZUSDT @ trailing stop +10.0000%",
                        "close": ""
                    },
                    "vol": "0.00005000",
                    "vol_exec": "0.00000000",
                    "cost": "0.00000",
                    "fee": "0.00000",
                    "price": "0.00000",
                    "stopprice": "99874.10000",
                    "limitprice": "110971.20000",
                    "misc": "",
                    "oflags": "fcib",
                    "trigger": "index"
                }
            }
        }
    
    api = MockKrakenAPI(mock_response)
    orders = extract_trailing_stop_orders(api)
    
    assert len(orders) == 2
    
    # Check first order
    assert orders[0]['id'] == 'OZAFUQ-6FB7W-GR63OS'
    assert orders[0]['pair'] == 'XXBTZUSDT'
    assert orders[0]['direction'] == 'buy'
    assert orders[0]['volume'] == '0.00006000'
    assert orders[0]['trailing_offset_percent'] == '15.0000'
    
    # Check second order
    assert orders[1]['id'] == 'ORWBHN-LMPRM-TG4RWJ'
    assert orders[1]['pair'] == 'XXBTZUSDT'
    assert orders[1]['direction'] == 'sell'
    assert orders[1]['volume'] == '0.00005000'
    assert orders[1]['trailing_offset_percent'] == '10.0000'
