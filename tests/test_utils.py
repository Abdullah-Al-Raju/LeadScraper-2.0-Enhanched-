import unittest
from unittest.mock import patch, MagicMock
import time
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.utils import ProgressTracker

class TestProgressTracker(unittest.TestCase):

    @patch('modules.utils.logger')
    @patch('time.time')
    def test_finish_normal(self, mock_time, mock_logger):
        # Set up mock times: start at 100.0, finish at 160.0 (60 seconds elapsed)
        mock_time.side_effect = [100.0, 160.0]

        tracker = ProgressTracker(total=10)
        # tracker.start_time is set to 100.0

        tracker.finish()
        # time.time() returns 160.0, elapsed = 60.0
        # time_per_item = 60.0 / 10 = 6.0

        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]

        self.assertIn("Completed 10 items", log_message)
        self.assertIn("in 1.0 minutes", log_message) # 60s / 60 = 1.0
        self.assertIn("(6.0s per item)", log_message)

    @patch('modules.utils.logger')
    @patch('time.time')
    def test_finish_zero_total(self, mock_time, mock_logger):
        # Test edge case where total is 0
        mock_time.side_effect = [100.0, 160.0]

        tracker = ProgressTracker(total=0)

        # This would raise ZeroDivisionError before our fix
        tracker.finish()

        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]

        self.assertIn("Completed 0 items", log_message)
        self.assertIn("in 1.0 minutes", log_message)
        self.assertIn("(0.0s per item)", log_message)

    @patch('modules.utils.logger')
    @patch('time.time')
    def test_update(self, mock_time, mock_logger):
        mock_time.side_effect = [100.0, 160.0]

        tracker = ProgressTracker(total=10)
        tracker.update("Working...")

        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]

        self.assertIn("Progress: 1/10", log_message)
        self.assertIn("(10.0%)", log_message)
        self.assertIn("- Elapsed: 1.0m", log_message)
        self.assertIn("- Working...", log_message)

if __name__ == '__main__':
    unittest.main()
