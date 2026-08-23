import pytest
from unittest.mock import MagicMock, patch
from modules.sheets import get_unprocessed_rows

def test_get_unprocessed_rows_exception():
    """
    Test that get_unprocessed_rows returns an empty list when an exception
    is raised during sheet extraction.
    """
    # Create a mock sheet object
    mock_sheet = MagicMock()

    # Mock the worksheet method to return a mock worksheet
    mock_worksheet = MagicMock()
    mock_sheet.worksheet.return_value = mock_worksheet

    # Make get_all_records raise an exception
    mock_worksheet.get_all_records.side_effect = Exception("Simulated API Error")

    # We patch the logger to avoid spamming test output, and to verify it was called
    with patch("modules.sheets.logger.error") as mock_logger_error:
        # Call the function
        result = get_unprocessed_rows(mock_sheet)

        # Verify the result is an empty list
        assert result == []

        # Verify the logger was called with the error
        mock_logger_error.assert_called_once()
        assert "Error reading input rows: Simulated API Error" in mock_logger_error.call_args[0][0]
