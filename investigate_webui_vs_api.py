#!/usr/bin/env python3
"""
Investigation: What price does Kraken Web UI show vs REST API 'c' field?

This script investigates the difference between:
1. REST API 'c' field (last trade closed) - what TTSLO uses
2. REST API 'a' field (best ask price) - order book
3. REST API 'b' field (best bid price) - order book

The Kraken web UI shows the "current price" which may be different from
the last executed trade price.
"""
import time
import json
from datetime import datetime, timezone
from kraken_api import KrakenAPI


def investigate_all_ticker_fields(pair='XXBTZUSD', num_samples=30, interval=1):
    """
    Poll all ticker fields every second to see which ones update frequently.
    
    This will help us understand what the Kraken web UI is actually showing.
    """
    print("="*80)
    print(f"Investigating ALL Ticker Fields for {pair}")
    print("="*80)
    print(f"Samples: {num_samples}, Interval: {interval} second(s)")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("="*80)
    print()
    
    print("Field Descriptions:")
    print("  'a' = Ask (best ask price in order book) [price, whole lot vol, lot vol]")
    print("  'b' = Bid (best bid price in order book) [price, whole lot vol, lot vol]")
    print("  'c' = Last trade closed [price, lot volume]")
    print("  'v' = Volume [today, last 24 hours]")
    print("  'p' = VWAP [today, last 24 hours]")
    print("  't' = Number of trades [today, last 24 hours]")
    print()
    print("KEY INSIGHT:")
    print("  - The Kraken WEB UI likely shows 'a' (ask) or 'b' (bid) or midpoint")
    print("  - These update when ORDER BOOK changes (orders placed/cancelled)")
    print("  - The 'c' field only updates when TRADES execute")
    print("  - Order book changes are MUCH more frequent than trades!")
    print()
    
    api = KrakenAPI()
    samples = []
    
    for i in range(num_samples):
        try:
            timestamp = datetime.now(timezone.utc)
            ticker = api.get_ticker(pair)
            
            # Extract the ticker data for the pair
            pair_data = None
            for key, value in ticker.items():
                if isinstance(value, dict):
                    pair_data = value
                    break
            
            if pair_data:
                # Extract all relevant fields
                last_trade = pair_data.get('c', ['N/A', 'N/A'])
                ask = pair_data.get('a', ['N/A', 'N/A', 'N/A'])
                bid = pair_data.get('b', ['N/A', 'N/A', 'N/A'])
                
                sample = {
                    'timestamp': timestamp,
                    'last_trade_price': last_trade[0] if isinstance(last_trade, list) else 'N/A',
                    'ask_price': ask[0] if isinstance(ask, list) else 'N/A',
                    'bid_price': bid[0] if isinstance(bid, list) else 'N/A',
                }
                
                # Calculate midpoint (what many UIs show as "current price")
                if sample['ask_price'] != 'N/A' and sample['bid_price'] != 'N/A':
                    try:
                        midpoint = (float(sample['ask_price']) + float(sample['bid_price'])) / 2
                        sample['midpoint'] = f"{midpoint:.2f}"
                    except:
                        sample['midpoint'] = 'N/A'
                else:
                    sample['midpoint'] = 'N/A'
                
                samples.append(sample)
                
                # Print the sample
                time_str = timestamp.strftime('%H:%M:%S')
                print(f"[{i+1:2d}] {time_str} | "
                      f"Last Trade: ${sample['last_trade_price']:>10} | "
                      f"Bid: ${sample['bid_price']:>10} | "
                      f"Ask: ${sample['ask_price']:>10} | "
                      f"Midpoint: ${sample['midpoint']:>10}")
            
            if i < num_samples - 1:
                time.sleep(interval)
                
        except Exception as e:
            print(f"[{i+1:2d}] ERROR: {e}")
            if i < num_samples - 1:
                time.sleep(interval)
    
    print()
    print("="*80)
    print("Analysis: Which Fields Change Frequently?")
    print("="*80)
    
    if len(samples) > 1:
        # Count changes for each field
        last_trade_changes = 0
        bid_changes = 0
        ask_changes = 0
        midpoint_changes = 0
        
        for i in range(1, len(samples)):
            if samples[i]['last_trade_price'] != samples[i-1]['last_trade_price']:
                last_trade_changes += 1
            if samples[i]['bid_price'] != samples[i-1]['bid_price']:
                bid_changes += 1
            if samples[i]['ask_price'] != samples[i-1]['ask_price']:
                ask_changes += 1
            if samples[i]['midpoint'] != samples[i-1]['midpoint']:
                midpoint_changes += 1
        
        total_transitions = len(samples) - 1
        
        print(f"Total samples: {len(samples)}")
        print(f"Total transitions: {total_transitions}")
        print()
        print(f"Last Trade Price ('c') changed: {last_trade_changes} times ({last_trade_changes/total_transitions*100:.1f}%)")
        print(f"Bid Price ('b') changed:         {bid_changes} times ({bid_changes/total_transitions*100:.1f}%)")
        print(f"Ask Price ('a') changed:         {ask_changes} times ({ask_changes/total_transitions*100:.1f}%)")
        print(f"Midpoint (bid+ask)/2 changed:    {midpoint_changes} times ({midpoint_changes/total_transitions*100:.1f}%)")
        print()
        
        print("="*80)
        print("CONCLUSION")
        print("="*80)
        print()
        
        if bid_changes > last_trade_changes * 2 or ask_changes > last_trade_changes * 2:
            print("✓ BID/ASK prices change MUCH MORE FREQUENTLY than last trade price")
            print("✓ This explains why Kraken web UI appears to update constantly")
            print()
            print("EXPLANATION:")
            print("  1. Kraken WEB UI likely shows BID, ASK, or MIDPOINT price")
            print("  2. These update when orders are placed/cancelled in the order book")
            print("  3. Order book changes happen MULTIPLE TIMES PER SECOND")
            print("  4. This is NOT the same as the last executed TRADE price")
            print()
            print("WHAT TTSLO USES vs WHAT WEB UI SHOWS:")
            print("  - TTSLO: Last trade price ('c' field) - actual executed trades")
            print("  - Web UI: Likely bid/ask/midpoint - order book prices")
            print()
            print("WHY THIS MATTERS:")
            print("  - Last trade = actual market price (what trades executed at)")
            print("  - Bid/ask = pending orders (not executed yet)")
            print("  - For position management, last trade is more accurate")
            print("  - For real-time display, bid/ask gives illusion of constant movement")
        else:
            print("During this test period, all fields updated at similar rates")
            print("This may indicate very active trading")
        
        print()
        print("="*80)
        print("RECOMMENDATION")
        print("="*80)
        print()
        print("If you want price updates similar to Kraken web UI:")
        print("  1. Use WebSocket API for real-time order book updates")
        print("  2. Subscribe to 'book' or 'spread' channel (not just 'ticker')")
        print("  3. Display bid, ask, or midpoint instead of last trade")
        print()
        print("However, for TTSLO's use case (trigger monitoring):")
        print("  - Using last trade price is CORRECT")
        print("  - It represents actual market execution prices")
        print("  - Trigger thresholds should be based on executed trades")
        print("  - Not on pending orders in the order book")


if __name__ == "__main__":
    import sys
    
    # Default to 30 samples at 1 second intervals (30 seconds total)
    num_samples = 30
    interval = 1
    
    if len(sys.argv) > 1:
        try:
            num_samples = int(sys.argv[1])
        except ValueError:
            print(f"Invalid number of samples: {sys.argv[1]}")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            interval = int(sys.argv[2])
        except ValueError:
            print(f"Invalid interval: {sys.argv[2]}")
            sys.exit(1)
    
    print()
    print("This test will help explain why Kraken web UI updates constantly")
    print("while TTSLO sees the same price for multiple cycles.")
    print()
    input("Press Enter to start the test...")
    print()
    
    investigate_all_ticker_fields(num_samples=num_samples, interval=interval)
