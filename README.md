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

- **Fail-Safe Order Logic**: Never creates incorrect orders under any circumstances
- **Price Threshold Triggers**: Set price levels (above/below) that trigger TSL order creation
- **CSV-based Configuration**: Simple CSV files for configuration, state, and logs
- **Interactive CSV Editor**: Built-in TUI for editing configuration files with keyboard navigation
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
python ttslo.py --create-sample-config
```

2. Edit `config_sample.csv` and save it as `config.csv`:

**Option A: Using the CSV Editor TUI**
```bash
python csv_editor.py config_sample.csv
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
python ttslo.py --validate-config
```

4. Test your configuration in dry-run mode:
```bash
python ttslo.py --dry-run --verbose --once
```

5. Run continuously:
```bash
python ttslo.py --interval 60
```

## CSV Editor

TTSLO includes an interactive TUI (Text User Interface) for editing configuration files. The CSV editor provides a user-friendly way to view and modify your configuration without manually editing CSV files.

### Usage

```bash
# Edit the main config file
python csv_editor.py config.csv

# Edit the sample config
python csv_editor.py config_sample.csv

# Edit any CSV file
python csv_editor.py yourfile.csv
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

- Interactive table view with color-coded rows
- Modal dialog for editing cell values
- Add and delete rows
- Visual notifications for all operations
- Keyboard-driven workflow

For detailed documentation, see [CSV_EDITOR_README.md](CSV_EDITOR_README.md).

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
| `id` | Unique identifier for this configuration |
| `pair` | Kraken trading pair (e.g., XXBTZUSD for BTC/USD, XETHZUSD for ETH/USD) |
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
- `last_checked`: Last time this configuration was checked

### Log File (logs.csv)

All events are logged to this CSV file with timestamps, log levels, and relevant details.

## Usage Examples

### Validate Configuration File
```bash
python ttslo.py --validate-config
```
This validates your configuration and shows:
- All errors that must be fixed
- Warnings about unusual settings
- A human-readable summary of what will be executed

### Run Once (Single Check)
```bash
python ttslo.py --once --verbose
```

### Run Continuously with Custom Interval
```bash
python ttslo.py --interval 120  # Check every 2 minutes
```

### Dry-Run Mode (No Real Orders)
```bash
python ttslo.py --dry-run --verbose
```

### Custom File Locations
```bash
python ttslo.py --config my_config.csv --state my_state.csv --log my_logs.csv
```

### Custom .env File Location
```bash
python ttslo.py --env-file /path/to/custom.env
```

## Command-Line Options

```
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
python ttslo.py --validate-config
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
$ python ttslo.py --validate-config

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
Run `python ttslo.py --validate-config` to see detailed error messages. Fix all errors in your config.csv file before running.

### "API credentials required" error
Make sure you've set `KRAKEN_API_KEY` and `KRAKEN_API_SECRET` environment variables.

### "No configurations found" warning
Your `config.csv` file is empty or missing. Run `--create-sample-config` to generate a template.

### Order creation fails
- Check that your API key has the correct permissions
- Verify you have sufficient balance
- Ensure the trading pair is correct (use `--validate-config` to check)
- Check Kraken's API status

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is provided as-is for educational and personal use. Use at your own risk. Trading cryptocurrencies involves substantial risk of loss.

## Disclaimer

This tool is not financial advice. Always do your own research and understand the risks involved in cryptocurrency trading. The authors are not responsible for any losses incurred while using this tool.
