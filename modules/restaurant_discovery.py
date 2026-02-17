"""
INTELLIGENT AI AGENT - Restaurant Discovery
AI plans strategy, decides searches, executes via DuckDuckGo, adapts based on results
"""

from modules.utils import logger, truncate_text
from modules.search import search_duckduckgo
from modules.ai_manager import ai_call
import config


def discover_restaurants(location, quantity=100, category='restaurant'):
    """
    AI Agent discovers restaurants intelligently
    
    AI decides:
    - What search strategy to use
    - What queries to run
    - How to adapt based on results
    - When it has enough data
    
    Args:
        location: City/area
        quantity: Target number
        category: Business type
        
    Returns:
        List of restaurant dicts with names
    """
    logger.info(f"AI AGENT STARTING: Find {quantity} {category}s in {location}")
    
    # Phase 1: AI plans the strategy
    search_plan = _ai_plan_search_strategy(location, quantity, category)
    
    logger.info(f"AI STRATEGY: {search_plan.get('approach', 'Unknown')}")
    logger.info(f"AI WILL RUN: {len(search_plan.get('queries', []))} searches")
    
    # Phase 2: AI executes the searches
    all_names = []
    queries = search_plan.get('queries', [])
    
    for i, query in enumerate(queries, 1):
        logger.info(f"AI Query {i}/{len(queries)}: {query}")
        
        try:
            # Run search via DuckDuckGo
            results = search_duckduckgo(query, max_results=15)
            
            # AI extracts names from results
            names = _ai_extract_names_from_results(results, location, category)
            
            if names:
                all_names.extend(names)
                logger.info(f"  AI extracted {len(names)} names (total: {len(all_names)})")
            
            # AI decides if we should continue
            if len(all_names) >= quantity * 1.5:
                logger.info(f"AI DECISION: Enough data ({len(all_names)} names), stopping")
                break
                
        except Exception as e:
            logger.warning(f"  Search failed: {e}")
            continue
    
    # Phase 3: AI validates and cleans results
    logger.info(f"AI VALIDATION: Cleaning {len(all_names)} names...")
    validated = _ai_validate_names(all_names, location, category)
    
    logger.info(f"AI VALIDATED: {len(validated)} quality names")
    
    # Return requested quantity
    final = validated[:quantity]
    
    logger.info(f"AI COMPLETE: Returning {len(final)} restaurants")
    
    return final


def _ai_plan_search_strategy(location, quantity, category):
    """
    AI plans the search strategy
    
    AI analyzes:
    - Location characteristics
    - Category type  
    - Quantity needed
    - Best search approach
    
    Returns:
        Dict with strategy and queries
    """
    logger.info("AI: Planning search strategy...")
    
    system_prompt = """You are an intelligent search strategist.

Your goal: Find restaurant names in a given location using DuckDuckGo searches.

Plan the BEST search strategy:
- Decide what types of queries will work
- Generate diverse, effective search queries
- Avoid repetitive or useless searches
- Think about what will give REAL restaurant names

Return JSON:
{
  "approach": "brief description of strategy",
  "reasoning": "why this approach will work",
  "queries": ["query 1", "query 2", ...],
  "expected_results": "what we expect to find"
}

IMPORTANT:
- Generate 8-12 diverse queries
- Focus on queries that return LISTS of restaurants
- Avoid generic queries that won't help
- Be intelligent and strategic"""

    user_prompt = f"""Plan a search strategy to find {quantity} {category} names in {location}.

Location: {location}
Category: {category}
Target: {quantity} names

What search queries should I run on DuckDuckGo to get the best results?"""

    try:
        # Use AIManager for model rotation
        plan = ai_call(system_prompt, user_prompt, temperature=0.7)
        
        if plan:
            logger.info(f"AI REASONING: {plan.get('reasoning', 'N/A')}")
            return plan
        else:
            raise Exception("AI call returned None")
        
    except Exception as e:
        logger.warning(f"AI planning failed: {e}, using fallback")
        
        # Fallback strategy
        return {
            'approach': 'Multi-query diverse search',
            'queries': [
                f"restaurants in {location}",
                f"best {category}s {location}",
                f"{location} dining guide",
                f"top places to eat {location}",
                f"{category} {location} directory",
                f"popular restaurants {location}",
                f"where to eat in {location}",
                f"{location} food scene"
            ]
        }


def _ai_extract_names_from_results(results, location, category):
    """
    AI extracts restaurant names from search results
    
    Uses AI to intelligently identify real restaurant names
    from search result titles/snippets
    
    Returns:
        List of name dicts
    """
    if not results:
        return []
    
    # Combine search results into text
    combined_text = ""
    for r in results[:10]:  # Top 10 results
        title = r.get('title', '')
        snippet = r.get('body', '') or r.get('description', '')
        combined_text += f"{title}\n{snippet}\n\n"
    
    combined_text = truncate_text(combined_text, 3000)
    
    system_prompt = f"""You are an expert at identifying {category} names.

Given search results, extract ONLY real {category} business names.

CRITICAL RULES:
- Extract ONLY actual business names (e.g., "Pizza Hut", "Star Kabab")
- DO NOT extract: sentences, descriptions, website names, generic terms
- Filter out garbage like "Best restaurants", "Top 10", "Location guide"
- Return 5-15 high-quality names per extraction

Return JSON array of names:
["Business Name 1", "Business Name 2", ...]

If no valid names, return: []"""

    user_prompt = f"""Extract {category} names from these search results:

---
{combined_text}
---

Return ONLY real {category} business names in {location}."""

    try:
        # Use AIManager for model rotation
        names = ai_call(system_prompt, user_prompt, temperature=0.2)
        
        if not names or not isinstance(names, list):
            return []
        
        # Convert to dicts
        return [
            {'name': name, 'location': location, 'category': category}
            for name in names
            if isinstance(name, str) and 3 <= len(name) <= 60
        ]
        
    except Exception as e:
        logger.debug(f"AI extraction failed: {e}")
        return []


def _ai_validate_names(names, location, category):
    """
    AI validates and filters restaurant names
    
    Removes duplicates, garbage, and low-quality names
    
    Returns:
        List of validated names
    """
    if not names:
        return []
    
    # Deduplicate first
    seen = set()
    unique = []
    
    for name_dict in names:
        name_lower = name_dict['name'].lower().strip()
        
        if name_lower not in seen and len(name_lower) >= 3:
            seen.add(name_lower)
            unique.append(name_dict)
    
    logger.info(f"After dedup: {len(unique)} unique names")
    
    # If we have a reasonable amount, return them
    if len(unique) >= 20:
        return unique
    
    # Otherwise, we need more data
    logger.warning(f"Only {len(unique)} names found - may need more searches")
    return unique
