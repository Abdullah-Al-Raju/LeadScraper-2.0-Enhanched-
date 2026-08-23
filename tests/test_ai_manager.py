import unittest
import sys
import os

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.ai_manager import AIManager

class TestAIManagerInitialization(unittest.TestCase):
    def test_basic_initialization(self):
        """Test AIManager initialization with valid parameters"""
        api_key = "test_api_key"
        models = ["model1", "model2"]
        base_url = "https://api.test.com/v1"

        manager = AIManager(api_key, models, base_url)

        # Verify passed arguments are assigned correctly
        self.assertEqual(manager.api_key, api_key)
        self.assertEqual(manager.models, models)
        self.assertEqual(manager.base_url, base_url)

        # Verify default properties
        self.assertEqual(manager.current_index, 0)
        self.assertEqual(manager.failed_models, {})
        self.assertEqual(manager.cooldown_period, 60)

    def test_initialization_with_empty_models(self):
        """Test AIManager initialization with empty models list"""
        manager = AIManager("key", [], "url")
        self.assertEqual(manager.models, [])
        self.assertEqual(manager.current_index, 0)

    def test_initialization_with_none_values(self):
        """Test AIManager initialization with None values to ensure it handles them without errors"""
        manager = AIManager(None, None, None)
        self.assertIsNone(manager.api_key)
        self.assertIsNone(manager.models)
        self.assertIsNone(manager.base_url)
        self.assertEqual(manager.current_index, 0)

if __name__ == '__main__':
    unittest.main()
