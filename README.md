# TTSLO - Triggered Trailing Stop Loss Orders

A Python tool for Kraken.com that monitors cryptocurrency prices and automatically creates Trailing Stop Loss (TSL) orders when specified price thresholds are met.

## ⚠️ Security Notice

TTSLO is designed with **fail-safe** order handling. The system will **NEVER** create an order if anything is uncertain or abnormal. See [SECURITY.md](docs/SECURITY.md) for complete safety guarantees and security documentation.

## Overview

The Kraken.com exchange allows for Trailing Stop Loss (TSL) orders, but you can only create them at the current market price with a percentage offset. This tool solves that limitation by:

- Monitoring cryptocurrency prices continuously
- Creating TSL orders automatically when your specified price thresholds are reached
- Providing flexible configuration through CSV files
- Supporting dry-run mode for testing
- Maintaining state and comprehensive logging

## Features

- **Real-Time WebSocket Price Monitoring**: Get instant price updates via Kraken's WebSocket API (90,000x faster than REST!)
- **Find Profitable Candidates**: Analyze volatility to identify bracketing opportunities (NEW!)
- **Fail-Safe Order Logic**: Never creates incorrect orders under any circumstances
- **Robust Error Handling**: Comprehensive error detection and recovery for API failures (timeouts, connection issues, server errors)
- **Price Threshold Triggers**: Set price levels (above/below) that trigger TSL order creation
- **CSV-based Configuration**: Simple CSV files for configuration, state, and logs
- **Interactive CSV Editor**: Built-in TUI for editing configuration files with keyboard navigation
- **Telegram Notifications**: Get real-time alerts via Telegram for triggers, orders, and errors (optional)
- **Dry-Run Mode**: Test your configurations without creating real orders
- **Verbose Debug Mode**: Detailed logging for troubleshooting
- **Continuous Monitoring**: Runs continuously and checks prices at regular intervals
- **State Persistence**: Tracks which triggers have fired to avoid duplicates
- **Flexible Configuration**: Support for multiple trading pairs and strategies
- **Comprehensive Validation**: Pre-flight checks prevent invalid configurations

## Installation

1. Clone this repository:
```bash
git clone https://github.com/raymondclowe/ttslo.git
cd ttslo
```

2. Install dependencies:

**Option A: Using uv (recommended)**
```bash
uv sync
```

**Option B: Using pip**
```bash
pip install -r requirements.txt
pip install textual  # For the CSV editor
```

---

Alternatively, you can use the new method:

2. Install dependencies using uv:
```bash
uv sync
```

**What is uv?** [uv](https://github.com/astral-sh/uv) is a fast Python package manager and project manager. If you don't have uv installed, you can install it first:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```
```

3. Set up your Kraken API credentials:

**Option A: Environment Variables**
```bash
# Read-only credentials (for price monitoring)
export KRAKEN_API_KEY="your_readonly_api_key"
export KRAKEN_API_SECRET="your_readonly_api_secret"

# Read-write credentials (for creating orders)
export KRAKEN_API_KEY_RW="your_readwrite_api_key"
export KRAKEN_API_SECRET_RW="your_readwrite_api_secret"
```

**Option B: .env File**
Create a `.env` file in the project directory:
```
KRAKEN_API_KEY=your_readonly_api_key
KRAKEN_API_SECRET=your_readonly_api_secret
KRAKEN_API_KEY_RW=your_readwrite_api_key
KRAKEN_API_SECRET_RW=your_readwrite_api_secret
```

**Note:** The tool checks for credentials from multiple sources:
- Standard names (e.g., `KRAKEN_API_KEY`)
- Copilot-prefixed names (e.g., `copilot_KRAKEN_API_KEY`)
- COPILOT_W_* variants (e.g., `COPILOT_W_KR_RO_PUBLIC`)
- GitHub environment secrets (e.g., `COPILOT_KRAKEN_API_KEY`, `COPILOT_KRAKEN_API_SECRET`)

This allows flexible deployment in development, CI/CD, and production environments.

## Quick Start

1. Create a sample configuration file:
```bash
uv run ttslo.py --create-sample-config
```

2. Edit `config_sample.csv` and save it as `config.csv`:

**Option A: Using the CSV Editor TUI**
```bash
uv run python csv_editor.py config_sample.csv
# Edit the file, then press Ctrl+S to save
# Copy or rename to config.csv
```

**Option B: Manual editing**
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_1,XXBTZUSD,50000,above,sell,0.01,5.0,true
eth_1,XETHZUSD,3000,above,sell,0.1,3.5,true
```

3. Validate your configuration:
```bash
uv run ttslo.py --validate-config
```

4. Test your configuration in dry-run mode:
```bash
uv run ttslo.py --dry-run --verbose --once
```

5. Run continuously:
```bash
uv run ttslo.py --interval 60
```

## WebSocket Real-Time Price Monitoring

TTSLO now uses Kraken's WebSocket API for real-time price updates, providing:

- **Instant Updates**: Receive prices as trades occur on Kraken (sub-second latency)
- **90,000x Faster**: Cached price access in 0.003ms vs 270ms for REST API
- **Lower API Usage**: Single persistent connection instead of repeated polling
- **Automatic Fallback**: If WebSocket fails, automatically uses REST API

### Performance

| Operation | REST API | WebSocket | Improvement |
|-----------|----------|-----------|-------------|
| First price request | 270ms | 1,700ms | -6x (one-time) |
| Cached price access | 270ms | 0.003ms | **90,000x** |
| Real-time updates | 60s delay | <1s latency | **60x+** |

### Usage

WebSocket is enabled by default - no configuration needed! For more details, see [WEBSOCKET_INTEGRATION.md](docs/WEBSOCKET_INTEGRATION.md).

To disable WebSocket (use REST only):
```python
# In your code
api = KrakenAPI(use_websocket=False)
```

## CSV Editor

TTSLO includes an interactive TUI (Text User Interface) for editing configuration files. The CSV editor provides a user-friendly way to view and modify your configuration without manually editing CSV files.

### Smart Config File Detection

When you run the CSV editor without specifying a file, it automatically detects the correct config:

```bash
# Automatically uses the service's config file
uv run python csv_editor.py

# Explicitly specify a file
uv run python csv_editor.py /var/lib/ttslo/config.csv
```

The editor checks (in priority order):
1. `TTSLO_CONFIG_FILE` environment variable (same as the service uses)
2. If running as `ttslo` user → `/var/lib/ttslo/config.csv`
3. Otherwise → `config.csv` in current directory

### Safe Concurrent Editing

The CSV editor uses a coordination protocol to prevent race conditions:
- **Handshake Protocol**: Editor requests lock, service confirms when idle
- **Service Pauses**: Service suspends all I/O during editing (reads, writes, logs)
- **Zero Race Conditions**: Service finishes ongoing operations before editor locks
- **No Downtime**: Edit config while service is running - no restart needed!

The coordination ensures the service completes any in-progress write operations before the editor locks the file, eliminating all race condition risks.

### Usage Examples

```bash
# Edit the service's active config (auto-detected)
uv run python csv_editor.py

# Edit a specific file
uv run python csv_editor.py config.csv

# Edit with environment override
TTSLO_CONFIG_FILE=/var/lib/ttslo/config.csv uv run python csv_editor.py

# Edit the sample config
uv run python csv_editor.py config_sample.csv

# Edit any CSV file
uv run python csv_editor.py yourfile.csv
```

### Key Bindings

- `Ctrl+S`: Save the CSV file
- `Ctrl+Q`: Quit the application (prompts if unsaved)
- `Ctrl+N`: Add a new row
- `Ctrl+D`: Delete the current row
- `Ctrl+Shift+D`: Duplicate the current row
- `Enter` or `e`: Edit the selected cell
- `?` or `F1`: Show help screen
- `Arrow Keys`: Navigate the table
- `Tab/Shift+Tab`: Navigate between cells

### Features

- **Smart file detection**: Automatically finds the service's config
- **File locking**: Prevents conflicts with the running service
- **Help screen**: Press `?` or `F1` for comprehensive help
- **Row duplication**: Quickly duplicate rows with `Ctrl+Shift+D`
- **Unsaved changes indicator**: `*` in title shows unsaved changes
- **Quit confirmation**: Prompts to save when quitting with unsaved changes
- **Inline editing with smart dropdowns**: Binary fields (above/below, buy/sell) use dropdown with single-key selection
- Interactive table view with color-coded rows
- Inline editor with validation and smart defaults
- Cell-level validation for configuration fields:
  - `threshold_type`: dropdown (A=Above, B=Below)
  - `direction`: dropdown (B=Buy, S=Sell)
  - `enabled`: dropdown (T=True, F=False)
  - `pair`: validates against known Kraken pairs
  - `id`: prevents duplicate IDs
- Add and delete rows
- Visual notifications for all operations
- Keyboard-driven workflow

For detailed documentation, see [CSV_EDITOR_README.md](docs/CSV_EDITOR_README.md).

**Roadmap**: We're continuously improving the CSV Editor! See [CSV_EDITOR_ROADMAP.md](docs/CSV_EDITOR_ROADMAP.md) for planned enhancements. Recent additions include help screen, row duplication, unsaved changes indicators, and inline editing with smart dropdowns.

## Web Dashboard

TTSLO includes a Flask-based web dashboard for monitoring your orders in real-time. The dashboard provides a clean, executive-style interface with four main views:

### Features

- **Pending Orders**: View orders that haven't triggered yet, with visual progress bars showing how close they are to triggering
- **Active TSL Orders**: Monitor orders that have triggered and are currently active on Kraken
- **Completed Orders**: Review executed orders with benefit calculations comparing trigger price vs execution price
- **Asset Balances & Risk**: Monitor account balances and analyze risk for pending and active orders
  - Shows available balance for each asset involved in pending/active orders
  - Calculates coverage: how much of order requirements are covered by current balances
  - Risk warnings: CRITICAL (insufficient), WARNING (low coverage), SAFE (sufficient)
  - Analyzes both buy orders (need quote currency) and sell orders (need base currency)
  - Helps identify when to top up balances or cancel orders before failures occur
- **Real-Time Data**: Auto-refreshes every 30 seconds with live price updates from Kraken
- **High Performance**: Hybrid memory + disk caching for instant loads even after service restarts
- **Clean Design**: Simple, professional interface with no distracting colors or gradients

### Usage

Start the dashboard:
```bash
# Default settings (localhost:5000)
uv run python dashboard.py

# Custom host and port
uv run python dashboard.py --host 0.0.0.0 --port 8080

# Enable debug mode
uv run python dashboard.py --debug
```

Then open your browser to `http://localhost:5000` (or your specified host/port).

### Environment Variables

The dashboard respects the following environment variables:
- `TTSLO_CONFIG_FILE`: Path to config.csv (default: config.csv)
- `TTSLO_STATE_FILE`: Path to state.csv (default: state.csv)
- `TTSLO_LOG_FILE`: Path to logs.csv (default: logs.csv)
- `TTSLO_CHECK_INTERVAL`: Main monitor check interval in seconds (default: 60)
- `TTSLO_CACHE_DIR`: Directory for persistent disk cache (default: .cache)

### Performance & Caching

The dashboard uses a hybrid caching system for optimal performance:
- **Memory Cache** (L1): Fast in-memory cache for sub-second response times
- **Disk Cache** (L2): Persistent JSON cache that survives restarts

Benefits:
- First load after restart: **< 1 second** (disk cache)
- Subsequent loads: **< 0.01 seconds** (memory cache)
- Reduced Kraken API calls by ~90%
- Instant dashboard availability after service restarts

Monitor cache performance:
```bash
curl http://localhost:5000/api/cache-stats
```

See [docs/CACHE_CONFIGURATION.md](docs/CACHE_CONFIGURATION.md) for detailed configuration options.

### API Endpoints

The dashboard exposes REST API endpoints for integration:
- `GET /api/status` - System status and configuration
- `GET /api/cache-stats` - Cache statistics and performance metrics
- `GET /api/pending` - List of pending orders
- `GET /api/active` - List of active TSL orders
- `GET /api/completed` - List of completed orders
- `GET /api/balances` - Asset balances and risk analysis for pending/active orders
- `GET /health` - Health check endpoint (returns 200 if healthy, 503 if unhealthy)
- `GET /backup` - Download backup zip file with all config, state, and log files
- `GET /openapi.json` - OpenAPI 3.0 specification for API discovery

### Security Note

The dashboard requires read-write Kraken API credentials to enable cancel functionality (cancel pending orders, cancel active orders, cancel all). It's designed for local use and should not be exposed to the internet without additional security measures.

When running with `--host 0.0.0.0`, the dashboard binds to all network interfaces, making it accessible from your local network. To restrict access to your local subnet only, use firewall rules:

```bash
# Example: Allow access only from local subnet (192.168.1.0/24)
sudo ufw allow from 192.168.1.0/24 to any port 5000
sudo ufw deny 5000

# Or using iptables
sudo iptables -A INPUT -p tcp --dport 5000 -s 192.168.1.0/24 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 5000 -j DROP
```

The systemd service uses `--host 0.0.0.0` for network access while remaining protected by the system firewall.

## Understanding "Benefit" (Slippage) in Completed Orders

**Important:** The "Benefit" (now labeled "Slippage") in the dashboard's Completed Orders section is often negative - **this is normal and expected for Trailing Stop Loss orders!**

The slippage metric shows the difference between your trigger price and the actual execution price. Trailing stop loss orders naturally have negative slippage because the price must move against you (by the trailing offset %) before the order executes.

**Example:**
- SELL order triggers at $2.53
- With 1% trailing offset, it executes when price drops to ~$2.50
- Slippage: -$0.03 (-1.23%)
- **This is the cost of TSL protection, NOT a net loss on your trade!**

### Key Points:

1. **Negative slippage is normal** - expect -1% to -2% matching your trailing offset
2. **Focus on total profit** - Did you buy low and sell high overall?
3. **It's like insurance** - Small cost for protection from bad fill prices
4. **Bracket strategy works** - Despite slippage, you profit from price oscillations

For a complete explanation with examples, see: [Understanding Benefit (Slippage)](docs/UNDERSTANDING_BENEFIT.md)

## Tools

### Cryptocurrency Statistics Analysis

Analyze minute-by-minute price statistics to predict price movements and generate profitable trading configurations.

```bash
# Analyze default pairs (30+ popular coins)
python3 tools/coin_stats.py

# Profit-based config generation (NEW!)
python3 tools/coin_stats.py \
  --pairs XXBTZUSD XETHZUSD SOLUSD \
  --percentage-profit 5.0 \
  --profit-days 7 \
  --target-usd-volume 2.0

# Sell-then-buy strategy for HODLed assets (BTC, ETH)
python3 tools/coin_stats.py \
  --pairs XBTUSDT XETHZUSD \
  --strategy sell-then-buy \
  --suggestbracket 2.0 \
  --suggestoffset 1.0 \
  --target-usd-volume 2.0

# Legacy bracket strategy (buy-then-sell)
python3 tools/coin_stats.py \
  --pairs XXBTZUSD XETHZUSD SOLUSD \
  --hours 48 \
  --csv-output summary.csv \
  --html-output index.html \
  --config-output suggested_config.csv \
  --suggestbracket 2.0 \
  --suggestoffset 1.0 \
  --target-usd-volume 2.0
```

The tool:
- Fetches minute-by-minute OHLC data (up to 2,880 data points per pair)
- Calculates mean, median, standard deviation of prices
- Tests for normal distribution (Shapiro-Wilk test)
- Generates distribution graphs as PNGs
- Exports summary to CSV for spreadsheet analysis
- Creates HTML viewer for easy browser viewing of all graphs
- **NEW: Profit-based config generation** (opt-in with --percentage-profit)
  - Automatically calculates optimal trigger prices and trailing offsets
  - Targets specific profit percentage INCLUDING slippage from trailing offset
  - Ensures >50% probability of success within specified timeframe
  - Reports unsuitable coins with plausible profit alternatives
  - Example: `--percentage-profit 5.0 --profit-days 7` finds pairs that can achieve 5% profit within 7 days
- **NEW: Strategy selection** (--strategy parameter)
  - **buy-then-sell** (default): Buy dip first (enabled), then sell high (linked, activates after buy fills)
    - Best for accumulating assets or trading volatile coins
  - **sell-then-buy**: Sell boom first (enabled), then buy back lower (linked, activates after sell fills)
    - Best for assets you want to hold long-term (BTC, ETH) - take profit on rallies, re-accumulate on dips
- Legacy: Bracket strategy with fixed offsets (default mode)
  - Uses fixed bracket and trailing offsets (--suggestbracket, --suggestoffset)
  - Portfolio-optimized for 95% chance at least one entry triggers
  - Active when --percentage-profit is NOT specified
  - Generates chained orders using linked_order_id feature
- Intelligent volume calculation based on target USD value
  - Converts USD target to coin units with +/- 25% variance
  - Ensures Kraken minimum order requirements (ordermin) are met
  - Customizable via `--target-usd-volume` (default: $1.00)

**Example Output (Profit-Based Mode)**:
```
PROFIT-BASED CONFIG GENERATION
======================================================================
Target profit: 5.0% (after trailing offset slippage)
Profit window: 7 days

✓ BTC/USD: trigger ±6.5%, trailing 1.5%, prob 52.3%
✓ ETH/USD: trigger ±7.2%, trailing 2.0%, prob 51.8%
✗ STABLE/USD: Plausible profit: ~1.2%
    Insufficient volatility: max plausible profit ~1.2%

Config generation complete:
  Pairs included: 25
  Pairs excluded (insufficient volatility): 7
  
✓ Suggested config saved to suggested_config.csv

💡 Suggestion: Run with lower --percentage-profit or higher --profit-days
```

See [COIN_STATS.md](docs/COIN_STATS.md) for detailed documentation.

### Find Profitable Candidates

A tool to analyze volatility and identify profitable bracketing opportunities.

```bash
# Analyze default pairs
uv run python tools/find_profitable_candidates.py

# Custom analysis
uv run python tools/find_profitable_candidates.py \
  --pairs XXBTZUSD XETHZUSD SOLUSD \
  --hours 48 \
  --target-profit 5.0 \
  --top 3

# Interactive mode (dry-run)
uv run python tools/find_profitable_candidates.py \
  --interactive --dry-run
```

The tool:
- Fetches hourly OHLC data (default: 48 hours)
- Calculates volatility metrics and oscillation patterns
- Estimates probability of hitting profit targets
- Ranks candidates by profitability
- Creates bracketing orders (buy low, sell high)

**Example Output**:
```
Pair: BTC/USD has a 30% probability of making a 5% profit in ~24 hours
```

See [FIND_PROFITABLE_CANDIDATES.md](docs/FIND_PROFITABLE_CANDIDATES.md) for detailed documentation.

## Safety and Security

### Fail-Safe Guarantees

TTSLO implements multiple layers of safety to prevent incorrect orders:

1. **Parameter Validation**: Every parameter is explicitly validated before any order
2. **Fail-Safe Defaults**: System defaults to NO ORDER on any uncertainty
3. **Exception Handling**: All exceptions prevent order creation
4. **Pre-Flight Checks**: Configuration must pass validation before operation starts
5. **Simple Code**: All order logic uses clear, step-by-step code for human review

### Order Creation Will Never Happen If:

- Any required parameter is missing or invalid
- Configuration validation fails
- API credentials are unavailable
- Current price cannot be retrieved
- Threshold condition is not met
- Any exception occurs during processing
- Configuration is disabled
- Configuration has already been triggered

### Code Design for Security Review

The codebase has been specifically designed for security review by beginners:

- **No complex Python idioms**: Only simple if-then-else and loops
- **Explicit step-by-step logic**: Each function has numbered steps with comments
- **Safety annotations**: Every check has a "SAFETY:" comment explaining why
- **Comprehensive tests**: All safety features are tested

See [SECURITY.md](docs/SECURITY.md) for complete documentation of safety guarantees.

## Configuration

### Configuration File (config.csv)

The configuration file defines your trigger conditions and TSL order parameters:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier for this configuration (must be unique) |
| `pair` | Kraken trading pair (e.g., `XXBTZUSD` for BTC/USD, `XETHZUSD` for ETH/USD). Use Kraken pair codes (e.g., `XXBTZUSD`, `XETHZUSD`, `SOLUSD`) to avoid formats like `BTC/USD` or `BTCUSD`. |
| `threshold_price` | Price threshold that triggers the TSL order |
| `threshold_type` | Condition type: "above" or "below" |
| `direction` | TSL order direction: "buy" or "sell" |
| `volume` | Amount to trade (in base currency) |
| `trailing_offset_percent` | Trailing stop offset as percentage (e.g., 5.0 for 5%) |
| `enabled` | "true" or "false" - whether this configuration is active |
| `linked_order_id` | (Optional) ID of another order to enable when THIS order fills successfully. Enables chained orders for automated buy-low/sell-high strategies. |

### State File (state.csv)


The state file tracks which triggers have fired. This file is automatically managed by the application:

- `id`: Configuration ID
- `triggered`: Whether the trigger has fired ("true" or "false")
- `trigger_price`: Price at which the trigger fired
- `trigger_time`: Timestamp when trigger fired
- `order_id`: Kraken order ID for the created TSL order
- `activated_on`: **Timestamp (ISO format) when the rule was activated/triggered.** This field is set when a trigger condition is met and provides an audit trail of when the rule became active. It is useful for tracking activation times, debugging, and ensuring that triggers are not duplicated. The value persists in the state file and is reloaded on restart.
- `last_checked`: Last time this configuration was checked

### Log File (logs.csv)

All events are logged to this CSV file with timestamps, log levels, and relevant details.

## Telegram Notifications (Optional)

TTSLO can send real-time Telegram notifications for important events. This feature is completely optional - the system works normally without it.

### Setup

1. **Create a Telegram Bot**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow the prompts
   - Copy the bot token (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Get Your Chat ID**
   - Message [@userinfobot](https://t.me/userinfobot) on Telegram
   - Copy your chat ID (e.g., `123456789`)

3. **Configure Environment**
   - Add to your `.env` file:
     ```
     TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
     ```

4. **Create Notifications Config**
   - Copy `notifications.ini.example` to `notifications.ini`
   - Add your username and chat ID in the `[recipients]` section
   - Configure which events you want to be notified about

### Example Configuration

```ini
[recipients]
alice = 123456789

[notify.config_changed]
users = alice

[notify.validation_error]
users = alice

[notify.trigger_reached]
users = alice

[notify.tsl_created]
users = alice

[notify.tsl_filled]
users = alice
```

### Testing Notifications

Test your notification setup:
```bash
uv run python demo_notifications.py
```

For complete documentation, see [NOTIFICATIONS_README.md](docs/NOTIFICATIONS_README.md).

## API Error Handling

TTSLO includes comprehensive error handling for Kraken API failures:

### Error Types Handled

1. **Timeout Errors** - Request takes too long (default: 30s timeout)
2. **Connection Errors** - Cannot reach Kraken API (network issues, DNS failures)
3. **Server Errors (5xx)** - Kraken API experiencing issues (maintenance, overload)
4. **Rate Limiting (429)** - Too many requests to the API
5. **Other Request Errors** - Malformed requests, SSL errors, etc.

### Error Behavior

When an API error occurs:
- The error is logged with type and details
- A Telegram notification is sent (if configured)
- The operation is safely aborted (no orders created on errors)
- The system continues running and retries on next cycle

### Example Error Scenarios

**Network Outage**: If your internet connection drops, TTSLO will:
- Log connection errors for each failed API call
- **Queue** notifications that fail to send
- **Persist** the queue to disk (`notification_queue.json`)
- All errors are still logged locally in logs.csv
- Continue trying on next monitoring cycle
- **Automatically flush** queued notifications when connection is restored
- **Send recovery notification** with downtime duration and queued message count

**Kraken Maintenance**: If Kraken API returns 503 (Service Unavailable):
- Log server error with status code
- Send notification about Kraken being down (queued if network is also down)
- Skip processing for this cycle
- Automatically resume when service is back

**API Rate Limiting**: If you exceed rate limits:
- Log rate limit error
- Send notification about rate limiting
- System continues (with backoff handled by monitoring interval)

### Configuration

To receive API error notifications, add to your `notifications.ini`:

```ini
[notify.api_error]
users = alice
```

This ensures you're immediately notified of any API issues so you can take action if needed.

### Limitations of Telegram Notifications

**Enhanced with Notification Queue**: TTSLO now includes an intelligent notification queue system that handles network outages gracefully.

**How it works**:

1. **During Network Outage**:
   - Notifications that fail to send are automatically queued
   - Queue is persisted to disk (`notification_queue.json`)
   - Console shows: `📬 Queued notification for alice (X total in queue)`
   - All errors still logged to `logs.csv`

2. **When Network Recovers**:
   - Next successful API call triggers automatic queue flush
   - All queued notifications sent with `[Queued from TIMESTAMP]` prefix
   - Recovery notification sent to all recipients with downtime duration
   - Queue cleared after successful delivery

3. **Persistent Across Restarts**:
   - Queue survives application restarts
   - Notifications will be sent when app restarts and network is available

**Example Recovery Notification**:
```
✅ TTSLO: Telegram notifications restored

Notifications were unavailable for 2 hours 15 minutes
From: 2025-10-23 10:00:00 UTC
To: 2025-10-23 12:15:00 UTC

Sending 5 queued notifications...
```

**What Gets Logged vs Notified**:
- ✅ **Always logged**: All API errors, with full details and timestamps
- 📬 **Queued if unreachable**: Telegram messages queued for later delivery
- ✅ **Eventually delivered**: All queued notifications sent when network restored
- ✅ **Console output**: Error messages printed to stdout/stderr (visible in systemd logs)

**Best Practices**:
1. Always monitor `logs.csv` for complete error history
2. Set up monitoring on the log file itself (e.g., log aggregation tools)
3. Consider running TTSLO on a server with redundant network connections
4. Use `--verbose` mode to see real-time console output

## Command Line Options

```text
--config FILE           Configuration file (default: config.csv)
--state FILE            State file (default: state.csv)
--log FILE              Log file (default: logs.csv)
--dry-run               Don't actually create orders
--verbose               Verbose output
--once                  Run once and exit (default: run continuously)
--interval SECONDS      Seconds between checks in continuous mode (default: 60)
--create-sample-config  Create a sample configuration file and exit
--validate-config       Validate configuration file and exit (shows what will be executed)
--env-file FILE         Path to .env file (default: .env)
```

## Testing

Run the full test suite inside the uv-managed environment to verify Kraken API and TTSLO integrations:

```bash
uv run pytest -q
```

## Kraken API Setup

### Two API Key Pairs

TTSLO uses two separate API key pairs for enhanced security:

1. **Read-Only Keys** (`KRAKEN_API_KEY`, `KRAKEN_API_SECRET`)
   - Used for price monitoring and data retrieval
   - Safe to use during testing and debugging
   - Required permissions: Query Funds, Query Open Orders & Trades

2. **Read-Write Keys** (`KRAKEN_API_KEY_RW`, `KRAKEN_API_SECRET_RW`)
   - Used only for creating orders
   - Optional for dry-run mode
   - Required permissions: Create & Modify Orders

### Creating API Keys

1. Log in to your Kraken account
2. Go to Settings → API
3. Create **two** separate API keys:

**Read-Only Key:**
   - Name: "TTSLO Read-Only"
   - Permissions:
     - Query Funds
     - Query Open Orders & Trades

**Read-Write Key:**
   - Name: "TTSLO Read-Write"
   - Permissions:
     - Create & Modify Orders

**Important**: Never commit your API credentials to version control!

## Common Trading Pairs

- Bitcoin: `XXBTZUSD` (BTC/USD)
- Ethereum: `XETHZUSD` (ETH/USD)
- Solana: `SOLUSD` (SOL/USD)
- Cardano: `ADAUSD` (ADA/USD)

For a complete list, see [Kraken's trading pairs documentation](https://support.kraken.com/hc/en-us/articles/201893658-Currency-pairs-available-for-trading-on-Kraken).

## Example Scenarios

### Scenario 1: Bitcoin Profit Protection
You bought BTC at $45,000 and want to protect profits if it reaches $50,000:

```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_profit,XXBTZUSD,50000,above,sell,0.5,5.0,true
```

When BTC reaches $50,000, a TSL sell order is created with a 5% trailing offset.

### Scenario 2: Ethereum Dip Buying
You want to buy ETH if it drops below $3,000:

```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
eth_dip,XETHZUSD,3000,below,buy,1.0,3.0,true
```

When ETH drops below $3,000, a TSL buy order is created with a 3% trailing offset.

### Scenario 3: Chained Orders (Buy Low, Sell High)
Automatically chain orders to buy low and sell high for profit-taking:

```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled,linked_order_id
btc_buy,XXBTZUSD,100000,below,buy,0.01,2.0,true,btc_sell
btc_sell,XXBTZUSD,120000,above,sell,0.01,2.0,false,
```

**How it works:**
1. `btc_buy` monitors for BTC to drop below $100,000
2. When threshold is met, creates a TSL buy order with 2% trailing offset
3. **When the buy order fills successfully**, the system automatically enables `btc_sell`
4. `btc_sell` then monitors for BTC to rise above $120,000
5. When that threshold is met, creates a TSL sell order
6. Result: Automated buy-low ($100k), sell-high ($120k) strategy = $200 profit per 0.01 BTC

**Key Points:**
- Linked order activates ONLY when parent order fills completely (status='closed')
- Partial fills do NOT activate the linked order
- Canceled orders do NOT activate the linked order
- Can chain multiple orders: A→B→C→D for complex strategies
- Validator detects circular references (A→B→A) and prevents them

## Safety Tips

1. **Always validate your configuration first**: `--validate-config`
2. **Test with dry-run mode**: `--dry-run --verbose --once`
3. **Start with small volumes**: Test with minimal amounts before using real trading volumes
4. **Monitor the logs**: Check `logs.csv` regularly for any issues
5. **Use appropriate trailing offsets**: Too tight may trigger prematurely, too loose may not protect profits
6. **Keep API keys secure**: Use environment variables, never hardcode credentials

## Configuration Validation

TTSLO automatically validates your configuration on startup and will not run if errors are found. Use `--validate-config` to check your configuration without running the application.

### Common Errors Detected

- **Invalid numbers**: "o.5" instead of "0.5", "abc" instead of a number
- **Missing required fields**: Empty or missing id, pair, volume, etc.
- **Invalid values**: threshold_type must be "above" or "below", direction must be "buy" or "sell"
- **Unknown trading pairs**: Pair codes that don't match known Kraken pairs (shown as warning)
- **Duplicate IDs**: Multiple configurations with the same id
- **Negative values**: Negative prices, volumes, or offsets
- **Threshold already met**: Trigger price already reached by current market price
- **Insufficient gap**: Gap between threshold and current price is less than trailing offset

### Market Price Validation

When API credentials are available, the validator checks configurations against current market prices:

- **Threshold Already Met**: Error if "above" threshold is below current price, or "below" threshold is above current price
  - Example: Setting threshold "above $50,000" when BTC is already at $115,000
- **Insufficient Gap**: Error if the gap between threshold and current price is less than the trailing offset
  - Example: Current price $100, threshold $103, but 5% trailing offset needs at least $5 gap
- **Small Gap Warning**: Warning if gap is less than 2x the trailing offset
  - Provides recommendation for optimal gap size

To enable market price validation with `--validate-config`, set your read-only API credentials:
```bash
export KRAKEN_API_KEY="your_readonly_key"
export KRAKEN_API_SECRET="your_readonly_secret"
uv run ttslo.py --validate-config
```

### Warnings

The validator also provides warnings for potentially problematic configurations:

- **Unusual logic**: Buying when price goes up, selling when price goes down
- **Extreme offsets**: Very small (<0.1%) or very large (>50%) trailing offsets
- **Unknown pairs**: Trading pairs not in the known list (may still be valid)
- **Very small/large values**: Unusually small volumes or extreme prices
- **Small gaps**: Gap between threshold and current price less than 2x trailing offset

### Example Validation Output

```bash
$ uv run ttslo.py --validate-config

================================================================================
CONFIGURATION VALIDATION REPORT
================================================================================

✓ VALIDATION PASSED

Configurations checked: 2
Errors found: 0
Warnings found: 0

================================================================================
CONFIGURATION SUMMARY
================================================================================

[btc_profit] ✓ ACTIVE
  Pair: XXBTZUSD
  Trigger: When price goes above 50000
  Action: Create SELL trailing stop loss
  Volume: 0.1
  Trailing offset: 5.0%

[eth_dip] ✓ ACTIVE
  Pair: XETHZUSD
  Trigger: When price goes below 3000
  Action: Create BUY trailing stop loss
  Volume: 1.0
  Trailing offset: 3.5%

================================================================================
✓ Configuration is ready to use!
================================================================================
```

## Troubleshooting

### "Configuration validation failed" error
Run `uv run ttslo.py --validate-config` to see detailed error messages. Fix all errors in your config.csv file before running.

### "API credentials required" error
Make sure you've set `KRAKEN_API_KEY` and `KRAKEN_API_SECRET` environment variables.

### "No configurations found" warning
Your `config.csv` file is empty or missing. Run `--create-sample-config` to generate a template.

### Order creation fails
- Check that your API key has the correct permissions
- Verify you have sufficient balance
- Ensure the trading pair is correct (use `--validate-config` to check)
- Check Kraken's API status

## Utilities

### Extract Open Orders

A utility to extract open trailing-stop orders from Kraken and output them in config.csv format for easy comparison:

```bash
# Output to stdout
uv run python extract_open_orders.py

# Save to file
uv run python extract_open_orders.py --output-file open_orders.csv

# Compare with your config
uv run python extract_open_orders.py > open_orders.csv
diff config.csv open_orders.csv
```

This is useful when config.csv or state.csv may be out of sync with actual open orders on Kraken. See [EXTRACT_ORDERS_README.md](docs/EXTRACT_ORDERS_README.md) for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is provided as-is for educational and personal use. Use at your own risk. Trading cryptocurrencies involves substantial risk of loss.

## Disclaimer

This tool is not financial advice. Always do your own research and understand the risks involved in cryptocurrency trading. The authors are not responsible for any losses incurred while using this tool.
