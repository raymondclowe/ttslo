# TTSLO - Triggered Trailing Stop Loss Orders

A Python tool for Kraken.com that monitors cryptocurrency prices and automatically creates Trailing Stop Loss (TSL) orders when specified price thresholds are met.

## ⚠️ Security Notice

TTSLO is designed with **fail-safe** order handling. The system will **NEVER** create an order if anything is uncertain or abnormal. See [SECURITY.md](SECURITY.md) for complete safety guarantees and security documentation.

## Overview

The Kraken.com exchange allows for Trailing Stop Loss (TSL) orders, but you can only create them at the current market price with a percentage offset. This tool solves that limitation by:

- Monitoring cryptocurrency prices continuously
- Creating TSL orders automatically when your specified price thresholds are reached
- Providing flexible configuration through CSV files
- Supporting dry-run mode for testing
- Maintaining state and comprehensive logging

## Features

- **Real-Time WebSocket Price Monitoring**: Get instant price updates via Kraken's WebSocket API (90,000x faster than REST!)
- **Fail-Safe Order Logic**: Never creates incorrect orders under any circumstances
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

**Note:** The tool checks for both standard names (e.g., `KRAKEN_API_KEY`) and Copilot-prefixed names (e.g., `copilot_KRAKEN_API_KEY`) to support GitHub Copilot agent environments.

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

WebSocket is enabled by default - no configuration needed! For more details, see [WEBSOCKET_INTEGRATION.md](WEBSOCKET_INTEGRATION.md).

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
- `Ctrl+Q`: Quit the application
- `Ctrl+N`: Add a new row
- `Ctrl+D`: Delete the current row
- `Enter`: Edit the selected cell
- `Arrow Keys`: Navigate the table
- `Tab/Shift+Tab`: Navigate between cells

### Features

- **Smart file detection**: Automatically finds the service's config
- **File locking**: Prevents conflicts with the running service
- Interactive table view with color-coded rows
- Modal dialog for editing cell values with validation
- Cell-level validation for configuration fields:
  - `threshold_type`: must be "above" or "below"
  - `direction`: must be "buy" or "sell"
  - `enabled`: must be true/false, yes/no, or 1/0
  - `pair`: validates against known Kraken pairs
  - `id`: prevents duplicate IDs
- Add and delete rows
- Visual notifications for all operations
- Keyboard-driven workflow
For detailed documentation, see [CSV_EDITOR_README.md](CSV_EDITOR_README.md).

## Web Dashboard

TTSLO includes a Flask-based web dashboard for monitoring your orders in real-time. The dashboard provides a clean, executive-style interface with three main views:

### Features

- **Pending Orders**: View orders that haven't triggered yet, with visual progress bars showing how close they are to triggering
- **Active TSL Orders**: Monitor orders that have triggered and are currently active on Kraken
- **Completed Orders**: Review executed orders with benefit calculations comparing trigger price vs execution price
- **Real-Time Data**: Auto-refreshes every 30 seconds with live price updates from Kraken
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

### API Endpoints

The dashboard exposes REST API endpoints for integration:
- `GET /api/status` - System status and configuration
- `GET /api/pending` - List of pending orders
- `GET /api/active` - List of active TSL orders
- `GET /api/completed` - List of completed orders

### Security Note

The dashboard runs in read-only mode by default and only requires read-only Kraken API credentials. It's designed for local use and should not be exposed to the internet without additional security measures.

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

See [SECURITY.md](SECURITY.md) for complete documentation of safety guarantees.

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

For complete documentation, see [NOTIFICATIONS_README.md](NOTIFICATIONS_README.md).

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

This is useful when config.csv or state.csv may be out of sync with actual open orders on Kraken. See [EXTRACT_ORDERS_README.md](EXTRACT_ORDERS_README.md) for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is provided as-is for educational and personal use. Use at your own risk. Trading cryptocurrencies involves substantial risk of loss.

## Disclaimer

This tool is not financial advice. Always do your own research and understand the risks involved in cryptocurrency trading. The authors are not responsible for any losses incurred while using this tool.
