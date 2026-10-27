"""
Zero-Stall Search Engine for LeadScraper.
Performs fast official website lookups with multi-backend resilience (Yahoo / DuckDuckGo / Startpage).
"""

import re
import urllib.parse
from typing import Dict, List, Optional
from ddgs import DDGS
from lead_scraper.config import AGGREGATOR_DOMAINS, IGNORED_SUBDOMAINS


def extract_domain(url: str) -> str:
    """Extracts normalized clean root domain from a URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        for sub in IGNORED_SUBDOMAINS:
            if netloc.startswith(sub):
                netloc = netloc[len(sub):]
        return netloc
    except Exception:
        return ""


def is_aggregator(url: str) -> bool:
    """Returns True if the URL belongs to a directory, social, or review aggregator."""
    domain = extract_domain(url)
    if not domain:
        return True
    if any(domain == agg or domain.endswith("." + agg) for agg in AGGREGATOR_DOMAINS):
        return True
    # Heuristics for generic aggregator/directory domain names
    if any(term in domain for term in ["directory", "nearme", "roasterfinder", "restaurantfinder"]):
        return True
    return False


def search_duckduckgo(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Executes a high-speed search query using DDGS with primary Yahoo backend (<1.2s)
    and automatic failover to DuckDuckGo/Startpage backends.
    """
    results: List[Dict[str, str]] = []
    
    # Try backends in order of datacenter stability
    for backend in ["yahoo", "startpage", "duckduckgo"]:
        try:
            with DDGS() as ddgs:
                ddgs_res = list(ddgs.text(query, max_results=max_results, backend=backend))
                if ddgs_res:
                    for r in ddgs_res:
                        results.append({
                            "title": r.get("title", ""),
                            "href": r.get("href", "") or r.get("url", ""),
                            "url": r.get("href", "") or r.get("url", ""),
                            "body": r.get("body", "") or r.get("description", ""),
                        })
                    return results
        except Exception:
            continue

    return results


def search_for_official_website(business_name: str, location: Optional[str] = None) -> Optional[str]:
    """
    Finds the official website for a business name using exactly 1 targeted search.
    Filters out aggregators (Yelp, TripAdvisor, Facebook, etc.).
    """
    clean_name = business_name.strip()
    query = f"{clean_name} {location or ''}".strip()
    
    results = search_duckduckgo(query, max_results=5)
    for r in results:
        url = r.get("href") or r.get("url")
        if url and not is_aggregator(url):
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
    return None
