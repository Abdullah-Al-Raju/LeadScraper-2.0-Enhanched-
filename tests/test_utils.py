import pytest
from modules.utils import hash_business
import re

def get_expected_hash(name, city=""):
    name_clean = re.sub(r'[^a-z0-9]', '', str(name).lower())
    city_clean = re.sub(r'[^a-z0-9]', '', str(city).lower())
    return f"{name_clean}_{city_clean}"

def test_hash_business_basic():
    """Test basic usage with name and city."""
    name = "Pizza Hut"
    city = "Dhaka"
    assert hash_business(name, city) == get_expected_hash(name, city)
    assert hash_business(name, city) == "pizzahut_dhaka"

def test_hash_business_default_city():
    """Test usage when city is omitted."""
    name = "Pizza Hut"
    assert hash_business(name) == get_expected_hash(name, "")
    assert hash_business(name) == "pizzahut_"

def test_hash_business_case_insensitivity():
    """Test that hashing is case insensitive."""
    assert hash_business("PIZZA HUT", "DHAKA") == hash_business("pizza hut", "dhaka")
    assert hash_business("PiZzA hUt") == hash_business("pizza hut")

def test_hash_business_whitespace_and_special_chars():
    """Test that leading, trailing whitespace and special characters are stripped."""
    assert hash_business("  Pizza Hut !@#$ ", " Dhaka 123 ") == hash_business("Pizza Hut", "Dhaka 123")
    assert hash_business("  Pizza Hut !@#$ ", " Dhaka 123 ") == "pizzahut_dhaka123"

def test_hash_business_empty_strings():
    """Test hashing with empty strings."""
    assert hash_business("", "") == get_expected_hash("", "")
    assert hash_business("", "") == "_"

def test_hash_business_none_inputs():
    """Test hashing with None values (which get stringified by str())."""
    assert hash_business(None, None) == "none_none"

def test_hash_business_different_inputs():
    """Test that different inputs produce different hashes."""
    assert hash_business("Pizza Hut", "Dhaka") != hash_business("Domino's", "Dhaka")
    assert hash_business("Pizza Hut", "Dhaka") != hash_business("Pizza Hut", "Chittagong")

def test_hash_business_consistency():
    """Test that the same input always produces the same output (deterministic)."""
    hash1 = hash_business("Starbucks", "New York")
    hash2 = hash_business("Starbucks", "New York")
    assert hash1 == hash2
