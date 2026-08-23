"""
Async HTTP Client for LeadScraper
Replaces synchronous requests with async httpx for concurrent processing
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    """Async HTTP client with connection pooling and retry logic"""

    def __init__(self, timeout: float = 30.0, max_connections: int = 20):
        """
        Initialize async HTTP client

        Args:
            timeout: Request timeout in seconds
            max_connections: Maximum concurrent connections
        """
        self.timeout = timeout
        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=10
        )
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Context manager entry"""
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=self.limits,
            follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.client:
            await self.client.aclose()

    async def get(self, url: str, **kwargs) -> Optional[httpx.Response]:
        """
        Async GET request with error handling

        Args:
            url: URL to request
            **kwargs: Additional kwargs for httpx

        Returns:
            Response object or None on error
        """
        try:
            if not self.client:
                raise RuntimeError("Client not initialized - use async with")

            response = await self.client.get(url, **kwargs)
            response.raise_for_status()
            return response

        except httpx.TimeoutException:
            logger.warning(f"Timeout: {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP {e.response.status_code}: {url}")
            return None
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    async def post(self, url: str, **kwargs) -> Optional[httpx.Response]:
        """
        Async POST request with error handling

        Args:
            url: URL to request
            **kwargs: Additional kwargs for httpx

        Returns:
            Response object or None on error
        """
        try:
            if not self.client:
                raise RuntimeError("Client not initialized - use async with")

            response = await self.client.post(url, **kwargs)
            response.raise_for_status()
            return response

        except httpx.TimeoutException:
            logger.warning(f"Timeout: {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP {e.response.status_code}: {url}")
            return None
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            return None


# Singleton instance for reuse
_http_client: Optional[AsyncHTTPClient] = None


async def get_http_client() -> AsyncHTTPClient:
    """Get or create shared HTTP client"""
    global _http_client
    if _http_client is None:
        _http_client = AsyncHTTPClient()
    return _http_client
