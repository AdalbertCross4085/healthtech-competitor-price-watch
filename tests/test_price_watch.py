import unittest

from src.price_watch import CatalogCheck, assess_check, price_from_text


class PriceWatchTest(unittest.TestCase):
    def test_lower_competitor_price_requires_staff_review(self):
        check = CatalogCheck("remote cardiology visit", 180.0, "https://competitor.example/visit")

        decision = assess_check(check, "Remote cardiology visit: $149")

        self.assertTrue(decision.notify_staff)
        self.assertIn("appointment estimates", decision.message)
        self.assertEqual(decision.competitor_price, 149.0)

    def test_price_parser_handles_commas(self):
        self.assertEqual(price_from_text("annual plan $1,250"), 1250.0)


if __name__ == "__main__":
    unittest.main()
