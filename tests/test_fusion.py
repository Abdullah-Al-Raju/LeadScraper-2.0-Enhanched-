"""
Unit tests for modules/fusion.py
"""

import pytest
from modules.fusion import merge_multi_source_data, calculate_confidence_score


def test_merge_multi_source_data():
    sources = [
        {
            "source_type": "website",
            "business_name": "ACME Industries",
            "phone_numbers": ["555-123-4567"],
            "email_addresses": ["info@acme.com"],
            "facebook": "https://facebook.com/acme",
            "twitter": "https://x.com/acme"
        },
        {
            "source_type": "search_snippet",
            "business_name": "ACME Inc",
            "phone_numbers": ["555-999-0000"],
            "street_address": "742 Evergreen Terrace",
            "city": "Springfield"
        }
    ]

    fused = merge_multi_source_data(sources)
    assert fused is not None
    assert fused["business_name"] in ["ACME Industries", "ACME Inc"]
    assert "555-123-4567" in fused["phone_numbers"]
    assert "info@acme.com" in fused["email_addresses"]
    assert fused["street_address"] == "742 Evergreen Terrace"
    assert fused["city"] == "Springfield"
    assert fused["facebook"] == "https://facebook.com/acme"
    assert fused["twitter"] == "https://x.com/acme"
    assert fused["confidence_score"] > 20


def test_calculate_confidence_score():
    profile = {
        "business_name": "Cafe Delight",
        "phone_numbers": ["555-123-4567"],
        "email_addresses": ["cafe@delight.com"],
        "street_address": "123 Coffee Way",
        "website": "https://cafedelight.com",
        "facebook": "https://facebook.com/cafedelight",
        "instagram": "https://instagram.com/cafedelight",
        "sources_used": ["website", "search"]
    }
    score = calculate_confidence_score(profile)
    assert score >= 50
