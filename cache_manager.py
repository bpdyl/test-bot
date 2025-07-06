import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from config import config

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages caching for IPO data and other frequently accessed information"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.ensure_cache_dir()
        
    def ensure_cache_dir(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def _get_cache_file_path(self, key: str) -> str:
        """Get the file path for a cache key"""
        return os.path.join(self.cache_dir, f"{key}.json")
        
    def get(self, key: str) -> Optional[Any]:
        """Retrieve data from cache if it exists and is not expired"""
        if not config.ENABLE_CACHING:
            return None
            
        cache_file = self._get_cache_file_path(key)
        
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                
            # Check if cache is expired
            cache_time = datetime.fromisoformat(cached_data['timestamp'])
            expiry_time = cache_time + timedelta(minutes=config.CACHE_DURATION_MINUTES)
            
            if datetime.now() > expiry_time:
                logger.info(f"Cache expired for key: {key}")
                self.delete(key)
                return None
                
            logger.info(f"Cache hit for key: {key}")
            return cached_data['data']
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Error reading cache for key {key}: {e}")
            self.delete(key)
            return None
            
    def set(self, key: str, data: Any) -> None:
        """Store data in cache with timestamp"""
        if not config.ENABLE_CACHING:
            return
            
        cache_file = self._get_cache_file_path(key)
        
        try:
            cache_data = {
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'expires_in_minutes': config.CACHE_DURATION_MINUTES
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.info(f"Cached data for key: {key}")
            
        except Exception as e:
            logger.error(f"Error writing cache for key {key}: {e}")
            
    def delete(self, key: str) -> None:
        """Delete a specific cache entry"""
        cache_file = self._get_cache_file_path(key)
        if os.path.exists(cache_file):
            os.remove(cache_file)
            logger.info(f"Deleted cache for key: {key}")
            
    def clear_all(self) -> None:
        """Clear all cache entries"""
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                if file.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, file))
            logger.info("Cleared all cache entries")
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache"""
        if not os.path.exists(self.cache_dir):
            return {'total_files': 0, 'total_size': 0}
            
        files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in files)
        
        return {
            'total_files': len(files),
            'total_size': total_size,
            'cache_dir': self.cache_dir
        }

# Global cache manager instance
cache_manager = CacheManager() 