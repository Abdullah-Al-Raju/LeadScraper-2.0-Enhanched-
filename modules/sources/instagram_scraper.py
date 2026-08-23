"""
Instagram Business Scraper Module
Searches and extracts contact information from Instagram Business Profiles
"""

import re

from bs4 import BeautifulSoup
from modules.utils import logger, retry_on_failure, async_retry_on_failure, is_valid_email, format_phone


# ============================================================
# INSTAGRAM SEARCH
# ============================================================

@retry_on_failure(max_retries=2)
def search_instagram_business(business_name, location=None, category=None):
    """
    Search for Instagram business profile

    Args:
        business_name: Name or category of business
        location: Location/city
        category: Business category (optional)

    Returns:
        Instagram profile URL if found, None otherwise
    """
    try:
        # Construct search query
        query_parts = [f'"{business_name}"']
        if location:
            query_parts.append(f'"{location}"')
        if category and category != business_name:
            query_parts.append(f'"{category}"')

        query_parts.append('site:instagram.com')

        query = ' '.join(query_parts)

        logger.info(f"Searching Instagram: {query}")

        # Use DuckDuckGo to search Instagram
        from modules.search import search_duckduckgo
        results = search_duckduckgo(query)

        if not results:
            logger.debug("No Instagram results found")
            return None

        # Find first Instagram profile
        for result in results:
            url = result.get('href') or result.get('link', '')
            if not url:
                continue

            # Check if it's a valid Instagram profile
            if 'instagram.com' in url.lower():
                # Filter out posts, reels, stories, explore
                if any(
                    x in url.lower() for x in [
                        '/p/',
                        '/reel/',
                        '/stories/',
                        '/explore/',
                        '/tv/']):
                    continue

                # Accept profile URLs
                if re.search(r'instagram\.com/[^/]+/?$', url):
                    cleaned_url = _clean_instagram_url(url)

                    logger.info(f"Found Instagram profile: {cleaned_url}")
                    return cleaned_url

        logger.debug("No valid Instagram business profile found")
        return None

    except Exception as e:
        logger.error(f"Error searching Instagram: {e}")
        return None


def _clean_instagram_url(url):
    """Clean and normalize Instagram URL"""
    # Remove query parameters
    url = url.split('?')[0]

    # Remove trailing slash
    url = url.rstrip('/')

    return url


# ============================================================
# INSTAGRAM DATA EXTRACTION
# ============================================================

@async_retry_on_failure(max_retries=2)
async def extract_instagram_data(profile_url):
    """
    Extract business information from Instagram profile

    Args:
        profile_url: Instagram business profile URL

    Returns:
        Dictionary with extracted contact information and source URL
    """
    if not profile_url:
        return None

    logger.info(f"Extracting from Instagram profile: {profile_url}")

    try:
        # Fetch the page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        from modules.http_client import get_http_client
        http = await get_http_client()
        response = await http.get(profile_url, headers=headers, timeout=15)

        if not response:
            return None

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # Extract data
        data = _empty_contacts()

        # Get all page text
        # Business name from title or meta
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Extract username (usually "Name (@username) • Instagram")
            match = re.search(r'([^(]+)', title_text)
            if match:
                business_name = match.group(1).strip()
                if business_name and business_name != 'Instagram':
                    data['business_name'] = business_name

        # Try OG meta
        og_title = soup.find('meta', property='og:title')
        if og_title and not data['business_name']:
            data['business_name'] = og_title.get('content', '').strip()

        # Bio description (contains contact info)
        og_description = soup.find('meta', property='og:description')
        bio_text = ''
        if og_description:
            bio_text = og_description.get('content', '').strip()
            logger.debug(f"Instagram bio: {bio_text}")

        # Extract phone from bio
        if bio_text:
            phone_regex = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            phones = re.findall(phone_regex, bio_text)
            for phone in phones:
                formatted = format_phone(phone)
                if formatted and formatted not in data['phone_numbers']:
                    data['phone_numbers'].append(formatted)

        # Extract email from bio
        if bio_text:
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_regex, bio_text)
            for email in emails:
                if is_valid_email(email) and 'instagram.com' not in email:
                    if email not in data['email_addresses']:
                        data['email_addresses'].append(email)

        # Extract website from bio (Instagram shows a clickable link)
        # Look for external links
        external_link = soup.find(
            'a', href=re.compile(r'^https?://(?!.*instagram\.com)'))
        if external_link:
            href = external_link.get('href', '')
            if 'http' in href and 'instagram.com' not in href:
                data['website'] = href

        # Parse address from bio if present
        # Common patterns: "📍 Location" or "Address:"
        if bio_text:
            address_patterns = [
                r'📍\s*([^\\n]+)',
                r'(?:Address|Location):\s*([^\\n]+)',
                r'([A-Z][a-z]+,\s*[A-Z]{2}\s*\d{5})'  # City, ST 12345
            ]
            for pattern in address_patterns:
                match = re.search(pattern, bio_text, re.IGNORECASE)
                if match:
                    data['street_address'] = match.group(1).strip()
                    break

        # Add Instagram URL as source
        data['instagram_url'] = profile_url
        data['source_type'] = 'instagram'

        if data['business_name'] or data['phone_numbers'] or data['email_addresses']:
            logger.info(
                f"Extracted from Instagram: {
                    data.get(
                        'business_name',
                        'Unknown')} - {
                    len(
                        data['phone_numbers'])} phones, {
                    len(
                        data['email_addresses'])} emails")
            return data
        else:
            logger.warning("No useful data extracted from Instagram profile")
            return None

    except Exception as e:
        logger.error(f"Error extracting from Instagram {profile_url}: {e}")
        return None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _empty_contacts():
    """Return empty contacts dictionary"""
    return {
        'business_name': None,
        'phone_numbers': [],
        'email_addresses': [],
        'street_address': None,
        'city': None,
        'state': None,
        'zip_code': None,
        'website': None,
        'facebook': None,
        'instagram': None,
        'instagram_url': None,
        'twitter': None,
        'linkedin': None,
        'business_hours': None,
        'owner_name': None
    }
