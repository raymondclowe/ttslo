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
            'order_id', 'activated_on', 'last_checked'
        ])
        writer.writeheader()
        writer.writerow({
            'id': 'test_1',
            'triggered': 'false',
            'trigger_price': '',
            'trigger_time': '',
            'order_id': '',
            'activated_on': '',
            'last_checked': ''
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
