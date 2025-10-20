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
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify
from config import ConfigManager
from kraken_api import KrakenAPI
from creds import load_env
from notifications import NotificationManager

app = Flask(__name__)

# Configuration
CONFIG_FILE = os.getenv('TTSLO_CONFIG_FILE', 'config.csv')
STATE_FILE = os.getenv('TTSLO_STATE_FILE', 'state.csv')
LOG_FILE = os.getenv('TTSLO_LOG_FILE', 'logs.csv')

# Cache for config/state data to reduce file I/O
_config_cache = {'data': None, 'mtime': 0, 'ttl': 5.0}  # 5 second TTL
_state_cache = {'data': None, 'mtime': 0, 'ttl': 5.0}  # 5 second TTL
_price_cache = {'data': {}, 'timestamp': 0, 'ttl': 5.0}  # 5 second TTL for prices

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


def get_cached_config():
    """Get config with file-based caching."""
    global _config_cache
    cache_start = time.time()
    
    # Check if file exists
    if not os.path.exists(CONFIG_FILE):
        print(f"[PERF] get_cached_config: file not found")
        return []
    
    # Get current file modification time
    current_mtime = os.path.getmtime(CONFIG_FILE)
    current_time = time.time()
    
    # Check if cache is valid (file hasn't changed and TTL not expired)
    cache_age = current_time - _config_cache['mtime']
    if (_config_cache['data'] is not None and 
        _config_cache['mtime'] == current_mtime and 
        cache_age < _config_cache['ttl']):
        print(f"[PERF] get_cached_config: using cache (age {cache_age:.3f}s)")
        return _config_cache['data']
    
    # Cache miss or expired - load from file
    print(f"[PERF] get_cached_config: cache miss, loading from file")
    configs = config_manager.load_config()
    
    # Update cache
    _config_cache['data'] = configs
    _config_cache['mtime'] = current_mtime
    
    elapsed = time.time() - cache_start
    print(f"[PERF] get_cached_config: completed in {elapsed:.3f}s")
    return configs


def get_cached_state():
    """Get state with file-based caching."""
    global _state_cache
    cache_start = time.time()
    
    # Check if file exists
    if not os.path.exists(STATE_FILE):
        print(f"[PERF] get_cached_state: file not found")
        return {}
    
    # Get current file modification time
    current_mtime = os.path.getmtime(STATE_FILE)
    current_time = time.time()
    
    # Check if cache is valid (file hasn't changed and TTL not expired)
    cache_age = current_time - _state_cache['mtime']
    if (_state_cache['data'] is not None and 
        _state_cache['mtime'] == current_mtime and 
        cache_age < _state_cache['ttl']):
        print(f"[PERF] get_cached_state: using cache (age {cache_age:.3f}s)")
        return _state_cache['data']
    
    # Cache miss or expired - load from file
    print(f"[PERF] get_cached_state: cache miss, loading from file")
    state = config_manager.load_state()
    
    # Update cache
    _state_cache['data'] = state
    _state_cache['mtime'] = current_mtime
    
    elapsed = time.time() - cache_start
    print(f"[PERF] get_cached_state: completed in {elapsed:.3f}s")
    return state


def get_current_prices():
    """Get current prices for all pairs in config."""
    global _price_cache
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
    
    # Check price cache
    current_time = time.time()
    cache_age = current_time - _price_cache['timestamp']
    if cache_age < _price_cache['ttl'] and _price_cache['data']:
        # Check if we have all needed prices in cache
        cached_pairs = set(_price_cache['data'].keys())
        if pairs.issubset(cached_pairs):
            print(f"[PERF] Using cached prices (age {cache_age:.3f}s)")
            # Return only the prices we need
            prices = {pair: _price_cache['data'][pair] for pair in pairs if pair in _price_cache['data']}
            elapsed = time.time() - start_time
            print(f"[PERF] get_current_prices completed in {elapsed:.3f}s (from cache), returned {len(prices)} prices")
            return prices
    
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
        
        # Update price cache
        _price_cache['data'] = prices
        _price_cache['timestamp'] = current_time
    
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
        # Get all open orders from Kraken
        api_start = time.time()
        open_orders_result = kraken_api.query_open_orders()
        api_elapsed = time.time() - api_start
        print(f"[PERF] query_open_orders API call took {api_elapsed:.3f}s")
        
        open_orders = open_orders_result.get('open', {})
        print(f"[PERF] Kraken returned {len(open_orders)} open orders")
        
        filter_start = time.time()
        # Match with our state
        for config_id, config_state in state.items():
            if config_state.get('triggered') != 'true':
                continue
            
            order_id = config_state.get('order_id')
            if not order_id:
                continue
            
            # Check if this order is still open
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
                })
        filter_elapsed = time.time() - filter_start
        print(f"[PERF] Filtering/matching {len(state)} state entries took {filter_elapsed:.3f}s")
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
        # Get closed orders from Kraken
        api_start = time.time()
        closed_orders_result = kraken_api.query_closed_orders()
        api_elapsed = time.time() - api_start
        print(f"[PERF] query_closed_orders API call took {api_elapsed:.3f}s")
        
        closed_orders = closed_orders_result.get('closed', {})
        print(f"[PERF] Kraken returned {len(closed_orders)} closed orders")
        
        filter_start = time.time()
        # Match with our state
        for config_id, config_state in state.items():
            if config_state.get('triggered') != 'true':
                continue
            
            order_id = config_state.get('order_id')
            if not order_id:
                continue
            
            # Check if this order is closed
            order_info = closed_orders.get(order_id)
            if order_info and order_info.get('status') in ['closed', 'canceled']:
                config = config_map.get(config_id, {})
                trigger_price = float(config_state.get('trigger_price', 0))
                executed_price = float(order_info.get('price', 0))
                
                # Calculate benefit (for sell orders, higher is better; for buy, lower is better)
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
                    'benefit_percent': benefit_percent
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
    return jsonify({
        'config_file': CONFIG_FILE,
        'state_file': STATE_FILE,
        'config_exists': os.path.exists(CONFIG_FILE),
        'state_exists': os.path.exists(STATE_FILE),
        'kraken_api_available': kraken_api is not None,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


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
            # Get the actual server IP address, prioritizing 192.168.x.x
            try:
                hostname = socket.gethostname()
                # Get all IP addresses for this host
                all_ips = socket.getaddrinfo(hostname, None)
                
                # Filter to IPv4 addresses only
                ipv4_addresses = [ip[4][0] for ip in all_ips if ip[0] == socket.AF_INET]
                
                # Prioritize 192.168.x.x addresses
                local_ips = [ip for ip in ipv4_addresses if ip.startswith('192.168.')]
                if local_ips:
                    host_ip = local_ips[0]
                elif ipv4_addresses:
                    # Use first non-localhost IP
                    non_localhost = [ip for ip in ipv4_addresses if ip != '127.0.0.1']
                    host_ip = non_localhost[0] if non_localhost else ipv4_addresses[0]
                else:
                    host_ip = '127.0.0.1'
            except:
                host_ip = '127.0.0.1'
        else:
            host_ip = args.host
        
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
