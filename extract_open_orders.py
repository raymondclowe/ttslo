#!/usr/bin/env python3
"""
Extract Open Orders Utility

Queries Kraken API for open orders, filters for trailing-stop orders only,
and outputs them in the same CSV format as config.csv for easy comparison.

Usage:
    python extract_open_orders.py
    python extract_open_orders.py --output-file open_orders.csv
"""

import argparse
import csv
import sys
from kraken_api import KrakenAPI
from creds import load_env


def extract_trailing_stop_orders(api):
    """
    Query Kraken API for open orders and filter trailing-stop orders.
    
    Args:
        api: KrakenAPI instance
        
    Returns:
        List of dictionaries containing order information
    """
    try:
        result = api.query_open_orders()
    except Exception as e:
        print(f"Error querying open orders: {e}", file=sys.stderr)
        return []
    
    # query_open_orders() returns the 'result' dict which contains 'open'
    open_orders = result.get('open', {})
    trailing_stop_orders = []
    
    for order_id, order_data in open_orders.items():
        # Get order description
        descr = order_data.get('descr', {})
        ordertype = descr.get('ordertype', '')
        
        # Filter for trailing-stop orders only
        if ordertype != 'trailing-stop':
            continue
        
        # Extract order details
        pair = descr.get('pair', '')
        direction = descr.get('type', '')  # 'buy' or 'sell'
        volume = order_data.get('vol', '')
        
        # Extract trailing offset from price field
        # Format is like "+5.0000%" or "-5.0000%"
        price_str = descr.get('price', '')
        trailing_offset_percent = ''
        if price_str:
            # Remove '+', '-', and '%' to get the numeric value
            trailing_offset_percent = price_str.replace('+', '').replace('-', '').replace('%', '').strip()
        
        # Map to config.csv format
        order_info = {
            'id': order_id,  # Use Kraken order ID as the id
            'pair': pair,
            'threshold_price': '',  # Not available in open orders - these are trigger conditions
            'threshold_type': '',   # Not available in open orders
            'direction': direction,
            'volume': volume,
            'trailing_offset_percent': trailing_offset_percent,
            'enabled': 'false'  # If it's open, it has already been triggered
        }
        
        trailing_stop_orders.append(order_info)
    
    return trailing_stop_orders


def output_as_csv(orders, output_file=None):
    """
    Output orders in config.csv format.
    
    Args:
        orders: List of order dictionaries
        output_file: Optional file path to write to (default: stdout)
    """
    fieldnames = ['id', 'pair', 'threshold_price', 'threshold_type', 'direction', 
                  'volume', 'trailing_offset_percent', 'enabled']
    
    if output_file:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for order in orders:
                writer.writerow(order)
        print(f"Wrote {len(orders)} trailing-stop orders to {output_file}", file=sys.stderr)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        for order in orders:
            writer.writerow(order)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Extract open trailing-stop orders from Kraken API and output in config.csv format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Output to stdout
  python extract_open_orders.py
  
  # Save to file
  python extract_open_orders.py --output-file open_orders.csv
  
  # Compare with config.csv
  python extract_open_orders.py > open_orders.csv
  diff config.csv open_orders.csv
        """
    )
    
    parser.add_argument(
        '--output-file', '-o',
        help='Write output to file instead of stdout'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_env()
    
    # Initialize Kraken API
    # Try read-write credentials first (for full order access), fallback to read-only
    try:
        api = KrakenAPI.from_env(readwrite=True)
    except Exception as e:
        print(f"Warning: Could not load read-write credentials, trying read-only: {e}", file=sys.stderr)
        try:
            api = KrakenAPI.from_env(readwrite=False)
        except Exception as e:
            print(f"Error: Could not initialize Kraken API: {e}", file=sys.stderr)
            print("Please ensure KRAKEN_API_KEY and KRAKEN_API_SECRET are set", file=sys.stderr)
            sys.exit(1)
    
    # Extract trailing-stop orders
    orders = extract_trailing_stop_orders(api)
    
    if not orders:
        print("No open trailing-stop orders found", file=sys.stderr)
    
    # Output as CSV
    output_as_csv(orders, args.output_file)


if __name__ == '__main__':
    main()
