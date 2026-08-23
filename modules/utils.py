"""
Utility functions for LeadScraper
Rate limiting, retry logic, logging, text cleaning, robots.txt checking
"""

import time
import random
import logging
import functools
import hashlib
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import config


# ============================================================
# LOGGING SETUP
# ============================================================

def setup_logging():
    """Configure logging for the application"""
    import os

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


logger = setup_logging()


# ============================================================
# RATE LIMITING
# ============================================================

def rate_limit(min_delay=None, jitter=None):
    """
    Rate limiting decorator with jitter

    Args:
        min_delay: Minimum delay in seconds (default from config)
        jitter: Maximum random jitter in seconds (default from config)
    """
    def decorator(func):
        last_call = [0]  # Use list to make it mutable in closure

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = min_delay or config.DELAY_BETWEEN_LEADS
            jitter_val = jitter or config.DELAY_JITTER

            # Calculate time since last call
            elapsed = time.time() - last_call[0]

            # Add delay if needed
            if elapsed < delay:
                sleep_time = delay - elapsed + random.uniform(0, jitter_val)
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)

            # Execute function
            result = func(*args, **kwargs)

            # Update last call time
            last_call[0] = time.time()

            return result

        return wrapper
    return decorator


# ============================================================
# RETRY LOGIC
# ============================================================

def retry_on_failure(max_retries=None, backoff=None, exceptions=(Exception,)):
    """
    Retry decorator with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts (default from config)
        backoff: Base backoff time in seconds (default from config)
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = max_retries or config.MAX_RETRIES
            backoff_time = backoff or config.RETRY_BACKOFF

            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries:
                        logger.error(f"{func.__name__} failed after {retries} retries: {e}")
                        raise

                    # Calculate exponential backoff
                    wait_time = backoff_time * (2 ** attempt)
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{retries + 1}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)

        return wrapper
    return decorator


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    """
    Clean and normalize text

    Args:
        text: Raw text string

    Returns:
        Cleaned text string
    """
    if not text:
        return ""

    # Remove extra whitespace
    text = " ".join(text.split())

    # Remove common unicode artifacts
    text = text.replace('\xa0', ' ')
    text = text.replace('\u200b', '')

    return text.strip()


def truncate_text(text, max_chars=None):
    """
    Truncate text to maximum length

    Args:
        text: Text to truncate
        max_chars: Maximum characters (default from config)

    Returns:
        Truncated text
    """
    max_length = max_chars or config.MAX_CONTEXT_CHARS

    if len(text) <= max_length:
        return text

    return text[:max_length] + "..."


def extract_visible_text(soup):
    """
    Extract visible text from BeautifulSoup object
    Removes scripts, styles, and hidden elements

    Args:
        soup: BeautifulSoup object

    Returns:
        Visible text string
    """
    # Remove script and style elements
    for element in soup(['script', 'style', 'meta', 'link', 'noscript']):
        element.decompose()

    # Get text
    text = soup.get_text(separator=' ', strip=True)

    # Clean text
    return clean_text(text)


# ============================================================
# ROBOTS.TXT CHECKING
# ============================================================

def can_fetch_url(url):
    """
    Check if URL can be fetched according to robots.txt

    Args:
        url: URL to check

    Returns:
        Boolean indicating if URL can be fetched
    """
    if not config.RESPECT_ROBOTS_TXT:
        return True

    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        can_fetch = rp.can_fetch(config.USER_AGENT, url)

        if not can_fetch:
            logger.warning(f"robots.txt disallows fetching: {url}")

        return can_fetch

    except Exception as e:
        logger.debug(f"Error checking robots.txt for {url}: {e}. Allowing fetch.")
        return True  # If we can't check, allow by default


# ============================================================
# URL UTILITIES
# ============================================================

def normalize_url(url):
    """
    Normalize URL for consistency

    Args:
        url: URL string

    Returns:
        Normalized URL
    """
    if not url:
        return ""

    # Convert to string and strip whitespace
    url = str(url).strip()

    if not url:
        return ""

    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Remove trailing slash
    url = url.rstrip('/')

    return url


def is_aggregator(url):
    """
    Check if URL is from an aggregator site

    Args:
        url: URL to check

    Returns:
        Boolean indicating if URL is from aggregator
    """
    if not url:
        return False

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Remove www.
    domain = domain.replace('www.', '')

    # Check against aggregator list
    return any(agg in domain for agg in config.AGGREGATOR_DOMAINS)


def get_domain(url):
    """
    Extract domain from URL

    Args:
        url: URL string

    Returns:
        Domain string
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url)
        return parsed.netloc.replace('www.', '')
    except Exception:
        return ""


# ============================================================
# HASHING (for duplicate detection)
# ============================================================

def hash_business(name, city=""):
    """
    Create hash for business (for duplicate detection)

    Args:
        name: Business name
        city: City/location

    Returns:
        Hash string
    """
    key = f"{name.lower().strip()}|{city.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()


# ============================================================
# DATA VALIDATION
# ============================================================

def is_valid_email(email):
    """
    Basic email validation

    Args:
        email: Email address

    Returns:
        Boolean indicating if email is valid
    """
    if not email:
        return False

    # Exclude noreply and generic emails
    invalid_prefixes = ['noreply', 'no-reply', 'donotreply']
    if any(prefix in email.lower() for prefix in invalid_prefixes):
        return False

    # Basic format check
    import re
    pattern = config.EMAIL_PATTERN
    return bool(re.match(pattern, email))


def format_phone(phone):
    """
    Format phone number to (XXX) XXX-XXXX format

    Args:
        phone: Raw phone number string

    Returns:
        Formatted phone number
    """
    if not phone:
        return ""

    # Remove all non-digits
    import re
    digits = re.sub(r'\D', '', phone)

    # Handle US phone numbers (10 digits)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    # Handle with country code (11 digits, starting with 1)
    if len(digits) == 11 and digits[0] == '1':
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    # Return as-is if not standard format
    return phone


# ============================================================
# COMPLETENESS SCORING
# ============================================================

def calculate_completeness(contacts):
    """
    Calculate completeness score for extracted contacts

    Args:
        contacts: Dictionary of contact information

    Returns:
        Float between 0 and 1 indicating completeness
    """
    if not contacts:
        return 0.0

    # Define weights for different fields
    field_weights = {
        'phone_numbers': 0.25,
        'email_addresses': 0.25,
        'street_address': 0.15,
        'city': 0.10,
        'state': 0.05,
        'business_name': 0.10,
        'website': 0.10
    }

    score = 0.0

    for field, weight in field_weights.items():
        value = contacts.get(field)

        # Check if field has value
        if value:
            # Handle list fields
            if isinstance(value, list):
                if len(value) > 0:
                    score += weight
            # Handle string fields
            elif isinstance(value, str) and value.strip():
                score += weight

    return score


# ============================================================
# PROGRESS TRACKING
# ============================================================

class ProgressTracker:
    """Simple progress tracker for console output"""

    def __init__(self, total):
        self.total = total
        self.current = 0
        self.start_time = time.time()

    def update(self, status=""):
        """Update progress"""
        self.current += 1
        elapsed = time.time() - self.start_time
        avg_time = elapsed / self.current if self.current > 0 else 0
        remaining = (self.total - self.current) * avg_time

        logger.info(
            f"Progress: {self.current}/{self.total} "
            f"({self.current/self.total*100:.1f}%) "
            f"- Elapsed: {elapsed/60:.1f}m "
            f"- Remaining: {remaining/60:.1f}m "
            f"- {status}"
        )

    def finish(self):
        """Mark as finished"""
        elapsed = time.time() - self.start_time
        logger.info(
            f"Completed {self.total} items in {elapsed/60:.1f} minutes "
            f"({elapsed/self.total:.1f}s per item)"
        )
