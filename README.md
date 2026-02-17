<p align="center">
  <h1 align="center">🔍 LeadScraper 2.0 Enhanced</h1>
  <p align="center">
    <strong>AI-Powered Business Lead Generation Tool</strong><br>
    Automatically discover businesses, find their websites, and extract contact information — all written to Google Sheets.
  </p>
  <p align="center">
    <a href="#-quick-start">Quick Start</a> •
    <a href="#-how-it-works">How It Works</a> •
    <a href="#-comparison">Comparison</a> •
    <a href="#-faq">FAQ</a>
  </p>
</p>

---

## 📖 What Is This?

LeadScraper 2.0 is an **automated business lead generation tool**. Give it a location and category (e.g., "restaurants in Dhaka"), and it will:

1. 🤖 **Discover** real businesses using AI-powered search
2. 🌐 **Find** their official websites
3. 📞 **Extract** phone numbers, emails, addresses, social media
4. 📊 **Write** everything to a Google Sheet — ready to use

**No manual Googling. No copy-pasting. No spreadsheet headaches.**

---

## 🔄 Evolution: How We Got Here

| Feature | 📋 Manual Research | 🔧 LeadScraper v1.0 | ⚡ LeadScraper 2.0 Enhanced | 🚀 LeadScraper Ultimate *(Coming Soon)* |
|---|---|---|---|---|
| **Business Discovery** | Google it yourself | Reads from sheet | AI discovers businesses automatically | AI discovers + validates + enriches |
| **Website Finding** | Click through links | Single search engine | Multi-engine (DuckDuckGo + 6 engines) | Smart engine rotation + proxy support |
| **Data Extraction** | Copy-paste manually | Basic regex only | AI + Regex + JSON-LD (3-tier) | Deep crawl + AI analysis + API enrichment |
| **Social Media** | Search Facebook/IG | Not supported | Auto-finds Facebook + Instagram | All platforms + follower counts + engagement |
| **Speed** | 10-15 min/business | 2-3 min/business | **10-12 sec/business** | 5 sec/business with caching |
| **Accuracy** | Depends on you | ~50% | **~80%+ with multi-source fusion** | 95%+ with AI verification |
| **Concurrent** | One at a time | One at a time | 3 businesses in parallel | 10+ in parallel |
| **Error Handling** | You deal with it | Basic retry | Smart rate limiting + fallbacks | Auto-healing + retry queue |
| **Output** | Your own spreadsheet | Google Sheets | Google Sheets + confidence scores | Sheets + CRM + API + Export |
| **Cost** | Free (your time) | Free | **Free** (uses free AI models) | Free tier + Premium option |
| **Setup Time** | N/A | 30 min | **10 min** | 5 min (one-click) |

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.8+** installed ([Download](https://www.python.org/downloads/))
- **Google Account** (for Google Sheets)
- **OpenRouter Account** (free — [Sign up](https://openrouter.ai/))

### Step 1: Clone & Install

```bash
git clone https://github.com/Abdullah-Al-Raju/LeadScraper-2.0-Enhanched-.git
cd LeadScraper-2.0-Enhanched-

pip install -r requirements.txt
```

### Step 2: Set Up Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **Google Sheets API** and **Google Drive API**
4. Create a **Service Account**:
   - Go to *IAM & Admin → Service Accounts*
   - Click *Create Service Account*
   - Give it a name (e.g., "leadscraper")
   - Click *Create and Continue*
   - Skip role assignment → Click *Done*
5. Create a key:
   - Click on your service account
   - Go to *Keys* tab → *Add Key → Create New Key → JSON*
   - Download the JSON file
6. Save the JSON file as `credentials/service_account.json`
7. Create a Google Sheet and **share it** with the service account email (the email in the JSON file)

### Step 3: Get OpenRouter API Key

1. Go to [OpenRouter](https://openrouter.ai/) and sign up (free)
2. Go to [API Keys](https://openrouter.ai/keys)
3. Click *Create Key*
4. Copy the key

### Step 4: Configure Environment

```bash
# Copy the example config
cp .env.example .env

# Edit .env with your actual values
```

Fill in your `.env` file:

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
GOOGLE_SHEET_ID=your-sheet-id-from-url
SERVICE_ACCOUNT_FILE=credentials/service_account.json
```

> **Finding your Google Sheet ID:** Open your sheet, look at the URL:
> `https://docs.google.com/spreadsheets/d/`**THIS_PART_IS_YOUR_ID**`/edit`

### Step 5: Run It

```bash
# Discover 3 restaurants in a location
python main.py --discover "Bonani,Bangladesh" --quantity 3

# With terminal capture (recommended — saves logs)
python cap.py python main.py --discover "Bonani,Bangladesh" --quantity 3
```

---

## 🔧 How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    LeadScraper 2.0                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. AI DISCOVERY                                        │
│     └─ AI plans search strategy                         │
│     └─ Runs 8-12 diverse DuckDuckGo searches            │
│     └─ AI extracts real business names from results      │
│     └─ Deduplicates and validates                        │
│                                                         │
│  2. WEBSITE FINDING                                      │
│     └─ Searches for each business website                │
│     └─ Filters out aggregators (Yelp, WhitePages, etc)   │
│     └─ Returns the actual business website               │
│                                                         │
│  3. PARALLEL EXTRACTION (4 sources at once!)             │
│     ├─ Website Crawler (crawls homepage + contact page)  │
│     ├─ Search Snippet Extraction (from result text)      │
│     ├─ Facebook Search (finds business page)             │
│     └─ Instagram Search (finds business profile)         │
│                                                         │
│  4. DATA FUSION                                          │
│     └─ Merges data from all sources                      │
│     └─ Resolves conflicts (most reliable source wins)    │
│     └─ Calculates confidence score (0-100%)             │
│                                                         │
│  5. OUTPUT TO GOOGLE SHEETS                              │
│     └─ Writes: Name, Phone, Email, Address, Website,     │
│        Facebook, Instagram, Hours, Owner, Confidence     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Architecture

```
main.py                     ← Entry point & pipeline orchestration
├── config.py               ← All configuration settings
├── cap.py                  ← Terminal output capture system
│
├── modules/
│   ├── ai_manager.py       ← AI model rotation (15 free models!)
│   ├── async_pipeline.py   ← Async parallel processing
│   ├── async_config.py     ← Async settings
│   ├── crawler.py          ← Website crawler (async)
│   ├── extractor.py        ← Contact extraction (AI + Regex + JSON-LD)
│   ├── fusion.py           ← Multi-source data merger
│   ├── search.py           ← DuckDuckGo search (async)
│   ├── sheets.py           ← Google Sheets integration
│   ├── restaurant_discovery.py  ← AI-powered business discovery
│   ├── http_client.py      ← HTTP client with retry logic
│   ├── rate_limiter.py     ← Smart rate limiting
│   ├── cache.py            ← Progress caching (resume support)
│   ├── display.py          ← Terminal UI formatting
│   ├── utils.py            ← Utility functions
│   │
│   └── sources/
│       ├── search_result_extractor.py  ← Extract data from search snippets
│       ├── facebook_scraper.py         ← Facebook page finder
│       └── instagram_scraper.py        ← Instagram profile finder
```

---

## 📊 Usage Examples

### Discover restaurants in a city

```bash
python main.py --discover "Gulshan,Dhaka" --quantity 10
```

### Discover cafes specifically

```bash
python main.py --discover "Banani,Dhaka" --quantity 5 --category cafe
```

### Process businesses already in your sheet

```bash
# If you already have business names in the Input tab:
python main.py
```

### With logging capture

```bash
python cap.py python main.py --discover "Dhanmondi,Dhaka" --quantity 20
```

### Check your Google Sheet

After running, check your Google Sheet:

- **Input tab**: Shows discovered businesses with processing status
- **Results tab**: Contains all extracted contact data with confidence scores

---

## 📋 Output Fields

| Column | Description | Example |
|--------|-------------|---------|
| Business Name | Official business name | Pizza Hut Gulshan |
| Phone | Phone number(s) | +880 1712345678 |
| Email | Email address(es) | <info@pizzahut.com.bd> |
| Address | Street address | House 45, Road 11, Gulshan-2 |
| City | City/Location | Dhaka |
| Website | Official website URL | <https://pizzahut.com.bd> |
| Facebook | Facebook page URL | <https://facebook.com/PizzaHutBD> |
| Instagram | Instagram profile URL | <https://instagram.com/pizzahutbd> |
| Hours | Business hours | Sat-Thu: 11AM-11PM |
| Owner | Owner/Manager name | Mr. Rahman |
| Confidence | Data reliability score | 85% |
| Sources | Where data came from | website, facebook_search, search_results |

---

## 🤔 FAQ

### General Questions

**Q: Is this free?**
> Yes! LeadScraper 2.0 uses free AI models via OpenRouter and free Google Sheets API. Zero cost.

**Q: What countries does it work for?**
> Any country. It searches the open web using DuckDuckGo, which has global coverage. Tested extensively with Bangladesh, but works for USA, UK, India, or anywhere.

**Q: How accurate is the data?**
> The confidence score tells you. 80%+ means highly reliable (data from 2-3 sources confirming each other). 40-60% means partial data. Below 40% means limited information found.

**Q: Can I use this for any business type, not just restaurants?**
> Yes! Change the `--category` flag: `--category "salon"`, `--category "pharmacy"`, `--category "hotel"`, etc.

### Setup Questions

**Q: I get "GOOGLE_SHEET_ID not set" error**
> Make sure you created a `.env` file (not `.env.example`) with your actual Sheet ID.

**Q: I get "Service account file not found" error**
> Download the JSON key from Google Cloud Console and save it as `credentials/service_account.json`.

**Q: I get "Permission denied" on Google Sheets**
> Share your Google Sheet with the service account email (found in your JSON file under `client_email`).

**Q: I get "OPENROUTER_API_KEY not set" error**
> Add your OpenRouter API key to the `.env` file. Get one free at [openrouter.ai/keys](https://openrouter.ai/keys).

### Usage Questions

**Q: It seems slow — is it working?**
> Yes! Each business takes ~10-12 seconds (searching, crawling, extracting from 4 sources in parallel). With `cap.py`, you'll see real-time progress. Without it, check the Google Sheet for live updates.

**Q: Can I resume if it crashes?**
> Yes! LeadScraper has built-in progress caching. Just run the same command again — it skips already-processed businesses.

**Q: How many businesses can I process at once?**
> Tested up to 100. For large batches (50+), expect some rate limiting from search engines (HTTP 429 errors) — the tool handles these automatically with cooldown periods.

**Q: Can I change the AI models used?**
> Yes, edit `config.py` → `OPENROUTER_MODELS` list. The tool rotates through all models automatically for maximum throughput.

**Q: What if a search engine blocks me?**
> The tool uses 6+ search engines (DuckDuckGo, Google, Brave, Yahoo, Yandex, Mojeek) and automatically falls back when one blocks. Rate limiting is built in.

### Technical Questions

**Q: What's the tech stack?**
> Python 3.8+, httpx (async HTTP), BeautifulSoup4 (HTML parsing), gspread (Google Sheets), OpenRouter API (AI).

**Q: What AI models does it use?**
> 15 free models via OpenRouter, including DeepSeek, Qwen, Nvidia Nemotron, and more. The AI Manager rotates through them to avoid rate limits.

**Q: Is my data safe?**
> Yes. Your API keys stay in `.env` (never committed to Git). Data goes directly to YOUR Google Sheet. Nothing is stored on external servers.

**Q: Can I run this on a server/VPS?**
> Yes! It's a Python script — runs anywhere Python 3.8+ is installed. Works on Windows, Mac, and Linux.

---

## 🔐 Security Notes

- **Never commit your `.env` file** — it contains API keys
- **Never commit `credentials/`** — it contains your Google service account key
- **The `.gitignore` is configured** to exclude all sensitive files automatically
- **API keys are loaded from environment variables** — not hardcoded

---

## 📁 Project Structure

```
LeadScraper-2.0-Enhanced/
├── .env.example        ← Template for your environment variables
├── .gitignore          ← Keeps secrets out of Git
├── main.py             ← Main entry point
├── config.py           ← Configuration settings
├── cap.py              ← Terminal capture (real-time output + logging)
├── requirements.txt    ← Python dependencies
├── PRD.md              ← Product Requirements Document
├── CATEGORY_GUIDE.md   ← Guide for different business categories
├── README.md           ← This file
│
├── credentials/        ← YOUR service account JSON (not in Git)
│   └── service_account.json
│
├── modules/            ← Core business logic
│   ├── ai_manager.py
│   ├── async_pipeline.py
│   ├── crawler.py
│   ├── extractor.py
│   ├── fusion.py
│   ├── search.py
│   ├── sheets.py
│   └── sources/
│       ├── search_result_extractor.py
│       ├── facebook_scraper.py
│       └── instagram_scraper.py
│
└── logs/               ← Terminal capture output (not in Git)
```

---

## 🛠 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Module not found" | Run `pip install -r requirements.txt` |
| "Sheet not found" | Check GOOGLE_SHEET_ID in .env matches your sheet URL |
| "Permission denied" | Share Google Sheet with service account email |
| Tool appears frozen | Use `python cap.py` wrapper for real-time output |
| HTTP 429 errors | Normal — rate limiting. Tool handles this automatically |
| HTTP 403 errors | Some search engines block. Tool falls back to others |
| Unicode errors | Already fixed in v2.0 — all ASCII status messages |
| Wrong websites found | Aggregator filter blocks 40+ junk domains automatically |

---

## 👤 Author

**Abdullah Al Raju**

- GitHub: [@Abdullah-Al-Raju](https://github.com/Abdullah-Al-Raju)
- Email: <abdullahalraju33@gmail.com>

---

## 📜 License

This project is open source. Feel free to use, modify, and distribute.

---

<p align="center">
  <strong>⭐ Star this repo if it helped you!</strong><br>
  Built with Python, AI, and lots of debugging 🐛
</p>
