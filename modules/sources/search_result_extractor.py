"""
Search Result Extractor Module
Extracts business data FROM search result snippets (not the actual pages)
MAXIMUM EXTRACTION MODE - All possible patterns
"""

import re
import requests
from bs4 import BeautifulSoup
from modules.utils import (
    logger, is_valid_email, format_phone,
    is_valid_social_url, normalize_url, is_aggregator
)
from modules.search import is_result_relevant
import config


# ============================================================
# EXTRACTION PATTERNS
# ============================================================

# Phone number patterns (aligned with config)
PHONE_PATTERNS = getattr(config, 'PHONE_PATTERNS', [
    r'(?<![\d.])(?:\+?1[\s.-]?)?\(?([2-9][0-9]{2})\)?[\s.-]?([2-9][0-9]{2})[\s.-]?([0-9]{4})(?!\d)',
    r'(?<![\d.])\+([1-9][0-9]{0,2})[\s.-]?\(?([0-9]{1,4})\)?[\s.-]?([0-9]{2,4})[\s.-]?([0-9]{2,4})(?:[\s.-]?([0-9]{2,4}))?(?!\d)',
])

# Email patterns
EMAIL_PATTERNS = [config.EMAIL_PATTERN]

# Social media patterns (ALL platforms)
SOCIAL_PATTERNS = {
    'facebook': [
        r'(?:facebook\.com|fb\.com|fb\.me)/(?:pages/)?(?:[\w\.\-]+/)?(\w+)',
        r'fb\.com/([\w\.\-]+)',
    ],
    'instagram': [
        r'(?:instagram\.com|instagr\.am)/(\w+)',
    ],
    'twitter': [
        r'(?:twitter\.com|x\.com)/(\w+)',
    ],
    'linkedin': [
        r'linkedin\.com/(?:company|in)/([\w\-]+)',
    ],
    'tiktok': [
        r'tiktok\.com/@([\w\.\-]+)',
    ],
    'whatsapp': [
        r'(?:wa\.me|api\.whatsapp\.com)/(\d+)',
        r'whatsapp:(\d+)',
    ],
    'youtube': [
        r'youtube\.com/(?:c|channel|user)/([\w\-]+)',
    ],
}

# Address patterns (ALL formats)
ADDRESS_PATTERNS = [
    # General pattern with city, state, zip
    r'(\d+[^,\n]*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}\s*\d{5})',
    
    # Street addresses with house/street number (excluding AM/PM time expressions)
    r'\b(\d{1,5}\s+(?!(?:am|pm|AM|PM|min|hour|st|nd|rd|th)\b)(?:[NSEW]\.?\s+)?[A-Za-z0-9\s,.-]+?\b(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Court|Ct|Plaza|Plz)\b\.?(?:,\s*(?:Suite|Ste|Apt|Unit)\s*[A-Za-z0-9]+)?(?:[,\s\n]+[A-Za-z\s]+[,\s]+[A-Za-z]{2,10}\s*\d{5})?)',
    
    # With explicit keywords (must contain street digits)
    r'(?:address|location|located at|find us|visit us)[:|\s]+([^\n]{10,150})',
    
    # Bangladesh format
    r'((?:House|H|Plot|P)[\s#]*\d+[,\s]+[\w\s,]{5,80})',
    
    # GPS coordinates
    r'(?:GPS|coordinates|lat|long)[:|\s]*([-+]?\d+\.\d+,\s*[-+]?\d+\.\d+)',
]

# Business hours patterns (ALL formats)
HOURS_PATTERNS = [
    r'(?:hours?|open|opening|timings?)[:|\s]+([\w\s\-:,]+(?:am|pm|AM|PM|24)[\w\s\-:,]*)',
    r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[\w\s]*:?\s*\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?\s*[-–]\s*\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?',
    r'\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)\s*[-–to]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)',
    r'(?:24/7|24 hours|always open)',
]

# Owner/Manager patterns
OWNER_PATTERNS = [
    r'(?:owner|founder|co-founder|manager|proprietor|ceo|president|contact person|founded by|owned by)[:|\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
]

# Delivery platform patterns
DELIVERY_PATTERNS = {
    'foodpanda': r'foodpanda\.(?:com|bd)',
    'pathao': r'pathao\.(?:com|food)',
    'ubereats': r'ubereats\.com',
    'doordash': r'doordash\.com',
    'grubhub': r'grubhub\.com',
    'zomato': r'zomato\.com',
    'swiggy': r'swiggy\.com',
}


# ============================================================
# SEARCH RESULT SNIPPET EXTRACTION
# ============================================================

def extract_from_search_results(business_name, location, category=None):
    """
    Extract contact info FROM search result snippets.
    Uses targeted single-pass search with fallback to minimize rate limits.
    """
    logger.info(f"Extracting from search results for: {business_name} {location}")
    
    data = _empty_contacts()
    data['business_name'] = business_name
    data['source_type'] = 'search_results'
    
    # 1. Primary comprehensive search query
    primary_query = f'"{business_name}" "{location}" contact phone email'
    try:
        results_data = _search_and_extract(primary_query, business_name=business_name)
        if results_data:
            data = _merge_search_data(data, results_data)
    except Exception as e:
        logger.debug(f"Primary search failed: {e}")
    
    # 2. Only if no contact info was found, try unquoted fallback
    if not (data['phone_numbers'] or data['email_addresses']):
        fallback_query = f'{business_name} {location} contact phone address'
        try:
            results_data = _search_and_extract(fallback_query, business_name=business_name)
            if results_data:
                data = _merge_search_data(data, results_data)
        except Exception as e:
            logger.debug(f"Fallback search failed: {e}")
    
    # Return if we found anything useful
    if data['phone_numbers'] or data['email_addresses'] or data['street_address'] or data['website']:
        logger.info(f"Extracted from search results: {len(data['phone_numbers'])} phones, {len(data['email_addresses'])} emails")
        return data
    
    return None


def _search_and_extract(query, business_name=None):
    """
    Search and extract data from result snippets
    
    Args:
        query: Search query
        business_name: Name of target business
        
    Returns:
        Dictionary with extracted data
    """
    try:
        from modules.search import search_duckduckgo
        
        results = search_duckduckgo(query, max_results=10)
        
        if not results:
            return None
        
        data = _empty_contacts()
        data['business_name'] = business_name
        
        for result in results:
            title = result.get('title', '')
            snippet = result.get('body', '') or result.get('description', '')
            url = result.get('href', '') or result.get('link', '')
            combined_text = f"{title} {snippet} {url}"
            
            # Extract official website if relevant and not aggregator
            if not data.get('website') and url and not is_aggregator(url):
                if is_result_relevant(url, title, business_name or data.get('business_name', '')):
                    data['website'] = normalize_url(url)
            
            _extract_phones(combined_text, data)
            _extract_emails(combined_text, data)
            _extract_social_media(combined_text, data)
            _extract_addresses(combined_text, data)
            _extract_hours(combined_text, data)
            _extract_owner(combined_text, data)
            _extract_delivery_platforms(combined_text, data)
        
        if data['phone_numbers'] or data['email_addresses'] or data['street_address'] or data['website']:
            return data
        return None
        
    except Exception as e:
        logger.debug(f"Error extracting from search results: {e}")
        return None


def _extract_phones(text, data):
    """Extract phone number formats with NANP validation"""
    for pattern in PHONE_PATTERNS:
        for match in re.finditer(pattern, text):
            formatted = format_phone(match.group(0))
            if formatted and formatted not in data['phone_numbers']:
                if len(data['phone_numbers']) < config.MAX_PHONES_PER_BUSINESS:
                    data['phone_numbers'].append(formatted)


def _extract_emails(text, data):
    """Extract email formats with strict validation"""
    for pattern in EMAIL_PATTERNS:
        for match in re.finditer(pattern, text):
            email = match.group(0).rstrip('.,;:!?)>"\'')
            email = re.sub(r'(phone(?:number)?|tel|email|address|contact|website|hours|mon|tue|wed|thu|fri|sat|sun)$', '', email, flags=re.IGNORECASE).rstrip('.,;:!?)>"\'')
            if is_valid_email(email) and email not in data['email_addresses']:
                if len(data['email_addresses']) < config.MAX_EMAILS_PER_BUSINESS:
                    data['email_addresses'].append(email)


def _extract_social_media(text, data):
    """Extract ALL social media links with validation"""
    social_count = 0
    
    for platform, patterns in SOCIAL_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if social_count >= config.MAX_SOCIAL_LINKS:
                    return
                
                # Reconstruct URL and validate
                if platform == 'facebook':
                    url = f"https://facebook.com/{match}"
                    if not data.get('facebook') and is_valid_social_url(url):
                        data['facebook'] = url
                        data['facebook_url'] = url
                        social_count += 1
                elif platform == 'instagram':
                    url = f"https://instagram.com/{match}"
                    if not data.get('instagram') and is_valid_social_url(url):
                        data['instagram'] = url
                        data['instagram_url'] = url
                        social_count += 1
                elif platform == 'twitter':
                    url = f"https://twitter.com/{match}"
                    if not data.get('twitter') and is_valid_social_url(url):
                        data['twitter'] = url
                        social_count += 1
                elif platform == 'linkedin':
                    url = f"https://linkedin.com/company/{match}"
                    if not data.get('linkedin') and is_valid_social_url(url):
                        data['linkedin'] = url
                        social_count += 1
                elif platform == 'tiktok':
                    url = f"https://tiktok.com/@{match}"
                    if not data.get('tiktok') and is_valid_social_url(url):
                        data['tiktok'] = url
                        social_count += 1
                elif platform == 'whatsapp':
                    url = f"https://wa.me/{match}"
                    if not data.get('whatsapp'):
                        data['whatsapp'] = url
                        social_count += 1
                elif platform == 'youtube':
                    url = f"https://youtube.com/{match}"
                    if not data.get('youtube') and is_valid_social_url(url):
                        data['youtube'] = url
                        social_count += 1


def _clean_address(address: str) -> Optional[str]:
    """Clean extracted address string and remove sentence trailing artifacts."""
    if not address or not re.search(r'\d', address):
        return None
    # Remove any URLs
    address = re.sub(r'https?://\S*', '', address).strip()
    
    # If there's a 5-digit zip code, cut off any non-address text following it
    zip_match = re.search(r'^(.*?\b\d{5}(?:-\d{4})?\b)', address)
    if zip_match:
        address = zip_match.group(1).strip()
    elif '. ' in address:
        first_part = address.split('. ')[0].strip()
        if len(first_part) >= 10 and (any(s in first_part for s in ['St', 'Street', 'Ave', 'Avenue', 'Rd', 'Road', 'Blvd', 'Dr', 'Way', 'Lane', 'Ln', 'Ct', 'Plaza', 'Suite', 'Ste', 'Apt', 'Unit']) or re.search(r'\b\d{5}\b', first_part)):
            address = first_part
            
    # Clean whitespace and trailing punctuation
    address = ' '.join(address.split()).rstrip('.,;:-')
    if 10 <= len(address) <= 120 and re.search(r'\d', address):
        return address
    return None


def _extract_addresses(text, data):
    """Extract addresses"""
    if data.get('street_address'):
        return  # Already have address
    
    for pattern in ADDRESS_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_addr = match.group(1).strip()
            cleaned = _clean_address(raw_addr)
            if cleaned:
                data['street_address'] = cleaned
                return


def _extract_hours(text, data):
    """Extract business hours"""
    if data.get('business_hours'):
        return
    
    for pattern in HOURS_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hours = match.group(0).strip() if pattern == HOURS_PATTERNS[-1] else match.group(1).strip()
            data['business_hours'] = hours
            return


def _extract_owner(text, data):
    """Extract owner/manager name"""
    if data.get('owner_name'):
        return
    
    stop_words = {'this', 'that', 'our', 'your', 'the', 'their', 'all', 'any', 'some', 'many', 'family', 'business'}
    for pattern in OWNER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            owner = match.group(1).strip()
            words = owner.lower().split()
            if any(w in stop_words for w in words):
                continue
            data['owner_name'] = owner
            return


def _extract_delivery_platforms(text, data):
    """Extract delivery platform availability"""
    delivery = []
    
    for platform, pattern in DELIVERY_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            delivery.append(platform)
    
    if delivery:
        data['delivery_platforms'] = ', '.join(delivery)


def _merge_search_data(existing, new_data):
    """Merge search result data"""
    if not new_data:
        return existing
    
    # Merge lists
    for phone in new_data.get('phone_numbers', []):
        if phone not in existing['phone_numbers']:
            if len(existing['phone_numbers']) < config.MAX_PHONES_PER_BUSINESS:
                existing['phone_numbers'].append(phone)
    
    for email in new_data.get('email_addresses', []):
        if email not in existing['email_addresses']:
            if len(existing['email_addresses']) < config.MAX_EMAILS_PER_BUSINESS:
                existing['email_addresses'].append(email)
    
    # Merge single values (take first found)
    single_fields = ['street_address', 'business_hours', 'owner_name', 'delivery_platforms',
                     'facebook', 'instagram', 'twitter', 'linkedin', 'whatsapp', 'youtube', 'tiktok',
                     'facebook_url', 'instagram_url']
    
    for field in single_fields:
        if new_data.get(field) and not existing.get(field):
            existing[field] = new_data[field]
    
    return existing


# ============================================================
# FACEBOOK/INSTAGRAM SEARCH EXTRACTION
# ============================================================

def extract_from_social_search(business_name, location, platform='facebook'):
    """
    Extract contact info by searching for social media pages
    and parsing the search result snippets (not the actual page)
    
    Args:
        business_name: Business name
        location: Location
        platform: 'facebook' or 'instagram'
        
    Returns:
        Dictionary with data OR URL to the page
    """
    logger.info(f"Searching {platform.title()} for: {business_name} {location}")
    
    try:
        from modules.search import search_duckduckgo
        
        if platform == 'facebook':
            query = f'"{business_name}" "{location}" site:facebook.com contact phone'
        else:
            query = f'"{business_name}" "{location}" site:instagram.com contact phone'
        
        results = search_duckduckgo(query, max_results=5)
        
        if not results:
            return None
        
        data = _empty_contacts()
        data['business_name'] = business_name
        data['source_type'] = f'{platform}_search'
        
        for result in results:
            url = result.get('href', '') or result.get('link', '')
            title = result.get('title', '')
            snippet = result.get('body', '') or result.get('description', '')
            combined_text = f"{title} {snippet} {url}"
            
            # Store URL if it points to a valid business profile (not a post, media, or group)
            if url and platform in url and is_valid_social_url(url):
                if platform == 'facebook' and not data.get('facebook'):
                    data['facebook'] = url
                    data['facebook_url'] = url
                elif platform == 'instagram' and not data.get('instagram'):
                    data['instagram'] = url
                    data['instagram_url'] = url
            
            # Extract contact from snippet
            _extract_phones(combined_text, data)
            _extract_emails(combined_text, data)
        
        if data.get('facebook') or data.get('instagram') or data['phone_numbers'] or data['email_addresses']:
            logger.info(f"Found {platform} data: {len(data['phone_numbers'])} phones, URL: {data.get('facebook') or data.get('instagram')}")
            return data
        
        return None
        
    except Exception as e:
        logger.debug(f"Error in {platform} search extraction: {e}")
        return None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _empty_contacts():
    """Return empty contacts dictionary with ALL fields"""
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
        'instagram_url': None,
        'twitter': None,
        'linkedin': None,
        'whatsapp': None,
        'youtube': None,
        'tiktok': None,
        'business_hours': None,
        'owner_name': None,
        'delivery_platforms': None,
    }

