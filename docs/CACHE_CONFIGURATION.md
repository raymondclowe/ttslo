# Dashboard Caching Configuration

The TTSLO Dashboard uses a hybrid caching system (memory + disk) to improve performance and provide instant dashboard loads after restarts.

## Cache Architecture

### Two-Tier Caching
1. **Memory Cache** (L1): Fast in-memory cache with TTL-based expiration
   - Used for frequently accessed data within the same session
   - Expires after `DASHBOARD_REFRESH_INTERVAL` seconds (default: 30s)
   - Lost on service restart

2. **Disk Cache** (L2): Persistent JSON-based cache on disk
   - Used when memory cache expires or on first load after restart
   - Stored in `.cache/` directory (configurable)
   - Survives service restarts
   - Same TTL as memory cache

### Cache Fallback Chain
1. Check memory cache → if valid, return immediately
2. Check disk cache → if valid, populate memory cache and return
3. Call API/load file → populate both caches and return

## Configuration

### Environment Variables

#### `TTSLO_CACHE_DIR`
Directory to store disk cache files.

**Default:** `.cache`

**Example:**
```bash
export TTSLO_CACHE_DIR="/var/cache/ttslo"
```

#### `TTSLO_CHECK_INTERVAL`
Main monitor check interval in seconds. Dashboard refresh interval is calculated as `max(5, CHECK_INTERVAL // 2)`.

**Default:** `60`

**Example:**
```bash
export TTSLO_CHECK_INTERVAL=120  # Dashboard refreshes every 60s
```

## Cached Data

### Kraken API Responses
- **open_orders**: Open orders from Kraken
- **closed_orders**: Closed orders from Kraken
- **current_prices**: Current prices for all trading pairs

### Local Files
- **config**: Config CSV data
- **state**: State CSV data

### Computed Data
- **pending_orders**: Calculated pending orders (not yet triggered)
- **active_orders**: Calculated active orders (triggered, on Kraken)
- **completed_orders**: Calculated completed orders (executed)
- **balances_and_risks**: Balance and risk analysis

## Cache Management

### Monitoring Cache

Check cache statistics via the API endpoint:

```bash
curl http://localhost:5000/api/cache-stats
```

Response:
```json
{
  "cache_dir": ".cache",
  "entry_count": 9,
  "total_size_bytes": 45678,
  "total_size_mb": 0.044,
  "dashboard_refresh_interval": 30,
  "cache_enabled": true
}
```

### Clearing Cache

To clear the disk cache:

```bash
rm -rf .cache/*.json
```

Or programmatically via Python:

```python
from disk_cache import DiskCache

cache = DiskCache()
cache.clear()
```

### Cache Files

Cache files are stored as JSON in the cache directory:

```
.cache/
  ├── open_orders.json
  ├── closed_orders.json
  ├── config.json
  ├── state.json
  ├── current_prices.json
  ├── pending_orders.json
  ├── active_orders.json
  ├── completed_orders.json
  └── balances_and_risks.json
```

Each file contains:
```json
{
  "timestamp": "2025-10-26T12:34:56.789",
  "value": { ... }
}
```

## Performance Benefits

### Before (In-Memory Only)
- First load after restart: **60-120 seconds** (multiple API calls)
- Subsequent loads: **0.1-0.5 seconds** (cache hits)
- Service restart: Cache lost, **60-120 seconds** to warm up

### After (Hybrid Memory + Disk)
- First load after restart: **< 1 second** (disk cache)
- Subsequent loads: **< 0.01 seconds** (memory cache)
- Service restart: **< 1 second** (disk cache survives)

### Rate Limit Impact
- Reduced API calls by ~90% during normal operation
- Eliminates cold-start API burst after restarts
- More headroom for manual API usage

## Troubleshooting

### Dashboard Shows Stale Data

Check cache TTL:
```bash
# Check current refresh interval
curl http://localhost:5000/api/status | jq '.refresh_interval'

# Adjust if needed
export TTSLO_CHECK_INTERVAL=30  # Shorter = fresher data
```

Clear cache to force refresh:
```bash
rm -rf .cache/*.json
```

### Cache Directory Permissions

Ensure the dashboard process has write permissions:

```bash
# Create cache directory with correct permissions
mkdir -p .cache
chmod 755 .cache

# If running as systemd service
chown ttslo:ttslo .cache
```

### Cache Size Growing

Monitor cache size:
```bash
du -sh .cache
```

The cache auto-expires old entries. Each entry is small (typically < 100KB). Normal size: 1-5MB.

To limit cache size, reduce `TTSLO_CHECK_INTERVAL`:
```bash
export TTSLO_CHECK_INTERVAL=30  # Shorter TTL = smaller cache
```

## Development Notes

### Adding New Cached Functions

To add disk caching to a new function:

```python
from dashboard import ttl_cache, DASHBOARD_REFRESH_INTERVAL

@ttl_cache(seconds=DASHBOARD_REFRESH_INTERVAL, disk_key='my_new_cache')
def get_my_data():
    """Get data with hybrid caching."""
    # ... expensive operation ...
    return data
```

### Custom TTL

For data that changes infrequently, use longer TTL:

```python
@ttl_cache(seconds=300, disk_key='slow_changing_data')  # 5 minutes
def get_slow_data():
    return data
```

### Disable Disk Cache

To disable disk caching for a specific function, omit `disk_key`:

```python
@ttl_cache(seconds=30)  # Memory cache only
def get_volatile_data():
    return data
```

## Security Considerations

### Cache Directory Location

**Default:** `.cache` (relative to working directory)

For production deployments, use absolute path:

```bash
export TTSLO_CACHE_DIR="/var/cache/ttslo"
```

### Cache File Permissions

Cache files contain API response data. Set appropriate permissions:

```bash
chmod 600 .cache/*.json  # Read/write for owner only
```

### Sensitive Data

Cache files may contain:
- Order IDs
- Trading pairs
- Volumes
- Prices
- Account balances

**Do NOT:**
- Commit `.cache/` to git (already in `.gitignore`)
- Share cache files publicly
- Store cache on shared filesystems without encryption

## References

- [disk_cache.py](../disk_cache.py) - Core cache module
- [dashboard.py](../dashboard.py) - Dashboard with hybrid caching
- [LEARNINGS.md](../LEARNINGS.md#dashboard-disk-cache-for-performance-2025-10-26) - Implementation notes
