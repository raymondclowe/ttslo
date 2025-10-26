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
from flask import Flask, render_template, jsonify, send_file, request
from config import ConfigManager
from kraken_api import KrakenAPI
from creds import load_env
from notifications import NotificationManager

app = Flask(__name__)

# Configuration
CONFIG_FILE = os.getenv('TTSLO_CONFIG_FILE', 'config.csv')
STATE_FILE = os.getenv('TTSLO_STATE_FILE', 'state.csv')
LOG_FILE = os.getenv('TTSLO_LOG_FILE', 'logs.csv')
CHECK_INTERVAL = int(os.getenv('TTSLO_CHECK_INTERVAL', '60'))  # Main monitor check interval in seconds
DASHBOARD_REFRESH_INTERVAL = max(5, CHECK_INTERVAL // 2)  # Dashboard refresh = check_interval/2, minimum 5s

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

# Cache for open orders - aligns with dashboard refresh interval
@ttl_cache(seconds=DASHBOARD_REFRESH_INTERVAL)
def get_cached_open_orders():
    """Get open orders from Kraken with TTL caching."""
    if not kraken_api:
        return {}
    result = kraken_api.query_open_orders()
    return result.get('open', {})

# Cache for closed orders - aligns with dashboard refresh interval
@ttl_cache(seconds=DASHBOARD_REFRESH_INTERVAL)
def get_cached_closed_orders():
    """Get closed orders from Kraken with TTL caching."""
    if not kraken_api:
        return {}
    result = kraken_api.query_closed_orders()
    return result.get('closed', {})


@ttl_cache(seconds=DASHBOARD_REFRESH_INTERVAL)
def get_cached_config():
    """Get config with TTL-based caching."""
    if not os.path.exists(CONFIG_FILE):
        return []
    return config_manager.load_config()


@ttl_cache(seconds=DASHBOARD_REFRESH_INTERVAL)
def get_cached_state():
    """Get state with TTL-based caching."""
    if not os.path.exists(STATE_FILE):
        return {}
    return config_manager.load_state()


@ttl_cache(seconds=DASHBOARD_REFRESH_INTERVAL)
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


@ttl_cache(seconds=DASHBOARD_REFRESH_INTERVAL)
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


@ttl_cache(seconds=DASHBOARD_REFRESH_INTERVAL)
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
                # Extract trailing offset from price field
                # Format is like "+5.0000%" or "-5.0000%"
                price_str = descr.get('price', '')
                trailing_offset_percent = None
                if price_str:
                    # Remove '+', '-', and '%' to get the numeric value
                    trailing_offset_percent = price_str.replace('+', '').replace('-', '').replace('%', '').strip()
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
                    'trailing_offset_percent': trailing_offset_percent,
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


@ttl_cache(seconds=DASHBOARD_REFRESH_INTERVAL)
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
        # Collect order IDs from triggered state entries
        order_ids = []
        config_id_by_order = {}  # Map order_id -> config_id
        
        for config_id, config_state in state.items():
            if config_state.get('triggered') != 'true':
                continue
            order_id = config_state.get('order_id')
            if not order_id:
                continue
            order_ids.append(order_id)
            config_id_by_order[order_id] = config_id
        
        print(f"[PERF] Found {len(order_ids)} triggered orders in state")
        
        if not order_ids:
            print(f"[PERF] No triggered orders to query")
            return []
        
        # Query specific order IDs directly (more efficient than fetching all closed orders)
        # Kraken's QueryOrders endpoint can query up to 50 orders at once
        query_start = time.time()
        try:
            closed_orders = kraken_api.query_orders(order_ids)
            query_elapsed = time.time() - query_start
            print(f"[PERF] Queried {len(order_ids)} specific orders in {query_elapsed:.3f}s, got {len(closed_orders)} results")
            
            # Check if query_orders returned all expected orders
            missing_orders = set(order_ids) - set(closed_orders.keys())
            if missing_orders:
                print(f"[PERF] WARNING: query_orders missing {len(missing_orders)} orders: {list(missing_orders)[:3]}...")
                # Query closed orders to find missing ones
                all_closed = get_cached_closed_orders()
                for oid in missing_orders:
                    if oid in all_closed:
                        closed_orders[oid] = all_closed[oid]
                        print(f"[PERF] Found missing order {oid[:12]}... in closed orders")
        except Exception as e:
            print(f"[PERF] Error querying specific orders: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to the old method if query_orders fails
            closed_orders = get_cached_closed_orders()
            print(f"[PERF] Fallback: using cached closed orders, got {len(closed_orders)} orders")
        
        filter_start = time.time()
        for order_id, order_info in closed_orders.items():
            config_id = config_id_by_order.get(order_id)
            if not config_id:
                # This is a manual order not tracked in state
                # Skip for now - only show orders we created
                continue
                
            if order_info and order_info.get('status') in ['closed', 'canceled']:
                config = config_map.get(config_id, {})
                config_state = state.get(config_id, {})
                trigger_price = float(config_state.get('trigger_price', 0))
                initial_price = float(config_state.get('initial_price', 0))
                executed_price = float(order_info.get('price', 0))
                
                # Calculate benefit from trigger_price (existing behavior)
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
                
                # Calculate total benefit from initial_price (new feature)
                total_benefit = 0
                total_benefit_percent = 0
                if initial_price > 0 and executed_price > 0:
                    direction = config.get('direction', 'sell')
                    if direction == 'sell':
                        # Selling: benefit if executed higher than initial
                        total_benefit = executed_price - initial_price
                        total_benefit_percent = (total_benefit / initial_price) * 100
                    else:  # buy
                        # Buying: benefit if executed lower than initial
                        total_benefit = initial_price - executed_price
                        total_benefit_percent = (total_benefit / initial_price) * 100
                
                completed.append({
                    'id': config_id,
                    'order_id': order_id,
                    'pair': config.get('pair'),
                    'trigger_price': trigger_price,
                    'initial_price': initial_price,
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
                    'total_benefit': total_benefit,
                    'total_benefit_percent': total_benefit_percent,
                    'trailing_offset_percent': config.get('trailing_offset_percent'),
                })
        
        # Include manual closed trailing-stop orders from Kraken not in state
        try:
            all_closed = get_cached_closed_orders()
            for order_id, order_info in all_closed.items():
                # Skip if already included
                if any(c.get('order_id') == order_id for c in completed):
                    continue
                    
                descr = order_info.get('descr', {}) or {}
                ordertype = descr.get('ordertype')
                
                # Only include trailing-stop orders
                if ordertype != 'trailing-stop':
                    continue
                    
                # For manual orders (not in state), only show closed orders
                # Canceled manual orders are not relevant
                if order_info.get('status') != 'closed':
                    continue
                
                # Add as manual completed order
                executed_price = float(order_info.get('price', 0))
                completed.append({
                    'id': order_id,
                    'order_id': order_id,
                    'pair': descr.get('pair'),
                    'trigger_price': None,
                    'executed_price': executed_price,
                    'trigger_time': None,
                    'close_time': datetime.fromtimestamp(
                        order_info.get('closetm', 0), tz=timezone.utc
                    ).isoformat() if order_info.get('closetm') else None,
                    'volume': order_info.get('vol'),
                    'status': order_info.get('status'),
                    'direction': descr.get('type'),  # 'buy' or 'sell'
                    'benefit': None,
                    'benefit_percent': None,
                    'trailing_offset_percent': None,
                    'manual': True,
                    'source': 'kraken'
                })
        except Exception as e:
            print(f"[PERF] Error adding manual completed orders: {e}")
        
        filter_elapsed = time.time() - filter_start
        print(f"[PERF] Filtering/matching {len(closed_orders)} orders took {filter_elapsed:.3f}s")
    except Exception as e:
        print(f"[PERF] Error getting completed orders: {e}")
    
    elapsed = time.time() - start_time
    print(f"[PERF] get_completed_orders completed in {elapsed:.3f}s, returned {len(completed)} orders")
    return completed


def _extract_base_asset(pair: str) -> str:
    """
    Extract the base asset from a trading pair.
    
    Args:
        pair: Trading pair (e.g., 'XXBTZUSD', 'XETHZUSD', 'DYDXUSD')
        
    Returns:
        Base asset code (e.g., 'XXBT', 'XETH', 'DYDX') or empty string if can't determine
    """
    # Known mappings for common pairs
    pair_mappings = {
        'XBTUSDT': 'XXBT',
        'XBTUSD': 'XXBT',
        'XXBTZEUR': 'XXBT',
        'XXBTZGBP': 'XXBT',
        'XXBTZUSD': 'XXBT',
        'ETHUSDT': 'XETH',
        'ETHUSD': 'XETH',
        'XETHZEUR': 'XETH',
        'XETHZUSD': 'XETH',
        'SOLUSDT': 'SOL',
        'SOLEUR': 'SOL',
        'SOLUSD': 'SOL',
        'ADAUSDT': 'ADA',
        'ADAUSD': 'ADA',
        'DOTUSDT': 'DOT',
        'DOTUSD': 'DOT',
        'AVAXUSDT': 'AVAX',
        'AVAXUSD': 'AVAX',
        'LINKUSDT': 'LINK',
        'LINKUSD': 'LINK',
        'DYDXUSD': 'DYDX',
        'NEARUSD': 'NEAR',
        'MEMEUSD': 'MEME',
    }
    
    # Check if we have a known mapping
    if pair in pair_mappings:
        return pair_mappings[pair]
    
    # Try to extract from pattern
    # Note: Order matters - check longer suffixes first (e.g., USDT before USD)
    for quote in ['USDT', 'ZUSD', 'ZEUR', 'EUR', 'ZGBP', 'GBP', 'ZJPY', 'JPY', 'USD']:
        if pair.endswith(quote):
            base = pair[:-len(quote)]
            if base:
                return base
    
    return ''


def _extract_quote_asset(pair: str) -> str:
    """
    Extract the quote asset from a trading pair.
    
    Args:
        pair: Trading pair (e.g., 'XXBTZUSD', 'XETHZUSD', 'DYDXUSD')
        
    Returns:
        Quote asset code (e.g., 'ZUSD', 'EUR') normalized to Kraken's internal notation
        
    Note:
        Kraken uses 'Z' prefix for fiat currencies in API responses:
        - USD → ZUSD
        - EUR → ZEUR
        - GBP → ZGBP
        - JPY → ZJPY
    """
    # Try to extract from pattern
    # Note: Order matters - check longer suffixes first (e.g., USDT before USD)
    for quote in ['USDT', 'ZUSD', 'ZEUR', 'EUR', 'ZGBP', 'GBP', 'ZJPY', 'JPY', 'USD']:
        if pair.endswith(quote):
            # Normalize to Kraken's internal notation (Z-prefixed for fiat)
            if quote == 'USD':
                return 'ZUSD'
            elif quote == 'EUR':
                return 'ZEUR'
            elif quote == 'GBP':
                return 'ZGBP'
            elif quote == 'JPY':
                return 'ZJPY'
            else:
                return quote
    
    return ''


@ttl_cache(seconds=DASHBOARD_REFRESH_INTERVAL)
def get_balances_and_risks():
    """
    Get account balances and analyze risk for pending and active orders.
    
    Returns:
        Dictionary with:
        - assets: List of asset balance info with risk analysis
        - risk_summary: Overall risk assessment
    """
    start_time = time.time()
    print(f"[PERF] get_balances_and_risks started at {datetime.now(timezone.utc).isoformat()}")
    
    if not kraken_api:
        print(f"[PERF] get_balances_and_risks: no kraken_api, elapsed {time.time() - start_time:.3f}s")
        return {'assets': [], 'risk_summary': {'status': 'unknown', 'message': 'Kraken API not available'}}
    
    try:
        # Get pending and active orders (exclude completed)
        pending = get_pending_orders()
        active = get_active_orders()
        prices = get_current_prices()
        
        # Get account balances
        balances = kraken_api.get_balance()
        
        # Collect unique assets from orders
        assets_needed = {}  # asset -> {buy_volume, sell_volume, pairs}
        
        for order in pending + active:
            pair = order.get('pair')
            if not pair:
                continue
            
            base_asset = _extract_base_asset(pair)
            quote_asset = _extract_quote_asset(pair)
            
            if not base_asset:
                continue
            
            volume = float(order.get('volume', 0))
            direction = order.get('direction', '')
            
            # Initialize asset tracking if needed
            if base_asset not in assets_needed:
                assets_needed[base_asset] = {'buy_volume': 0, 'sell_volume': 0, 'pairs': set()}
            if quote_asset and quote_asset not in assets_needed:
                assets_needed[quote_asset] = {'buy_volume': 0, 'sell_volume': 0, 'pairs': set()}
            
            # Track volume requirements
            if direction == 'sell':
                # Selling base asset - need base asset balance
                assets_needed[base_asset]['sell_volume'] += volume
                assets_needed[base_asset]['pairs'].add(pair)
            elif direction == 'buy':
                # Buying base asset - need quote currency balance (not base asset)
                # Track the pair for the base asset but don't require base asset balance
                assets_needed[base_asset]['pairs'].add(pair)
                
                # For buys, we need the quote currency
                if quote_asset and pair in prices:
                    price = prices[pair]
                    quote_needed = volume * price
                    assets_needed[quote_asset]['buy_volume'] += quote_needed
                    assets_needed[quote_asset]['pairs'].add(pair)
        
        # Build asset info with risk analysis
        asset_list = []
        overall_warnings = []
        
        for asset, needs in assets_needed.items():
            # Get balance for this asset
            balance = float(balances.get(asset, 0))
            
            # Calculate requirements
            sell_requirement = needs['sell_volume']
            buy_requirement = needs['buy_volume']
            
            # Determine current sufficiency
            current_sufficient = balance >= sell_requirement
            
            # Risk scenarios
            all_sells_trigger = balance >= sell_requirement
            all_buys_trigger = balance >= buy_requirement
            
            # Determine risk level
            if sell_requirement > 0:
                sell_coverage = (balance / sell_requirement * 100) if sell_requirement > 0 else 100
            else:
                sell_coverage = 100
                
            if buy_requirement > 0:
                buy_coverage = (balance / buy_requirement * 100) if buy_requirement > 0 else 100
            else:
                buy_coverage = 100
            
            # Determine risk status
            if sell_requirement > 0 and balance < sell_requirement:
                risk_status = 'danger'
                risk_message = f'Insufficient balance for sell orders ({balance:.4f} < {sell_requirement:.4f})'
                overall_warnings.append(f'{asset}: {risk_message}')
            elif buy_requirement > 0 and balance < buy_requirement:
                risk_status = 'danger'
                risk_message = f'Insufficient balance for buy orders ({balance:.4f} < {buy_requirement:.4f})'
                overall_warnings.append(f'{asset}: {risk_message}')
            elif sell_requirement > 0 and balance < sell_requirement * 1.5:
                risk_status = 'warning'
                risk_message = f'Low balance for sell orders (only {sell_coverage:.0f}% coverage)'
                overall_warnings.append(f'{asset}: {risk_message}')
            elif buy_requirement > 0 and balance < buy_requirement * 1.5:
                risk_status = 'warning'
                risk_message = f'Low balance for buy orders (only {buy_coverage:.0f}% coverage)'
                overall_warnings.append(f'{asset}: {risk_message}')
            else:
                risk_status = 'safe'
                risk_message = 'Sufficient balance'
            
            asset_list.append({
                'asset': asset,
                'balance': balance,
                'sell_requirement': sell_requirement,
                'buy_requirement': buy_requirement,
                'sell_coverage': sell_coverage,
                'buy_coverage': buy_coverage,
                'risk_status': risk_status,
                'risk_message': risk_message,
                'pairs': sorted(list(needs['pairs']))
            })
        
        # Sort by risk status (danger first, then warning, then safe)
        risk_order = {'danger': 0, 'warning': 1, 'safe': 2}
        asset_list.sort(key=lambda x: (risk_order.get(x['risk_status'], 3), x['asset']))
        
        # Overall risk summary
        if any(a['risk_status'] == 'danger' for a in asset_list):
            risk_summary = {
                'status': 'danger',
                'message': 'Critical: Insufficient balance for some orders'
            }
        elif any(a['risk_status'] == 'warning' for a in asset_list):
            risk_summary = {
                'status': 'warning',
                'message': 'Warning: Low balance for some orders'
            }
        else:
            risk_summary = {
                'status': 'safe',
                'message': 'All balances sufficient'
            }
        
        elapsed = time.time() - start_time
        print(f"[PERF] get_balances_and_risks completed in {elapsed:.3f}s, analyzed {len(asset_list)} assets")
        
        return {
            'assets': asset_list,
            'risk_summary': risk_summary
        }
        
    except Exception as e:
        print(f"[PERF] Error in get_balances_and_risks: {e}")
        import traceback
        traceback.print_exc()
        return {
            'assets': [],
            'risk_summary': {
                'status': 'error',
                'message': 'Error fetching balances. Check logs for details.'
            }
        }


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


@app.route('/api/balances')
def api_balances():
    """API endpoint for asset balances and risk analysis."""
    start_time = time.time()
    print(f"[PERF] /api/balances endpoint called at {datetime.now(timezone.utc).isoformat()}")
    result = jsonify(get_balances_and_risks())
    elapsed = time.time() - start_time
    print(f"[PERF] /api/balances endpoint completed in {elapsed:.3f}s")
    return result


@app.route('/api/status')
def api_status():
    """API endpoint for overall system status."""

# Summary of logical flow for dashboard endpoints
#
# 1. Config and state are loaded with configurable TTL cache (aligns with monitor interval)
# 2. Prices are fetched in batch and cached (aligns with monitor interval)
# 3. Open orders are fetched in one call and cached (aligns with monitor interval)
# 4. Closed orders are fetched in one call and cached (aligns with monitor interval)
# 5. All matching/filtering is done in memory (fast)
# 6. Dashboard JS preserves last known data if fetch fails or is slow
    return jsonify({
        'config_file': CONFIG_FILE,
        'state_file': STATE_FILE,
        'config_exists': os.path.exists(CONFIG_FILE),
        'state_exists': os.path.exists(STATE_FILE),
        'kraken_api_available': kraken_api is not None,
        'check_interval': CHECK_INTERVAL,
        'refresh_interval': DASHBOARD_REFRESH_INTERVAL,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@app.route('/api/pending/<config_id>/cancel', methods=['POST'])
def api_cancel_pending(config_id):
    """
    Cancel a pending order by setting its enabled status.
    
    Args:
        config_id: The ID of the config to cancel
        
    Request body:
        {
            "status": "paused" | "canceled" | "false"  # New enabled status
        }
    
    Returns:
        JSON response with success/error status
    """
    try:
        data = request.get_json() or {}
        new_status = data.get('status', 'canceled')
        
        # Validate status value
        valid_statuses = ['true', 'false', 'paused', 'canceled']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        # Update the config file
        config_manager.update_config_enabled(config_id, new_status)
        
        print(f"[DASHBOARD] Pending order {config_id} set to enabled={new_status}")
        
        return jsonify({
            'success': True,
            'config_id': config_id,
            'new_status': new_status
        })
        
    except Exception as e:
        print(f"[DASHBOARD] Error canceling pending order {config_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/active/<order_id>/cancel', methods=['POST'])
def api_cancel_active(order_id):
    """
    Cancel an active Kraken order.
    
    Args:
        order_id: Kraken order ID (txid) to cancel
    
    Returns:
        JSON response with success/error status
    """
    if not kraken_api:
        return jsonify({
            'success': False,
            'error': 'Kraken API not available'
        }), 503
    
    try:
        # Cancel the order via Kraken API
        result = kraken_api.cancel_order(order_id)
        
        print(f"[DASHBOARD] Active order {order_id} canceled: {result}")
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'result': result
        })
        
    except Exception as e:
        print(f"[DASHBOARD] Error canceling active order {order_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/cancel-all', methods=['POST'])
def api_cancel_all():
    """
    Cancel all active orders immediately.
    
    Returns:
        JSON response with success/error status and details
    """
    if not kraken_api:
        return jsonify({
            'success': False,
            'error': 'Kraken API not available'
        }), 503
    
    try:
        # Get all open orders
        open_orders_result = kraken_api.query_open_orders()
        open_orders = open_orders_result.get('open', {})
        
        if not open_orders:
            return jsonify({
                'success': True,
                'message': 'No active orders to cancel',
                'canceled_count': 0
            })
        
        # Cancel each order
        canceled = []
        failed = []
        
        for order_id in open_orders.keys():
            try:
                kraken_api.cancel_order(order_id)
                canceled.append(order_id)
                print(f"[DASHBOARD] Canceled order {order_id}")
            except Exception as e:
                failed.append({'order_id': order_id, 'error': str(e)})
                print(f"[DASHBOARD] Failed to cancel order {order_id}: {e}")
        
        return jsonify({
            'success': len(failed) == 0,
            'canceled_count': len(canceled),
            'failed_count': len(failed),
            'canceled_orders': canceled,
            'failed_orders': failed
        })
        
    except Exception as e:
        print(f"[DASHBOARD] Error in cancel-all: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
