"""Playwright browser lifecycle manager.

This module provides a centralized manager for Playwright browser operations,
ensuring consistent resource management and cleanup across all browser automation.
"""

import logging
from typing import Callable, Any, List, Dict
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from .browser_config import BrowserConfig

logger = logging.getLogger(__name__)


class PlaywrightManager:
    """Manages Playwright browser lifecycle and scraping operations.
    
    This class encapsulates all Playwright browser management logic,
    providing a clean interface for browser automation while ensuring
    proper resource cleanup even when errors occur.
    
    Features:
    - Automatic browser lifecycle management
    - Context manager support for guaranteed cleanup
    - Configurable browser settings via BrowserConfig
    - Exception-safe resource cleanup
    
    Attributes:
        config: Browser configuration settings
    """
    
    def __init__(self, config: BrowserConfig = None):
        """Initialize PlaywrightManager with configuration.
        
        Args:
            config: Browser configuration (creates default if not provided)
        """
        self.config = config or BrowserConfig()
        logger.debug(f"PlaywrightManager initialized with {self.config}")
    
    def scrape(
        self,
        url: str,
        scraper: Callable[[Page], Any]
    ) -> Any:
        """Execute scraping operation with managed browser lifecycle.
        
        This method handles the complete browser lifecycle:
        1. Launch browser
        2. Create context with configuration
        3. Navigate to URL
        4. Execute scraper function
        5. Clean up resources (even on error)
        
        Args:
            url: URL to navigate to
            scraper: Function that takes a Page and returns scraped data
            
        Returns:
            Result from scraper function
            
        Raises:
            Exception: If browser operations or scraping fails
        """
        logger.info(f"Starting Playwright scraping session for {url}")
        
        with sync_playwright() as playwright:
            browser = None
            context = None
            page = None
            
            try:
                # Launch browser
                browser = playwright.chromium.launch(
                    headless=self.config.headless
                )
                logger.debug("Browser launched")
                
                # Create context with configuration
                context = browser.new_context(**self.config.to_dict())
                logger.debug("Browser context created")
                
                # Create page
                page = context.new_page()
                
                # Navigate to URL
                logger.debug(f"Navigating to {url}")
                page.goto(url, wait_until='networkidle', timeout=self.config.timeout)
                
                # Execute scraper function
                logger.debug("Executing scraper function")
                result = scraper(page)
                
                logger.info("Scraping completed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Error during scraping: {e}")
                raise
                
            finally:
                # Clean up resources in reverse order
                if page:
                    try:
                        page.close()
                        logger.debug("Page closed")
                    except Exception as e:
                        logger.warning(f"Error closing page: {e}")
                
                if context:
                    try:
                        context.close()
                        logger.debug("Context closed")
                    except Exception as e:
                        logger.warning(f"Error closing context: {e}")
                
                if browser:
                    try:
                        browser.close()
                        logger.debug("Browser closed")
                    except Exception as e:
                        logger.warning(f"Error closing browser: {e}")
    
    def scrape_with_auth(
        self,
        url: str,
        authenticator: Callable[[Page, BrowserContext], bool],
        scraper: Callable[[Page], Any]
    ) -> Any:
        """Execute scraping with authentication.
        
        This method extends scrape() to support authentication before scraping.
        Useful for sites that require login.
        
        Args:
            url: URL to navigate to after authentication
            authenticator: Function that performs authentication
            scraper: Function that performs scraping
            
        Returns:
            Result from scraper function
            
        Raises:
            Exception: If authentication or scraping fails
        """
        logger.info(f"Starting authenticated Playwright session for {url}")
        
        with sync_playwright() as playwright:
            browser = None
            context = None
            page = None
            
            try:
                # Launch browser
                browser = playwright.chromium.launch(
                    headless=self.config.headless
                )
                
                # Create context
                context = browser.new_context(**self.config.to_dict())
                page = context.new_page()
                
                # Authenticate
                logger.debug("Performing authentication")
                auth_success = authenticator(page, context)
                
                if not auth_success:
                    raise Exception("Authentication failed")
                
                logger.debug("Authentication successful")
                
                # Navigate to target URL
                logger.debug(f"Navigating to {url}")
                page.goto(url, wait_until='networkidle', timeout=self.config.timeout)
                
                # Execute scraper
                logger.debug("Executing scraper function")
                result = scraper(page)
                
                logger.info("Authenticated scraping completed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Error during authenticated scraping: {e}")
                raise
                
            finally:
                # Clean up resources
                if page:
                    try:
                        page.close()
                    except Exception as e:
                        logger.warning(f"Error closing page: {e}")
                
                if context:
                    try:
                        context.close()
                    except Exception as e:
                        logger.warning(f"Error closing context: {e}")
                
                if browser:
                    try:
                        browser.close()
                    except Exception as e:
                        logger.warning(f"Error closing browser: {e}")
