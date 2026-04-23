import unittest

from webapp.db import _normalize_price_library_entries


class PriceLibraryNormalizationTests(unittest.TestCase):
    def test_normalize_price_library_entries_deduplicates_and_sorts(self):
        rows = [
            {"name": "Штукатурка стен", "unit": "м2", "price": 700},
            {"name": "", "unit": "м2", "price": 100},
            {"name": "штукатурка стен", "unit": "м2", "price": 750},
            {"name": "Грунтовка", "unit": "м2", "price": 120},
        ]

        normalized = _normalize_price_library_entries(rows)

        self.assertEqual(
            normalized,
            [
                {"name": "Грунтовка", "unit": "м2", "price": "120"},
                {"name": "Штукатурка стен", "unit": "м2", "price": "700"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
