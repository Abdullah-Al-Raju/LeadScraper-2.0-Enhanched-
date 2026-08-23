"""
Directory Extractor Module
Extracts business contact information FROM directory/aggregator sites
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from modules.utils import logger, retry_on_failure, is_valid_email, format_phone
import config


# ============================================================
# DIRECTORY DETECTION
# ============================================================

# Known extractable directories
EXTRACTABLE_DIRECTORIES = {
    'yelp.com': 'yelp',
    'yellowpages.com': 'yellowpages',
    'foursquare.com': 'foursquare',
    'tripadvisor.com': 'tripadvisor',
    'facebook.com': 'facebook',
    'bdquery.com': 'generic_bd',
    'bangladeshbusinessdir.com': 'generic_bd',
    'doctor360.com.bd': 'generic_bd',
    'artificialbd.com': 'generic_bd',
    'eatinbd.com': 'generic_bd',
    'sweetcandies.us': 'generic',
    'manta.com': 'generic',
    'hotfrog.com': 'generic',
    'yellowbook.com': 'yellowpages'
}


def is_extractable_directory(url):
    """
    Check if URL is from an extractable directory
    
    Args:
        url: URL to check
        
    Returns:
        Tuple (is_directory: bool, directory_type: str)
    """
    if not url:
        return False, None
    
    url_lower = url.lower()
    
    for domain, dir_type in EXTRACTABLE_DIRECTORIES.items():
        if domain in url_lower:
            logger.info(f"Detected extractable directory: {dir_type} ({domain})")
            return True, dir_type
    
    # Check for generic directory patterns
    directory_keywords = ['directory', 'business-list', 'company-profile', 'local-business']
    if any(kw in url_lower for kw in directory_keywords):
        logger.info(f"Detected generic directory pattern in URL")
        return True, 'generic'
    
    return False, None


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

@retry_on_failure(max_retries=2)
def extract_from_directory(url, directory_type=None):
    """
    Extract business data from directory page
    
    Args:
        url: Directory page URL
        directory_type: Type of directory (optional, auto-detect if None)
        
    Returns:
        Dictionary with extracted contact information and source URL
    """
    if not url:
        return None
    
    # Auto-detect directory type if not provided
    if not directory_type:
        is_dir, directory_type = is_extractable_directory(url)
        if not is_dir:
            logger.warning(f"URL not recognized as extractable directory: {url}")
            return None
    
    logger.info(f"Extracting from {directory_type} directory: {url}")
    
    try:
        # Fetch the page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract based on directory type
        extractors = {
            'yelp': extract_from_yelp,
            'yellowpages': extract_from_yellowpages,
            'yellowbook': extract_from_yellowpages,
            'foursquare': extract_from_foursquare,
            'tripadvisor': extract_from_tripadvisor,
            'generic_bd': extract_generic_directory,
            'generic': extract_generic_directory
        }

        extractor_func = extractors.get(directory_type, extract_generic_directory)
        data = extractor_func(soup)
        
        if data:
            # Add source information
            data['directory_url'] = url
            data['source_type'] = f'directory:{directory_type}'
            logger.info(f"Successfully extracted from directory: {data.get('business_name', 'Unknown')}")
            return data
        else:
            logger.warning(f"No data extracted from directory: {url}")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting from directory {url}: {e}")
        return None


# ============================================================
# DIRECTORY-SPECIFIC EXTRACTORS
# ============================================================

def extract_from_yelp(soup):
    """Extract from Yelp business page"""
    data = _empty_contacts()
    
    try:
        # Business name
        name_elem = soup.find('h1', class_=re.compile('businessName|heading'))
        if name_elem:
            data['business_name'] = name_elem.get_text(strip=True)
        
        # Phone number
        phone_elem = soup.find('p', class_=re.compile('phone'))
        if not phone_elem:
            phone_elem = soup.find('a', href=re.compile('tel:'))
        if phone_elem:
            phone_text = phone_elem.get_text(strip=True) if hasattr(phone_elem, 'get_text') else phone_elem.get('href', '').replace('tel:', '')
            formatted = format_phone(phone_text)
            if formatted:
                data['phone_numbers'].append(formatted)
        
        # Address
        address_elem = soup.find('address')
        if address_elem:
            addr_text = address_elem.get_text(strip=True)
            data['street_address'] = addr_text.split(',')[0] if ',' in addr_text else addr_text
        
        # Website
        website_elem = soup.find('a', class_=re.compile('website'))
        if website_elem:
            data['website'] = website_elem.get('href')
        
    except Exception as e:
        logger.debug(f"Error in Yelp extraction: {e}")
    
    return data if (data['phone_numbers'] or data['business_name']) else None


def extract_from_yellowpages(soup):
    """Extract from Yellow Pages"""
    data = _empty_contacts()
    
    try:
        # Business name
        name_elem = soup.find('h1') or soup.find('h2', class_=re.compile('business-name'))
        if name_elem:
            data['business_name'] = name_elem.get_text(strip=True)
        
        # Phone
        phone_link = soup.find('a', class_=re.compile('phone|call'))
        if phone_link:
            phone_text = phone_link.get_text(strip=True)
            formatted = format_phone(phone_text)
            if formatted:
                data['phone_numbers'].append(formatted)
        
        # Address
        street = soup.find(class_=re.compile('street-address'))
        city = soup.find(class_=re.compile('locality'))
        state = soup.find(class_=re.compile('region'))
        zipcode = soup.find(class_=re.compile('postal-code'))
        
        if street:
            data['street_address'] = street.get_text(strip=True)
        if city:
            data['city'] = city.get_text(strip=True)
        if state:
            data['state'] = state.get_text(strip=True)
        if zipcode:
            data['zip_code'] = zipcode.get_text(strip=True)
        
    except Exception as e:
        logger.debug(f"Error in Yellow Pages extraction: {e}")
    
    return data if (data['phone_numbers'] or data['business_name']) else None


def extract_from_foursquare(soup):
    """Extract from Foursquare"""
    data = _empty_contacts()
    
    try:
        # Business name
        name_elem = soup.find('h1', class_=re.compile('venueName'))
        if name_elem:
            data['business_name'] = name_elem.get_text(strip=True)
        
        # Phone
        phone_elem = soup.find('div', class_=re.compile('phone'))
        if phone_elem:
            formatted = format_phone(phone_elem.get_text(strip=True))
            if formatted:
                data['phone_numbers'].append(formatted)
        
        # Address
        address = soup.find('div', class_=re.compile('address'))
        if address:
            data['street_address'] = address.get_text(strip=True)
        
    except Exception as e:
        logger.debug(f"Error in Foursquare extraction: {e}")
    
    return data if (data['phone_numbers'] or data['business_name']) else None


def extract_from_tripadvisor(soup):
    """Extract from TripAdvisor"""
    data = _empty_contacts()
    
    try:
        # Business name
        name_elem = soup.find('h1', attrs={'data-automation': 'mainH1'}) or soup.find('h1')
        if name_elem:
            data['business_name'] = name_elem.get_text(strip=True)
        
        # Phone
        phone_elem = soup.find('a', href=re.compile('tel:')) or soup.find('span', class_=re.compile('phone'))
        if phone_elem:
            phone_text = phone_elem.get('href', '').replace('tel:', '') if phone_elem.get('href') else phone_elem.get_text(strip=True)
            formatted = format_phone(phone_text)
            if formatted:
                data['phone_numbers'].append(formatted)
        
        # Address
        address_elem = soup.find('span', class_=re.compile('address'))
        if address_elem:
            data['street_address'] = address_elem.get_text(strip=True)
        
    except Exception as e:
        logger.debug(f"Error in TripAdvisor extraction: {e}")
    
    return data if (data['phone_numbers'] or data['business_name']) else None


def extract_generic_directory(soup):
    """
    Generic directory extraction using common patterns
    Works for most directory sites
    """
    data = _empty_contacts()
    
    try:
        # Get all text for AI extraction if needed
        page_text = soup.get_text(separator=' ', strip=True)
        
        # Business name - try common patterns
        name_selectors = [
            soup.find('h1'),
            soup.find('h2'),
            soup.find(class_=re.compile('business.*name|company.*name|title', re.I)),
            soup.find(attrs={'itemprop': 'name'})
        ]
        for elem in name_selectors:
            if elem:
                name = elem.get_text(strip=True)
                if name and len(name) < 100:  # Sanity check
                    data['business_name'] = name
                    break
        
        # Phone - try common patterns
        phone_patterns = [
            soup.find('a', href=re.compile('tel:')),
            soup.find(class_=re.compile('phone|contact.*number|tel', re.I)),
            soup.find(attrs={'itemprop': 'telephone'})
        ]
        for elem in phone_patterns:
            if elem:
                phone_text = elem.get('href', '').replace('tel:', '') if elem.get('href') else elem.get_text(strip=True)
                formatted = format_phone(phone_text)
                if formatted and formatted not in data['phone_numbers']:
                    data['phone_numbers'].append(formatted)
        
        # Email - search in links and text
        email_link = soup.find('a', href=re.compile('mailto:'))
        if email_link:
            email = email_link.get('href', '').replace('mailto:', '')
            if is_valid_email(email):
                data['email_addresses'].append(email)
        
        # Regex fallback for phone/email in text
        if not data['phone_numbers']:
            phone_regex = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            phones = re.findall(phone_regex, page_text)
            for phone in phones[:3]:  # Max 3
                formatted = format_phone(phone)
                if formatted and formatted not in data['phone_numbers']:
                    data['phone_numbers'].append(formatted)
        
        if not data['email_addresses']:
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_regex, page_text)
            for email in emails[:2]:  # Max 2
                if is_valid_email(email) and email not in data['email_addresses']:
                    data['email_addresses'].append(email)
        
        # Address - try common patterns
        address_selectors = [
            soup.find(class_=re.compile('address|location', re.I)),
            soup.find(attrs={'itemprop': 'address'})
        ]
        for elem in address_selectors:
            if elem:
                addr = elem.get_text(strip=True)
                if addr and len(addr) < 200:
                    data['street_address'] = addr
                    break
        
        # Website link
        website_link = soup.find('a', class_=re.compile('website|url|link', re.I))
        if website_link:
            href = website_link.get('href', '')
            if href and not href.startswith('#') and 'http' in href:
                data['website'] = href
        
    except Exception as e:
        logger.debug(f"Error in generic directory extraction: {e}")
    
    return data if (data['phone_numbers'] or data['email_addresses'] or data['business_name']) else None


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
        'twitter': None,
        'linkedin': None,
        'business_hours': None,
        'owner_name': None
    }
