"""Browser configuration for Playwright automation.

This module provides a centralized configuration dataclass for Playwright
browser settings, ensuring consistency across all browser automation operations.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
    """Configuration for Playwright browser automation.
    
    This dataclass encapsulates all browser-related configuration settings,
    providing a single source of truth for browser behavior across the application.
    
    Attributes:
        headless: Whether to run browser without GUI (default: True)
        timeout: Default timeout in milliseconds for operations (default: 30000)
        user_agent: User agent string for browser requests
        viewport: Browser viewport dimensions (width, height)
        locale: Browser locale setting (default: "en-US")
        timezone: Browser timezone (default: "America/Guayaquil")
    """
    
    headless: bool = True
    timeout: int = 30000
    user_agent: str = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
    viewport: Dict[str, int] = field(default_factory=lambda: {
        'width': 1920,
        'height': 1080
    })
    locale: str = "en-US"
    timezone: str = "America/Guayaquil"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to Playwright context options.
        
        This method transforms the configuration into a dictionary format
        that can be directly passed to Playwright's browser.new_context() method.
        
        Returns:
            Dictionary of Playwright context options
        """
        return {
            'user_agent': self.user_agent,
            'viewport': self.viewport,
            'locale': self.locale,
            'timezone_id': self.timezone
        }
    
    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"BrowserConfig(headless={self.headless}, "
            f"timeout={self.timeout}ms, "
            f"viewport={self.viewport['width']}x{self.viewport['height']})"
        )
