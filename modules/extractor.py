"""
Contact Information Extraction Module
Multi-tier extraction: JSON-LD → AI → Regex
"""

import re
import json
import requests
import config
from modules.utils import (
    logger, truncate_text, is_valid_email,
    format_phone, is_valid_social_url, retry_on_failure
)


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

def extract_contacts(crawl_data, category=None):
    """
    Extract contact information using multi-tier deterministic approach:
    Tier 0: Milli Direct Discoveries & Social Media
    Tier 1: Structured data (JSON-LD Schema.org)
    Tier 2: High-speed Regex & Cloudflare XOR Deobfuscation Engine
    """
    if not crawl_data:
        return None
    
    # Try Tier 1: Structured data (JSON-LD)
    contacts = extract_from_structured_data(crawl_data.get('structured_data', []))
    
    # Merge direct Milli discovered contacts
    milli_contacts = crawl_data.get('milli_contacts', {})
    if milli_contacts:
        for em in milli_contacts.get('emails', []):
            clean_em = em.lower().strip().rstrip('.,;:!?)>"\'')
            if is_valid_email(clean_em) and clean_em not in [e.lower() for e in contacts.get('email_addresses', [])]:
                contacts.setdefault('email_addresses', []).append(clean_em)
        for ph in milli_contacts.get('phones', []):
            formatted_p = format_phone(ph)
            if formatted_p:
                combined = crawl_data.get('combined_text', '')
                if combined and len(combined) > 100:
                    digits = re.sub(r'\D', '', formatted_p)
                    combined_digits = re.sub(r'\D', '', combined)
                    if digits[-10:] not in combined_digits and formatted_p not in combined:
                        continue
                if formatted_p not in contacts.get('phone_numbers', []):
                    contacts.setdefault('phone_numbers', []).append(formatted_p)
        for k, v in milli_contacts.get('social_media', {}).items():
            target_k = 'twitter' if k == 'twitter_x' else k
            if v and is_valid_social_url(v) and not contacts.get(target_k):
                contacts[target_k] = v
    
    # Try Tier 2: Regex & Cloudflare XOR Engine
    if not _is_sufficient(contacts):
        regex_contacts = extract_with_regex(
            crawl_data.get('combined_text', ''),
            crawl_data.get('mailto_links', []),
            crawl_data.get('tel_links', [])
        )
        contacts = _merge_contacts(contacts, regex_contacts)
        
    # Extract address from text if not found in structured data
    if not contacts.get('street_address'):
        from modules.sources.search_result_extractor import _extract_addresses
        _extract_addresses(crawl_data.get('combined_text', ''), contacts)
    
    # Try Tier 3 (Optional): OpenRouter Free Auto-Router
    if not _is_sufficient(contacts) and getattr(config, 'ENABLE_AI_FALLBACK', True):
        try:
            from modules.ai_manager import ai_manager
            if ai_manager.is_available():
                logger.info("Contacts sparse after deterministic parsing. Querying OpenRouter free router...")
                ai_contacts = ai_manager.extract_contacts_with_ai_sync(
                    crawl_data.get('combined_text', ''),
                    category=category
                )
                if ai_contacts:
                    contacts = _merge_contacts(contacts, ai_contacts)
        except Exception as e:
            logger.debug(f"Optional AI extraction tier error: {e}")
    
    # Add social links
    social = crawl_data.get('social_links', {})
    for platform in ['facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok', 'whatsapp']:
        val = social.get(platform)
        if not contacts.get(platform) and val and is_valid_social_url(val):
            contacts[platform] = val
    
    # Add website
    if not contacts.get('website'):
        contacts['website'] = crawl_data.get('homepage_url')
        
    # Resolve business_name if still missing
    if not contacts.get('business_name'):
        title = crawl_data.get('title') or ""
        if title:
            parts = re.split(r'\s+[-–—]\s+|\s*[|:•]\s*', title)
            clean_name = parts[0].strip() if parts else title.strip()
            if len(clean_name) >= 2 and len(clean_name) <= 50:
                contacts['business_name'] = clean_name
    if not contacts.get('business_name') and contacts.get('website'):
        from urllib.parse import urlparse
        domain = urlparse(contacts['website']).netloc.replace('www.', '').split('.')[0]
        if domain:
            contacts['business_name'] = domain.replace('-', ' ').title()
    
    return contacts


# ============================================================
# TIER 1: STRUCTURED DATA EXTRACTION
# ============================================================

def extract_from_structured_data(structured_data_list):
    """
    Extract contacts from JSON-LD structured data
    
    Args:
        structured_data_list: List of structured data dictionaries
        
    Returns:
        Dictionary with contact information
    """
    contacts = _empty_contacts()
    
    if not structured_data_list:
        return contacts
    
    logger.info("Extracting from structured data (JSON-LD)...")
    
    for data in structured_data_list:
        # Handle both single objects and arrays
        if isinstance(data, list):
            items = data
        else:
            items = [data]
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            # Extract based on @type
            item_type = item.get('@type', '')
            
            if item_type in ['LocalBusiness', 'Organization', 'Restaurant', 'Store']:
                # Business name
                if not contacts['business_name'] and item.get('name'):
                    contacts['business_name'] = item['name']
                
                # Phone
                if item.get('telephone'):
                    phone = format_phone(item['telephone'])
                    if phone and phone not in contacts['phone_numbers']:
                        contacts['phone_numbers'].append(phone)
                
                # Email
                if item.get('email'):
                    email = item['email']
                    if is_valid_email(email) and email not in contacts['email_addresses']:
                        contacts['email_addresses'].append(email)
                
                # Address
                address = item.get('address')
                if address and isinstance(address, dict):
                    if not contacts['street_address'] and address.get('streetAddress'):
                        contacts['street_address'] = address['streetAddress']
                    if not contacts['city'] and address.get('addressLocality'):
                        contacts['city'] = address['addressLocality']
                    if not contacts['state'] and address.get('addressRegion'):
                        contacts['state'] = address['addressRegion']
                    if not contacts['zip_code'] and address.get('postalCode'):
                        contacts['zip_code'] = address['postalCode']
                
                # Opening hours
                if not contacts['business_hours'] and item.get('openingHours'):
                    hours = item['openingHours']
                    if isinstance(hours, list):
                        contacts['business_hours'] = ', '.join(hours)
                    else:
                        contacts['business_hours'] = str(hours)
    
    if contacts['phone_numbers'] or contacts['email_addresses']:
        logger.info(f"Extracted from structured data: {len(contacts['phone_numbers'])} phones, {len(contacts['email_addresses'])} emails")
    
    return contacts


# ============================================================
# TIER 2: INTELLIGENT AI EXTRACTION
# ============================================================

def extract_with_ai(text):
    """Deprecated: Deterministic high-speed regex & DOM extractor used instead."""
    return _empty_contacts()


def extract_with_ai_category_aware(text, category=None):
    """Deprecated: Deterministic high-speed regex & DOM extractor used instead."""
    return _empty_contacts()

# TIER 3: REGEX EXTRACTION
# ============================================================

def extract_with_regex(text, mailto_links=None, tel_links=None):
    """
    Extract contacts using regex patterns
    
    Args:
        text: Text to extract from
        mailto_links: Pre-extracted mailto links
        tel_links: Pre-extracted tel links
        
    Returns:
        Dictionary with contact information
    """
    if not text:
        return _empty_contacts()
    
    logger.info("Performing regex extraction...")
    
    contacts = _empty_contacts()
    
    # Extract phone numbers
    max_phones = getattr(config, 'MAX_PHONES_PER_BUSINESS', 5)
    max_emails = getattr(config, 'MAX_EMAILS_PER_BUSINESS', 5)

    for pattern in config.PHONE_PATTERNS:
        matches = re.finditer(pattern, text)
        for match in matches:
            if len(contacts['phone_numbers']) >= max_phones:
                break
            phone = match.group(0)
            formatted = format_phone(phone)
            if formatted and formatted not in contacts['phone_numbers']:
                contacts['phone_numbers'].append(formatted)
    
    # Add tel: links
    if tel_links:
        for phone in tel_links:
            if len(contacts['phone_numbers']) >= max_phones:
                break
            formatted = format_phone(phone)
            if formatted and formatted not in contacts['phone_numbers']:
                contacts['phone_numbers'].append(formatted)
    
    # Extract emails
    email_matches = re.finditer(config.EMAIL_PATTERN, text)
    for match in email_matches:
        if len(contacts['email_addresses']) >= max_emails:
            break
        email = match.group(0).lower().strip().rstrip('.,;:!?)>"\'')
        email = re.sub(r'(phone(?:number)?|tel|email|address|contact|website|hours|mon|tue|wed|thu|fri|sat|sun)$', '', email, flags=re.IGNORECASE).rstrip('.,;:!?)>"\'')
        if is_valid_email(email) and email not in [e.lower() for e in contacts['email_addresses']]:
            contacts['email_addresses'].append(email)
    
    # Add mailto: links
    if mailto_links:
        for email in mailto_links:
            if len(contacts['email_addresses']) >= max_emails:
                break
            clean_email = email.lower().strip().rstrip('.,;:!?)>"\'')
            clean_email = re.sub(r'(phone(?:number)?|tel|email|address|contact|website|hours|mon|tue|wed|thu|fri|sat|sun)$', '', clean_email, flags=re.IGNORECASE).rstrip('.,;:!?)>"\'')
            if is_valid_email(clean_email) and clean_email not in [e.lower() for e in contacts['email_addresses']]:
                contacts['email_addresses'].append(clean_email)
    
    # Extract social media
    for platform, pattern in config.SOCIAL_PATTERNS.items():
        if not contacts.get(platform):
            match = re.search(pattern, text, re.IGNORECASE)
            if match and is_valid_social_url(match.group(0)):
                contacts[platform] = match.group(0)
    
    logger.info(f"Regex extraction: {len(contacts['phone_numbers'])} phones, {len(contacts['email_addresses'])} emails")
    
    return contacts


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
        'youtube': None,
        'tiktok': None,
        'whatsapp': None,
        'business_hours': None,
        'owner_name': None
    }


def _merge_contacts(contacts1, contacts2):
    """
    Merge two contact dictionaries, preferring non-empty values
    
    Args:
        contacts1: First contacts dict (higher priority)
        contacts2: Second contacts dict
        
    Returns:
        Merged contacts dictionary
    """
    merged = _empty_contacts()
    
    for key in merged.keys():
        val1 = contacts1.get(key)
        val2 = contacts2.get(key)
        
        # Handle lists (phone_numbers, email_addresses)
        if isinstance(merged[key], list):
            merged[key] = list(set((val1 or []) + (val2 or [])))
        # Handle strings
        else:
            merged[key] = val1 or val2
    
    return merged


def _is_sufficient(contacts):
    """
    Check if contacts have sufficient information
    
    Args:
        contacts: Contacts dictionary
        
    Returns:
        Boolean indicating if sufficient
    """
    if not contacts:
        return False
    
    # Consider sufficient if we have at least phone or email
    has_phone = bool(contacts.get('phone_numbers'))
    has_email = bool(contacts.get('email_addresses'))
    
    return has_phone or has_email


# ============================================================
# CATEGORY-AWARE AI EXTRACTION (OPTIONAL)
# ============================================================

def extract_with_ai(text: str, category: str = "") -> dict:
    """
    Extract contacts using OpenRouter AI free auto-router if configured,
    or return empty contacts dict if API key is not present.
    """
    try:
        from modules.ai_manager import ai_manager
        if ai_manager.is_available():
            return ai_manager.extract_contacts_with_ai_sync(text, category=category)
    except Exception as e:
        logger.debug(f"AI extraction helper failed: {e}")
    return _empty_contacts()


def extract_with_ai_category_aware(text: str, category: str = "") -> dict:
    """Category-aware wrapper for AI extraction."""
    return extract_with_ai(text, category=category)



