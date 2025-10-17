# Real-Time Multi-Pair Price Monitor TUI

An attractive Textual-based terminal user interface for monitoring cryptocurrency prices in real-time using Kraken's WebSocket API.

## Features

✨ **Multi-Pair Monitoring** - Track multiple cryptocurrency pairs simultaneously
📊 **Live Price Updates** - Real-time updates as trades occur on the exchange
💹 **Price Change Indicators** - Visual indicators for price increases (green) and decreases (red)
📈 **Bid/Ask Spreads** - Monitor bid/ask prices and spread percentages
📉 **24-Hour High/Low** - Track 24-hour price ranges
⏱️ **Live Statistics** - Update counter, uptime, and connection status
🎨 **Beautiful Interface** - Clean, colorful TUI powered by Textual
⌨️ **Keyboard Controls** - Easy navigation and refresh controls

## Installation

The TUI requires `textual` and `websocket-client` packages (already in project dependencies):

```bash
uv add textual websocket-client
```

## Usage

### Basic Usage (Monitor default pairs)

```bash
uv run python realtime_price_tui.py
```

This monitors 5 pairs by default: BTC/USD, ETH/USD, SOL/USD, ADA/USD, DOT/USD

### Custom Pairs

```bash
uv run python realtime_price_tui.py --pairs XBT/USD ETH/USD MATIC/USD
```

### Available Pairs

Use WebSocket format (with slash):
- `XBT/USD` - Bitcoin vs USD
- `ETH/USD` - Ethereum vs USD
- `SOL/USD` - Solana vs USD
- `ADA/USD` - Cardano vs USD
- `DOT/USD` - Polkadot vs USD
- `MATIC/USD` - Polygon vs USD
- `LINK/USD` - Chainlink vs USD
- `UNI/USD` - Uniswap vs USD
- And many more...

## Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│ 🚀 Kraken Real-Time Price Monitor                          │
├─────────────────────────────────────────────────────────────┤
│ 📊 Pairs: 5  │  📈 Updates: 247  │  ⏱️  Uptime: 00:03:45  │
├─────────────────────────────────────────────────────────────┤
│ Pair       │ Last Price │ Change        │ Bid/Ask/Spread   │
├────────────┼────────────┼───────────────┼──────────────────┤
│ XBT/USD    │ $108,050   │ +$6.20 (+0.01%)                │
│ ETH/USD    │ $3,881     │ -$2.50 (-0.06%)                │
│ SOL/USD    │ $184.50    │ +$0.80 (+0.43%)                │
│ ...        │            │                                  │
└─────────────────────────────────────────────────────────────┘
```

### Table Columns

- **Pair** - Trading pair name
- **Last Price** - Most recent trade price (green for up, red for down)
- **Change** - Price change from previous update with percentage
- **Bid** - Current best bid price
- **Ask** - Current best ask price
- **Spread** - Bid/ask spread with percentage
- **24h High** - Highest price in last 24 hours
- **24h Low** - Lowest price in last 24 hours
- **Updates** - Number of updates received for this pair
- **Last Update** - Time of last update (HH:MM:SS)

## Keyboard Shortcuts

- **Q** - Quit the application
- **R** - Refresh the display
- **Arrow Keys** - Navigate the table
- **Ctrl+C** - Force quit

## Color Coding

- 🟢 **Green** - Price increase
- 🔴 **Red** - Price decrease
- **White** - No change or initial value

## Technical Details

### WebSocket Connection

The TUI connects to Kraken's public WebSocket API at `wss://ws.kraken.com/` and subscribes to the ticker channel for all specified pairs. Updates are pushed in real-time as trades occur on the exchange.

### Update Frequency

- **REST API polling**: Would see updates at your polling interval (e.g., every 10 seconds)
- **WebSocket (this TUI)**: Receives updates immediately when trades occur (typically 20-60 updates per minute during active trading)

### No Authentication Required

This TUI uses Kraken's public market data feed and does not require API credentials.

## Comparison to Other Tools

### vs. Basic Price Monitor (`realtime_price_monitor.py`)
- ✅ Multiple pairs in single view (vs. sequential updates)
- ✅ Tabular layout with all data visible
- ✅ Live statistics and uptime tracking
- ✅ Color-coded price changes
- ✅ Interactive keyboard controls

### vs. REST API Polling (TTSLO)
- ✅ Instant updates when trades occur (no polling delay)
- ✅ Real-time monitoring vs. periodic checks
- ✅ Lower latency (sub-second vs. 10-60 second intervals)
- ❌ More complex (persistent connection vs. simple HTTP requests)

## Use Cases

1. **Market Monitoring** - Watch multiple pairs simultaneously
2. **Price Discovery** - See real-time bid/ask spreads
3. **Trading Analysis** - Monitor price movements and trading activity
4. **Research & Testing** - Verify API behavior and price update frequencies
5. **Educational** - Learn about WebSocket streaming and real-time data

## Example Session

```bash
$ uv run python realtime_price_tui.py --pairs XBT/USD ETH/USD SOL/USD

# TUI launches with real-time updates
# Price changes are highlighted in green/red
# Statistics update every second
# Press 'q' to quit
```

## Extending the TUI

The code is modular and can be extended with:

- **Additional data fields** - Volume, trades count, VWAP, etc.
- **Alerts** - Price threshold notifications
- **Charts** - Historical price charts
- **Export** - Save data to CSV or database
- **Multiple views** - Switch between different layouts
- **Filtering** - Show/hide specific pairs

## Performance

- **Memory**: ~50 MB for 5 pairs
- **CPU**: Minimal (updates are event-driven)
- **Network**: Persistent WebSocket connection (~1-2 KB/sec)
- **Latency**: Sub-second for price updates

## Troubleshooting

### "Error: websocket-client not installed"
```bash
uv add websocket-client
```

### "Error: textual not installed"
```bash
uv add textual
```

### Terminal not showing colors
Make sure your terminal supports ANSI colors and Unicode characters.

### Connection issues
- Check internet connectivity
- Verify Kraken's API status at status.kraken.com
- Try fewer pairs to reduce connection load

## Credits

- Built with [Textual](https://textual.textualize.io/) - Modern TUI framework
- Data from [Kraken WebSocket API](https://docs.kraken.com/websockets/)
- Part of the TTSLO project

## License

Same as TTSLO project - see main LICENSE file.
