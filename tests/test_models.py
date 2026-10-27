import pytest
from lead_scraper.models import Lead


def test_lead_model_creation_and_defaults():
    lead = Lead(business_name="Falcon Coffee")
    assert lead.business_name == "Falcon Coffee"
    assert lead.website is None
    assert lead.emails == []
    assert lead.phones == []
    assert lead.social_media == {}
    assert lead.confidence_score == 0.0
    assert lead.status == "success"
    assert lead.engine == "milli-scrapes"
    assert lead.scraped_at is not None


def test_lead_calculate_confidence():
    lead = Lead(
        business_name="Blue Bottle",
        website="https://bluebottlecoffee.com",
        emails=["contact@bluebottle.com"],
        phones=["555-1234"],
        social_media={"instagram": "https://instagram.com/bluebottle"},
        address="315 Linden St, San Francisco, CA"
    )
    score = lead.calculate_confidence()
    assert score == 1.0


def test_lead_to_flat_dict():
    lead = Lead(
        business_name="Tartine Bakery",
        website="https://tartinebakery.com",
        emails=["info@tartine.com", "press@tartine.com"],
        phones=["415-555-0199"],
        social_media={"instagram": "https://instagram.com/tartine"},
        location="San Francisco, CA"
    )
    lead.calculate_confidence()
    flat = lead.to_flat_dict()
    assert flat["business_name"] == "Tartine Bakery"
    assert flat["website"] == "https://tartinebakery.com"
    assert flat["emails"] == "info@tartine.com, press@tartine.com"
    assert flat["phones"] == "415-555-0199"
    assert flat["instagram"] == "https://instagram.com/tartine"
    assert flat["location"] == "San Francisco, CA"
    assert flat["confidence_score"] > 0.0


def test_lead_display_card():
    lead = Lead(
        business_name="Sightglass Coffee",
        website="https://sightglasscoffee.com",
        emails=["orders@sightglass.com"],
        phones=["415-648-2200"],
        location="San Francisco"
    )
    lead.calculate_confidence()
    card = lead.display_card()
    assert "SIGHTGLASS COFFEE" in card
    assert "https://sightglasscoffee.com" in card
    assert "orders@sightglass.com" in card
    assert "415-648-2200" in card
