# LeadScraper Falcon

An autonomous business discovery, anti-bot web scraping, and contact intelligence pipeline powered by the Milli Universal Engine.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue.svg)](#quick-start)
[![Engine](https://img.shields.io/badge/Engine-Milli%20Universal-00c853.svg)](https://github.com/Abdullah-Al-Raju/milli-scrapes)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Overview

**LeadScraper Falcon** is a high-throughput, deterministic lead generation and business intelligence pipeline. It automates the process of discovering operational businesses, resolving their official websites, and extracting verified contact information—including direct emails, phone numbers, physical addresses, and social media endpoints.

The pipeline integrates the **Milli Universal Engine**, combining fast-path asynchronous HTTP/2 connection pooling with headless browser rendering for dynamic JavaScript Single Page Applications (SPAs). It features in-memory V8 microtask interception for sub-millisecond cookie consent dismissal, native Cloudflare Turnstile handling, deterministic Cloudflare XOR email decoding (`data-cfemail`), and an adaptive per-domain host pacer to prevent rate-limit blocks.

---

## Key Features

- **Zero-Code Interactive Wizard**: Launch via 1-click scripts (`run.bat` on Windows, `run.sh` on Linux/macOS) with guided numbered templates for non-technical users.
- **Dynamic Business Discovery**: Search operating businesses by location and category using heuristic search matrices and regional geospatial topology while filtering out 40+ directory aggregators (Yelp, TripAdvisor, YellowPages).
- **Deep Contact Extraction**: Automatically extracts verified emails, phone numbers, street addresses, and social endpoints (Facebook, Instagram, LinkedIn, Twitter/X, TikTok, YouTube, WhatsApp).
- **Impressum & Subpage Deep Crawler**: Traverses internal subpages (`/contact`, `/kontakt`, `/impressum`, `/mentions-legales`, `/about`) to recover legally mandated contact information.
- **Cloudflare XOR Deobfuscation**: Decodes `<span data-cfemail="...">` and `/cdn-cgi/l/email-protection#...` scrambled emails deterministically in sub-millisecond execution.
- **Adaptive Polite Host Pacer**: Enforces per-domain token buckets (50ms–200ms) with exponential backoff on HTTP 429 errors while running concurrent requests across different hosts at full speed.
- **Multi-Source Data Fusion**: Corroborates fields across up to 5 concurrent sources (website, search snippets, Schema.org JSON-LD, social metadata) and computes a 0–100% Bayesian confidence score.
- **Automatic Multi-Format Export**: Automatically saves every run simultaneously to `.csv`, `.json`, and `.txt` in the `output/` directory, with optional real-time streaming to Google Sheets.

---

## Quick Start

### 1-Click Launchers

Clone the repository and launch immediately using the included platform scripts:

```bash
git clone https://github.com/Abdullah-Al-Raju/lead-scraper-falcon.git
cd lead-scraper-falcon
```

- **Windows**: Double-click `run.bat` or run in Command Prompt:
  ```cmd
  run.bat
  ```
- **Linux / macOS**: Run `run.sh` in terminal:
  ```bash
  chmod +x run.sh && ./run.sh
  ```

*The launcher script verifies Python 3.8+, creates and activates a virtual environment, installs dependencies from `requirements.txt` (including the integrated Milli Engine), and launches the interactive wizard.*

### Manual Installation

```bash
# Clone repository
git clone https://github.com/Abdullah-Al-Raju/lead-scraper-falcon.git
cd lead-scraper-falcon

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch interactive menu
python main.py
```

---

## Interactive Wizard Modes

Running `python main.py` with no arguments opens the interactive template menu:

```text
=================================================================
  🦅 LEADSCRAPER FALCON - ZERO-CODE INTERACTIVE WIZARD
  Powered by Milli Universal Engine
=================================================================

Choose an extraction template:
  [1] Direct Website Extraction   (Scrape & enrich a specific website URL)
  [2] Named Business Search       (Find & enrich a business by its name)
  [3] Dynamic Discovery           (Find multiple businesses by location & category)
  [q] Exit
```

1. **Option 1 (Direct Website Extraction)**: Scrapes a provided URL directly, deobfuscating emails, crawling contact subpages, and extracting social profiles.
2. **Option 2 (Named Business Search)**: Takes a business name and optional city, discovers the official website, filters directory aggregator links, and enriches the lead.
3. **Option 3 (Dynamic Discovery)**: Takes a location, business category, and target lead quantity, discovering and enriching multiple businesses in parallel.

### Output Files

Every run automatically writes results to all three standard formats in the `output/` folder:

| Format | Path | Purpose |
| :--- | :--- | :--- |
| **CSV** | `output/leads_<timestamp>.csv` | Ready for Microsoft Excel, Google Sheets, and CRM import |
| **JSON** | `output/leads_<timestamp>.json` | Structured JSON with full source provenance and confidence scores |
| **TXT** | `output/leads_<timestamp>.txt` | Human-readable lead report summary |

---

## Command-Line Interface (CLI)

For automated environments, CI/CD, or batch scripts, LeadScraper Falcon supports direct CLI arguments:

```bash
# Direct website extraction
python main.py --url "https://example.com" --local

# Named business search
python main.py --business "Philz Coffee" --city "San Francisco" --local

# Dynamic discovery mode
python main.py --discover "Austin, TX" --category "coffee shop" --quantity 10 --local
```

### CLI Arguments Reference

| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--discover` | string | `None` | Target geographic location to discover businesses |
| `--category` | string | `None` | Business category or niche filter |
| `--quantity` | integer | `10` | Number of businesses to extract |
| `--business` | string | `None` | Direct business search by name |
| `--city` | string | `None` | City hint for direct business search |
| `--url` | string | `None` | Direct URL mode: scrape a single website |
| `--local` | flag | `False` | Run in standalone mode without Google Sheets sync |
| `--output` | string | `None` | Custom export filepath (`.csv`, `.json`, or `.txt`) |
| `--no-milli` | flag | `False` | Disable the Milli engine and fall back to standard HTTPX |
| `--ai` | flag | `False` | Enable optional AI extraction fallback (requires `OPENROUTER_API_KEY`) |

---

## Google Sheets Integration (Optional)

To stream leads directly into a shared Google Sheet:

1. Enable the **Google Sheets API** and **Google Drive API** in Google Cloud Console.
2. Create a Service Account, generate a JSON key, and save it as `credentials/service_account.json`.
3. Share your target Google Sheet with the service account's `client_email`.
4. Copy `.env.example` to `.env` and set:
   ```env
   GOOGLE_SHEET_ID=your-google-sheet-id
   SERVICE_ACCOUNT_FILE=credentials/service_account.json
   ```
5. Run commands without `--local`:
   ```bash
   python main.py --discover "SoHo, New York" --category "boutique" --quantity 25
   ```

---

## Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        LeadScraper Falcon Pipeline                     │
├────────────────────────────────────────────────────────────────────────┤
│  [1] Discovery Engine     Multi-engine search & OSM geospatial data    │
│  [2] Aggregator Filter    Strips 40+ directory domains (Yelp, TripAdv) │
│  [3] Milli Universal      Dual-path SIMD HTTP/2 & CDP browser rendering│
│  [4] Anti-Bot Interceptor Sub-1ms V8 cookie consent & Turnstile solver │
│  [5] Contact Extractor    Cloudflare XOR deobfuscator & Impressum crawl│
│  [6] Social Sniper        Extracts FB, IG, LinkedIn, X, TikTok, YT, WA │
│  [7] Data Fusion          Bayesian confidence scoring (0–100%)         │
│  [8] Multi-Export         Simultaneous CSV, JSON, TXT & Google Sheets  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Benchmarks & Sample Datasets

- **10,000 Leads Benchmark**: Benchmark report evaluating 10,000 production leads across 50 industries. See [`BENCHMARK_10000_LEADS_REPORT.md`](BENCHMARK_10000_LEADS_REPORT.md).
- **Global 10,000 Restaurants Dataset**: Extraction across Australia, USA, Luxembourg, UAE, and Japan. See [`output/10000_RESTAURANTS_LEADS_REPORT.md`](output/10000_RESTAURANTS_LEADS_REPORT.md).
- **Luxembourg Nationwide 700**: 700 dining establishments across Luxembourg. Download: [`output/luxembourg_700_restaurants.csv`](output/luxembourg_700_restaurants.csv).

---

## Project Structure

```text
lead-scraper-falcon/
├── run.bat                     # 1-Click launcher for Windows
├── run.sh                      # 1-Click launcher for Linux and macOS
├── main.py                     # Entry point & interactive wizard
├── config.py                   # Configuration & rate limits
├── requirements.txt            # Dependencies (includes integrated Milli engine)
├── modules/
│   ├── crawler.py              # Milli Universal Engine integration
│   ├── extractor.py            # Contact extraction & Cloudflare deobfuscator
│   ├── fusion.py               # Multi-source data fusion & confidence scoring
│   ├── local_exporter.py       # Multi-format export (CSV, JSON, TXT)
│   ├── discovery.py            # Dynamic business discovery engine
│   ├── search.py               # Search querying & aggregator domain filter
│   ├── rate_limiter.py         # Adaptive per-host rate limiter
│   └── sheets.py               # Google Sheets cloud synchronization
├── output/                     # Generated export files
└── tests/                      # Pytest test suite
```

---

## Testing

Run the test suite with `pytest`:

```bash
pytest tests/ -v
```

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Author

**Abdullah Al Raju**  
- GitHub: [@Abdullah-Al-Raju](https://github.com/Abdullah-Al-Raju)  
- Email: abdullahalraju33@gmail.com
