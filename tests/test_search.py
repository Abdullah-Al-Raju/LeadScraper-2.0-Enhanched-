"""
Unit tests for modules/search.py
"""

import pytest
from modules.utils import is_aggregator, normalize_url
from modules.search import validate_search_setup


def test_is_aggregator():
    assert is_aggregator("https://www.yelp.com/biz/some-restaurant") is True
    assert is_aggregator("https://www.tripadvisor.com/Restaurant_Review") is True
    assert is_aggregator("https://www.yellowpages.com/item") is True
    assert is_aggregator("https://m.facebook.com/mybusiness") is True
    assert is_aggregator("https://www.joespizzaplace.com") is False
    assert is_aggregator("https://acmewidgets.org/contact") is False


def test_normalize_url():
    assert normalize_url("http://example.com/") == "http://example.com"
    assert normalize_url("example.com/about/") == "https://example.com/about"


def test_validate_search_setup():
    # Validates that search engine connectivity is operational
    assert validate_search_setup() is True
