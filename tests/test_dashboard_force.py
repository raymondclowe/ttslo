"""
Tests for dashboard force pending order functionality.
"""

import os
import sys
import tempfile
import csv
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dashboard
from config import ConfigManager
from kraken_api import KrakenAPI


def test_force_pending_order_success():
    """Test successfully forcing a pending order - creates TSL order immediately."""
    # Create temporary config and state files
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        config_file = f.name
        writer = csv.DictWriter(f, fieldnames=['id', 'pair', 'threshold_price', 'threshold_type', 'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writeheader()
        writer.writerow({
            'id': 'test_btc_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '1.0',
            'enabled': 'true'
        })
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        state_file = f.name
        # Empty state file initially
    
    try:
        # Create config manager
        config_manager = ConfigManager(config_file, state_file, 'logs.csv')
        
        # Mock Kraken API
        with patch.object(dashboard, 'kraken_api') as mock_api:
            # Mock get_current_price
            mock_api.get_current_price.return_value = 51234.56
            
            # Mock add_trailing_stop_loss to return order ID
            mock_api.add_trailing_stop_loss.return_value = {
                'txid': ['OIZXVF-N5TQ5-DHTPIR']
            }
            
            # Mock config_manager in dashboard
            with patch.object(dashboard, 'config_manager', config_manager):
                # Mock get_cached_config to return our config
                with patch.object(dashboard, 'get_cached_config') as mock_get_config:
                    mock_get_config.return_value = [{
                        'id': 'test_btc_1',
                        'pair': 'XXBTZUSD',
                        'threshold_price': '50000',
                        'threshold_type': 'above',
                        'direction': 'sell',
                        'volume': '0.1',
                        'trailing_offset_percent': '1.0',
                        'enabled': 'true'
                    }]
                    
                    # Create test client
                    with dashboard.app.test_client() as client:
                        # Call force endpoint
                        response = client.post('/api/pending/test_btc_1/force')
                        
                        # Check response
                        assert response.status_code == 200
                        data = response.get_json()
                        assert data['success'] is True
                        assert data['config_id'] == 'test_btc_1'
                        assert data['pair'] == 'XXBTZUSD'
                        assert data['order_id'] == 'OIZXVF-N5TQ5-DHTPIR'
                        assert data['trigger_price'] == 51234.56
                        assert 'created successfully' in data['message'].lower()
                        
                        # Verify API was called to create order
                        mock_api.add_trailing_stop_loss.assert_called_once()
                        call_args = mock_api.add_trailing_stop_loss.call_args
                        assert call_args[1]['pair'] == 'XXBTZUSD'
                        assert call_args[1]['direction'] == 'sell'
                        assert call_args[1]['volume'] == '0.1'
                        assert call_args[1]['trailing_offset_percent'] == '1.0'
        
        # Verify threshold_price was updated in config file
        configs = config_manager.load_config()
        assert len(configs) == 1
        assert configs[0]['id'] == 'test_btc_1'
        assert float(configs[0]['threshold_price']) == 51234.56
        
        # Verify state was updated
        state = config_manager.load_state()
        assert 'test_btc_1' in state
        assert state['test_btc_1']['triggered'] == 'true'
        assert state['test_btc_1']['order_id'] == 'OIZXVF-N5TQ5-DHTPIR'
        assert float(state['test_btc_1']['trigger_price']) == 51234.56
        
    finally:
        # Cleanup
        if os.path.exists(config_file):
            os.unlink(config_file)
        if os.path.exists(state_file):
            os.unlink(state_file)


def test_force_pending_order_not_found():
    """Test forcing a non-existent order."""
    # Mock get_cached_config to return empty list
    with patch.object(dashboard, 'get_cached_config') as mock_get_config:
        mock_get_config.return_value = []
        
        with dashboard.app.test_client() as client:
            response = client.post('/api/pending/nonexistent_id/force')
            
            assert response.status_code == 404
            data = response.get_json()
            assert data['success'] is False
            assert 'not found' in data['error'].lower()


def test_force_pending_order_missing_direction():
    """Test forcing an order with missing direction field."""
    with patch.object(dashboard, 'get_cached_config') as mock_get_config:
        mock_get_config.return_value = [{
            'id': 'test_id',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'volume': '0.1',
            'trailing_offset_percent': '1.0',
            'enabled': 'true'
            # Missing 'direction' field
        }]
        
        with dashboard.app.test_client() as client:
            response = client.post('/api/pending/test_id/force')
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] is False
            assert 'no direction' in data['error'].lower()


def test_force_pending_order_tsl_creation_failure():
    """Test forcing when TSL order creation fails."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        config_file = f.name
        writer = csv.DictWriter(f, fieldnames=['id', 'pair', 'threshold_price', 'threshold_type', 'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writeheader()
        writer.writerow({
            'id': 'test_btc_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '1.0',
            'enabled': 'true'
        })
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        state_file = f.name
    
    try:
        config_manager = ConfigManager(config_file, state_file, 'logs.csv')
        
        # Mock Kraken API
        with patch.object(dashboard, 'kraken_api') as mock_api:
            mock_api.get_current_price.return_value = 51234.56
            
            # Mock add_trailing_stop_loss to raise error (e.g., insufficient balance)
            mock_api.add_trailing_stop_loss.side_effect = Exception("EGeneral:Insufficient funds")
            
            with patch.object(dashboard, 'config_manager', config_manager):
                with patch.object(dashboard, 'get_cached_config') as mock_get_config:
                    mock_get_config.return_value = [{
                        'id': 'test_btc_1',
                        'pair': 'XXBTZUSD',
                        'threshold_price': '50000',
                        'threshold_type': 'above',
                        'direction': 'sell',
                        'volume': '0.1',
                        'trailing_offset_percent': '1.0',
                        'enabled': 'true'
                    }]
                    
                    with dashboard.app.test_client() as client:
                        response = client.post('/api/pending/test_btc_1/force')
                        
                        assert response.status_code == 500
                        data = response.get_json()
                        assert data['success'] is False
                        assert 'failed to create tsl order' in data['error'].lower()
        
        # Verify config was still updated (threshold price changed)
        configs = config_manager.load_config()
        assert float(configs[0]['threshold_price']) == 51234.56
        
        # Verify state was NOT updated (no order was created)
        state = config_manager.load_state()
        if 'test_btc_1' in state:
            assert state['test_btc_1'].get('triggered') != 'true'
        
    finally:
        if os.path.exists(config_file):
            os.unlink(config_file)
        if os.path.exists(state_file):
            os.unlink(state_file)


def test_force_pending_order_index_unavailable_fallback():
    """Test forcing when index price unavailable, falls back to last price."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        config_file = f.name
        writer = csv.DictWriter(f, fieldnames=['id', 'pair', 'threshold_price', 'threshold_type', 'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writeheader()
        writer.writerow({
            'id': 'test_btc_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '1.0',
            'enabled': 'true'
        })
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        state_file = f.name
    
    try:
        config_manager = ConfigManager(config_file, state_file, 'logs.csv')
        
        # Mock Kraken API
        with patch.object(dashboard, 'kraken_api') as mock_api:
            mock_api.get_current_price.return_value = 51234.56
            
            # First call fails with index unavailable, second succeeds
            mock_api.add_trailing_stop_loss.side_effect = [
                Exception("EGeneral:Invalid arguments:Index unavailable"),
                {'txid': ['ORDER-ID-123']}
            ]
            
            with patch.object(dashboard, 'config_manager', config_manager):
                with patch.object(dashboard, 'get_cached_config') as mock_get_config:
                    mock_get_config.return_value = [{
                        'id': 'test_btc_1',
                        'pair': 'XXBTZUSD',
                        'threshold_price': '50000',
                        'threshold_type': 'above',
                        'direction': 'sell',
                        'volume': '0.1',
                        'trailing_offset_percent': '1.0',
                        'enabled': 'true'
                    }]
                    
                    with dashboard.app.test_client() as client:
                        response = client.post('/api/pending/test_btc_1/force')
                        
                        assert response.status_code == 200
                        data = response.get_json()
                        assert data['success'] is True
                        assert data['order_id'] == 'ORDER-ID-123'
                        
                        # Verify API was called twice (first with index, then with last)
                        assert mock_api.add_trailing_stop_loss.call_count == 2
                        
                        # First call should have trigger='index'
                        first_call = mock_api.add_trailing_stop_loss.call_args_list[0]
                        assert first_call[1].get('trigger') == 'index'
                        
                        # Second call should have trigger='last'
                        second_call = mock_api.add_trailing_stop_loss.call_args_list[1]
                        assert second_call[1].get('trigger') == 'last'
        
        # Verify state was updated
        state = config_manager.load_state()
        assert state['test_btc_1']['triggered'] == 'true'
        assert state['test_btc_1']['order_id'] == 'ORDER-ID-123'
        
    finally:
        if os.path.exists(config_file):
            os.unlink(config_file)
        if os.path.exists(state_file):
            os.unlink(state_file)


def test_force_pending_order_no_pair():
    """Test forcing an order with no trading pair."""
    # Mock get_cached_config to return config without pair
    with patch.object(dashboard, 'get_cached_config') as mock_get_config:
        mock_get_config.return_value = [{
            'id': 'test_id',
            'threshold_price': '50000',
            'enabled': 'true'
            # No 'pair' field
        }]
        
        with dashboard.app.test_client() as client:
            response = client.post('/api/pending/test_id/force')
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] is False
            assert 'no trading pair' in data['error'].lower()


def test_force_pending_order_no_kraken_api():
    """Test forcing when Kraken API is not available."""
    # Mock get_cached_config
    with patch.object(dashboard, 'get_cached_config') as mock_get_config:
        mock_get_config.return_value = [{
            'id': 'test_id',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '1.0',
            'enabled': 'true'
        }]
        
        # Mock kraken_api to None
        with patch.object(dashboard, 'kraken_api', None):
            with dashboard.app.test_client() as client:
                response = client.post('/api/pending/test_id/force')
                
                assert response.status_code == 503
                data = response.get_json()
                assert data['success'] is False
                assert 'not available' in data['error'].lower()


def test_force_pending_order_price_fetch_error():
    """Test forcing when price fetch fails."""
    # Mock get_cached_config
    with patch.object(dashboard, 'get_cached_config') as mock_get_config:
        mock_get_config.return_value = [{
            'id': 'test_id',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '1.0',
            'enabled': 'true'
        }]
        
        # Mock kraken_api to raise error on get_current_price
        with patch.object(dashboard, 'kraken_api') as mock_api:
            mock_api.get_current_price.side_effect = Exception("API error")
            
            with dashboard.app.test_client() as client:
                response = client.post('/api/pending/test_id/force')
                
                assert response.status_code == 500
                data = response.get_json()
                assert data['success'] is False
                assert 'could not get current price' in data['error'].lower()


def test_update_config_threshold_price():
    """Test the update_config_threshold_price method."""
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        config_file = f.name
        writer = csv.DictWriter(f, fieldnames=['id', 'pair', 'threshold_price', 'threshold_type', 'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writeheader()
        writer.writerow({
            'id': 'test_id',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '1.0',
            'enabled': 'true'
        })
    
    try:
        config_manager = ConfigManager(config_file, 'state.csv', 'logs.csv')
        
        # Update threshold_price
        config_manager.update_config_threshold_price('test_id', 51234.56)
        
        # Verify it was updated
        configs = config_manager.load_config()
        assert len(configs) == 1
        assert configs[0]['id'] == 'test_id'
        assert configs[0]['threshold_price'] == '51234.56'
        
        # Other fields should be unchanged
        assert configs[0]['pair'] == 'XXBTZUSD'
        assert configs[0]['direction'] == 'sell'
        assert configs[0]['enabled'] == 'true'
        
    finally:
        if os.path.exists(config_file):
            os.unlink(config_file)


def test_update_config_threshold_price_not_found():
    """Test updating threshold_price for non-existent config."""
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        config_file = f.name
        writer = csv.DictWriter(f, fieldnames=['id', 'pair', 'threshold_price', 'threshold_type', 'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writeheader()
    
    try:
        config_manager = ConfigManager(config_file, 'state.csv', 'logs.csv')
        
        # Try to update non-existent config - should raise ValueError
        import pytest
        with pytest.raises(ValueError, match='not found'):
            config_manager.update_config_threshold_price('nonexistent', 12345)
        
    finally:
        if os.path.exists(config_file):
            os.unlink(config_file)

