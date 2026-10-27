import pytest
from unittest.mock import patch
from lead_scraper.discovery import (
    generate_discovery_queries,
    clean_title_to_name,
    extract_candidates_from_results,
    discover_business_candidates,
)


def test_generate_discovery_queries():
    queries = generate_discovery_queries("Bakery", "Austin, TX")
    assert len(queries) >= 3
    assert any("Bakery" in q for q in queries)
    assert any("Austin, TX" in q for q in queries)


def test_clean_title_to_name():
    assert clean_title_to_name("Tartine Bakery - Home", "Bakery", "San Francisco") == "Tartine Bakery"
    assert clean_title_to_name("Sightglass Coffee | Best Coffee in SF", "Coffee", "San Francisco") == "Sightglass Coffee"
    assert clean_title_to_name("The 10 Best Bakeries in Austin - Yelp", "Bakery", "Austin") is None


def test_extract_candidates_from_results():
    results = [
        {
            "title": "Tartine Bakery - Official Site",
            "href": "https://tartinebakery.com",
            "body": "Welcome to Tartine Bakery in San Francisco."
        },
        {
            "title": "Top 10 Bakeries in San Francisco - Travel Guide",
            "href": "https://www.tripadvisor.com/bakeries",
            "body": "1. Craftsman and Wolves is a modern patisserie. 2. Arsicault Bakery has great croissants."
        }
    ]
    candidates = extract_candidates_from_results(results, "San Francisco", "Bakery")
    assert len(candidates) >= 2
    
    # Check official direct site candidate
    tartine = next((c for c in candidates if c["website"] == "https://tartinebakery.com"), None)
    assert tartine is not None
    assert "Tartine" in tartine["name"]
    
    # Check listicle extracted candidate
    arsicault = next((c for c in candidates if "Arsicault" in c["name"]), None)
    assert arsicault is not None


def test_discover_business_candidates():
    mock_results = [
        {
            "title": "Precision Plumbing Austin",
            "href": "https://precisionplumbingaustin.com",
            "body": "Top plumbing services in Austin."
        },
        {
            "title": "Austin Master Plumbers - Directory",
            "href": "https://austinmasterplumbing.com",
            "body": "Affordable residential and commercial plumbers."
        }
    ]
    with patch("lead_scraper.discovery.search_duckduckgo", return_value=mock_results):
        candidates = discover_business_candidates("Plumber", "Austin, TX", quantity=2)
        assert len(candidates) == 2
        assert candidates[0]["website"] == "https://precisionplumbingaustin.com"
