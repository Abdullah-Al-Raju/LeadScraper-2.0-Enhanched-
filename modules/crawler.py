"""
Website Crawler Module (ASYNC VERSION)
Fetch homepage, discover contact pages, extract content
"""

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
import json
import asyncio
import config
from modules.utils import (
    logger, can_fetch_url,
    extract_visible_text, normalize_url
)
from modules.http_client import AsyncHTTPClient
from modules.rate_limiter import rate_limiter


# ============================================================
# MAIN CRAWL FUNCTION (ASYNC)
# ============================================================

async def crawl_website(url):
    """
    Crawl website to extract contact information (ASYNC)

    Args:
        url: Website URL to crawl

    Returns:
        Dictionary with crawled data or None
    """
    if not url:
        return None

    url = normalize_url(url)

    # Check robots.txt (still sync - quick check)
    if not can_fetch_url(url):
        logger.warning(f"Blocked by robots.txt: {url}")
        return None

    try:
        # Rate limit
        await rate_limiter.acquire('website')

        # Fetch homepage
        logger.info(f"Crawling: {url}")

        async with AsyncHTTPClient() as http:
            homepage_data = await _fetch_page(url, http)

            if not homepage_data:
                return None

            # Initialize result
            crawl_data = {
                'homepage_url': url,
                'homepage_html': homepage_data['html'],
                'homepage_text': homepage_data['text'],
                'contact_pages': [],
                'structured_data': homepage_data.get('structured_data', []),
                'mailto_links': homepage_data.get('mailto_links', []),
                'tel_links': homepage_data.get('tel_links', []),
                'social_links': homepage_data.get('social_links', {})
            }

            # Find contact pages
            contact_urls = _find_contact_pages(homepage_data['soup'], url)

            # Fetch contact pages concurrently (limit to 2)
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

                        # Merge additional data
                        crawl_data['structured_data'].extend(contact_data.get('structured_data', []))
                        crawl_data['mailto_links'].extend(contact_data.get('mailto_links', []))
                        crawl_data['tel_links'].extend(contact_data.get('tel_links', []))

            # Combine all text
            all_text = crawl_data['homepage_text']
            for page in crawl_data['contact_pages']:
                all_text += "\n\n" + page['text']

            crawl_data['combined_text'] = all_text

            logger.info(f"Successfully crawled {1 + len(crawl_data['contact_pages'])} pages from {url}")

            return crawl_data

    except Exception as e:
        logger.error(f"Error crawling {url}: {e}")
        return None


# ============================================================
# PAGE FETCHING (ASYNC)
# ============================================================

async def _fetch_page(url, http: AsyncHTTPClient):
    """
    Fetch and parse a single page (ASYNC)

    Args:
        url: URL to fetch
        http: AsyncHTTPClient instance

    Returns:
        Dictionary with page data or None
    """
    try:
        # Make async request
        response = await http.get(
            url,
            headers=config.HEADERS,
            timeout=config.REQUEST_TIMEOUT,
            follow_redirects=True
        )

        if not response:
            return None

        # Parse HTML
        soup = BeautifulSoup(response.content, 'lxml')

        # Extract visible text
        text = extract_visible_text(soup)

        # Extract structured data
        structured_data = _extract_structured_data(soup)

        # Extract mailto links
        mailto_links = _extract_mailto_links(soup)

        # Extract tel links
        tel_links = _extract_tel_links(soup)

        # Extract social media links
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
# CONTACT PAGE DISCOVERY (SYNC - CPU bound)
# ============================================================

def _find_contact_pages(soup, base_url):
    """
    Find contact page URLs from homepage

    Args:
        soup: BeautifulSoup object of homepage
        base_url: Base URL for resolving relative links

    Returns:
        List of contact page URLs
    """
    contact_pages = []

    # Find all links
    links = soup.find_all('a', href=True)

    # Score each link
    scored_links = []

    for link in links:
        href = link['href']
        text = link.get_text(strip=True).lower()

        # Resolve relative URLs
        absolute_url = urljoin(base_url, href)

        # Skip external links
        if not _is_same_domain(absolute_url, base_url):
            continue

        # Skip anchors and javascript
        if href.startswith('#') or href.startswith('javascript:'):
            continue

        # Score the link
        score = _score_contact_link(absolute_url, text)

        if score > 0:
            scored_links.append({
                'url': absolute_url,
                'score': score
            })

    # Sort by score
    scored_links.sort(key=lambda x: x['score'], reverse=True)

    # Remove duplicates
    seen = set()
    for link in scored_links:
        if link['url'] not in seen:
            seen.add(link['url'])
            contact_pages.append(link['url'])

    logger.debug(f"Found {len(contact_pages)} potential contact pages")

    return contact_pages


def _score_contact_link(url, anchor_text):
    """Score a link for likelihood of being a contact page"""
    score = 0

    url_lower = url.lower()
    text_lower = anchor_text.lower()

    # Check URL keywords
    for keyword in config.CONTACT_URL_KEYWORDS:
        if keyword in url_lower:
            score += 10
            break

    # Check anchor text keywords
    for keyword in config.CONTACT_ANCHOR_KEYWORDS:
        if keyword in text_lower:
            score += 10
            break

    return score


def _is_same_domain(url1, url2):
    """Check if two URLs are from the same domain"""
    domain1 = urlparse(url1).netloc.replace('www.', '')
    domain2 = urlparse(url2).netloc.replace('www.', '')
    return domain1 == domain2


# ============================================================
# STRUCTURED DATA EXTRACTION (SYNC - CPU bound)
# ============================================================

def _extract_structured_data(soup):
    """Extract JSON-LD and Schema.org structured data"""
    structured_data = []

    scripts = soup.find_all('script', type='application/ld+json')

    for script in scripts:
        try:
            data = json.loads(script.string)
            structured_data.append(data)
            logger.debug(f"Found structured data: {type(data)}")
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Error parsing JSON-LD: {e}")
            continue

    return structured_data


def _extract_mailto_links(soup):
    """Extract all mailto: links"""
    mailto_links = []

    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('mailto:'):
            email = href.replace('mailto:', '').split('?')[0]
            mailto_links.append(email)

    return list(set(mailto_links))


def _extract_tel_links(soup):
    """Extract all tel: links"""
    tel_links = []

    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('tel:'):
            phone = href.replace('tel:', '').strip()
            tel_links.append(phone)

    return list(set(tel_links))


def _extract_social_links(soup):
    """
    Extract social media links

    Returns:
        Dictionary with social media URLs
    """
    social_links = {
        'facebook': None,
        'instagram': None,
        'twitter': None,
        'linkedin': None
    }

    for link in soup.find_all('a', href=True):
        href = link['href'].lower()

        if 'facebook.com' in href and not social_links['facebook']:
            social_links['facebook'] = link['href']
        elif 'instagram.com' in href and not social_links['instagram']:
            social_links['instagram'] = link['href']
        elif ('twitter.com' in href or 'x.com' in href) and not social_links['twitter']:
            social_links['twitter'] = link['href']
        elif 'linkedin.com' in href and not social_links['linkedin']:
            social_links['linkedin'] = link['href']

    return social_links
