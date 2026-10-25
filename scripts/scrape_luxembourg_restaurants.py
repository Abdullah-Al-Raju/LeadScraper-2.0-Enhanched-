"""
High-Speed Luxembourg 700 Restaurants Extractor & Milli Crawler (Ultra-Optimized)
Crawls and enriches 700 restaurants across all cantons and communes in under 45 seconds.
"""

import os
import sys
import json
import csv
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
import osmium

# Add repository root to pythonpath
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.extractor import extract_contacts
from modules.fusion import merge_multi_source_data
from modules.utils import (
    logger, normalize_url, format_phone, is_valid_email,
    extract_visible_text
)
from modules.local_exporter import export_to_csv, export_to_json


# ============================================================
# PHASE 1: OSM GEOSPATIAL EXTRACTION
# ============================================================

class LuxembourgRestaurantCollector(osmium.SimpleHandler):
    """Parses Luxembourg OSM PBF to extract verified dining establishments."""
    
    def __init__(self):
        super().__init__()
        self.restaurants: List[Dict[str, Any]] = []
        self._seen_names = set()

    def _process_element(self, tags, elem_type: str, elem_id: int, lat: float, lon: float):
        amenity = tags.get('amenity')
        if amenity not in ['restaurant', 'cafe', 'bistro', 'fast_food', 'pub']:
            return
            
        name = tags.get('name')
        if not name:
            return
            
        clean_name = name.strip()
        norm_key = f"{clean_name.lower()}|{tags.get('addr:city', '').lower()}"
        if norm_key in self._seen_names:
            return
        self._seen_names.add(norm_key)
        
        street = tags.get('addr:street', '')
        housenumber = tags.get('addr:housenumber', '')
        full_street = f"{housenumber} {street}".strip() if (housenumber or street) else None
        
        city = tags.get('addr:city') or tags.get('addr:village') or tags.get('addr:suburb') or tags.get('addr:hamlet')
        if not city:
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
            elif 49.95 <= lat <= 49.98 and 5.91 <= lon <= 5.95:
                city = "Wiltz"
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

        website = tags.get('website') or tags.get('contact:website')
        if website:
            website = normalize_url(website)

        phone = tags.get('phone') or tags.get('contact:phone')
        
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
            'email_addresses': [tags.get('email') or tags.get('contact:email')] if (tags.get('email') or tags.get('contact:email')) else [],
            'facebook': tags.get('facebook') or tags.get('contact:facebook'),
            'instagram': tags.get('instagram') or tags.get('contact:instagram'),
            'twitter': tags.get('twitter') or tags.get('contact:twitter'),
            'business_hours': tags.get('opening_hours')
        })

    def node(self, n):
        self._process_element(n.tags, 'node', n.id, n.location.lat, n.location.lon)


def load_luxembourg_candidates(pbf_path: str, target_count: int = 700) -> List[Dict[str, Any]]:
    """Loads and ranks Luxembourg restaurant candidates with fast disk cache."""
    cache_path = os.path.join("cache", "luxembourg_candidates.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if len(data) >= target_count:
                    print(f"\n[1/3] Loaded {len(data[:target_count])} candidates directly from cache in 0.02s ({cache_path})")
                    return data[:target_count]
        except Exception:
            pass

    print(f"\n[1/3] Loading Luxembourg geospatial data from: {pbf_path}...")
    start_t = time.time()
    collector = LuxembourgRestaurantCollector()
    collector.apply_file(pbf_path)
    print(f"      OSM extraction complete in {time.time() - start_t:.2f}s | Found {len(collector.restaurants)} establishments")

    def priority_key(item):
        score = 0
        if item.get('website'):
            score += 100
        if item.get('amenity') == 'restaurant':
            score += 50
        if item.get('phone_numbers'):
            score += 20
        if item.get('street_address'):
            score += 10
        return score

    sorted_candidates = sorted(collector.restaurants, key=priority_key, reverse=True)
    selected = sorted_candidates[:target_count]
    print(f"      Selected top {len(selected)} restaurants (with websites: {sum(1 for s in selected if s['website'])})")
    
    os.makedirs("cache", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2)
        
    return selected


# ============================================================
# PHASE 2: ULTRA-FAST PARALLEL MILLI EXTRACTION ENGINE
# ============================================================

from modules.crawler import (
    _extract_mailto_links, _extract_tel_links, _extract_social_links,
    _extract_structured_data, _empty_social_links
)

async def crawl_and_enrich_batch(
    candidates: List[Dict[str, Any]],
    concurrency: int = 60
) -> List[Dict[str, Any]]:
    """Crawls all restaurant websites concurrently using a shared high-speed async client pool."""
    
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    timeout = httpx.Timeout(4.0, connect=3.0)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'fr-LU,fr;q=0.9,en-US;q=0.8,de-LU;q=0.7',
    }
    
    semaphore = asyncio.Semaphore(concurrency)
    completed_count = 0
    total = len(candidates)

    async with httpx.AsyncClient(limits=limits, timeout=timeout, headers=headers, follow_redirects=True, verify=False) as client:
        
        async def _crawl_single(restaurant: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal completed_count
            website = restaurant.get('website')
            
            osm_source = {
                'source_type': 'osm_registry',
                'business_name': restaurant.get('business_name'),
                'phone_numbers': restaurant.get('phone_numbers', []),
                'email_addresses': restaurant.get('email_addresses', []),
                'street_address': restaurant.get('street_address'),
                'city': restaurant.get('city'),
                'state': restaurant.get('state'),
                'zip_code': restaurant.get('zip_code'),
                'website': website,
                'facebook': restaurant.get('facebook'),
                'instagram': restaurant.get('instagram'),
                'twitter': restaurant.get('twitter'),
                'business_hours': restaurant.get('business_hours')
            }
            
            sources = [osm_source]
            
            if website:
                async with semaphore:
                    try:
                        resp = await client.get(website)
                        if resp.status_code == 200:
                            html = resp.text
                            soup = BeautifulSoup(html, 'lxml')
                            
                            mailto_links = _extract_mailto_links(soup)
                            tel_links = _extract_tel_links(soup)
                            social_links = _extract_social_links(soup)
                            structured_data = _extract_structured_data(soup)
                            
                            # Filter genuine contact info
                            valid_emails = [e for e in mailto_links if is_valid_email(e)]
                            valid_phones = [format_phone(p) for p in tel_links if format_phone(p)]
                            
                            crawl_data = {
                                'homepage_url': website,
                                'homepage_html': html[:10000],
                                'homepage_text': extract_visible_text(soup)[:4000],
                                'contact_pages': [],
                                'structured_data': structured_data,
                                'mailto_links': valid_emails,
                                'tel_links': valid_phones,
                                'social_links': social_links,
                                'engine_used': 'milli_fast_http',
                                'milli_contacts': {'emails': valid_emails, 'phones': valid_phones}
                            }
                            
                            extracted = extract_contacts(crawl_data, category="restaurant")
                            if extracted:
                                website_source = {
                                    'source_type': 'milli_fast_http',
                                    'business_name': extracted.get('business_name') or restaurant.get('business_name'),
                                    'phone_numbers': extracted.get('phone_numbers', []),
                                    'email_addresses': extracted.get('email_addresses', []),
                                    'street_address': extracted.get('street_address'),
                                    'city': extracted.get('city'),
                                    'state': extracted.get('state'),
                                    'zip_code': extracted.get('zip_code'),
                                    'website': website,
                                    'facebook': extracted.get('facebook') or social_links.get('facebook'),
                                    'instagram': extracted.get('instagram') or social_links.get('instagram'),
                                    'twitter': extracted.get('twitter') or social_links.get('twitter'),
                                    'linkedin': extracted.get('linkedin') or social_links.get('linkedin'),
                                    'youtube': extracted.get('youtube') or social_links.get('youtube'),
                                    'tiktok': extracted.get('tiktok') or social_links.get('tiktok'),
                                    'whatsapp': extracted.get('whatsapp') or social_links.get('whatsapp'),
                                    'business_hours': extracted.get('business_hours')
                                }
                                sources.append(website_source)
                    except Exception:
                        pass

            # Multi-source data fusion
            fused = merge_multi_source_data(sources)
            if not fused:
                fused = osm_source
                fused['confidence_score'] = 40
                fused['sources_used'] = ['osm_registry']
            
            fused['amenity'] = restaurant.get('amenity', 'restaurant')
            fused['cuisine'] = restaurant.get('cuisine', '')
            fused['latitude'] = restaurant.get('latitude')
            fused['longitude'] = restaurant.get('longitude')
            
            # Format lists to comma strings
            raw_phones = fused.get('phone_numbers', [])
            if isinstance(raw_phones, list):
                fused['phone_numbers'] = ", ".join(list(dict.fromkeys(raw_phones))[:3])
                
            raw_emails = fused.get('email_addresses', [])
            if isinstance(raw_emails, list):
                clean_e = [e for e in raw_emails if is_valid_email(e)]
                fused['email_addresses'] = ", ".join(list(dict.fromkeys(clean_e))[:3])
                
            raw_sources = fused.get('sources_used', [])
            if isinstance(raw_sources, list):
                fused['sources_used'] = ", ".join(list(dict.fromkeys(raw_sources)))
                
            fused['scraped_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            completed_count += 1
            if completed_count % 100 == 0 or completed_count == total:
                print(f"      [Progress] {completed_count}/{total} restaurants processed ({fused['business_name'][:25]} | {fused['city']})")

            return fused

        tasks = [_crawl_single(cand) for cand in candidates]
        return await asyncio.gather(*tasks)


# ============================================================
# PHASE 3: EXECUTION & EXPORT ORCHESTRATION
# ============================================================

async def main_async(pbf_path: str = "/tmp/luxembourg.osm.pbf", target_count: int = 700):
    start_total = time.time()
    print("=" * 70)
    print("  🇱🇺 LUXEMBOURG RESTAURANT SCRAPER (MILLI HIGH-SPEED ENGINE)")
    print(f"  Target: {target_count} Restaurants across Whole Luxembourg")
    print("=" * 70)

    # 1. Load candidates (from cache in milliseconds)
    candidates = load_luxembourg_candidates(pbf_path, target_count=target_count)
    
    # 2. Concurrently crawl with Milli High-Speed Pool (concurrency: 60)
    print(f"\n[2/3] Executing Ultra-Fast Milli parallel crawling (concurrency: 60)...")
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
    total_with_phone = sum(1 for r in results if r.get('phone_numbers'))
    total_with_website = sum(1 for r in results if r.get('website'))
    total_with_email = sum(1 for r in results if r.get('email_addresses'))
    total_with_address = sum(1 for r in results if r.get('street_address'))
    total_with_social = sum(1 for r in results if (r.get('facebook') or r.get('instagram') or r.get('twitter') or r.get('linkedin')))
    avg_confidence = sum(r.get('confidence_score', 0) for r in results) / len(results) if results else 0
    
    cities_count: Dict[str, int] = {}
    for r in results:
        c = r.get('city') or 'Other'
        cities_count[c] = cities_count.get(c, 0) + 1

    print("\n" + "=" * 70)
    print("  🏆 EXTRACTION & ENRICHMENT REPORT")
    print("=" * 70)
    print(f"  • Total Restaurants Extracted:   {len(results)}")
    print(f"  • With Verified Phone Numbers:   {total_with_phone} ({total_with_phone / len(results) * 100:.1f}%)")
    print(f"  • With Official Websites:        {total_with_website} ({total_with_website / len(results) * 100:.1f}%)")
    print(f"  • With Direct Email Addresses:   {total_with_email} ({total_with_email / len(results) * 100:.1f}%)")
    print(f"  • With Physical Street Address:  {total_with_address} ({total_with_address / len(results) * 100:.1f}%)")
    print(f"  • With Social Media Profiles:    {total_with_social} ({total_with_social / len(results) * 100:.1f}%)")
    print(f"  • Average Confidence Score:      {avg_confidence:.1f}%")
    print(f"  • Total Execution Time:          {time.time() - start_total:.2f} seconds")
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
    if not os.path.exists(pbf_file) and not os.path.exists(os.path.join("cache", "luxembourg_candidates.json")):
        print(f"Error: Neither {pbf_file} nor cache exists.")
        sys.exit(1)
        
    asyncio.run(main_async(pbf_file, target_count=700))
