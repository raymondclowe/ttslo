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
import threading
from typing import Optional, Dict

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

from creds import find_kraken_credentials


class KrakenAPIError(Exception):
    """Base exception for Kraken API errors."""
    def __init__(self, message: str, error_type: str = "unknown", details: Optional[Dict] = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


class KrakenAPITimeoutError(KrakenAPIError):
    """Raised when API request times out."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, error_type="timeout", details=details)


class KrakenAPIConnectionError(KrakenAPIError):
    """Raised when connection to Kraken fails."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, error_type="connection", details=details)


class KrakenAPIServerError(KrakenAPIError):
    """Raised when Kraken API returns 5xx server error."""
    def __init__(self, message: str, status_code: int = None, details: Optional[Dict] = None):
        details = details or {}
        if status_code:
            details['status_code'] = status_code
        super().__init__(message, error_type="server_error", details=details)


class KrakenAPIRateLimitError(KrakenAPIError):
    """Raised when API rate limit is exceeded."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, error_type="rate_limit", details=details)


class WebSocketPriceProvider:
    """
    Real-time price provider using Kraken WebSocket API.
    
    This class maintains a WebSocket connection to Kraken and provides
    real-time price updates via the ticker channel.
    """
    
    def __init__(self):
        """Initialize WebSocket price provider."""
        self.ws = None
        self.running = False
        self.connected = False
        self.prices = {}  # pair -> price (WebSocket format: XBT/USD)
        self.lock = threading.Lock()
        self.ws_thread = None
        self.subscribed_pairs = set()
        
    def _normalize_pair_to_ws_format(self, pair: str) -> str:
        """
        Convert REST API pair format to WebSocket format.
        
        Args:
            pair: Trading pair in REST format (e.g., 'XXBTZUSD', 'XETHZUSD')
            
        Returns:
            Trading pair in WebSocket format (e.g., 'XBT/USD', 'ETH/USD')
        """
        # Common conversions
        conversions = {
            'XXBTZUSD': 'XBT/USD',
            'XETHZUSD': 'ETH/USD',
            'XXBTZUSDT': 'XBT/USDT',
            'XETHZUSDT': 'ETH/USDT',
        }
        
        if pair in conversions:
            return conversions[pair]
        
        # Generic conversion for other pairs
        # Remove leading X's and insert slash before currency
        # e.g., XXRPZUSD -> XRP/USD
        if pair.startswith('X'):
            # Strip leading X's and try to split
            cleaned = pair.lstrip('X')
            # Most pairs are <asset>Z<currency> or <asset><currency>
            if 'Z' in cleaned:
                parts = cleaned.split('Z', 1)
                return f"{parts[0]}/{parts[1]}"
            # Fallback: assume last 3-4 chars are currency
            for cur_len in [4, 3]:
                if len(cleaned) > cur_len:
                    return f"{cleaned[:-cur_len]}/{cleaned[-cur_len:]}"
        
        # If we can't convert, return as-is and let WebSocket API handle it
        return pair
    
    def subscribe(self, pair: str):
        """
        Subscribe to price updates for a trading pair.
        
        Args:
            pair: Trading pair in REST format (e.g., 'XXBTZUSD')
        """
        if not WEBSOCKET_AVAILABLE:
            return
        
        # Convert to WebSocket format
        ws_pair = self._normalize_pair_to_ws_format(pair)
        
        with self.lock:
            if ws_pair in self.subscribed_pairs:
                return  # Already subscribed
            self.subscribed_pairs.add(ws_pair)
        
        if not self.connected:
            self._start_connection()
        
        # Send subscription message
        if self.ws and self.connected:
            subscribe_msg = {
                "event": "subscribe",
                "pair": [ws_pair],
                "subscription": {"name": "ticker"}
            }
            try:
                self.ws.send(json.dumps(subscribe_msg))
            except Exception as e:
                print(f"Error subscribing to {ws_pair}: {e}")
    
    def get_current_price(self, pair: str) -> Optional[float]:
        """
        Get the most recent price for a trading pair.
        
        Args:
            pair: Trading pair in REST format (e.g., 'XXBTZUSD')
            
        Returns:
            Current price or None if not available
        """
        ws_pair = self._normalize_pair_to_ws_format(pair)
        
        with self.lock:
            return self.prices.get(ws_pair)
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            # Handle ticker updates
            if isinstance(data, list) and len(data) >= 4:
                channel_name = data[-2] if len(data) > 2 else None
                pair_name = data[-1] if len(data) > 0 else None
                
                if channel_name == 'ticker':
                    ticker_data = data[1]
                    
                    # Extract current price from 'c' field (last trade closed)
                    if isinstance(ticker_data, dict) and 'c' in ticker_data:
                        price_array = ticker_data['c']
                        if isinstance(price_array, list) and len(price_array) > 0:
                            price = float(price_array[0])
                            
                            # Store the latest price
                            with self.lock:
                                self.prices[pair_name] = price
                                
        except Exception as e:
            # Silently ignore parse errors to avoid flooding logs
            pass
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        # Only log significant errors
        if not isinstance(error, (ConnectionResetError, BrokenPipeError)):
            print(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        self.connected = False
        # Attempt to reconnect after a short delay
        if self.running:
            time.sleep(5)
            self._reconnect()
    
    def _on_open(self, ws):
        """Handle WebSocket open."""
        self.connected = True
        
        # Re-subscribe to all pairs after connection
        with self.lock:
            pairs_to_subscribe = list(self.subscribed_pairs)
        
        for pair in pairs_to_subscribe:
            subscribe_msg = {
                "event": "subscribe",
                "pair": [pair],
                "subscription": {"name": "ticker"}
            }
            try:
                ws.send(json.dumps(subscribe_msg))
            except Exception:
                pass
    
    def _start_connection(self):
        """Start WebSocket connection in background thread."""
        if not WEBSOCKET_AVAILABLE:
            return
        
        if self.running:
            return  # Already running
        
        self.ws = websocket.WebSocketApp(
            "wss://ws.kraken.com/",
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        self.running = True
        self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.ws_thread.start()
        
        # Wait for connection (with timeout)
        timeout = 10
        start = time.time()
        while not self.connected and time.time() - start < timeout:
            time.sleep(0.1)
    
    def _reconnect(self):
        """Attempt to reconnect to WebSocket."""
        if not self.running:
            return
        
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        
        self._start_connection()
    
    def stop(self):
        """Stop WebSocket connection."""
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass


class KrakenAPI:
    """Client for interacting with Kraken API."""
    
    # Shared WebSocket price provider (singleton pattern for efficiency)
    _ws_provider = None
    _ws_provider_lock = threading.Lock()
    
    def __init__(self, api_key=None, api_secret=None, base_url="https://api.kraken.com", use_websocket=True):
        """
        Initialize Kraken API client.
        
        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret
            base_url: Base URL for Kraken API
            use_websocket: If True, use WebSocket for price data (default: True)
        """
        # Do not auto-discover credentials in the constructor to preserve
        # predictable behavior for unit tests. Use `from_env` to create a
        # KrakenAPI instance that loads credentials from environment/.env/copilot
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.use_websocket = use_websocket and WEBSOCKET_AVAILABLE
        
        # Initialize WebSocket provider if needed
        if self.use_websocket:
            with KrakenAPI._ws_provider_lock:
                if KrakenAPI._ws_provider is None:
                    KrakenAPI._ws_provider = WebSocketPriceProvider()

    @classmethod
    def from_env(cls, readwrite: bool = False, env_file: str = '.env', base_url: str = "https://api.kraken.com", use_websocket: bool = True):
        """Construct a KrakenAPI using credentials discovered from env/.env/copilot.

        This keeps the constructor side-effect free for unit tests while
        providing an explicit helper for the live application.
        
        Args:
            readwrite: If True, use read-write credentials
            env_file: Path to .env file
            base_url: Base URL for Kraken API
            use_websocket: If True, use WebSocket for price data (default: True)
        """
        key, secret = find_kraken_credentials(readwrite=readwrite, env_file=env_file)
        return cls(api_key=key, api_secret=secret, base_url=base_url, use_websocket=use_websocket)
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
    
    def _query_public(self, method, params=None, timeout=30):
        """
        Query public Kraken API endpoint.
        
        Args:
            method: API method name
            params: Optional parameters dictionary
            timeout: Request timeout in seconds (default: 30)
            
        Returns:
            API response as dictionary
            
        Raises:
            KrakenAPITimeoutError: If request times out
            KrakenAPIConnectionError: If connection fails
            KrakenAPIServerError: If server returns 5xx error
            KrakenAPIRateLimitError: If rate limit exceeded (429)
            KrakenAPIError: For other API errors
        """
        url = f"{self.base_url}/0/public/{method}"
        print(f"[DEBUG] KrakenAPI._query_public: Calling {url} with params={params}")
        
        try:
            response = requests.get(url, params=params or {}, timeout=timeout)
            print(f"[DEBUG] KrakenAPI._query_public: Response status={response.status_code}")
            
            # Check for rate limiting
            if response.status_code == 429:
                raise KrakenAPIRateLimitError(
                    f"Kraken API rate limit exceeded for {method}",
                    details={'method': method, 'url': url}
                )
            
            # Check for server errors (5xx)
            if response.status_code >= 500:
                raise KrakenAPIServerError(
                    f"Kraken API server error (HTTP {response.status_code}) for {method}",
                    status_code=response.status_code,
                    details={'method': method, 'url': url, 'response': response.text[:500]}
                )
            
            # Raise for other HTTP errors (4xx)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout as e:
            raise KrakenAPITimeoutError(
                f"Request to Kraken API timed out after {timeout}s for {method}",
                details={'method': method, 'url': url, 'timeout': timeout}
            ) from e
            
        except requests.exceptions.ConnectionError as e:
            raise KrakenAPIConnectionError(
                f"Failed to connect to Kraken API for {method}: {str(e)}",
                details={'method': method, 'url': url}
            ) from e
            
        except requests.exceptions.RequestException as e:
            # Catch any other requests exceptions
            raise KrakenAPIError(
                f"Request failed for {method}: {str(e)}",
                error_type="request_error",
                details={'method': method, 'url': url}
            ) from e
    
    def _query_private(self, method, params=None, timeout=30):
        """
        Query private Kraken API endpoint (requires authentication).
        
        Args:
            method: API method name
            params: Optional parameters dictionary
            timeout: Request timeout in seconds (default: 30)
            
        Returns:
            API response as dictionary
            
        Raises:
            KrakenAPITimeoutError: If request times out
            KrakenAPIConnectionError: If connection fails
            KrakenAPIServerError: If server returns 5xx error
            KrakenAPIRateLimitError: If rate limit exceeded (429)
            KrakenAPIError: For other API errors
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
        
        print(f"[DEBUG] KrakenAPI._query_private: Calling {url} with params={params}")

        print(f"[DEBUG] Headers: {headers}")
        print(f"[DEBUG] Payload: {json_data}")
        
        
        try:
            response = requests.post(url, headers=headers, data=json_data, timeout=timeout)
            print(f"[DEBUG] KrakenAPI._query_private: Response status={response.status_code}")

            print(f"[DEBUG] KrakenAPI._query_private: Response headers={response.headers}")
            print(f"[DEBUG] KrakenAPI._query_private: Response body={response.text}")

            # Check for rate limiting
            if response.status_code == 429:
                raise KrakenAPIRateLimitError(
                    f"Kraken API rate limit exceeded for {method}",
                    details={'method': method, 'url': url}
                )
            
            # Check for server errors (5xx)
            if response.status_code >= 500:
                raise KrakenAPIServerError(
                    f"Kraken API server error (HTTP {response.status_code}) for {method}",
                    status_code=response.status_code,
                    details={'method': method, 'url': url, 'response': response.text[:500]}
                )
            
            # Raise for other HTTP errors (4xx)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout as e:
            raise KrakenAPITimeoutError(
                f"Request to Kraken API timed out after {timeout}s for {method}",
                details={'method': method, 'url': url, 'timeout': timeout}
            ) from e
            
        except requests.exceptions.ConnectionError as e:
            raise KrakenAPIConnectionError(
                f"Failed to connect to Kraken API for {method}: {str(e)}",
                details={'method': method, 'url': url}
            ) from e
            
        except requests.exceptions.RequestException as e:
            # Catch any other requests exceptions
            raise KrakenAPIError(
                f"Request failed for {method}: {str(e)}",
                error_type="request_error",
                details={'method': method, 'url': url}
            ) from e
    
    def get_ticker(self, pair):
        """
        Get ticker information for a trading pair or multiple pairs.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD') or comma-separated pairs
            
        Returns:
            Ticker information dictionary
        """
        print(f"[DEBUG] KrakenAPI.get_ticker: pair={pair}")
        result = self._query_public('Ticker', {'pair': pair})
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
    
    def get_ohlc(self, pair, interval=1440, since=None):
        """
        Get OHLC (Open, High, Low, Close) data for a trading pair.
        
        Args:
            pair: Trading pair (e.g., 'XXBTZUSD' for BTC/USD)
            interval: Time frame interval in minutes (default: 1440 = 1 day)
                     Valid values: 1, 5, 15, 30, 60, 240, 1440, 10080, 21600
            since: Return committed OHLC data since given timestamp (optional)
            
        Returns:
            Dictionary containing OHLC data with structure:
            {
                'pair_name': [
                    [time, open, high, low, close, vwap, volume, count],
                    ...
                ],
                'last': timestamp
            }
        """
        print(f"[DEBUG] KrakenAPI.get_ohlc: pair={pair}, interval={interval}, since={since}")
        params = {'pair': pair, 'interval': interval}
        if since is not None:
            params['since'] = since
            
        result = self._query_public('OHLC', params)
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
    
    def get_current_price(self, pair):
        print(f"[DEBUG] KrakenAPI.get_current_price: pair={pair}")
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
        
        # Step 2: Try to get price from WebSocket if enabled
        if self.use_websocket and KrakenAPI._ws_provider:
            # Subscribe to the pair if not already subscribed
            KrakenAPI._ws_provider.subscribe(pair)
            
            # Try to get cached price from WebSocket
            ws_price = KrakenAPI._ws_provider.get_current_price(pair)
            
            # If we have a WebSocket price, use it
            if ws_price is not None:
                return ws_price
            
            # If no WebSocket price yet, wait a short time for first update
            # This handles the case where we just subscribed
            max_wait = 2.0  # seconds
            wait_interval = 0.1  # seconds
            elapsed = 0.0
            
            while elapsed < max_wait:
                time.sleep(wait_interval)
                elapsed += wait_interval
                
                ws_price = KrakenAPI._ws_provider.get_current_price(pair)
                if ws_price is not None:
                    return ws_price
            
            # If still no price from WebSocket, fall back to REST API
        
        # Step 3: Fall back to REST API (original implementation)
        # Get ticker data from API
        # This will raise an exception if the API call fails
        ticker = self.get_ticker(pair)
        
        # Step 4: Validate ticker response
        if not isinstance(ticker, dict):
            raise Exception(f"Invalid ticker response: expected dictionary, got {type(ticker)}")
        
        if not ticker:
            raise Exception(f"Empty ticker response for {pair}")
        
        # Step 5: Extract price from ticker data
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
        
        # Step 6: If we reach here, we couldn't extract the price
        raise Exception(f"Could not extract price for {pair} from ticker response")
    
    def get_current_prices_batch(self, pairs):
        """
        Get current prices for multiple trading pairs in a single API call.
        
        This is much more efficient than calling get_current_price() for each pair
        individually, as it reduces the number of API calls from N to 1.
        
        Args:
            pairs: List or set of trading pairs (e.g., ['XXBTZUSD', 'XETHZUSD'])
            
        Returns:
            Dictionary mapping pairs to their current prices
            Example: {'XXBTZUSD': 50000.0, 'XETHZUSD': 3000.0}
        """
        print(f"[DEBUG] KrakenAPI.get_current_prices_batch: fetching {len(pairs)} pairs")
        start_time = time.time()
        
        if not pairs:
            return {}
        
        # Convert to list if needed
        pair_list = list(pairs)
        
        # Join pairs with commas for batch request
        pair_param = ','.join(pair_list)
        
        try:
            # Get ticker data for all pairs at once
            ticker = self.get_ticker(pair_param)
            
            # Extract prices from response
            prices = {}
            for pair_key, pair_data in ticker.items():
                if not isinstance(pair_data, dict):
                    continue
                
                # Extract the last trade price
                last_trade = pair_data.get('c')
                if last_trade and len(last_trade) > 0:
                    try:
                        price = float(last_trade[0])
                        if price > 0:
                            prices[pair_key] = price
                    except (ValueError, TypeError) as e:
                        print(f"[DEBUG] Could not parse price for {pair_key}: {e}")
            
            elapsed = time.time() - start_time
            print(f"[DEBUG] KrakenAPI.get_current_prices_batch: fetched {len(prices)} prices in {elapsed:.3f}s")
            return prices
            
        except Exception as e:
            print(f"[DEBUG] Error in get_current_prices_batch: {e}")
            # On error, return empty dict - caller can fall back to individual requests
            return {}
    
    def get_asset_pair_info(self, pair):
        """
        Get detailed information about a trading pair from Kraken AssetPairs API.
        
        This includes important trading parameters like:
        - ordermin: Minimum order volume
        - costmin: Minimum order cost
        - pair_decimals: Price decimal precision
        - lot_decimals: Volume decimal precision
        
        Args:
            pair: Trading pair (e.g., 'NEARUSD', 'XXBTZUSD')
            
        Returns:
            Dictionary with pair info, or None if pair not found
            Example: {'ordermin': '0.7', 'costmin': '0.5', ...}
        """
        try:
            # Query the AssetPairs endpoint
            response = self._query_public('AssetPairs', {'pair': pair})
            
            # Check for API errors
            if response.get('error'):
                error_list = response.get('error', [])
                error_msg = ', '.join(str(e) for e in error_list)
                raise KrakenAPIError(f"Kraken API error: {error_msg}")
            
            # Extract result field
            result = response.get('result', {})
            if not result or not isinstance(result, dict):
                return None
            
            # The result contains pairs keyed by their altname or wsname
            # Usually there's only one key in the result
            for pair_key, pair_data in result.items():
                if isinstance(pair_data, dict):
                    return pair_data
            
            return None
            
        except Exception as e:
            print(f"[DEBUG] Error fetching pair info for {pair}: {e}")
            return None
    
    def add_order(self, pair, order_type, direction, volume, **kwargs):
        print(f"[DEBUG] KrakenAPI.add_order: pair={pair}, order_type={order_type}, direction={direction}, volume={volume}, kwargs={kwargs}")
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
        print(f"[DEBUG] KrakenAPI.add_trailing_stop_loss: pair={pair}, direction={direction}, volume={volume}, trailing_offset_percent={trailing_offset_percent}, kwargs={kwargs}")
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
        print(f"[DEBUG] KrakenAPI.get_balance: calling Balance endpoint")
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
        print(f"[DEBUG] KrakenAPI.get_trade_balance: asset={asset}")
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
        print(f"[DEBUG] KrakenAPI.query_open_orders: trades={trades}, userref={userref}")
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
    
    def query_closed_orders(self, trades=False, userref=None, start=None, end=None, ofs=None, closetime='both'):
        print(f"[DEBUG] KrakenAPI.query_closed_orders: trades={trades}, userref={userref}, start={start}, end={end}, ofs={ofs}, closetime={closetime}")
        """
        Query information about closed orders.
        
        Args:
            trades: Whether or not to include trades related to position in output
            userref: Restrict results to given user reference id
            start: Starting unix timestamp or order tx id of results (optional)
            end: Ending unix timestamp or order tx id of results (optional)
            ofs: Result offset
            closetime: Which time to use (open, close, both - default: both)
            
        Returns:
            Dictionary containing closed orders information
        """
        params = {'closetime': closetime}
        if trades:
            params['trades'] = trades
        if userref is not None:
            params['userref'] = userref
        if start is not None:
            params['start'] = start
        if end is not None:
            params['end'] = end
        if ofs is not None:
            params['ofs'] = ofs
            
        result = self._query_private('ClosedOrders', params)
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
    
    def query_orders(self, txids, trades=False):
        """
        Query information about specific orders by their transaction IDs.
        
        Args:
            txids: Comma-delimited list of transaction IDs to query (up to 50)
            trades: Whether or not to include trades related to position in output
            
        Returns:
            Dictionary containing order information for the specified transaction IDs
        """
        if not txids:
            return {}
        
        # Ensure txids is a string (comma-separated if it's a list)
        if isinstance(txids, list):
            txids = ','.join(txids)
        
        params = {'txid': txids}
        if trades:
            params['trades'] = trades
            
        result = self._query_private('QueryOrders', params)
        
        if result.get('error'):
            raise Exception(f"Kraken API error: {result['error']}")
            
        return result.get('result', {})
    
    def cancel_order(self, txid):
        print(f"[DEBUG] KrakenAPI.cancel_order: txid={txid}")
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
