"""
Core LeadScraper Engine.
Powered natively by milli_scrapes for ultra-fast, anti-bot resilient contact extraction.
"""

import asyncio
import re
import urllib.parse
from typing import Any, Callable, Dict, List, Optional
from milli_scrapes import UniversalScraper
from lead_scraper.models import Lead
from lead_scraper.search import search_for_official_website, extract_domain
from lead_scraper.discovery import discover_business_candidates
from lead_scraper.config import DEFAULT_CONCURRENCY


class LeadScraper:
    """High-speed business lead extraction engine powered by Milli-Scrapes."""

    def __init__(
        self,
        headless: bool = True,
        auto_consent: bool = True,
        auto_turnstile: bool = True,
        prefer_fast_path: bool = True,
    ):
        self.scraper = UniversalScraper(
            headless=headless,
            auto_consent=auto_consent,
            auto_turnstile=auto_turnstile,
            prefer_fast_path=prefer_fast_path,
        )
        self._browser_lock = asyncio.Lock()

    async def close(self):
        """Cleanly releases browser and connection pool resources."""
        if hasattr(self.scraper, "close"):
            await self.scraper.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _clean_email(email: str) -> str:
        """Strips noisy suffixes and concatenated words from emails."""
        cleaned = email.strip().strip(".,;:<>\"'")
        match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", cleaned)
        if match:
            candidate = match.group(1).rstrip(".,;:")
            candidate = re.sub(
                r"(?i)(\.(?:com|org|net|edu|gov|io|ai|biz|info|co|uk|de|fr|ca|au))(?:phone|tel|telephone|contact|call|mobile|fax|office|hours|email).*$",
                r"\1",
                candidate,
            )
            return candidate.strip(".,;:<>\"'")
        return cleaned

    @staticmethod
    def _extract_address(text: str) -> Optional[str]:
        """Heuristic extractor for physical street addresses in scraped text."""
        if not text:
            return None
        # Pattern for standard street address lines (e.g. 123 Market Street, Suite 400)
        pattern = (
            r"\b\d{1,5}\s+(?:[A-Z][A-Za-z0-9\.\'-]+\s+){1,4}"
            r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Highway|Hwy)\b"
            r"(?:,?\s+(?:Suite|Ste|Unit|Floor|Apt|#)\s*\d+)?"
        )
        match = re.search(pattern, text)
        if match:
            candidate = match.group(0).strip()
            if 8 <= len(candidate) <= 80:
                return candidate
        return None

    @staticmethod
    def _resolve_name(raw_name: Optional[str], text: str, url: str) -> str:
        """Resolves a human-readable business name from raw name, page text, or domain."""
        if raw_name and len(raw_name.strip()) >= 2:
            return raw_name.strip()

        # Try to find title in text or markdown header
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            candidate = title_match.group(1).strip()
            # Clean off site suffixes
            parts = re.split(r"[-|:•—]", candidate)
            if parts and len(parts[0].strip()) >= 2:
                return parts[0].strip()

        # Domain fallback (e.g. https://tartinebakery.com -> Tartine Bakery)
        domain = extract_domain(url)
        if domain:
            base = domain.split(".")[0]
            # Replace dashes/underscores with space and title case
            return base.replace("-", " ").replace("_", " ").title()

        return "Unknown Business"

    # -------------------------------------------------------------------------
    # Core Scrape Methods
    # -------------------------------------------------------------------------

    async def scrape_website(
        self,
        url: str,
        business_name: Optional[str] = None,
        location: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Lead:
        """
        Template 1: Direct Website Extraction.
        Scrapes a target website directly via Milli-Scrapes without any search queries.
        """
        parsed_url = url if url.startswith(("http://", "https://")) else f"https://{url}"
        
        try:
            result = await self.scraper.scrape_url(
                url=parsed_url,
                extract_contacts=True,
                prefer_fast_path=True,
            )
        except Exception:
            # Escalation to headless optical browser serialized by lock
            try:
                async with self._browser_lock:
                    result = await self.scraper.scrape_url(
                        url=parsed_url,
                        extract_contacts=True,
                        force_browser=True,
                    )
            except Exception as e:
                return Lead(
                    business_name=business_name or extract_domain(url).title(),
                    website=parsed_url,
                    location=location,
                    category=category,
                    status=f"error: {str(e)[:50]}",
                )

        contacts = result.get("contacts", {})
        raw_emails = contacts.get("emails", [])
        clean_emails = list(dict.fromkeys(
            self._clean_email(e) for e in raw_emails if "@" in e and len(e) >= 6
        ))
        
        raw_phones = contacts.get("phones", [])
        clean_phones = list(dict.fromkeys(p.strip() for p in raw_phones if len(p.strip()) >= 7))
        
        socials = contacts.get("social_media", {})
        clean_socials = {k: v for k, v in socials.items() if v}
        
        markdown_text = result.get("markdown", "")
        resolved_name = self._resolve_name(business_name, markdown_text, parsed_url)
        extracted_addr = self._extract_address(markdown_text)

        lead = Lead(
            business_name=resolved_name,
            website=parsed_url,
            category=category,
            location=location,
            emails=clean_emails,
            phones=clean_phones,
            social_media=clean_socials,
            address=extracted_addr,
            status="success",
            engine=result.get("engine", "milli-scrapes"),
        )
        lead.calculate_confidence()
        return lead

    async def scrape_named_business(
        self,
        name: str,
        location: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Lead:
        """
        Template 2: Named Business Extraction.
        Executes exactly 1 targeted site search, then crawls the official website via Milli.
        """
        website = search_for_official_website(name, location)
        if website:
            return await self.scrape_website(
                url=website,
                business_name=name,
                location=location,
                category=category,
            )

        # Fallback if no website could be found
        lead = Lead(
            business_name=name,
            website=None,
            location=location,
            category=category,
            status="no_website_found",
        )
        lead.calculate_confidence()
        return lead

    async def scrape_batch(
        self,
        candidates: List[Dict[str, Any]],
        max_concurrency: int = DEFAULT_CONCURRENCY,
        on_progress: Optional[Callable[[int, int, Lead], None]] = None,
    ) -> List[Lead]:
        """
        Processes a list of business candidates concurrently using Milli-Scrapes.
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        total = len(candidates)
        completed = 0
        leads: List[Lead] = []

        async def _worker(candidate: Dict[str, Any]) -> Lead:
            nonlocal completed
            async with semaphore:
                name = candidate.get("name", "Unknown")
                website = candidate.get("website")
                location = candidate.get("location")
                category = candidate.get("category")

                if website:
                    lead = await self.scrape_website(
                        url=website,
                        business_name=name,
                        location=location,
                        category=category,
                    )
                else:
                    lead = await self.scrape_named_business(
                        name=name,
                        location=location,
                        category=category,
                    )

                completed += 1
                if on_progress:
                    on_progress(completed, total, lead)
                return lead

        tasks = [_worker(cand) for cand in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r in results:
            if isinstance(r, Lead):
                leads.append(r)

        return leads

    async def discover_and_scrape(
        self,
        category: str,
        location: str,
        quantity: int = 10,
        max_concurrency: int = DEFAULT_CONCURRENCY,
        on_progress: Optional[Callable[[int, int, Lead], None]] = None,
    ) -> List[Lead]:
        """
        Template 3: Dynamic Category & Location Discovery.
        Discovers official candidate websites dynamically and scrapes them concurrently.
        """
        candidates = discover_business_candidates(
            category=category,
            location=location,
            quantity=quantity,
        )
        if not candidates:
            return []

        return await self.scrape_batch(
            candidates=candidates,
            max_concurrency=max_concurrency,
            on_progress=on_progress,
        )
