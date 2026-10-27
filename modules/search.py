"""
DuckDuckGo Search Module (ASYNC VERSION)
Search for business websites and filter aggregators
"""
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None
import time
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
    logger.info(f"Primary search failed for '{business_name}', trying fallback query")
    
    # Small delay between attempts
    await asyncio.sleep(config.SEARCH_DELAY)
    
    url = await _search_with_query(business_name, city, include_contact=False)
    
    return url


def is_result_relevant(url: str, title: str, business_name: str) -> bool:
    """Verifies that the search result title or domain has lexical relevance to the business."""
    if not business_name or not url:
        return False
    import re
    from urllib.parse import urlparse
    biz_lower = business_name.lower().strip()
    title_lower = title.lower() if title else ""
    domain = urlparse(url).netloc.replace('www.', '').lower()
    
    # 1. Does the title mention key words of the business?
    stopwords = {'the', 'and', 'inc', 'llc', 'ltd', 'company', 'services', 'co'}
    biz_words = [w for w in re.split(r'[^a-z0-9]', biz_lower) if len(w) >= 3 and w not in stopwords]
    
    if not biz_words:
        return True
        
    if any(w in title_lower for w in biz_words):
        return True
        
    # 2. Does the domain contain any key business words?
    domain_clean = re.sub(r'[^a-z0-9]', '', domain)
    if any(w in domain_clean for w in biz_words):
        return True
        
    return False


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
            title = result.get('title', '')
            
            if not url:
                continue
            
            # Normalize URL
            url = normalize_url(url)
            
            # Skip aggregators
            if is_aggregator(url):
                logger.debug(f"Skipping aggregator: {url}")
                continue
                
            # Verify lexical relevance to target business
            if not is_result_relevant(url, title, business_name):
                logger.debug(f"Skipping irrelevant search match: {url} (Title: {title})")
                continue
            
            # Found valid, verified URL!
            logger.info(f"Found website: {url}")
            return url
        
        logger.warning(f"All results were aggregators or invalid for: {business_name}")
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
        if DDGS is None:
            raise ImportError("Neither duckduckgo-search nor ddgs is installed")
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
    if DDGS is None:
        logger.error("DDGS module is not available")
        return []
    for attempt in range(2):
        try:
            results = list(DDGS().text(query, max_results=max_results))
            if results:
                return results
        except Exception as e:
            if attempt == 0:
                time.sleep(1.2)
                continue
            logger.debug(f"Search error for '{query}': {e}")
    return []
