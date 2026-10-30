"""
LeadScraper Configuration
Defines aggregator blacklists, default timeouts, concurrency settings, and output paths.
"""

import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Engine Settings - Milli Fastness & Polite Pacing
DEFAULT_CONCURRENCY = 25
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_SUBPAGE_TIMEOUT = 4.0
POLITE_INTERVAL_SAME_DOMAIN = 0.05  # 50ms token bucket per host
HTTP_429_MAX_RETRIES = 3
MAX_SEARCH_RESULTS_PER_QUERY = 15

# Domain Aggregators & Directories Blacklist (Filtered out to prioritize official business websites)
AGGREGATOR_DOMAINS = {
    # Major review & delivery platforms
    "yelp.com", "tripadvisor.com", "yellowpages.com", "superpages.com",
    "foursquare.com", "zomato.com", "opentable.com", "grubhub.com",
    "doordash.com", "ubereats.com", "postmates.com", "deliveroo.com",
    "menupages.com", "zagat.com", "seamless.com", "angi.com",
    "thumbtack.com", "homeadvisor.com", "bbb.org", "mapquest.com",
    
    # Social & Media platforms
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com",
    "wikipedia.org", "reddit.com", "quora.com",
    
    # General directories
    "justdial.com", "sulekha.com", "manta.com", "chamberofcommerce.com",
    "hotfrog.com", "brownbook.net", "cybo.com", "infobel.com",
    "bdplaces.com", "trustpilot.com", "capterra.com", "g2.com",
    "clutch.co", "upcity.com", "goodfirms.co",
    
    # Editorial, guides & listicle blogs
    "theinfatuation.com", "eater.com", "timeout.com", "thrillist.com",
    "grokipedia.com", "citysearch.com", "expertise.com", "tastingtable.com",
    "wanderlog.com", "cntraveler.com", "culturetrip.com", "travelandleisure.com",
    "coffeeroasterfinder.com", "coffeevogue.com", "roastlocal.com", "tencoffees.com",
    "seekseattle.com", "emeraldpalate.com", "mybestseattle.com", "bakio.co",
    "coffeeroasternearme.com", "restaurantji.com", "menupix.com", "sirved.com",
    
    # Lead databases & intelligence tools
    "contactout.com", "zoominfo.com", "rocketreach.co", "apollo.io",
    "lusha.com", "crunchbase.com", "dnb.com", "seamless.ai",
}

# Domain TLDs to clean
IGNORED_SUBDOMAINS = {"www.", "m.", "mobile."}
