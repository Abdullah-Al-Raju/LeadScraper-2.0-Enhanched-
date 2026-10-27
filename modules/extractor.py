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
    format_phone, retry_on_failure
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
            if is_valid_email(em) and em not in contacts.get('email_addresses', []):
                contacts.setdefault('email_addresses', []).append(em)
        for ph in milli_contacts.get('phones', []):
            formatted_p = format_phone(ph)
            if formatted_p and formatted_p not in contacts.get('phone_numbers', []):
                contacts.setdefault('phone_numbers', []).append(formatted_p)
        for k, v in milli_contacts.get('social_media', {}).items():
            target_k = 'twitter' if k == 'twitter_x' else k
            if v and not contacts.get(target_k):
                contacts[target_k] = v
    
    # Try Tier 2: Regex & Cloudflare XOR Engine
    if not _is_sufficient(contacts):
        regex_contacts = extract_with_regex(
            crawl_data.get('combined_text', ''),
            crawl_data.get('mailto_links', []),
            crawl_data.get('tel_links', [])
        )
        contacts = _merge_contacts(contacts, regex_contacts)
    
    # Add social links
    social = crawl_data.get('social_links', {})
    for platform in ['facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok', 'whatsapp']:
        if not contacts.get(platform) and social.get(platform):
            contacts[platform] = social.get(platform)
    
    # Add website
    if not contacts.get('website'):
        contacts['website'] = crawl_data.get('homepage_url')
    
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
    for pattern in config.PHONE_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                phone = ''.join(match)
            else:
                phone = match
            
            formatted = format_phone(phone)
            if formatted and formatted not in contacts['phone_numbers']:
                contacts['phone_numbers'].append(formatted)
    
    # Add tel: links
    if tel_links:
        for phone in tel_links:
            formatted = format_phone(phone)
            if formatted and formatted not in contacts['phone_numbers']:
                contacts['phone_numbers'].append(formatted)
    
    # Extract emails
    email_matches = re.findall(config.EMAIL_PATTERN, text)
    for email in email_matches:
        if is_valid_email(email) and email not in contacts['email_addresses']:
            contacts['email_addresses'].append(email)
    
    # Add mailto: links
    if mailto_links:
        for email in mailto_links:
            if is_valid_email(email) and email not in contacts['email_addresses']:
                contacts['email_addresses'].append(email)
    
    # Extract social media
    for platform, pattern in config.SOCIAL_PATTERNS.items():
        if not contacts.get(platform):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
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
# CATEGORY-AWARE AI EXTRACTION
# ============================================================


