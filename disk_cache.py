"""
Disk-based cache module for TTSLO.

Provides persistent caching of API responses across restarts.
Uses JSON files in a cache directory with TTL (Time To Live) expiration.
"""
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


class DiskCache:
    """
    Simple disk-based cache with TTL support.
    
    Stores cache entries as JSON files in a cache directory.
    Each entry has a timestamp and expires after TTL seconds.
    """
    
    def __init__(self, cache_dir: str = '.cache', default_ttl: int = 300):
        """
        Initialize disk cache.
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Sanitize key for filesystem
        safe_key = key.replace('/', '_').replace('\\', '_')
        return self.cache_dir / f"{safe_key}.json"
    
    def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """
        Get a value from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
            ttl: Time-to-live in seconds (uses default_ttl if None)
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        ttl = ttl if ttl is not None else self.default_ttl
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            # Check if expired
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            age = (datetime.now() - cache_time).total_seconds()
            
            if age < ttl:
                return cache_data['value']
            else:
                # Cache expired, remove file
                cache_path.unlink(missing_ok=True)
                return None
                
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
            # Cache corrupted or unreadable, remove it
            cache_path.unlink(missing_ok=True)
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
        """
        cache_path = self._get_cache_path(key)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'value': value
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
        except (TypeError, OSError) as e:
            # Silently fail if value not serializable or disk error
            pass
    
    def delete(self, key: str) -> None:
        """Delete a cache entry."""
        cache_path = self._get_cache_path(key)
        cache_path.unlink(missing_ok=True)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        for cache_file in self.cache_dir.glob('*.json'):
            cache_file.unlink(missing_ok=True)
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache size, entry count, etc.
        """
        cache_files = list(self.cache_dir.glob('*.json'))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'cache_dir': str(self.cache_dir),
            'entry_count': len(cache_files),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024)
        }
