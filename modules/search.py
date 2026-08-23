from ddgs import DDGS
"""
DuckDuckGo Search Module (ASYNC VERSION)
Search for business websites and filter aggregators
"""
import asyncio
import config
from modules.utils import logger, is_aggregator, normalize_url
from modules.rate_limiter import rate_limiter


# ============================================================
# SEARCH FOR WEBSITE (ASYNC)
# ============================================================

async def search_for_website(business_name, city=""):
    """
    Search for business website using DuckDuckGo (ASYNC)

    Args:
        business_name: Name of the business
        city: City/location (optional)

    Returns:
        URL string or None if not found
    """
    if not business_name:
        logger.warning("Empty business name provided to search")
        return None

    # Rate limit
    await rate_limiter.acquire('google')

    # Try primary search query
    url = await _search_with_query(business_name, city, include_contact=True)

    if url:
        return url

    # Fallback: try without contact keywords
    logger.info(
        f"Primary search failed for '{business_name}', trying fallback query")

    # Small delay between attempts
    await asyncio.sleep(config.SEARCH_DELAY)

    url = await _search_with_query(business_name, city, include_contact=False)

    return url


async def _search_with_query(business_name, city="", include_contact=True):
    """
    Perform search with constructed query (ASYNC)

    Args:
        business_name: Name of the business
        city: City/location
        include_contact: Include contact keywords in query

    Returns:
        URL string or None
    """
    # Construct search query
    query_parts = [f'"{business_name}"']

    if city:
        query_parts.append(f'"{city}"')

    if include_contact:
        query_parts.append('contact OR phone OR email')

    query = ' '.join(query_parts)

    logger.info(f"Searching: {query}")

    try:
        # DDGS is sync, so run in executor
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: list(DDGS().text(query, max_results=config.MAX_SEARCH_RESULTS))
        )

        if not results:
            logger.warning(f"No search results for: {query}")
            return None

        # Filter and validate results
        for result in results:
            url = result.get('href') or result.get('link')

            if not url:
                continue

            # Normalize URL
            url = normalize_url(url)

            # Skip aggregators
            if is_aggregator(url):
                logger.debug(f"Skipping aggregator: {url}")
                continue

            # Found valid URL!
            logger.info(f"Found website: {url}")
            return url

        logger.warning(
            f"All results were aggregators or invalid for: {business_name}")
        return None

    except Exception as e:
        logger.error(f"Search error for '{business_name}': {e}")
        return None


def validate_search_setup():
    """
    Validate search setup (can stay sync)

    Returns:
        bool: True if setup is valid
    """
    try:
        # Test ddg search
        logger.info("DuckDuckGo search module validated")
        return True
    except ImportError:
        logger.error("DuckDuckGo search module not installed!")
        logger.error("Install with: pip install duckduckgo-search")
        return False
    except Exception as e:
        logger.error(f"Search validation failed: {e}")
        return False


def search_duckduckgo(query, max_results=10):
    """
    Helper function for backward compatibility
    Performs synchronous DuckDuckGo search

    Args:
        query: Search query string
        max_results: Maximum number of results

    Returns:
        List of search result dictionaries
    """
    try:
        results = list(DDGS().text(query, max_results=max_results))
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []
