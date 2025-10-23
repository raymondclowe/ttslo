#!/usr/bin/env python3
"""
Comprehensive tests for order field mapping and direction handling.

This test suite validates that all fields in orders created by ttslo.py
and kraken_api.py match the Kraken API requirements and example orders.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from kraken_api import KrakenAPI


class TestOrderFieldMapping:
    """Test order field mapping from config to Kraken API."""

    def test_add_trailing_stop_loss_field_mapping_sell(self):
        """Test that add_trailing_stop_loss correctly maps fields for SELL order."""
        # Create mock API
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        # Mock the private query method to capture parameters
        with patch.object(api, '_query_private') as mock_query:
            mock_query.return_value = {
                'error': [],
                'result': {
                    'txid': ['ORDER-123'],
                    'descr': {
                        'order': 'sell 0.01 XBTUSDT @ trailing stop +5.0%'
                    }
                }
            }
            
            # Call the method with SELL parameters
            result = api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='sell',
                volume=0.01,
                trailing_offset_percent=5.0
            )
            
            # Verify the API was called with correct parameters
            mock_query.assert_called_once()
            call_args = mock_query.call_args
            
            # Extract the params passed to AddOrder
            params = call_args[0][1]  # Second argument is the params dict
            
            # Validate all required fields are present
            assert 'pair' in params, "pair field must be present"
            assert 'type' in params, "type field must be present"
            assert 'ordertype' in params, "ordertype field must be present"
            assert 'volume' in params, "volume field must be present"
            assert 'price' in params, "price field must be present"
            
            # Validate field values
            assert params['pair'] == 'XXBTZUSD', "pair should be passed as-is"
            assert params['type'] == 'sell', "direction should map to type='sell'"
            assert params['ordertype'] == 'trailing-stop', "ordertype should be 'trailing-stop'"
            assert params['volume'] == '0.01', "volume should be converted to string"
            assert params['price'] == '+5.0%', "trailing offset should be formatted as '+X.X%'"
            
            # Validate the response
            assert 'txid' in result
            assert result['txid'] == ['ORDER-123']

    def test_add_trailing_stop_loss_field_mapping_buy(self):
        """Test that add_trailing_stop_loss correctly maps fields for BUY order."""
        # Create mock API
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        # Mock the private query method to capture parameters
        with patch.object(api, '_query_private') as mock_query:
            mock_query.return_value = {
                'error': [],
                'result': {
                    'txid': ['ORDER-456'],
                    'descr': {
                        'order': 'buy 0.005 XBTUSDT @ trailing stop +10.0%'
                    }
                }
            }
            
            # Call the method with BUY parameters
            result = api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='buy',
                volume=0.005,
                trailing_offset_percent=10.0
            )
            
            # Verify the API was called with correct parameters
            mock_query.assert_called_once()
            call_args = mock_query.call_args
            
            # Extract the params passed to AddOrder
            params = call_args[0][1]
            
            # Validate field values
            assert params['pair'] == 'XXBTZUSD', "pair should be passed as-is"
            assert params['type'] == 'buy', "direction should map to type='buy'"
            assert params['ordertype'] == 'trailing-stop', "ordertype should be 'trailing-stop'"
            assert params['volume'] == '0.005', "volume should be converted to string"
            assert params['price'] == '+10.0%', "trailing offset should be formatted as '+X.X%'"

    def test_add_order_field_mapping(self):
        """Test that add_order correctly maps fields."""
        # Create mock API
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        # Mock the private query method
        with patch.object(api, '_query_private') as mock_query:
            mock_query.return_value = {
                'error': [],
                'result': {
                    'txid': ['ORDER-789']
                }
            }
            
            # Call add_order with various parameters
            result = api.add_order(
                pair='XETHZUSD',
                order_type='limit',
                direction='buy',
                volume=0.5,
                price='3000.0'
            )
            
            # Verify the API was called
            mock_query.assert_called_once()
            call_args = mock_query.call_args
            
            # Extract the params
            params = call_args[0][1]
            
            # Validate field mapping
            assert params['pair'] == 'XETHZUSD', "pair should be passed as-is"
            assert params['type'] == 'buy', "direction should map to type"
            assert params['ordertype'] == 'limit', "order_type should map to ordertype"
            assert params['volume'] == '0.5', "volume should be converted to string"
            assert params['price'] == '3000.0', "additional params should be included"

    def test_direction_normalization(self):
        """Test that direction is normalized to lowercase."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        with patch.object(api, '_query_private') as mock_query:
            mock_query.return_value = {
                'error': [],
                'result': {'txid': ['ORDER-X']}
            }
            
            # Test uppercase SELL
            api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='SELL',
                volume=0.01,
                trailing_offset_percent=5.0
            )
            
            params = mock_query.call_args[0][1]
            assert params['type'] == 'sell', "SELL should be normalized to sell"
            
            # Reset mock
            mock_query.reset_mock()
            
            # Test mixed case Buy
            api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='Buy',
                volume=0.01,
                trailing_offset_percent=5.0
            )
            
            params = mock_query.call_args[0][1]
            assert params['type'] == 'buy', "Buy should be normalized to buy"

    def test_trailing_offset_formatting(self):
        """Test various trailing offset percentage formats."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        test_cases = [
            (5.0, '+5.0%'),
            (10.5, '+10.5%'),
            (0.5, '+0.5%'),
            (15, '+15.0%'),
            (3.14159, '+3.1%'),  # Should round to 1 decimal
        ]
        
        for input_offset, expected_format in test_cases:
            with patch.object(api, '_query_private') as mock_query:
                mock_query.return_value = {
                    'error': [],
                    'result': {'txid': ['ORDER-X']}
                }
                
                api.add_trailing_stop_loss(
                    pair='XXBTZUSD',
                    direction='sell',
                    volume=0.01,
                    trailing_offset_percent=input_offset
                )
                
                params = mock_query.call_args[0][1]
                assert params['price'] == expected_format, \
                    f"Offset {input_offset} should format as {expected_format}, got {params['price']}"

    def test_volume_string_conversion(self):
        """Test that volume is correctly converted to string."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        test_volumes = [
            0.01,
            0.005,
            1.0,
            10,
            0.00001,
        ]
        
        for volume in test_volumes:
            with patch.object(api, '_query_private') as mock_query:
                mock_query.return_value = {
                    'error': [],
                    'result': {'txid': ['ORDER-X']}
                }
                
                api.add_trailing_stop_loss(
                    pair='XXBTZUSD',
                    direction='sell',
                    volume=volume,
                    trailing_offset_percent=5.0
                )
                
                params = mock_query.call_args[0][1]
                assert isinstance(params['volume'], str), \
                    f"Volume should be string, got {type(params['volume'])}"
                assert params['volume'] == str(volume), \
                    f"Volume {volume} should convert to '{str(volume)}'"


class TestOrderFieldValidation:
    """Test validation of order fields."""

    def test_missing_pair_raises_error(self):
        """Test that missing pair raises ValueError."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        with pytest.raises(ValueError, match="pair parameter is required"):
            api.add_trailing_stop_loss(
                pair='',
                direction='sell',
                volume=0.01,
                trailing_offset_percent=5.0
            )

    def test_missing_direction_raises_error(self):
        """Test that missing direction raises ValueError."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        with pytest.raises(ValueError, match="direction parameter is required"):
            api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='',
                volume=0.01,
                trailing_offset_percent=5.0
            )

    def test_invalid_direction_raises_error(self):
        """Test that invalid direction raises ValueError."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        with pytest.raises(ValueError, match="direction must be 'buy' or 'sell'"):
            api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='invalid',
                volume=0.01,
                trailing_offset_percent=5.0
            )

    def test_missing_volume_raises_error(self):
        """Test that missing volume raises ValueError."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        with pytest.raises(ValueError, match="volume parameter is required"):
            api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='sell',
                volume=None,
                trailing_offset_percent=5.0
            )

    def test_invalid_volume_raises_error(self):
        """Test that invalid volume raises ValueError."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        with pytest.raises(ValueError, match="volume must be a valid number"):
            api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='sell',
                volume='invalid',
                trailing_offset_percent=5.0
            )

    def test_negative_volume_raises_error(self):
        """Test that negative volume raises ValueError."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        with pytest.raises(ValueError, match="volume must be positive"):
            api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='sell',
                volume=-0.01,
                trailing_offset_percent=5.0
            )

    def test_missing_trailing_offset_raises_error(self):
        """Test that missing trailing offset raises ValueError."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        with pytest.raises(ValueError, match="trailing_offset_percent parameter is required"):
            api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='sell',
                volume=0.01,
                trailing_offset_percent=None
            )

    def test_invalid_trailing_offset_raises_error(self):
        """Test that invalid trailing offset raises ValueError."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        with pytest.raises(ValueError, match="trailing_offset_percent must be a valid number"):
            api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='sell',
                volume=0.01,
                trailing_offset_percent='invalid'
            )

    def test_negative_trailing_offset_raises_error(self):
        """Test that negative trailing offset raises ValueError."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        with pytest.raises(ValueError, match="trailing_offset_percent must be positive"):
            api.add_trailing_stop_loss(
                pair='XXBTZUSD',
                direction='sell',
                volume=0.01,
                trailing_offset_percent=-5.0
            )


class TestExampleOrderCompliance:
    """Test compliance with real example orders from Kraken API."""

    def test_matches_example_sell_order(self):
        """Test that our implementation creates orders matching the example SELL order."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        # Example SELL order from example_tslo_orders-20251021.json:
        # {
        #   "descr": {
        #     "pair": "XBTUSDT",
        #     "type": "sell",
        #     "ordertype": "trailing-stop",
        #     "price": "+11.0000%"
        #   },
        #   "vol": "0.00006600"
        # }
        
        with patch.object(api, '_query_private') as mock_query:
            mock_query.return_value = {
                'error': [],
                'result': {'txid': ['ORDER-SELL']}
            }
            
            # Create order with same parameters as example
            api.add_trailing_stop_loss(
                pair='XBTUSDT',
                direction='sell',
                volume=0.00006600,
                trailing_offset_percent=11.0
            )
            
            params = mock_query.call_args[0][1]
            
            # Verify matches example order
            assert params['pair'] == 'XBTUSDT', "Pair should match example"
            assert params['type'] == 'sell', "Type should be 'sell' like example"
            assert params['ordertype'] == 'trailing-stop', "Order type should match example"
            assert params['price'] == '+11.0%', "Price format should match example"
            # Volume is converted using str() which may use scientific notation for small numbers
            assert params['volume'] == str(0.00006600), "Volume should be converted to string"
            assert float(params['volume']) == 0.00006600, "Volume value should match example"

    def test_matches_example_buy_order(self):
        """Test that our implementation creates orders matching the example BUY order."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        # Example BUY order from example_tslo_orders-20251021.json:
        # {
        #   "descr": {
        #     "pair": "XBTUSDT",
        #     "type": "buy",
        #     "ordertype": "trailing-stop",
        #     "price": "+9.0000%"
        #   },
        #   "vol": "0.00005500"
        # }
        
        with patch.object(api, '_query_private') as mock_query:
            mock_query.return_value = {
                'error': [],
                'result': {'txid': ['ORDER-BUY']}
            }
            
            # Create order with same parameters as example
            api.add_trailing_stop_loss(
                pair='XBTUSDT',
                direction='buy',
                volume=0.00005500,
                trailing_offset_percent=9.0
            )
            
            params = mock_query.call_args[0][1]
            
            # Verify matches example order
            assert params['pair'] == 'XBTUSDT', "Pair should match example"
            assert params['type'] == 'buy', "Type should be 'buy' like example"
            assert params['ordertype'] == 'trailing-stop', "Order type should match example"
            assert params['price'] == '+9.0%', "Price format should match example"
            # Volume is converted using str() which may use scientific notation for small numbers
            assert params['volume'] == str(0.00005500), "Volume should be converted to string"
            assert float(params['volume']) == 0.00005500, "Volume value should match example"

    def test_both_directions_use_plus_prefix(self):
        """Test that both buy and sell orders use '+' prefix in price (as per examples)."""
        api = KrakenAPI(api_key="test_key", api_secret="dGVzdF9zZWNyZXQ=")
        
        for direction in ['buy', 'sell']:
            with patch.object(api, '_query_private') as mock_query:
                mock_query.return_value = {
                    'error': [],
                    'result': {'txid': ['ORDER-X']}
                }
                
                api.add_trailing_stop_loss(
                    pair='XBTUSDT',
                    direction=direction,
                    volume=0.01,
                    trailing_offset_percent=5.0
                )
                
                params = mock_query.call_args[0][1]
                
                # Both buy and sell should use '+' prefix
                assert params['price'].startswith('+'), \
                    f"{direction} order should have '+' prefix in price"
                assert params['price'].endswith('%'), \
                    f"{direction} order should have '%' suffix in price"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
