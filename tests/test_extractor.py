"""
Unit tests for modules/extractor.py
"""

import pytest
from modules.extractor import (
    extract_contacts,
    extract_from_structured_data,
    extract_with_regex
)
from modules.utils import format_phone, is_valid_email


def test_format_phone():
    assert format_phone("12345") is None  # Too short
    assert format_phone("999-999-9999") is None  # Dummy number
    formatted = format_phone("+1 555-234-5678")
    assert formatted is not None
    assert "234-5678" in formatted


def test_is_valid_email():
    assert is_valid_email("info@example.com") is True
    assert is_valid_email("contact@my-domain.co.uk") is True
    assert is_valid_email("invalid@domain.png") is False
    assert is_valid_email("user@") is False
    assert is_valid_email("notanemail") is False


def test_extract_with_regex():
    text = """
    Welcome to ACME Corp!
    Call us today at +1 555-234-5678 or fax us at 555-876-5432.
    For support, email support@acmecorp.com or reach sales at sales@acmecorp.com.
    Visit us at https://facebook.com/acmepizza and https://instagram.com/acmepizza
    """
    contacts = extract_with_regex(text)
    assert len(contacts["phone_numbers"]) >= 1
    assert any("234-5678" in p for p in contacts["phone_numbers"])
    assert "support@acmecorp.com" in contacts["email_addresses"]
    assert "sales@acmecorp.com" in contacts["email_addresses"]
    assert contacts["facebook"] is not None
    assert "acmepizza" in contacts["facebook"]


def test_extract_from_structured_data():
    structured_data = [
        {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": "ACME Cafe",
            "telephone": "+1-555-987-6543",
            "email": "hello@acmecafe.com",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Main St",
                "addressLocality": "Springfield",
                "addressRegion": "IL",
                "postalCode": "62701"
            }
        }
    ]
    contacts = extract_from_structured_data(structured_data)

    assert contacts["business_name"] == "ACME Cafe"
    assert "(555) 987-6543" in contacts["phone_numbers"]
    assert "hello@acmecafe.com" in contacts["email_addresses"]
    assert contacts["street_address"] == "123 Main St"
    assert contacts["city"] == "Springfield"
    assert contacts["state"] == "IL"
    assert contacts["zip_code"] == "62701"


def test_extract_contacts_with_milli_data():
    crawl_data = {
        "homepage_url": "https://acme.org",
        "homepage_html": "<html><body><h1>ACME</h1></body></html>",
        "combined_text": "ACME Corp main office.",
        "structured_data": [],
        "mailto_links": [],
        "tel_links": [],
        "milli_contacts": {
            "phones": ["+1-555-111-2222"],
            "emails": ["contact@acme.org"]
        },
        "social_links": {
            "linkedin": "https://linkedin.com/company/acme"
        }
    }
    extracted = extract_contacts(crawl_data)
    assert any("111-2222" in p for p in extracted.get("phone_numbers", []))
    assert "contact@acme.org" in extracted.get("email_addresses", [])
    assert extracted.get("linkedin") == "https://linkedin.com/company/acme"


def test_extract_contacts_with_milli_social_media():
    crawl_data = {
        "homepage_url": "https://tokyodining.jp",
        "homepage_html": "<html><body><h1>Tokyo Dining</h1></body></html>",
        "combined_text": "Tokyo Dining authentic sushi in Ginza.",
        "structured_data": [],
        "milli_contacts": {
            "emails": ["reservations@tokyodining.jp"],
            "phones": ["+81-3-1234-5678"],
            "social_media": {
                "instagram": "https://instagram.com/tokyodining_ginza",
                "facebook": "https://facebook.com/tokyodiningjp",
                "twitter_x": "https://x.com/tokyodining",
                "tiktok": "https://tiktok.com/@tokyodining"
            }
        }
    }
    extracted = extract_contacts(crawl_data)
    assert "reservations@tokyodining.jp" in extracted.get("email_addresses", [])
    assert extracted.get("instagram") == "https://instagram.com/tokyodining_ginza"
    assert extracted.get("facebook") == "https://facebook.com/tokyodiningjp"
    assert extracted.get("twitter") == "https://x.com/tokyodining"
    assert extracted.get("tiktok") == "https://tiktok.com/@tokyodining"

