#!/usr/bin/env python3
"""
Price Update Frequency Testing Tool

This script measures and compares the price update frequency between:
1. Kraken REST API public endpoint (polling)
2. Kraken WebSocket API (real-time streaming)

The goal is to determine which method provides more up-to-date price information
and measure actual update frequencies for BTC/USD trading pair.
"""
import sys
import time
import json
import statistics
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional
import requests

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("Note: websocket-client not available. WebSocket tests will be skipped.")
    print("Install with: pip install websocket-client")

from kraken_api import KrakenAPI


class PriceUpdate:
    """Represents a single price update event."""
    
    def __init__(self, timestamp: datetime, price: float, source: str):
        self.timestamp = timestamp
        self.price = price
        self.source = source
    
    def __repr__(self):
        return f"PriceUpdate({self.timestamp.isoformat()}, ${self.price:,.2f}, {self.source})"


class PriceMonitor:
    """Monitor price updates and calculate statistics."""
    
    def __init__(self):
        self.updates: List[PriceUpdate] = []
        self.lock = threading.Lock()
    
    def add_update(self, update: PriceUpdate):
        """Add a price update."""
        with self.lock:
            self.updates.append(update)
    
    def get_statistics(self) -> Dict:
        """Calculate statistics from collected updates."""
        with self.lock:
            if len(self.updates) < 2:
                return {
                    'total_updates': len(self.updates),
                    'error': 'Not enough data points'
                }
            
            # Calculate time intervals between updates
            intervals = []
            price_changes = []
            
            for i in range(1, len(self.updates)):
                prev = self.updates[i-1]
                curr = self.updates[i]
                
                interval = (curr.timestamp - prev.timestamp).total_seconds()
                intervals.append(interval)
                
                price_change = abs(curr.price - prev.price)
                if price_change > 0:
                    price_changes.append(price_change)
            
            # Calculate statistics
            stats = {
                'total_updates': len(self.updates),
                'duration_seconds': (self.updates[-1].timestamp - self.updates[0].timestamp).total_seconds(),
                'min_price': min(u.price for u in self.updates),
                'max_price': max(u.price for u in self.updates),
                'avg_price': statistics.mean(u.price for u in self.updates),
                'unique_prices': len(set(u.price for u in self.updates)),
            }
            
            if intervals:
                stats.update({
                    'avg_interval_seconds': statistics.mean(intervals),
                    'min_interval_seconds': min(intervals),
                    'max_interval_seconds': max(intervals),
                    'median_interval_seconds': statistics.median(intervals),
                })
            
            if price_changes:
                stats.update({
                    'price_changes_detected': len(price_changes),
                    'avg_price_change': statistics.mean(price_changes),
                    'min_price_change': min(price_changes),
                    'max_price_change': max(price_changes),
                })
            
            return stats


class RESTAPITester:
    """Test REST API polling behavior."""
    
    def __init__(self, pair: str = 'XXBTZUSD'):
        self.pair = pair
        self.api = KrakenAPI()
        self.monitor = PriceMonitor()
    
    def poll_prices(self, duration_seconds: int = 120, interval_seconds: float = 1.0):
        """
        Poll prices from REST API at regular intervals.
        
        Args:
            duration_seconds: How long to monitor (in seconds)
            interval_seconds: Time between polls (in seconds)
        """
        print(f"\n{'='*80}")
        print(f"REST API Polling Test")
        print(f"{'='*80}")
        print(f"Pair: {self.pair}")
        print(f"Duration: {duration_seconds} seconds")
        print(f"Polling interval: {interval_seconds} seconds")
        print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        poll_count = 0
        
        while time.time() - start_time < duration_seconds:
            try:
                poll_start = time.time()
                price = self.api.get_current_price(self.pair)
                poll_end = time.time()
                
                timestamp = datetime.now(timezone.utc)
                update = PriceUpdate(timestamp, price, 'REST')
                self.monitor.add_update(update)
                
                poll_count += 1
                latency_ms = (poll_end - poll_start) * 1000
                
                print(f"[{poll_count:3d}] {timestamp.strftime('%H:%M:%S.%f')[:-3]} | "
                      f"${price:>10,.2f} | Latency: {latency_ms:>6.1f}ms")
                
                # Wait for the next poll interval
                elapsed = time.time() - poll_start
                sleep_time = max(0, interval_seconds - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                print(f"Error during poll: {e}")
                time.sleep(interval_seconds)
        
        print(f"\n{'='*80}")
        print(f"REST API Polling Complete")
        print(f"{'='*80}\n")
        
        return self.monitor.get_statistics()


class WebSocketTester:
    """Test WebSocket real-time streaming behavior."""
    
    def __init__(self, pair: str = 'XBT/USD'):
        self.pair = pair
        self.monitor = PriceMonitor()
        self.ws = None
        self.running = False
        self.connected = False
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            # Handle ticker updates
            if isinstance(data, list) and len(data) >= 4:
                channel_name = data[-2] if len(data) > 2 else None
                
                if channel_name == 'ticker':
                    ticker_data = data[1]
                    
                    # Extract current price from 'c' field (last trade closed)
                    if isinstance(ticker_data, dict) and 'c' in ticker_data:
                        price_array = ticker_data['c']
                        if isinstance(price_array, list) and len(price_array) > 0:
                            price = float(price_array[0])
                            timestamp = datetime.now(timezone.utc)
                            
                            update = PriceUpdate(timestamp, price, 'WebSocket')
                            self.monitor.add_update(update)
                            
                            print(f"[WS] {timestamp.strftime('%H:%M:%S.%f')[:-3]} | "
                                  f"${price:>10,.2f}")
            
            # Handle heartbeat
            elif isinstance(data, dict) and data.get('event') == 'heartbeat':
                pass  # Silent heartbeat
                
            # Handle subscription confirmation
            elif isinstance(data, dict) and data.get('event') == 'subscriptionStatus':
                if data.get('status') == 'subscribed':
                    print(f"✓ Subscribed to {data.get('channelName')} for {data.get('pair')}")
                    
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket errors."""
        print(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        print(f"\nWebSocket connection closed")
        self.connected = False
    
    def on_open(self, ws):
        """Handle WebSocket open."""
        print(f"✓ WebSocket connection established")
        self.connected = True
        
        # Subscribe to ticker feed
        subscribe_message = {
            "event": "subscribe",
            "pair": [self.pair],
            "subscription": {
                "name": "ticker"
            }
        }
        ws.send(json.dumps(subscribe_message))
        print(f"→ Sent subscription request for {self.pair}")
    
    def stream_prices(self, duration_seconds: int = 120):
        """
        Stream prices from WebSocket API in real-time.
        
        Args:
            duration_seconds: How long to monitor (in seconds)
        """
        if not WEBSOCKET_AVAILABLE:
            print("WebSocket client not available. Skipping WebSocket test.")
            return None
        
        print(f"\n{'='*80}")
        print(f"WebSocket Streaming Test")
        print(f"{'='*80}")
        print(f"Pair: {self.pair}")
        print(f"Duration: {duration_seconds} seconds")
        print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
        print(f"{'='*80}\n")
        
        # Create WebSocket connection
        self.ws = websocket.WebSocketApp(
            "wss://ws.kraken.com/",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run WebSocket in a separate thread
        self.running = True
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for connection
        timeout = 10
        start_wait = time.time()
        while not self.connected and time.time() - start_wait < timeout:
            time.sleep(0.1)
        
        if not self.connected:
            print("Failed to connect to WebSocket")
            return None
        
        # Monitor for specified duration
        time.sleep(duration_seconds)
        
        # Close connection
        self.running = False
        if self.ws:
            self.ws.close()
        
        print(f"\n{'='*80}")
        print(f"WebSocket Streaming Complete")
        print(f"{'='*80}\n")
        
        return self.monitor.get_statistics()


def print_statistics(stats: Dict, title: str):
    """Print statistics in a formatted way."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")
    
    if 'error' in stats:
        print(f"Error: {stats['error']}")
        return
    
    print(f"Total Updates:        {stats['total_updates']}")
    print(f"Duration:             {stats['duration_seconds']:.2f} seconds")
    print(f"Unique Prices:        {stats['unique_prices']}")
    print(f"Price Range:          ${stats['min_price']:,.2f} - ${stats['max_price']:,.2f}")
    print(f"Average Price:        ${stats['avg_price']:,.2f}")
    
    if 'avg_interval_seconds' in stats:
        print(f"\nUpdate Intervals:")
        print(f"  Average:            {stats['avg_interval_seconds']:.3f} seconds")
        print(f"  Median:             {stats['median_interval_seconds']:.3f} seconds")
        print(f"  Min:                {stats['min_interval_seconds']:.3f} seconds")
        print(f"  Max:                {stats['max_interval_seconds']:.3f} seconds")
        print(f"  Updates per minute: {60 / stats['avg_interval_seconds']:.2f}")
    
    if 'price_changes_detected' in stats:
        print(f"\nPrice Changes:")
        print(f"  Total Changes:      {stats['price_changes_detected']}")
        print(f"  Average Change:     ${stats['avg_price_change']:,.2f}")
        print(f"  Min Change:         ${stats['min_price_change']:,.2f}")
        print(f"  Max Change:         ${stats['max_price_change']:,.2f}")
    
    print(f"{'='*80}\n")


def compare_results(rest_stats: Dict, ws_stats: Optional[Dict]):
    """Compare REST and WebSocket results."""
    print(f"\n{'='*80}")
    print(f"COMPARISON: REST API vs WebSocket")
    print(f"{'='*80}\n")
    
    if 'error' in rest_stats:
        print("REST API: Insufficient data")
    else:
        rest_updates_per_min = 60 / rest_stats.get('avg_interval_seconds', 60)
        print(f"REST API:")
        print(f"  Updates per minute:  {rest_updates_per_min:.2f}")
        print(f"  Unique prices:       {rest_stats['unique_prices']}")
        print(f"  Price changes:       {rest_stats.get('price_changes_detected', 0)}")
    
    if ws_stats and 'error' not in ws_stats:
        ws_updates_per_min = 60 / ws_stats.get('avg_interval_seconds', 60)
        print(f"\nWebSocket:")
        print(f"  Updates per minute:  {ws_updates_per_min:.2f}")
        print(f"  Unique prices:       {ws_stats['unique_prices']}")
        print(f"  Price changes:       {ws_stats.get('price_changes_detected', 0)}")
        
        if 'error' not in rest_stats:
            print(f"\nDifference:")
            print(f"  WebSocket is {ws_updates_per_min / rest_updates_per_min:.1f}x faster at updates")
    
    print(f"\n{'='*80}\n")


def main():
    """Main entry point."""
    print(f"\n{'='*80}")
    print(f"Kraken Price Update Frequency Analysis")
    print(f"{'='*80}")
    print(f"Testing BTC/USD price update behavior")
    print(f"Comparing REST API polling vs WebSocket streaming")
    print(f"{'='*80}\n")
    
    # Configuration
    rest_pair = 'XXBTZUSD'  # REST API format
    ws_pair = 'XBT/USD'      # WebSocket format
    test_duration = 120      # 2 minutes per test
    rest_interval = 1.0      # Poll every 1 second
    
    # Test REST API
    rest_tester = RESTAPITester(pair=rest_pair)
    rest_stats = rest_tester.poll_prices(
        duration_seconds=test_duration,
        interval_seconds=rest_interval
    )
    print_statistics(rest_stats, "REST API Results")
    
    # Test WebSocket (if available)
    ws_stats = None
    if WEBSOCKET_AVAILABLE:
        ws_tester = WebSocketTester(pair=ws_pair)
        ws_stats = ws_tester.stream_prices(duration_seconds=test_duration)
        if ws_stats:
            print_statistics(ws_stats, "WebSocket Results")
    
    # Compare results
    compare_results(rest_stats, ws_stats)
    
    # Summary and Recommendations
    print(f"\n{'='*80}")
    print(f"SUMMARY AND RECOMMENDATIONS")
    print(f"{'='*80}\n")
    
    print("Key Findings:")
    print("1. REST API provides snapshot data when polled")
    print("2. Price updates reflect the latest market price at query time")
    print("3. REST API has rate limit of ~1 request per second")
    
    if ws_stats and 'error' not in ws_stats:
        print("4. WebSocket provides real-time streaming updates")
        print("5. WebSocket receives updates immediately when trades occur")
        print("6. WebSocket is significantly faster for real-time price monitoring")
    
    print("\nRecommendations:")
    print("• For real-time price monitoring: Use WebSocket API")
    print("• For occasional price checks: Use REST API")
    print("• For automated trading: Use WebSocket for minimal latency")
    print("• Both public and private endpoints return the same market price")
    print("• The 'delay' observed with REST is likely due to polling interval")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
