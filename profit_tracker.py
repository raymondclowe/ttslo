"""
Profit tracking and reporting for TTSLO trades.

Records executed trades with entry/exit prices and calculates profit/loss.
"""
import csv
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, getcontext


class ProfitTracker:
    """Track and report profits from executed trades."""
    
    def __init__(self, trades_file='trades.csv'):
        """
        Initialize profit tracker.
        
        Args:
            trades_file: Path to trades CSV file
        """
        self.trades_file = trades_file
        getcontext().prec = 28  # High precision for financial calculations
    
    def initialize_trades_file(self):
        """Initialize trades file with headers if it doesn't exist."""
        # Check if file already has proper header
        if os.path.exists(self.trades_file) and os.path.getsize(self.trades_file) > 0:
            try:
                with open(self.trades_file, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames and 'trade_id' in reader.fieldnames:
                        return  # File is properly initialized
            except Exception:
                pass  # If error reading, reinitialize
        
        fieldnames = [
            'trade_id',
            'config_id',
            'pair',
            'direction',
            'volume',
            'entry_price',
            'exit_price',
            'entry_time',
            'exit_time',
            'profit_loss',
            'profit_loss_pct',
            'status',
            'notes'
        ]
        
        with open(self.trades_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
    
    def record_order_trigger(self, config_id, pair, direction, volume, trigger_price, trigger_time):
        """
        Record an order trigger (potential trade entry).
        
        Args:
            config_id: Configuration ID
            pair: Trading pair
            direction: Order direction (buy/sell)
            volume: Trade volume
            trigger_price: Price at trigger
            trigger_time: Trigger timestamp
        """
        self.initialize_trades_file()
        
        # Generate trade ID from config_id and timestamp
        trade_id = f"{config_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        # Write trade entry
        fieldnames = [
            'trade_id', 'config_id', 'pair', 'direction', 'volume',
            'entry_price', 'exit_price', 'entry_time', 'exit_time',
            'profit_loss', 'profit_loss_pct', 'status', 'notes'
        ]
        
        row = {
            'trade_id': trade_id,
            'config_id': config_id,
            'pair': pair,
            'direction': direction,
            'volume': str(volume),
            'entry_price': str(trigger_price),
            'exit_price': '',
            'entry_time': trigger_time,
            'exit_time': '',
            'profit_loss': '',
            'profit_loss_pct': '',
            'status': 'triggered',
            'notes': 'Order created, awaiting fill'
        }
        
        with open(self.trades_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(row)
        
        return trade_id
    
    def record_order_fill(self, config_id, fill_price, fill_time, order_id=None):
        """
        Record an order fill (trade completion).
        
        Updates the trade record with exit price and calculates profit.
        
        Args:
            config_id: Configuration ID
            fill_price: Price at fill
            fill_time: Fill timestamp
            order_id: Kraken order ID (optional)
        
        Returns:
            Tuple of (profit_loss, profit_loss_pct) or (None, None) if trade not found
        """
        self.initialize_trades_file()
        
        if not os.path.exists(self.trades_file):
            return None, None
        
        # Read all trades
        trades = []
        fieldnames = None
        with open(self.trades_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            trades = list(reader)
        
        if not fieldnames:
            return None, None
        
        # Find the most recent triggered trade for this config
        trade_found = False
        for trade in reversed(trades):
            if trade.get('config_id') == config_id and trade.get('status') == 'triggered':
                # Calculate profit
                try:
                    entry_price = Decimal(str(trade.get('entry_price', '0')))
                    exit_price = Decimal(str(fill_price))
                    volume = Decimal(str(trade.get('volume', '0')))
                    direction = trade.get('direction', '').lower()
                    
                    if entry_price > 0 and volume > 0:
                        # Calculate profit based on direction
                        if direction == 'sell':
                            # For sell: profit = (entry - exit) * volume
                            # Sell at entry, buy back at exit
                            profit_loss = (entry_price - exit_price) * volume
                            profit_loss_pct = ((entry_price - exit_price) / entry_price) * Decimal('100')
                        else:  # buy
                            # For buy: profit = (exit - entry) * volume
                            # Buy at entry, sell at exit
                            profit_loss = (exit_price - entry_price) * volume
                            profit_loss_pct = ((exit_price - entry_price) / entry_price) * Decimal('100')
                        
                        # Update trade record
                        trade['exit_price'] = str(fill_price)
                        trade['exit_time'] = fill_time
                        trade['profit_loss'] = str(profit_loss)
                        trade['profit_loss_pct'] = str(profit_loss_pct)
                        trade['status'] = 'completed'
                        trade['notes'] = f'Order filled. Order ID: {order_id}' if order_id else 'Order filled'
                        
                        trade_found = True
                        
                        # Write updated trades
                        with open(self.trades_file, 'w', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(trades)
                        
                        return float(profit_loss), float(profit_loss_pct)
                    
                except (ValueError, InvalidOperation, ZeroDivisionError) as e:
                    print(f"Error calculating profit for trade {config_id}: {e}")
                    return None, None
                
                break
        
        if not trade_found:
            # No triggered trade found, might be a standalone fill
            # Record as completed trade with unknown entry
            trade_id = f"{config_id}_fill_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            
            # Build row matching fieldnames
            row = {}
            for field in fieldnames:
                row[field] = ''
            
            # Fill in known values
            row['trade_id'] = trade_id
            row['config_id'] = config_id
            row['exit_price'] = str(fill_price)
            row['exit_time'] = fill_time
            row['status'] = 'filled_only'
            row['notes'] = f'Order filled without tracked entry. Order ID: {order_id}' if order_id else 'Order filled without tracked entry'
            
            with open(self.trades_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(row)
        
        return None, None
    
    def get_profit_summary(self):
        """
        Generate profit summary statistics.
        
        Returns:
            Dictionary with profit statistics
        """
        if not os.path.exists(self.trades_file):
            return {
                'total_trades': 0,
                'completed_trades': 0,
                'triggered_trades': 0,
                'total_profit_loss': 0,
                'total_profit_loss_pct': 0,
                'profitable_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
            }
        
        trades = []
        with open(self.trades_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            trades = list(reader)
        
        total_trades = len(trades)
        completed_trades = [t for t in trades if t.get('status') == 'completed']
        triggered_trades = [t for t in trades if t.get('status') == 'triggered']
        
        profits = []
        losses = []
        
        for trade in completed_trades:
            try:
                profit = Decimal(str(trade.get('profit_loss', '0')))
                if profit > 0:
                    profits.append(profit)
                elif profit < 0:
                    losses.append(abs(profit))
            except (ValueError, InvalidOperation):
                continue
        
        total_profit_loss = sum(profits) - sum(losses)
        profitable_count = len(profits)
        losing_count = len(losses)
        
        return {
            'total_trades': total_trades,
            'completed_trades': len(completed_trades),
            'triggered_trades': len(triggered_trades),
            'total_profit_loss': float(total_profit_loss),
            'profitable_trades': profitable_count,
            'losing_trades': losing_count,
            'win_rate': (profitable_count / len(completed_trades) * 100) if completed_trades else 0,
            'avg_profit': float(sum(profits) / len(profits)) if profits else 0,
            'avg_loss': float(sum(losses) / len(losses)) if losses else 0,
            'largest_win': float(max(profits)) if profits else 0,
            'largest_loss': float(max(losses)) if losses else 0,
        }
    
    def print_summary(self):
        """Print profit summary to console."""
        summary = self.get_profit_summary()
        
        print("\n" + "="*70)
        print("PROFIT SUMMARY REPORT")
        print("="*70)
        print(f"Total Trades: {summary['total_trades']}")
        print(f"  - Completed: {summary['completed_trades']}")
        print(f"  - Triggered (Pending): {summary['triggered_trades']}")
        print()
        print(f"Total P&L: ${summary['total_profit_loss']:,.2f}")
        print()
        print(f"Profitable Trades: {summary['profitable_trades']}")
        print(f"Losing Trades: {summary['losing_trades']}")
        print(f"Win Rate: {summary['win_rate']:.1f}%")
        print()
        print(f"Average Profit: ${summary['avg_profit']:,.2f}")
        print(f"Average Loss: ${summary['avg_loss']:,.2f}")
        print(f"Largest Win: ${summary['largest_win']:,.2f}")
        print(f"Largest Loss: ${summary['largest_loss']:,.2f}")
        print("="*70)
