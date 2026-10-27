"""
Tests for Universal Business Discovery Engine (modules/discovery.py)
"""
import pytest
from modules.discovery import (
    _generate_discovery_queries,
    _clean_candidate_name,
    _is_valid_business_name,
    _extract_business_entities,
    _validate_and_format_entities,
    DISCOVERY_STOPWORDS
)


def test_generate_discovery_queries():
    queries = _generate_discovery_queries("Austin, TX", "plumber")
    assert len(queries) >= 5
    assert any("plumber" in q for q in queries)
    assert any("Austin, TX" in q for q in queries)

    # Test plural handling
    coffee_queries = _generate_discovery_queries("Seattle", "coffee shop")
    assert any("coffee shops" in q for q in coffee_queries)


def test_clean_candidate_name():
    assert _clean_candidate_name("1. Acme Plumbing", "Chicago", "plumber") == "Acme Plumbing"
    assert _clean_candidate_name("Apex Dental - Official Site", "Dallas", "dentist") == "Apex Dental"
    assert _clean_candidate_name("\"Precision Auto Care\"", "Miami", "mechanic") == "Precision Auto Care"


def test_is_valid_business_name():
    # Valid business entities
    assert _is_valid_business_name("Acme Plumbing & Heating", "Chicago", "plumber") is True
    assert _is_valid_business_name("Blue Bottle Coffee", "Oakland", "coffee") is True
    assert _is_valid_business_name("Sullivan & Cromwell LLP", "New York", "lawyer") is True

    # Invalid names / stopword media brands
    assert _is_valid_business_name("Eater Austin", "Austin", "coffee") is False
    assert _is_valid_business_name("Time Out", "Austin", "coffee") is False
    assert _is_valid_business_name("TripAdvisor", "Austin", "hotel") is False
    assert _is_valid_business_name("Best 10 Plumbers", "Chicago", "plumber") is False
    assert _is_valid_business_name("Austin", "Austin", "coffee") is False
    assert _is_valid_business_name("https://example.com", "Austin", "coffee") is False
    assert _is_valid_business_name("A", "Austin", "coffee") is False


def test_extract_business_entities():
    mock_results = [
        {
            "title": "Precision Plumbing - Chicago, IL",
            "body": "Call Precision Plumbing for all residential and commercial plumbing needs."
        },
        {
            "title": "Top 10 Plumbers in Chicago | The Guide",
            "body": "1. Apex Rooter Services\n2. Windy City Pipes\n3. Best Plumber Guide"
        }
    ]
    extracted = _extract_business_entities(mock_results, "Chicago", "plumber")
    assert "Precision Plumbing" in extracted
    assert "Apex Rooter Services" in extracted
    assert "Windy City Pipes" in extracted
    # Media & listicle titles must be rejected
    assert "The Guide" not in extracted
    assert "Top 10 Plumbers" not in extracted


def test_validate_and_format_entities():
    raw_names = ["Apex Dental", "apex dental", "Apex Dental", "Smile Care"]
    formatted = _validate_and_format_entities(raw_names, "Denver", "dentist")
    assert len(formatted) == 2
    assert formatted[0] == {'name': 'Apex Dental', 'location': 'Denver', 'category': 'dentist'}
    assert formatted[1] == {'name': 'Smile Care', 'location': 'Denver', 'category': 'dentist'}
