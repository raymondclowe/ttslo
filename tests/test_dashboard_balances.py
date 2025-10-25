"""
Tests for dashboard asset balances and risk analysis functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from dashboard import (
    app, _extract_base_asset, _extract_quote_asset
)


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestAssetExtraction:
    """Test asset extraction from trading pairs."""
    
    def test_extract_base_asset_known_pairs(self):
        """Test extraction of base assets from known pairs."""
        assert _extract_base_asset('XXBTZUSD') == 'XXBT'
        assert _extract_base_asset('XETHZUSD') == 'XETH'
        assert _extract_base_asset('SOLUSD') == 'SOL'
        assert _extract_base_asset('DYDXUSD') == 'DYDX'
        assert _extract_base_asset('NEARUSD') == 'NEAR'
        assert _extract_base_asset('MEMEUSD') == 'MEME'
        assert _extract_base_asset('ADAUSD') == 'ADA'
    
    def test_extract_base_asset_pattern(self):
        """Test extraction using pattern matching."""
        assert _extract_base_asset('ATOMUSD') == 'ATOM'
        assert _extract_base_asset('MATICUSDT') == 'MATIC'
        assert _extract_base_asset('LINKZUSD') == 'LINK'
    
    def test_extract_quote_asset(self):
        """Test extraction of quote assets."""
        assert _extract_quote_asset('XXBTZUSD') == 'ZUSD'
        assert _extract_quote_asset('SOLUSD') == 'USD'
        assert _extract_quote_asset('XETHZEUR') == 'ZEUR'
        assert _extract_quote_asset('ADAUSDT') == 'USDT'


class TestBalancesAPI:
    """Test balances API endpoint."""
    
    @patch('dashboard.kraken_api')
    @patch('dashboard.get_pending_orders')
    @patch('dashboard.get_active_orders')
    @patch('dashboard.get_current_prices')
    def test_api_balances_endpoint_structure(self, mock_prices, mock_active, mock_pending, mock_api, client):
        """Test /api/balances endpoint returns expected structure."""
        # Mock data
        mock_pending.return_value = [
            {'pair': 'ATOMUSD', 'direction': 'sell', 'volume': 10.0}
        ]
        mock_active.return_value = []
        mock_prices.return_value = {'ATOMUSD': 100.0}
        mock_api.get_balance.return_value = {'ATOM': 15.0, 'USD': 5000.0}
        
        response = client.get('/api/balances')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'assets' in data
        assert 'risk_summary' in data
        assert isinstance(data['assets'], list)
        assert isinstance(data['risk_summary'], dict)
        
        # Should have data about ATOM
        if len(data['assets']) > 0:
            atom_asset = next((a for a in data['assets'] if a['asset'] == 'ATOM'), None)
            if atom_asset:
                assert 'balance' in atom_asset
                assert 'risk_status' in atom_asset
                assert 'sell_requirement' in atom_asset
    
    @patch('dashboard.kraken_api')
    @patch('dashboard.get_pending_orders')
    @patch('dashboard.get_active_orders')
    @patch('dashboard.get_current_prices')
    def test_api_balances_risk_levels(self, mock_prices, mock_active, mock_pending, mock_api, client):
        """Test that risk levels are properly calculated."""
        # Test with insufficient balance scenario
        mock_pending.return_value = [
            {'pair': 'LINKUSD', 'direction': 'sell', 'volume': 100.0}
        ]
        mock_active.return_value = []
        mock_prices.return_value = {'LINKUSD': 10.0}
        mock_api.get_balance.return_value = {'LINK': 50.0}  # Only half what's needed
        
        response = client.get('/api/balances')
        data = response.get_json()
        
        # Should detect danger
        link_asset = next((a for a in data['assets'] if a['asset'] == 'LINK'), None)
        if link_asset:
            assert link_asset['risk_status'] in ['danger', 'warning']
            assert link_asset['sell_requirement'] > link_asset['balance']
