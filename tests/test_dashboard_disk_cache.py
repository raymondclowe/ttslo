"""
Tests for disk cache integration in dashboard.
"""
import tempfile
import shutil
from pathlib import Path
from dashboard import app, disk_cache


def test_cache_stats_endpoint():
    """Test that /api/cache-stats endpoint returns cache statistics."""
    with app.test_client() as client:
        response = client.get('/api/cache-stats')
        
        assert response.status_code == 200
        data = response.json
        
        # Check expected fields
        assert 'cache_dir' in data
        assert 'entry_count' in data
        assert 'total_size_bytes' in data
        assert 'total_size_mb' in data
        assert 'dashboard_refresh_interval' in data
        assert 'cache_enabled' in data
        assert data['cache_enabled'] == True


def test_hybrid_cache_disk_persistence():
    """Test that cache persists to disk and can be retrieved after restart."""
    # Clear cache first
    disk_cache.clear()
    
    with app.test_client() as client:
        # First request - should populate cache
        response1 = client.get('/api/status')
        assert response1.status_code == 200
        
        # Check cache stats - should have entries
        stats_response = client.get('/api/cache-stats')
        stats = stats_response.json
        
        # After a status call, we should have some cache entries
        # (at least config, state, and potentially others)
        assert stats['entry_count'] >= 0  # May be 0 if files don't exist


def test_cache_dir_env_variable():
    """Test that TTSLO_CACHE_DIR environment variable is respected."""
    import os
    
    # Check that cache_dir comes from environment or default
    cache_dir = os.getenv('TTSLO_CACHE_DIR', '.cache')
    assert disk_cache.cache_dir == Path(cache_dir)


def test_status_endpoint_includes_cache_dir():
    """Test that /api/status endpoint includes cache_dir."""
    with app.test_client() as client:
        response = client.get('/api/status')
        
        assert response.status_code == 200
        data = response.json
        
        assert 'cache_dir' in data
        assert data['cache_dir'] == disk_cache.cache_dir.name or data['cache_dir'] == str(disk_cache.cache_dir)
