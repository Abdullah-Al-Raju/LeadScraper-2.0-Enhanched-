"""
Rate Limiter for LeadScraper
Prevents API bans by limiting request rate per service
"""

import asyncio
from collections import defaultdict
import time
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with per-service limits"""
    
    def __init__(self):
        """Initialize rate limiter"""
        self.calls = defaultdict(list)
        
        # Service-specific limits: (max_calls, window_seconds)
        self.limits = {
            'facebook': (10, 60),        # 10 calls per 60 seconds
            'instagram': (10, 60),       # 10 calls per 60 seconds
            'google': (20, 60),          # 20 calls per 60 seconds
            'openrouter': (60, 60),      # 60 calls per 60 seconds
            'website': (30, 60),         # 30 website crawls per 60 seconds
            'default': (15, 60)          # Default for unknown services
        }
    
    async def acquire(self, service: str = 'default'):
        """
        Wait if rate limit would be exceeded
        
        Args:
            service: Service name (facebook, instagram, google, etc.)
        """
        max_calls, window = self.limits.get(service, self.limits['default'])
        now = time.time()
        
        # Remove old calls outside window
        self.calls[service] = [
            t for t in self.calls[service]
            if now - t < window
        ]
        
        # Check if at limit
        if len(self.calls[service]) >= max_calls:
            # Calculate wait time
            oldest_call = self.calls[service][0]
            wait_time = window - (now - oldest_call)
            
            if wait_time > 0:
                logger.warning(
                    f"Rate limit: {service} ({len(self.calls[service])}/{max_calls}), "
                    f"waiting {wait_time:.1f}s"
                )
                await asyncio.sleep(wait_time)
                
                # Refresh window after wait
                now = time.time()
                self.calls[service] = [
                    t for t in self.calls[service]
                    if now - t < window
                ]
        
        # Record this call
        self.calls[service].append(now)
    
    def get_status(self, service: str = 'default') -> dict:
        """
        Get current rate limit status
        
        Returns:
            dict with current_calls, max_calls, window
        """
        max_calls, window = self.limits.get(service, self.limits['default'])
        now = time.time()
        
        # Count recent calls
        recent_calls = [
            t for t in self.calls[service]
            if now - t < window
        ]
        
        return {
            'service': service,
            'current_calls': len(recent_calls),
            'max_calls': max_calls,
            'window_seconds': window,
            'remaining': max_calls - len(recent_calls)
        }


# Global rate limiter instance
rate_limiter = RateLimiter()
