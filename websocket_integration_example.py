#!/usr/bin/env python3
"""
WebSocket Price Monitor Integration Example for TTSLO

This example shows how the TTSLO application could be enhanced to use
WebSocket for real-time price monitoring instead of REST API polling.

This would provide:
- Instant price updates when trades occur
- Lower latency
- More efficient use of API resources
- No polling overhead

Note: This is a demonstration/example, not integrated into the main application.
"""
import json
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Callable, Dict

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


class WebSocketPriceProvider:
    """
    Real-time price provider using Kraken WebSocket API.
    
    This class can be used as a drop-in replacement for REST API polling
    in the TTSLO application, providing real-time price updates.
    """
    
    def __init__(self):
        self.ws = None
        self.running = False
        self.connected = False
        self.prices = {}  # pair -> price
        self.callbacks = []  # List of callback functions
        self.lock = threading.Lock()
        self.ws_thread = None
        
    def subscribe(self, pair: str, callback: Optional[Callable] = None):
        """
        Subscribe to price updates for a trading pair.
        
        Args:
            pair: Trading pair in WebSocket format (e.g., 'XBT/USD')
            callback: Optional callback function(pair, price) called on updates
        """
        if callback:
            with self.lock:
                if callback not in self.callbacks:
                    self.callbacks.append(callback)
        
        if not self.connected:
            self._start_connection()
        
        # Send subscription message
        if self.ws:
            subscribe_msg = {
                "event": "subscribe",
                "pair": [pair],
                "subscription": {"name": "ticker"}
            }
            self.ws.send(json.dumps(subscribe_msg))
    
    def get_current_price(self, pair: str) -> Optional[float]:
        """
        Get the most recent price for a trading pair.
        
        Args:
            pair: Trading pair (e.g., 'XBT/USD')
            
        Returns:
            Current price or None if not available
        """
        with self.lock:
            return self.prices.get(pair)
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            if isinstance(data, list) and len(data) >= 4:
                channel_name = data[-2]
                pair_name = data[-1]
                
                if channel_name == 'ticker':
                    ticker_data = data[1]
                    
                    if isinstance(ticker_data, dict) and 'c' in ticker_data:
                        price = float(ticker_data['c'][0])
                        
                        # Update stored price
                        with self.lock:
                            self.prices[pair_name] = price
                            callbacks_copy = self.callbacks.copy()
                        
                        # Call all registered callbacks
                        for callback in callbacks_copy:
                            try:
                                callback(pair_name, price)
                            except Exception as e:
                                print(f"Error in callback: {e}")
                                
        except Exception as e:
            print(f"Error processing WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        print(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        print("WebSocket connection closed")
        self.connected = False
    
    def _on_open(self, ws):
        """Handle WebSocket open."""
        print("WebSocket connection established")
        self.connected = True
    
    def _start_connection(self):
        """Start WebSocket connection in background thread."""
        if not WEBSOCKET_AVAILABLE:
            raise ImportError("websocket-client not installed")
        
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
        
        # Wait for connection
        timeout = 10
        start = time.time()
        while not self.connected and time.time() - start < timeout:
            time.sleep(0.1)
        
        if not self.connected:
            raise ConnectionError("Failed to connect to WebSocket")
    
    def stop(self):
        """Stop WebSocket connection."""
        self.running = False
        if self.ws:
            self.ws.close()


def demo_integration_with_ttslo():
    """
    Demonstration of how WebSocket could integrate with TTSLO.
    
    This shows how the price monitoring loop could be modified to use
    WebSocket instead of REST API polling.
    """
    print("="*80)
    print("TTSLO WebSocket Integration Demo")
    print("="*80)
    print()
    
    if not WEBSOCKET_AVAILABLE:
        print("Error: websocket-client not installed")
        print("Install with: uv add websocket-client")
        return
    
    # Create price provider
    price_provider = WebSocketPriceProvider()
    
    # Example configuration (like in TTSLO config.csv)
    configs = [
        {
            'id': 'btc_profit',
            'pair': 'XBT/USD',  # WebSocket format
            'pair_rest': 'XXBTZUSD',  # REST format (for reference)
            'threshold_price': 50000,
            'threshold_type': 'above',
            'enabled': True
        },
        {
            'id': 'eth_dip',
            'pair': 'ETH/USD',
            'pair_rest': 'XETHZUSD',
            'threshold_price': 3000,
            'threshold_type': 'below',
            'enabled': True
        }
    ]
    
    # Define callback for price updates
    def on_price_update(pair, price):
        """Called whenever a price update is received."""
        timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S')
        print(f"[{timestamp}] {pair}: ${price:,.2f}")
        
        # Check all configs for triggers
        for config in configs:
            if not config['enabled']:
                continue
            
            if config['pair'] != pair:
                continue
            
            threshold = config['threshold_price']
            threshold_type = config['threshold_type']
            
            # Check if threshold is met
            triggered = False
            if threshold_type == 'above' and price >= threshold:
                triggered = True
            elif threshold_type == 'below' and price <= threshold:
                triggered = True
            
            if triggered:
                print(f"  ⚠️  TRIGGER: {config['id']} - {pair} {threshold_type} ${threshold:,.2f}")
                print(f"      Current price: ${price:,.2f}")
                # In real TTSLO, this would create a trailing stop loss order
    
    # Subscribe to all pairs with callback
    print("Subscribing to price feeds...")
    for config in configs:
        if config['enabled']:
            price_provider.subscribe(config['pair'], on_price_update)
            print(f"  ✓ Subscribed to {config['pair']}")
    
    print()
    print("Monitoring prices in real-time...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Monitor for 30 seconds
        time.sleep(30)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        price_provider.stop()
    
    print()
    print("Demo complete!")
    print()
    print("Benefits of WebSocket integration:")
    print("  • Instant price updates (no polling delay)")
    print("  • Lower latency for trigger detection")
    print("  • More efficient (no repeated API calls)")
    print("  • Automatic updates as market moves")
    print()


def demo_comparison():
    """
    Compare REST polling vs WebSocket for TTSLO use case.
    """
    print("="*80)
    print("REST Polling vs WebSocket Comparison for TTSLO")
    print("="*80)
    print()
    
    print("CURRENT METHOD (REST Polling):")
    print("  1. Every 60 seconds, poll Kraken REST API")
    print("  2. Get current price for each trading pair")
    print("  3. Check if any thresholds are met")
    print("  4. Wait 60 seconds, repeat")
    print()
    print("  Pros:")
    print("    + Simple implementation")
    print("    + Works with current code")
    print("    + Sufficient for most use cases")
    print()
    print("  Cons:")
    print("    - Up to 60 second delay in trigger detection")
    print("    - Repeated API calls (rate limit concerns)")
    print("    - Miss price movements between polls")
    print()
    
    print("WEBSOCKET METHOD (Real-Time):")
    print("  1. Establish WebSocket connection")
    print("  2. Subscribe to ticker feeds")
    print("  3. Receive price updates as trades occur")
    print("  4. Check thresholds on each update")
    print()
    print("  Pros:")
    print("    + Instant updates (< 1 second latency)")
    print("    + No polling overhead")
    print("    + Detect triggers immediately")
    print("    + See every price movement")
    print()
    print("  Cons:")
    print("    - More complex implementation")
    print("    - Need to handle reconnections")
    print("    - Requires persistent connection")
    print()
    
    print("RECOMMENDATION for TTSLO:")
    print("  • Current REST polling is ADEQUATE for most users")
    print("  • 60-second interval is reasonable for position management")
    print("  • WebSocket would be an optimization, not a necessity")
    print("  • Consider WebSocket if:")
    print("    - You need sub-minute trigger detection")
    print("    - You're monitoring many pairs")
    print("    - You want to minimize API rate limit usage")
    print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--compare':
        demo_comparison()
    else:
        demo_integration_with_ttslo()
