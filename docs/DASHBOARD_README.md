# TTSLO Dashboard Guide

The TTSLO Dashboard provides a clean, professional web interface for monitoring your triggered trailing stop loss orders in real-time.

## Quick Start

```bash
# Start the dashboard
uv run python dashboard.py

# Open your browser to:
http://localhost:5000
```

## Dashboard Overview

The dashboard displays three main sections:

### 1. Pending Orders

Shows orders from `config.csv` that haven't triggered yet.

**Features:**
- Current price vs. threshold price
- Visual progress bar showing distance to trigger
- Percentage and dollar distance calculations
- "READY TO TRIGGER" alert when threshold is met

**Example:**
```
btc_sell_high          XXBTZUSD
Threshold: $120000.00 (above)   Current: $108824.00
Direction: sell                  Volume: 0.01

[===========          ] 10.27%
$11176.00 below threshold
```

### 2. Active TSL Orders

Shows orders that have triggered and are currently active on Kraken.

**Features:**
- Order ID from Kraken
- Trigger price and time
- Current order status
- Volume and execution details

**Data Source:** Pulled from Kraken API using `query_open_orders()`

### 3. Completed Orders

Shows orders that have executed on Kraken.

**Features:**
- Comparison of trigger price vs. execution price
- Benefit calculation (how much better the TSL order performed)
- Color-coded profit/loss indicators
- Execution timestamps

**Benefit Calculation:**
- For **sell** orders: `benefit = executed_price - trigger_price`
  - Positive = sold higher than trigger (good!)
  - Example: Triggered at $105,000, executed at $108,000 = +$3,000 benefit
- For **buy** orders: `benefit = trigger_price - executed_price`
  - Positive = bought lower than trigger (good!)
  - Example: Triggered at $80,000, executed at $78,000 = +$2,000 benefit

## Auto-Refresh

The dashboard automatically refreshes every 30 seconds. You can also manually refresh using the "Refresh Data" button.

## API Endpoints

The dashboard provides REST API endpoints for integration:

```bash
# System status
curl http://localhost:5000/api/status

# Pending orders (JSON)
curl http://localhost:5000/api/pending

# Active orders (JSON)
curl http://localhost:5000/api/active

# Completed orders (JSON)
curl http://localhost:5000/api/completed
```

## Configuration

### Environment Variables

```bash
export TTSLO_CONFIG_FILE=config.csv    # Config file path
export TTSLO_STATE_FILE=state.csv      # State file path
export TTSLO_LOG_FILE=logs.csv         # Log file path
```

### Command Line Options

```bash
# Custom host and port
uv run python dashboard.py --host 0.0.0.0 --port 8080

# Enable debug mode (more verbose logging)
uv run python dashboard.py --debug
```

## How It Works

1. **Reads Local Files:** Dashboard reads `config.csv` and `state.csv` from the same directory as the running ttslo instance
2. **Gets Live Prices:** Uses Kraken API (WebSocket or REST) to get current prices
3. **Calculates Distance:** Compares current price to threshold to show how close to triggering
4. **Monitors Active Orders:** Queries Kraken for status of triggered orders
5. **Shows Completed Orders:** Fetches closed orders from Kraken and calculates benefit

## Example Workflow

1. **Setup your config.csv:**
   ```csv
   id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
   btc_sell,XXBTZUSD,100000,above,sell,0.01,5.0,true
   ```

2. **Start ttslo (in one terminal):**
   ```bash
   uv run ttslo.py
   ```

3. **Start dashboard (in another terminal):**
   ```bash
   uv run python dashboard.py
   ```

4. **Monitor in browser:**
   - Watch pending orders approach their trigger thresholds
   - See orders move to "Active" when triggered
   - Review completed orders and their benefits

## Troubleshooting

### "Kraken API: Unavailable"

**Problem:** Dashboard shows Kraken API is unavailable.

**Solutions:**
1. Check that your `.env` file has valid Kraken API credentials:
   ```
   KRAKEN_API_KEY=your_readonly_key
   KRAKEN_API_SECRET=your_readonly_secret
   ```
2. Verify credentials work:
   ```bash
   uv run python -c "from kraken_api import KrakenAPI; api = KrakenAPI.from_env(); print(api.get_current_price('XXBTZUSD'))"
   ```

**Note:** Dashboard will still show pending orders without Kraken API, but won't show current prices or active/completed orders.

### "Config or state files missing"

**Problem:** Dashboard shows config/state files missing.

**Solutions:**
1. Make sure `config.csv` and `state.csv` exist in the same directory
2. Create sample config: `uv run ttslo.py --create-sample-config`
3. Initialize state file manually or by running ttslo once

### No Data Showing

**Problem:** Dashboard loads but shows no orders.

**Solutions:**
1. Check that `config.csv` has enabled orders (`enabled=true`)
2. Verify `state.csv` exists and has matching IDs
3. Check browser console for errors (F12)
4. Try manually refreshing with the "Refresh Data" button

## Security Notes

- Dashboard runs in **read-only mode** - it never modifies config or state files
- Only requires **read-only Kraken API credentials**
- Designed for **local use** (localhost by default)
- Should not be exposed to the internet without additional security measures (authentication, HTTPS, etc.)

## Technical Details

- **Framework:** Flask (Python web framework)
- **Frontend:** Vanilla JavaScript (no external libraries)
- **Styling:** Pure CSS (no frameworks)
- **API:** RESTful JSON endpoints
- **Updates:** Client-side polling every 30 seconds

## Contributing

To modify the dashboard:

1. **Backend:** Edit `dashboard.py` for API endpoints and data processing
2. **Frontend:** Edit `templates/dashboard.html` for UI changes
3. **Tests:** Add tests to `tests/test_dashboard.py`
4. **Run tests:** `uv run pytest tests/test_dashboard.py -v`

## Design Principles

- **Executive Style:** Clean, professional appearance
- **Actionable Information:** Focus on what matters
- **Minimal Distractions:** No unnecessary decorations
- **Professional Palette:** Blue and gray tones only
- **No Purple, No Gradients:** As requested in requirements ✅
