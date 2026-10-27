"""
Universal Business Discovery Engine
Dynamic, category-agnostic entity discovery across any industry and location.
100% Zero-Cost & Deterministic (Zero external LLM API dependencies required).
"""

import re
from typing import List, Dict, Any
from modules.utils import logger
from modules.search import search_duckduckgo
import config

# Stopwords & media brands to filter out of business candidate names
DISCOVERY_STOPWORDS = {
    'best', 'top', 'guide', 'review', 'reviews', 'directory', 'list', 'listing',
    'ultimate', 'near me', 'ratings', 'ranked', 'ranking', 'how to', 'find a',
    'the 10', 'the 15', 'the 20', 'top 10', 'top 15', 'top 20', 'best 10', 'best 15',
    'tripadvisor', 'yelp', 'foursquare', 'wikipedia', 'eater', 'timeout', 'time out', 'infatuation',
    'thrillist', 'reddit', 'facebook', 'instagram', 'forbes', 'medium', 'linkedin',
    'local businesses', 'yellow pages', 'angies list', 'bbb', 'places to', 'things to do',
    'contact us', 'contact us today', 'about us', 'same day', 'emergency plumbing',
    'neighborhoods', 'local roasters', 'healthgrades', 'angi', 'angies', 'chamber of commerce'
}


def discover_businesses(location: str, quantity: int = 50, category: str = "business") -> List[Dict[str, Any]]:
    """
    Dynamically discovers businesses in any target location and category.
    
    Args:
        location: City/region/area name (e.g., 'Austin, TX', 'London', 'Tokyo')
        quantity: Target number of businesses to discover
        category: Any business category or industry (e.g. 'plumber', 'dentist', 'coffee', 'saas', 'lawyer')
        
    Returns:
        List of candidate dictionaries: [{'name': '...', 'website': '...', 'location': '...', 'city': '...', 'category': '...'}]
    """
    clean_category = (category or "business").strip()
    clean_location = (location or "").strip()
    logger.info(f"DISCOVERY ENGINE: Finding {quantity} '{clean_category}' entities in '{clean_location}'")
    
    # Generate search queries dynamically tailored to category & location
    queries = _generate_discovery_queries(clean_location, clean_category)
    logger.info(f"DISCOVERY PLAN: Running up to {len(queries)} search queries for {clean_category}")
    
    candidates: List[Dict[str, Any]] = []
    seen = set()
    
    # Optional: OpenRouter free router candidate suggestions if configured
    try:
        from modules.ai_manager import ai_manager
        if ai_manager.is_available() and getattr(config, 'ENABLE_AI_FALLBACK', True):
            logger.info("OpenRouter AI enabled: Querying free auto-router for candidate businesses...")
            ai_suggestions = ai_manager.discover_businesses_with_ai_sync(
                clean_location, clean_category, quantity=min(quantity, 25)
            )
            for item in ai_suggestions:
                name = item.get('business_name')
                if name:
                    k = name.lower().strip()
                    if k not in seen:
                        seen.add(k)
                        candidates.append({
                            'name': name.strip(),
                            'website': item.get('website'),
                            'location': clean_location,
                            'city': clean_location,
                            'category': clean_category
                        })
            if ai_suggestions:
                logger.info(f"OpenRouter free models contributed {len(ai_suggestions)} candidates")
    except Exception as e:
        logger.debug(f"Optional AI discovery error: {e}")
    
    # Execute deterministic search queries
    for i, query in enumerate(queries, 1):
        if len(candidates) >= quantity:
            logger.info(f"DISCOVERY: Candidate pool target reached ({len(candidates)}), stopping searches early")
            break
            
        logger.info(f"Search Query {i}/{len(queries)}: {query}")
        try:
            results = search_duckduckgo(query, max_results=12)
            extracted = _extract_business_entities(results, clean_location, clean_category)
            
            for item in extracted:
                k = item['name'].lower().strip()
                if k not in seen:
                    seen.add(k)
                    candidates.append(item)
            logger.info(f"  Extracted {len(extracted)} entities (total candidates: {len(candidates)})")
        except Exception as e:
            logger.warning(f"  Search query failed ({query}): {e}")
            continue

    final = candidates[:quantity]
    logger.info(f"DISCOVERY COMPLETE: Returning {len(final)} verified '{clean_category}' businesses in {clean_location}")
    return final


def _generate_discovery_queries(location: str, category: str) -> List[str]:
    """Generates dynamic search queries adapted to any category and location."""
    cat_plural = category if category.endswith('s') else f"{category}s"
    return [
        f'{category} in {location}',
        f'{category} {location} contact phone',
        f'best {cat_plural} in {location}'
    ]


def _extract_business_entities(results: List[Dict[str, Any]], location: str, category: str) -> List[Dict[str, Any]]:
    """Extracts genuine business names and official websites from search snippets and titles."""
    if not results:
        return []

    import urllib.parse
    from modules.utils import is_aggregator, normalize_url
    candidates = []
    seen = set()
    
    for r in results:
        url = r.get('href') or r.get('link') or ''
        title = r.get('title', '')
        snippet = r.get('body') or r.get('description') or ''
        
        # 1. Non-aggregator official sites: Extract business name & website URL directly
        if not is_aggregator(url):
            root_url = None
            if url:
                url_norm = normalize_url(url)
                parsed = urllib.parse.urlparse(url_norm)
                root_url = f"{parsed.scheme}://{parsed.netloc}"
            title_parts = re.split(r'\s+[-–—]\s+|\s*[|:•]\s*', title)
            for part in title_parts:
                cleaned = _clean_candidate_name(part, location, category)
                if cleaned and _is_valid_business_name(cleaned, location, category):
                    k = cleaned.lower()
                    if k not in seen:
                        seen.add(k)
                        candidates.append({
                            'name': cleaned,
                            'website': root_url,
                            'location': location,
                            'city': location,
                            'category': category
                        })
                    break

        # 2. Comma-separated lists in snippets (e.g. Yelp, local guides, Eater)
        list_matches = re.finditer(
            r'(?:[-–—]|\blike\b|\bsuch as\b)\s*(?:(?:last\s+updated|updated|as\s+of)?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}\s*[-–—:]\s*)?([A-Z][\w\s\'&’.-]+(?:,\s*(?:and\s+)?[A-Z][\w\s\'&’.-]+)+)',
            snippet,
            re.IGNORECASE
        )
        for m in list_matches:
            raw_list = m.group(1)
            items = re.split(r',\s*(?:and\s+)?|\s+and\s+', raw_list)
            for item in items:
                cleaned_item = re.sub(
                    r'^(?:last\s+updated|updated|as\s+of)?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}\s*[-–—:]\s*',
                    '',
                    item,
                    flags=re.IGNORECASE
                ).strip()
                cleaned_item = re.sub(r'\s*(&\s*more|sorted\s+by.*|etc\b.*|\bmore\b.*)$', '', cleaned_item, flags=re.IGNORECASE).strip()
                cleaned = _clean_candidate_name(cleaned_item, location, category)
                if cleaned and _is_valid_business_name(cleaned, location, category):
                    k = cleaned.lower()
                    if k not in seen:
                        seen.add(k)
                        candidates.append({
                            'name': cleaned,
                            'website': None,
                            'location': location,
                            'city': location,
                            'category': category
                        })

        # 3. Numbered list items inside snippets (e.g. "1. Acme Plumbing", "2. Precision Dental")
        numbered_matches = re.findall(r'(?:^|\n)\s*\d+[\.)]\s+([A-Z][A-Za-z0-9 \t\'&’.-]{2,40})', snippet)
        for match in numbered_matches:
            cleaned = _clean_candidate_name(match, location, category)
            if cleaned and _is_valid_business_name(cleaned, location, category):
                k = cleaned.lower()
                if k not in seen:
                    seen.add(k)
                    candidates.append({
                        'name': cleaned,
                        'website': None,
                        'location': location,
                        'city': location,
                        'category': category
                    })

    return candidates


def _clean_candidate_name(raw: str, location: str, category: str) -> str:
    """Cleans punctuation, website suffixes, and boilerplate from business candidates."""
    name = raw.strip()
    # Remove leading numbering or bullet points
    name = re.sub(r'^\d+[\.)\s]+', '', name).strip()
    # Remove action verbs and prefixes
    name = re.sub(
        r'^(contact\s+us\s+today|contact\s+us|contact|about\s+us|about|visit\s+a|visit|welcome\s+to|call\s+us|call)\s*[\-|:•—–]?\s*',
        '',
        name,
        flags=re.IGNORECASE
    ).strip()
    # Remove trailing common website suffixes or location
    loc_pattern = re.escape(location) if location else r'$^'
    name = re.sub(
        r'\s*[\-|:•—–]?\s*(official site|official website|home|homepage|website|in\s+' + loc_pattern + r').*$',
        '',
        name,
        flags=re.IGNORECASE
    ).strip()
    # Strip any dangling separators at end or start
    name = re.sub(r'^[\s\-|:•—–]+|[\s\-|:•—–]+$', '', name).strip()
    # Strip quotes, whitespace and trailing dots
    name = name.strip('"\'. \t')
    return name


def _is_valid_business_name(name: str, location: str, category: str) -> bool:
    """Verifies that a string is a probable business entity rather than a publication or article title."""
    if not name or len(name) < 3 or len(name) > 50:
        return False
        
    name_lower = name.lower()
    
    # Reject if matches URL pattern
    if name_lower.startswith(('http://', 'https://', 'www.')) or name_lower.endswith(('.com', '.org', '.net', '.io', '.co')):
        return False

    # Location matching check: reject if name is just location (e.g. "Chicago, IL" or "Austin")
    loc_lower = location.lower()
    loc_parts = [p.strip().lower() for p in re.split(r'[,/]', location) if p.strip()]
    if name_lower in loc_parts or name_lower == loc_lower:
        return False
    if loc_parts and all(part in name_lower for part in loc_parts) and len(name_lower) <= len(loc_lower) + 5:
        return False

    # Reject if exactly matches category
    cat_lower = category.lower()
    if name_lower in [cat_lower, f"{loc_lower} {cat_lower}", f"{cat_lower} in {loc_lower}"]:
        return False

    # Reject generic SEO title combinations of category and location (e.g. "Plumber Chicago, IL")
    for loc_token in loc_parts:
        if loc_token and loc_token in name_lower and cat_lower in name_lower and len(name_lower) <= len(loc_token) + len(cat_lower) + 12:
            return False
        
    # Reject if contains known stopwords or aggregator brands
    for stop in DISCOVERY_STOPWORDS:
        if stop in name_lower:
            return False

    # Reject sentence fragments with periods (unless standard business abbreviations)
    if '.' in name and not re.search(r'\b(?:inc|co|ltd|corp|dr|st)\.', name_lower):
        return False

    # Reject leading prepositions and conversational sentence starters
    if re.match(r'^(?:from|to|for|in|at|with|by|and|or|more|such as|like|perfect for|good for|ideal for)\b', name_lower):
        return False

    # Reject common descriptive buzzwords from guide text
    buzzwords = ['local favorite', 'trendy', 'remote worker', 'coffee lover', 'great spot', 'hidden gem', 'neighborhoods']
    if any(bw in name_lower for bw in buzzwords):
        return False

    # Reject common listicle title prefixes
    if re.match(r'^(the\s+\d+|\d+\s+best|\d+\s+top|here\s+are|why\s+you|where\s+to)', name_lower):
        return False

    return True


def _validate_and_format_entities(names: List[str], location: str, category: str) -> List[Dict[str, Any]]:
    """Deduplicates and formats verified business entities into standard dictionaries."""
    seen = set()
    validated = []
    
    for name in names:
        key = name.lower().strip()
        if key not in seen and len(key) >= 3:
            seen.add(key)
            validated.append({
                'name': name.strip(),
                'location': location,
                'category': category
            })
            
    return validated
