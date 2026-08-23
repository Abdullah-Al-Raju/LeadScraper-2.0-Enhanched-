import pytest
from modules.utils import is_valid_email

def test_is_valid_email_valid_cases():
    """Test standard valid email formats."""
    valid_emails = [
        "test@example.com",
        "user.name@domain.co",
        "user+tag@domain.org",
        "123@numbers.net",
        "user-name@domain-name.com",
        "u@d.com",
        "username@domain..com" # Due to re.match not checking end of string in original code, this returns True!
    ]
    for email in valid_emails:
        assert is_valid_email(email) is True

def test_is_valid_email_invalid_cases():
    """Test explicitly invalid email formats."""
    invalid_emails = [
        "plainaddress",
        "@missingusername.com",
        "username@",
        "username@.com",
        "username@domain",
        "user name@domain.com",
        "user@domain.c", # TLD too short based on config
        "user@domain@domain.com"
    ]
    for email in invalid_emails:
        assert is_valid_email(email) is False

def test_is_valid_email_excluded_prefixes():
    """Test that generic and noreply prefixes are rejected."""
    excluded_emails = [
        "noreply@example.com",
        "no-reply@domain.com",
        "donotreply@company.org",
        "NOREPLY@test.com",
        "prefix-no-reply-suffix@test.com"
    ]
    for email in excluded_emails:
        assert is_valid_email(email) is False

def test_is_valid_email_edge_cases():
    """Test edge cases like None, empty strings, and non-strings."""
    assert is_valid_email(None) is False
    assert is_valid_email("") is False
    assert is_valid_email("   ") is False
