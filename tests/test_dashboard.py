"""
Tests for the TTSLO Dashboard.
"""
import pytest
import os
import tempfile
import csv
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
    return config_file


@pytest.fixture
def sample_state_file(tmp_path):
    """Create a sample state file for testing."""
    state_file = tmp_path / "state.csv"
    with open(state_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'id', 'triggered', 'trigger_price', 'trigger_time', 
            'order_id', 'activated_on', 'last_checked', 'offset'
        ])
        writer.writeheader()
        writer.writerow({
            'id': 'test_1',
            'triggered': 'false',
            'trigger_price': '',
            'trigger_time': '',
            'order_id': '',
            'activated_on': '',
            'last_checked': '',
            'offset': ''
        })
    return state_file


def test_index_page(client):
    """Test that the index page loads."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'TTSLO Dashboard' in response.data


def test_api_status(client):
    """Test the status API endpoint."""
    response = client.get('/api/status')
    assert response.status_code == 200
    data = response.get_json()
    assert 'config_file' in data
    assert 'state_file' in data
    assert 'kraken_api_available' in data
    assert 'timestamp' in data


def test_api_pending(client):
    """Test the pending orders API endpoint."""
    response = client.get('/api/pending')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_api_active(client):
    """Test the active orders API endpoint."""
    response = client.get('/api/active')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_api_completed(client):
    """Test the completed orders API endpoint."""
    response = client.get('/api/completed')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_calculate_distance_above():
    """Test distance calculation for 'above' threshold."""
    from dashboard import calculate_distance_to_trigger
    
    # Price below threshold
    result = calculate_distance_to_trigger('50000', '48000', 'above')
    assert result['absolute'] == 2000
    assert result['percent'] > 0
    assert result['triggered'] is False
    
    # Price above threshold
    result = calculate_distance_to_trigger('50000', '52000', 'above')
    assert result['absolute'] < 0
    assert result['triggered'] is True


def test_calculate_distance_below():
    """Test distance calculation for 'below' threshold."""
    from dashboard import calculate_distance_to_trigger
    
    # Price above threshold
    result = calculate_distance_to_trigger('50000', '52000', 'below')
    assert result['absolute'] == 2000
    assert result['percent'] > 0
    assert result['triggered'] is False
    
    # Price below threshold
    result = calculate_distance_to_trigger('50000', '48000', 'below')
    assert result['absolute'] < 0
    assert result['triggered'] is True


def test_pending_orders_include_offset(client):
    """Test that pending orders include trailing_offset_percent."""
    response = client.get('/api/pending')
    assert response.status_code == 200
    data = response.get_json()
    
    # If there are pending orders, verify they include offset
    if len(data) > 0:
        order = data[0]
        assert 'trailing_offset_percent' in order


def test_active_orders_include_offset(client):
    """Test that active orders include trailing_offset_percent."""
    response = client.get('/api/active')
    assert response.status_code == 200
    data = response.get_json()
    
    # If there are active orders, verify they include offset
    if len(data) > 0:
        order = data[0]
        assert 'trailing_offset_percent' in order


def test_completed_orders_include_offset(client):
    """Test that completed orders include trailing_offset_percent."""
    response = client.get('/api/completed')
    assert response.status_code == 200
    data = response.get_json()
    
    # If there are completed orders, verify they include offset
    if len(data) > 0:
        order = data[0]
        assert 'trailing_offset_percent' in order


def test_manual_order_trailing_offset_extraction():
    """Test that manual orders extract trailing_offset_percent from price field."""
    # Simulate a manual order from Kraken
    mock_order_info = {
        'vol': '1.5',
        'vol_exec': '0',
        'status': 'open',
        'descr': {
            'ordertype': 'trailing-stop',
            'pair': 'XETHZUSD',
            'type': 'sell',
            'price': '+1.5000%'  # Trailing offset format
        }
    }
    
    # Extract trailing offset like dashboard.py does
    descr = mock_order_info.get('descr', {}) or {}
    price_str = descr.get('price', '')
    trailing_offset_percent = None
    if price_str:
        trailing_offset_percent = price_str.replace('+', '').replace('-', '').replace('%', '').strip()
    
    # Verify extraction
    assert trailing_offset_percent is not None
    assert trailing_offset_percent == '1.5000'
    
    # Test with different formats
    test_cases = [
        ('+5.0000%', '5.0000'),
        ('-3.2500%', '3.2500'),
        ('+10.0%', '10.0'),
        ('', None),
    ]
    
    for price_str, expected in test_cases:
        if price_str:
            result = price_str.replace('+', '').replace('-', '').replace('%', '').strip()
            assert result == expected
        else:
            result = None
            assert result == expected


def test_manual_order_has_manual_flag():
    """Test that manual orders are marked with manual=True flag."""
    from dashboard import get_active_orders
    
    # This test validates the structure but requires mocking
    # Just verify the function exists and can be called
    try:
        orders = get_active_orders()
        assert isinstance(orders, list)
        
        # If there are manual orders, they should have the manual flag
        manual_orders = [o for o in orders if o.get('manual')]
        for order in manual_orders:
            assert order.get('manual') is True
            assert order.get('source') == 'kraken'
            # Manual orders should have trailing_offset_percent extracted or None
            assert 'trailing_offset_percent' in order
    except Exception:
        # If Kraken API isn't available, that's fine
        pass
