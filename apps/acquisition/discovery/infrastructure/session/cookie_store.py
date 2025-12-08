"""Cookie persistence for session management."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class CookieStore:
    """Handles cookie persistence to disk.
    
    This class provides a simple interface for saving and loading cookies
    to/from JSON files. It handles file I/O errors gracefully and ensures
    the session directory exists.
    
    Attributes:
        session_file: Path to the JSON file where cookies are stored
    """
    
    def __init__(self, session_file: Path):
        """Initialize CookieStore with a session file path.
        
        Args:
            session_file: Path to the JSON file for cookie storage
        """
        self.session_file = Path(session_file)
    
    def save(self, cookies: List[Dict[str, Any]]) -> None:
        """Save cookies to file.
        
        Creates the parent directory if it doesn't exist and writes
        cookies as JSON to the session file.
        
        Args:
            cookies: List of cookie dictionaries to save
            
        Raises:
            IOError: If file cannot be written (logged but not raised)
        """
        try:
            # Ensure parent directory exists
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write cookies as JSON
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            
            logger.info(f"Saved {len(cookies)} cookies to {self.session_file}")
            
        except (IOError, OSError) as e:
            logger.error(f"Failed to save cookies to {self.session_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving cookies: {e}")
            raise
    
    def load(self) -> List[Dict[str, Any]]:
        """Load cookies from file.
        
        Returns:
            List of cookie dictionaries, or empty list if file doesn't exist
            or is corrupted
            
        Raises:
            IOError: If file exists but cannot be read (logged but not raised)
        """
        if not self.session_file.exists():
            logger.debug(f"Session file {self.session_file} does not exist")
            return []
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            if not isinstance(cookies, list):
                logger.warning(f"Invalid cookie format in {self.session_file}, expected list")
                return []
            
            logger.info(f"Loaded {len(cookies)} cookies from {self.session_file}")
            return cookies
            
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted JSON in {self.session_file}: {e}")
            return []
        except (IOError, OSError) as e:
            logger.error(f"Failed to read cookies from {self.session_file}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading cookies: {e}")
            return []
    
    def clear(self) -> None:
        """Clear saved cookies by deleting the session file.
        
        Does nothing if the file doesn't exist.
        
        Raises:
            IOError: If file exists but cannot be deleted (logged but not raised)
        """
        if not self.session_file.exists():
            logger.debug(f"Session file {self.session_file} does not exist, nothing to clear")
            return
        
        try:
            self.session_file.unlink()
            logger.info(f"Cleared cookies from {self.session_file}")
            
        except (IOError, OSError) as e:
            logger.error(f"Failed to delete session file {self.session_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error clearing cookies: {e}")
            raise
