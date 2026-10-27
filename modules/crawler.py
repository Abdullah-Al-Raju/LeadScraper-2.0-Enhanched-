"""
Website Crawler Module (Milli-Enhanced & Async)
Fetch homepage, discover contact pages, extract content.

Features:
- Primary Engine: Milli Universal Engine (Dual-Path Fast HTTP SIMD + Optical CDP)
- Anti-Bot & Captcha: In-Loop Cloudflare Turnstile & Cookie Consent auto-sniper
- Contact Discovery: Sitemap mapping and deep route discovery (/contact, /about, /locations)
- Resilient Fallback: AsyncHTTPClient (HTTPX) + BeautifulSoup
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

import config
from modules.utils import (
    logger, can_fetch_url,
    extract_visible_text, normalize_url, is_valid_social_url, is_waf_blocked
)
from modules.http_client import AsyncHTTPClient
from modules.rate_limiter import rate_limiter

# Milli Scrapes Integration
try:
    from milli_scrapes.scraper.universal import UniversalScraper
    from milli_scrapes.crawler.mapper import MilliMapper
    from milli_scrapes.extractor.markdown import HTMLToMarkdownExtractor
    from milli_scrapes.extractor.structured import StructuredDataExtractor
    MILLI_AVAILABLE = True
except ImportError:
    MILLI_AVAILABLE = False


def is_milli_available() -> bool:
    """Check if Milli Scrapes engine is installed and available."""
    return MILLI_AVAILABLE


# ============================================================
# MAIN CRAWL FUNCTION (ASYNC)
# ============================================================

async def crawl_website(url: str, force_milli: bool = True) -> Optional[Dict[str, Any]]:
    """
    Crawl website to extract contact information.
    Uses Milli Universal Engine when available, with automatic HTTPX fallback.
    
    Args:
        url: Website URL to crawl
        force_milli: Prefer Milli engine if available
        
    Returns:
        Dictionary with crawled data or None
    """
    if not url:
        return None
    
    url = normalize_url(url)
    
    # Check robots.txt (if configured)
    if getattr(config, 'RESPECT_ROBOTS_TXT', False) and not can_fetch_url(url):
        logger.warning(f"Blocked by robots.txt: {url}")
        return None
    
    try:
        # Rate limit
        await rate_limiter.acquire('website')
        
        logger.info(f"Crawling: {url} (Milli Engine: {'ENABLED' if MILLI_AVAILABLE and force_milli else 'OFF'})")
        
        # 1. Try Milli Universal Scraper
        if MILLI_AVAILABLE and force_milli:
            try:
                crawl_data = await _crawl_with_milli(url)
                if crawl_data and (crawl_data.get('homepage_text') or crawl_data.get('homepage_html')):
                    logger.info(f"Milli successfully crawled {url} [engine: {crawl_data.get('engine_used')}]")
                    return crawl_data
            except Exception as milli_err:
                logger.warning(f"Milli scrape encountered issue on {url}: {milli_err}. Falling back to HTTPX...")
        
        # 2. Resilient Fallback to HTTPX + BeautifulSoup
        return await _crawl_with_httpx_fallback(url)
        
    except Exception as e:
        logger.error(f"Error crawling {url}: {e}")
        return None


# ============================================================
# MILLI UNIVERSAL ENGINE CRAWLER
# ============================================================

async def _crawl_with_milli(url: str, max_contact_pages: int = 2) -> Optional[Dict[str, Any]]:
    """
    Crawls a target website using Milli's Universal Scraper.
    Bypasses Cloudflare Turnstile, auto-dismisses cookie consent banners,
    and extracts structured metadata and clean Markdown.
    """
    scraper = UniversalScraper(
        headless=True,
        auto_consent=True,
        auto_turnstile=True,
        prefer_fast_path=True
    )
    
    try:
        # 1. Scrape Homepage
        res = await scraper.scrape_url(url, triage=True)
        html = res.get("html") or res.get("metadata", {}).get("raw_html", "")
        markdown = res.get("markdown", "")
        
        # Check if WAF blocked or access denied - escalate to optical browser Turnstile solver
        if is_waf_blocked(html, markdown):
            logger.info(f"WAF or Challenge detected on {url}. Escalating to Milli Optical Browser with Turnstile solver...")
            try:
                res = await scraper.scrape_url(url, force_browser=True)
                html = res.get("html") or res.get("metadata", {}).get("raw_html", "")
                markdown = res.get("markdown", "")
            except Exception as esc_err:
                logger.debug(f"Optical browser escalation error: {esc_err}")
                return None
            if is_waf_blocked(html, markdown):
                logger.warning(f"Target {url} remained protected after browser escalation.")
                return None
        
        soup = BeautifulSoup(html, 'lxml') if html else None
        page_title = res.get('title') or (soup.title.get_text(strip=True) if soup and soup.title else "")
        
        mailto_links = _extract_mailto_links(soup) if soup else []
        tel_links = _extract_tel_links(soup) if soup else []
        social_links = _extract_social_links(soup) if soup else _empty_social_links()
        
        # Merge Milli contact discoveries (social media handles validated)
        milli_contacts = res.get("contacts", {})
        if milli_contacts.get("social_media"):
            m_soc = milli_contacts["social_media"]
            for k in ("facebook", "instagram", "twitter_x", "linkedin", "youtube", "tiktok"):
                target_k = "twitter" if k == "twitter_x" else k
                s_val = m_soc.get(k)
                if s_val and is_valid_social_url(s_val) and not social_links.get(target_k):
                    social_links[target_k] = s_val
            
        structured_data = _extract_structured_data(soup) if soup else []
        if res.get("tables"):
            structured_data.append({"milli_tables": res.get("tables")})
            
        crawl_data = {
            'homepage_url': url,
            'title': page_title,
            'homepage_html': html,
            'homepage_text': markdown if markdown else (extract_visible_text(soup) if soup else ""),
            'contact_pages': [],
            'structured_data': structured_data,
            'mailto_links': list(set(mailto_links)),
            'tel_links': list(set(tel_links)),
            'social_links': social_links,
            'engine_used': f"milli_{res.get('engine', 'universal')}",
            'milli_contacts': milli_contacts
        }
        
        # 2. Discover Contact Pages from page links
        contact_urls = []
        if soup:
            contact_urls = _find_contact_pages(soup, url)
            
        # Only check blind guess if no contact URLs were found and no email was extracted on homepage
        if not contact_urls and not crawl_data['mailto_links'] and not milli_contacts.get('emails'):
            contact_urls = [urljoin(url, "/contact")][:max_contact_pages]
        else:
            contact_urls = contact_urls[:max_contact_pages]
            
        # 3. Fetch subpages with Milli concurrently with tight timeout
        if contact_urls:
            async def _fetch_sub(sub_url: str):
                try:
                    sub_res = await asyncio.wait_for(scraper.scrape_url(sub_url, triage=True), timeout=3.5)
                    sub_html = sub_res.get("html") or ""
                    sub_soup = BeautifulSoup(sub_html, 'lxml') if sub_html else None
                    sub_text = sub_res.get("markdown") or (extract_visible_text(sub_soup) if sub_soup else "")
                    
                    sub_mails = _extract_mailto_links(sub_soup) if sub_soup else []
                    sub_tels = _extract_tel_links(sub_soup) if sub_soup else []
                    sub_social = _extract_social_links(sub_soup) if sub_soup else {}
                    if sub_res.get("contacts", {}).get("social_media"):
                        sub_soc = sub_res["contacts"]["social_media"]
                        for k in ("facebook", "instagram", "twitter_x", "linkedin", "youtube", "tiktok"):
                            target_k = "twitter" if k == "twitter_x" else k
                            s_val = sub_soc.get(k)
                            if s_val and is_valid_social_url(s_val) and not sub_social.get(target_k):
                                sub_social[target_k] = s_val
                    
                    return {
                        "url": sub_url,
                        "text": sub_text,
                        "html": sub_html,
                        "mailto_links": sub_mails,
                        "tel_links": sub_tels,
                        "social_links": sub_social,
                        "structured_data": _extract_structured_data(sub_soup) if sub_soup else []
                    }
                except Exception as e:
                    logger.debug(f"Subpage scrape error for {sub_url}: {e}")
                    return None
                    
            sub_tasks = [_fetch_sub(cu) for cu in contact_urls[:max_contact_pages]]
            sub_results = await asyncio.gather(*sub_tasks, return_exceptions=True)
            
            for sub_data in sub_results:
                if sub_data and not isinstance(sub_data, Exception):
                    crawl_data['contact_pages'].append({
                        'url': sub_data.get('url', ''),
                        'text': sub_data.get('text', '')
                    })
                    crawl_data['structured_data'].extend(sub_data.get('structured_data', []))
                    crawl_data['mailto_links'].extend(sub_data.get('mailto_links', []))
                    crawl_data['tel_links'].extend(sub_data.get('tel_links', []))
                    
                    for s_key, s_val in sub_data.get('social_links', {}).items():
                        if s_val and not crawl_data['social_links'].get(s_key):
                            crawl_data['social_links'][s_key] = s_val
                            
        crawl_data['mailto_links'] = list(set(crawl_data['mailto_links']))
        crawl_data['tel_links'] = list(set(crawl_data['tel_links']))
        
        all_text = crawl_data['homepage_text']
        for page in crawl_data['contact_pages']:
            all_text += "\n\n" + page['text']
        crawl_data['combined_text'] = all_text
        
        return crawl_data
        
    finally:
        if scraper._owns_browser and scraper.browser._engine:
            try:
                await scraper.browser.aclose()
            except Exception:
                pass


# ============================================================
# HTTPX FALLBACK CRAWLER
# ============================================================

async def _crawl_with_httpx_fallback(url: str) -> Optional[Dict[str, Any]]:
    """Resilient fallback crawler using AsyncHTTPClient."""
    async with AsyncHTTPClient() as http:
        homepage_data = await _fetch_page(url, http)
        
        if not homepage_data:
            return None
        
        page_title = homepage_data['soup'].title.get_text(strip=True) if homepage_data.get('soup') and homepage_data['soup'].title else ""
        crawl_data = {
            'homepage_url': url,
            'title': page_title,
            'homepage_html': homepage_data['html'],
            'homepage_text': homepage_data['text'],
            'contact_pages': [],
            'structured_data': homepage_data.get('structured_data', []),
            'mailto_links': homepage_data.get('mailto_links', []),
            'tel_links': homepage_data.get('tel_links', []),
            'social_links': homepage_data.get('social_links', {}),
            'engine_used': 'httpx_fallback'
        }
        
        contact_urls = _find_contact_pages(homepage_data['soup'], url)
        
        if contact_urls:
            contact_tasks = [
                _fetch_page(contact_url, http)
                for contact_url in contact_urls[:2]
            ]
            contact_results = await asyncio.gather(*contact_tasks, return_exceptions=True)
            
            for contact_data in contact_results:
                if contact_data and not isinstance(contact_data, Exception):
                    crawl_data['contact_pages'].append({
                        'url': contact_data.get('url', ''),
                        'text': contact_data['text']
                    })
                    crawl_data['structured_data'].extend(contact_data.get('structured_data', []))
                    crawl_data['mailto_links'].extend(contact_data.get('mailto_links', []))
                    crawl_data['tel_links'].extend(contact_data.get('tel_links', []))
        
        all_text = crawl_data['homepage_text']
        for page in crawl_data['contact_pages']:
            all_text += "\n\n" + page['text']
        
        crawl_data['combined_text'] = all_text
        logger.info(f"Successfully crawled {1 + len(crawl_data['contact_pages'])} pages from {url} (HTTPX)")
        return crawl_data


async def _fetch_page(url: str, http: AsyncHTTPClient) -> Optional[Dict[str, Any]]:
    """Fetch and parse a single page using AsyncHTTPClient."""
    try:
        headers = getattr(config, 'HEADERS', {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })
        timeout = getattr(config, 'REQUEST_TIMEOUT', 10)
        
        response = await http.get(
            url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True
        )
        
        if not response:
            return None
        
        soup = BeautifulSoup(response.content, 'lxml')
        text = extract_visible_text(soup)
        if is_waf_blocked(response.text, text):
            logger.warning(f"WAF or Access Denied detected on {url} (HTTPX). Bypassing.")
            return None
        structured_data = _extract_structured_data(soup)
        mailto_links = _extract_mailto_links(soup)
        tel_links = _extract_tel_links(soup)
        social_links = _extract_social_links(soup)
        
        return {
            'url': url,
            'html': response.text,
            'soup': soup,
            'text': text,
            'structured_data': structured_data,
            'mailto_links': mailto_links,
            'tel_links': tel_links,
            'social_links': social_links
        }
        
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


# ============================================================
# CONTACT PAGE DISCOVERY & UTILITIES
# ============================================================

def _find_contact_pages(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Find contact page URLs from homepage soup."""
    contact_pages = []
    links = soup.find_all('a', href=True)
    scored_links = []
    
    contact_url_keywords = getattr(config, 'CONTACT_URL_KEYWORDS', [
        'contact', 'about', 'reach', 'location', 'touch', 'support', 'help'
    ])
    contact_anchor_keywords = getattr(config, 'CONTACT_ANCHOR_KEYWORDS', [
        'contact', 'about', 'get in touch', 'reach us', 'find us', 'our office'
    ])
    
    for link in links:
        href = link['href']
        text = link.get_text(strip=True).lower()
        
        absolute_url = urljoin(base_url, href)
        
        if not _is_same_domain(absolute_url, base_url):
            continue
        
        if href.startswith('#') or href.startswith('javascript:'):
            continue
        
        score = _score_contact_link(absolute_url, text, contact_url_keywords, contact_anchor_keywords)
        if score > 0:
            scored_links.append({'url': absolute_url, 'score': score})
    
    scored_links.sort(key=lambda x: x['score'], reverse=True)
    
    seen = set()
    for item in scored_links:
        if item['url'] not in seen:
            seen.add(item['url'])
            contact_pages.append(item['url'])
    
    return contact_pages


def _score_contact_link(url: str, anchor_text: str, url_keywords: List[str], anchor_keywords: List[str]) -> int:
    """Score a link for likelihood of being a contact page."""
    score = 0
    url_lower = url.lower()
    text_lower = anchor_text.lower()
    
    for keyword in url_keywords:
        if keyword in url_lower:
            score += 10
            break
    
    for keyword in anchor_keywords:
        if keyword in text_lower:
            score += 10
            break
            
    return score


def _is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are from the same domain."""
    domain1 = urlparse(url1).netloc.replace('www.', '')
    domain2 = urlparse(url2).netloc.replace('www.', '')
    return domain1 == domain2


def _extract_structured_data(soup: BeautifulSoup) -> List[Any]:
    """Extract JSON-LD and Schema.org structured data."""
    structured_data = []
    scripts = soup.find_all('script', type='application/ld+json')
    
    for script in scripts:
        try:
            if script.string:
                data = json.loads(script.string)
                structured_data.append(data)
        except Exception:
            continue
    
    return structured_data


def _extract_mailto_links(soup: BeautifulSoup) -> List[str]:
    """Extract all mailto: links."""
    mailto_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.lower().startswith('mailto:'):
            email = href[7:].split('?')[0].strip()
            if email:
                mailto_links.append(email)
    return list(set(mailto_links))


def _extract_tel_links(soup: BeautifulSoup) -> List[str]:
    """Extract all tel: links."""
    tel_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.lower().startswith('tel:'):
            phone = href[4:].strip()
            if phone:
                tel_links.append(phone)
    return list(set(tel_links))


def _empty_social_links() -> Dict[str, Optional[str]]:
    return {
        'facebook': None,
        'instagram': None,
        'twitter': None,
        'linkedin': None,
        'youtube': None,
        'tiktok': None,
        'whatsapp': None
    }


def _extract_social_links(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """Extract comprehensive social media links."""
    social_links = _empty_social_links()
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        href_lower = href.lower()
        
        if not is_valid_social_url(href):
            continue
            
        parsed_href = urlparse(href)
        netloc = parsed_href.netloc.lower()
        
        if ('facebook.com' in netloc or 'fb.me' in netloc) and not social_links['facebook']:
            social_links['facebook'] = href
        elif 'instagram.com' in netloc and not social_links['instagram']:
            social_links['instagram'] = href
        elif ('twitter.com' in netloc or netloc == 'x.com' or netloc.endswith('.x.com')) and not social_links['twitter']:
            social_links['twitter'] = href
        elif 'linkedin.com' in netloc and not social_links['linkedin']:
            social_links['linkedin'] = href
        elif ('youtube.com' in netloc or 'youtu.be' in netloc) and not social_links['youtube']:
            social_links['youtube'] = href
        elif 'tiktok.com' in netloc and not social_links['tiktok']:
            social_links['tiktok'] = href
        elif ('wa.me' in netloc or 'whatsapp' in netloc) and not social_links['whatsapp']:
            social_links['whatsapp'] = href
    
    return social_links
