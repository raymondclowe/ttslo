#!/usr/bin/env python3
"""
Test suite for Kraken API client with mocked responses.
"""
import json
import hashlib
import hmac
import base64
from unittest.mock import Mock, patch, MagicMock
import pytest

from kraken_api import KrakenAPI


class MockResponse:
    """Mock response object for requests."""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class TestKrakenAPIPublic:
    """Test public API endpoints."""
    
    def test_init_default_base_url(self):
        """Test initialization with default base URL."""
        api = KrakenAPI()
        assert api.base_url == "https://api.kraken.com"
        assert api.api_key is None
        assert api.api_secret is None
    
    def test_init_custom_base_url(self):
        """Test initialization with custom base URL for testing."""
        custom_url = "http://localhost:8080"
        api = KrakenAPI(base_url=custom_url)
        assert api.base_url == custom_url
    
    def test_init_with_credentials(self):
        """Test initialization with API credentials."""
        api = KrakenAPI(api_key="test_key", api_secret="test_secret")
        assert api.api_key == "test_key"
        assert api.api_secret == "test_secret"
    
    @patch('kraken_api.requests.get')
    def test_get_ticker_success(self, mock_get):
        """Test successful ticker retrieval."""
        mock_response = MockResponse({
            "error": [],
            "result": {
                "XXXBTZUSDT": {
                    "a": ["50000.00000", "1", "1.000"],
                    "b": ["49999.00000", "2", "2.000"],
                    "c": ["50000.50000", "0.00100000"],
                    "v": ["100.12345678", "200.12345678"],
                    "p": ["49500.00000", "49600.00000"],
                    "t": [1000, 2000],
                    "l": ["49000.00000", "48900.00000"],
                    "h": ["50100.00000", "50200.00000"],
                    "o": "49800.00000"
                }
            }
        })
        mock_get.return_value = mock_response
        api = KrakenAPI()
        result = api.get_ticker('XXXBTZUSDT')
        assert 'XXXBTZUSDT' in result
        assert result['XXXBTZUSDT']['c'][0] == "50000.50000"
        mock_get.assert_called_once()
    
    @patch('kraken_api.requests.get')
    def test_get_ticker_error(self, mock_get):
        """Test ticker retrieval with API error."""
        mock_response = MockResponse({
            "error": ["EQuery:Unknown asset pair"]
        })
        mock_get.return_value = mock_response
        
        api = KrakenAPI()
        with pytest.raises(Exception, match="Kraken API error"):
            api.get_ticker('INVALID')
    
    @patch('kraken_api.requests.get')
    def test_get_current_price_success(self, mock_get):
        """Test successful price retrieval."""
        mock_response = MockResponse({
            "error": [],
            "result": {
                "XXBTZUSDT": {
                    "c": ["50000.50000", "0.00100000"]
                }
            }
        })
        mock_get.return_value = mock_response
        
        api = KrakenAPI()
        price = api.get_current_price('XXXBTZUSDT')
        assert price == 50000.50000
        mock_get.assert_called_once()
    
    @patch('kraken_api.requests.get')
    def test_get_current_price_empty_pair(self, mock_get):
        """Test price retrieval with empty pair."""
        api = KrakenAPI()
        with pytest.raises(ValueError, match="pair parameter is required"):
            api.get_current_price('')
    
    @patch('kraken_api.requests.get')
    def test_get_current_price_invalid_type(self, mock_get):
        """Test price retrieval with invalid type."""
        api = KrakenAPI()
        with pytest.raises(ValueError, match="pair must be a string"):
            api.get_current_price(123)


class TestKrakenAPIPrivate:
    """Test private API endpoints."""
    
    def test_query_private_no_credentials(self):
        """Test private endpoint without credentials."""
        api = KrakenAPI()
        with pytest.raises(ValueError, match="API key and secret required"):
            api.get_balance()
    
    @patch('kraken_api.requests.post')
    def test_get_balance_success(self, mock_post):
        """Test successful balance retrieval."""
        mock_response = MockResponse({
            "error": [],
            "result": {
                "XXBT": "10.5000",
                "USDT": "50000.0000"
            }
        })
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        result = api.get_balance()
        
        assert result['XXBT'] == "10.5000"
    assert result['USDT'] == "50000.0000"
        
        # Verify the request was made with JSON content type
        call_args = mock_post.call_args
        assert call_args[1]['headers']['Content-Type'] == 'application/json'
    
    @patch('kraken_api.requests.post')
    def test_get_balance_error(self, mock_post):
        """Test balance retrieval with API error."""
        mock_response = MockResponse({
            "error": ["EAPI:Invalid key"]
        })
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        with pytest.raises(Exception, match="Kraken API error"):
            api.get_balance()
    
    @patch('kraken_api.requests.post')
    def test_query_open_orders_success(self, mock_post):
        """Test successful open orders query."""
        mock_response = MockResponse({
            "error": [],
            "result": {
                "open": {
                    "ORDER-ID-1": {
                        "status": "open",
                        "descr": {
                            "pair": "XXXBTZUSDT",
                            "type": "buy",
                            "ordertype": "limit",
                            "price": "50000.0"
                        },
                        "vol": "0.1",
                        "vol_exec": "0.0"
                    }
                }
            }
        })
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        result = api.query_open_orders()
        
        assert 'open' in result
        assert 'ORDER-ID-1' in result['open']
        assert result['open']['ORDER-ID-1']['status'] == 'open'
    
    @patch('kraken_api.requests.post')
    def test_query_open_orders_with_params(self, mock_post):
        """Test open orders query with parameters."""
        mock_response = MockResponse({
            "error": [],
            "result": {"open": {}}
        })
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        api.query_open_orders(trades=True, userref=123)
        
        # Verify parameters were included in the request
        call_args = mock_post.call_args
        request_data = json.loads(call_args[1]['data'])
        assert request_data['trades'] == True
        assert request_data['userref'] == 123
    
    @patch('kraken_api.requests.post')
    def test_cancel_order_success(self, mock_post):
        """Test successful order cancellation."""
        mock_response = MockResponse({
            "error": [],
            "result": {
                "count": 1,
                "pending": False
            }
        })
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        result = api.cancel_order('ORDER-ID-1')
        
        assert result['count'] == 1
        
        # Verify txid was included in the request
        call_args = mock_post.call_args
        request_data = json.loads(call_args[1]['data'])
        assert request_data['txid'] == 'ORDER-ID-1'
    
    def test_cancel_order_empty_txid(self):
        """Test cancel order with empty txid."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        with pytest.raises(ValueError, match="txid parameter is required"):
            api.cancel_order('')
    
    @patch('kraken_api.requests.post')
    def test_edit_order_success(self, mock_post):
        """Test successful order edit."""
        mock_response = MockResponse({
            "error": [],
            "result": {
                "status": "ok",
                "txid": "NEW-ORDER-ID"
            }
        })
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        result = api.edit_order('ORDER-ID-1', pair='XXBTZUSD', volume=0.2, price=51000)
        
        assert result['status'] == 'ok'
        
        # Verify parameters were included in the request
        call_args = mock_post.call_args
        request_data = json.loads(call_args[1]['data'])
        assert request_data['txid'] == 'ORDER-ID-1'
        assert request_data['pair'] == 'XXBTZUSD'
        assert request_data['volume'] == '0.2'
        assert request_data['price'] == '51000'
    
    def test_edit_order_empty_txid(self):
        """Test edit order with empty txid."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        with pytest.raises(ValueError, match="txid parameter is required"):
            api.edit_order('')
    
    @patch('kraken_api.requests.post')
    def test_add_order_success(self, mock_post):
        """Test successful order creation."""
        mock_response = MockResponse({
            "error": [],
            "result": {
                "descr": {
                    "order": "buy 0.1 XXXBTZUSDT @ limit 50000.0"
                },
                "txid": ["NEW-ORDER-ID"]
            }
        })
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        result = api.add_order('XXBTZUSDT', 'limit', 'buy', 0.1, price='50000.0')
        
        assert 'txid' in result
        assert result['txid'][0] == 'NEW-ORDER-ID'
        
        # Verify parameters were included correctly
        call_args = mock_post.call_args
        request_data = json.loads(call_args[1]['data'])
        assert request_data['pair'] == 'XXXBTZUSDT'
        assert request_data['type'] == 'buy'
        assert request_data['ordertype'] == 'limit'
        assert request_data['volume'] == '0.1'
        assert request_data['price'] == '50000.0'
    
    @patch('kraken_api.requests.post')
    def test_add_trailing_stop_loss_success(self, mock_post):
        """Test successful trailing stop loss order."""
        mock_response = MockResponse({
            "error": [],
            "result": {
                "descr": {
                    "order": "sell 0.1 XXXBTZUSDT @ trailing stop +5.0%"
                },
                "txid": ["TRAILING-ORDER-ID"]
            }
        })
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        result = api.add_trailing_stop_loss('XXBTZUSDT', 'sell', 0.1, 5.0)
        
        assert 'txid' in result
        
        # Verify trailing stop parameters
        call_args = mock_post.call_args
        request_data = json.loads(call_args[1]['data'])
        assert request_data['ordertype'] == 'trailing-stop'
        assert request_data['price'] == '+5.0%'  # Trailing offset is passed as 'price'
    
    @patch('kraken_api.requests.post')
    def test_get_trade_balance_success(self, mock_post):
        """Test successful trade balance retrieval."""
        mock_response = MockResponse({
            "error": [],
            "result": {
                "eb": "100000.0000",
                "tb": "95000.0000",
                "m": "5000.0000",
                "e": "95000.0000",
                "mf": "90000.0000"
            }
        })
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        result = api.get_trade_balance()
        
        assert result['eb'] == "100000.0000"
        assert result['tb'] == "95000.0000"


class TestKrakenAPISignature:
    """Test signature generation."""
    
    def test_signature_generation(self):
        """Test that signature is generated correctly."""
        # Use a known test vector
        api_secret = base64.b64encode(b"test_secret_key").decode()
        api = KrakenAPI(api_key="test_key", api_secret=api_secret)
        
        urlpath = "/0/private/Balance"
        nonce = "1234567890000"
        data = '{"nonce": "1234567890000"}'
        
        signature = api._get_kraken_signature(urlpath, data, nonce)
        
        # Verify signature is base64 encoded
        assert isinstance(signature, str)
        assert len(signature) > 0
        
        # Verify we can decode it as base64
        decoded = base64.b64decode(signature)
        assert len(decoded) == 64  # SHA512 produces 64 bytes
    
    def test_signature_different_for_different_data(self):
        """Test that different data produces different signatures."""
        api_secret = base64.b64encode(b"test_secret_key").decode()
        api = KrakenAPI(api_key="test_key", api_secret=api_secret)
        
        urlpath = "/0/private/Balance"
        nonce1 = "1234567890000"
        data1 = '{"nonce": "1234567890000"}'
        nonce2 = "1234567890001"
        data2 = '{"nonce": "1234567890001"}'
        
        sig1 = api._get_kraken_signature(urlpath, data1, nonce1)
        sig2 = api._get_kraken_signature(urlpath, data2, nonce2)
        
        assert sig1 != sig2


class TestKrakenAPIErrorHandling:
    """Test error handling."""
    
    @patch('kraken_api.requests.post')
    def test_http_error_handling(self, mock_post):
        """Test handling of HTTP errors."""
        mock_response = MockResponse({}, status_code=500)
        mock_response.raise_for_status = Mock(side_effect=Exception("HTTP 500"))
        mock_post.return_value = mock_response
        
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        with pytest.raises(Exception, match="HTTP 500"):
            api.get_balance()
    
    @patch('kraken_api.requests.get')
    def test_public_http_error(self, mock_get):
        """Test handling of HTTP errors on public endpoints."""
        mock_response = MockResponse({}, status_code=404)
        mock_response.raise_for_status = Mock(side_effect=Exception("HTTP 404"))
        mock_get.return_value = mock_response
        
        api = KrakenAPI()
        with pytest.raises(Exception, match="HTTP 404"):
            api.get_ticker('INVALID')
    
    def test_add_trailing_stop_loss_validation(self):
        """Test parameter validation for trailing stop loss."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        # Test empty pair
        with pytest.raises(ValueError, match="pair parameter is required"):
            api.add_trailing_stop_loss('', 'sell', 0.1, 5.0)
        
        # Test invalid direction
        with pytest.raises(ValueError, match="direction must be 'buy' or 'sell'"):
            api.add_trailing_stop_loss('XXBTZUSDT', 'invalid', 0.1, 5.0)
        
        # Test zero volume
        with pytest.raises(ValueError, match="volume must be positive"):
            api.add_trailing_stop_loss('XXBTZUSDT', 'sell', 0, 5.0)
        
        # Test negative offset
        with pytest.raises(ValueError, match="trailing_offset_percent must be positive"):
            api.add_trailing_stop_loss('XXBTZUSDT', 'sell', 0.1, -5.0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
