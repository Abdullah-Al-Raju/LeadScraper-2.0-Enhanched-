import pytest
from unittest.mock import patch

from main import _validate_config

def test_validate_config_all_valid():
    """Test when all configurations are set and valid."""
    with patch('main.config') as mock_config, \
         patch('main.logger') as mock_logger:

        # Mock configuration variables to be true/present
        mock_config.GOOGLE_SHEET_ID = "some_sheet_id"
        mock_config.SERVICE_ACCOUNT_FILE = "some_path.json"
        mock_config.OPENROUTER_API_KEY = "some_api_key"

        result = _validate_config()

        assert result is True
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()

def test_validate_config_missing_sheet_id():
    """Test when GOOGLE_SHEET_ID is missing."""
    with patch('main.config') as mock_config, \
         patch('main.logger') as mock_logger:

        mock_config.GOOGLE_SHEET_ID = ""
        mock_config.SERVICE_ACCOUNT_FILE = "some_path.json"
        mock_config.OPENROUTER_API_KEY = "some_api_key"

        result = _validate_config()

        assert result is False
        mock_logger.error.assert_called_with("GOOGLE_SHEET_ID not set. Please configure in .env file")
        mock_logger.warning.assert_not_called()

def test_validate_config_missing_service_account():
    """Test when SERVICE_ACCOUNT_FILE is missing."""
    with patch('main.config') as mock_config, \
         patch('main.logger') as mock_logger:

        mock_config.GOOGLE_SHEET_ID = "some_sheet_id"
        mock_config.SERVICE_ACCOUNT_FILE = ""
        mock_config.OPENROUTER_API_KEY = "some_api_key"

        result = _validate_config()

        assert result is False
        mock_logger.error.assert_called_with("SERVICE_ACCOUNT_FILE not set. Please configure in .env file")
        mock_logger.warning.assert_not_called()

def test_validate_config_missing_api_key():
    """Test when OPENROUTER_API_KEY is missing. It should still be valid."""
    with patch('main.config') as mock_config, \
         patch('main.logger') as mock_logger:

        mock_config.GOOGLE_SHEET_ID = "some_sheet_id"
        mock_config.SERVICE_ACCOUNT_FILE = "some_path.json"
        mock_config.OPENROUTER_API_KEY = ""

        result = _validate_config()

        assert result is True
        mock_logger.error.assert_not_called()

        # Verify warnings were called
        assert mock_logger.warning.call_count == 2
        mock_logger.warning.assert_any_call("OPENROUTER_API_KEY not set. AI extraction will be disabled.")
        mock_logger.warning.assert_any_call("The tool will still work with regex fallback.")

def test_validate_config_multiple_missing():
    """Test when multiple required configs are missing."""
    with patch('main.config') as mock_config, \
         patch('main.logger') as mock_logger:

        mock_config.GOOGLE_SHEET_ID = ""
        mock_config.SERVICE_ACCOUNT_FILE = ""
        mock_config.OPENROUTER_API_KEY = "some_api_key"

        result = _validate_config()

        assert result is False
        assert mock_logger.error.call_count == 2
        mock_logger.error.assert_any_call("GOOGLE_SHEET_ID not set. Please configure in .env file")
        mock_logger.error.assert_any_call("SERVICE_ACCOUNT_FILE not set. Please configure in .env file")
