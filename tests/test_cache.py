import unittest
from unittest.mock import patch

from modules.cache import ProgressCache


class TestProgressCache(unittest.TestCase):

    @patch('modules.cache.ProgressCache.load')
    def test_get_completed_rows_when_load_returns_none(self, mock_load):
        # Arrange
        mock_load.return_value = None
        cache = ProgressCache(cache_file='dummy_cache.json')

        # Act
        result = cache.get_completed_rows()

        # Assert
        self.assertEqual(result, [])
        mock_load.assert_called_once()

    @patch('modules.cache.ProgressCache.load')
    def test_get_completed_rows_when_no_completed_rows_key(self, mock_load):
        # Arrange
        mock_load.return_value = {'other_key': 'value'}
        cache = ProgressCache(cache_file='dummy_cache.json')

        # Act
        result = cache.get_completed_rows()

        # Assert
        self.assertEqual(result, [])
        mock_load.assert_called_once()

    @patch('modules.cache.ProgressCache.load')
    def test_get_completed_rows_with_completed_rows(self, mock_load):
        # Arrange
        expected_rows = [1, 2, 3]
        mock_load.return_value = {'completed_rows': expected_rows}
        cache = ProgressCache(cache_file='dummy_cache.json')

        # Act
        result = cache.get_completed_rows()

        # Assert
        self.assertEqual(result, expected_rows)
        mock_load.assert_called_once()


if __name__ == '__main__':
    unittest.main()
