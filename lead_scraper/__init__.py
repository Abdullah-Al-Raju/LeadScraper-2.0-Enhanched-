"""
LeadScraper Falcon: Pure Milli-First Lead Collection Engine.
"""

from lead_scraper.models import Lead
from lead_scraper.core import LeadScraper
from lead_scraper.exporter import export_leads
from lead_scraper.search import search_duckduckgo, search_for_official_website
from lead_scraper.discovery import discover_business_candidates

__version__ = "2.0.0"
__all__ = [
    "Lead",
    "LeadScraper",
    "export_leads",
    "search_duckduckgo",
    "search_for_official_website",
    "discover_business_candidates",
]
