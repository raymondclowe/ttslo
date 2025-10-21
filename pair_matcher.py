#!/usr/bin/env python3
"""
Pair Matcher - Resolve human-readable trading pair names to Kraken pair codes.

This module helps users enter trading pairs in a human-readable format like:
- BTC/USD, btc/usd, BTCUSD
- ETH/USDT, eth/usdt, ETHUSDT
- SOL/EUR, sol/eur, SOLEUR

And automatically resolves them to the official Kraken pair codes like:
- XXBTZUSD (for BTC/USD)
- XBTUSDT (for BTC/USDT)
- XETHZUSD (for ETH/USD)
- SOLUSD (for SOL/EUR)

The module uses a combination of exact matching and fuzzy matching to find
the correct pair code, and returns a confidence score to indicate the quality
of the match.
"""

from typing import Optional, Tuple, List
from difflib import SequenceMatcher
from kraken_pairs_util import get_cached_pairs, fetch_kraken_pairs


class PairMatchResult:
    """Result of a pair matching operation."""
    
    def __init__(self, pair_code: str, confidence: float, match_type: str, 
                 human_input: str, kraken_wsname: str = ""):
        """
        Initialize a pair match result.
        
        Args:
            pair_code: The official Kraken pair code (e.g., 'XXBTZUSD')
            confidence: Match confidence from 0.0 to 1.0
            match_type: Type of match ('exact', 'normalized', 'fuzzy')
            human_input: The original human input
            kraken_wsname: The Kraken websocket name (e.g., 'XBT/USD')
        """
        self.pair_code = pair_code
        self.confidence = confidence
        self.match_type = match_type
        self.human_input = human_input
        self.kraken_wsname = kraken_wsname
    
    def is_exact(self) -> bool:
        """Returns True if this is an exact match."""
        return self.match_type == 'exact'
    
    def is_high_confidence(self) -> bool:
        """Returns True if confidence is high (>= 0.9)."""
        return self.confidence >= 0.9
    
    def __str__(self) -> str:
        """String representation of the match result."""
        return f"{self.pair_code} ({self.match_type}, confidence: {self.confidence:.2f})"


def normalize_pair_input(human_input: str) -> str:
    """
    Normalize human input for matching.
    
    Examples:
        'BTC/USD' -> 'XBTUSD'
        'btc/usdt' -> 'XBTUSDT'
        'eth-usd' -> 'ETHUSD'
        
    Args:
        human_input: The human-readable pair name
        
    Returns:
        Normalized string ready for matching
    """
    # Convert to uppercase
    normalized = human_input.upper().strip()
    
    # Remove common separators
    normalized = normalized.replace('/', '').replace('-', '').replace('_', '').replace(' ', '')
    
    # Replace common aliases
    normalized = normalized.replace('BTC', 'XBT')
    
    return normalized


def find_pair_match(human_input: str) -> Optional[PairMatchResult]:
    """
    Find the best matching Kraken pair code for human-readable input.
    
    This function tries multiple matching strategies in order:
    1. Exact match against pair codes
    2. Exact match against altnames
    3. Normalized match against wsnames (e.g., 'BTC/USD' -> 'XBT/USD')
    4. Fuzzy match with confidence scoring
    
    Args:
        human_input: The human-readable pair name (e.g., 'BTC/USD', 'eth/usdt')
        
    Returns:
        PairMatchResult if a match is found, None otherwise
    """
    if not human_input or not human_input.strip():
        return None
    
    try:
        # Get all Kraken pairs
        pairs_data = fetch_kraken_pairs()
        
        # Strategy 1: Exact match against pair codes
        human_upper = human_input.upper().strip()
        if human_upper in pairs_data:
            pair_info = pairs_data[human_upper]
            return PairMatchResult(
                pair_code=human_upper,
                confidence=1.0,
                match_type='exact',
                human_input=human_input,
                kraken_wsname=pair_info.get('wsname', '')
            )
        
        # Strategy 2: Exact match against altnames
        for pair_code, pair_info in pairs_data.items():
            altname = pair_info.get('altname', '').upper()
            if altname == human_upper:
                return PairMatchResult(
                    pair_code=pair_code,
                    confidence=1.0,
                    match_type='exact',
                    human_input=human_input,
                    kraken_wsname=pair_info.get('wsname', '')
                )
        
        # Strategy 3: Normalized match against wsnames
        # Normalize the input (remove separators, replace BTC with XBT)
        normalized_input = normalize_pair_input(human_input)
        
        # Check if input looks like "BASE/QUOTE" format
        slash_parts = human_input.upper().strip().split('/')
        if len(slash_parts) == 2:
            base, quote = slash_parts
            base = base.strip().replace('BTC', 'XBT')
            quote = quote.strip()
            wsname_target = f"{base}/{quote}"
            
            # Look for exact wsname match
            for pair_code, pair_info in pairs_data.items():
                wsname = pair_info.get('wsname', '')
                if wsname == wsname_target:
                    return PairMatchResult(
                        pair_code=pair_code,
                        confidence=1.0,
                        match_type='normalized',
                        human_input=human_input,
                        kraken_wsname=wsname
                    )
        
        # Try to match normalized input against normalized wsnames
        for pair_code, pair_info in pairs_data.items():
            wsname = pair_info.get('wsname', '')
            normalized_wsname = normalize_pair_input(wsname)
            
            if normalized_wsname == normalized_input:
                return PairMatchResult(
                    pair_code=pair_code,
                    confidence=0.95,
                    match_type='normalized',
                    human_input=human_input,
                    kraken_wsname=wsname
                )
        
        # Strategy 4: Fuzzy matching
        # Find best fuzzy match with confidence score
        best_match = None
        best_score = 0.0
        
        for pair_code, pair_info in pairs_data.items():
            wsname = pair_info.get('wsname', '')
            altname = pair_info.get('altname', '')
            
            # Calculate similarity scores
            wsname_score = SequenceMatcher(None, normalized_input, normalize_pair_input(wsname)).ratio()
            altname_score = SequenceMatcher(None, normalized_input, normalize_pair_input(altname)).ratio()
            pair_code_score = SequenceMatcher(None, normalized_input, pair_code.upper()).ratio()
            
            # Take the best score
            max_score = max(wsname_score, altname_score, pair_code_score)
            
            if max_score > best_score:
                best_score = max_score
                best_match = (pair_code, wsname)
        
        # Only return fuzzy matches if confidence is reasonable (> 0.7)
        if best_match and best_score > 0.7:
            return PairMatchResult(
                pair_code=best_match[0],
                confidence=best_score,
                match_type='fuzzy',
                human_input=human_input,
                kraken_wsname=best_match[1]
            )
        
        return None
        
    except Exception as e:
        # If we can't fetch pairs data, return None
        return None


def find_similar_pairs(human_input: str, limit: int = 5) -> List[PairMatchResult]:
    """
    Find multiple similar pair matches for suggestions.
    
    This is useful for showing the user multiple options when their input
    is ambiguous or when a fuzzy match isn't confident enough.
    
    Args:
        human_input: The human-readable pair name
        limit: Maximum number of results to return
        
    Returns:
        List of PairMatchResult objects, sorted by confidence (highest first)
    """
    if not human_input or not human_input.strip():
        return []
    
    try:
        pairs_data = fetch_kraken_pairs()
        normalized_input = normalize_pair_input(human_input)
        
        matches = []
        
        for pair_code, pair_info in pairs_data.items():
            wsname = pair_info.get('wsname', '')
            altname = pair_info.get('altname', '')
            
            # Calculate similarity scores
            wsname_score = SequenceMatcher(None, normalized_input, normalize_pair_input(wsname)).ratio()
            altname_score = SequenceMatcher(None, normalized_input, normalize_pair_input(altname)).ratio()
            pair_code_score = SequenceMatcher(None, normalized_input, pair_code.upper()).ratio()
            
            # Take the best score
            max_score = max(wsname_score, altname_score, pair_code_score)
            
            # Only include if score is reasonable
            if max_score > 0.5:
                matches.append(PairMatchResult(
                    pair_code=pair_code,
                    confidence=max_score,
                    match_type='fuzzy' if max_score < 0.95 else 'normalized',
                    human_input=human_input,
                    kraken_wsname=wsname
                ))
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)
        
        return matches[:limit]
        
    except Exception:
        return []


def validate_pair_exists(pair_code: str) -> bool:
    """
    Check if a pair code exists in Kraken's trading pairs.
    
    Args:
        pair_code: The Kraken pair code to validate
        
    Returns:
        True if the pair exists, False otherwise
    """
    try:
        pair_codes = get_cached_pairs()
        return pair_code.upper() in pair_codes
    except Exception:
        return False


# Example usage
if __name__ == "__main__":
    # Test various inputs
    test_inputs = [
        'BTC/USD',
        'btc/usd',
        'BTCUSD',
        'ETH/USDT',
        'eth-usdt',
        'SOL/EUR',
        'XXBTZUSD',  # Already a pair code
        'ada/usd',
        'BTC/USDT',
    ]
    
    print("Pair Matcher Test Results")
    print("=" * 60)
    
    for human_input in test_inputs:
        result = find_pair_match(human_input)
        if result:
            print(f"\nInput: '{human_input}'")
            print(f"  → {result.pair_code}")
            print(f"  wsname: {result.kraken_wsname}")
            print(f"  match: {result.match_type}")
            print(f"  confidence: {result.confidence:.2%}")
            if not result.is_high_confidence():
                print(f"  ⚠️  Low confidence - verify this is correct")
        else:
            print(f"\nInput: '{human_input}' → NO MATCH FOUND")
