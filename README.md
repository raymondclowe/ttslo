# TTSLO - Triggered Trailing Stop Loss Orders

A Python tool for Kraken.com that monitors cryptocurrency prices and automatically creates Trailing Stop Loss (TSL) orders when specified price thresholds are met.

## Overview

The Kraken.com exchange allows for Trailing Stop Loss (TSL) orders, but you can only create them at the current market price with a percentage offset. This tool solves that limitation by:

- Monitoring cryptocurrency prices continuously
- Creating TSL orders automatically when your specified price thresholds are reached
- Providing flexible configuration through CSV files
- Supporting dry-run mode for testing
- Maintaining state and comprehensive logging

## Features

- **Price Threshold Triggers**: Set price levels (above/below) that trigger TSL order creation
- **CSV-based Configuration**: Simple CSV files for configuration, state, and logs
- **Dry-Run Mode**: Test your configurations without creating real orders
- **Verbose Debug Mode**: Detailed logging for troubleshooting
- **Continuous Monitoring**: Runs continuously and checks prices at regular intervals
- **State Persistence**: Tracks which triggers have fired to avoid duplicates
- **Flexible Configuration**: Support for multiple trading pairs and strategies

## Installation

1. Clone this repository:
```bash
git clone https://github.com/raymondclowe/ttslo.git
cd ttslo
```

2. Install dependencies:
```bash
pip install -r requirements.txt
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
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_1,XXBTZUSD,50000,above,sell,0.01,5.0,true
eth_1,XETHZUSD,3000,above,sell,0.1,3.5,true
```

3. Test your configuration in dry-run mode:
```bash
python ttslo.py --dry-run --verbose --once
```

4. Run continuously:
```bash
python ttslo.py --interval 60
```

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

1. **Always test with dry-run mode first**: `--dry-run --verbose --once`
2. **Start with small volumes**: Test with minimal amounts before using real trading volumes
3. **Monitor the logs**: Check `logs.csv` regularly for any issues
4. **Use appropriate trailing offsets**: Too tight may trigger prematurely, too loose may not protect profits
5. **Keep API keys secure**: Use environment variables, never hardcode credentials

## Troubleshooting

### "API credentials required" error
Make sure you've set `KRAKEN_API_KEY` and `KRAKEN_API_SECRET` environment variables, or use `--api-key` and `--api-secret` options.

### "No configurations found" warning
Your `config.csv` file is empty or missing. Run `--create-sample-config` to generate a template.

### Order creation fails
- Check that your API key has the correct permissions
- Verify you have sufficient balance
- Ensure the trading pair is correct
- Check Kraken's API status

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is provided as-is for educational and personal use. Use at your own risk. Trading cryptocurrencies involves substantial risk of loss.

## Disclaimer

This tool is not financial advice. Always do your own research and understand the risks involved in cryptocurrency trading. The authors are not responsible for any losses incurred while using this tool.
