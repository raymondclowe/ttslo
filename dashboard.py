#!/usr/local/bin/uv run
"""
TTSLO Dashboard - Web-based monitoring for triggered trailing stop loss orders.

Provides a clean, executive-style dashboard for monitoring:
- Pending orders (not yet triggered)
- Active TSL orders (triggered, waiting to execute)
- Completed orders (executed with price comparison)
"""

import os
import sys
import signal
import time
import json
import zipfile
import io
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, jsonify, send_file
from config import ConfigManager
from kraken_api import KrakenAPI
from creds import load_env
from notifications import NotificationManager

app = Flask(__name__)

# Configuration
CONFIG_FILE = os.getenv('TTSLO_CONFIG_FILE', 'config.csv')
STATE_FILE = os.getenv('TTSLO_STATE_FILE', 'state.csv')
LOG_FILE = os.getenv('TTSLO_LOG_FILE', 'logs.csv')

# TTL cache decorator using native Python functools
def ttl_cache(seconds=5):
    """
    Simple TTL (Time To Live) cache decorator using native Python.
    Cache expires after the specified number of seconds.
    
    Args:
        seconds: Cache TTL in seconds (default: 5)
    """
    def decorator(func):
        cache = {'result': None, 'timestamp': 0}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            cache_age = current_time - cache['timestamp']
            
            # Return cached result if still valid
            if cache['result'] is not None and cache_age < seconds:
                print(f"[PERF] {func.__name__}: using cache (age {cache_age:.3f}s)")
                return cache['result']
            
            # Cache miss or expired - call function
            print(f"[PERF] {func.__name__}: cache miss, executing function")
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            # Update cache
            cache['result'] = result
            cache['timestamp'] = current_time
            
            print(f"[PERF] {func.__name__}: completed in {elapsed:.3f}s")
            return result
        
        return wrapper
    return decorator

# Initialize managers
config_manager = ConfigManager(CONFIG_FILE, STATE_FILE, LOG_FILE)

# Initialize Kraken API (read-only)
load_env()
kraken_api = None
try:
    kraken_api = KrakenAPI.from_env(readwrite=False)
except Exception as e:
    print(f"Warning: Could not initialize Kraken API: {e}")
    print("Dashboard will run in limited mode without live Kraken data.")

# Notification manager will be initialized in main() after environment is confirmed
notification_manager = None

# Short TTL cache for open orders (5s)
@ttl_cache(seconds=5)
def get_cached_open_orders():
    """Get open orders from Kraken with short TTL caching."""
    if not kraken_api:
        return {}
    result = kraken_api.query_open_orders()
    return result.get('open', {})

# Longer TTL cache for closed orders (30s)
@ttl_cache(seconds=30)
def get_cached_closed_orders():
    """Get closed orders from Kraken with longer TTL caching."""
    if not kraken_api:
        return {}
    result = kraken_api.query_closed_orders()
    return result.get('closed', {})


@ttl_cache(seconds=5)
def get_cached_config():
    """Get config with TTL-based caching."""
    if not os.path.exists(CONFIG_FILE):
        return []
    return config_manager.load_config()


@ttl_cache(seconds=5)
def get_cached_state():
    """Get state with TTL-based caching."""
    if not os.path.exists(STATE_FILE):
        return {}
    return config_manager.load_state()


@ttl_cache(seconds=5)
def get_current_prices():
    """Get current prices for all pairs in config with TTL-based caching."""
    start_time = time.time()
    print(f"[PERF] get_current_prices started at {datetime.now(timezone.utc).isoformat()}")
    
    prices = {}
    if not kraken_api:
        print(f"[PERF] get_current_prices: no kraken_api, elapsed {time.time() - start_time:.3f}s")
        return prices
    
    # Use cached config
    configs = get_cached_config()
    
    pairs = set(config.get('pair') for config in configs if config.get('pair'))
    print(f"[PERF] Found {len(pairs)} unique pairs to fetch prices for")
    
    # Batch fetch all prices in a single API call (much faster!)
    if pairs:
        batch_start = time.time()
        prices = kraken_api.get_current_prices_batch(pairs)
        print(f"[PERF] Batch fetch of {len(pairs)} pairs took {time.time() - batch_start:.3f}s, got {len(prices)} prices")
        
        # If batch fetch didn't return all prices, fall back to individual fetches for missing ones
        missing_pairs = pairs - set(prices.keys())
        if missing_pairs:
            print(f"[PERF] Batch fetch missed {len(missing_pairs)} pairs, fetching individually")
            for pair in missing_pairs:
                try:
                    pair_start = time.time()
                    price = kraken_api.get_current_price(pair)
                    if price:
                        prices[pair] = price
                    print(f"[PERF] get_current_price({pair}) took {time.time() - pair_start:.3f}s")
                except Exception as e:
                    print(f"[PERF] Error getting price for {pair}: {e}")
    
    elapsed = time.time() - start_time
    print(f"[PERF] get_current_prices completed in {elapsed:.3f}s, returned {len(prices)} prices")
    return prices


def calculate_distance_to_trigger(threshold_price, current_price, threshold_type):
    """
    Calculate how far an order is from triggering.
    
    Returns:
        dict with 'percent' and 'absolute' distance
    """
    try:
        threshold = float(threshold_price)
        current = float(current_price)
        
        if threshold_type == 'above':
            distance = threshold - current
            percent = (distance / current) * 100
        else:  # below
            distance = current - threshold
            percent = (distance / current) * 100
        
        return {
            'absolute': distance,
            'percent': percent,
            'triggered': (threshold_type == 'above' and current >= threshold) or 
                        (threshold_type == 'below' and current <= threshold)
        }
    except (ValueError, TypeError, ZeroDivisionError):
        return {'absolute': 0, 'percent': 0, 'triggered': False}


def get_pending_orders():
    """Get orders that haven't triggered yet."""
    start_time = time.time()
    print(f"[PERF] get_pending_orders started at {datetime.now(timezone.utc).isoformat()}")
    
    # Use cached config and state
    configs = get_cached_config()
    state = get_cached_state()
    
    price_start = time.time()
    prices = get_current_prices()
    print(f"[PERF] get_current_prices took {time.time() - price_start:.3f}s")
    
    pending = []
    for config in configs:
        config_id = config.get('id')
        enabled = config.get('enabled', '').lower() == 'true'
        
        # Skip if already triggered or disabled
        if not enabled:
            continue
        
        config_state = state.get(config_id, {})
        if config_state.get('triggered') == 'true':
            continue
        
        # Get current price
        pair = config.get('pair')
        current_price = prices.get(pair)
        
        # Calculate distance to trigger
        distance = None
        if current_price:
            distance = calculate_distance_to_trigger(
                config.get('threshold_price'),
                current_price,
                config.get('threshold_type')
            )
        
        pending.append({
            'id': config_id,
            'pair': pair,
            'threshold_price': config.get('threshold_price'),
            'threshold_type': config.get('threshold_type'),
            'direction': config.get('direction'),
            'volume': config.get('volume'),
            'trailing_offset_percent': config.get('trailing_offset_percent'),
            'current_price': current_price,
            'distance': distance
        })
    
    elapsed = time.time() - start_time
    print(f"[PERF] get_pending_orders completed in {elapsed:.3f}s, returned {len(pending)} orders")
    return pending


def get_active_orders():
    """Get orders that have triggered and are active on Kraken."""
    start_time = time.time()
    print(f"[PERF] get_active_orders started at {datetime.now(timezone.utc).isoformat()}")
    
    if not kraken_api:
        print(f"[PERF] get_active_orders: no kraken_api, elapsed {time.time() - start_time:.3f}s")
        return []
    
    # Use cached config and state
    state = get_cached_state()
    configs = get_cached_config()
    
    # Create a map of config IDs to their configs
    config_map = {c.get('id'): c for c in configs}
    
    active = []
    
    try:
        # Use cached open orders (5s TTL)
        open_orders = get_cached_open_orders()
        print(f"[PERF] Cached open orders: {len(open_orders)}")
        filter_start = time.time()
        for config_id, config_state in state.items():
            if config_state.get('triggered') != 'true':
                continue
            order_id = config_state.get('order_id')
            if not order_id:
                continue
            order_info = open_orders.get(order_id)
            if order_info:
                config = config_map.get(config_id, {})
                active.append({
                    'id': config_id,
                    'order_id': order_id,
                    'pair': config.get('pair'),
                    'trigger_price': config_state.get('trigger_price'),
                    'trigger_time': config_state.get('trigger_time'),
                    'volume': order_info.get('vol'),
                    'executed_volume': order_info.get('vol_exec', '0'),
                    'status': order_info.get('status'),
                    'order_type': order_info.get('descr', {}).get('ordertype'),
                    'price': order_info.get('descr', {}).get('price'),
                    'trailing_offset_percent': config.get('trailing_offset_percent'),
                })
        filter_elapsed = time.time() - filter_start
        print(f"[PERF] Filtering/matching {len(state)} state entries took {filter_elapsed:.3f}s")
        # Note: previously this function attempted to add 'manual closed orders'
        # by iterating over a variable named `closed_orders` and appending to
        # a `completed` list. Those variables are not defined in this
        # function's scope and that produced NameError exceptions (seen in
        # logs). Closed/completed orders are handled in get_completed_orders(),
        # so the manual-closed-orders logic was removed to avoid the errors.
        # Include open Kraken trailing-stop orders that are not recorded in state.csv
        # Mark these as manual so the UI can indicate they weren't created by this service.
        try:
            for order_id, order_info in open_orders.items():
                # Skip if already included (matched via state)
                if any(a.get('order_id') == order_id for a in active):
                    continue
                descr = order_info.get('descr', {}) or {}
                ordertype = descr.get('ordertype')
                # Only include trailing-stop orders (TSL)
                if ordertype != 'trailing-stop':
                    continue
                # Add as manual/open order
                active.append({
                    'id': order_id,
                    'order_id': order_id,
                    'pair': descr.get('pair'),
                    'trigger_price': None,
                    'trigger_time': None,
                    'volume': order_info.get('vol'),
                    'executed_volume': order_info.get('vol_exec', '0'),
                    'status': order_info.get('status'),
                    'order_type': ordertype,
                    'price': descr.get('price'),
                    'manual': True,
                    'source': 'kraken'
                })
        except Exception as e:
            print(f"[PERF] Error adding manual open orders: {e}")
    except Exception as e:
        print(f"[PERF] Error getting active orders: {e}")
    
    elapsed = time.time() - start_time
    print(f"[PERF] get_active_orders completed in {elapsed:.3f}s, returned {len(active)} orders")
    return active


def get_completed_orders():
    """Get orders that have executed."""
    start_time = time.time()
    print(f"[PERF] get_completed_orders started at {datetime.now(timezone.utc).isoformat()}")
    
    if not kraken_api:
        print(f"[PERF] get_completed_orders: no kraken_api, elapsed {time.time() - start_time:.3f}s")
        return []
    
    # Use cached config and state
    state = get_cached_state()
    configs = get_cached_config()
    
    # Create a map of config IDs to their configs
    config_map = {c.get('id'): c for c in configs}
    
    completed = []
    
    try:
        # Use cached closed orders (30s TTL)
        closed_orders = get_cached_closed_orders()
        print(f"[PERF] Cached closed orders: {len(closed_orders)}")
        filter_start = time.time()
        for config_id, config_state in state.items():
            if config_state.get('triggered') != 'true':
                continue
            order_id = config_state.get('order_id')
            if not order_id:
                continue
            order_info = closed_orders.get(order_id)
            if order_info and order_info.get('status') in ['closed', 'canceled']:
                config = config_map.get(config_id, {})
                trigger_price = float(config_state.get('trigger_price', 0))
                executed_price = float(order_info.get('price', 0))
                benefit = 0
                benefit_percent = 0
                if trigger_price > 0:
                    direction = config.get('direction', 'sell')
                    if direction == 'sell':
                        benefit = executed_price - trigger_price
                        benefit_percent = (benefit / trigger_price) * 100
                    else:  # buy
                        benefit = trigger_price - executed_price
                        benefit_percent = (benefit / trigger_price) * 100
                completed.append({
                    'id': config_id,
                    'order_id': order_id,
                    'pair': config.get('pair'),
                    'trigger_price': trigger_price,
                    'executed_price': executed_price,
                    'trigger_time': config_state.get('trigger_time'),
                    'close_time': datetime.fromtimestamp(
                        order_info.get('closetm', 0), tz=timezone.utc
                    ).isoformat() if order_info.get('closetm') else None,
                    'volume': order_info.get('vol'),
                    'status': order_info.get('status'),
                    'direction': config.get('direction'),
                    'benefit': benefit,
                    'benefit_percent': benefit_percent,
                    'trailing_offset_percent': config.get('trailing_offset_percent'),
                })
        filter_elapsed = time.time() - filter_start
        print(f"[PERF] Filtering/matching {len(state)} state entries took {filter_elapsed:.3f}s")
    except Exception as e:
        print(f"[PERF] Error getting completed orders: {e}")
    
    elapsed = time.time() - start_time
    print(f"[PERF] get_completed_orders completed in {elapsed:.3f}s, returned {len(completed)} orders")
    return completed


@app.route('/')
def index():
    """Render the dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/pending')
def api_pending():
    """API endpoint for pending orders."""
    start_time = time.time()
    print(f"[PERF] /api/pending endpoint called at {datetime.now(timezone.utc).isoformat()}")
    result = jsonify(get_pending_orders())
    elapsed = time.time() - start_time
    print(f"[PERF] /api/pending endpoint completed in {elapsed:.3f}s")
    return result


@app.route('/api/active')
def api_active():
    """API endpoint for active orders."""
    start_time = time.time()
    print(f"[PERF] /api/active endpoint called at {datetime.now(timezone.utc).isoformat()}")
    result = jsonify(get_active_orders())
    elapsed = time.time() - start_time
    print(f"[PERF] /api/active endpoint completed in {elapsed:.3f}s")
    return result


@app.route('/api/completed')
def api_completed():
    """API endpoint for completed orders."""
    start_time = time.time()
    print(f"[PERF] /api/completed endpoint called at {datetime.now(timezone.utc).isoformat()}")
    result = jsonify(get_completed_orders())
    elapsed = time.time() - start_time
    print(f"[PERF] /api/completed endpoint completed in {elapsed:.3f}s")
    return result


@app.route('/api/status')
def api_status():
    """API endpoint for overall system status."""

# Summary of logical flow for dashboard endpoints
#
# 1. Config and state are loaded with 5s TTL cache (fast repeated access)
# 2. Prices are fetched in batch and cached for 5s (minimize API calls)
# 3. Open orders are fetched in one call and cached for 5s (minimize API calls)
# 4. Closed orders are fetched in one call and cached for 30s (since they rarely change)
# 5. All matching/filtering is done in memory (fast)
# 6. Dashboard JS preserves last known data if fetch fails or is slow
    return jsonify({
        'config_file': CONFIG_FILE,
        'state_file': STATE_FILE,
        'config_exists': os.path.exists(CONFIG_FILE),
        'state_exists': os.path.exists(STATE_FILE),
        'kraken_api_available': kraken_api is not None,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@app.route('/health')
def health():
    """Health check endpoint for monitoring."""
    checks = {
        'config_file': os.path.exists(CONFIG_FILE),
        'kraken_api': kraken_api is not None,
        'telegram_notifications': True  # Default to True if not enabled
    }
    
    # Check notification status if enabled
    if notification_manager and notification_manager.enabled:
        # If last notification failed, mark as unhealthy
        if notification_manager.last_notification_success is False:
            checks['telegram_notifications'] = False
        # If queue has items, notifications are failing
        elif notification_manager.notification_queue:
            checks['telegram_notifications'] = False
    
    is_healthy = all(checks.values())
    
    return jsonify({
        'status': 'healthy' if is_healthy else 'unhealthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'checks': checks
    }), 200 if is_healthy else 503


@app.route('/health-details')
def health_details():
    """Detailed health status page."""
    return render_template('health_details.html')


@app.route('/api/test-notification', methods=['POST'])
def test_notification():
    """Send a test notification with health information."""
    if not notification_manager or not notification_manager.enabled:
        return jsonify({
            'success': False,
            'error': 'Notifications not enabled',
            'details': {
                'token_present': bool(notification_manager.telegram_token) if notification_manager else False,
                'recipients_count': len(notification_manager.recipients) if notification_manager else 0
            }
        }), 503
    
    # Get current health info
    health_checks = {
        'config_file': os.path.exists(CONFIG_FILE),
        'kraken_api': kraken_api is not None,
        'telegram_notifications': notification_manager.last_notification_success is not False
    }
    
    # Get system info
    system_info = {
        'config_file': CONFIG_FILE,
        'state_file': STATE_FILE,
        'config_exists': os.path.exists(CONFIG_FILE),
        'state_exists': os.path.exists(STATE_FILE),
        'kraken_api_available': kraken_api is not None
    }
    
    health_info = {
        'status': 'healthy' if all(health_checks.values()) else 'unhealthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'checks': health_checks,
        'system_info': system_info
    }
    
    # Send test notification
    result = notification_manager.send_test_notification(health_info)
    
    return jsonify(result), 200 if result['success'] else 500


@app.route('/backup')
def backup():
    """Create and download a backup zip file with all config and data files."""
    # Create an in-memory zip file
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add config file if it exists
        if os.path.exists(CONFIG_FILE):
            zf.write(CONFIG_FILE, os.path.basename(CONFIG_FILE))
        
        # Add state file if it exists
        if os.path.exists(STATE_FILE):
            zf.write(STATE_FILE, os.path.basename(STATE_FILE))
        
        # Add log file if it exists
        if os.path.exists(LOG_FILE):
            zf.write(LOG_FILE, os.path.basename(LOG_FILE))
        
        # Add .env file if it exists (contains credentials)
        env_file = os.getenv('TTSLO_ENV_FILE', '.env')
        if os.path.exists(env_file):
            zf.write(env_file, os.path.basename(env_file))
        
        # Add notifications config if it exists
        notifications_ini_paths = [
            'notifications.ini',
            '/var/lib/ttslo/notifications.ini',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notifications.ini')
        ]
        for notif_path in notifications_ini_paths:
            if os.path.exists(notif_path):
                zf.write(notif_path, 'notifications.ini')
                break
        
        # Add a manifest with backup metadata
        manifest = {
            'backup_time': datetime.now(timezone.utc).isoformat(),
            'files_included': zf.namelist()
        }
        zf.writestr('backup_manifest.json', json.dumps(manifest, indent=2))
    
    # Seek to beginning of BytesIO buffer
    memory_file.seek(0)
    
    # Generate filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    filename = f'ttslo-backup-{timestamp}.zip'
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )


@app.route('/openapi.json')
def openapi_spec():
    """Serve the OpenAPI specification."""
    spec_path = os.path.join(os.path.dirname(__file__), 'openapi.json')
    with open(spec_path, 'r') as f:
        spec = json.load(f)
    return jsonify(spec)


if __name__ == '__main__':
    import argparse
    
    # Initialize notification manager here, after environment variables are loaded by systemd
    # Re-initialize at runtime (overwriting module-level None assignment)
    # Search for notifications.ini in multiple locations
    def find_notifications_ini():
        """Find notifications.ini in order: current dir, /var/lib/ttslo, script dir."""
        search_paths = [
            'notifications.ini',  # Current working directory
            '/var/lib/ttslo/notifications.ini',  # State directory
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notifications.ini')  # Script directory
        ]
        for path in search_paths:
            if os.path.exists(path):
                return path
        return 'notifications.ini'  # Default, will fail gracefully
    
    notification_ini = find_notifications_ini()
    notification_manager = None
    try:
        notification_manager = NotificationManager(notification_ini)
        if notification_manager.enabled:
            print(f"Telegram notifications enabled for {len(notification_manager.recipients)} recipients (using {notification_ini})")
        else:
            print(f"Telegram notifications disabled (token present: {bool(notification_manager.telegram_token)}, recipients: {len(notification_manager.recipients)}, config: {notification_ini})")
    except Exception as e:
        print(f"Warning: Could not initialize notification manager: {e}")
        notification_manager = None
    
    def signal_handler(signum, frame):
        """Handle termination signals gracefully."""
        sig_name = signal.Signals(signum).name
        print(f"\nReceived signal {sig_name} ({signum}). Shutting down Dashboard gracefully...")
        if notification_manager and notification_manager.enabled:
            try:
                notification_manager.notify_service_stopped_async(
                    service_name="TTSLO Dashboard",
                    reason=f"Received {sig_name} signal (systemctl stop/restart or kill)"
                )
            except Exception:
                notification_manager.notify_service_stopped(
                    service_name="TTSLO Dashboard",
                    reason=f"Received {sig_name} signal (systemctl stop/restart or kill)"
                )
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)  # systemctl stop/restart
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGHUP, signal_handler)   # Terminal closed
    
    parser = argparse.ArgumentParser(description='TTSLO Dashboard')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print(f"Starting TTSLO Dashboard on http://{args.host}:{args.port}")
    print(f"Config file: {CONFIG_FILE}")
    print(f"State file: {STATE_FILE}")
    print(f"Kraken API: {'Available' if kraken_api else 'Not available'}")
    
    # Send service started notification
    if notification_manager and notification_manager.enabled:
        # Determine the actual accessible URL
        import socket
        if args.host in ('0.0.0.0', '::'):
            # Get the actual server IP address by creating a socket connection
            # This gives us the actual LAN IP that would be used for outbound connections
            try:
                # Create a UDP socket (doesn't actually send data)
                # Connect to a public DNS server to determine our local IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                host_ip = s.getsockname()[0]
                s.close()
            except Exception:
                # Fallback: try to get IP from network interfaces
                try:
                    hostname = socket.gethostname()
                    # Get all IP addresses for this host
                    all_ips = socket.getaddrinfo(hostname, None)
                    
                    # Filter to IPv4 addresses only
                    ipv4_addresses = [ip[4][0] for ip in all_ips if ip[0] == socket.AF_INET]
                    
                    # Prioritize 192.168.x.x and 10.x.x.x addresses (private networks)
                    local_ips = [ip for ip in ipv4_addresses if ip.startswith('192.168.') or ip.startswith('10.')]
                    if local_ips:
                        host_ip = local_ips[0]
                    elif ipv4_addresses:
                        # Use first non-localhost IP
                        non_localhost = [ip for ip in ipv4_addresses if not ip.startswith('127.')]
                        host_ip = non_localhost[0] if non_localhost else ipv4_addresses[0]
                    else:
                        host_ip = '127.0.0.1'
                except Exception:
                    host_ip = '127.0.0.1'
        else:
            host_ip = args.host
        
        try:
            notification_manager.notify_service_started_async(
                service_name="TTSLO Dashboard",
                host=host_ip,
                port=args.port
            )
        except Exception:
            notification_manager.notify_service_started(
                service_name="TTSLO Dashboard",
                host=host_ip,
                port=args.port
            )
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        print(f"\nERROR: Dashboard crashed: {str(e)}", file=sys.stderr)
        if notification_manager:
            notification_manager.notify_service_stopped(
                service_name="TTSLO Dashboard",
                reason=f"Crashed: {str(e)}"
            )
        raise
