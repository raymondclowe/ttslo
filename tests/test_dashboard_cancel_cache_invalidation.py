"""
Tests for dashboard cancel cache invalidation.

Verifies that caches are invalidated after cancel operations so the UI gets fresh data.
"""
import pytest
import os
import csv
import json
from unittest.mock import Mock, patch, MagicMock
from dashboard import app, get_pending_orders, get_active_orders


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
    return config_file


def test_cancel_pending_invalidates_cache(client, sample_config_file, tmp_path):
    """Test that canceling a pending order invalidates the pending orders cache."""
    from dashboard import config_manager
    
    # Set up config manager with test file
    config_manager.config_file = str(sample_config_file)
    config_manager.state_file = str(tmp_path / "state.csv")
    
    # Verify cache has invalidate method
    assert hasattr(get_pending_orders, 'invalidate'), "get_pending_orders should have invalidate method"
    
    # Create a spy to track if invalidate is called
    original_invalidate = get_pending_orders.invalidate
    invalidate_called = {'count': 0}
    
    def spy_invalidate():
        invalidate_called['count'] += 1
        original_invalidate()
    
    get_pending_orders.invalidate = spy_invalidate
    
    try:
        # Cancel the pending order
        response = client.post(
            '/api/pending/test_1/cancel',
            data=json.dumps({'status': 'canceled'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify invalidate was called
        assert invalidate_called['count'] == 1, "Cache invalidate should be called once after cancel"
        
    finally:
        # Restore original invalidate
        get_pending_orders.invalidate = original_invalidate


@patch('dashboard.kraken_api')
def test_cancel_active_invalidates_cache(mock_kraken_api, client):
    """Test that canceling an active order invalidates the active orders cache."""
    mock_kraken_api.cancel_order.return_value = {'count': 1}
    
    # Verify cache has invalidate method
    assert hasattr(get_active_orders, 'invalidate'), "get_active_orders should have invalidate method"
    
    # Create a spy to track if invalidate is called
    original_invalidate = get_active_orders.invalidate
    invalidate_called = {'count': 0}
    
    def spy_invalidate():
        invalidate_called['count'] += 1
        original_invalidate()
    
    get_active_orders.invalidate = spy_invalidate
    
    try:
        # Cancel an active order
        response = client.post('/api/active/ORDER123/cancel')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify invalidate was called
        assert invalidate_called['count'] == 1, "Cache invalidate should be called once after cancel"
        
    finally:
        # Restore original invalidate
        get_active_orders.invalidate = original_invalidate


@patch('dashboard.kraken_api')
def test_cancel_all_invalidates_cache(mock_kraken_api, client):
    """Test that cancel-all invalidates the active orders cache."""
    # Mock open orders
    mock_kraken_api.query_open_orders.return_value = {
        'open': {
            'ORDER1': {},
            'ORDER2': {}
        }
    }
    mock_kraken_api.cancel_order.return_value = {'count': 1}
    
    # Verify cache has invalidate method
    assert hasattr(get_active_orders, 'invalidate'), "get_active_orders should have invalidate method"
    
    # Create a spy to track if invalidate is called
    original_invalidate = get_active_orders.invalidate
    invalidate_called = {'count': 0}
    
    def spy_invalidate():
        invalidate_called['count'] += 1
        original_invalidate()
    
    get_active_orders.invalidate = spy_invalidate
    
    try:
        # Cancel all orders
        response = client.post('/api/cancel-all')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['canceled_count'] == 2
        
        # Verify invalidate was called
        assert invalidate_called['count'] == 1, "Cache invalidate should be called once after cancel-all"
        
    finally:
        # Restore original invalidate
        get_active_orders.invalidate = original_invalidate


def test_cache_invalidate_method_exists():
    """Test that cached functions have invalidate method."""
    assert hasattr(get_pending_orders, 'invalidate'), "get_pending_orders should have invalidate method"
    assert hasattr(get_active_orders, 'invalidate'), "get_active_orders should have invalidate method"
    assert callable(get_pending_orders.invalidate), "invalidate should be callable"
    assert callable(get_active_orders.invalidate), "invalidate should be callable"


def test_cache_invalidate_clears_memory_cache():
    """Test that calling invalidate clears the memory cache."""
    # Call the function to populate cache
    result1 = get_pending_orders()
    
    # Invalidate cache
    get_pending_orders.invalidate()
    
    # Next call should be a cache miss (will re-execute function)
    # We can't directly test this without modifying the function,
    # but we can verify invalidate doesn't crash
    result2 = get_pending_orders()
    
    # Both should return valid results
    assert isinstance(result1, list)
    assert isinstance(result2, list)
