"""
Tests for Kraken balance normalization with double-prefix assets.

This test specifically addresses the issue where assets with double prefixes
(like XXBT, XXETH) were incorrectly normalized due to lstrip('XZ') removing
ALL leading X/Z characters instead of checking special cases first.

GitHub Issue: "Fix Kraken balance normalization when asset uses double prefix"
"""
import pytest
from kraken_api import KrakenAPI


class TestNormalizeAssetKey:
    """Test the _normalize_asset_key static method."""
    
    def test_btc_variants_normalize_to_xxbt(self):
        """All BTC variants should normalize to XXBT."""
        assert KrakenAPI._normalize_asset_key('XXBT') == 'XXBT'
        assert KrakenAPI._normalize_asset_key('XBT') == 'XXBT'
        assert KrakenAPI._normalize_asset_key('xbt') == 'XXBT'  # lowercase
        assert KrakenAPI._normalize_asset_key('xxbt') == 'XXBT'  # lowercase
    
    def test_btc_funding_wallet_normalizes_to_xxbt(self):
        """BTC funding wallet (.F suffix) should normalize to XXBT."""
        assert KrakenAPI._normalize_asset_key('XBT.F') == 'XXBT'
        assert KrakenAPI._normalize_asset_key('XXBT.F') == 'XXBT'
        assert KrakenAPI._normalize_asset_key('xbt.f') == 'XXBT'  # lowercase
    
    def test_eth_variants_normalize_to_xeth(self):
        """All ETH variants should normalize to XETH."""
        assert KrakenAPI._normalize_asset_key('XETH') == 'XETH'
        assert KrakenAPI._normalize_asset_key('ETH') == 'XETH'
        assert KrakenAPI._normalize_asset_key('XXETH') == 'XETH'  # hypothetical double-prefix
        assert KrakenAPI._normalize_asset_key('eth') == 'XETH'  # lowercase
    
    def test_eth_funding_wallet_normalizes_to_xeth(self):
        """ETH funding wallet (.F suffix) should normalize to XETH."""
        assert KrakenAPI._normalize_asset_key('ETH.F') == 'XETH'
        assert KrakenAPI._normalize_asset_key('XETH.F') == 'XETH'
        assert KrakenAPI._normalize_asset_key('eth.f') == 'XETH'  # lowercase
    
    def test_fiat_currencies_normalize_to_z_prefix(self):
        """Fiat currencies should normalize to Z-prefixed form."""
        assert KrakenAPI._normalize_asset_key('USD') == 'ZUSD'
        assert KrakenAPI._normalize_asset_key('ZUSD') == 'ZUSD'
        assert KrakenAPI._normalize_asset_key('EUR') == 'ZEUR'
        assert KrakenAPI._normalize_asset_key('ZEUR') == 'ZEUR'
        assert KrakenAPI._normalize_asset_key('GBP') == 'ZGBP'
        assert KrakenAPI._normalize_asset_key('ZGBP') == 'ZGBP'
    
    def test_stablecoins_stay_as_is(self):
        """Stablecoins should keep their name without prefix."""
        assert KrakenAPI._normalize_asset_key('USDT') == 'USDT'
        assert KrakenAPI._normalize_asset_key('USDC') == 'USDC'
    
    def test_other_assets_strip_single_x_prefix(self):
        """Other assets with X prefix should have it stripped."""
        assert KrakenAPI._normalize_asset_key('XDYDX') == 'DYDX'
        assert KrakenAPI._normalize_asset_key('XSOL') == 'SOL'
        assert KrakenAPI._normalize_asset_key('XADA') == 'ADA'
    
    def test_assets_without_prefix_stay_as_is(self):
        """Assets without X/Z prefix should stay unchanged."""
        assert KrakenAPI._normalize_asset_key('DYDX') == 'DYDX'
        assert KrakenAPI._normalize_asset_key('SOL') == 'SOL'
        assert KrakenAPI._normalize_asset_key('ADA') == 'ADA'
    
    def test_empty_string_returns_empty(self):
        """Empty string should return empty string."""
        assert KrakenAPI._normalize_asset_key('') == ''
        assert KrakenAPI._normalize_asset_key('  ') == ''  # whitespace only
    
    def test_case_insensitive(self):
        """Normalization should be case-insensitive."""
        assert KrakenAPI._normalize_asset_key('xxbt') == 'XXBT'
        assert KrakenAPI._normalize_asset_key('XbT') == 'XXBT'
        assert KrakenAPI._normalize_asset_key('dYdX') == 'DYDX'


class TestGetNormalizedBalances:
    """Test the get_normalized_balances method."""
    
    def test_aggregates_spot_and_funding_btc(self):
        """BTC in spot and funding wallets should be aggregated under XXBT."""
        # Mock API instance
        api = KrakenAPI()
        
        # Mock the get_balance response
        def mock_get_balance():
            return {
                'XXBT': '1.5',       # Spot wallet
                'XBT.F': '0.5',      # Funding wallet
                'ZUSD': '10000.00'
            }
        
        api.get_balance = mock_get_balance
        
        normalized = api.get_normalized_balances()
        
        # Both BTC variants should be summed under XXBT
        assert 'XXBT' in normalized
        assert normalized['XXBT'] == 2.0  # 1.5 + 0.5
        assert normalized['ZUSD'] == 10000.0
    
    def test_aggregates_spot_and_funding_eth(self):
        """ETH in spot and funding wallets should be aggregated under XETH."""
        api = KrakenAPI()
        
        def mock_get_balance():
            return {
                'XETH': '10.0',      # Spot wallet
                'ETH.F': '5.0',      # Funding wallet
                'ZUSD': '5000.00'
            }
        
        api.get_balance = mock_get_balance
        
        normalized = api.get_normalized_balances()
        
        # Both ETH variants should be summed under XETH
        assert 'XETH' in normalized
        assert normalized['XETH'] == 15.0  # 10.0 + 5.0
    
    def test_handles_only_funding_wallet(self):
        """Should handle case where balance only exists in funding wallet."""
        api = KrakenAPI()
        
        def mock_get_balance():
            return {
                'XXBT': '0.0000000000',  # Spot wallet empty
                'XBT.F': '0.0106906064'  # Only in funding
            }
        
        api.get_balance = mock_get_balance
        
        normalized = api.get_normalized_balances()
        
        # Should still aggregate correctly
        assert 'XXBT' in normalized
        assert normalized['XXBT'] == pytest.approx(0.0106906064)
    
    def test_handles_mixed_assets(self):
        """Should handle multiple different asset types correctly."""
        api = KrakenAPI()
        
        def mock_get_balance():
            return {
                'XXBT': '1.0',
                'XBT.F': '0.5',
                'XETH': '10.0',
                'ETH.F': '2.0',
                'DYDX': '100.0',
                'ZUSD': '5000.0',
                'USD.F': '1000.0',
                'USDT': '500.0'
            }
        
        api.get_balance = mock_get_balance
        
        normalized = api.get_normalized_balances()
        
        # Check all assets are correctly normalized and aggregated
        assert normalized['XXBT'] == 1.5       # 1.0 + 0.5
        assert normalized['XETH'] == 12.0      # 10.0 + 2.0
        assert normalized['DYDX'] == 100.0     # No aggregation
        assert normalized['ZUSD'] == 6000.0    # 5000.0 + 1000.0
        assert normalized['USDT'] == 500.0     # No aggregation
    
    def test_ignores_non_numeric_balances(self):
        """Should skip balances that can't be converted to float."""
        api = KrakenAPI()
        
        def mock_get_balance():
            return {
                'XXBT': '1.0',
                'XETH': 'invalid',  # Bad value
                'DYDX': '100.0',
                'ERROR': 'N/A'       # Bad value
            }
        
        api.get_balance = mock_get_balance
        
        normalized = api.get_normalized_balances()
        
        # Should include valid balances and skip invalid ones
        assert 'XXBT' in normalized
        assert normalized['XXBT'] == 1.0
        assert 'DYDX' in normalized
        assert normalized['DYDX'] == 100.0
        # Invalid ones should not appear or should be 0
        assert 'XETH' not in normalized or normalized.get('XETH', 0) == 0
        assert 'ERROR' not in normalized or normalized.get('ERROR', 0) == 0
