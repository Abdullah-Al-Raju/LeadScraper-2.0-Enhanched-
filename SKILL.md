---
name: lead-scraper-falcon
description: Autonomous business intelligence, lead generation, and contact extraction engine powered natively by Milli-Scrapes. Discovers operating businesses, filters out 40+ directory aggregators, bypasses Cloudflare Turnstile and cookie walls in sub-milliseconds, harvests emails, phones, social handles (Instagram, Facebook, X, LinkedIn, TikTok), and automatically exports to CSV, JSON, and formatted TXT cards.
---

# LeadScraper Falcon Agent Skill

Use this skill whenever an autonomous agent, multi-agent workflow, or user needs to:
1. **Extract leads from a direct website URL** (0 searches, instant Milli crawl).
2. **Find verified contacts for a named business** (1 targeted official website lookup).
3. **Discover operating businesses dynamically** by category and location anywhere in the world.
4. **Auto-dismiss cookie walls & bypass Cloudflare Turnstile** with zero-second stall loops.
5. **Harvest comprehensive social media endpoints** (Instagram, Facebook, X/Twitter, LinkedIn, TikTok, YouTube).
6. **Automatically export leads to JSON, CSV, and TXT** in the `output/` folder.

---

## 1. CLI Command Quick Reference

### Template 1: Direct Website Extraction (0 searches)
```bash
python main.py --url "https://bluebottlecoffee.com"
```

### Template 2: Named Business Search (1 targeted search)
```bash
python main.py --name "Tartine Bakery" --location "San Francisco"
```

### Template 3: Dynamic Category & Location Discovery
```bash
python main.py --category "Dentist" --location "Austin, TX" --quantity 10
```

---

## 2. CLI Flags Reference Table

| Flag | Type | Default | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `--url` | String | `None` | Template 1: Direct website extraction | `--url "https://bluebottlecoffee.com"` |
| `--name` | String | `None` | Template 2: Business name to lookup | `--name "Tartine Bakery"` |
| `--location` | String | `None` | Target location / city / country | `--location "San Francisco"` |
| `--category` | String | `None` | Template 3: Business category or niche | `--category "Coffee Roasters"` |
| `--quantity` | Integer | `10` | Number of leads to extract in discovery | `--quantity 20` |
| `--concurrency` | Integer | `5` | Concurrent worker tasks | `--concurrency 8` |

---

## 3. Python Programmatic API

```python
import asyncio
from lead_scraper import LeadScraper, export_leads

async def main():
    async with LeadScraper() as scraper:
        # Template 1
        lead = await scraper.scrape_website("https://news.ycombinator.com")
        print(lead.display_card())

        # Template 2
        lead2 = await scraper.scrape_named_business("Tartine Bakery", location="San Francisco")
        print(lead2.emails, lead2.phones)

        # Template 3
        leads = await scraper.discover_and_scrape(
            category="Dentist",
            location="Austin, TX",
            quantity=10
        )
        paths = export_leads(leads)
        print("Exported to:", paths)

asyncio.run(main())
```

---

## 4. Automatic Multi-Format Output

Every run writes to `output/`:
- `output/leads_<timestamp>.json` (Structured JSON records)
- `output/leads_<timestamp>.csv` (Tabular spreadsheet UTF-8 with BOM)
- `output/leads_<timestamp>.txt` (Formatted business cards)
