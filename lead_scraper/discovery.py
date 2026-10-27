"""
Dynamic Business Discovery Engine for LeadScraper.
Extracts official business websites and entity candidates dynamically for any
category and location in the world without hardcoded assumptions.
"""

import re
import urllib.parse
from typing import Dict, List, Optional
from lead_scraper.search import search_duckduckgo, is_aggregator, extract_domain


def generate_discovery_queries(category: str, location: str) -> List[str]:
    """Generates 3 diverse, high-yield discovery queries."""
    cat = category.strip()
    loc = location.strip()
    return [
        f"best {cat} in {loc}",
        f"{loc} {cat} guide directory",
        f"top {cat} {loc}",
    ]


def clean_title_to_name(title: str, category: str, location: str) -> Optional[str]:
    """Cleans a search result title down to the raw business name."""
    if not title:
        return None
    
    # Strip site markers and slogans
    parts = re.split(r"[-|:•—–]", title)
    for part in parts:
        clean = part.strip()
        clean_lower = clean.lower()
        # Skip noise words, directories, and listicle headings
        if any(term in clean_lower for term in [
            "yelp", "tripadvisor", "the 10", "the 15", "top 10", "best 10",
            "guide to", "directory", "near me", "reviews", "ratings", "official website"
        ]):
            continue
        if re.match(r"^(\d+|\bthe\b|\bbest\b|\btop\b)\s+", clean, re.IGNORECASE):
            continue
        if 3 <= len(clean) <= 50 and not clean.startswith(("http", "www.")):
            if clean_lower not in [location.lower(), f"in {location.lower()}", category.lower()]:
                return clean
    return None


def extract_candidates_from_results(
    results: List[Dict[str, str]],
    location: str,
    category: str
) -> List[Dict[str, Any]]:
    """Extracts candidate businesses and direct websites from search results."""
    candidates: List[Dict[str, Any]] = []
    seen_domains = set()
    seen_names = set()

    for r in results:
        url = r.get("href") or r.get("url") or ""
        title = r.get("title", "")
        snippet = r.get("body", "")

        # 1. Direct Official Site Extraction
        if url and not is_aggregator(url):
            domain = extract_domain(url)
            if domain and domain not in seen_domains:
                parsed = urllib.parse.urlparse(url)
                root_url = f"{parsed.scheme or 'https'}://{parsed.netloc}"
                name = clean_title_to_name(title, category, location)
                if not name:
                    name = domain.split(".")[0].replace("-", " ").title()
                
                name_key = name.lower()
                if name_key not in seen_names:
                    seen_domains.add(domain)
                    seen_names.add(name_key)
                    candidates.append({
                        "name": name,
                        "website": root_url,
                        "location": location,
                        "category": category,
                    })
                    continue

        # 2. Numbered entity lists in review / aggregator snippets
        # e.g., "1. Tartine Bakery ... 2. Craftsman and Wolves"
        combined_text = f"{title}\n{snippet}"
        numbered_matches = re.findall(
            r"(?:^|\n|\s)\d+[\.\)]\s+([A-Z][A-Za-z0-9'& -]{2,35}?)(?=\s+(?:is|has|was|offers|features|located|\bin\b|,|\.|\n|$))",
            combined_text
        )
        for match in numbered_matches:
            clean = match.strip().rstrip(" ,.-")
            clean_low = clean.lower()
            if len(clean) >= 3 and clean_low not in seen_names:
                if not any(w in clean_low for w in ["best", "top", "guide", "review", "directory", "near me"]):
                    seen_names.add(clean_low)
                    candidates.append({
                        "name": clean,
                        "website": None,  # Will be discovered via 1 targeted search
                        "location": location,
                        "category": category,
                    })

    return candidates


def discover_business_candidates(
    category: str,
    location: str,
    quantity: int = 10
) -> List[Dict[str, Any]]:
    """
    Discovers candidate businesses for a given category and location.
    Stops query execution as soon as enough candidates are discovered.
    """
    candidates: List[Dict[str, Any]] = []
    queries = generate_discovery_queries(category, location)
    
    for query in queries:
        results = search_duckduckgo(query, max_results=15)
        batch = extract_candidates_from_results(results, location, category)
        for item in batch:
            if item not in candidates:
                candidates.append(item)
            if len(candidates) >= quantity:
                break
        if len(candidates) >= quantity:
            break

    return candidates[:quantity]
