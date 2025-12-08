"""Rate limiting component to control request frequency."""

import time
import random
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class RateLimiter:
    """Controls request frequency to avoid blocking by external services.
    
    This class implements a simple rate limiter with configurable delay
    and random jitter to make request patterns less predictable.
    
    Attributes:
        rate: Base delay in seconds between requests
        jitter: Tuple of (min_multiplier, max_multiplier) for randomization
    """
    
    def __init__(self, rate: float, jitter: Tuple[float, float] = (0.5, 1.5)):
        """Initialize RateLimiter with rate and jitter configuration.
        
        Args:
            rate: Base delay in seconds between requests (e.g., 2.0 for 2 seconds)
            jitter: Tuple of (min, max) multipliers for random jitter.
                   Default (0.5, 1.5) means delay will be between 50% and 150% of rate.
                   
        Raises:
            ValueError: If rate is negative or jitter values are invalid
        """
        if rate < 0:
            raise ValueError(f"Rate must be non-negative, got {rate}")
        
        if jitter[0] < 0 or jitter[1] < jitter[0]:
            raise ValueError(f"Invalid jitter range: {jitter}")
        
        self.rate = rate
        self.jitter = jitter
        logger.debug(f"RateLimiter initialized with rate={rate}s, jitter={jitter}")
    
    def wait(self) -> None:
        """Wait appropriate time before next request.
        
        Calculates delay as: base_rate + random_jitter
        where random_jitter is uniformly distributed between
        (rate * jitter[0]) and (rate * jitter[1])
        """
        if self.rate == 0:
            # No delay needed
            return
        
        # Calculate jittered delay
        jitter_min = self.rate * self.jitter[0]
        jitter_max = self.rate * self.jitter[1]
        delay = random.uniform(jitter_min, jitter_max)
        
        logger.debug(f"Rate limiting: waiting {delay:.2f}s (base={self.rate}s)")
        time.sleep(delay)
    
    def get_delay(self) -> float:
        """Calculate the delay that would be used without actually waiting.
        
        Useful for testing or logging purposes.
        
        Returns:
            The calculated delay in seconds
        """
        if self.rate == 0:
            return 0.0
        
        jitter_min = self.rate * self.jitter[0]
        jitter_max = self.rate * self.jitter[1]
        return random.uniform(jitter_min, jitter_max)
