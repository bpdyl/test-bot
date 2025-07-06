import os
import logging
from datetime import datetime
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from config import config

logger = logging.getLogger(__name__)

class ScreenshotManager:
    """Manages screenshot capture for debugging purposes"""
    
    def __init__(self, screenshot_dir: str = None):
        self.screenshot_dir = screenshot_dir or config.SCREENSHOT_DIR
        self.ensure_screenshot_dir()
        
    def ensure_screenshot_dir(self):
        """Ensure screenshot directory exists"""
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
            logger.info(f"Created screenshot directory: {self.screenshot_dir}")
            
    def take_screenshot(self, driver: WebDriver, context: str, error_type: str = "error") -> Optional[str]:
        """Take a screenshot and save it with descriptive filename"""
        if not config.ENABLE_SCREENSHOTS:
            return None
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{error_type}_{context}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            driver.save_screenshot(filepath)
            logger.info(f"Screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
            
    def take_error_screenshot(self, driver: WebDriver, context: str, error_message: str = "") -> Optional[str]:
        """Take a screenshot specifically for error conditions"""
        return self.take_screenshot(driver, context, "error")
        
    def take_debug_screenshot(self, driver: WebDriver, context: str) -> Optional[str]:
        """Take a screenshot for debugging purposes"""
        return self.take_screenshot(driver, context, "debug")
        
    def take_dry_run_screenshot(self, driver: WebDriver, context: str) -> Optional[str]:
        """Take a screenshot during dry run mode"""
        return self.take_screenshot(driver, context, "dry_run")
        
    def cleanup_dry_run_screenshots(self):
        """Clean up all dry run screenshots"""
        if not os.path.exists(self.screenshot_dir):
            return
            
        files_removed = 0
        for filename in os.listdir(self.screenshot_dir):
            if filename.startswith('dry_run_') and filename.endswith('.png'):
                filepath = os.path.join(self.screenshot_dir, filename)
                try:
                    os.remove(filepath)
                    files_removed += 1
                except Exception as e:
                    logger.warning(f"Failed to remove dry run screenshot {filepath}: {e}")
                    
        if files_removed > 0:
            logger.info(f"Cleaned up {files_removed} dry run screenshots")
        
    def cleanup_old_screenshots(self, days_to_keep: int = 7):
        """Clean up screenshots older than specified days"""
        if not os.path.exists(self.screenshot_dir):
            return
            
        current_time = datetime.now()
        files_removed = 0
        
        for filename in os.listdir(self.screenshot_dir):
            if filename.endswith('.png'):
                filepath = os.path.join(self.screenshot_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                
                if (current_time - file_time).days > days_to_keep:
                    try:
                        os.remove(filepath)
                        files_removed += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove old screenshot {filepath}: {e}")
                        
        if files_removed > 0:
            logger.info(f"Cleaned up {files_removed} old screenshots")
            
    def get_screenshot_stats(self) -> dict:
        """Get statistics about screenshots"""
        if not os.path.exists(self.screenshot_dir):
            return {'total_files': 0, 'total_size': 0}
            
        files = [f for f in os.listdir(self.screenshot_dir) if f.endswith('.png')]
        total_size = sum(os.path.getsize(os.path.join(self.screenshot_dir, f)) for f in files)
        
        return {
            'total_files': len(files),
            'total_size': total_size,
            'screenshot_dir': self.screenshot_dir
        }

# Global screenshot manager instance
screenshot_manager = ScreenshotManager() 