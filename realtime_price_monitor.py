#!/usr/bin/env python3
"""
Real-Time Price Monitor - WebSocket Demo

This script demonstrates how to get real-time BTC/USD prices from Kraken
using the WebSocket API. It's a simple, production-ready example that can
be adapted for use in trading applications.

No authentication required - uses public market data feed.
"""
import json
import sys
import signal
from datetime import datetime, timezone

try:
    import websocket
except ImportError:
    print("Error: websocket-client not installed")
    print("Install with: uv add websocket-client")
    print("Or: pip install websocket-client")
    sys.exit(1)


class KrakenPriceMonitor:
    """Real-time price monitor using Kraken WebSocket API."""
    
    def __init__(self, pairs=['XBT/USD']):
        """
        Initialize price monitor.
        
        Args:
            pairs: List of trading pairs to monitor (WebSocket format: 'XBT/USD')
        """
        self.pairs = pairs
        self.ws = None
        self.running = False
        self.prices = {}  # Store latest price for each pair
        
    def on_message(self, ws, message):
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
                            volume = float(price_array[1])
                            
                            # Store the latest price
                            self.prices[pair_name] = price
                            
                            # Format timestamp
                            timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]
                            
                            # Display the update
                            print(f"[{timestamp}] {pair_name:>12} | ${price:>12,.2f} | Volume: {volume:.8f}")
                    
                    # Also show bid/ask spread
                    if 'a' in ticker_data and 'b' in ticker_data:
                        ask = float(ticker_data['a'][0])
                        bid = float(ticker_data['b'][0])
                        spread = ask - bid
                        spread_pct = (spread / bid) * 100
                        
                        # Only print spread on first update or significant changes
                        if spread_pct > 0.01:  # More than 0.01% spread
                            print(f"             {'':>12} | Spread: ${spread:>10,.2f} ({spread_pct:.3f}%)")
            
            # Handle heartbeat (silent - just keep alive)
            elif isinstance(data, dict) and data.get('event') == 'heartbeat':
                pass
                
            # Handle subscription confirmation
            elif isinstance(data, dict) and data.get('event') == 'subscriptionStatus':
                status = data.get('status')
                channel = data.get('channelName')
                pair = data.get('pair')
                
                if status == 'subscribed':
                    print(f"✓ Subscribed to {channel} for {pair}")
                elif status == 'error':
                    error_msg = data.get('errorMessage', 'Unknown error')
                    print(f"✗ Subscription error: {error_msg}")
                    
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket errors."""
        print(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        print(f"\n✗ WebSocket connection closed")
        self.running = False
    
    def on_open(self, ws):
        """Handle WebSocket open."""
        print(f"✓ Connected to Kraken WebSocket")
        
        # Subscribe to ticker feed for all pairs
        subscribe_message = {
            "event": "subscribe",
            "pair": self.pairs,
            "subscription": {
                "name": "ticker"
            }
        }
        ws.send(json.dumps(subscribe_message))
        print(f"→ Requesting ticker data for: {', '.join(self.pairs)}\n")
    
    def start(self):
        """Start monitoring prices in real-time."""
        print(f"\n{'='*80}")
        print(f"Kraken Real-Time Price Monitor")
        print(f"{'='*80}")
        print(f"Monitoring: {', '.join(self.pairs)}")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*80}\n")
        
        # Set up signal handler for clean shutdown
        def signal_handler(sig, frame):
            print("\n\nShutting down...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Create WebSocket connection
        self.ws = websocket.WebSocketApp(
            "wss://ws.kraken.com/",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run forever (blocking)
        self.running = True
        self.ws.run_forever()
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.ws:
            self.ws.close()
    
    def get_current_prices(self):
        """Get the most recent prices for all monitored pairs."""
        return self.prices.copy()


def main():
    """Main entry point."""
    # Define pairs to monitor (you can add more)
    pairs = ['XBT/USD', 'ETH/USD']
    
    # Create and start monitor
    monitor = KrakenPriceMonitor(pairs=pairs)
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        monitor.stop()
    except Exception as e:
        print(f"\nError: {e}")
        monitor.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
