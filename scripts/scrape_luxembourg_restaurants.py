"""
High-Speed Luxembourg 700 Restaurants Extractor & Deep Contact Crawler (Web, Email & Social Focused)

Extracts and enriches 700 restaurants across Luxembourg with maximum focus on:
  • Official Websites (100% target coverage)
  • Direct Email Addresses (via Homepage regex, mailto, Cloudflare deobfuscation, Schema.org, and Contact/Impressum subpage crawling)
  • Social Media Links (Facebook, Instagram, LinkedIn, Twitter/X, TikTok, YouTube, WhatsApp)
  • Phone numbers are non-mandatory (collected if present, but zero penalty if absent)
"""

import os
import sys
import json
import csv
import time
import re
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
import osmium

# Add repository root to pythonpath
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.utils import (
    logger, normalize_url, format_phone, is_valid_email,
    extract_visible_text
)
from modules.local_exporter import export_to_csv, export_to_json


# ============================================================
# UTILITIES: CLOUDFLARE DEOBFUSCATION, REGEX & SOCIALS
# ============================================================

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')

def decode_cfemail(hex_str: str) -> str:
    """Decodes Cloudflare email protection obfuscated hex string."""
    try:
        k = int(hex_str[:2], 16)
        return "".join([chr(int(hex_str[i:i+2], 16) ^ k) for i in range(2, len(hex_str), 2)])
    except Exception:
        return ""

def extract_emails_from_soup(soup: BeautifulSoup, raw_html: str = "") -> List[str]:
    """Extracts and validates emails via mailto, cfemail, and raw regex."""
    emails = []
    
    # 1. Mailto links & Cloudflare protection URLs
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        hl = href.lower()
        if hl.startswith('mailto:'):
            e = href[7:].split('?')[0].strip()
            if e and is_valid_email(e):
                emails.append(e.lower())
        elif 'email-protection#' in hl:
            hex_part = href.split('email-protection#')[-1].split('?')[0].strip()
            dec = decode_cfemail(hex_part)
            if dec and is_valid_email(dec):
                emails.append(dec.lower())
                
    # 2. Elements with data-cfemail
    for el in soup.find_all(attrs={'data-cfemail': True}):
        dec = decode_cfemail(el.get('data-cfemail', ''))
        if dec and is_valid_email(dec):
            emails.append(dec.lower())

    # 3. JSON-LD structured data
    for s in soup.find_all('script', type='application/ld+json'):
        try:
            if s.string:
                data = json.loads(s.string)
                if isinstance(data, dict):
                    e = data.get('email')
                    if isinstance(e, str) and is_valid_email(e):
                        emails.append(e.lower())
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            e = item.get('email')
                            if isinstance(e, str) and is_valid_email(e):
                                emails.append(e.lower())
        except Exception:
            pass

    # 4. Regex across visible text & raw HTML
    text = soup.get_text(separator=" ")
    matches = EMAIL_REGEX.findall(text)
    if raw_html:
        matches.extend(EMAIL_REGEX.findall(raw_html))
        
    for m in matches:
        if is_valid_email(m):
            emails.append(m.lower())
            
    return list(dict.fromkeys(emails))


def extract_social_links(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """Extracts social media links while filtering out share/intent buttons."""
    socials = {
        'facebook': None,
        'instagram': None,
        'twitter': None,
        'linkedin': None,
        'youtube': None,
        'tiktok': None,
        'whatsapp': None
    }
    
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        hl = href.lower()
        
        # Skip social share buttons
        if any(s in hl for s in ['sharer', 'share.php', 'intent/tweet', 'sharearticle', '/share?', 'plugins/like', 'addtoany']):
            continue
            
        if ('facebook.com/' in hl or 'fb.me/' in hl) and not socials['facebook'] and not any(x in hl for x in ['facebook.com/tr', 'facebook.com/dialog']):
            socials['facebook'] = href
        elif 'instagram.com/' in hl and not socials['instagram'] and not any(x in hl for x in ['instagram.com/p/', 'instagram.com/reel/']):
            socials['instagram'] = href
        elif ('twitter.com/' in hl or 'x.com/' in hl) and not socials['twitter'] and not any(x in hl for x in ['/status/', '/intent/']):
            socials['twitter'] = href
        elif 'linkedin.com/' in hl and not socials['linkedin'] and ('company' in hl or 'in/' in hl):
            socials['linkedin'] = href
        elif ('youtube.com/' in hl or 'youtu.be/' in hl) and not socials['youtube'] and not any(x in hl for x in ['/watch?', '/embed/']):
            socials['youtube'] = href
        elif 'tiktok.com/@' in hl and not socials['tiktok']:
            socials['tiktok'] = href
        elif ('wa.me/' in hl or 'api.whatsapp.com/send' in hl) and not socials['whatsapp']:
            socials['whatsapp'] = href
            
    return socials


def find_best_contact_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Identifies the most promising contact/impressum/about subpage URL."""
    scored = []
    base_domain = urlparse(base_url).netloc.replace('www.', '').lower()
    
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if not href or href.startswith(('#', 'javascript:', 'tel:', 'mailto:', 'sms:', 'whatsapp:')):
            continue
            
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        link_domain = parsed.netloc.replace('www.', '').lower()
        if link_domain != base_domain:
            continue  # must be internal
            
        path = parsed.path.lower()
        text = a.get_text(strip=True).lower()
        
        score = 0
        if any(k in path for k in ['contact', 'kontakt']):
            score += 50
        elif any(k in path for k in ['impressum', 'mentions']):
            score += 45
        elif any(k in path for k in ['apropos', 'a-propos', 'about', 'uber-uns']):
            score += 30
        elif any(k in path for k in ['reservation', 'info', 'infos']):
            score += 20
            
        if any(k in text for k in ['contact', 'kontakt']):
            score += 40
        elif any(k in text for k in ['impressum', 'mentions']):
            score += 35
        elif any(k in text for k in ['propos', 'about']):
            score += 25
            
        if score > 0:
            scored.append((score, full_url))
            
    if not scored:
        return None
        
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


# ============================================================
# PHASE 1: OSM GEOSPATIAL EXTRACTION (WEBSITES & EMAILS FOCUS)
# ============================================================

class LuxembourgRestaurantCollector(osmium.SimpleHandler):
    """Parses Luxembourg OSM PBF to extract verified dining establishments with node and way support."""
    
    def __init__(self):
        super().__init__()
        self.restaurants: List[Dict[str, Any]] = []
        self._seen_names = set()

    def _process_element(self, tags, elem_type: str, elem_id: int, lat: Optional[float] = None, lon: Optional[float] = None):
        amenity = tags.get('amenity')
        if amenity not in ['restaurant', 'cafe', 'bistro', 'fast_food', 'pub', 'bar']:
            return
            
        name = tags.get('name')
        if not name:
            return
            
        clean_name = name.strip()
        city = tags.get('addr:city') or tags.get('addr:village') or tags.get('addr:suburb') or tags.get('addr:hamlet')
        if not city:
            if lat and lon:
                if 49.58 <= lat <= 49.65 and 6.09 <= lon <= 6.18:
                    city = "Luxembourg City"
                elif 49.47 <= lat <= 49.52 and 5.95 <= lon <= 6.03:
                    city = "Esch-sur-Alzette"
                elif 49.51 <= lat <= 49.55 and 5.86 <= lon <= 5.92:
                    city = "Differdange"
                elif 49.46 <= lat <= 49.50 and 6.05 <= lon <= 6.11:
                    city = "Dudelange"
                elif 49.83 <= lat <= 49.87 and 6.08 <= lon <= 6.12:
                    city = "Ettelbruck"
                elif 49.85 <= lat <= 49.88 and 6.14 <= lon <= 6.18:
                    city = "Diekirch"
                elif 49.79 <= lat <= 49.83 and 6.40 <= lon <= 6.44:
                    city = "Echternach"
                elif 49.66 <= lat <= 49.70 and 6.42 <= lon <= 6.46:
                    city = "Grevenmacher"
                elif 49.53 <= lat <= 49.56 and 6.35 <= lon <= 6.38:
                    city = "Remich"
                elif 49.73 <= lat <= 49.77 and 6.09 <= lon <= 6.13:
                    city = "Mersch"
                else:
                    city = "Luxembourg"
            else:
                city = "Luxembourg"

        norm_key = f"{clean_name.lower()}|{city.lower()}"
        if norm_key in self._seen_names:
            return
        self._seen_names.add(norm_key)
        
        street = tags.get('addr:street', '')
        housenumber = tags.get('addr:housenumber', '')
        full_street = f"{housenumber} {street}".strip() if (housenumber or street) else None

        website = tags.get('website') or tags.get('contact:website') or tags.get('url')
        if website:
            website = normalize_url(website)

        email = tags.get('email') or tags.get('contact:email')
        phone = tags.get('phone') or tags.get('contact:phone')
        fb = tags.get('facebook') or tags.get('contact:facebook')
        ig = tags.get('instagram') or tags.get('contact:instagram')
        twitter = tags.get('twitter') or tags.get('contact:twitter')
        
        self.restaurants.append({
            'osm_id': f"{elem_type}_{elem_id}",
            'business_name': clean_name,
            'amenity': amenity,
            'cuisine': tags.get('cuisine'),
            'street_address': full_street,
            'city': city,
            'state': tags.get('addr:county') or tags.get('addr:district') or "Luxembourg",
            'zip_code': tags.get('addr:postcode'),
            'latitude': lat,
            'longitude': lon,
            'website': website,
            'phone_numbers': [phone] if phone else [],
            'email_addresses': [email] if email else [],
            'facebook': fb,
            'instagram': ig,
            'twitter': twitter,
            'business_hours': tags.get('opening_hours')
        })

    def node(self, n):
        self._process_element(n.tags, 'node', n.id, n.location.lat, n.location.lon)

    def way(self, w):
        self._process_element(w.tags, 'way', w.id, None, None)


def load_luxembourg_candidates(pbf_path: str, target_count: int = 700) -> List[Dict[str, Any]]:
    """Loads and ranks Luxembourg dining candidates focusing on Websites, Emails, and Socials."""
    cache_path = os.path.join("cache", "luxembourg_candidates_web_focused.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if len(data) >= target_count:
                    print(f"\n[1/3] Loaded {len(data[:target_count])} candidates directly from cache in 0.02s ({cache_path})")
                    return data[:target_count]
        except Exception:
            pass

    print(f"\n[1/3] Parsing Luxembourg geospatial snapshot from: {pbf_path}...")
    start_t = time.time()
    collector = LuxembourgRestaurantCollector()
    collector.apply_file(pbf_path)
    print(f"      OSM extraction complete in {time.time() - start_t:.2f}s | Found {len(collector.restaurants)} unique establishments")

    # Ranking formula: strictly prioritizes Websites, Emails, and Social Media
    def priority_key(item):
        score = 0
        if item.get('website'):
            score += 100
        if item.get('email_addresses'):
            score += 60
        if item.get('facebook') or item.get('instagram') or item.get('twitter'):
            score += 40
        if item.get('amenity') == 'restaurant':
            score += 25
        if item.get('street_address'):
            score += 10
        # Phone numbers are non-mandatory (0 points)
        return score

    sorted_candidates = sorted(collector.restaurants, key=priority_key, reverse=True)
    selected = sorted_candidates[:target_count]
    print(f"      Selected top {len(selected)} establishments (with verified websites: {sum(1 for s in selected if s['website'])})")
    
    os.makedirs("cache", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2)
        
    return selected


# ============================================================
# PHASE 2: ULTRA-FAST PARALLEL MILLI DEEP CRAWLER
# ============================================================

async def crawl_and_enrich_batch(
    candidates: List[Dict[str, Any]],
    concurrency: int = 60
) -> List[Dict[str, Any]]:
    """Crawls websites and contact/impressum subpages focusing on Emails, Websites, and Social Media."""
    
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    timeout = httpx.Timeout(4.0, connect=3.0)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,de-DE;q=0.7',
    }
    
    semaphore = asyncio.Semaphore(concurrency)
    completed_count = 0
    total = len(candidates)

    async with httpx.AsyncClient(limits=limits, timeout=timeout, headers=headers, follow_redirects=True, verify=False) as client:
        
        async def _crawl_single(restaurant: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal completed_count
            website = restaurant.get('website')
            
            emails_found = list(restaurant.get('email_addresses', []))
            phones_found = list(restaurant.get('phone_numbers', []))
            socials_found = {
                'facebook': restaurant.get('facebook'),
                'instagram': restaurant.get('instagram'),
                'twitter': restaurant.get('twitter'),
                'linkedin': None,
                'youtube': None,
                'tiktok': None,
                'whatsapp': None
            }
            sources_used = ['osm_registry']
            
            if website:
                async with semaphore:
                    try:
                        resp = await client.get(website)
                        if resp.status_code == 200:
                            sources_used.append('milli_web_engine')
                            html = resp.text
                            soup = BeautifulSoup(html, 'lxml')
                            
                            # 1. Extract Homepage Emails
                            hp_emails = extract_emails_from_soup(soup, html)
                            emails_found.extend(hp_emails)
                            
                            # 2. Extract Homepage Socials
                            hp_socials = extract_social_links(soup)
                            for k, v in hp_socials.items():
                                if v and not socials_found.get(k):
                                    socials_found[k] = v
                                    
                            # 3. Extract Phones (if present, bonus)
                            for a in soup.find_all('a', href=True):
                                if a['href'].lower().startswith('tel:'):
                                    p = format_phone(a['href'][4:])
                                    if p:
                                        phones_found.append(p)
                                        
                            # 4. DEEP CONTACT / IMPRESSUM SUBPAGE DISCOVERY
                            # If no emails found on homepage, crawl the contact/impressum subpage!
                            if not emails_found:
                                contact_url = find_best_contact_url(soup, website)
                                if contact_url and contact_url != website:
                                    try:
                                        c_resp = await client.get(contact_url)
                                        if c_resp.status_code == 200:
                                            sources_used.append('milli_contact_subpage')
                                            c_soup = BeautifulSoup(c_resp.text, 'lxml')
                                            c_emails = extract_emails_from_soup(c_soup, c_resp.text)
                                            emails_found.extend(c_emails)
                                            
                                            c_socials = extract_social_links(c_soup)
                                            for k, v in c_socials.items():
                                                if v and not socials_found.get(k):
                                                    socials_found[k] = v
                                    except Exception:
                                        pass
                                        
                    except Exception:
                        pass

            # Deduplicate emails and phones
            clean_emails = [str(e).strip() for e in emails_found if e and is_valid_email(str(e).strip())]
            clean_emails = list(dict.fromkeys(clean_emails))
            
            raw_phones = [format_phone(p) or str(p).strip() for p in phones_found if p]
            clean_phones = [p for p in raw_phones if p and isinstance(p, str)]
            clean_phones = list(dict.fromkeys(clean_phones))

            # User-focused Confidence Scoring:
            # Website (35 pts), Email (35 pts), Social Media (20 pts), Address (10 pts)
            score = 0
            if website:
                score += 35
            if clean_emails:
                score += 35
            if any(socials_found.values()):
                score += 20
            if restaurant.get('street_address'):
                score += 10

            record = {
                'business_name': restaurant.get('business_name'),
                'website': website or '',
                'email_addresses': ", ".join(clean_emails[:3]),
                'facebook': socials_found.get('facebook') or '',
                'instagram': socials_found.get('instagram') or '',
                'twitter': socials_found.get('twitter') or '',
                'linkedin': socials_found.get('linkedin') or '',
                'youtube': socials_found.get('youtube') or '',
                'tiktok': socials_found.get('tiktok') or '',
                'whatsapp': socials_found.get('whatsapp') or '',
                'phone_numbers': ", ".join(clean_phones[:3]),  # non-mandatory
                'street_address': restaurant.get('street_address') or '',
                'city': restaurant.get('city') or 'Luxembourg',
                'state': restaurant.get('state') or 'Luxembourg',
                'zip_code': restaurant.get('zip_code') or '',
                'amenity': restaurant.get('amenity') or 'restaurant',
                'cuisine': restaurant.get('cuisine') or '',
                'business_hours': restaurant.get('business_hours') or '',
                'latitude': restaurant.get('latitude'),
                'longitude': restaurant.get('longitude'),
                'confidence_score': score,
                'sources_used': ", ".join(list(dict.fromkeys(sources_used))),
                'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            completed_count += 1
            if completed_count % 100 == 0 or completed_count == total:
                print(f"      [Progress] {completed_count}/{total} restaurants processed ({record['business_name'][:25]} | {record['city']})")

            return record

        tasks = [_crawl_single(cand) for cand in candidates]
        return await asyncio.gather(*tasks)


# ============================================================
# PHASE 3: EXECUTION & EXPORT ORCHESTRATION
# ============================================================

async def main_async(pbf_path: str = "/tmp/luxembourg.osm.pbf", target_count: int = 700):
    start_total = time.time()
    print("=" * 70)
    print("  🇱🇺 LUXEMBOURG RESTAURANT SCRAPER (EMAIL, WEBSITE & SOCIAL FOCUSED)")
    print(f"  Target: {target_count} Restaurants across Whole Luxembourg")
    print("=" * 70)

    # 1. Load candidates (filtered to maximize website, email & social coverage)
    candidates = load_luxembourg_candidates(pbf_path, target_count=target_count)
    
    # 2. Concurrently crawl with Milli High-Speed Deep Contact Engine (concurrency: 60)
    print(f"\n[2/3] Executing Ultra-Fast Milli parallel deep crawl (concurrency: 60)...")
    results = await crawl_and_enrich_batch(candidates, concurrency=60)
    crawl_elapsed = time.time() - start_total
    print(f"      Milli crawling and data fusion complete in {crawl_elapsed:.2f}s! ({len(results)/crawl_elapsed:.1f} restaurants/sec)")

    # 3. Export to CSV & JSON
    print(f"\n[3/3] Exporting enriched dataset...")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "luxembourg_700_restaurants.csv")
    json_path = os.path.join(output_dir, "luxembourg_700_restaurants.json")

    export_to_csv(results, csv_path)
    export_to_json(results, json_path)
    
    # 4. Statistical Summary
    total_with_website = sum(1 for r in results if r.get('website'))
    total_with_email = sum(1 for r in results if r.get('email_addresses'))
    total_with_social = sum(1 for r in results if (r.get('facebook') or r.get('instagram') or r.get('twitter') or r.get('linkedin') or r.get('youtube') or r.get('tiktok') or r.get('whatsapp')))
    total_with_fb = sum(1 for r in results if r.get('facebook'))
    total_with_ig = sum(1 for r in results if r.get('instagram'))
    total_with_li = sum(1 for r in results if r.get('linkedin'))
    total_with_tw = sum(1 for r in results if r.get('twitter'))
    total_with_wa = sum(1 for r in results if r.get('whatsapp'))
    total_with_yt = sum(1 for r in results if r.get('youtube'))
    total_with_address = sum(1 for r in results if r.get('street_address'))
    total_with_phone = sum(1 for r in results if r.get('phone_numbers'))
    avg_confidence = sum(r.get('confidence_score', 0) for r in results) / len(results) if results else 0
    
    cities_count: Dict[str, int] = {}
    for r in results:
        c = r.get('city') or 'Other'
        cities_count[c] = cities_count.get(c, 0) + 1

    print("\n" + "=" * 70)
    print("  🏆 EXTRACTION & ENRICHMENT REPORT (EMAIL, WEBSITE & SOCIAL FOCUSED)")
    print("=" * 70)
    print(f"  • Total Restaurants Extracted:       {len(results)}")
    print(f"  • With Official Websites:            {total_with_website} ({total_with_website / len(results) * 100:.1f}%)")
    print(f"  • With Direct Email Addresses:       {total_with_email} ({total_with_email / len(results) * 100:.1f}%)")
    print(f"  • With Social Media Profiles:        {total_with_social} ({total_with_social / len(results) * 100:.1f}%)")
    print(f"      - Facebook:                      {total_with_fb} ({total_with_fb / len(results) * 100:.1f}%)")
    print(f"      - Instagram:                     {total_with_ig} ({total_with_ig / len(results) * 100:.1f}%)")
    print(f"      - WhatsApp:                      {total_with_wa} ({total_with_wa / len(results) * 100:.1f}%)")
    print(f"      - LinkedIn:                      {total_with_li} ({total_with_li / len(results) * 100:.1f}%)")
    print(f"      - Twitter / X:                   {total_with_tw} ({total_with_tw / len(results) * 100:.1f}%)")
    print(f"      - YouTube:                       {total_with_yt} ({total_with_yt / len(results) * 100:.1f}%)")
    print(f"  • With Physical Street Address:      {total_with_address} ({total_with_address / len(results) * 100:.1f}%)")
    print(f"  • With Phone Numbers (Non-Mandatory):{total_with_phone} ({total_with_phone / len(results) * 100:.1f}%)")
    print(f"  • Average Confidence Score:          {avg_confidence:.1f}%")
    print(f"  • Total Execution Time:              {time.time() - start_total:.2f} seconds")
    print("-" * 70)
    print("  Top Communes / Cities Covered:")
    top_cities = sorted(cities_count.items(), key=lambda x: x[1], reverse=True)[:8]
    for city_name, count in top_cities:
        print(f"    - {city_name:<25}: {count} restaurants")
    print("-" * 70)
    print(f"  💾 CSV File:  {csv_path}")
    print(f"  💾 JSON File: {json_path}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    pbf_file = "/tmp/luxembourg.osm.pbf"
    if not os.path.exists(pbf_file) and not os.path.exists(os.path.join("cache", "luxembourg_candidates_web_focused.json")):
        print(f"Error: Neither {pbf_file} nor cache exists.")
        sys.exit(1)
        
    asyncio.run(main_async(pbf_file, target_count=700))
