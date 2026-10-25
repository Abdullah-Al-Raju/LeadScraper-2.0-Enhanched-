"""
Unit tests for modules/crawler.py
"""

import pytest
import asyncio
from bs4 import BeautifulSoup
from modules.crawler import crawl_website, _find_contact_pages, is_milli_available


def test_milli_availability():
    # In this environment, milli_scrapes is installed and should be available
    assert is_milli_available() is True


def test_find_contact_pages():
    base_url = "https://example.com"
    html = """
    <html>
      <body>
        <a href="/contact-us">Contact Us</a>
        <a href="/about">About Us</a>
        <a href="/locations">Locations</a>
        <a href="/privacy-policy">Privacy</a>
        <a href="https://external.com/contact">External Contact</a>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = _find_contact_pages(soup, base_url)

    assert "https://example.com/contact-us" in urls
    assert "https://example.com/about" in urls
    assert "https://external.com/contact" not in urls


@pytest.mark.asyncio
async def test_crawl_website_fallback_httpx():
    # Test crawler with force_milli=False (HTTPX fallback path)
    res = await crawl_website("https://httpbin.org/html", force_milli=False)
    assert res is not None
    assert "Herman Melville" in res["homepage_text"] or len(res["homepage_html"]) > 100
    assert res.get("engine_used") == "httpx_fallback"


@pytest.mark.asyncio
async def test_crawl_website_milli():
    # Test crawler with Milli enabled
    res = await crawl_website("https://httpbin.org/html", force_milli=True)
    assert res is not None
    assert "milli_contacts" in res
    assert len(res.get("combined_text", "")) > 0
