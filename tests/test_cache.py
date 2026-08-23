import unittest
import json
from unittest.mock import patch, mock_open
import tempfile
import os

from modules.cache import ProgressCache


class TestProgressCache(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory and file for safe testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = os.path.join(
            self.temp_dir.name, 'test_progress.json')
        self.cache = ProgressCache(cache_file=self.cache_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_creates_directory(self):
        """Test that __init__ creates the parent directory if it doesn't exist."""
        # Use a sub-directory in the temp dir to ensure it doesn't exist yet
        sub_dir = os.path.join(self.temp_dir.name, 'sub_dir')
        new_cache_file = os.path.join(sub_dir, 'new_cache.json')

        self.assertFalse(os.path.exists(sub_dir))
        ProgressCache(cache_file=new_cache_file)
        self.assertTrue(os.path.exists(sub_dir))

    def test_save_happy_path(self):
        """Test successfully saving data to the cache."""
        test_data = {"completed": 5, "last_row": 10}
        self.cache.save(test_data.copy())

        # Verify file exists
        self.assertTrue(os.path.exists(self.cache_file))

        # Read the file to verify contents
        with open(self.cache_file, 'r') as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data["completed"], 5)
        self.assertEqual(saved_data["last_row"], 10)
        self.assertIn("last_updated", saved_data)

    @patch('modules.cache.logger')
    def test_save_error_path(self, mock_logger):
        """Test error handling when saving data fails."""
        test_data = {"completed": 5}

        # Mock open to raise an IOError when trying to write
        mock_open_func = mock_open()
        mock_open_func.side_effect = IOError("Permission denied")

        with patch('builtins.open', mock_open_func):
            self.cache.save(test_data)

        # Verify logger.error was called with a message containing the
        # exception
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        self.assertIn("Failed to save cache", error_msg)
        self.assertIn("Permission denied", error_msg)

    def test_load_happy_path(self):
        """Test successfully loading data from the cache."""
        # Setup: Save some data first
        test_data = {"completed": 5, "completed_rows": [1, 2, 3]}
        with open(self.cache_file, 'w') as f:
            json.dump(test_data, f)

        loaded_data = self.cache.load()
        self.assertEqual(loaded_data["completed"], 5)
        self.assertEqual(loaded_data["completed_rows"], [1, 2, 3])

    def test_load_file_not_found(self):
        """Test loading when the cache file does not exist."""
        # Ensure file does not exist
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

        loaded_data = self.cache.load()
        self.assertIsNone(loaded_data)

    @patch('modules.cache.logger')
    def test_load_error_path(self, mock_logger):
        """Test error handling when loading data fails."""
        # Setup: create file so exists() check passes
        with open(self.cache_file, 'w') as f:
            f.write("invalid json")

        # The built-in json.load will raise json.decoder.JSONDecodeError
        loaded_data = self.cache.load()

        self.assertIsNone(loaded_data)
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        self.assertIn("Failed to load progress", error_msg)

    def test_clear_happy_path(self):
        """Test successfully clearing the cache file."""
        # Setup: create file
        with open(self.cache_file, 'w') as f:
            f.write("{}")

        self.assertTrue(os.path.exists(self.cache_file))
        self.cache.clear()
        self.assertFalse(os.path.exists(self.cache_file))

    def test_clear_file_not_found(self):
        """Test clearing when file doesn't exist (should not error)."""
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

        # Should complete without error
        self.cache.clear()

    @patch('modules.cache.logger')
    @patch('pathlib.Path.unlink')
    def test_clear_error_path(self, mock_unlink, mock_logger):
        """Test error handling when clearing fails."""
        # Setup: create file so exists() check passes
        with open(self.cache_file, 'w') as f:
            f.write("{}")

        mock_unlink.side_effect = PermissionError("Cannot delete")

        self.cache.clear()

        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        self.assertIn("Failed to clear cache", error_msg)
        self.assertIn("Cannot delete", error_msg)

    def test_exists(self):
        """Test checking if cache exists."""
        self.assertFalse(self.cache.exists())

        with open(self.cache_file, 'w') as f:
            f.write("{}")

        self.assertTrue(self.cache.exists())

    def test_get_completed_rows(self):
        """Test getting completed rows."""
        # Empty case
        self.assertEqual(self.cache.get_completed_rows(), [])

        # Populated case
        test_data = {"completed_rows": [1, 2, 5]}
        with open(self.cache_file, 'w') as f:
            json.dump(test_data, f)

        self.assertEqual(self.cache.get_completed_rows(), [1, 2, 5])

    def test_add_completed_row(self):
        """Test adding a completed row."""
        # Initially empty
        self.cache.add_completed_row(1)

        loaded = self.cache.load()
        self.assertEqual(loaded["completed_rows"], [1])
        self.assertEqual(loaded["last_row"], 1)
        self.assertEqual(loaded["completed"], 1)

        # Add another row
        self.cache.add_completed_row(5)

        loaded = self.cache.load()
        self.assertEqual(loaded["completed_rows"], [1, 5])
        self.assertEqual(loaded["last_row"], 5)
        self.assertEqual(loaded["completed"], 2)

        # Add duplicate row (should not duplicate in list)
        self.cache.add_completed_row(1)

        loaded = self.cache.load()
        self.assertEqual(loaded["completed_rows"], [1, 5])


if __name__ == '__main__':
    unittest.main()
