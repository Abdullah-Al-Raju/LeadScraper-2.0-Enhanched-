import unittest
from modules.extractor import _get_category_context


class TestExtractor(unittest.TestCase):
    def test_get_category_context_restaurant(self):
        context = _get_category_context('Cafe')
        self.assertIn("RESTAURANT/FOOD SERVICE", context)
        self.assertIn("Reservation or delivery", context)

    def test_get_category_context_medical(self):
        context = _get_category_context('Dentist')
        self.assertIn("MEDICAL/DENTAL", context)
        self.assertIn("Appointment phone numbers", context)

    def test_get_category_context_auto(self):
        context = _get_category_context('Auto Repair')
        self.assertIn("AUTOMOTIVE/REPAIR", context)
        self.assertIn("Emergency/towing numbers", context)

    def test_get_category_context_retail(self):
        context = _get_category_context('Book Store')
        self.assertIn("RETAIL/SHOP", context)
        self.assertIn("Product categories", context)

    def test_get_category_context_professional(self):
        context = _get_category_context('Law Firm')
        self.assertIn("PROFESSIONAL SERVICES", context)
        self.assertIn("Consultation contact information", context)

    def test_get_category_context_default(self):
        context = _get_category_context('Plumber')
        self.assertIn("This is a Plumber business", context)
        self.assertIn("Extract all relevant contact information", context)

    def test_get_category_context_empty(self):
        self.assertEqual(_get_category_context(''), "")
        self.assertEqual(_get_category_context(None), "")


if __name__ == '__main__':
    unittest.main()
