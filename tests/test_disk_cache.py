"""
Tests for disk cache module.
"""
import json
import time
import tempfile
import shutil
from pathlib import Path
from disk_cache import DiskCache


def test_disk_cache_basic_set_get():
    """Test basic set and get operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = DiskCache(cache_dir=tmpdir, default_ttl=300)
        
        # Set a value
        cache.set('test_key', {'data': 'test_value'})
        
        # Get the value back
        result = cache.get('test_key')
        assert result == {'data': 'test_value'}


def test_disk_cache_ttl_expiration():
    """Test that cache entries expire after TTL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = DiskCache(cache_dir=tmpdir, default_ttl=1)  # 1 second TTL
        
        # Set a value
        cache.set('test_key', 'test_value')
        
        # Should be retrievable immediately
        assert cache.get('test_key') == 'test_value'
        
        # Wait for TTL to expire
        time.sleep(1.1)
        
        # Should return None after expiration
        assert cache.get('test_key') is None


def test_disk_cache_custom_ttl():
    """Test using custom TTL on get."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = DiskCache(cache_dir=tmpdir, default_ttl=300)
        
        # Set a value
        cache.set('test_key', 'test_value')
        
        # Get with very short TTL
        time.sleep(0.1)
        result = cache.get('test_key', ttl=0.05)  # 50ms TTL
        
        # Should have expired
        assert result is None


def test_disk_cache_nonexistent_key():
    """Test getting a key that doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = DiskCache(cache_dir=tmpdir)
        
        result = cache.get('nonexistent_key')
        assert result is None


def test_disk_cache_delete():
    """Test deleting cache entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = DiskCache(cache_dir=tmpdir)
        
        # Set a value
        cache.set('test_key', 'test_value')
        assert cache.get('test_key') == 'test_value'
        
        # Delete it
        cache.delete('test_key')
        assert cache.get('test_key') is None


def test_disk_cache_clear():
    """Test clearing all cache entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = DiskCache(cache_dir=tmpdir)
        
        # Set multiple values
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')
        
        # Clear cache
        cache.clear()
        
        # All should be gone
        assert cache.get('key1') is None
        assert cache.get('key2') is None
        assert cache.get('key3') is None


def test_disk_cache_stats():
    """Test cache statistics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = DiskCache(cache_dir=tmpdir)
        
        # Add some entries
        cache.set('key1', {'large': 'data' * 100})
        cache.set('key2', {'more': 'data' * 100})
        
        stats = cache.get_stats()
        
        assert stats['entry_count'] == 2
        assert stats['total_size_bytes'] > 0
        assert stats['total_size_mb'] > 0
        assert tmpdir in stats['cache_dir']


def test_disk_cache_persistence_across_instances():
    """Test that cache persists across different DiskCache instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create first cache instance and set a value
        cache1 = DiskCache(cache_dir=tmpdir, default_ttl=300)
        cache1.set('test_key', 'test_value')
        
        # Create second instance pointing to same directory
        cache2 = DiskCache(cache_dir=tmpdir, default_ttl=300)
        
        # Should be able to read value from second instance
        result = cache2.get('test_key')
        assert result == 'test_value'


def test_disk_cache_key_sanitization():
    """Test that cache keys with special characters are handled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = DiskCache(cache_dir=tmpdir)
        
        # Set value with special characters in key
        cache.set('api/endpoint/path', 'test_value')
        
        # Should be retrievable
        result = cache.get('api/endpoint/path')
        assert result == 'test_value'


def test_disk_cache_complex_data():
    """Test caching complex nested data structures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = DiskCache(cache_dir=tmpdir)
        
        complex_data = {
            'orders': [
                {'id': '123', 'price': 50000.50, 'volume': 1.5},
                {'id': '456', 'price': 3000.25, 'volume': 10.0}
            ],
            'metadata': {
                'timestamp': '2025-01-01T00:00:00',
                'count': 2
            }
        }
        
        cache.set('complex_key', complex_data)
        
        result = cache.get('complex_key')
        assert result == complex_data
        assert result['orders'][0]['id'] == '123'
        assert result['metadata']['count'] == 2
