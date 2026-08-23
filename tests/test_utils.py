import pytest
from modules.utils import format_phone

def test_format_phone_empty_or_none():
    """Test handling of empty or None inputs."""
    assert format_phone(None) == ""
    assert format_phone("") == ""
    assert format_phone(False) == ""

def test_format_phone_basic_stripping():
    """Test basic removal of non-digit and non-plus characters."""
    assert format_phone("123-456-7890") == "1234567890"
    assert format_phone("(123) 456 7890") == "1234567890"
    assert format_phone("123.456.7890") == "1234567890"
    assert format_phone("call me at 12345") == "12345"

def test_format_phone_with_plus():
    """Test that the plus sign (+) is preserved."""
    assert format_phone("+1-123-456-7890") == "+11234567890"
    assert format_phone("+44 (0) 1234 567 890") == "+4401234567890"
    assert format_phone("my number is +91 98765 43210") == "+919876543210"

def test_format_phone_non_string_input():
    """Test with non-string inputs that can be converted to strings."""
    assert format_phone(1234567890) == "1234567890"
    # Even if passing a float, the logic strips non-digit characters.
    # str(123.45) is "123.45" and '.' is stripped.
    assert format_phone(123.45) == "12345"
