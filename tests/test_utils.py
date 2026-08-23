from modules.utils import normalize_url


def test_normalize_url_empty():
    """Test with empty or None input"""
    assert normalize_url("") == ""
    assert normalize_url(None) == ""


def test_normalize_url_with_http():
    """Test URL that already has http scheme"""
    assert normalize_url("http://example.com") == "http://example.com"


def test_normalize_url_with_https():
    """Test URL that already has https scheme"""
    assert normalize_url("https://example.com") == "https://example.com"


def test_normalize_url_without_scheme():
    """Test URL without a scheme"""
    assert normalize_url("example.com") == "https://example.com"


def test_normalize_url_with_trailing_slash():
    """Test URL with a trailing slash"""
    assert normalize_url("https://example.com/") == "https://example.com"
    assert normalize_url("example.com/") == "https://example.com"


def test_normalize_url_with_whitespace():
    """Test URL with leading or trailing whitespace"""
    assert normalize_url("  https://example.com  ") == "https://example.com"
    assert normalize_url("  example.com  ") == "https://example.com"


def test_normalize_url_non_string():
    """Test non-string inputs"""
    # It should convert non-strings to strings and normalize
    assert normalize_url(12345) == "https://12345"


def test_normalize_url_ftp():
    """Test with non-http schemes to see behavior"""
    # The current implementation will prepend https:// to ftp://,
    # or if we change it to allow any scheme we would test that.
    # For now, following the specific prompt logic:
    # `if not url.startswith('http'): url = 'https://' + url`
    assert normalize_url("ftp://example.com") == "https://ftp://example.com"
