import pytest
from modules.utils import get_domain

class TestGetDomain:
    """Test suite for the get_domain utility function."""

    def test_basic_domains(self):
        """Test simple domains with and without scheme."""
        assert get_domain("https://example.com") == "example.com"
        assert get_domain("http://test.org") == "test.org"

    def test_www_removal(self):
        """Test that 'www.' prefix is properly removed."""
        assert get_domain("https://www.example.com") == "example.com"
        assert get_domain("http://www.test.org") == "test.org"

    def test_complex_urls(self):
        """Test URLs with paths, queries, and fragments."""
        assert get_domain("https://example.com/path/to/page?q=1#top") == "example.com"
        assert get_domain("https://www.example.com/path/to/page") == "example.com"

    def test_subdomains(self):
        """Test URLs with subdomains other than www."""
        assert get_domain("https://blog.example.com") == "blog.example.com"
        assert get_domain("http://api.staging.example.com") == "api.staging.example.com"

    def test_ports(self):
        """Test URLs containing port numbers."""
        assert get_domain("https://example.com:8080/path") == "example.com:8080"
        assert get_domain("http://www.example.com:3000") == "example.com:3000"

    def test_empty_and_none(self):
        """Test empty strings and None values."""
        assert get_domain("") == ""
        assert get_domain(None) == ""

    def test_no_scheme(self):
        """Test URLs missing the http/https scheme.
        urlparse handles these differently depending on the input,
        but let's see how the function handles it currently.
        If it's just 'example.com', urlparse might parse it as a path.
        """
        assert get_domain("example.com") == ""

    def test_invalid_types_exception_handling(self):
        """Test that invalid types trigger the except block and return empty string."""
        assert get_domain(123) == ""
        assert get_domain(["https://example.com"]) == ""
        assert get_domain({"url": "https://example.com"}) == ""
