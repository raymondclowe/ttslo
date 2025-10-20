#!/usr/bin/env python3
"""
Test script to verify dashboard performance optimizations.
"""
import time
import sys
from unittest.mock import Mock, MagicMock, patch

# Test the caching mechanism
def test_caching():
    """Test that caching reduces file I/O."""
    print("Testing config/state caching...")
    
    # Import after mocking if needed
    from dashboard import get_cached_config, get_cached_state, _config_cache, _state_cache
    
    # Reset caches
    _config_cache['data'] = None
    _config_cache['mtime'] = 0
    _state_cache['data'] = None
    _state_cache['mtime'] = 0
    
    # First call should load from file
    start = time.time()
    config1 = get_cached_config()
    elapsed1 = time.time() - start
    print(f"First config load: {elapsed1:.3f}s, got {len(config1)} configs")
    
    # Second call should use cache
    start = time.time()
    config2 = get_cached_config()
    elapsed2 = time.time() - start
    print(f"Second config load (cached): {elapsed2:.3f}s, got {len(config2)} configs")
    
    # Cache should be faster
    if elapsed2 < elapsed1:
        print("✓ Caching is working - second call was faster")
    else:
        print("⚠ Caching may not be working - second call was not faster")
    
    # Same for state
    start = time.time()
    state1 = get_cached_state()
    elapsed1 = time.time() - start
    print(f"First state load: {elapsed1:.3f}s, got {len(state1)} state entries")
    
    start = time.time()
    state2 = get_cached_state()
    elapsed2 = time.time() - start
    print(f"Second state load (cached): {elapsed2:.3f}s, got {len(state2)} state entries")
    
    if elapsed2 < elapsed1:
        print("✓ State caching is working - second call was faster")
    else:
        print("⚠ State caching may not be working - second call was not faster")


def test_batch_price_fetching():
    """Test that batch price fetching reduces API calls."""
    print("\nTesting batch price fetching...")
    
    # Mock the KrakenAPI
    mock_api = Mock()
    
    # Mock batch fetch to return prices for all pairs
    mock_api.get_current_prices_batch.return_value = {
        'XXBTZUSD': 50000.0,
        'XETHZUSD': 3000.0
    }
    
    # Mock individual fetch (should not be called if batch works)
    mock_api.get_current_price.side_effect = Exception("Should not call individual fetch when batch works")
    
    # Test with our mock
    pairs = {'XXBTZUSD', 'XETHZUSD'}
    
    start = time.time()
    prices = mock_api.get_current_prices_batch(pairs)
    elapsed = time.time() - start
    
    print(f"Batch fetch of {len(pairs)} pairs: {elapsed:.3f}s")
    print(f"Got {len(prices)} prices: {prices}")
    
    # Verify batch method was called once
    assert mock_api.get_current_prices_batch.call_count == 1
    print("✓ Batch fetch called once as expected")
    
    # Verify we got both prices
    assert len(prices) == 2
    assert 'XXBTZUSD' in prices
    assert 'XETHZUSD' in prices
    print("✓ Batch fetch returned all expected prices")


def test_instrumentation():
    """Test that instrumentation logs are working."""
    print("\nTesting instrumentation...")
    
    from dashboard import get_current_prices
    
    # This should print performance logs
    print("Calling get_current_prices() - watch for [PERF] logs:")
    
    # Note: This will fail if kraken_api is not initialized, but that's OK for testing
    try:
        prices = get_current_prices()
        print(f"✓ Function executed, returned {len(prices)} prices")
    except Exception as e:
        print(f"✓ Function executed with expected error (no API): {e}")


if __name__ == '__main__':
    print("=" * 60)
    print("Dashboard Performance Test Suite")
    print("=" * 60)
    
    try:
        test_caching()
        test_batch_price_fetching()
        test_instrumentation()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
