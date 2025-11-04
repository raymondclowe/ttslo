#!/usr/bin/env python3
"""
Profit Report Tool

Generates executive summary reports of trading profits and losses.
Shows profits attempted, profits made, and detailed trade statistics.
"""
import sys
import os
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, getcontext

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from profit_tracker import ProfitTracker


def format_currency(value):
    """Format currency value with appropriate precision."""
    if abs(value) >= 1000:
        return f"${value:,.2f}"
    elif abs(value) >= 1:
        return f"${value:.2f}"
    elif abs(value) >= 0.01:
        return f"${value:.4f}"
    else:
        return f"${value:.8f}"


def print_detailed_trades(trades_file):
    """Print detailed trade history."""
    if not os.path.exists(trades_file):
        print("\nNo trades found.\n")
        return
    
    trades = []
    with open(trades_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        trades = list(reader)
    
    if not trades:
        print("\nNo trades found.\n")
        return
    
    print("\n" + "="*120)
    print("DETAILED TRADE HISTORY")
    print("="*120)
    
    # Header
    print(f"{'Trade ID':<30} {'Pair':<12} {'Dir':<5} {'Volume':<12} {'Entry $':<12} {'Exit $':<12} {'P&L $':<12} {'P&L %':<10} {'Status':<12}")
    print("-"*120)
    
    # Sort by entry time
    sorted_trades = sorted(trades, key=lambda t: t.get('entry_time', ''), reverse=True)
    
    for trade in sorted_trades:
        trade_id = trade.get('trade_id', '')[:28]
        pair = trade.get('pair', '')[:10]
        direction = trade.get('direction', '')[:4]
        volume = trade.get('volume', '')[:10]
        entry_price = trade.get('entry_price', '')[:10]
        exit_price = trade.get('exit_price', '')[:10]
        profit_loss = trade.get('profit_loss', '')
        profit_loss_pct = trade.get('profit_loss_pct', '')
        status = trade.get('status', '')[:10]
        
        # Format profit/loss with color indicators
        pl_str = ''
        pct_str = ''
        if profit_loss and status == 'completed':
            try:
                pl_val = float(profit_loss)
                pct_val = float(profit_loss_pct)
                pl_indicator = '✓' if pl_val > 0 else '✗' if pl_val < 0 else '='
                pl_str = f"{pl_indicator} {format_currency(pl_val)}"
                pct_str = f"{pct_val:+.2f}%"
            except (ValueError, InvalidOperation):
                pl_str = profit_loss[:10]
                pct_str = profit_loss_pct[:8]
        
        print(f"{trade_id:<30} {pair:<12} {direction:<5} {volume:<12} {entry_price:<12} {exit_price:<12} {pl_str:<12} {pct_str:<10} {status:<12}")
    
    print("="*120)


def print_profit_by_pair(trades_file):
    """Print profit summary grouped by trading pair."""
    if not os.path.exists(trades_file):
        return
    
    trades = []
    with open(trades_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        trades = list(reader)
    
    # Group by pair
    pair_stats = {}
    for trade in trades:
        if trade.get('status') != 'completed':
            continue
        
        pair = trade.get('pair', 'Unknown')
        profit_loss = trade.get('profit_loss', '0')
        
        try:
            pl = Decimal(profit_loss)
        except (ValueError, InvalidOperation):
            continue
        
        if pair not in pair_stats:
            pair_stats[pair] = {
                'count': 0,
                'profit': Decimal('0'),
                'wins': 0,
                'losses': 0
            }
        
        pair_stats[pair]['count'] += 1
        pair_stats[pair]['profit'] += pl
        if pl > 0:
            pair_stats[pair]['wins'] += 1
        elif pl < 0:
            pair_stats[pair]['losses'] += 1
    
    if not pair_stats:
        return
    
    print("\n" + "="*80)
    print("PROFIT BY TRADING PAIR")
    print("="*80)
    print(f"{'Pair':<15} {'Trades':<10} {'Wins':<8} {'Losses':<10} {'Total P&L':<15} {'Avg P&L':<15}")
    print("-"*80)
    
    # Sort by profit
    sorted_pairs = sorted(pair_stats.items(), key=lambda x: x[1]['profit'], reverse=True)
    
    for pair, stats in sorted_pairs:
        count = stats['count']
        profit = float(stats['profit'])
        wins = stats['wins']
        losses = stats['losses']
        avg = profit / count if count > 0 else 0
        
        print(f"{pair:<15} {count:<10} {wins:<8} {losses:<10} {format_currency(profit):<15} {format_currency(avg):<15}")
    
    print("="*80)


def print_performance_metrics(tracker):
    """Print advanced performance metrics."""
    summary = tracker.get_profit_summary()
    
    if summary['completed_trades'] == 0:
        return
    
    print("\n" + "="*70)
    print("PERFORMANCE METRICS")
    print("="*70)
    
    # Calculate additional metrics
    total_pl = summary['total_profit_loss']
    avg_win = summary['avg_profit']
    avg_loss = summary['avg_loss']
    win_rate = summary['win_rate']
    
    # Profit factor: ratio of gross profit to gross loss
    total_profit = avg_win * summary['profitable_trades']
    total_loss = avg_loss * summary['losing_trades']
    profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
    
    # Expected value per trade
    expected_value = total_pl / summary['completed_trades'] if summary['completed_trades'] > 0 else 0
    
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Expected Value per Trade: {format_currency(expected_value)}")
    print(f"Risk/Reward Ratio: {abs(avg_win/avg_loss):.2f}" if avg_loss > 0 else "Risk/Reward Ratio: N/A")
    print("="*70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Profit Report - Generate executive summary of trading profits',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate profit summary report
  %(prog)s
  
  # Specify custom trades file
  %(prog)s --trades-file /path/to/trades.csv
  
  # Show detailed trade history
  %(prog)s --detailed
  
  # Show profit by trading pair
  %(prog)s --by-pair
        """
    )
    
    parser.add_argument('--trades-file', default='trades.csv',
                       help='Path to trades CSV file (default: trades.csv)')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed trade history')
    parser.add_argument('--by-pair', action='store_true',
                       help='Show profit grouped by trading pair')
    parser.add_argument('--metrics', action='store_true',
                       help='Show advanced performance metrics')
    parser.add_argument('--all', action='store_true',
                       help='Show all reports (summary + detailed + by-pair + metrics)')
    
    args = parser.parse_args()
    
    # Check if trades file exists
    if not os.path.exists(args.trades_file):
        print(f"Error: Trades file not found: {args.trades_file}", file=sys.stderr)
        print("\nNo trades have been recorded yet.", file=sys.stderr)
        print("Trades will be recorded when TTSLO orders are triggered and filled.", file=sys.stderr)
        sys.exit(1)
    
    # Initialize profit tracker
    tracker = ProfitTracker(trades_file=args.trades_file)
    
    # Print summary (always shown)
    tracker.print_summary()
    
    # Print optional reports
    if args.all or args.detailed:
        print_detailed_trades(args.trades_file)
    
    if args.all or args.by_pair:
        print_profit_by_pair(args.trades_file)
    
    if args.all or args.metrics:
        print_performance_metrics(tracker)
    
    # If no optional flags, suggest using them
    if not (args.detailed or args.by_pair or args.metrics or args.all):
        print("\nTip: Use --detailed, --by-pair, --metrics, or --all for more details")


if __name__ == '__main__':
    main()
