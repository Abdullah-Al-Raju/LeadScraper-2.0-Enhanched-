"""
LeadScraper Configuration
All configuration constants and settings
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================
# GOOGLE SHEETS CONFIGURATION
# ============================================================

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
INPUT_TAB_NAME = "Input"
OUTPUT_TAB_NAME = "Results"
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "credentials/service_account.json")

# ============================================================
# OPENROUTER AI CONFIGURATION
# ============================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Multi-model rotation (AI switches models on rate limits)
OPENROUTER_MODELS = [
    # Original 4 models
    "arcee-ai/trinity-large-preview:free",
    "stepfun/step-3.5-flash:free",
    "deepseek/deepseek-r1-0528:free",
    "openrouter/aurora-alpha",

    # NEW: 11 additional free models for massive capacity!
    "liquid/lfm-2.5-1.2b-thinking:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-235b-a22b-thinking-2507",
    "qwen/qwen3-vl-30b-a3b-thinking",
    "qwen/qwen3-vl-235b-a22b-thinking",
    "qwen/qwen3-coder:free"
]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_CONTEXT_CHARS = 4000  # Keep under AI token limit

# AI Manager settings
AI_RETRY_DELAY = 5  # seconds before retrying failed model
AI_MODEL_COOLDOWN = 60  # seconds before retrying rate-limited model

# ============================================================
# SCRAPING BEHAVIOR
# ============================================================

REQUEST_TIMEOUT = 10           # seconds
DELAY_BETWEEN_LEADS = 1        # seconds (reduced for speed)
DELAY_JITTER = 1               # random 0-1 seconds added
MAX_RETRIES = 2                # reduced retries (fail faster)
RETRY_BACKOFF = 3              # seconds between retries (reduced)
MAX_PAGES_PER_SITE = 3         # homepage + 2 contact pages
RESPECT_ROBOTS_TXT = False      # check robots.txt before crawling

# ============================================================
# MULTI-SOURCE CONFIGURATION
# ============================================================
ENABLE_FACEBOOK = True         # search Facebook business pages
ENABLE_INSTAGRAM = True        # search Instagram business profiles
ENABLE_DIRECTORIES = True      # extract from directory sites
ENABLE_MULTI_SEARCH = True     # search multiple engines

# Source prioritization (1-10, higher = more trustworthy)
SOURCE_PRIORITY = {
    'website': 10,             # Official website (highest priority)
    'facebook': 9,             # Facebook page (high quality)
    'instagram': 7,            # Instagram profile
    'directory': 5             # Directory listing (lower priority)
}

# Data fusion settings
MIN_CONFIDENCE_SCORE = 60      # minimum score to mark as success
REQUIRE_CROSS_VERIFICATION = False  # require 2+ sources for verification


# ============================================================
# DISCOVERY MODE CONFIGURATION
# ============================================================
ENABLE_DISCOVERY_MODE = True   # enable restaurant discovery mode
DEFAULT_DISCOVERY_QUANTITY = 100  # default number to discover
MAX_DISCOVERY_QUANTITY = 500   # maximum allowed

# Extraction limits (MAXIMUM mode)
MAX_PHONES_PER_BUSINESS = 10   # max phones to extract per business
MAX_EMAILS_PER_BUSINESS = 10   # max emails to extract
MAX_SOCIAL_LINKS = 20          # max social media links

# Validation
REQUIRE_CONTACT_FOR_DISCOVERY = True  # only add if has phone OR email
MIN_CONFIDENCE_FOR_OUTPUT = 30  # lower threshold for discovery mode

# Sheet Management
AUTO_CLEAR_INPUT_ON_DISCOVERY = True  # clear input sheet before discovery
AUTO_DEDUPLICATE_RESULTS = True       # auto-remove duplicates
AUTO_SORT_RESULTS = True              # sort by confidence



# ============================================================
# SEARCH CONFIGURATION
# ============================================================

MAX_SEARCH_RESULTS = 8
SEARCH_DELAY = 1  # seconds between searches (reduced for speed)

# Domains to filter out (aggregators, not official business sites)
AGGREGATOR_DOMAINS = [
    # Social & review sites
    "yelp.com", "yellowpages.com", "facebook.com",
    "instagram.com", "twitter.com", "linkedin.com",
    "tripadvisor.com", "bbb.org", "mapquest.com",
    "foursquare.com", "grubhub.com", "doordash.com",
    "ubereats.com", "nextdoor.com", "angi.com",
    "thumbtack.com", "zocdoc.com", "healthgrades.com",
    "vitals.com", "webmd.com", "google.com", "bing.com",
    # Phone directories & lookup sites
    "spokeo.com", "numlooker.com", "whitepages.com",
    "truecaller.com", "beenverified.com", "fastpeoplesearch.com",
    "411.com", "anywho.com", "zabasearch.com", "pipl.com",
    "thatsthem.com", "usphonebook.com", "reversephonelookup.com",
    # Airlines & travel (common false positives)
    "airwaysbd.com", "bfrsfb.com",
    # News & wiki
    "wikipedia.org", "news.google.com",
    # Government
    "gov.bd", "gov.com",
    # Job sites
    "indeed.com", "glassdoor.com", "monster.com",
    # General directories
    "justdial.com", "sulekha.com", "manta.com",
    "chamberofcommerce.com", "hotfrog.com",
    "brownbook.net", "cybo.com", "infobel.com",
]

# ============================================================
# CONTACT PAGE DETECTION
# ============================================================

# Keywords in URL that indicate contact page
CONTACT_URL_KEYWORDS = [
    "contact", "about", "reach", "touch", "location",
    "find-us", "get-in-touch", "connect", "our-team"
]

# Keywords in anchor text that indicate contact page
CONTACT_ANCHOR_KEYWORDS = [
    "contact", "about", "reach us", "find us", "location",
    "get in touch", "our team", "contact us", "about us"
]

# ============================================================
# EXTRACTION PATTERNS
# ============================================================

# Phone number patterns (flexible for various formats)
PHONE_PATTERNS = [
    r'\+?1?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
    r'\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
]

# Email pattern
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# Social media patterns
SOCIAL_PATTERNS = {
    'facebook': r'(?:https?://)?(?:www\.)?facebook\.com/[\w\-\.]+',
    'instagram': r'(?:https?://)?(?:www\.)?instagram\.com/[\w\-\.]+',
    'twitter': r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/[\w\-\.]+',
    'linkedin': r'(?:https?://)?(?:www\.)?linkedin\.com/(?:company|in)/[\w\-\.]+'
}

# ============================================================
# LOGGING
# ============================================================

LOG_FILE = "logs/scraper.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================
# STATUS MESSAGES
# ============================================================

STATUS_PROCESSING = "Processing..."
STATUS_DONE = "[DONE]"
STATUS_PARTIAL = "[PARTIAL]"
STATUS_NO_WEBSITE = "[NO WEBSITE]"
STATUS_CRAWL_FAILED = "[CRAWL FAILED]"
STATUS_EXTRACTION_FAILED = "[EXTRACTION FAILED]"
STATUS_ROBOTS_BLOCKED = "[BLOCKED]"
STATUS_RETRY = "[RETRY]"

# ============================================================
# USER-AGENT
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}
