"""Tests for profit tracking functionality."""
import os
import tempfile
import pytest
from decimal import Decimal

from profit_tracker import ProfitTracker


@pytest.fixture
def temp_trades_file():
    """Create a temporary trades file."""
    fd, path = tempfile.mkstemp(suffix='.csv')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_initialize_trades_file(temp_trades_file):
    """Test that trades file is initialized with correct headers."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    tracker.initialize_trades_file()
    
    assert os.path.exists(temp_trades_file)
    
    # Check headers
    with open(temp_trades_file, 'r') as f:
        header = f.readline().strip()
        assert 'trade_id' in header
        assert 'config_id' in header
        assert 'pair' in header
        assert 'profit_loss' in header
        assert 'status' in header


def test_record_order_trigger(temp_trades_file):
    """Test recording an order trigger."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    
    trade_id = tracker.record_order_trigger(
        config_id='test_config',
        pair='XXBTZUSD',
        direction='sell',
        volume=0.01,
        trigger_price=50000,
        trigger_time='2024-01-01T00:00:00'
    )
    
    assert trade_id is not None
    assert 'test_config' in trade_id
    
    # Read the file and verify
    import csv
    with open(temp_trades_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['config_id'] == 'test_config'
        assert rows[0]['pair'] == 'XXBTZUSD'
        assert rows[0]['direction'] == 'sell'
        assert rows[0]['status'] == 'triggered'


def test_record_order_fill_sell_profit(temp_trades_file):
    """Test recording an order fill for a sell order with profit."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    
    # Record trigger
    tracker.record_order_trigger(
        config_id='test_sell',
        pair='XXBTZUSD',
        direction='sell',
        volume=0.01,
        trigger_price=50000,  # Sell at 50000
        trigger_time='2024-01-01T00:00:00'
    )
    
    # Record fill at lower price (profit for sell)
    profit, profit_pct = tracker.record_order_fill(
        config_id='test_sell',
        fill_price=49000,  # Buy back at 49000
        fill_time='2024-01-01T01:00:00',
        order_id='TEST123'
    )
    
    # For sell: profit = (entry - exit) * volume = (50000 - 49000) * 0.01 = 10
    assert profit is not None
    assert profit == pytest.approx(10.0, rel=0.01)
    assert profit_pct == pytest.approx(2.0, rel=0.01)  # (1000/50000)*100 = 2%


def test_record_order_fill_sell_loss(temp_trades_file):
    """Test recording an order fill for a sell order with loss."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    
    # Record trigger
    tracker.record_order_trigger(
        config_id='test_sell_loss',
        pair='XXBTZUSD',
        direction='sell',
        volume=0.01,
        trigger_price=50000,  # Sell at 50000
        trigger_time='2024-01-01T00:00:00'
    )
    
    # Record fill at higher price (loss for sell)
    profit, profit_pct = tracker.record_order_fill(
        config_id='test_sell_loss',
        fill_price=51000,  # Buy back at 51000
        fill_time='2024-01-01T01:00:00',
        order_id='TEST124'
    )
    
    # For sell: profit = (entry - exit) * volume = (50000 - 51000) * 0.01 = -10
    assert profit is not None
    assert profit == pytest.approx(-10.0, rel=0.01)
    assert profit_pct == pytest.approx(-2.0, rel=0.01)


def test_record_order_fill_buy_profit(temp_trades_file):
    """Test recording an order fill for a buy order with profit."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    
    # Record trigger
    tracker.record_order_trigger(
        config_id='test_buy',
        pair='XXBTZUSD',
        direction='buy',
        volume=0.01,
        trigger_price=49000,  # Buy at 49000
        trigger_time='2024-01-01T00:00:00'
    )
    
    # Record fill at higher price (profit for buy)
    profit, profit_pct = tracker.record_order_fill(
        config_id='test_buy',
        fill_price=50000,  # Sell at 50000
        fill_time='2024-01-01T01:00:00',
        order_id='TEST125'
    )
    
    # For buy: profit = (exit - entry) * volume = (50000 - 49000) * 0.01 = 10
    assert profit is not None
    assert profit == pytest.approx(10.0, rel=0.01)
    assert profit_pct == pytest.approx(2.04, rel=0.01)  # (1000/49000)*100 ≈ 2.04%


def test_record_order_fill_buy_loss(temp_trades_file):
    """Test recording an order fill for a buy order with loss."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    
    # Record trigger
    tracker.record_order_trigger(
        config_id='test_buy_loss',
        pair='XXBTZUSD',
        direction='buy',
        volume=0.01,
        trigger_price=50000,  # Buy at 50000
        trigger_time='2024-01-01T00:00:00'
    )
    
    # Record fill at lower price (loss for buy)
    profit, profit_pct = tracker.record_order_fill(
        config_id='test_buy_loss',
        fill_price=49000,  # Sell at 49000
        fill_time='2024-01-01T01:00:00',
        order_id='TEST126'
    )
    
    # For buy: profit = (exit - entry) * volume = (49000 - 50000) * 0.01 = -10
    assert profit is not None
    assert profit == pytest.approx(-10.0, rel=0.01)
    assert profit_pct == pytest.approx(-2.0, rel=0.01)


def test_get_profit_summary_empty(temp_trades_file):
    """Test profit summary with no trades."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    
    summary = tracker.get_profit_summary()
    
    assert summary['total_trades'] == 0
    assert summary['completed_trades'] == 0
    assert summary['total_profit_loss'] == 0
    assert summary['win_rate'] == 0


def test_get_profit_summary_with_trades(temp_trades_file):
    """Test profit summary with multiple trades."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    
    # Record multiple trades
    # Profitable sell
    tracker.record_order_trigger('trade1', 'XXBTZUSD', 'sell', 0.01, 50000, '2024-01-01T00:00:00')
    tracker.record_order_fill('trade1', 49000, '2024-01-01T01:00:00', 'ORDER1')
    
    # Losing sell
    tracker.record_order_trigger('trade2', 'XXBTZUSD', 'sell', 0.01, 50000, '2024-01-01T02:00:00')
    tracker.record_order_fill('trade2', 51000, '2024-01-01T03:00:00', 'ORDER2')
    
    # Profitable buy
    tracker.record_order_trigger('trade3', 'XXBTZUSD', 'buy', 0.01, 49000, '2024-01-01T04:00:00')
    tracker.record_order_fill('trade3', 50000, '2024-01-01T05:00:00', 'ORDER3')
    
    # Pending trade
    tracker.record_order_trigger('trade4', 'XXBTZUSD', 'buy', 0.01, 48000, '2024-01-01T06:00:00')
    
    summary = tracker.get_profit_summary()
    
    assert summary['total_trades'] == 4
    assert summary['completed_trades'] == 3
    assert summary['triggered_trades'] == 1
    assert summary['profitable_trades'] == 2
    assert summary['losing_trades'] == 1
    assert summary['win_rate'] == pytest.approx(66.67, rel=0.1)
    # Total P&L: +10 (sell) -10 (sell) +10 (buy) = +10
    assert summary['total_profit_loss'] == pytest.approx(10.0, rel=0.01)


def test_fill_without_trigger(temp_trades_file):
    """Test recording a fill without a prior trigger."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    
    # Try to record fill without trigger
    profit, profit_pct = tracker.record_order_fill(
        config_id='no_trigger',
        fill_price=50000,
        fill_time='2024-01-01T00:00:00',
        order_id='ORDER123'
    )
    
    # Should return None for profit since no entry found
    assert profit is None
    assert profit_pct is None
    
    # But should still record the fill
    import csv
    with open(temp_trades_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['status'] == 'filled_only'


def test_multiple_configs(temp_trades_file):
    """Test tracking multiple configs independently."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    
    # Create two separate trades
    tracker.record_order_trigger('config1', 'XXBTZUSD', 'sell', 0.01, 50000, '2024-01-01T00:00:00')
    tracker.record_order_trigger('config2', 'XETHZUSD', 'buy', 0.1, 3000, '2024-01-01T00:00:00')
    
    # Fill config1
    profit1, _ = tracker.record_order_fill('config1', 49000, '2024-01-01T01:00:00', 'ORDER1')
    
    # Fill config2
    profit2, _ = tracker.record_order_fill('config2', 3100, '2024-01-01T01:00:00', 'ORDER2')
    
    assert profit1 is not None
    assert profit2 is not None
    assert profit1 == pytest.approx(10.0, rel=0.01)
    assert profit2 == pytest.approx(10.0, rel=0.01)


def test_print_summary_no_crash(temp_trades_file):
    """Test that print_summary doesn't crash."""
    tracker = ProfitTracker(trades_file=temp_trades_file)
    
    # Should work with empty file
    tracker.print_summary()
    
    # Add some trades and test again
    tracker.record_order_trigger('trade1', 'XXBTZUSD', 'sell', 0.01, 50000, '2024-01-01T00:00:00')
    tracker.record_order_fill('trade1', 49000, '2024-01-01T01:00:00', 'ORDER1')
    
    tracker.print_summary()
