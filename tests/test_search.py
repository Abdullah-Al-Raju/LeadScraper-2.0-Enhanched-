import pytest
from unittest.mock import patch, MagicMock
from lead_scraper.search import (
    extract_domain,
    is_aggregator,
    search_duckduckgo,
    search_for_official_website,
)


def test_extract_domain():
    assert extract_domain("https://www.tartinebakery.com/menu") == "tartinebakery.com"
    assert extract_domain("http://m.yelp.com/biz/123") == "yelp.com"
    assert extract_domain("https://sub.domain.co.uk/page") == "sub.domain.co.uk"
    assert extract_domain("") == ""


def test_is_aggregator():
    assert is_aggregator("https://www.yelp.com/biz/blue-bottle") is True
    assert is_aggregator("https://tripadvisor.com/restaurants") is True
    assert is_aggregator("https://www.facebook.com/bluebottle") is True
    assert is_aggregator("https://www.yellowpages.com/search") is True
    assert is_aggregator("https://bluebottlecoffee.com") is False
    assert is_aggregator("https://tartinebakery.com") is False


def test_search_for_official_website():
    mock_results = [
        {"title": "Tartine Bakery on Yelp", "href": "https://www.yelp.com/biz/tartine-bakery"},
        {"title": "Tartine Bakery - Official Site", "href": "https://tartinebakery.com/menu"},
        {"title": "Tartine on Facebook", "href": "https://www.facebook.com/tartine"},
    ]
    with patch("lead_scraper.search.search_duckduckgo", return_value=mock_results):
        site = search_for_official_website("Tartine Bakery", "San Francisco")
        assert site == "https://tartinebakery.com"


def test_search_for_official_website_not_found():
    mock_results = [
        {"title": "Tartine on Yelp", "href": "https://www.yelp.com/biz/tartine"},
        {"title": "Tartine on TripAdvisor", "href": "https://www.tripadvisor.com/tartine"},
    ]
    with patch("lead_scraper.search.search_duckduckgo", return_value=mock_results):
        site = search_for_official_website("Unknown Secret Place")
        assert site is None
