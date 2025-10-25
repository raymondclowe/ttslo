"""
Tests for dashboard cancel functionality.
"""
import pytest
import os
import csv
import json
from unittest.mock import Mock, patch
from dashboard import app, config_manager


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_config_file(tmp_path):
    """Create a sample config file for testing."""
    config_file = tmp_path / "config.csv"
    with open(config_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'id', 'pair', 'threshold_price', 'threshold_type', 
            'direction', 'volume', 'trailing_offset_percent', 'enabled'
        ])
        writer.writeheader()
        writer.writerow({
            'id': 'test_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        })
        writer.writerow({
            'id': 'test_2',
            'pair': 'XETHZUSD',
            'threshold_price': '3000',
            'threshold_type': 'below',
            'direction': 'buy',
            'volume': '0.1',
            'trailing_offset_percent': '3.0',
            'enabled': 'true'
        })
    return config_file


def test_cancel_pending_order_sets_status(client, sample_config_file, tmp_path):
    """Test that canceling a pending order updates its enabled status."""
    # Set up config manager with test file
    config_manager.config_file = str(sample_config_file)
    
    # Cancel the pending order
    response = client.post(
        '/api/pending/test_1/cancel',
        data=json.dumps({'status': 'canceled'}),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['config_id'] == 'test_1'
    assert data['new_status'] == 'canceled'
    
    # Verify the config file was updated
    with open(sample_config_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert rows[0]['id'] == 'test_1'
        assert rows[0]['enabled'] == 'canceled'
        assert rows[1]['id'] == 'test_2'
        assert rows[1]['enabled'] == 'true'  # Other row unchanged


def test_cancel_pending_order_supports_multiple_statuses(client, sample_config_file):
    """Test that cancel endpoint supports different status values."""
    config_manager.config_file = str(sample_config_file)
    
    # Test with 'paused'
    response = client.post(
        '/api/pending/test_1/cancel',
        data=json.dumps({'status': 'paused'}),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['new_status'] == 'paused'
    
    # Verify update
    with open(sample_config_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert rows[0]['enabled'] == 'paused'


def test_cancel_pending_order_invalid_status(client, sample_config_file):
    """Test that invalid status values are rejected."""
    config_manager.config_file = str(sample_config_file)
    
    response = client.post(
        '/api/pending/test_1/cancel',
        data=json.dumps({'status': 'invalid'}),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'Invalid status' in data['error']


def test_cancel_pending_order_nonexistent_id(client, sample_config_file):
    """Test that canceling a nonexistent config ID fails gracefully."""
    config_manager.config_file = str(sample_config_file)
    
    response = client.post(
        '/api/pending/nonexistent_id/cancel',
        data=json.dumps({'status': 'canceled'}),
        content_type='application/json'
    )
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data['success'] is False


@patch('dashboard.kraken_api')
def test_cancel_active_order_calls_kraken_api(mock_kraken_api, client):
    """Test that canceling an active order calls Kraken API."""
    mock_kraken_api.cancel_order.return_value = {'count': 1}
    
    response = client.post('/api/active/ORDER123/cancel')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['order_id'] == 'ORDER123'
    
    # Verify Kraken API was called
    mock_kraken_api.cancel_order.assert_called_once_with('ORDER123')


@patch('dashboard.kraken_api')
def test_cancel_active_order_handles_api_error(mock_kraken_api, client):
    """Test that API errors are handled gracefully."""
    mock_kraken_api.cancel_order.side_effect = Exception('API error')
    
    response = client.post('/api/active/ORDER123/cancel')
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'API error' in data['error']


def test_cancel_active_order_no_kraken_api(client):
    """Test that cancel fails gracefully when Kraken API is unavailable."""
    import dashboard
    original_kraken_api = dashboard.kraken_api
    try:
        dashboard.kraken_api = None
        response = client.post('/api/active/ORDER123/cancel')
        
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not available' in data['error']
    finally:
        dashboard.kraken_api = original_kraken_api


@patch('dashboard.kraken_api')
def test_cancel_all_orders_success(mock_kraken_api, client):
    """Test that cancel-all successfully cancels all orders."""
    # Mock open orders
    mock_kraken_api.query_open_orders.return_value = {
        'open': {
            'ORDER1': {},
            'ORDER2': {},
            'ORDER3': {}
        }
    }
    mock_kraken_api.cancel_order.return_value = {'count': 1}
    
    response = client.post('/api/cancel-all')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['canceled_count'] == 3
    assert data['failed_count'] == 0
    assert len(data['canceled_orders']) == 3
    
    # Verify all orders were canceled
    assert mock_kraken_api.cancel_order.call_count == 3


@patch('dashboard.kraken_api')
def test_cancel_all_orders_partial_failure(mock_kraken_api, client):
    """Test that cancel-all handles partial failures."""
    # Mock open orders
    mock_kraken_api.query_open_orders.return_value = {
        'open': {
            'ORDER1': {},
            'ORDER2': {},
            'ORDER3': {}
        }
    }
    
    # First order succeeds, second fails, third succeeds
    mock_kraken_api.cancel_order.side_effect = [
        {'count': 1},
        Exception('API error'),
        {'count': 1}
    ]
    
    response = client.post('/api/cancel-all')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is False  # Not all succeeded
    assert data['canceled_count'] == 2
    assert data['failed_count'] == 1
    assert len(data['failed_orders']) == 1
    assert 'API error' in data['failed_orders'][0]['error']


@patch('dashboard.kraken_api')
def test_cancel_all_orders_no_orders(mock_kraken_api, client):
    """Test that cancel-all handles no orders gracefully."""
    mock_kraken_api.query_open_orders.return_value = {'open': {}}
    
    response = client.post('/api/cancel-all')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['canceled_count'] == 0
    assert 'No active orders' in data['message']
    
    # Verify cancel_order was not called
    mock_kraken_api.cancel_order.assert_not_called()


def test_cancel_all_orders_no_kraken_api(client):
    """Test that cancel-all fails gracefully when Kraken API is unavailable."""
    import dashboard
    original_kraken_api = dashboard.kraken_api
    try:
        dashboard.kraken_api = None
        response = client.post('/api/cancel-all')
        
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not available' in data['error']
    finally:
        dashboard.kraken_api = original_kraken_api


def test_config_manager_update_enabled_status(tmp_path):
    """Test ConfigManager.update_config_enabled method."""
    config_file = tmp_path / "config.csv"
    
    # Create initial config
    with open(config_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'id', 'pair', 'threshold_price', 'threshold_type', 
            'direction', 'volume', 'trailing_offset_percent', 'enabled'
        ])
        writer.writeheader()
        writer.writerow({
            'id': 'test_1',
            'pair': 'XXBTZUSD',
            'threshold_price': '50000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.01',
            'trailing_offset_percent': '5.0',
            'enabled': 'true'
        })
    
    # Update enabled status
    from config import ConfigManager
    manager = ConfigManager(str(config_file), '', '')
    manager.update_config_enabled('test_1', 'paused')
    
    # Verify update
    with open(config_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert rows[0]['enabled'] == 'paused'


def test_config_manager_update_enabled_preserves_comments(tmp_path):
    """Test that update_config_enabled preserves comment lines."""
    config_file = tmp_path / "config.csv"
    
    # Create config with comments
    with open(config_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'pair', 'threshold_price', 'threshold_type', 
                        'direction', 'volume', 'trailing_offset_percent', 'enabled'])
        writer.writerow(['test_1', 'XXBTZUSD', '50000', 'above', 'sell', '0.01', '5.0', 'true'])
        writer.writerow(['# This is a comment', '', '', '', '', '', '', ''])
        writer.writerow(['test_2', 'XETHZUSD', '3000', 'below', 'buy', '0.1', '3.0', 'true'])
    
    # Update enabled status
    from config import ConfigManager
    manager = ConfigManager(str(config_file), '', '')
    manager.update_config_enabled('test_1', 'canceled')
    
    # Verify comment is preserved
    with open(config_file, 'r') as f:
        lines = f.readlines()
        assert '# This is a comment' in lines[2]
    
    # Verify correct row was updated
    # DictReader skips comments, so we get test_1 and test_2 only
    with open(config_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader if row.get('id') and not row['id'].startswith('#')]
        assert rows[0]['id'] == 'test_1'
        assert rows[0]['enabled'] == 'canceled'
        assert rows[1]['id'] == 'test_2'
        assert rows[1]['enabled'] == 'true'
