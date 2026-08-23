"""
Data Fusion Module
Merges and verifies data from multiple sources
"""

import config
from modules.utils import logger


# ============================================================
# CONSTANTS
# ============================================================

FUSION_FIELDS = ('business_name', 'street_address', 'city', 'state', 'zip_code', 'website', 'facebook', 'instagram', 'business_hours')
VERIFIED_SINGLE_FIELDS = ('business_name', 'street_address', 'city', 'state', 'zip_code', 'website')
IMPORTANT_COMPLETENESS_FIELDS = ('business_name', 'phone_numbers', 'email_addresses', 'street_address', 'website')

# ============================================================
# MAIN FUSION FUNCTION
# ============================================================

def merge_multi_source_data(sources_data):
    """
    Merge data from multiple sources into single comprehensive profile
    
    Args:
        sources_data: List of data dictionaries from different sources
            Example: [
                {'source_type': 'facebook', 'business_name': 'Pizza Hut', 'phone_numbers': ['123']},
                {'source_type': 'website', 'business_name': 'Pizza Hut Gulshan', 'phone_numbers': ['123', '456']},
            ]
    
    Returns:
        Merged dictionary with confidence score and source tracking
    """
    if not sources_data:
        return None
    
    # Filter out None/empty sources
    valid_sources = [s for s in sources_data if s and (s.get('business_name') or s.get('phone_numbers') or s.get('email_addresses'))]
    
    if not valid_sources:
        return None
    
    logger.info(f"Merging data from {len(valid_sources)} sources")
    
    # Initialize merged data
    merged = _empty_contacts()
    merged['sources_used'] = []
    merged['source_urls'] = {}
    
    # Track field occurrences for confidence calculation
    field_sources = {
        'business_name': [],
        'phone_numbers': {},
        'email_addresses': {},
        'street_address': [],
        'city': [],
        'state': [],
        'zip_code': [],
        'website': [],
        'facebook': [],
        'instagram': [],
        'business_hours': []
    }
    
    # Collect all data
    for source_data in valid_sources:
        source_type = source_data.get('source_type', 'unknown')
        merged['sources_used'].append(source_type)
        
        # Store source URLs
        if source_data.get('facebook_url'):
            merged['source_urls']['facebook'] = source_data['facebook_url']
        if source_data.get('instagram_url'):
            merged['source_urls']['instagram'] = source_data['instagram_url']
        if source_data.get('directory_url'):
            merged['source_urls']['directory'] = source_data['directory_url']
        if source_data.get('website'):
            merged['source_urls']['website'] = source_data['website']
        
        # Collect field data
        for field in FUSION_FIELDS:
            value = source_data.get(field)
            if value:
                field_sources[field].append((value, source_type))
        
        # Collect lists (phone, email)
        for phone in source_data.get('phone_numbers', []):
            if phone not in field_sources['phone_numbers']:
                field_sources['phone_numbers'][phone] = []
            field_sources['phone_numbers'][phone].append(source_type)
        
        for email in source_data.get('email_addresses', []):
            if email not in field_sources['email_addresses']:
                field_sources['email_addresses'][email] = []
            field_sources['email_addresses'][email].append(source_type)
    
    # Merge fields with conflict resolution
    merged['business_name'] = _resolve_single_field(field_sources['business_name'])
    merged['street_address'] = _resolve_single_field(field_sources['street_address'])
    merged['city'] = _resolve_single_field(field_sources['city'])
    merged['state'] = _resolve_single_field(field_sources['state'])
    merged['zip_code'] = _resolve_single_field(field_sources['zip_code'])
    merged['website'] = _resolve_single_field(field_sources['website'])
    merged['facebook'] = _resolve_single_field(field_sources['facebook']) or merged['source_urls'].get('facebook')
    merged['instagram'] = _resolve_single_field(field_sources['instagram']) or merged['source_urls'].get('instagram')
    merged['business_hours'] = _resolve_single_field(field_sources['business_hours'])
    
    # Merge lists (prioritize most common)
    merged['phone_numbers'] = _resolve_list_field(field_sources['phone_numbers'])
    merged['email_addresses'] = _resolve_list_field(field_sources['email_addresses'])
    
    # Calculate confidence score
    merged['confidence_score'] = calculate_confidence_score(merged, field_sources)
    
    # Determine verified fields (appear in 2+ sources)
    merged['verified_fields'] = _get_verified_fields(field_sources)
    
    logger.info(f"Merged profile: {merged['business_name']} - Confidence: {merged['confidence_score']}% - {len(merged['sources_used'])} sources")
    
    return merged


# ============================================================
# CONFLICT RESOLUTION
# ============================================================

def _resolve_single_field(field_data):
    """
    Resolve conflicts for single-value fields
    
    Args:
        field_data: List of tuples [(value, source_type), ...]
        
    Returns:
        Best value based on source priority and consistency
    """
    if not field_data:
        return None
    
    # If all sources agree, return that value
    unique_values = list(set([v[0] for v in field_data]))
    if len(unique_values) == 1:
        return unique_values[0]
    
    # If conflict, prioritize by source type
    source_priority = getattr(config, 'SOURCE_PRIORITY', {
        'website': 10,
        'facebook': 9,
        'instagram': 7,
        'directory': 5
    })
    
    # Sort by priority
    sorted_data = sorted(field_data, key=lambda x: source_priority.get(x[1].replace('directory:', '').split(':')[0], 0), reverse=True)
    
    # Return highest priority value
    return sorted_data[0][0] if sorted_data else None


def _resolve_list_field(field_dict):
    """
    Resolve conflicts for list fields (phone, email)
    
    Args:
        field_dict: Dictionary {value: [source1, source2, ...]}
        
    Returns:
        List of values sorted by number of confirming sources
    """
    if not field_dict:
        return []
    
    # Sort by number of sources confirming each value
    sorted_items = sorted(field_dict.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Return all values (most confirmed first)
    return [item[0] for item in sorted_items]


# ============================================================
# CONFIDENCE SCORING
# ============================================================

def calculate_confidence_score(merged_data, field_sources):
    """
    Calculate confidence score (0-100) based on:
    - Number of sources
    - Field verification (multiple sources confirm)
    - Data completeness
    
    Args:
        merged_data: Merged contact data
        field_sources: Field occurrence tracking
        
    Returns:
        Confidence score 0-100
    """
    score = 0
    
    # Base score from number of sources (max 30 points)
    num_sources = len(merged_data.get('sources_used', []))
    source_score = min(num_sources * 10, 30)
    score += source_score
    
    # Score from cross-verification (max 40 points)
    verification_score = 0
    
    # Phone verification (important)
    phone_dict = field_sources.get('phone_numbers', {})
    if phone_dict:
        max_phone_sources = max(len(sources) for sources in phone_dict.values())
        if max_phone_sources >= 3:
            verification_score += 15
        elif max_phone_sources == 2:
            verification_score += 10
        elif max_phone_sources == 1:
            verification_score += 5
    
    # Email verification
    email_dict = field_sources.get('email_addresses', {})
    if email_dict:
        max_email_sources = max(len(sources) for sources in email_dict.values())
        if max_email_sources >= 3:
            verification_score += 15
        elif max_email_sources == 2:
            verification_score += 10
        elif max_email_sources == 1:
            verification_score += 5
    
    # Address verification
    address_sources = field_sources.get('street_address', [])
    if len(address_sources) >= 2:
        verification_score += 10
    elif len(address_sources) == 1:
        verification_score += 5
    
    score += min(verification_score, 40)
    
    # Score from data completeness (max 30 points)
    completeness_score = 0
    
    for field in IMPORTANT_COMPLETENESS_FIELDS:
        value = merged_data.get(field)
        if value:
            if isinstance(value, list):
                if len(value) > 0:
                    completeness_score += 6
            else:
                completeness_score += 6
    
    score += min(completeness_score, 30)
    
    # Cap at 100
    return min(score, 100)


def _get_verified_fields(field_sources):
    """
    Get list of verified fields (confirmed by 2+ sources)
    
    Args:
        field_sources: Field occurrence tracking
        
    Returns:
        List of verified field names
    """
    verified = []
    
    # Check single fields
    for field in VERIFIED_SINGLE_FIELDS:
        if len(field_sources.get(field, [])) >= 2:
            verified.append(field)
    
    # Check list fields
    phone_dict = field_sources.get('phone_numbers', {})
    if any(len(sources) >= 2 for sources in phone_dict.values()):
        verified.append('phone')
    
    email_dict = field_sources.get('email_addresses', {})
    if any(len(sources) >= 2 for sources in email_dict.values()):
        verified.append('email')
    
    return verified


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
        'owner_name': None,
        'confidence_score': 0,
        'sources_used': [],
        'source_urls': {},
        'verified_fields': []
    }
