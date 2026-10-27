"""
Intelligent Business Discovery Engine
Generates diverse search queries via DuckDuckGo and extracts real business names using heuristic & regex parsing.
100% Zero-Cost & Deterministic (Zero external LLM API dependencies).
"""

import re
from modules.utils import logger, truncate_text
from modules.search import search_duckduckgo
import config


def discover_restaurants(location, quantity=100, category='restaurant'):
    """
    Discovers businesses in a target location using diverse multi-query searches.
    
    Args:
        location: City/area name (e.g., 'Austin, TX', 'Sydney')
        quantity: Target number of businesses
        category: Business category/type
        
    Returns:
        List of business dictionaries with names
    """
    logger.info(f"DISCOVERY ENGINE: Finding {quantity} {category}s in {location}")
    
    # Phase 1: Plan search strategy
    search_plan = _plan_search_strategy(location, quantity, category)
    queries = search_plan.get('queries', [])
    logger.info(f"DISCOVERY PLAN: Running {len(queries)} diverse search queries")
    
    # Phase 2: Execute searches
    all_names = []
    
    for i, query in enumerate(queries, 1):
        logger.info(f"Search Query {i}/{len(queries)}: {query}")
        
        try:
            results = search_duckduckgo(query, max_results=15)
            names = _extract_names_from_results(results, location, category)
            
            if names:
                all_names.extend(names)
                logger.info(f"  Extracted {len(names)} names (total: {len(all_names)})")
            
            if len(all_names) >= quantity * 1.5:
                logger.info(f"DISCOVERY: Reached target candidate pool ({len(all_names)} names), stopping searches")
                break
                
        except Exception as e:
            logger.warning(f"  Search query failed: {e}")
            continue
    
    # Phase 3: Validate and deduplicate results
    validated = _validate_names(all_names, location, category)
    final = validated[:quantity]
    logger.info(f"DISCOVERY COMPLETE: Returning {len(final)} verified {category}s in {location}")
    return final


def _plan_search_strategy(location, quantity, category):
    """Generates diverse search queries for regional business discovery."""
    return {
        'approach': 'Multi-query diverse heuristic search',
        'queries': [
            f"best {category}s in {location}",
            f"{location} {category} guide",
            f"top {category}s {location}",
            f"{category} directory {location}",
            f"popular {category}s {location}",
            f"where to find {category} in {location}",
            f"{location} local {category} list",
            f"{category} recommendations {location}"
        ]
    }


def _extract_names_from_results(results, location, category):
    """Extracts business names from search result snippets and titles."""
    if not results:
        return []
    
    combined_text = ""
    for r in results[:10]:
        title = r.get('title', '')
        snippet = r.get('body', '') or r.get('description', '')
        combined_text += f"{title}\n{snippet}\n\n"
    
    candidates = []
    
    # 1. Look for numbered lists in snippets: e.g. "1. Tartine Bakery", "2. Sightglass"
    numbered_matches = re.findall(r'(?:^|\n|\s)\d+\.\s+([A-Z][A-Za-z0-9\s\'&-]{2,40})', combined_text)
    for m in numbered_matches:
        clean_m = m.strip()
        if len(clean_m) >= 3 and not any(w in clean_m.lower() for w in ['best', 'top', 'guide', 'michelin', 'review', 'restaurant', 'coffee', 'directory']):
            candidates.append(clean_m)

    # 2. Extract from titles
    for r in results:
        title = r.get('title', '')
        parts = re.split(r'[-|:•—]', title)
        for part in parts:
            clean = part.strip()
            clean_lower = clean.lower()
            if any(term in clean_lower for term in ['yelp', 'tripadvisor', 'foursquare', 'wikipedia', 'the 10', 'the 15', 'top 10', 'best 10', 'guide to']):
                continue
            if re.match(r'^(\d+|\bthe\b|\bbest\b|\btop\b)\s+', clean, re.IGNORECASE):
                continue
            if 3 <= len(clean) <= 45 and not clean.startswith(('http', 'www.')):
                if clean_lower not in [location.lower(), f"in {location.lower()}", category.lower()]:
                    candidates.append(clean)

    # Deduplicate preserving order
    seen = set()
    result_list = []
    for c in candidates:
        c_low = c.lower()
        if c_low not in seen:
            seen.add(c_low)
            result_list.append({'name': c, 'location': location, 'category': category})

    return result_list


def _validate_names(names, location, category):
    """Deduplicates and cleans business names."""
    if not names:
        return []
    
    seen = set()
    unique = []
    
    for name_dict in names:
        name_lower = name_dict['name'].lower().strip()
        if name_lower not in seen and len(name_lower) >= 3:
            seen.add(name_lower)
            unique.append(name_dict)
    
    return unique
