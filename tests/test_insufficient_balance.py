"""
Tests for insufficient balance detection and notification.
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from ttslo import TTSLO
from config import ConfigManager
from notifications import NotificationManager


class MockKrakenAPI:
    """Mock Kraken API for testing."""
    
    def __init__(self, balance=None, add_order_error=None):
        """
        Initialize mock API.
        
        Args:
            balance: Balance to return from get_balance() and get_normalized_balances()
            add_order_error: Exception to raise from add_trailing_stop_loss()
        """
        self.balance = balance or {}
        self.add_order_error = add_order_error
        self.add_order_calls = []
    
    def get_balance(self):
        """Return mock balance."""
        return self.balance
    
    def get_normalized_balances(self):
        """Return mock normalized balance (same as get_balance for testing)."""
        return self.balance
    
    def get_asset_pair_info(self, pair):
        """Return mock pair info."""
        # Return minimal info to pass checks
        return {'ordermin': '0.0001'}
    
    def add_trailing_stop_loss(self, pair, direction, volume, trailing_offset_percent, **kwargs):
        """Mock order creation."""
        self.add_order_calls.append({
            'pair': pair,
            'direction': direction,
            'volume': volume,
            'trailing_offset_percent': trailing_offset_percent
        })
        
        if self.add_order_error:
            raise self.add_order_error
        
        return {'txid': ['MOCK-ORDER-ID-123']}


def test_check_sufficient_balance_with_spot_only():
    """Test balance check with balance only in spot wallet."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    # Balance with only spot BTC
    balance = {
        'XXBT': '1.5',
        'ZUSD': '10000.00'
    }
    
    api = MockKrakenAPI(balance=balance)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api,
        dry_run=False
    )
    
    # Check balance for 1.0 BTC sell order
    is_sufficient, message, available = ttslo.check_sufficient_balance(
        pair='XXBTZUSD',
        direction='sell',
        volume=1.0,
        config_id='test_config'
    )
    
    assert is_sufficient is True
    assert available == Decimal('1.5')
    assert 'Sufficient' in message
    assert 'XXBT' in message


def test_check_sufficient_balance_with_funding_only():
    """Test balance check with balance only in funding wallet."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    # Balance with only funding BTC (as per AGENTS.md example)
    balance = {
        'XXBT': '0.0000000000',
        'XBT.F': '0.0106906064'
    }
    
    api = MockKrakenAPI(balance=balance)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api,
        dry_run=False
    )
    
    # Check balance for 0.01 BTC sell order
    is_sufficient, message, available = ttslo.check_sufficient_balance(
        pair='XXBTZUSD',
        direction='sell',
        volume=0.01,
        config_id='test_config'
    )
    
    assert is_sufficient is True
    assert available >= Decimal('0.01')
    assert 'Sufficient' in message


def test_check_sufficient_balance_with_both_spot_and_funding():
    """Test balance check with balance in both spot and funding wallets."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    # Balance with both spot and funding BTC
    balance = {
        'XXBT': '0.5',
        'XBT.F': '0.6'
    }
    
    api = MockKrakenAPI(balance=balance)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api,
        dry_run=False
    )
    
    # Check balance for 1.0 BTC sell order (should sum both wallets)
    is_sufficient, message, available = ttslo.check_sufficient_balance(
        pair='XXBTZUSD',
        direction='sell',
        volume=1.0,
        config_id='test_config'
    )
    
    assert is_sufficient is True
    assert available == Decimal('1.1')  # 0.5 + 0.6
    assert 'Sufficient' in message


def test_check_insufficient_balance():
    """Test balance check with insufficient balance."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    # Insufficient balance
    balance = {
        'XXBT': '0.5',
        'XBT.F': '0.3'
    }
    
    api = MockKrakenAPI(balance=balance)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api,
        dry_run=False
    )
    
    # Check balance for 1.0 BTC sell order
    is_sufficient, message, available = ttslo.check_sufficient_balance(
        pair='XXBTZUSD',
        direction='sell',
        volume=1.0,
        config_id='test_config'
    )
    
    assert is_sufficient is False
    assert available == Decimal('0.8')  # 0.5 + 0.3
    assert 'Insufficient' in message


def test_create_order_blocks_on_insufficient_balance():
    """Test that create_tsl_order blocks order when balance is insufficient."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    # Insufficient balance
    balance = {
        'XXBT': '0.5'
    }
    
    api = MockKrakenAPI(balance=balance)
    notification_manager = Mock(spec=NotificationManager)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api,
        dry_run=False,
        notification_manager=notification_manager
    )
    
    config = {
        'id': 'test_config',
        'pair': 'XXBTZUSD',
        'direction': 'sell',
        'volume': '1.0',
        'trailing_offset_percent': '5.0'
    }
    
    # Try to create order with insufficient balance
    order_id = ttslo.create_tsl_order(config, trigger_price=50000.0)
    
    # Order should not be created
    assert order_id is None
    
    # API should not have been called
    assert len(api.add_order_calls) == 0
    
    # Notification should have been sent
    notification_manager.notify_insufficient_balance.assert_called_once()
    call_args = notification_manager.notify_insufficient_balance.call_args[1]
    assert call_args['config_id'] == 'test_config'
    assert call_args['pair'] == 'XXBTZUSD'
    assert call_args['direction'] == 'sell'
    assert call_args['volume'] == '1.0'


def test_create_order_succeeds_with_sufficient_balance():
    """Test that create_tsl_order succeeds when balance is sufficient."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    # Sufficient balance
    balance = {
        'XXBT': '2.0'
    }
    
    api = MockKrakenAPI(balance=balance)
    notification_manager = Mock(spec=NotificationManager)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api,
        dry_run=False,
        notification_manager=notification_manager
    )
    
    config = {
        'id': 'test_config',
        'pair': 'XXBTZUSD',
        'direction': 'sell',
        'volume': '1.0',
        'trailing_offset_percent': '5.0'
    }
    
    # Try to create order with sufficient balance
    order_id = ttslo.create_tsl_order(config, trigger_price=50000.0)
    
    # Order should be created successfully
    assert order_id == 'MOCK-ORDER-ID-123'
    
    # API should have been called
    assert len(api.add_order_calls) == 1
    
    # Insufficient balance notification should NOT have been sent
    notification_manager.notify_insufficient_balance.assert_not_called()
    
    # Success notification should have been sent
    notification_manager.notify_tsl_order_created.assert_called_once()


def test_create_order_handles_kraken_insufficient_funds_error():
    """Test that Kraken API error for insufficient funds triggers notification."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    # Balance check passes but Kraken returns insufficient funds error
    balance = {
        'XXBT': '2.0'
    }
    
    # Kraken API will raise an exception about insufficient funds
    api = MockKrakenAPI(
        balance=balance,
        add_order_error=Exception('Kraken API error: Insufficient funds')
    )
    notification_manager = Mock(spec=NotificationManager)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api,
        dry_run=False,
        notification_manager=notification_manager
    )
    
    config = {
        'id': 'test_config',
        'pair': 'XXBTZUSD',
        'direction': 'sell',
        'volume': '1.0',
        'trailing_offset_percent': '5.0'
    }
    
    # Try to create order
    order_id = ttslo.create_tsl_order(config, trigger_price=50000.0)
    
    # Order should not be created
    assert order_id is None
    
    # Order failed notification should have been sent
    notification_manager.notify_order_failed.assert_called_once()
    call_args = notification_manager.notify_order_failed.call_args[1]
    assert call_args['config_id'] == 'test_config'
    assert 'Insufficient funds' in call_args['error']


def test_balance_check_for_buy_orders():
    """Test that balance check works for buy orders (checks quote currency)."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    # Balance with USD (quote currency for buy orders)
    balance = {
        'XXBT': '0.0',  # No BTC (base asset)
        'ZUSD': '60000.00'  # Has USD (quote currency)
    }
    api = MockKrakenAPI(balance=balance)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api,
        dry_run=False
    )
    
    # Check balance for buy order - buying 1.0 BTC at $50,000
    # Need 1.0 * $50,000 = $50,000 USD
    is_sufficient, message, available = ttslo.check_sufficient_balance(
        pair='XXBTZUSD',
        direction='buy',
        volume=1.0,
        current_price=50000.0,
        config_id='test_config'
    )
    
    # Balance check should pass (have $60k, need $50k)
    assert is_sufficient is True
    assert 'ZUSD' in message or 'USD' in message
    assert available == Decimal('60000.00')


def test_normalize_asset():
    """Test asset normalization."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    api = MockKrakenAPI()
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api
    )
    
    # Test various asset key formats
    assert ttslo._normalize_asset('XXBT') == 'BT'
    assert ttslo._normalize_asset('XBT.F') == 'BT'
    assert ttslo._normalize_asset('XETH') == 'ETH'
    assert ttslo._normalize_asset('ETH.F') == 'ETH'
    assert ttslo._normalize_asset('SOL') == 'SOL'
    assert ttslo._normalize_asset('ZUSD') == 'USD'


def test_extract_base_asset():
    """Test base asset extraction from trading pairs."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    api = MockKrakenAPI()
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api
    )
    
    # Test various trading pairs
    assert ttslo._extract_base_asset('XXBTZUSD') == 'XXBT'
    assert ttslo._extract_base_asset('XETHZUSD') == 'XETH'
    assert ttslo._extract_base_asset('SOLUSDT') == 'SOL'
    assert ttslo._extract_base_asset('ADAUSDT') == 'ADA'


def test_balance_check_insufficient_for_buy_orders():
    """Test that balance check fails for buy orders with insufficient quote currency."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    # Balance with insufficient USD for buy order
    balance = {
        'XXBT': '0.0',
        'ZUSD': '10000.00'  # Not enough USD to buy 1 BTC at $50k
    }
    api = MockKrakenAPI(balance=balance)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api,
        dry_run=False
    )
    
    # Check balance for buy order - buying 1.0 BTC at $50,000
    # Need 1.0 * $50,000 = $50,000 USD, but only have $10,000
    is_sufficient, message, available = ttslo.check_sufficient_balance(
        pair='XXBTZUSD',
        direction='buy',
        volume=1.0,
        current_price=50000.0,
        config_id='test_config'
    )
    
    # Balance check should fail
    assert is_sufficient is False
    assert 'Insufficient' in message
    assert 'ZUSD' in message or 'USD' in message
    assert available == Decimal('10000.00')


def test_buy_order_balance_without_current_price():
    """Test that buy order balance check fails if current_price is not provided."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.log = Mock()
    
    balance = {
        'ZUSD': '10000.00'
    }
    api = MockKrakenAPI(balance=balance)
    
    ttslo = TTSLO(
        config_manager=config_manager,
        kraken_api_readonly=api,
        kraken_api_readwrite=api,
        dry_run=False
    )
    
    # Check balance for buy order without current_price
    is_sufficient, message, available = ttslo.check_sufficient_balance(
        pair='XXBTZUSD',
        direction='buy',
        volume=1.0,
        config_id='test_config'
    )
    
    # Should fail with appropriate error
    assert is_sufficient is False
    assert 'Current price required' in message
    assert available is None
