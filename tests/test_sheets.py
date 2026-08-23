import pytest
from unittest.mock import patch

from modules.sheets import is_duplicate
import modules.sheets as sheets
from modules.utils import hash_business

@pytest.fixture(autouse=True)
def reset_processed_hashes():
    """Reset the global _processed_hashes set before and after each test."""
    original_hashes = sheets._processed_hashes.copy()
    sheets._processed_hashes.clear()
    yield
    sheets._processed_hashes.clear()
    sheets._processed_hashes.update(original_hashes)


def test_is_duplicate_new_business():
    """Test that a new business is not flagged as a duplicate."""
    business_name = "Test Business"
    city = "Test City"

    # First time should not be a duplicate
    result = is_duplicate(business_name, city)

    assert result is False
    assert hash_business(business_name, city) in sheets._processed_hashes


@patch("modules.sheets.logger.warning")
def test_is_duplicate_existing_business(mock_logger_warning):
    """Test that an existing business is flagged as a duplicate."""
    business_name = "Test Business"
    city = "Test City"

    # Add it the first time
    is_duplicate(business_name, city)

    # Second time it should be a duplicate
    result = is_duplicate(business_name, city)

    assert result is True
    mock_logger_warning.assert_called_once_with(f"Duplicate detected: {business_name} ({city})")


def test_is_duplicate_case_insensitive():
    """Test that duplicate detection is case insensitive."""
    business_name1 = "Test Business"
    business_name2 = "test business"
    city = "Test City"

    # Add with Title Case
    is_duplicate(business_name1, city)

    # Check with lower case
    result = is_duplicate(business_name2, city)

    assert result is True


def test_is_duplicate_empty_city():
    """Test duplicate detection works when city is empty."""
    business_name = "Test Business"

    # Add with empty city
    result1 = is_duplicate(business_name)
    assert result1 is False

    # Check again with empty city
    result2 = is_duplicate(business_name)
    assert result2 is True


def test_is_duplicate_whitespace():
    """Test that duplicate detection strips whitespace properly."""
    business_name = " Test Business "
    city = " Test City "

    # Add with whitespace
    is_duplicate(business_name, city)

    # Check without whitespace
    result = is_duplicate("Test Business", "Test City")

    assert result is True
