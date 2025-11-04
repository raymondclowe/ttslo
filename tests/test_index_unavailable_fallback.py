"""
Test for index price unavailable fallback to last trade price.

This test verifies that when a trading pair doesn't have an index price available,
the system automatically retries with the last trade price.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from ttslo import TTSLO
from config import ConfigManager
from kraken_api import KrakenAPI, KrakenAPIError


class TestIndexUnavailableFallback:
    """Test suite for index unavailable fallback logic."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.config_manager = Mock(spec=ConfigManager)
        self.kraken_api_readonly = Mock(spec=KrakenAPI)
        self.kraken_api_readonly.get_normalized_balances.return_value = {'XXBT': '1.0', 'ZUSD': '10000.0'}
        self.kraken_api_readonly.get_asset_pair_info.return_value = {'ordermin': '0.0001'}
        self.kraken_api_readonly._normalize_asset_key.side_effect = lambda x: x
        self.kraken_api_readwrite = Mock(spec=KrakenAPI)
    self.kraken_api_readwrite.get_normalized_balances.return_value = {'XXBT': '1.0', 'ZUSD': '10000.0'}
    self.kraken_api_readwrite.get_asset_pair_info.return_value = {'ordermin': '0.0001'}
    self.kraken_api_readwrite._normalize_asset_key.side_effect = lambda x: x
        
        # Mock get_balance to return sufficient balance
        self.kraken_api_readwrite.get_balance = Mock(return_value={
            'XXBT': '10.0',
            'XETH': '100.0',
            'SOL': '1000.0',  # For SOL tests
            'ZUSD': '100000.0'
        })
        
        # Create TTSLO instance
        self.ttslo = TTSLO(
            config_manager=self.config_manager,
            kraken_api_readonly=self.kraken_api_readonly,
            kraken_api_readwrite=self.kraken_api_readwrite,
            dry_run=False,
            verbose=True
        )
    
    def test_index_unavailable_retries_with_last_price(self):
        """
        Test that when index price is unavailable, the system retries with last price.
        """
        # Setup: Mock API to fail first with "Index unavailable" then succeed
        first_call = True
        
        def mock_add_trailing_stop_loss(*args, **kwargs):
            nonlocal first_call
            if first_call:
                first_call = False
                # First call with trigger='index' should fail
                if kwargs.get('trigger') == 'index':
                    raise Exception("Kraken API error: EGeneral:Invalid arguments:Index unavailable")
                else:
                    # Should not reach here on first call
                    pytest.fail("First call should use trigger='index'")
            else:
                # Second call with trigger='last' should succeed
                if kwargs.get('trigger') == 'last':
                    return {
                        'txid': ['ORDER123'],
                        'descr': {'order': 'test order'}
                    }
                else:
                    pytest.fail("Second call should use trigger='last'")
        
        self.kraken_api_readwrite.add_trailing_stop_loss = Mock(
            side_effect=mock_add_trailing_stop_loss
        )
        
        # Create test config
        config = {
            'id': 'sol_24',
            'pair': 'SOLUSDT',
            'direction': 'sell',
            'volume': '10',
            'trailing_offset_percent': '5.0'
        }
        
        # Execute: Create TSL order
        order_id = self.ttslo.create_tsl_order(config, trigger_price=1.5)
        
        # Assert: Order was created successfully
        assert order_id == 'ORDER123'
        
        # Assert: add_trailing_stop_loss was called twice
        assert self.kraken_api_readwrite.add_trailing_stop_loss.call_count == 2
        
        # Assert: First call used trigger='index'
        first_call_kwargs = self.kraken_api_readwrite.add_trailing_stop_loss.call_args_list[0][1]
        assert first_call_kwargs.get('trigger') == 'index'
        
        # Assert: Second call used trigger='last'
        second_call_kwargs = self.kraken_api_readwrite.add_trailing_stop_loss.call_args_list[1][1]
        assert second_call_kwargs.get('trigger') == 'last'
    
    def test_non_index_error_does_not_retry(self):
        """
        Test that other errors (not index unavailable) do not trigger retry.
        """
        # Setup: Mock API to fail with a different error
        self.kraken_api_readwrite.add_trailing_stop_loss = Mock(
            side_effect=Exception("Kraken API error: EGeneral:Insufficient funds")
        )
        
        # Create test config
        config = {
            'id': 'test_1',
            'pair': 'XXBTZUSD',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0'
        }
        
        # Execute: Create TSL order
        order_id = self.ttslo.create_tsl_order(config, trigger_price=50000.0)
        
        # Assert: Order was not created
        assert order_id is None
        
        # Assert: add_trailing_stop_loss was called only once (no retry)
        assert self.kraken_api_readwrite.add_trailing_stop_loss.call_count == 1
    
    def test_both_index_and_last_fail(self):
        """
        Test that if both index and last price fail, order is not created.
        """
        # Setup: Mock API to fail both times
        call_count = 0
        
        def mock_add_trailing_stop_loss(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call with trigger='index' fails
                raise Exception("Kraken API error: EGeneral:Invalid arguments:Index unavailable")
            else:
                # Second call with trigger='last' also fails
                raise Exception("Kraken API error: EGeneral:Invalid arguments:ordermin")
        
        self.kraken_api_readwrite.add_trailing_stop_loss = Mock(
            side_effect=mock_add_trailing_stop_loss
        )
        
        # Create test config
        config = {
            'id': 'test_2',
            'pair': 'SOLUSDT',
            'direction': 'sell',
            'volume': '10',
            'trailing_offset_percent': '5.0'
        }
        
        # Execute: Create TSL order
        order_id = self.ttslo.create_tsl_order(config, trigger_price=1.5)
        
        # Assert: Order was not created
        assert order_id is None
        
        # Assert: add_trailing_stop_loss was called twice (original + retry)
        assert self.kraken_api_readwrite.add_trailing_stop_loss.call_count == 2
    
    def test_case_insensitive_index_unavailable_detection(self):
        """
        Test that error detection is case-insensitive.
        """
        # Setup: Mock API with different case variations
        test_cases = [
            "Kraken API error: EGeneral:Invalid arguments:Index unavailable",
            "Kraken API error: EGeneral:Invalid arguments:index unavailable",
            "Kraken API error: EGeneral:Invalid arguments:INDEX UNAVAILABLE",
        ]
        
        for error_msg in test_cases:
            # Reset mock
            call_count = 0
            
            def mock_add_trailing_stop_loss(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception(error_msg)
                else:
                    return {
                        'txid': ['ORDER123'],
                        'descr': {'order': 'test order'}
                    }
            
            self.kraken_api_readwrite.add_trailing_stop_loss = Mock(
                side_effect=mock_add_trailing_stop_loss
            )
            
            # Create test config
            config = {
                'id': f'test_case_{error_msg[:10]}',
                'pair': 'SOLUSDT',
                'direction': 'sell',
                'volume': '10',
                'trailing_offset_percent': '5.0'
            }
            
            # Execute: Create TSL order
            order_id = self.ttslo.create_tsl_order(config, trigger_price=1.5)
            
            # Assert: Order was created (retry succeeded)
            assert order_id == 'ORDER123', f"Failed for error message: {error_msg}"
    
    def test_successful_first_attempt_no_retry(self):
        """
        Test that successful first attempt does not trigger retry.
        """
        # Setup: Mock API to succeed on first attempt
        self.kraken_api_readwrite.add_trailing_stop_loss = Mock(
            return_value={
                'txid': ['ORDER789'],
                'descr': {'order': 'test order'}
            }
        )
        
        # Create test config
        config = {
            'id': 'btc_1',
            'pair': 'XXBTZUSD',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0'
        }
        
        # Execute: Create TSL order
        order_id = self.ttslo.create_tsl_order(config, trigger_price=50000.0)
        
        # Assert: Order was created
        assert order_id == 'ORDER789'
        
        # Assert: add_trailing_stop_loss was called only once (no retry needed)
        assert self.kraken_api_readwrite.add_trailing_stop_loss.call_count == 1
        
        # Assert: Used trigger='index'
        call_kwargs = self.kraken_api_readwrite.add_trailing_stop_loss.call_args[1]
        assert call_kwargs.get('trigger') == 'index'
