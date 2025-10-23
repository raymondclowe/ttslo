# TTSLO Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
uv sync
```

**Note:** [uv](https://github.com/astral-sh/uv) is a fast Python package manager. If you don't have uv installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

### 2. Get Kraken API Credentials
1. Log in to [Kraken](https://www.kraken.com)
2. Go to Settings → API
3. Create **two** API keys:

**Read-Only Key** (for price monitoring):
   - Name: "TTSLO Read-Only"
   - Permissions: Query Funds, Query Open Orders & Trades

**Read-Write Key** (for creating orders):
   - Name: "TTSLO Read-Write"
   - Permissions: Create & Modify Orders

4. Save both API Keys and Private Keys

### 3. Set Environment Variables

**Option A: Environment Variables**
```bash
export KRAKEN_API_KEY="your_readonly_api_key"
export KRAKEN_API_SECRET="your_readonly_api_secret"
export KRAKEN_API_KEY_RW="your_readwrite_api_key"
export KRAKEN_API_SECRET_RW="your_readwrite_api_secret"
```

**Option B: Create .env file**
```bash
cat > .env << EOF
KRAKEN_API_KEY=your_readonly_api_key
KRAKEN_API_SECRET=your_readonly_api_secret
KRAKEN_API_KEY_RW=your_readwrite_api_key
KRAKEN_API_SECRET_RW=your_readwrite_api_secret
EOF
```

### 4. Create Configuration
```bash
# Generate sample configuration
uv run ttslo.py --create-sample-config

# Copy and edit
cp config_sample.csv config.csv
nano config.csv  # or your favorite editor
```

### 5. Validate Configuration
```bash
uv run ttslo.py --validate-config
```
This shows errors, warnings, and what will be executed. Fix any errors before proceeding.

### 6. Test in Dry-Run Mode
```bash
uv run ttslo.py --dry-run --verbose --once
```

### 7. Run for Real
```bash
# Run continuously (checks every 60 seconds)
uv run ttslo.py

# Run with custom interval
uv run ttslo.py --interval 120
```

## Common Configurations

### Protect BTC Profits Above $50k
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_profit,XBTUSDT,50000,above,sell,0.1,5.0,true
```
**What it does:** When BTC reaches $50,000, creates a sell TSL order for 0.1 BTC with 5% trailing offset.

### Buy ETH Dip Below $2500
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
eth_dip,ETHUSDT,2500,below,buy,1.0,3.0,true
```
**What it does:** When ETH drops below $2,500, creates a buy TSL order for 1.0 ETH with 3% trailing offset.

### Multiple Strategies
```csv
id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled
btc_high,XBTUSDT,60000,above,sell,0.05,5.0,true
btc_low,XBTUSDT,40000,below,buy,0.05,4.0,true
eth_high,ETHUSDT,3500,above,sell,0.5,4.5,true
sol_breakout,SOLUSD,150,above,sell,10,6.0,true
```

## Monitoring

### Check Logs
```bash
# View recent logs
tail -f logs.csv

# Search for errors
grep ERROR logs.csv

# Check specific config
grep "btc_profit" logs.csv
```

### Check State
```bash
# View current state
cat state.csv

# Check if triggers fired
grep "true" state.csv
```

## Tips & Tricks

### Test Without Risk
Always use `--dry-run --verbose --once` first to test your configuration.

### Start Small
Begin with small volumes to test the system before committing larger amounts.

### Multiple Strategies
You can have many rows in config.csv for different pairs and conditions.

### Disable Temporarily
Set `enabled` to `false` to temporarily disable a configuration without deleting it.

### Reset State
If you want to re-enable a triggered configuration:
```bash
# Edit state.csv and change triggered from "true" to "false"
nano state.csv
```

### Run as Background Service
```bash
# Using nohup
nohup uv run ttslo.py > ttslo.out 2>&1 &

# Using screen
screen -S ttslo
uv run ttslo.py
# Ctrl+A, D to detach

# Using systemd (Linux)
# Create /etc/systemd/system/ttslo.service
```

## Troubleshooting

### "API credentials required"
Set `KRAKEN_API_KEY` and `KRAKEN_API_SECRET` environment variables.

### "No configurations found"
Your `config.csv` is missing or empty. Run `--create-sample-config`.

### Order creation fails
- Verify API key permissions
- Check account balance
- Confirm trading pair format (XBTUSDT, not BTC/USDT)

### Wrong price detected
- Kraken may use different pair names
- Check exact pair name in Kraken API docs
- Verify threshold_type is "above" or "below"

## Safety Checklist

- [ ] Tested with `--dry-run` first
- [ ] Started with small volumes
- [ ] API key has only required permissions
- [ ] API credentials stored securely (not in code)
- [ ] Monitoring logs.csv regularly
- [ ] Understand trailing stop loss mechanics
- [ ] Have backup plan if system goes down

## Advanced Usage

### Custom File Locations
```bash
uv run ttslo.py \
  --config /path/to/my_config.csv \
  --state /path/to/my_state.csv \
  --log /path/to/my_logs.csv
```

### One-Time Check
```bash
# Run once and exit (useful for cron jobs)
uv run ttslo.py --once
```

### Verbose Debugging
```bash
# See all debug messages
uv run ttslo.py --verbose
```

## Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review [Kraken API documentation](https://docs.kraken.com/rest/)
- Check logs.csv for detailed error messages
- Review state.csv to see what has triggered

---

**Remember:** Trading involves risk. Always understand what you're doing and never invest more than you can afford to lose.
