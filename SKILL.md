---
name: leadscraper-enhanced
description: Autonomous business intelligence, lead generation, and contact extraction engine. Discovers operating businesses, filters out 40+ directory aggregators, deobfuscates Cloudflare protected emails, deep-crawls European Impressum subpages, harvests social media endpoints (Instagram, Facebook, X, LinkedIn, TikTok), and fuses multi-source data with Bayesian confidence scoring at $0.00 compute cost.
---

# LeadScraper 2.0 Enhanced Agent Skill

Use this skill whenever an autonomous agent, multi-agent workflow, or user needs to:
1. **Find and verify businesses** in any city, country, or industry niche (e.g. coffee shops in Austin, dental clinics in London, fine dining in Tokyo).
2. **Scrape official business websites** and bypass Cloudflare Turnstile, anti-bot gates, and cookie consent banners.
3. **Deobfuscate scrambled emails** protected by Cloudflare `data-cfemail` or `/cdn-cgi/l/email-protection#...` without human intervention.
4. **Discover hidden European emails** legally published on `/contact`, `/kontakt`, `/impressum`, or `/mentions-legales` subpages.
5. **Harvest social media endpoints** (Instagram, Facebook, X/Twitter, LinkedIn, TikTok, YouTube, WhatsApp).
6. **Fuse multi-source records** with automated Bayesian-weighted confidence scoring (0–100%) and export to clean CSV/JSON or stream into Google Sheets.

---

## 1. CLI Command Quick Reference

### Direct Website Scraping & Contact Extraction
```bash
python main.py --url "https://kaempff-kohler.lu" --local --output output/single_lead.json
```

### Business Name Search & Enrichment
```bash
python main.py --business "Philz Coffee" --city "San Francisco" --category "coffee" --local --output output/coffee.csv
```

### Geographic Discovery & Lead Generation
```bash
python main.py --discover "Austin, TX" --quantity 25 --category "coffee" --local --output output/austin_coffee.csv
```

### Google Sheets Cloud Pipeline Mode
```bash
python main.py --discover "SoHo, New York" --quantity 50 --category "boutique"
```

### Force Fallback HTTPX (Disable Milli Engine)
```bash
python main.py --url "https://example.com" --no-milli --local --output output/lead.json
```

---

## 2. CLI Flags Reference Table

| Flag | Type | Default | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `--url` | String | `None` | Direct URL mode: scrape and extract contacts from a single site | `--url "https://kaempff-kohler.lu"` |
| `--business` | String | `None` | Search for a specific business by name | `--business "Tartine Bakery"` |
| `--city` | String | `None` | Geographic city hint for `--business` search | `--city "San Francisco"` |
| `--discover` | String | `None` | Target city/region to discover businesses | `--discover "Melbourne, Australia"` |
| `--category` | String | `""` | Business category or niche filter | `--category "restaurants"` |
| `--quantity` | Integer | `10` | Number of businesses to discover and extract | `--quantity 50` |
| `--local` | Flag | `False` | Run in 100% standalone mode ($0 cost, no Sheets required) | `--local` |
| `--output` | String | `None` | Destination filepath (`.csv` or `.json`) | `--output output/leads.csv` |
| `--no-milli` | Flag | `False` | Disable Milli V8 engine and use fallback HTTPX | `--no-milli` |

---

## 3. Python API Integration

### Direct Single Website Extraction
```python
import asyncio
from modules.crawler import crawl_website
from modules.extractor import extract_contacts

async def get_lead_from_website(url: str) -> dict:
    # Deep crawl homepage and contact/impressum subpages with Milli V8 engine
    crawl_data = await crawl_website(url, force_milli=True)
    if not crawl_data:
        return {"error": "Crawl failed"}
    
    # Extract contacts (Cloudflare deobfuscation + regex + JSON-LD + social media)
    contacts = extract_contacts(crawl_data)
    return contacts

# Run
data = asyncio.run(get_lead_from_website("https://kaempff-kohler.lu"))
print(data["email_addresses"])
print(data["instagram"])
```

### Multi-Source Data Fusion & Confidence Scoring
```python
from modules.fusion import fuse_lead_sources

sources = {
    "website": {
        "business_name": "Philz Coffee",
        "email_addresses": ["info@philzcoffee.com"],
        "phone_numbers": ["(415) 875-9943"],
        "instagram": "https://instagram.com/philzcoffee",
        "facebook": "https://facebook.com/philzcoffee"
    },
    "search_snippets": {
        "business_name": "Philz Coffee",
        "street_address": "3101 24th St",
        "city": "San Francisco",
        "state_region": "CA"
    }
}

fused_record = fuse_lead_sources(sources)
print(f"Confidence Score: {fused_record['confidence_score']}%")
```

---

## 4. Environment Configuration (`.env`)

For **100% Local Mode (`--local`)**, no API keys or environment variables are required!

For **Google Sheets & AI Discovery Mode**, configure `.env`:
```env
# Optional: OpenRouter key for rotating free open-weights AI models
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional: Google Cloud Service Account for Sheets integration
GOOGLE_SHEET_ID=your-google-sheet-id-from-url
SERVICE_ACCOUNT_FILE=credentials/service_account.json
```

---

## 5. Output Data Schema

When saving to JSON, each lead object adheres to:

```json
{
  "business_name": "Restaurant Name",
  "category": "Cuisine or Industry",
  "website": "https://official-website.com",
  "email_addresses": ["contact@domain.com"],
  "phone_numbers": ["+1 555-123-4567"],
  "street_address": "123 Main Street",
  "city": "City Name",
  "state_region": "State / Canton",
  "postal_code": "ZIP / Postal Code",
  "country": "Country Name",
  "social_media": {
    "instagram": "https://instagram.com/handle",
    "facebook": "https://facebook.com/handle",
    "twitter": "https://x.com/handle",
    "linkedin": "https://linkedin.com/company/handle",
    "tiktok": null,
    "youtube": null,
    "whatsapp": null
  },
  "confidence_score": 85.0,
  "sources_corroborated": ["official_website", "json_ld_schema", "search_snippets"]
}
```
