"""
Search Result Extractor Module
Extracts business data FROM search result snippets (not the actual pages)
MAXIMUM EXTRACTION MODE - All possible patterns
"""

import re
from modules.utils import logger, is_valid_email, format_phone
import config


# ============================================================
# MAXIMUM EXTRACTION PATTERNS
# ============================================================

# Phone number patterns (ALL formats)
PHONE_PATTERNS = [
    # Bangladesh formats
    r'\+880\s*1[3-9]\d{8}',                          # +880 1712345678
    r'880\s*1[3-9]\d{8}',                             # 880 1712345678
    r'\b01[3-9]\d{8}\b',                              # 01712345678
    r'\b0\d{10}\b',                                   # 01234567890

    # International formats
    r'\+\d{1,4}\s*\(?\d{1,4}\)?\s*\d{3,}[-.\s]?\d{3,}[-.\s]?\d{2,}',  # +1 (234) 567-8900
    r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',                # (123) 456-7890
    r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',              # 123-456-7890
    r'\b\d{3}\.\d{3}\.\d{4}\b',                      # 123.456.7890
    r'\b\d{10,15}\b',                                 # 1234567890

    # With keywords
    r'(?:phone|tel|call|mobile|contact|whatsapp|wa)[:|\s]+[\+\d][\d\s\-\(\)\.]{8,20}',

    # Special formats
    r'\+\d+[-.\s]?\d+[-.\s]?\d+[-.\s]?\d+',          # +1-234-567-8900
]

# Email patterns (ALL formats)
EMAIL_PATTERNS = [
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Standard email
    r'(?:email|e-mail|mail|contact)[:|\s]+[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}',
]

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
    # With keywords
    r'(?:address|location|located at|find us|visit us)[:|\s]+([^\n]{10,150})',

    # Street addresses
    r'(\d+\s+[\w\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)[\w\s,]*)',

    # Bangladesh format
    r'((?:House|H|Plot|P)[\s#]*\d+[,\s]+[\w\s,]{5,80})',

    # General pattern with city
    r'(\d+[^,\n]*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}\s*\d{5})',

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
    r'(?:owner|manager|chef|proprietor|founded by|by|contact person)[:|\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
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
    Extract contact info FROM search result snippets (MAXIMUM mode)

    Args:
        business_name: Business name or category
        location: Location/city
        category: Business category (optional)

    Returns:
        Dictionary with extracted contact information
    """
    logger.info(f"Extracting from search results for: {business_name} {location}")

    data = _empty_contacts()
    data['business_name'] = business_name
    data['source_type'] = 'search_results'

    # Try multiple search queries
    queries = [
        f'"{business_name}" "{location}" phone contact address',
        f'"{business_name}" "{location}" email website',
        f'"{business_name}" "{location}" facebook instagram',
        f'{business_name} {location} hours location',
    ]

    for query in queries:
        try:
            results_data = _search_and_extract(query)

            if results_data:
                data = _merge_search_data(data, results_data)

        except Exception as e:
            logger.debug(f"Search query failed: {e}")

    # Return if we found anything useful
    if data['phone_numbers'] or data['email_addresses'] or data['street_address']:
        logger.info(f"Extracted from search results: {len(data['phone_numbers'])} phones, {len(data['email_addresses'])} emails")
        return data

    return None


def _search_and_extract(query):
    """
    Search and extract data from result snippets (MAXIMUM extraction)

    Args:
        query: Search query

    Returns:
        Dictionary with extracted data
    """
    try:
        from modules.search import search_duckduckgo

        results = search_duckduckgo(query, max_results=10)

        if not results:
            return None

        data = _empty_contacts()

        for result in results:
            title = result.get('title', '')
            snippet = result.get('body', '') or result.get('description', '')
            url = result.get('href', '') or result.get('link', '')
            combined_text = f"{title} {snippet} {url}"

            # Extract EVERYTHING
            _extract_phones(combined_text, data)
            _extract_emails(combined_text, data)
            _extract_social_media(combined_text, data)
            _extract_addresses(combined_text, data)
            _extract_hours(combined_text, data)
            _extract_owner(combined_text, data)
            _extract_delivery_platforms(combined_text, data)

        return data if (data['phone_numbers'] or data['email_addresses']) else None

    except Exception as e:
        logger.debug(f"Error extracting from search results: {e}")
        return None


def _extract_phones(text, data):
    """Extract ALL phone number formats"""
    for pattern in PHONE_PATTERNS:
        phones = re.findall(pattern, text, re.IGNORECASE)
        for phone in phones:
            formatted = format_phone(phone)
            if formatted and formatted not in data['phone_numbers']:
                # Don't exceed limit
                if len(data['phone_numbers']) < config.MAX_PHONES_PER_BUSINESS:
                    data['phone_numbers'].append(formatted)


def _extract_emails(text, data):
    """Extract ALL email formats"""
    for pattern in EMAIL_PATTERNS:
        emails = re.findall(pattern, text, re.IGNORECASE)
        for email in emails:
            if is_valid_email(email) and email not in data['email_addresses']:
                if len(data['email_addresses']) < config.MAX_EMAILS_PER_BUSINESS:
                    data['email_addresses'].append(email)


def _extract_social_media(text, data):
    """Extract ALL social media links"""
    social_count = 0

    for platform, patterns in SOCIAL_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if social_count >= config.MAX_SOCIAL_LINKS:
                    return

                # Reconstruct URL
                if platform == 'facebook':
                    url = f"https://facebook.com/{match}"
                    if not data.get('facebook'):
                        data['facebook'] = url
                        data['facebook_url'] = url
                        social_count += 1
                elif platform == 'instagram':
                    url = f"https://instagram.com/{match}"
                    if not data.get('instagram'):
                        data['instagram'] = url
                        data['instagram_url'] = url
                        social_count += 1
                elif platform == 'twitter':
                    url = f"https://twitter.com/{match}"
                    if not data.get('twitter'):
                        data['twitter'] = url
                        social_count += 1
                elif platform == 'linkedin':
                    url = f"https://linkedin.com/company/{match}"
                    if not data.get('linkedin'):
                        data['linkedin'] = url
                        social_count += 1
                elif platform == 'tiktok':
                    url = f"https://tiktok.com/@{match}"
                    data['tiktok'] = url
                    social_count += 1
                elif platform == 'whatsapp':
                    url = f"https://wa.me/{match}"
                    data['whatsapp'] = url
                    social_count += 1
                elif platform == 'youtube':
                    url = f"https://youtube.com/{match}"
                    data['youtube'] = url
                    social_count += 1


def _extract_addresses(text, data):
    """Extract addresses"""
    if data.get('street_address'):
        return  # Already have address

    for pattern in ADDRESS_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            address = match.group(1).strip()
            # Clean up address
            address = ' '.join(address.split())
            if len(address) >= 10 and len(address) <= 150:
                data['street_address'] = address
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

    for pattern in OWNER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            owner = match.group(1).strip()
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

            # Store URL
            if url and platform in url:
                if platform == 'facebook':
                    data['facebook'] = url
                    data['facebook_url'] = url
                else:
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

