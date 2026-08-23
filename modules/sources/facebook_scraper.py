"""
Facebook Business Scraper Module
Searches and extracts contact information from Facebook Business Pages
"""

import re
import httpx
from bs4 import BeautifulSoup
from modules.utils import logger, retry_on_failure, retry_async_on_failure, is_valid_email, format_phone
import config


# ============================================================
# FACEBOOK SEARCH
# ============================================================

@retry_on_failure(max_retries=2)
def search_facebook_business(business_name, location=None, category=None):
    """
    Search for Facebook business page
    
    Args:
        business_name: Name or category of business
        location: Location/city
        category: Business category (optional)
        
    Returns:
        Facebook page URL if found, None otherwise
    """
    try:
        # Construct search query
        query_parts = [f'"{business_name}"']
        if location:
            query_parts.append(f'"{location}"')
        if category and category != business_name:
            query_parts.append(f'"{category}"')
        
        query_parts.append('site:facebook.com/pages OR site:facebook.com inurl:business')
        
        query = ' '.join(query_parts)
        
        logger.info(f"Searching Facebook: {query}")
        
        # Use DuckDuckGo to search Facebook
        from modules.search import search_duckduckgo
        results = search_duckduckgo(query)
        
        if not results:
            logger.debug("No Facebook results found")
            return None
        
        # Find first Facebook business page
        for result in results:
            url = result.get('href') or result.get('link', '')
            if not url:
                continue
            
            # Check if it's a valid Facebook page
            if 'facebook.com' in url.lower():
                # Filter out event pages, videos, posts
                if any(x in url.lower() for x in ['/events/', '/videos/', '/posts/', '/photo']):
                    continue
                
                # Accept pages with /pages/ or valid business page patterns
                if '/pages/' in url or re.search(r'facebook\.com/[^/]+/?$', url):
                    cleaned_url = _clean_facebook_url(url)
                    
                    logger.info(f"Found Facebook page: {cleaned_url}")
                    return cleaned_url
        
        logger.debug("No valid Facebook business page found")
        return None
        
    except Exception as e:
        logger.error(f"Error searching Facebook: {e}")
        return None


def _clean_facebook_url(url):
    """Clean and normalize Facebook URL"""
    # Remove query parameters
    url = url.split('?')[0]
    
    # Convert mobile to www
    url = url.replace('m.facebook.com', 'www.facebook.com')
    url = url.replace('mobile.facebook.com', 'www.facebook.com')
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    return url


# ============================================================
# FACEBOOK DATA EXTRACTION
# ============================================================

@retry_async_on_failure(max_retries=2)
async def extract_facebook_data(page_url):
    """
    Extract business information from Facebook page
    
    Args:
        page_url: Facebook business page URL
        
    Returns:
        Dictionary with extracted contact information and source URL
    """
    if not page_url:
        return None
    
    logger.info(f"Extracting from Facebook page: {page_url}")
    
    try:
        # Fetch the page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(page_url, headers=headers)
            response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract data
        data = _empty_contacts()
        
        # Get all page text for regex/AI fallback
        page_text = soup.get_text(separator=' ', strip=True)
        
        # Business name from title or meta
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Remove "| Facebook" suffix
            business_name = title_text.replace('| Facebook', '').strip()
            if business_name:
                data['business_name'] = business_name
        
        # Try to extract from meta tags
        og_title = soup.find('meta', property='og:title')
        if og_title and not data['business_name']:
            data['business_name'] = og_title.get('content', '').strip()
        
        # Phone number - look for common patterns
        phone_patterns = [
            soup.find('a', href=re.compile('tel:')),
            soup.find(attrs={'data-click': re.compile('phone', re.I)}),
            soup.find(text=re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'))
        ]
        
        for elem in phone_patterns:
            if elem:
                if hasattr(elem, 'get'):
                    phone_text = elem.get('href', '').replace('tel:', '')
                elif hasattr(elem, 'get_text'):
                    phone_text = elem.get_text(strip=True)
                else:
                    phone_text = str(elem)
                
                formatted = format_phone(phone_text)
                if formatted and formatted not in data['phone_numbers']:
                    data['phone_numbers'].append(formatted)
        
        # Regex fallback for phone in text
        if not data['phone_numbers']:
            phone_regex = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            phones = re.findall(phone_regex, page_text)
            for phone in phones[:2]:  # Max 2
                formatted = format_phone(phone)
                if formatted and formatted not in data['phone_numbers']:
                    data['phone_numbers'].append(formatted)
        
        # Email
        email_link = soup.find('a', href=re.compile('mailto:'))
        if email_link:
            email = email_link.get('href', '').replace('mailto:', '')
            if is_valid_email(email):
                data['email_addresses'].append(email)
        
        # Regex fallback for email
        if not data['email_addresses']:
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_regex, page_text)
            for email in emails[:2]:
                if is_valid_email(email) and 'facebook.com' not in email:
                    if email not in data['email_addresses']:
                        data['email_addresses'].append(email)
        
        # Address - look for patterns
        address_elem = soup.find(attrs={'data-click': re.compile('address', re.I)})
        if address_elem:
            data['street_address'] = address_elem.get_text(strip=True)
        
        # Website link - look for external links
        website_link = soup.find('a', href=re.compile(r'^https?://(?!.*facebook\.com)'))
        if website_link:
            href = website_link.get('href', '')
            if 'http' in href and 'facebook.com' not in href:
                data['website'] = href
        
        # Add Facebook URL as source
        data['facebook_url'] = page_url
        data['source_type'] = 'facebook'
        
        if data['business_name'] or data['phone_numbers'] or data['email_addresses']:
            logger.info(f"Extracted from Facebook: {data.get('business_name', 'Unknown')} - {len(data['phone_numbers'])} phones, {len(data['email_addresses'])} emails")
            return data
        else:
            logger.warning(f"No useful data extracted from Facebook page")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting from Facebook {page_url}: {e}")
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
        'facebook_url': None,
        'instagram': None,
        'twitter': None,
        'linkedin': None,
        'business_hours': None,
        'owner_name': None
    }
