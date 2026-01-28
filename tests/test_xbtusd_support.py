"""
Test XBTUSD pair support.

Tests that both XBTUSD (altname) and XXBTZUSD (pair code) are properly supported.
Also tests XBTUSDC support.
"""
import pytest
from validator import ConfigValidator
from pair_matcher import find_pair_match


class TestXBTUSDSupport:
    """Test that XBTUSD altname is properly supported."""
    
    def test_xbtusd_accepted_by_validator(self):
        """Test that validator accepts XBTUSD (altname)."""
        validator = ConfigValidator(kraken_api=None)
        known_pairs = validator._get_known_pairs()
        
        # XBTUSD is an altname, should be accepted
        assert 'XBTUSD' in known_pairs, "XBTUSD (altname) should be in known pairs"
        
    def test_xxbtzusd_accepted_by_validator(self):
        """Test that validator accepts XXBTZUSD (pair code)."""
        validator = ConfigValidator(kraken_api=None)
        known_pairs = validator._get_known_pairs()
        
        # XXBTZUSD is the actual pair code
        assert 'XXBTZUSD' in known_pairs, "XXBTZUSD (pair code) should be in known pairs"
    
    def test_xbtusdc_accepted_by_validator(self):
        """Test that validator accepts XBTUSDC."""
        validator = ConfigValidator(kraken_api=None)
        known_pairs = validator._get_known_pairs()
        
        # XBTUSDC is both pair code and altname
        assert 'XBTUSDC' in known_pairs, "XBTUSDC should be in known pairs"
    
    def test_pair_matcher_resolves_xbtusd(self):
        """Test that pair matcher resolves XBTUSD to XXBTZUSD."""
        result = find_pair_match('XBTUSD')
        
        assert result is not None, "XBTUSD should match a pair"
        assert result.pair_code == 'XXBTZUSD', "XBTUSD should resolve to XXBTZUSD"
        assert result.confidence == 1.0, "Should be exact match"
        
    def test_pair_matcher_resolves_xbtusdc(self):
        """Test that pair matcher resolves XBTUSDC correctly."""
        result = find_pair_match('XBTUSDC')
        
        assert result is not None, "XBTUSDC should match a pair"
        assert result.pair_code == 'XBTUSDC', "XBTUSDC should resolve to XBTUSDC"
        assert result.confidence == 1.0, "Should be exact match"


class TestUSDCSupport:
    """Test that USDC pairs are properly supported in base/quote extraction."""
    
    def test_usdc_in_quote_list(self):
        """Test that USDC is checked before USD in quote extraction."""
        # This is important because 'USDC' should be matched before 'USD'
        # to avoid incorrectly extracting 'XBTUS' as base and 'DC' as garbage
        from ttslo import TTSLO
        
        # Create a minimal TTSLO instance (we only need the extraction methods)
        ttslo = TTSLO(
            config_manager=None,
            kraken_api_readonly=None,
            dry_run=True
        )
        
        # Test _extract_base_asset for USDC pairs
        assert ttslo._extract_base_asset('XBTUSDC') == 'XXBT' or ttslo._extract_base_asset('XBTUSDC') == 'XBT'
        assert ttslo._extract_base_asset('ETHUSDC') == 'XETH' or ttslo._extract_base_asset('ETHUSDC') == 'ETH'
        
        # Test _extract_quote_asset for USDC pairs
        assert ttslo._extract_quote_asset('XBTUSDC') == 'USDC'
        assert ttslo._extract_quote_asset('ETHUSDC') == 'USDC'
