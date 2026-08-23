import unittest
from unittest.mock import patch

from modules.search import _build_search_query, _extract_first_valid_url


class TestSearchHelpers(unittest.TestCase):

    def test_build_search_query(self):
        # Only business name
        self.assertEqual(
            _build_search_query("Bob's Burgers", include_contact=False),
            '"Bob\'s Burgers"'
        )

        # Business name and city
        self.assertEqual(
            _build_search_query("Bob's Burgers", city="New York", include_contact=False),
            '"Bob\'s Burgers" "New York"'
        )

        # With contact keywords
        self.assertEqual(
            _build_search_query("Bob's Burgers", include_contact=True),
            '"Bob\'s Burgers" contact OR phone OR email'
        )

        # All together
        self.assertEqual(
            _build_search_query("Bob's Burgers", city="New York", include_contact=True),
            '"Bob\'s Burgers" "New York" contact OR phone OR email'
        )

    @patch('modules.search.is_aggregator')
    def test_extract_first_valid_url(self, mock_is_aggregator):
        results = [
            {'title': 'Yelp', 'href': 'https://yelp.com/biz/bobs-burgers'},  # should be aggregator
            {'title': 'Facebook', 'link': 'https://facebook.com/bobsburgers'},  # link instead of href, should be aggregator
            {'title': 'Bob\'s Burgers', 'href': 'https://bobsburgers.com'},  # Valid!
            {'title': 'Another', 'href': 'https://another.com'}  # Ignored
        ]

        # Define mock behavior for is_aggregator
        def mock_aggregator_check(url):
            if 'yelp' in url or 'facebook' in url:
                return True
            return False

        mock_is_aggregator.side_effect = mock_aggregator_check

        url = _extract_first_valid_url(results, "Bob's Burgers")

        # Assuming normalize_url doesn't drastically change the domain for this test
        # Based on typical implementations, it might add trailing slash or ensure https
        self.assertTrue('bobsburgers.com' in url)

    @patch('modules.search.is_aggregator')
    def test_extract_first_valid_url_no_valid(self, mock_is_aggregator):
        results = [
            {'title': 'Yelp', 'href': 'https://yelp.com/biz/bobs-burgers'},
        ]

        mock_is_aggregator.return_value = True

        url = _extract_first_valid_url(results, "Bob's Burgers")
        self.assertIsNone(url)

    @patch('modules.search.is_aggregator')
    def test_extract_first_valid_url_empty_results(self, mock_is_aggregator):
        url = _extract_first_valid_url([], "Bob's Burgers")
        self.assertIsNone(url)


if __name__ == '__main__':
    unittest.main()
