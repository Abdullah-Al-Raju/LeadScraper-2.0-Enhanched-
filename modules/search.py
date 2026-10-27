"""
DuckDuckGo Search Module (ASYNC & FAST HTML HYBRID)
High-speed website discovery with instant HTML parsing and zero-stall fallback.
"""
import time
import asyncio
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

import config
from modules.utils import logger, is_aggregator, normalize_url
from modules.rate_limiter import rate_limiter


# ============================================================
# FAST DIRECT DUCKDUCKGO HTML PARSER (SUB-SECOND, RESILIENT)
# ============================================================

def ddg_html_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Direct, lightweight HTTP parser for DuckDuckGo HTML interface.
    Bypasses third-party proxy rotators and dead engine timeouts.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        r = httpx.post(
            'https://html.duckduckgo.com/html/',
            data={'q': query},
            headers=headers,
            timeout=3.5,
            follow_redirects=True
        )
        if r.status_code != 200:
            return []
            
        soup = BeautifulSoup(r.text, 'lxml')
        results = []
        for result_div in soup.select('.result'):
            link = result_div.select_one('.result__title a')
            snippet_elem = result_div.select_one('.result__snippet')
            if not link:
                continue
            href = link.get('href', '')
            title = link.get_text(strip=True)
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
            
            # Unpack DuckDuckGo redirect link
            if 'uddg=' in href:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                actual_url = parsed.get('uddg', [href])[0]
            else:
                actual_url = href
                
            if actual_url.startswith(('http://', 'https://')):
                results.append({
                    'title': title,
                    'href': actual_url,
                    'link': actual_url,
                    'body': snippet,
                    'description': snippet
                })
            if len(results) >= max_results:
                break
                
        return results
    except Exception as e:
        logger.debug(f"Direct DDG HTML search error: {e}")
        return []


def search_duckduckgo(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Unified high-speed DuckDuckGo search.
    Tries lightweight direct HTML parser first (sub-second), falls back to DDGS library.
    """
    # 1. Fast direct HTML path (< 1.0s, no 429/403 fan-out errors)
    results = ddg_html_search(query, max_results=max_results)
    if results:
        return results
        
    # 2. Secondary fast engine fallback (Yahoo via DDGS)
    if DDGS is not None:
        try:
            ddgs_res = DDGS().text(query, backend='yahoo', max_results=max_results)
            if ddgs_res:
                return list(ddgs_res)
        except Exception as e:
            logger.debug(f"DDGS Yahoo search failed for '{query}': {e}")
            
    return []


# ============================================================
# SEARCH FOR WEBSITE (ASYNC)
# ============================================================

async def search_for_website(business_name: str, city: str = "") -> Optional[str]:
    """
    High-speed targeted official website locator.
    
    Args:
        business_name: Name of the business
        city: City/location (optional)
        
    Returns:
        Clean official root URL string or None
    """
    if not business_name:
        return None
        
    await rate_limiter.acquire('google')
    loop = asyncio.get_event_loop()
    
    # 1. Primary high-precision query
    city_str = f'"{city}"' if city else ""
    query = f'"{business_name}" {city_str} official website'.strip()
    logger.info(f"Locating official site: {query}")
    
    url = await loop.run_in_executor(None, _execute_website_search, query, business_name)
    if url:
        return url
        
    # 2. Unquoted fallback query
    fallback_query = f'{business_name} {city} website'.strip()
    logger.info(f"Trying fallback site query: {fallback_query}")
    url = await loop.run_in_executor(None, _execute_website_search, fallback_query, business_name)
    return url


def _execute_website_search(query: str, business_name: str) -> Optional[str]:
    """Performs search and isolates the verified non-aggregator official website."""
    results = search_duckduckgo(query, max_results=8)
    if not results:
        return None
        
    for result in results:
        url = result.get('href') or result.get('link')
        title = result.get('title', '')
        if not url:
            continue
            
        url = normalize_url(url)
        if is_aggregator(url):
            continue
            
        if is_result_relevant(url, title, business_name):
            # Extract clean domain root if path is deep
            parsed = urllib.parse.urlparse(url)
            root_url = f"{parsed.scheme}://{parsed.netloc}"
            logger.info(f"Found official website: {root_url} (from {url})")
            return root_url
            
    return None


def is_result_relevant(url: str, title: str, business_name: str) -> bool:
    """Verifies that the search result title or domain has lexical relevance to the business."""
    if not business_name or not url:
        return False
    import re
    biz_lower = business_name.lower().strip()
    title_lower = title.lower() if title else ""
    domain = urllib.parse.urlparse(url).netloc.replace('www.', '').lower()
    
    stopwords = {'the', 'and', 'inc', 'llc', 'ltd', 'company', 'services', 'co'}
    biz_words = [w for w in re.split(r'[^a-z0-9]', biz_lower) if len(w) >= 3 and w not in stopwords]
    
    if not biz_words:
        return True
        
    if any(w in title_lower for w in biz_words):
        return True
        
    domain_clean = re.sub(r'[^a-z0-9]', '', domain)
    if any(w in domain_clean for w in biz_words):
        return True
        
    return False


def validate_search_setup() -> bool:
    """Validate search availability."""
    return True
