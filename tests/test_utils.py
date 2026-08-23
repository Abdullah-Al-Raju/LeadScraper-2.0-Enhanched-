import unittest
from modules.utils import clean_text

class TestUtils(unittest.TestCase):

    def test_clean_text_empty_input(self):
        """Test with empty strings, None, and empty types."""
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text([]), "")

    def test_clean_text_whitespace(self):
        """Test extra whitespace removal including leading/trailing, tabs, and newlines."""
        self.assertEqual(clean_text("  hello   world  "), "hello world")
        self.assertEqual(clean_text("hello\tworld"), "hello world")
        self.assertEqual(clean_text("hello\nworld"), "hello world")
        self.assertEqual(clean_text("   \n\t   "), "")

    def test_clean_text_unicode_artifacts(self):
        """Test removal of unicode artifacts."""
        self.assertEqual(clean_text("hello\xa0world"), "hello world")
        self.assertEqual(clean_text("hello\u200bworld"), "helloworld")
        self.assertEqual(clean_text("hello\xa0\u200bworld"), "hello world")

    def test_clean_text_normal_string(self):
        """Test with normal text that doesn't need cleaning."""
        self.assertEqual(clean_text("hello world"), "hello world")
        self.assertEqual(clean_text("A normal sentence."), "A normal sentence.")

if __name__ == '__main__':
    unittest.main()
