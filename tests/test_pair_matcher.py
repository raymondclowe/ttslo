#!/usr/bin/env python3
"""
Tests for the Pair Matcher module.
"""
import pytest
from pair_matcher import (
    find_pair_match,
    normalize_pair_input,
    validate_pair_exists,
    find_similar_pairs,
    PairMatchResult
)


class TestNormalizePairInput:
    """Tests for normalize_pair_input function."""
    
    def test_uppercase_conversion(self):
        """Test that input is converted to uppercase."""
        assert normalize_pair_input('btc/usd') == 'XBTUSD'
        assert normalize_pair_input('eth/eur') == 'ETHEUR'
    
    def test_separator_removal(self):
        """Test that separators are removed."""
        assert normalize_pair_input('BTC/USD') == 'XBTUSD'
        assert normalize_pair_input('BTC-USD') == 'XBTUSD'
        assert normalize_pair_input('BTC_USD') == 'XBTUSD'
        assert normalize_pair_input('BTC USD') == 'XBTUSD'
    
    def test_btc_to_xbt_replacement(self):
        """Test that BTC is replaced with XBT."""
        assert normalize_pair_input('BTC/USD') == 'XBTUSD'
        assert normalize_pair_input('btc/eur') == 'XBTEUR'
        assert normalize_pair_input('BTCUSDT') == 'XBTUSDT'
    
    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is stripped."""
        assert normalize_pair_input('  BTC/USD  ') == 'XBTUSD'
        assert normalize_pair_input('\tETH/EUR\n') == 'ETHEUR'


class TestFindPairMatch:
    """Tests for find_pair_match function."""
    
    def test_exact_match_with_pair_code(self):
        """Test exact match when input is already a pair code."""
        result = find_pair_match('XXBTZUSD')
        assert result is not None
        assert result.pair_code == 'XXBTZUSD'
        assert result.match_type == 'exact'
        assert result.confidence == 1.0
        assert result.is_exact()
        assert result.is_high_confidence()
    
    def test_human_readable_btc_usd(self):
        """Test common BTC/USD format."""
        result = find_pair_match('BTC/USD')
        assert result is not None
        assert result.pair_code == 'XXBTZUSD'
        assert result.kraken_wsname == 'XBT/USD'
        assert result.is_high_confidence()
    
    def test_lowercase_input(self):
        """Test that lowercase input works."""
        result = find_pair_match('btc/usd')
        assert result is not None
        assert result.pair_code == 'XXBTZUSD'
        assert result.is_high_confidence()
    
    def test_no_separator_input(self):
        """Test input without separator (e.g., BTCUSD)."""
        result = find_pair_match('BTCUSD')
        assert result is not None
        assert result.pair_code == 'XXBTZUSD'
    
    def test_eth_usdt(self):
        """Test ETH/USDT pair."""
        result = find_pair_match('ETH/USDT')
        assert result is not None
        assert result.pair_code == 'ETHUSDT'
        assert result.kraken_wsname == 'ETH/USDT'
    
    def test_sol_eur(self):
        """Test SOL/EUR pair."""
        result = find_pair_match('SOL/EUR')
        assert result is not None
        assert result.pair_code == 'SOLEUR'
    
    def test_ada_usd(self):
        """Test ADA/USD pair."""
        result = find_pair_match('ada/usd')
        assert result is not None
        assert result.pair_code == 'ADAUSD'
    
    def test_empty_input(self):
        """Test that empty input returns None."""
        assert find_pair_match('') is None
        assert find_pair_match('   ') is None
        assert find_pair_match(None) is None
    
    def test_invalid_input(self):
        """Test that completely invalid input returns None or low confidence."""
        result = find_pair_match('NOTAREALPAIR123')
        # Should either be None or very low confidence fuzzy match
        if result is not None:
            assert result.confidence < 0.8
    
    def test_case_insensitive(self):
        """Test that matching is case-insensitive."""
        result1 = find_pair_match('BTC/USD')
        result2 = find_pair_match('btc/usd')
        result3 = find_pair_match('Btc/Usd')
        
        assert result1.pair_code == result2.pair_code == result3.pair_code
    
    def test_hyphen_separator(self):
        """Test hyphen as separator."""
        result = find_pair_match('ETH-USD')
        assert result is not None
        assert result.pair_code == 'XETHZUSD'
    
    def test_xethzusd_exact(self):
        """Test XETHZUSD exact match."""
        result = find_pair_match('XETHZUSD')
        assert result is not None
        assert result.pair_code == 'XETHZUSD'
        assert result.match_type == 'exact'


class TestValidatePairExists:
    """Tests for validate_pair_exists function."""
    
    def test_valid_pair_codes(self):
        """Test that known valid pair codes return True."""
        assert validate_pair_exists('XXBTZUSD') is True
        assert validate_pair_exists('XETHZUSD') is True
        assert validate_pair_exists('ETHUSDT') is True
    
    def test_case_insensitive_validation(self):
        """Test that validation is case-insensitive."""
        assert validate_pair_exists('xxbtzusd') is True
        assert validate_pair_exists('XXBTZUSD') is True
    
    def test_invalid_pair_code(self):
        """Test that invalid pair codes return False."""
        assert validate_pair_exists('NOTAPAIR') is False
        assert validate_pair_exists('') is False


class TestFindSimilarPairs:
    """Tests for find_similar_pairs function."""
    
    def test_returns_multiple_results(self):
        """Test that multiple similar pairs are returned."""
        results = find_similar_pairs('BTC', limit=5)
        assert len(results) > 0
        assert len(results) <= 5
    
    def test_sorted_by_confidence(self):
        """Test that results are sorted by confidence (highest first)."""
        results = find_similar_pairs('BTC/USD', limit=5)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].confidence >= results[i + 1].confidence
    
    def test_limit_parameter(self):
        """Test that limit parameter works."""
        results = find_similar_pairs('ETH', limit=3)
        assert len(results) <= 3
    
    def test_empty_input(self):
        """Test that empty input returns empty list."""
        assert find_similar_pairs('') == []
        assert find_similar_pairs('   ') == []


class TestPairMatchResult:
    """Tests for PairMatchResult class."""
    
    def test_exact_match_properties(self):
        """Test properties of exact match result."""
        result = PairMatchResult(
            pair_code='XXBTZUSD',
            confidence=1.0,
            match_type='exact',
            human_input='XXBTZUSD',
            kraken_wsname='XBT/USD'
        )
        
        assert result.is_exact()
        assert result.is_high_confidence()
        assert result.pair_code == 'XXBTZUSD'
        assert result.confidence == 1.0
    
    def test_fuzzy_match_properties(self):
        """Test properties of fuzzy match result."""
        result = PairMatchResult(
            pair_code='XXBTZUSD',
            confidence=0.75,
            match_type='fuzzy',
            human_input='BTCUSD',
            kraken_wsname='XBT/USD'
        )
        
        assert not result.is_exact()
        assert not result.is_high_confidence()
        assert result.match_type == 'fuzzy'
    
    def test_string_representation(self):
        """Test string representation of result."""
        result = PairMatchResult(
            pair_code='XXBTZUSD',
            confidence=0.95,
            match_type='normalized',
            human_input='BTC/USD',
            kraken_wsname='XBT/USD'
        )
        
        str_repr = str(result)
        assert 'XXBTZUSD' in str_repr
        assert 'normalized' in str_repr
        assert '0.95' in str_repr


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""
    
    def test_user_enters_common_pairs(self):
        """Test common user inputs resolve correctly."""
        test_cases = [
            ('BTC/USD', 'XXBTZUSD'),
            ('ETH/USD', 'XETHZUSD'),
            ('BTC/USDT', 'XBTUSDT'),
            ('ETH/USDT', 'ETHUSDT'),
            ('SOL/USD', 'SOLUSD'),
            ('ADA/USD', 'ADAUSD'),
        ]
        
        for human_input, expected_code in test_cases:
            result = find_pair_match(human_input)
            assert result is not None, f"Failed to match {human_input}"
            assert result.pair_code == expected_code, \
                f"Expected {expected_code} for {human_input}, got {result.pair_code}"
            assert result.is_high_confidence(), \
                f"Low confidence for {human_input}: {result.confidence}"
    
    def test_different_input_formats_same_result(self):
        """Test that different formats for same pair resolve to same code."""
        inputs = ['BTC/USD', 'btc/usd', 'BTCUSD', 'btc-usd', 'BTC USD']
        results = [find_pair_match(inp) for inp in inputs]
        
        # All should match
        assert all(r is not None for r in results)
        
        # All should resolve to same pair code
        pair_codes = [r.pair_code for r in results]
        assert len(set(pair_codes)) == 1
        assert pair_codes[0] == 'XXBTZUSD'


def test_all_scenarios():
    """Run all test scenarios."""
    # Run pytest programmatically if needed
    pass


if __name__ == "__main__":
    # Run tests with pytest
    import sys
    sys.exit(pytest.main([__file__, '-v']))
