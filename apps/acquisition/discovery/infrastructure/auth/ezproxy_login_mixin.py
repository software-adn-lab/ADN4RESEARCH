"""Base mixin for EZproxy authentication logic.

This module provides a reusable mixin that encapsulates the common
EZproxy login flow, eliminating code duplication between different
academic source connectors (IEEE, Scopus, etc.).
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import List
from playwright.sync_api import Page, BrowserContext

logger = logging.getLogger(__name__)


class EzproxyLoginMixin(ABC):
    """Base mixin for EZproxy authentication.
    
    This mixin implements the common EZproxy login flow using the
    template method pattern. Subclasses only need to provide:
    - login_url: The EZproxy login URL for their service
    - success_indicators: URL patterns or page titles that indicate success
    
    The login flow is:
    1. Navigate to login URL
    2. Check if already authenticated (redirect to target service)
    3. Find and fill login form
    4. Submit form
    5. Verify successful authentication
    
    Attributes:
        username: Institutional username
        password: Institutional password
        timeout: Timeout in milliseconds for Playwright operations
    """
    
    # These should be set by subclasses or passed to constructor
    username: str
    password: str
    timeout: int
    
    @abstractmethod
    def get_login_url(self) -> str:
        """Return the EZproxy login URL for this provider.
        
        Example: "https://bvirtual.epn.edu.ec/login?url=http://ieeexplore.ieee.org"
        
        Returns:
            The full EZproxy login URL
        """
        pass
    
    @abstractmethod
    def get_success_indicators(self) -> List[str]:
        """Return URL patterns or page titles that indicate successful login.
        
        These are checked against the current URL and page title after
        attempting login to verify success.
        
        Example: ["ieeexplore.ieee.org", "IEEE"]
        
        Returns:
            List of strings to check for in URL or page title
        """
        pass
    
    def perform_ezproxy_login(self, page: Page, context: BrowserContext) -> bool:
        """Perform EZproxy login using common flow.
        
        This is the main template method that orchestrates the login process.
        Subclasses should call this method from their _perform_login implementation.
        
        Args:
            page: Playwright page object
            context: Playwright browser context
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            login_url = self.get_login_url()
            success_indicators = self.get_success_indicators()
            
            logger.info(f"Navigating to EZproxy login: {login_url}")
            page.goto(login_url, wait_until='networkidle', timeout=self.timeout)
            
            time.sleep(2)
            
            # Check if already authenticated (redirected to target service)
            if self._is_authenticated(page, success_indicators):
                logger.info("✓ Active session detected (already authenticated)")
                return True
            
            # Find and fill login form
            logger.info("Looking for login form...")
            if not self._fill_login_form(page):
                raise Exception("Login form not found")
            
            # Submit form
            logger.info("Submitting login form...")
            self._submit_form(page)
            
            # Wait for authentication to complete
            logger.info("Waiting for authentication...")
            time.sleep(5)
            
            # Verify success
            if self._is_authenticated(page, success_indicators):
                logger.info("✓ Login successful")
                return True
            else:
                current_url = page.url
                logger.error(f"Login failed. Current URL: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False
    
    def _is_authenticated(self, page: Page, success_indicators: List[str]) -> bool:
        """Check if authentication was successful.
        
        Args:
            page: Playwright page object
            success_indicators: List of strings to check for in URL or title
            
        Returns:
            True if any success indicator is found in URL or page title
        """
        current_url = page.url
        page_title = page.title()
        
        for indicator in success_indicators:
            if indicator in current_url or indicator in page_title:
                logger.debug(f"Success indicator '{indicator}' found")
                return True
        
        return False
    
    def _fill_login_form(self, page: Page) -> bool:
        """Find and fill the login form with credentials.
        
        Tries multiple common selectors for username and password fields.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if form was found and filled successfully
        """
        # Try to find username field
        username_field = None
        username_selectors = [
            'input[name="user"]',
            'input[name="username"]',
            'input[name="email"]',
            'input[type="email"]',
            'input[id="username"]'
        ]
        
        for selector in username_selectors:
            try:
                username_field = page.query_selector(selector)
                if username_field:
                    logger.info(f"✓ Username field found: {selector}")
                    break
            except:
                continue
        
        # Find password field
        password_field = page.query_selector('input[type="password"]')
        
        if not username_field or not password_field:
            logger.error("Login form fields not found")
            return False
        
        # Fill credentials
        logger.info("Filling credentials...")
        username_field.fill(self.username)
        password_field.fill(self.password)
        
        return True
    
    def _submit_form(self, page: Page) -> None:
        """Submit the login form.
        
        Tries to find and click a submit button, or presses Enter
        on the password field as fallback.
        
        Args:
            page: Playwright page object
        """
        # Try to find submit button
        submit_button = None
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Sign In")',
            'button:has-text("Login")',
            'button:has-text("Ingresar")'
        ]
        
        for selector in submit_selectors:
            try:
                submit_button = page.query_selector(selector)
                if submit_button:
                    logger.debug(f"Submit button found: {selector}")
                    break
            except:
                continue
        
        if submit_button:
            logger.info("Clicking submit button...")
            submit_button.click()
        else:
            # Fallback: press Enter on password field
            logger.info("Submit button not found, pressing Enter...")
            password_field = page.query_selector('input[type="password"]')
            if password_field:
                password_field.press('Enter')
