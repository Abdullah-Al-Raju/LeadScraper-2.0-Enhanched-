# LeadScraper AI Agent - Product Requirements Document

## Overview

LeadScraper is an intelligent AI-powered business discovery and contact extraction system. It automatically finds businesses in any location, researches them across multiple sources, and extracts complete contact information with high accuracy.

**Key Capabilities**:
- AI-driven business discovery (no manual input needed)
- Multi-source contact extraction (Search, Facebook, Instagram, Websites)
- Intelligent data fusion with confidence scoring
- Professional terminal UI with real-time progress
- Automatic rate limit handling with model rotation
- One-command operation

---

## Core Features

### 1. AI-Powered Business Discovery

**What It Does**: AI automatically discovers businesses based on location and category.

**How It Works**:
1. User provides: location, quantity, category
2. AI plans optimal search strategy
3. AI generates diverse search queries
4. AI extracts business names from results
5. AI validates and cleans results

**Example**:
```bash
python main.py --discover "Dhaka, Bangladesh" --quantity 100
```

**Output**: 100 restaurant names populated in Input sheet, ready for extraction.

---

### 2. Multi-Source Intelligent Extraction

**What It Does**: Extracts contact information from multiple sources and fuses data intelligently.

**Sources**:
- **General Web Search**: Finds official websites and contact snippets
- **Facebook**: Searches business pages for phones/emails/addresses
- **Instagram**: Extracts contact info from business profiles
- **Traditional Website Crawl**: Scrapes official websites

**Data Fusion**:
- Cross-verifies information across sources
- Assigns confidence scores (0-100%)
- Prioritizes verified data
- Handles conflicts intelligently

**Extracted Data**:
- Business Name
- Phone Numbers (multiple)
- Email Addresses (multiple)
- Street Address
- City, State, ZIP
- Website URL
- Social Media Links
- Confidence Score

---

### 3. Multi-Model AI System

**What It Does**: Uses 4 different AI models with automatic rotation to handle rate limits.

**Models**:
1. `arcee-ai/trinity-large-preview:free`
2. `stepfun/step-3.5-flash:free`
3. `deepseek/deepseek-r1-0528:free`
4. `openrouter/aurora-alpha`

**Smart Rotation**:
- Automatically switches models on HTTP 429 (rate limit)
- 60-second cooldown per model
- Retries with different models
- Ensures continuous operation

**Benefits**:
- No manual intervention needed
- Handles rate limits gracefully
- Maximizes throughput
- Reduces downtime

---

### 4. Professional Terminal UI

**What It Does**: Beautiful, clean terminal interface with real-time progress tracking.

**Features**:

**Startup Banner**:
```
╔═══════════════════════════════════════════════════╗
║                                                   ║
║           LeadScraper AI Agent v2.0              ║
║       Intelligent Business Discovery              ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
```

**Color-Coded Messages** (no emojis):
- `[SUCCESS]` - Green (successful operations)
- `[WARNING]` - Yellow (warnings, rate limits)
- `[ERROR]` - Red (errors, failures)
- `[AI]` - Cyan (AI operations)
- `[INFO]` - White (general information)

**Completion Separator** (after each business):
```
────────────────────────────────────────────────────────────
────────────────────────── 3/10 ───────────────────────────
────────────────────────────────────────────────────────────
```

**Benefits**:
- Easy to track progress
- Professional appearance
- Clear visual feedback
- No clutter or emojis

---

### 5. Google Sheets Integration

**What It Does**: Uses Google Sheets as database for input and output.

**Structure**:

**Input Sheet**:
| Business Name | Category | City | Status |
|--------------|----------|------|--------|
| Pizza Hut | restaurant | Dhaka | Processing... |

**Results Sheet**:
| Business | Phone | Email | Address | Confidence | Sources |
|----------|-------|-------|---------|------------|---------|
| Pizza Hut | (123) 456-7890 | info@pizza.com | 123 Main St | 95% | website, facebook |

**Features**:
- Auto-deduplication
- Auto-sorting by confidence
- Status tracking
- Real-time updates

---

## Technical Architecture

### Module Structure

```
d:\Scrapper\
├── main.py                          # Main orchestrator + CLI
├── config.py                        # All configuration
├── .env                            # API keys
├── modules/
│   ├── ai_manager.py               # Multi-model AI rotation
│   ├── display.py                  # Terminal UI (rich)
│   ├── utils.py                    # Utilities, logging
│   ├── sheets.py                   # Google Sheets operations
│   ├── search.py                   # Multi-engine search
│   ├── crawler.py                  # Website crawling
│   ├── extractor.py                # Contact extraction
│   ├── fusion.py                   # Data fusion
│   ├── restaurant_discovery.py     # AI discovery
│   └── sources/
│       ├── facebook_scraper.py     # Facebook extraction
│       ├── instagram_scraper.py    # Instagram extraction
│       └── search_result_extractor.py
└── credentials/
    └── service_account.json        # Google Sheets auth
```

### Data Flow

```
User Command
    ↓
AI Discovery (optional)
    ↓
Multi-Source Search
    ↓
Parallel Extraction (Web, Facebook, Instagram, Website)
    ↓
Data Fusion (merge + validate)
    ↓
Results Sheet
```

### AI Architecture

```
User Request
    ↓
AIManager
    ↓
Model 1 (arcee-ai) → Try
    ↓ (429 rate limit)
Model 2 (stepfun) → Try
    ↓ (429 rate limit)
Model 3 (deepseek) → Try
    ↓ (success!)
Return Data
```

---

## Usage

### Setup

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure Environment** (`.env`):
```env
GOOGLE_SHEET_ID=your_sheet_id
OPENROUTER_API_KEY=your_api_key
SERVICE_ACCOUNT_FILE=credentials/service_account.json
```

3. **Add Google Sheets Credentials**:
- Place service_account.json in credentials/

### Running

**Discovery + Extraction (One Command)**:
```bash
# Find 100 restaurants in Dhaka
python main.py --discover "Dhaka, Bangladesh" --quantity 100

# Find 50 cafes in Chittagong
python main.py --discover "Chittagong" --quantity 50 --category cafe

# Quick test (5 businesses)
python main.py --discover "Dhaka" --quantity 5
```

**Manual Mode** (Input sheet already populated):
```bash
python main.py
```

### Output

**Terminal**:
- Real-time progress with color-coded messages
- Completion separators after each business
- Summary statistics at end

**Google Sheet**:
- Results sheet populated with all data
- Confidence scores for each business
- Source attribution

---

## Configuration

### AI Settings (`config.py`)

```python
OPENROUTER_MODELS = [
    "arcee-ai/trinity-large-preview:free",
    "stepfun/step-3.5-flash:free",
    "deepseek/deepseek-r1-0528:free",
    "openrouter/aurora-alpha"
]

AI_MODEL_COOLDOWN = 60  # seconds before retrying rate-limited model
```

### Speed Settings

```python
DELAY_BETWEEN_LEADS = 1     # seconds (reduced from 3)
DELAY_JITTER = 1            # random 0-1 seconds
MAX_RETRIES = 2             # reduced from 3
SEARCH_DELAY = 1            # seconds between searches
```

### Discovery Settings

```python
DEFAULT_DISCOVERY_QUANTITY = 100
MAX_DISCOVERY_QUANTITY = 500
AUTO_CLEAR_INPUT_ON_DISCOVERY = True
AUTO_DEDUPLICATE_RESULTS = True
AUTO_SORT_RESULTS = True
```

### Source Settings

```python
ENABLE_FACEBOOK = True
ENABLE_INSTAGRAM = True
ENABLE_DIRECTORIES = True
ENABLE_MULTI_SEARCH = True
```

### Extraction Limits

```python
MAX_PHONES_PER_BUSINESS = 10
MAX_EMAILS_PER_BUSINESS = 10
MAX_SOCIAL_LINKS = 20
```

---

## Performance

### Speed
- **Current**: ~40 seconds per business
- **Discovery**: ~3-5 seconds per name extraction
- **Total for 100**: ~70 minutes (discovery + extraction)

### Accuracy
- **Success Rate**: 70% (complete data)
- **Partial Rate**: 30% (some data)
- **Failure Rate**: 0% (always gets something)

### Rate Limits
- **Handled Automatically**: Multi-model rotation
- **No Downtime**: Continuous switching
- **4x Capacity**: 4 models = 4x rate limits

---

## Key Advantages

1. **Fully Automated**: One command, everything done
2. **Intelligent**: AI plans, executes, validates
3. **Resilient**: Handles rate limits, errors, missing data
4. **Multi-Source**: Cross-verifies data for accuracy
5. **Professional UI**: Clean, easy to track
6. **Configurable**: Extensive configuration options
7. **Scalable**: Can handle hundreds of businesses

---

## Dependencies

```
gspread==6.1.4
oauth2client==4.1.3
beautifulsoup4==4.12.3
requests==2.32.3
lxml==5.3.0
python-dotenv==1.0.1
duckduckgo-search==7.1.0
primp==0.6.4
rich==14.3.2
```

---

## Error Handling

### Rate Limits
- **Auto-handled**: Model rotation
- **Cooldown**: 60 seconds per model
- **Fallback**: Tries all 4 models

### Network Errors
- **Retries**: 2 attempts with backoff
- **Timeout**: 10 seconds per request
- **Graceful Degradation**: Continues with partial data

### Data Quality
- **Validation**: AI validates all extracted data
- **Confidence Scores**: 0-100% based on source count and verification
- **Deduplication**: Auto-removes duplicates

---

## Future Enhancements

### Potential Additions
1. **Progress Bars**: Rich progress bars for long operations
2. **Live Status Panel**: Real-time status display
3. **Results Table**: Summary table at completion
4. **Export Options**: CSV, JSON export
5. **Caching**: Cache search results to avoid re-searching
6. **Parallel Processing**: Process multiple businesses simultaneously
7. **More Sources**: LinkedIn, Yelp, TripAdvisor
8. **Resume Support**: Resume interrupted runs

---

## Support

For issues or questions:
1. Check logs in `logs/scraper.log`
2. Verify configuration in `config.py`
3. Ensure API keys are valid in `.env`
4. Check Google Sheets permissions

---

## License

Proprietary - Internal Use Only
