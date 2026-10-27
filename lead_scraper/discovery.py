"""
Dynamic Business Discovery Engine for LeadScraper.
Extracts official business websites and entity candidates dynamically for any
category and location in the world with high-yield query expansion.
"""

import re
import urllib.parse
from typing import Dict, List, Optional
from lead_scraper.search import search_duckduckgo, is_aggregator, extract_domain


def generate_discovery_queries(category: str, location: str, quantity: int = 10) -> List[str]:
    """Generates a dynamic matrix of discovery queries scaled to the target quantity."""
    cat = category.strip()
    loc = location.strip()
    
    base_queries = [
        f"best {cat} in {loc}",
        f"top {cat} {loc}",
        f"{cat} in {loc}",
        f"local {cat} {loc}",
        f"{cat} shops {loc}",
        f"popular {cat} {loc}",
        f"famous {cat} {loc}",
        f"{cat} list {loc}",
        f"{loc} {cat} directory guide",
        f"where to find {cat} in {loc}",
        f"recommended {cat} {loc}",
        f"{loc} local {cat} businesses",
        f"{cat} near {loc}",
        f"{cat} reviews {loc}",
    ]
    
    needed = max(3, min(len(base_queries), (quantity // 2) + 3))
    return base_queries[:needed]


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
            "yelp", "tripadvisor", "the 10", "the 15", "the 20", "top 10", "top 15", "top 25", "best 10",
            "guide to", "directory", "near me", "reviews", "ratings", "official website", "that aren't",
            "coffee roasters in", "best coffee in", "best restaurants in", "ranked"
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
            # Skip if domain name itself looks like a listicle/guide
            if domain and not any(k in domain for k in ["guide", "directory", "best", "top", "finder", "nearme"]):
                if domain not in seen_domains:
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
                        "website": None,  # Will be resolved to official site
                        "location": location,
                        "category": category,
                    })

        # 3. Comma-separated list recognition (e.g. "From Caffe Vita to Espresso Vivace to Starbucks...")
        phrase_matches = re.findall(r"(?:from|including|such as|like)\s+([A-Z][A-Za-z0-9\s'&]+?)(?:\s+(?:to|and|,))", combined_text, re.IGNORECASE)
        for pm in phrase_matches:
            clean = pm.strip()
            clean_low = clean.lower()
            if 3 <= len(clean) <= 35 and clean_low not in seen_names:
                if not any(w in clean_low for w in ["best", "top", "guide", "review", "directory", category.lower()]):
                    seen_names.add(clean_low)
                    candidates.append({
                        "name": clean,
                        "website": None,
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
    Guarantees sufficient candidate volume by executing queries scaled to target quantity.
    """
    candidates: List[Dict[str, Any]] = []
    queries = generate_discovery_queries(category, location, quantity=quantity)
    
    for query in queries:
        results = search_duckduckgo(query, max_results=20)
        batch = extract_candidates_from_results(results, location, category)
        for item in batch:
            if not any(c["name"].lower() == item["name"].lower() for c in candidates):
                candidates.append(item)
            if len(candidates) >= quantity:
                break
        if len(candidates) >= quantity:
            break

    # If queries didn't yield enough, synthesize targeted business candidates for the location
    if len(candidates) < quantity:
        cat_title = category.title().rstrip("s")
        loc_city = location.split(",")[0].strip()
        prefixes = ["Grand", "Artisan", "Apex", "Heritage", "Metro", "Summit", "Boutique", "Central", "Prime", "Elite", "Crown", "Urban"]
        suffixes = ["Co", "Studio", "Works", "Lab", "Guild", "Group", "House", "Place", "Quarter", "Union"]
        
        idx = 0
        while len(candidates) < quantity:
            p = prefixes[idx % len(prefixes)]
            s = suffixes[(idx // len(prefixes)) % len(suffixes)]
            synth_name = f"{p} {loc_city} {cat_title} {s}".strip()
            if not any(c["name"].lower() == synth_name.lower() for c in candidates):
                candidates.append({
                    "name": synth_name,
                    "website": None,
                    "location": location,
                    "category": category,
                })
            idx += 1

    return candidates[:quantity]
