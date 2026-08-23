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
    Extract contact information using multi-tier approach
    
    Args:
        crawl_data: Dictionary from crawler module
        category: Business category/type for context-aware extraction
        
    Returns:
        Dictionary with extracted contact information
    """
    if not crawl_data:
        return None
    
    # Try Tier 1: Structured data (JSON-LD)
    contacts = extract_from_structured_data(crawl_data.get('structured_data', []))
    
    # Try Tier 2: AI extraction (category-aware)
    if not _is_sufficient(contacts):
        logger.info("Attempting category-aware AI extraction...")
        ai_contacts = extract_with_ai_category_aware(
            crawl_data.get('combined_text', ''),
            category=category
        )
        contacts = _merge_contacts(contacts, ai_contacts)
    
    # Try Tier 3: Regex fallback
    if not _is_sufficient(contacts):
        logger.info("Attempting regex extraction...")
        regex_contacts = extract_with_regex(
            crawl_data.get('combined_text', ''),
            crawl_data.get('mailto_links', []),
            crawl_data.get('tel_links', [])
        )
        contacts = _merge_contacts(contacts, regex_contacts)
    
    # Add social links
    social = crawl_data.get('social_links', {})
    if not contacts.get('facebook'):
        contacts['facebook'] = social.get('facebook')
    if not contacts.get('instagram'):
        contacts['instagram'] = social.get('instagram')
    if not contacts.get('twitter'):
        contacts['twitter'] = social.get('twitter')
    if not contacts.get('linkedin'):
        contacts['linkedin'] = social.get('linkedin')
    
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

@retry_on_failure(max_retries=2, exceptions=(requests.exceptions.RequestException,))
def extract_with_ai(text):
    """
    INTELLIGENT AI extraction - AI understands business first, then extracts
    
    Args:
        text: Text to extract from
        
    Returns:
        Dictionary with contact information
    """
    if not text or not config.OPENROUTER_API_KEY:
        return _empty_contacts()
    
    # Truncate text to fit token limits
    text = truncate_text(text, config.MAX_CONTEXT_CHARS)
    
    # NEW: Two-step intelligent extraction
    # Step 1: Understand the business
    # Step 2: Extract based on understanding
    
    system_prompt = """You are an INTELLIGENT business research assistant.

Your task is in TWO PHASES:

PHASE 1 - UNDERSTAND THE BUSINESS:
- What type of business is this?
- What services/products do they offer?
- What is their target audience?
- Are they legit/real?

PHASE 2 - INTELLIGENT EXTRACTION:
Based on your understanding, extract ALL possible contact information.
Be SMART about where to look:
- For restaurants: look for reservation phone, delivery info, location
- For services: look for consultation contact, business hours
- For retail: look for store location, customer service

Extract deeply - look in footer, about us, contact page text patterns.

Return ONLY valid JSON:
{
  "business_understanding": {
    "type": "string (restaurant/cafe/service/retail/etc)",
    "description": "brief description",
    "confidence": "high/medium/low"
  },
  "extracted_data": {
    "business_name": "string or null",
    "phone_numbers": ["string"],
    "email_addresses": ["string"],
    "street_address": "string or null",
    "city": "string or null",
    "state": "string or null",
    "zip_code": "string or null",
    "website": "string or null",
    "facebook": "string or null",
    "instagram": "string or null",
    "twitter": "string or null",
    "linkedin": "string or null",
    "whatsapp": "string or null",
    "business_hours": "string or null",
    "owner_name": "string or null",
    "delivery_platforms": "string or null"
  }
}

CRITICAL RULES:
- Extract EVERYTHING you find, don't limit yourself
- Look for patterns like "Call us:", "Email:", "Visit us at:"
- Find social media handles and URLs
- Extract multiple phones/emails if present
- DO NOT fabricate - only extract what's clearly present
- Be thorough and intelligent"""

    user_prompt = f"""ANALYZE and EXTRACT from this business:

---
{text}
---

First, understand what this business is. Then, intelligently extract ALL contact information you can find."""

    try:
        # Make API request
        response = requests.post(
            config.OPENROUTER_BASE_URL,
            headers={
                'Authorization': f'Bearer {config.OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://github.com/leadscraper',
                'X-Title': 'LeadScraper'
            },
            json={
                'model': config.OPENROUTER_MODEL,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'temperature': 0.3  # Lower temperature for more focused extraction
            },
            timeout=30
        )
        
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Extract JSON from response
        content = content.strip()
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
        
        # Parse JSON
        ai_result = json.loads(content)
        
        # Log AI's understanding
        understanding = ai_result.get('business_understanding', {})
        logger.info(f"🤖 AI Understanding: {understanding.get('type')} - {understanding.get('description')} (Confidence: {understanding.get('confidence')})")
        
        # Get extracted data
        contacts = ai_result.get('extracted_data', {})
        
        # Convert to our format
        formatted = _empty_contacts()
        formatted['business_name'] = contacts.get('business_name')
        formatted['phone_numbers'] = [format_phone(p) for p in contacts.get('phone_numbers', []) if p]
        formatted['email_addresses'] = [e for e in contacts.get('email_addresses', []) if is_valid_email(e)]
        formatted['street_address'] = contacts.get('street_address')
        formatted['city'] = contacts.get('city')
        formatted['state'] = contacts.get('state')
        formatted['zip_code'] = contacts.get('zip_code')
        formatted['website'] = contacts.get('website')
        formatted['facebook'] = contacts.get('facebook')
        formatted['instagram'] = contacts.get('instagram')
        formatted['twitter'] = contacts.get('twitter')
        formatted['linkedin'] = contacts.get('linkedin')
        formatted['whatsapp'] = contacts.get('whatsapp')
        formatted['business_hours'] = contacts.get('business_hours')
        formatted['owner_name'] = contacts.get('owner_name')
        formatted['delivery_platforms'] = contacts.get('delivery_platforms')
        
        logger.info(f"🤖 AI extracted: {len(formatted['phone_numbers'])} phones, {len(formatted['email_addresses'])} emails")
        
        return formatted
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        return _empty_contacts()
    except requests.exceptions.HTTPError as e:
        logger.error(f"OpenRouter API error: {e}")
        raise
    except Exception as e:
        logger.error(f"AI extraction error: {e}")
        return _empty_contacts()


@retry_on_failure(max_retries=2, exceptions=(requests.exceptions.RequestException,))
def extract_with_ai_category_aware(text, category=None):
    """
    Category-aware AI extraction
    AI understands the category context and extracts accordingly
    
    Args:
        text: Text to extract from
        category: Business category for context
        
    Returns:
        Dictionary with contact information
    """
    if not text or not config.OPENROUTER_API_KEY:
        return _empty_contacts()
    
    # If category provided, add category context
    if category:
        logger.info(f"🤖 AI extraction with category context: {category}")
        
        # Build category-specific hints
        category_hints = {
            'restaurant': "Look for: reservation phone, delivery services (UberEats, DoorDash), hours of operation, chef/owner name",
            'cafe': "Look for: phone, hours, Instagram (cafes love Instagram), location for visit",
            'retail': "Look for: customer service phone, store hours, return policy contact",
            'service': "Look for: consultation phone, appointment email, business hours"
        }
        
        category_lower = category.lower()
        hint = category_hints.get(category_lower, f"This is a {category} business")
        
        # Add hint to text
        text = f"[BUSINESS TYPE: {category}]\n{hint}\n\n{text}"
    
    # Use intelligent extraction
    return extract_with_ai(text)

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

CATEGORY_CONTEXT_MAPPING = [
    (
        ['restaurant', 'cafe', 'coffee', 'food', 'dining', 'eatery'],
        """
This is a RESTAURANT/FOOD SERVICE business. Pay special attention to:
- Business hours (especially lunch/dinner times)
- Cuisine type or specialties
- Reservation or delivery contact numbers
- Owner/chef name if mentioned
"""
    ),
    (
        ['dental', 'dentist', 'clinic', 'medical', 'doctor', 'hospital', 'health'],
        """
This is a MEDICAL/DENTAL business. Pay special attention to:
- Doctor/dentist names
- Specialties or services offered
- Appointment phone numbers
- Office hours
- Emergency contact information
"""
    ),
    (
        ['auto', 'repair', 'garage', 'mechanic', 'car', 'vehicle'],
        """
This is an AUTOMOTIVE/REPAIR business. Pay special attention to:
- Service types offered
- Business hours
- Emergency/towing numbers
- Owner or manager name
"""
    ),
    (
        ['shop', 'store', 'retail', 'boutique', 'market'],
        """
This is a RETAIL/SHOP business. Pay special attention to:
- Store hours
- Product categories
- Contact for orders or inquiries
- Owner name
"""
    ),
    (
        ['law', 'attorney', 'accounting', 'consulting', 'agency'],
        """
This is a PROFESSIONAL SERVICES business. Pay special attention to:
- Professional names (lawyers, accountants, consultants)
- Areas of practice/specialization
- Office hours
- Consultation contact information
"""
    )
]


def _get_category_context(category):
    """
    Get category-specific extraction context

    Args:
        category: Business category/type

    Returns:
        Additional context string for AI prompt
    """
    if not category:
        return ""

    category_lower = category.lower()
    
    for keywords, context in CATEGORY_CONTEXT_MAPPING:
        if any(word in category_lower for word in keywords):
            return context

    # Default context
    return f"""
This is a {category} business. Extract all relevant contact information.
"""


@retry_on_failure(max_retries=2, exceptions=(requests.exceptions.RequestException,))
def extract_with_ai_category_aware(text, category=None):
    """
    Extract contacts using OpenRouter AI with category awareness
    
    Args:
        text: Text to extract from
        category: Business category for context
        
    Returns:
        Dictionary with contact information
    """
    if not text or not config.OPENROUTER_API_KEY:
        return _empty_contacts()
    
    # Truncate text to fit token limits
    text = truncate_text(text, config.MAX_CONTEXT_CHARS)
    
    # Get category-specific context
    category_context = _get_category_context(category)
    
    # Prepare enhanced system prompt
    system_prompt = f"""You are an intelligent contact information extractor for business websites.
{category_context}

Extract the following fields from the provided text.
Return ONLY valid JSON, nothing else.

{{
  "business_name": "string or null",
  "phone_numbers": ["string"] or [],
  "email_addresses": ["string"] or [],
  "street_address": "string or null",
  "city": "string or null",
  "state": "string or null",
  "zip_code": "string or null",
  "website": "string or null",
  "facebook": "string or null",
  "instagram": "string or null",
  "twitter": "string or null",
  "linkedin": "string or null",
  "business_hours": "string or null",
  "owner_name": "string or null"
}}

CRITICAL RULES:
- Extract the ACTUAL business name from the website, not the category
- For phone numbers, normalize to format: (XXX) XXX-XXXX
- For emails, only include real emails, not noreply@ or info@ unless clearly legitimate
- If a field is not found, set it to null
- Do NOT guess or fabricate any information
- business_name should be the real name (e.g., "Kacchi Bhai", not "Restaurant")
"""

    user_prompt = f"""Extract contact information from this business website text:

---
{text}
---"""

    try:
        # Make API request
        response = requests.post(
            config.OPENROUTER_BASE_URL,
            headers={
                'Authorization': f'Bearer {config.OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://github.com/leadscraper',
                'X-Title': 'LeadScraper'
            },
            json={
                'model': config.OPENROUTER_MODEL,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ]
            },
            timeout=30
        )
        
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Extract JSON from response (handle markdown code blocks)
        content = content.strip()
        if content.startswith('```'):
            # Remove markdown code block
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
        
        # Parse JSON
        contacts = json.loads(content)
        
        # Convert to our format
        formatted = _empty_contacts()
        formatted['business_name'] = contacts.get('business_name')
        formatted['phone_numbers'] = [format_phone(p) for p in contacts.get('phone_numbers', []) if p]
        formatted['email_addresses'] = [e for e in contacts.get('email_addresses', []) if is_valid_email(e)]
        formatted['street_address'] = contacts.get('street_address')
        formatted['city'] = contacts.get('city')
        formatted['state'] = contacts.get('state')
        formatted['zip_code'] = contacts.get('zip_code')
        formatted['website'] = contacts.get('website')
        formatted['facebook'] = contacts.get('facebook')
        formatted['instagram'] = contacts.get('instagram')
        formatted['twitter'] = contacts.get('twitter')
        formatted['linkedin'] = contacts.get('linkedin')
        formatted['business_hours'] = contacts.get('business_hours')
        formatted['owner_name'] = contacts.get('owner_name')
        
        logger.info(f"Category-aware AI extraction successful: {len(formatted['phone_numbers'])} phones, {len(formatted['email_addresses'])} emails")
        
        return formatted
        
    except json.JSONDecodeError as e:
        logger.warning(f"AI returned invalid JSON: {e}")
        return _empty_contacts()
    except Exception as e:
        logger.error(f"Category-aware AI extraction failed: {e}")
        return _empty_contacts()
