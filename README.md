# LeadScraper Falcon

An autonomous, high-speed business lead collection engine powered natively by the **Milli Universal Engine**.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue.svg)](#quick-start)
[![Engine](https://img.shields.io/badge/Engine-Milli--Scrapes-00c853.svg)](https://github.com/Abdullah-Al-Raju/milli-scrapes)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Abdullah-Al-Raju/lead-scraper-falcon/blob/main/notebooks/LeadScraper_Falcon_Quickstart.ipynb)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Overview

**LeadScraper Falcon** is a lean, deterministic lead generation pipeline. It eliminates brute-force search cascades and multi-search waterfalls in favor of a pure **Milli-First architecture**:

- **Milli Core Engine:** Sub-millisecond V8 cookie consent auto-dismissal, Cloudflare Turnstile bypass, and deep contact extraction (emails, phones, social handles, and physical addresses).
- **5-Tier Ground-Truth Verifier:** Cloudflare XOR email deobfuscation, subpage contact traversal, Schema.org JSON-LD social handle mining, and DNS MX/DMARC routing validation.
- **Zero Hallucination / Synthetic Policy:** Eliminates synthetic guesses (`info@domain` or fabricated vanity URLs). Only verifiably present contact vectors are collected.
- **Zero Search Waste:** Direct URLs require 0 searches. Named businesses require exactly 1 targeted site lookup. Dynamic discovery queries domain links directly without crawling thousands of search pages.
- **Non-Technical Wizard:** A guided 3-template menu that anyone can run without typing terminal arguments or code.
- **Automatic 3-Format Export:** Every run automatically outputs structured `.json`, `.csv`, and formatted `.txt` cards to the `output/` folder and displays the exact paths.

---

## The 3 Operating Templates

| Template | Mode | Search Overhead | Description |
|---|---|---|---|
| **1. Direct Website** | `--url <URL>` | **0 searches** | Instant crawl of a specific target website URL. |
| **2. Named Business** | `--name <NAME>` | **1 targeted search** | Resolves the official business site, then crawls verified contact channels. |
| **3. Dynamic Discovery** | `--category <CAT>` | **Targeted batch** | Finds operating businesses by category and location; crawls in parallel. |

---

## Quick Start

### ☁️ Try Directly in Google Colab (Zero Local Setup)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Abdullah-Al-Raju/lead-scraper-falcon/blob/main/notebooks/LeadScraper_Falcon_Quickstart.ipynb)

Open and run [`notebooks/LeadScraper_Falcon_Quickstart.ipynb`](notebooks/LeadScraper_Falcon_Quickstart.ipynb) directly in your browser.

---

### 🚀 1-Click Launchers (Non-Technical Users)

Clone the repository and launch the interactive wizard with a single click:

- **Windows:** Double-click `run.bat` (or run `run.bat` in Command Prompt)
- **Linux / macOS:** Run `./run.sh` in terminal:
  ```bash
  chmod +x run.sh && ./run.sh
  ```

*The launcher checks Python, creates a virtual environment, installs dependencies, and opens the wizard automatically.*

---

### CLI Usage (Automation & Power Users)

```bash
# 1. Direct website URL extraction (0 searches)
python main.py --url "https://bluebottlecoffee.com"

# 2. Named business lookup (1 targeted search)
python main.py --name "Tartine Bakery" --location "San Francisco"

# 3. Dynamic category & location discovery (default concurrency: 25 workers)
python main.py --category "Dentist" --location "Austin, TX" --quantity 50

# 4. Built-in high-speed benchmark (evaluate N leads)
python main.py --benchmark 50

# Adjust concurrent worker threads (default: 25)
python main.py --category "Bakery" --location "Paris" --quantity 100 --concurrency 50
```

---

## Python Programmatic API

```python
import asyncio
from lead_scraper import LeadScraper, export_leads

async def main():
    async with LeadScraper() as scraper:
        # Template 1: Direct website
        lead = await scraper.scrape_website("https://news.ycombinator.com")
        print(lead.display_card())

        # Template 2: Named business
        lead2 = await scraper.scrape_named_business("Tartine Bakery", location="San Francisco")
        print(lead2.emails, lead2.phones)

        # Template 3: Dynamic discovery
        leads = await scraper.discover_and_scrape(
            category="Coffee Roasters",
            location="Seattle",
            quantity=5
        )
        
        # Save to JSON, CSV, and TXT
        paths = export_leads(leads)
        print("Exported to:", paths)

asyncio.run(main())
```

---

## Automatic Multi-Format Export

Every extraction automatically generates 3 files in the `output/` directory:

```
output/
├── leads_20261027_101500.json    # Complete structured JSON records
├── leads_20261027_101500.csv     # Flat spreadsheet CSV (UTF-8 with BOM for Excel)
└── leads_20261027_101500.txt     # Human-readable business cards
```

---

## 5-Tier Ground-Truth Verification Cascade

Unlike traditional scrapers that inject speculative fallbacks (such as guessing `info@domain.com` or fabricating vanity social URLs), LeadScraper Falcon employs a strict **5-Tier Verification Cascade** (`lead_scraper/lead_verifier.py`) to extract only authentic, working contacts:

1. **Tier 1: Cloudflare Email XOR Deobfuscation (`cdn-cgi/email-protection`)**
   Automatically recovers email addresses masked by Cloudflare's hexadecimal XOR protection at sub-millisecond speeds.
2. **Tier 2: Deep Subpage Contact Traversal**
   When the landing page lacks contacts, the engine automatically traverses `/contact`, `/about`, `/contact-us`, `/team`, and `/reach-us` within the same domain to discover dedicated contact channels.
3. **Tier 3: Schema.org JSON-LD `sameAs` Entity Mining**
   Parses structured semantic graphs in HTML `<script type="application/ld+json">` tags to extract official, verified brand profiles across **Instagram, Facebook, X (Twitter), LinkedIn, TikTok, and YouTube**.
4. **Tier 4: DNS MX & DMARC Validation**
   Queries authoritative DNS servers asynchronously to verify that the domain has active mail exchanger (MX) records and published DMARC policies.
5. **Tier 5: Strict Zero-Hallucination Policy**
   Never emits synthetic or guessed emails. If a business only publishes an Instagram account and a website contact form, Falcon captures precisely that without fabricating non-existent emails.

---

## Architecture & Project Structure

```
lead-scraper-falcon/
├── lead_scraper/                   # Clean modular package
│   ├── __init__.py                 # Public package exports
│   ├── config.py                   # Aggregator blacklists, timeouts, paths
│   ├── models.py                   # Pydantic Lead model & confidence scoring
│   ├── search.py                   # Multi-backend zero-stall search engine
│   ├── discovery.py                # Dynamic entity & website discovery
│   ├── lead_verifier.py            # 5-tier ground-truth verifier & subpage harvester
│   ├── core.py                     # LeadScraper engine powered by milli_scrapes
│   ├── exporter.py                 # Multi-format auto-exporter (JSON, CSV, TXT)
│   └── ui.py                       # Interactive terminal wizard & rich tables
├── main.py                         # Single unified entrypoint
├── run.sh                          # Linux/macOS 1-click launcher
├── run.bat                         # Windows 1-click launcher
├── notebooks/
│   └── LeadScraper_Falcon_Quickstart.ipynb # Google Colab notebook
├── tests/                          # Comprehensive pytest test suite
│   ├── test_models.py
│   ├── test_search.py
│   ├── test_discovery.py
│   ├── test_core.py
│   └── test_exporter.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Verification & Testing

Run the automated test suite:

```bash
pytest tests/ -v
```

---

## License

This project is licensed under the [MIT License](LICENSE).
