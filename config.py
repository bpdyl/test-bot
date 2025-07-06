import os
from typing import Dict, Any

class Config:
    """Configuration class for IPO Bot settings"""
    
    def __init__(self):
        # Dry run mode - when True, bot will not actually apply IPOs
        self.DRY_RUN_MODE = os.getenv('DRY_RUN_MODE', 'False').lower() == 'true'
        
        # Caching settings
        self.ENABLE_CACHING = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
        self.CACHE_DURATION_MINUTES = int(os.getenv('CACHE_DURATION_MINUTES', '5'))
        
        # Screenshot settings
        self.ENABLE_SCREENSHOTS = os.getenv('ENABLE_SCREENSHOTS', 'true').lower() == 'true'
        self.SCREENSHOT_DIR = os.getenv('SCREENSHOT_DIR', 'screenshots')
        
        # Logging settings
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'ipo_bot.log')
        
        # Application settings
        self.APPLY_TIME = os.getenv('APPLY_TIME', '11:30')
        self.CHECK_INTERVAL_SECONDS = int(os.getenv('CHECK_INTERVAL_SECONDS', '60'))
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for logging"""
        return {
            'DRY_RUN_MODE': self.DRY_RUN_MODE,
            'ENABLE_CACHING': self.ENABLE_CACHING,
            'CACHE_DURATION_MINUTES': self.CACHE_DURATION_MINUTES,
            'ENABLE_SCREENSHOTS': self.ENABLE_SCREENSHOTS,
            'SCREENSHOT_DIR': self.SCREENSHOT_DIR,
            'LOG_LEVEL': self.LOG_LEVEL,
            'APPLY_TIME': self.APPLY_TIME,
            'CHECK_INTERVAL_SECONDS': self.CHECK_INTERVAL_SECONDS
        }

# Global config instance
config = Config() 