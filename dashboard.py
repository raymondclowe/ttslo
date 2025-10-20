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


def get_current_prices():
    """Get current prices for all pairs in config."""
    prices = {}
    if not kraken_api:
        return prices
    
    configs = config_manager.load_config()
    pairs = set(config.get('pair') for config in configs if config.get('pair'))
    
    for pair in pairs:
        try:
            price = kraken_api.get_current_price(pair)
            if price:
                prices[pair] = price
        except Exception as e:
            print(f"Error getting price for {pair}: {e}")
    
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
    configs = config_manager.load_config()
    state = config_manager.load_state()
    prices = get_current_prices()
    
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
    
    return pending


def get_active_orders():
    """Get orders that have triggered and are active on Kraken."""
    if not kraken_api:
        return []
    
    state = config_manager.load_state()
    configs = config_manager.load_config()
    
    # Create a map of config IDs to their configs
    config_map = {c.get('id'): c for c in configs}
    
    active = []
    
    try:
        # Get all open orders from Kraken
        open_orders_result = kraken_api.query_open_orders()
        open_orders = open_orders_result.get('open', {})
        
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
    except Exception as e:
        print(f"Error getting active orders: {e}")
    
    return active


def get_completed_orders():
    """Get orders that have executed."""
    if not kraken_api:
        return []
    
    state = config_manager.load_state()
    configs = config_manager.load_config()
    
    # Create a map of config IDs to their configs
    config_map = {c.get('id'): c for c in configs}
    
    completed = []
    
    try:
        # Get closed orders from Kraken
        closed_orders_result = kraken_api.query_closed_orders()
        closed_orders = closed_orders_result.get('closed', {})
        
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
    except Exception as e:
        print(f"Error getting completed orders: {e}")
    
    return completed


@app.route('/')
def index():
    """Render the dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/pending')
def api_pending():
    """API endpoint for pending orders."""
    return jsonify(get_pending_orders())


@app.route('/api/active')
def api_active():
    """API endpoint for active orders."""
    return jsonify(get_active_orders())


@app.route('/api/completed')
def api_completed():
    """API endpoint for completed orders."""
    return jsonify(get_completed_orders())


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
    global notification_manager
    try:
        notification_manager = NotificationManager()
        if notification_manager.enabled:
            print(f"Telegram notifications enabled for {len(notification_manager.recipients)} recipients")
        else:
            print(f"Telegram notifications disabled (token present: {bool(notification_manager.telegram_token)}, recipients: {len(notification_manager.recipients)})")
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
        notification_manager.notify_service_started(
            service_name="TTSLO Dashboard",
            host=args.host,
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
