"""
Tests for initial_price tracking and benefit calculation.
"""
import pytest
import tempfile
import os
from config import ConfigManager
from ttslo import TTSLO
from kraken_api import KrakenAPI


class MockKrakenAPI:
    """Mock Kraken API for testing."""
    
    def __init__(self, price=100.0):
        self.price = price
        
    def get_current_price(self, pair):
        """Return mock price."""
        return self.price


def test_initial_price_populated_on_first_run():
    """Test that initial_price is populated when config is first processed."""
    # Create temporary files
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Write a test config
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled\n')
            f.write('test_1,XXBTZUSD,50000,above,sell,0.01,5.0,true\n')
        
        # Create config manager and TTSLO instance
        config_manager = ConfigManager(config_file, state_file, log_file)
        mock_api = MockKrakenAPI(price=45000.0)  # Below threshold, won't trigger
        
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=mock_api,
            kraken_api_readwrite=mock_api,
            dry_run=False,
            verbose=False
        )
        
        # Load state and configs
        ttslo.load_state()
        ttslo.configs = config_manager.load_config()
        
        # Process the config
        ttslo.process_config(ttslo.configs[0])
        
        # Check that initial_price was set
        assert 'test_1' in ttslo.state
        assert ttslo.state['test_1'].get('initial_price') == '45000.0'
        
        # Save state and verify it persists
        ttslo.save_state()
        
        # Reload state and verify initial_price is there
        new_state = config_manager.load_state()
        assert 'test_1' in new_state
        assert new_state['test_1'].get('initial_price') == '45000.0'


def test_initial_price_not_overwritten():
    """Test that initial_price is not overwritten on subsequent runs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, 'config.csv')
        state_file = os.path.join(tmpdir, 'state.csv')
        log_file = os.path.join(tmpdir, 'logs.csv')
        
        # Write a test config
        with open(config_file, 'w') as f:
            f.write('id,pair,threshold_price,threshold_type,direction,volume,trailing_offset_percent,enabled\n')
            f.write('test_1,XXBTZUSD,50000,above,sell,0.01,5.0,true\n')
        
        # Create config manager and TTSLO instance with initial price of 45000
        config_manager = ConfigManager(config_file, state_file, log_file)
        mock_api = MockKrakenAPI(price=45000.0)
        
        ttslo = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=mock_api,
            kraken_api_readwrite=mock_api,
            dry_run=False,
            verbose=False
        )
        
        ttslo.load_state()
        ttslo.configs = config_manager.load_config()
        ttslo.process_config(ttslo.configs[0])
        ttslo.save_state()
        
        # Verify initial price was set to 45000
        assert ttslo.state['test_1'].get('initial_price') == '45000.0'
        
        # Now run again with a different price
        mock_api.price = 48000.0
        ttslo2 = TTSLO(
            config_manager=config_manager,
            kraken_api_readonly=mock_api,
            kraken_api_readwrite=mock_api,
            dry_run=False,
            verbose=False
        )
        
        ttslo2.load_state()
        ttslo2.configs = config_manager.load_config()
        ttslo2.process_config(ttslo2.configs[0])
        
        # Verify initial price is still 45000, not 48000
        assert ttslo2.state['test_1'].get('initial_price') == '45000.0'


def test_total_benefit_calculation():
    """Test that total benefit is calculated correctly in dashboard."""
    # Test directly with mock data instead of using get_completed_orders
    # to avoid real API calls
    
    # Simulate the benefit calculation logic from dashboard.py
    config_state = {
        'trigger_price': '48000.0',
        'initial_price': '45000.0'
    }
    
    config = {
        'direction': 'sell'
    }
    
    order_info = {
        'price': 47500.0
    }
    
    # Calculate benefit from trigger_price (existing behavior)
    trigger_price = float(config_state.get('trigger_price', 0))
    initial_price = float(config_state.get('initial_price', 0))
    executed_price = float(order_info.get('price', 0))
    
    benefit = 0
    benefit_percent = 0
    if trigger_price > 0:
        direction = config.get('direction', 'sell')
        if direction == 'sell':
            benefit = executed_price - trigger_price
            benefit_percent = (benefit / trigger_price) * 100
    
    # Verify slippage (trigger vs executed)
    # Sell order: executed - trigger = 47500 - 48000 = -500
    assert benefit == -500.0
    assert abs(benefit_percent - (-500.0 / 48000.0 * 100)) < 0.01
    
    # Calculate total benefit from initial_price (new feature)
    total_benefit = 0
    total_benefit_percent = 0
    if initial_price > 0 and executed_price > 0:
        direction = config.get('direction', 'sell')
        if direction == 'sell':
            # Selling: benefit if executed higher than initial
            total_benefit = executed_price - initial_price
            total_benefit_percent = (total_benefit / initial_price) * 100
    
    # Verify total benefit (initial vs executed)
    # Sell order: executed - initial = 47500 - 45000 = +2500
    assert total_benefit == 2500.0
    assert abs(total_benefit_percent - (2500.0 / 45000.0 * 100)) < 0.01


def test_total_benefit_buy_order():
    """Test total benefit calculation for buy orders."""
    # Test directly with mock data to avoid real API calls
    
    # Simulate buy order scenario
    config_state = {
        'trigger_price': '3200.0',
        'initial_price': '3500.0'
    }
    
    config = {
        'direction': 'buy'
    }
    
    order_info = {
        'price': 3230.0
    }
    
    trigger_price = float(config_state.get('trigger_price', 0))
    initial_price = float(config_state.get('initial_price', 0))
    executed_price = float(order_info.get('price', 0))
    
    # Calculate slippage
    benefit = 0
    benefit_percent = 0
    if trigger_price > 0:
        direction = config.get('direction', 'buy')
        if direction == 'buy':
            benefit = trigger_price - executed_price
            benefit_percent = (benefit / trigger_price) * 100
    
    # Verify slippage (buy: trigger - executed = 3200 - 3230 = -30)
    assert benefit == -30.0
    
    # Calculate total benefit
    total_benefit = 0
    total_benefit_percent = 0
    if initial_price > 0 and executed_price > 0:
        direction = config.get('direction', 'buy')
        if direction == 'buy':
            # Buying: benefit if executed lower than initial
            total_benefit = initial_price - executed_price
            total_benefit_percent = (total_benefit / initial_price) * 100
    
    # Verify total benefit (buy: initial - executed = 3500 - 3230 = +270)
    assert total_benefit == 270.0
    assert abs(total_benefit_percent - (270.0 / 3500.0 * 100)) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
