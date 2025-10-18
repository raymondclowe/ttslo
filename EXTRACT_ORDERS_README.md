# Extract Open Orders Utility

A command-line utility to extract open trailing-stop orders from Kraken API and output them in the same CSV format as `config.csv`.

## Purpose

Sometimes the config.csv and state.csv files may get out of sync with the actual open orders on Kraken. This utility allows you to:

- Query all open orders from Kraken API
- Filter to show only trailing-stop orders
- Output them in the same format as config.csv
- Easily compare with your local config.csv to find duplicates or missing orders

## Usage

### Basic Usage

Output to stdout:
```bash
python extract_open_orders.py
```

Or using uv:
```bash
uv run python extract_open_orders.py
```

### Save to File

```bash
python extract_open_orders.py --output-file open_orders.csv
```

Or:
```bash
python extract_open_orders.py > open_orders.csv
```

### Compare with config.csv

```bash
# Extract open orders
python extract_open_orders.py > open_orders.csv

# Compare with config
diff config.csv open_orders.csv

# Or use a visual diff tool
code --diff config.csv open_orders.csv
```

## Output Format

The output CSV has the same format as `config.csv`:

```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
```

### Field Mapping

| Field | Source | Notes |
|-------|--------|-------|
| id | Kraken order ID | The transaction ID from Kraken |
| pair | Order pair | e.g., XXBTZUSD |
| threshold_price | Not available | **Left blank** - trigger conditions aren't stored in open orders |
| threshold_type | Not available | **Left blank** - trigger conditions aren't stored in open orders |
| direction | Order type | 'buy' or 'sell' |
| volume | Order volume | Amount to trade |
| trailing_offset_percent | Order price | Extracted from trailing stop percentage (e.g., "+5.0000%" → "5.0000") |
| enabled | Always "false" | If it's open, it has already been triggered |

### Why Some Fields Are Blank

The `threshold_price` and `threshold_type` fields are not available in open orders because they represent the **trigger conditions** that caused the order to be created in the first place. Once an order is open on Kraken, only the order itself (trailing-stop details) is tracked, not the original trigger.

This is expected and normal - these fields would only be relevant when using TTSLO to create the orders based on price triggers.

## Requirements

- Python 3.7+
- Kraken API credentials (read-only or read-write)
- Same dependencies as main ttslo.py

## API Credentials

The utility uses the same credential discovery as the main ttslo application:

1. Environment variables: `KRAKEN_API_KEY` and `KRAKEN_API_SECRET`
2. Or read-write: `KRAKEN_API_KEY_RW` and `KRAKEN_API_SECRET_RW`
3. From `.env` file
4. Copilot-prefixed variants (for GitHub Copilot environments)

## Examples

### Example 1: Check for duplicates

```bash
# Extract open orders
python extract_open_orders.py > open_orders.csv

# Compare IDs - any matches might be duplicates
# (though config IDs are different from Kraken order IDs)
```

### Example 2: Find missing orders

If you have orders in config.csv that should have been created but aren't showing up in Kraken:

```bash
# Get your config
cat config.csv

# Get what's actually open on Kraken
python extract_open_orders.py

# Manually compare to see what's missing
```

### Example 3: Audit trailing-stop orders

```bash
# See all your open trailing-stop orders
python extract_open_orders.py

# Output:
# id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
# OZAFUQ-6FB7W-GR63OS,XXBTZUSDT,,,buy,0.00006000,15.0000,false
# ORWBHN-LMPRM-TG4RWJ,XXBTZUSDT,,,sell,0.00005000,10.0000,false
```

## Demo

Run the demo to see it in action with mock data:

```bash
python demo_extract_open_orders.py
```

This shows how the utility works without requiring actual Kraken API credentials.

## Testing

Run the tests:

```bash
pytest test_extract_open_orders.py -v
```

Or with uv:

```bash
uv run pytest test_extract_open_orders.py -v
```

## Related Files

- `extract_open_orders.py` - Main utility script
- `test_extract_open_orders.py` - Test suite
- `demo_extract_open_orders.py` - Demo with mock data
- `config.csv` - Your local configuration
- `state.csv` - Tracking state of triggered orders

## Troubleshooting

### "Error: Could not initialize Kraken API"

Make sure your API credentials are set:

```bash
export KRAKEN_API_KEY="your_key"
export KRAKEN_API_SECRET="your_secret"
```

Or create a `.env` file with these values.

### "No open trailing-stop orders found"

This is normal if:
- You don't have any trailing-stop orders currently open on Kraken
- All your orders are different types (limit, market, etc.)

### Different order IDs

The `id` field in the output is the Kraken transaction ID (e.g., "OZAFUQ-6FB7W-GR63OS"), which is different from the custom IDs you use in config.csv (e.g., "btc_1"). This is expected - you'll need to match orders based on pair, direction, volume, and trailing_offset_percent instead.
