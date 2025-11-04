"""
Tests for dashboard asset balances and risk analysis functionality.
"""
import pytest
import time
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
        """Test extraction of quote assets - all fiat normalized to Z-prefix."""
        assert _extract_quote_asset('XXBTZUSD') == 'ZUSD'
        assert _extract_quote_asset('SOLUSD') == 'ZUSD'  # USD normalized to ZUSD
        assert _extract_quote_asset('XETHZEUR') == 'ZEUR'
        assert _extract_quote_asset('ADAUSDT') == 'USDT'  # USDT stays as-is (not fiat)


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
        mock_api.get_balance.return_value = {'ATOM': 15.0, 'ZUSD': 5000.0}
        
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
    
    @patch('dashboard.kraken_api')
    @patch('dashboard.get_pending_orders')
    @patch('dashboard.get_active_orders')
    @patch('dashboard.get_current_prices')
    def test_buy_order_checks_quote_currency_not_base(self, mock_prices, mock_active, mock_pending, mock_api, client):
        """Test that BUY orders check quote currency (USD) balance, not base asset (ATOM) balance.
        
        This is the bug reported in the issue:
        - ATOMUSD buy order should check USD balance (to buy ATOM)
        - Should NOT check ATOM balance (you're buying ATOM, not selling it)
        """
        # Wait for cache to expire from previous test (DASHBOARD_REFRESH_INTERVAL = 30s)
        time.sleep(31)
        
        # Import function directly to bypass caching
        from dashboard import get_balances_and_risks
        from kraken_api import KrakenAPI
        
        # Setup: Buy 2.40 ATOM at $10 each = need $24 USD
        mock_pending.return_value = [
            {'pair': 'ATOMUSD', 'direction': 'buy', 'volume': 2.40}
        ]
        mock_active.return_value = []
        mock_prices.return_value = {'ATOMUSD': 10.0}  # $10 per ATOM
        
        # User has 0 ATOM but $50 ZUSD - should be SAFE for buy order
        raw_balance = {'ATOM': 0.0, 'ZUSD': 50.0}
        mock_api.get_balance.return_value = raw_balance
        # Add _normalize_asset_key to the mock
        mock_api._normalize_asset_key = KrakenAPI._normalize_asset_key
        # Provide get_normalized_balances using real normalization logic
        normalized_balance = {
            'ATOM': 0.0,      # ATOM stays as ATOM (no normalization needed)
            'ZUSD': 50.0      # ZUSD stays as ZUSD  
        }
        mock_api.get_normalized_balances.return_value = normalized_balance
        
        # Call function directly, bypassing Flask/cache
        data = get_balances_and_risks()
        
        # Find ATOM and ZUSD assets
        atom_asset = next((a for a in data['assets'] if a['asset'] == 'ATOM'), None)
        zusd_asset = next((a for a in data['assets'] if a['asset'] == 'ZUSD'), None)
        
        # ATOM should NOT show danger/warning (we're buying it, not selling)
        # It should either not appear OR show as safe
        if atom_asset:
            assert atom_asset['risk_status'] == 'safe', \
                f"ATOM should be safe for BUY order (not selling ATOM). Got: {atom_asset['risk_status']}, message: {atom_asset.get('risk_message')}"
            # Main assertion: buy_requirement should be 0 for ATOM (we don't need ATOM to buy ATOM)
            assert atom_asset['buy_requirement'] == 0, "Buy order should not require ATOM balance to buy ATOM"
        
        # ZUSD should show as safe (we have $50, need $24)
        assert zusd_asset is not None, "ZUSD asset should be tracked for buy order"
        assert zusd_asset['risk_status'] == 'safe', \
            f"ZUSD should be safe (have $50, need $24). Got: {zusd_asset['risk_status']}, message: {zusd_asset.get('risk_message')}"
        assert zusd_asset['buy_requirement'] == 24.0, "Should need $24 ZUSD to buy 2.40 ATOM at $10"
        assert zusd_asset['balance'] >= zusd_asset['buy_requirement'], "ZUSD balance should be sufficient"
    
    @patch('dashboard.kraken_api')
    @patch('dashboard.get_pending_orders')
    @patch('dashboard.get_active_orders')
    @patch('dashboard.get_current_prices')
    def test_sell_order_checks_base_currency_not_quote(self, mock_prices, mock_active, mock_pending, mock_api, client):
        """Test that SELL orders check base currency (ATOM) balance, not quote (USD)."""
        # Wait for cache to expire from previous test (DASHBOARD_REFRESH_INTERVAL = 30s)
        time.sleep(31)
        
        # Import function directly to bypass caching
        from dashboard import get_balances_and_risks
        
        # Setup: Sell 2.40 ATOM
        mock_pending.return_value = [
            {'pair': 'ATOMUSD', 'direction': 'sell', 'volume': 2.40}
        ]
        mock_active.return_value = []
        mock_prices.return_value = {'ATOMUSD': 10.0}
        
        # User has 0 ATOM but lots of ZUSD - should be DANGER for sell order
        mock_api.get_balance.return_value = {'ATOM': 0.0, 'ZUSD': 5000.0}
        
        # Call function directly, bypassing Flask/cache
        data = get_balances_and_risks()
        
        # Find ATOM asset
        atom_asset = next((a for a in data['assets'] if a['asset'] == 'ATOM'), None)
        
        # ATOM should show danger (insufficient balance for sell)
        assert atom_asset is not None, "ATOM asset should be tracked"
        assert atom_asset['risk_status'] == 'danger', \
            f"ATOM should be danger (0 ATOM < 2.40 needed). Got: {atom_asset['risk_status']}"
        assert atom_asset['sell_requirement'] == 2.40, "Should need 2.40 ATOM to sell"
        assert atom_asset['balance'] < atom_asset['sell_requirement'], "ATOM balance insufficient"
