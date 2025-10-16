"""
Kraken API Client for interacting with Kraken exchange.
"""
import hashlib
import hmac
import base64
import time
import urllib.parse
import json
import requests
import os

from creds import find_kraken_credentials


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
        # Do not auto-discover credentials in the constructor to preserve
        # predictable behavior for unit tests. Use `from_env` to create a
        # KrakenAPI instance that loads credentials from environment/.env/copilot
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    @classmethod
    def from_env(cls, readwrite: bool = False, env_file: str = '.env', base_url: str = "https://api.kraken.com"):
        """Construct a KrakenAPI using credentials discovered from env/.env/copilot.

        This keeps the constructor side-effect free for unit tests while
        providing an explicit helper for the live application.
        """
        key, secret = find_kraken_credentials(readwrite=readwrite, env_file=env_file)
        return cls(api_key=key, api_secret=secret, base_url=base_url)
    def _get_kraken_signature(self, urlpath, data, nonce):
        """
        Generate Kraken API signature for authentication.
        
        Args:
            urlpath: API endpoint path
            data: Request data as JSON string
            nonce: Nonce value
            
        Returns:
            Base64 encoded signature
        """
        # Signature = HMAC-SHA512 of (URI path + SHA256(nonce + POST data)) and base64 decoded secret API key
        encoded = (str(nonce) + data).encode()
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
        nonce = str(int(time.time() * 1000))
        data['nonce'] = nonce
        
        # Convert to JSON string for the request body
        json_data = json.dumps(data)
        
        headers = {
            'API-Key': self.api_key,
            'API-Sign': self._get_kraken_signature(urlpath, json_data, nonce),
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, data=json_data)
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
        
        SECURITY NOTE: This function will raise an exception if:
        - The pair parameter is invalid
        - The API call fails
        - The price cannot be extracted from the response
        
        This ensures price data is never silently incorrect.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD' for BTC/USD)
            
        Returns:
            Current price as float
            
        Raises:
            ValueError: If pair parameter is invalid
            Exception: If price cannot be retrieved
        """
        # Step 1: Validate pair parameter
        if not pair:
            raise ValueError("pair parameter is required and cannot be empty")
        if not isinstance(pair, str):
            raise ValueError(f"pair must be a string, got {type(pair)}")
        
        # Step 2: Get ticker data from API
        # This will raise an exception if the API call fails
        ticker = self.get_ticker(pair)
        
        # Step 3: Validate ticker response
        if not isinstance(ticker, dict):
            raise Exception(f"Invalid ticker response: expected dictionary, got {type(ticker)}")
        
        if not ticker:
            raise Exception(f"Empty ticker response for {pair}")
        
        # Step 4: Extract price from ticker data
        # Ticker response contains pair data with 'c' key for last trade closed
        # The format is [price, lot_volume]
        for pair_key, pair_data in ticker.items():
            # Validate pair_data is a dictionary
            if not isinstance(pair_data, dict):
                continue
            
            # Check if 'c' key exists (last trade closed)
            if 'c' in pair_data:
                price_data = pair_data['c']
                
                # Validate price_data is a list or tuple
                if not isinstance(price_data, (list, tuple)):
                    continue
                
                # Check list has at least one element
                if len(price_data) == 0:
                    continue
                
                # Extract the price (first element)
                price_str = price_data[0]
                
                # Convert to float
                try:
                    price_float = float(price_str)
                except (ValueError, TypeError) as e:
                    raise Exception(f"Could not convert price '{price_str}' to float for {pair}: {str(e)}")
                
                # Validate price is positive
                if price_float <= 0:
                    raise Exception(f"Invalid price {price_float} for {pair}: price must be positive")
                
                # Return the valid price
                return price_float
        
        # Step 5: If we reach here, we couldn't extract the price
        raise Exception(f"Could not extract price for {pair} from ticker response")
    
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
        
        SECURITY NOTE: This function will raise an exception if:
        - Any required parameter is missing or invalid
        - The API returns an error
        - The response is invalid
        
        This ensures errors are not silently ignored.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD')
            direction: 'buy' or 'sell'
            volume: Order volume (amount to trade)
            trailing_offset_percent: Trailing offset as percentage (e.g., 5.0 for 5%)
            **kwargs: Additional order parameters
            
        Returns:
            Order response dictionary
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If API call fails
        """
        # Step 1: Validate pair parameter
        if not pair:
            raise ValueError("pair parameter is required and cannot be empty")
        if not isinstance(pair, str):
            raise ValueError(f"pair must be a string, got {type(pair)}")
        
        # Step 2: Validate direction parameter
        if not direction:
            raise ValueError("direction parameter is required and cannot be empty")
        if not isinstance(direction, str):
            raise ValueError(f"direction must be a string, got {type(direction)}")
        
        # Normalize direction to lowercase
        direction_lower = direction.strip().lower()
        
        # Check direction is valid
        if direction_lower not in ['buy', 'sell']:
            raise ValueError(f"direction must be 'buy' or 'sell', got '{direction}'")
        
        # Step 3: Validate volume parameter
        if volume is None:
            raise ValueError("volume parameter is required and cannot be None")
        
        # Convert volume to float for validation
        try:
            volume_float = float(volume)
        except (ValueError, TypeError) as e:
            raise ValueError(f"volume must be a valid number, got '{volume}': {str(e)}")
        
        # Check volume is positive
        if volume_float <= 0:
            raise ValueError(f"volume must be positive, got {volume_float}")
        
        # Step 4: Validate trailing_offset_percent parameter
        if trailing_offset_percent is None:
            raise ValueError("trailing_offset_percent parameter is required and cannot be None")
        
        # Convert to float for validation
        try:
            offset_float = float(trailing_offset_percent)
        except (ValueError, TypeError) as e:
            raise ValueError(f"trailing_offset_percent must be a valid number, got '{trailing_offset_percent}': {str(e)}")
        
        # Check offset is positive
        if offset_float <= 0:
            raise ValueError(f"trailing_offset_percent must be positive, got {offset_float}")
        
        # Step 5: Build the parameters dictionary for the API call
        # Convert volume to string for API
        volume_str = str(volume)
        
        # Format trailing offset with sign and percentage
        # Example: 5.0 becomes "+5.0%"
        # For trailing stop orders, this is passed as 'price' parameter
        trailingoffset_str = f"{offset_float:+.1f}%"
        
        # Create parameters dictionary
        params = {
            'pair': pair,
            'type': direction_lower,
            'ordertype': 'trailing-stop',
            'volume': volume_str,
            'price': trailingoffset_str  # Trailing offset is passed as 'price' for trailing-stop orders
        }
        
        # Step 6: Add any additional parameters
        if kwargs:
            params.update(kwargs)
        
        # Step 7: Call the private API endpoint
        # This will raise an exception if credentials are missing
        result = self._query_private('AddOrder', params)
        
        # Step 8: Validate the result is a dictionary
        if not isinstance(result, dict):
            raise Exception(f"Invalid API response: expected dictionary, got {type(result)}")
        
        # Step 9: Check for API errors
        # Kraken returns errors in the 'error' field
        error_list = result.get('error')
        if error_list:
            # SAFETY: API returned errors - raise exception
            error_msg = ', '.join(str(e) for e in error_list)
            raise Exception(f"Kraken API error: {error_msg}")
        
        # Step 10: Extract and return the result
        # The actual order data is in the 'result' field
        order_result = result.get('result', {})
        
        # Validate result exists
        if not order_result:
            raise Exception("Kraken API returned empty result")
        
        # Return the order result dictionary
        return order_result
    
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
    
    def get_trade_balance(self, asset='ZUSD'):
        """
        Get trade balance information including margin, equity, and available funds.
        
        Args:
            asset: Base asset used to determine balance (default: 'ZUSD')
                   Examples: 'ZUSD', 'XXBT', 'XETH'
        
        Returns:
            Trade balance dictionary with fields:
                - eb: Equivalent balance (combined balance of all currencies)
                - tb: Trade balance (combined balance of all equity currencies)
                - m: Margin amount of open positions
                - n: Unrealized net profit/loss of open positions
                - c: Cost basis of open positions
                - v: Current floating valuation of open positions
                - e: Equity = trade balance + unrealized net profit/loss
                - mf: Free margin = equity - initial margin
                - ml: Margin level = (equity / initial margin) * 100
                - uv: Unexecuted value
        """
        params = {}
        if asset:
            params['asset'] = asset
            
        result = self._query_private('TradeBalance', params)
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
    
    def query_open_orders(self, trades=False, userref=None):
        """
        Query information about currently open orders.
        
        Args:
            trades: Whether or not to include trades related to position in output
            userref: Restrict results to given user reference id
            
        Returns:
            Dictionary containing open orders information
        """
        params = {}
        if trades:
            params['trades'] = trades
        if userref is not None:
            params['userref'] = userref
            
        result = self._query_private('OpenOrders', params)
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
    
    def cancel_order(self, txid):
        """
        Cancel an open order.
        
        Args:
            txid: Transaction ID or client order ID of order to cancel
            
        Returns:
            Dictionary containing cancellation result
        """
        if not txid:
            raise ValueError("txid parameter is required")
            
        params = {'txid': txid}
        result = self._query_private('CancelOrder', params)
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
    
    def edit_order(self, txid, pair=None, volume=None, price=None, **kwargs):
        """
        Edit an open order.
        
        Args:
            txid: Transaction ID of order to edit
            pair: Asset pair (optional, but recommended)
            volume: New order volume (optional)
            price: New order price (optional)
            **kwargs: Additional order parameters
            
        Returns:
            Dictionary containing edit result
        """
        if not txid:
            raise ValueError("txid parameter is required")
            
        params = {'txid': txid}
        if pair:
            params['pair'] = pair
        if volume is not None:
            params['volume'] = str(volume)
        if price is not None:
            params['price'] = str(price)
        params.update(kwargs)
        
        result = self._query_private('EditOrder', params)
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
