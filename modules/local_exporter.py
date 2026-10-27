"""
Local Exporter Module
Exports scraped lead results to CSV, JSON, and terminal displays.
Enables running LeadScraper Falcon standalone without Google Cloud dependencies.
"""

import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Any
from modules.utils import logger


LEAD_FIELDNAMES = [
    "business_name",
    "phone_numbers",
    "email_addresses",
    "street_address",
    "city",
    "state",
    "zip_code",
    "website",
    "facebook",
    "instagram",
    "twitter",
    "linkedin",
    "youtube",
    "tiktok",
    "whatsapp",
    "directory_url",
    "business_hours",
    "owner_name",
    "confidence_score",
    "sources_used",
    "scraped_at"
]


def format_lead_row(contacts: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a contacts dictionary into a standardized lead row."""
    source_urls = contacts.get('source_urls', {})
    
    phones = contacts.get('phone_numbers', [])
    if isinstance(phones, list):
        phone_str = ', '.join([str(p) for p in phones if p])
    else:
        phone_str = str(phones or '')
        
    emails = contacts.get('email_addresses', [])
    if isinstance(emails, list):
        email_str = ', '.join([str(e) for e in emails if e])
    else:
        email_str = str(emails or '')
        
    sources = contacts.get('sources_used', [])
    if isinstance(sources, list):
        source_str = ', '.join([str(s) for s in sources if s])
    else:
        source_str = str(sources or '')
        
    return {
        "business_name": contacts.get('business_name', ''),
        "phone_numbers": phone_str,
        "email_addresses": email_str,
        "street_address": contacts.get('street_address', ''),
        "city": contacts.get('city', ''),
        "state": contacts.get('state', ''),
        "zip_code": contacts.get('zip_code', ''),
        "website": contacts.get('website', '') or source_urls.get('website', ''),
        "facebook": contacts.get('facebook', '') or source_urls.get('facebook', ''),
        "instagram": contacts.get('instagram', '') or source_urls.get('instagram', ''),
        "twitter": contacts.get('twitter', ''),
        "linkedin": contacts.get('linkedin', ''),
        "youtube": contacts.get('youtube', ''),
        "tiktok": contacts.get('tiktok', ''),
        "whatsapp": contacts.get('whatsapp', ''),
        "directory_url": source_urls.get('directory', ''),
        "business_hours": contacts.get('business_hours', ''),
        "owner_name": contacts.get('owner_name', ''),
        "confidence_score": contacts.get('confidence_score', 0),
        "sources_used": source_str,
        "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def export_to_csv(leads: List[Dict[str, Any]], filepath: str) -> str:
    """Exports a list of lead dictionaries to a CSV file."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    rows = [format_lead_row(lead) for lead in leads]
    
    file_exists = os.path.exists(filepath)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=LEAD_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
        
    logger.info(f"Successfully exported {len(rows)} leads to CSV: {filepath}")
    return filepath


def export_to_json(leads: List[Dict[str, Any]], filepath: str) -> str:
    """Exports a list of lead dictionaries to a JSON file."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    rows = [format_lead_row(lead) for lead in leads]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Successfully exported {len(rows)} leads to JSON: {filepath}")
    return filepath


def print_lead_summary(lead: Dict[str, Any]):
    """Pretty prints lead details to the console."""
    row = format_lead_row(lead)
    print("\n" + "=" * 65)
    print(f"  🏢 BUSINESS: {row['business_name'] or 'Unknown'}")
    print("=" * 65)
    if row['website']:
        print(f"  🌐 Website:    {row['website']}")
    if row['phone_numbers']:
        print(f"  📞 Phone:      {row['phone_numbers']}")
    if row['email_addresses']:
        print(f"  ✉️  Email:      {row['email_addresses']}")
    if row['street_address'] or row['city']:
        print(f"  📍 Location:   {row['street_address']} {row['city']} {row['state']}")
    
    socials = []
    if row['facebook']: socials.append(f"FB: {row['facebook']}")
    if row['instagram']: socials.append(f"IG: {row['instagram']}")
    if row['linkedin']: socials.append(f"LI: {row['linkedin']}")
    if row['twitter']: socials.append(f"X: {row['twitter']}")
    if socials:
        print(f"  📱 Socials:    {' | '.join(socials)}")
        
    print(f"  🎯 Confidence: {row['confidence_score']}% | Sources: {row['sources_used']}")
    print("-" * 65)
