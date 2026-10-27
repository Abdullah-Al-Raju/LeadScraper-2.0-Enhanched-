import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from lead_scraper.core import LeadScraper
from lead_scraper.models import Lead


def test_clean_email():
    assert LeadScraper._clean_email("info@domain.com") == "info@domain.com"
    assert LeadScraper._clean_email("info@domain.comPhone") == "info@domain.com"
    assert LeadScraper._clean_email("contact@domain.comTelephone: 123") == "contact@domain.com"
    assert LeadScraper._clean_email("<user@domain.com>") == "user@domain.com"


def test_extract_address():
    text = "Visit us at 123 Market Street, Suite 400 for inquiries."
    addr = LeadScraper._extract_address(text)
    assert addr is not None
    assert "123 Market Street" in addr


def test_resolve_name():
    # Provided name overrides
    assert LeadScraper._resolve_name("My Cafe", "Some text", "https://example.com") == "My Cafe"
    
    # Markdown header
    text = "# Tartine Bakery - Fresh Sourdough\nWe bake bread every morning."
    assert LeadScraper._resolve_name(None, text, "https://tartinebakery.com") == "Tartine Bakery"
    
    # Domain fallback
    assert LeadScraper._resolve_name(None, "No title here", "https://blue-bottle-coffee.com") == "Blue Bottle Coffee"


@pytest.mark.asyncio
async def test_scrape_website_direct():
    scraper = LeadScraper(headless=True)
    mock_milli_result = {
        "status": 200,
        "elapsed_ms": 120.5,
        "engine": "fast_http",
        "markdown": "# Blue Bottle Coffee\nWelcome to our cafe. Call 555-1234.",
        "contacts": {
            "emails": ["support@bluebottle.comPhone"],
            "phones": ["555-1234"],
            "social_media": {"instagram": "https://instagram.com/bluebottle"},
        }
    }
    scraper.scraper.scrape_url = AsyncMock(return_value=mock_milli_result)

    lead = await scraper.scrape_website("https://bluebottlecoffee.com")
    assert lead.business_name == "Blue Bottle Coffee"
    assert lead.website == "https://bluebottlecoffee.com"
    assert lead.emails == ["support@bluebottle.com"]
    assert lead.phones == ["555-1234"]
    assert lead.social_media.get("instagram") == "https://instagram.com/bluebottle"
    assert lead.confidence_score > 0.5


@pytest.mark.asyncio
async def test_scrape_named_business():
    scraper = LeadScraper(headless=True)
    with patch("lead_scraper.core.search_for_official_website", return_value="https://tartinebakery.com"):
        scraper.scrape_website = AsyncMock(return_value=Lead(
            business_name="Tartine Bakery",
            website="https://tartinebakery.com",
            emails=["info@tartine.com"],
        ))
        lead = await scraper.scrape_named_business("Tartine Bakery", "San Francisco")
        assert lead.business_name == "Tartine Bakery"
        assert lead.website == "https://tartinebakery.com"
