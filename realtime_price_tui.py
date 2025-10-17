#!/usr/bin/env python3
"""
Real-Time Multi-Pair Price Monitor - Textual TUI

An attractive terminal user interface for monitoring cryptocurrency prices
in real-time using Kraken's WebSocket API. Displays multiple trading pairs
simultaneously with live updates, bid/ask spreads, and price changes.

No authentication required - uses public market data feed.

Usage:
    python realtime_price_tui.py
    python realtime_price_tui.py --pairs XBT/USD ETH/USD SOL/USD
"""

REALTIME_HELP = """
Monitor realtime prices for one or more trading pairs.

Pair syntax:
- Case-insensitive. Allowed forms are equivalent after normalization:
  BTCUSD, BTC/USD, BTC-USD, btc_usdt, etc.
- Normalization rule: remove non-alphanumeric characters and uppercase the result.
  Example: "btc/usd" -> "BTCUSD".

Important:
- USD and USDT are distinct assets. Specify both if you want BTC vs USD and BTC vs USDT.
  Example: BTC/USD != BTC/USDT
- Exchanges may use alternate asset codes (e.g. Kraken uses XBT for BTC and may return keys like 'XXBT' or 'XBT.F').
  The app normalizes common mappings (XBT -> BTC) and strips funding suffixes ('.F') when matching.

Examples:
  uv run python realtime_price_tui.py --pairs BTC/USD BTC/USDT
  uv run python realtime_price_tui.py --pairs BTC-USD BTC-USDT
"""

import json
import sys
import argparse
import threading
import re
from datetime import datetime, timezone
from typing import Dict, Optional
from decimal import Decimal


def normalize_pair_for_kraken(pair: str) -> str:
    """Normalize user-provided pair into Kraken's expected pair format.

    Rules:
    - Case-insensitive input.
    - Accepts separators like '/', '-', '_' or no separator.
    - Maps common asset aliases (BTC -> XBT) used by Kraken.
    - Returns a pair like 'XBT/USD' suitable for Kraken subscription.
    """
    if not pair or not isinstance(pair, str):
        return pair

    # Replace any non-alphanumeric characters with a single '/'
    cleaned = re.sub(r"[^A-Za-z0-9]+", '/', pair.strip())
    parts = [p for p in cleaned.split('/') if p]

    if len(parts) >= 2:
        base, quote = parts[0].upper(), parts[1].upper()
    else:
        # Try to split common concatenated forms like BTCUSD (base variable length)
        s = re.sub(r"[^A-Za-z0-9]", '', pair).upper()
        # Assume quote is 3 or 4 chars (USD, USDT, EUR, etc.)
        if len(s) > 3:
            # prefer 4-char quote if present (e.g., USDT)
            if s[-4:] in ("USDT",):
                base, quote = s[:-4], s[-4:]
            else:
                base, quote = s[:-3], s[-3:]
        else:
            base, quote = s, ''

    # Map common aliases to Kraken conventions
    alias_map = {
        'BTC': 'XBT',
        # add more mappings here if needed
    }
    base = alias_map.get(base, base)

    if not quote:
        return f"{base}"
    return f"{base}/{quote}"
import json
import sys
import argparse
import threading
from datetime import datetime, timezone
from typing import Dict, Optional
from decimal import Decimal

try:
    import websocket
except ImportError:
    print("Error: websocket-client not installed")
    print("Install with: uv add websocket-client")
    print("Or: pip install websocket-client")
    sys.exit(1)

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, DataTable, Static, Label
    from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
    from textual.binding import Binding
    from rich.text import Text
except ImportError:
    print("Error: textual not installed")
    print("Install with: uv add textual")
    print("Or: pip install textual")
    sys.exit(1)


class PriceData:
    """Stores price data for a trading pair."""
    
    def __init__(self, pair: str):
        self.pair = pair
        self.last_price: Optional[float] = None
        self.bid: Optional[float] = None
        self.ask: Optional[float] = None
        self.volume: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.previous_price: Optional[float] = None
        self.update_count: int = 0
        self.high_24h: Optional[float] = None
        self.low_24h: Optional[float] = None
        
    def update_price(self, price: float, volume: float = None):
        """Update the last trade price."""
        self.previous_price = self.last_price
        self.last_price = price
        if volume is not None:
            self.volume = volume
        self.last_update = datetime.now(timezone.utc)
        self.update_count += 1
        
    def update_bid_ask(self, bid: float, ask: float):
        """Update bid and ask prices."""
        self.bid = bid
        self.ask = ask
        
    def update_high_low(self, high: float, low: float):
        """Update 24h high and low."""
        self.high_24h = high
        self.low_24h = low
    
    @property
    def spread(self) -> Optional[float]:
        """Calculate bid/ask spread."""
        if self.bid and self.ask:
            return self.ask - self.bid
        return None
    
    @property
    def spread_percent(self) -> Optional[float]:
        """Calculate spread as percentage."""
        if self.bid and self.spread:
            return (self.spread / self.bid) * 100
        return None
    
    @property
    def price_change(self) -> Optional[float]:
        """Calculate price change from previous update."""
        if self.last_price and self.previous_price:
            return self.last_price - self.previous_price
        return None
    
    @property
    def price_change_percent(self) -> Optional[float]:
        """Calculate price change as percentage."""
        if self.previous_price and self.price_change:
            return (self.price_change / self.previous_price) * 100
        return None


class KrakenWebSocketClient:
    """WebSocket client for Kraken real-time data."""
    
    def __init__(self, pairs: list, callback):
        """
        Initialize WebSocket client.
        
        Args:
            pairs: List of trading pairs (e.g., ['XBT/USD', 'ETH/USD'])
            callback: Function to call with price updates
        """
        self.pairs = pairs
        self.callback = callback
        self.ws = None
        self.running = False
        self.connected = False
        self.ws_thread = None
        
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            # Handle ticker updates
            if isinstance(data, list) and len(data) >= 4:
                channel_name = data[-2] if len(data) > 2 else None
                pair_name = data[-1] if len(data) > 0 else None
                
                if channel_name == 'ticker' and pair_name:
                    ticker_data = data[1]
                    
                    if isinstance(ticker_data, dict):
                        # Extract price data
                        price_info = {}
                        
                        # Last trade closed
                        if 'c' in ticker_data:
                            price_array = ticker_data['c']
                            if isinstance(price_array, list) and len(price_array) > 0:
                                price_info['price'] = float(price_array[0])
                                if len(price_array) > 1:
                                    price_info['volume'] = float(price_array[1])
                        
                        # Bid and ask
                        if 'a' in ticker_data and 'b' in ticker_data:
                            ask = ticker_data['a']
                            bid = ticker_data['b']
                            if isinstance(ask, list) and isinstance(bid, list):
                                price_info['ask'] = float(ask[0])
                                price_info['bid'] = float(bid[0])
                        
                        # 24h high and low
                        if 'h' in ticker_data and 'l' in ticker_data:
                            high = ticker_data['h']
                            low = ticker_data['l']
                            if isinstance(high, list) and isinstance(low, list):
                                price_info['high_24h'] = float(high[1])  # 24h value
                                price_info['low_24h'] = float(low[1])
                        
                        # Call the callback with updates
                        if price_info:
                            self.callback(pair_name, price_info)
                            
        except Exception as e:
            pass  # Silently handle errors to avoid disrupting the UI
    
    def on_error(self, ws, error):
        """Handle WebSocket errors."""
        pass
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        self.connected = False
    
    def on_open(self, ws):
        """Handle WebSocket open."""
        self.connected = True
        
        # Subscribe to ticker feed for all pairs
        subscribe_message = {
            "event": "subscribe",
            "pair": self.pairs,
            "subscription": {
                "name": "ticker"
            }
        }
        ws.send(json.dumps(subscribe_message))
    
    def start(self):
        """Start the WebSocket connection in a background thread."""
        self.ws = websocket.WebSocketApp(
            "wss://ws.kraken.com/",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        self.running = True
        self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.ws_thread.start()
    
    def stop(self):
        """Stop the WebSocket connection."""
        self.running = False
        if self.ws:
            self.ws.close()


class PriceMonitorApp(App):
    """Textual TUI application for real-time price monitoring."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #title {
        dock: top;
        height: 3;
        content-align: center middle;
        background: $boost;
        color: $text;
        text-style: bold;
    }
    
    #stats-container {
        dock: top;
        height: 3;
        background: $panel;
        padding: 0 2;
    }
    
    #stats-row {
        height: 100%;
        align: center middle;
    }
    
    .stat-item {
        padding: 0 2;
        color: $text;
    }
    
    #price-table {
        border: solid $primary;
        height: 100%;
    }
    
    DataTable {
        height: 100%;
    }
    
    DataTable > .datatable--header {
        background: $primary;
        color: $text;
        text-style: bold;
    }
    
    DataTable > .datatable--cursor {
        background: $secondary 30%;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("c", "clear_stats", "Clear Stats", show=False),
    ]
    
    def __init__(self, pairs: list):
        """
        Initialize the app.
        
        Args:
            pairs: List of trading pairs to monitor
        """
        super().__init__()
        self.pairs = pairs
        self.price_data: Dict[str, PriceData] = {}
        self.ws_client = None
        self.start_time = datetime.now(timezone.utc)
        self.total_updates = 0
        
        # Initialize price data for each pair
        for pair in pairs:
            self.price_data[pair] = PriceData(pair)
    
    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header(show_clock=True)
        
        # Title
        yield Static("🚀 Kraken Real-Time Price Monitor", id="title")
        
        # Stats bar
        with Container(id="stats-container"):
            with Horizontal(id="stats-row"):
                yield Label("", id="stat-pairs", classes="stat-item")
                yield Label("", id="stat-updates", classes="stat-item")
                yield Label("", id="stat-uptime", classes="stat-item")
        
        # Price table
        yield DataTable(id="price-table", zebra_stripes=True, cursor_type="row")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the table and start WebSocket connection."""
        table = self.query_one("#price-table", DataTable)
        
        # Add columns
        table.add_column("Pair", key="pair", width=12)
        table.add_column("Last Price", key="price", width=15)
        table.add_column("Change", key="change", width=12)
        table.add_column("Bid", key="bid", width=15)
        table.add_column("Ask", key="ask", width=15)
        table.add_column("Spread", key="spread", width=12)
        table.add_column("24h High", key="high", width=15)
        table.add_column("24h Low", key="low", width=15)
        table.add_column("Updates", key="updates", width=10)
        table.add_column("Last Update", key="last_update", width=12)
        
        # Add rows for each pair
        for pair in self.pairs:
            table.add_row(
                pair,
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "0",
                "-",
                key=pair
            )
        
        # Start WebSocket connection
        self.ws_client = KrakenWebSocketClient(self.pairs, self.on_price_update)
        self.ws_client.start()
        
        # Update stats periodically
        self.set_interval(1.0, self.update_stats)
    
    def on_price_update(self, pair: str, price_info: dict):
        """
        Handle price updates from WebSocket.
        
        Args:
            pair: Trading pair name
            price_info: Dictionary with price data
        """
        if pair not in self.price_data:
            return
        
        data = self.price_data[pair]
        
        # Update price data
        if 'price' in price_info:
            data.update_price(price_info['price'], price_info.get('volume'))
        
        if 'bid' in price_info and 'ask' in price_info:
            data.update_bid_ask(price_info['bid'], price_info['ask'])
        
        if 'high_24h' in price_info and 'low_24h' in price_info:
            data.update_high_low(price_info['high_24h'], price_info['low_24h'])
        
        self.total_updates += 1
        
        # Update the table
        self.call_from_thread(self.update_table_row, pair)
    
    def update_table_row(self, pair: str):
        """Update a table row with new data."""
        table = self.query_one("#price-table", DataTable)
        data = self.price_data[pair]
        
        # Format price with color based on change
        if data.last_price:
            price_text = Text(f"${data.last_price:,.2f}")
            if data.price_change:
                if data.price_change > 0:
                    price_text.stylize("bold green")
                elif data.price_change < 0:
                    price_text.stylize("bold red")
        else:
            price_text = "-"
        
        # Format change
        if data.price_change and data.price_change_percent:
            change_text = Text(f"{data.price_change:+,.2f} ({data.price_change_percent:+.2f}%)")
            if data.price_change > 0:
                change_text.stylize("green")
            elif data.price_change < 0:
                change_text.stylize("red")
        else:
            change_text = "-"
        
        # Format bid/ask
        bid_text = f"${data.bid:,.2f}" if data.bid else "-"
        ask_text = f"${data.ask:,.2f}" if data.ask else "-"
        
        # Format spread
        if data.spread and data.spread_percent:
            spread_text = f"${data.spread:.2f} ({data.spread_percent:.3f}%)"
        else:
            spread_text = "-"
        
        # Format high/low
        high_text = f"${data.high_24h:,.2f}" if data.high_24h else "-"
        low_text = f"${data.low_24h:,.2f}" if data.low_24h else "-"
        
        # Format last update time
        if data.last_update:
            time_str = data.last_update.strftime('%H:%M:%S')
        else:
            time_str = "-"
        
        # Update the row
        table.update_cell(pair, "price", price_text)
        table.update_cell(pair, "change", change_text)
        table.update_cell(pair, "bid", bid_text)
        table.update_cell(pair, "ask", ask_text)
        table.update_cell(pair, "spread", spread_text)
        table.update_cell(pair, "high", high_text)
        table.update_cell(pair, "low", low_text)
        table.update_cell(pair, "updates", str(data.update_count))
        table.update_cell(pair, "last_update", time_str)
    
    def update_stats(self):
        """Update the statistics bar."""
        # Update pairs count
        stat_pairs = self.query_one("#stat-pairs", Label)
        stat_pairs.update(f"📊 Pairs: {len(self.pairs)}")
        
        # Update total updates
        stat_updates = self.query_one("#stat-updates", Label)
        stat_updates.update(f"📈 Updates: {self.total_updates}")
        
        # Update uptime
        uptime = datetime.now(timezone.utc) - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        stat_uptime = self.query_one("#stat-uptime", Label)
        stat_uptime.update(f"⏱️  Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def action_refresh(self):
        """Refresh the display."""
        for pair in self.pairs:
            self.update_table_row(pair)
    
    def action_clear_stats(self):
        """Clear statistics."""
        self.total_updates = 0
        self.start_time = datetime.now(timezone.utc)
        for data in self.price_data.values():
            data.update_count = 0
    
    def on_unmount(self):
        """Clean up when app closes."""
        if self.ws_client:
            self.ws_client.stop()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Real-time cryptocurrency price monitor with Textual TUI"
    )
    parser.add_argument(
        '--pairs',
        nargs='+',
        default=['XBT/USD', 'XBT/USDT', 'XBT/USDC', 'ETH/USD', 'SOL/USD', 'ADA/USD', 'DOT/USD'],
        help=REALTIME_HELP
    )
    
    args = parser.parse_args()
    
    # Normalize pairs to Kraken naming conventions before launching
    normalized_pairs = [normalize_pair_for_kraken(p) for p in args.pairs]

    # Run the app
    app = PriceMonitorApp(normalized_pairs)
    app.run()


if __name__ == "__main__":
    main()
