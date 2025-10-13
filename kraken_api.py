"""
Kraken API Client for interacting with Kraken exchange.
"""
import hashlib
import hmac
import base64
import time
import urllib.parse
import requests


class KrakenAPI:
    """Client for interacting with Kraken API."""
    
    def __init__(self, api_key=None, api_secret=None, base_url="https://api.kraken.com"):
        """
        Initialize Kraken API client.
        
        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret
            base_url: Base URL for Kraken API
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        
    def _get_kraken_signature(self, urlpath, data):
        """
        Generate Kraken API signature for authentication.
        
        Args:
            urlpath: API endpoint path
            data: Request data dictionary
            
        Returns:
            Base64 encoded signature
        """
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    
    def _query_public(self, method, params=None):
        """
        Query public Kraken API endpoint.
        
        Args:
            method: API method name
            params: Optional parameters dictionary
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/0/public/{method}"
        response = requests.get(url, params=params or {})
        response.raise_for_status()
        return response.json()
    
    def _query_private(self, method, params=None):
        """
        Query private Kraken API endpoint (requires authentication).
        
        Args:
            method: API method name
            params: Optional parameters dictionary
            
        Returns:
            API response as dictionary
        """
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for private endpoints")
            
        urlpath = f"/0/private/{method}"
        url = f"{self.base_url}{urlpath}"
        
        data = params or {}
        data['nonce'] = str(int(time.time() * 1000))
        
        headers = {
            'API-Key': self.api_key,
            'API-Sign': self._get_kraken_signature(urlpath, data)
        }
        
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()
    
    def get_ticker(self, pair):
        """
        Get ticker information for a trading pair.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD' for BTC/USD)
            
        Returns:
            Ticker information dictionary
        """
        result = self._query_public('Ticker', {'pair': pair})
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
    
    def get_current_price(self, pair):
        """
        Get current price for a trading pair.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD' for BTC/USD)
            
        Returns:
            Current price as float
        """
        ticker = self.get_ticker(pair)
        
        # Ticker response contains pair data with 'c' key for last trade closed
        # The format is [price, lot_volume]
        for pair_key, pair_data in ticker.items():
            if 'c' in pair_data:
                return float(pair_data['c'][0])
                
        raise Exception(f"Could not extract price for {pair}")
    
    def add_order(self, pair, order_type, direction, volume, **kwargs):
        """
        Add a new order.
        
        Args:
            pair: Trading pair
            order_type: Order type (market, limit, etc.)
            direction: 'buy' or 'sell'
            volume: Order volume
            **kwargs: Additional order parameters
            
        Returns:
            Order response dictionary
        """
        params = {
            'pair': pair,
            'type': direction,
            'ordertype': order_type,
            'volume': str(volume)
        }
        params.update(kwargs)
        
        result = self._query_private('AddOrder', params)
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
    
    def add_trailing_stop_loss(self, pair, direction, volume, trailing_offset_percent, **kwargs):
        """
        Add a trailing stop loss order.
        
        Args:
            pair: Trading pair
            direction: 'buy' or 'sell'
            volume: Order volume
            trailing_offset_percent: Trailing offset as percentage (e.g., 5.0 for 5%)
            **kwargs: Additional order parameters
            
        Returns:
            Order response dictionary
        """
        params = {
            'pair': pair,
            'type': direction,
            'ordertype': 'trailing-stop',
            'volume': str(volume),
            'trailingoffset': f"{trailing_offset_percent:+.1f}%"  # Format with sign and percentage
        }
        params.update(kwargs)
        
        result = self._query_private('AddOrder', params)
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
    
    def get_balance(self):
        """
        Get account balance.
        
        Returns:
            Balance dictionary
        """
        result = self._query_private('Balance')
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
