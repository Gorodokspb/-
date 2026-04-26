import unittest
from decimal import Decimal

import import_catalog_items


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []
        self.executemany_calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.executed.append((str(sql), params))

    def executemany(self, sql, params):
        self.executemany_calls.append((str(sql), list(params)))

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows=None):
        self.cursor_obj = FakeCursor(rows=rows)
        self.commits = 0

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1


class ImportCatalogItemsTests(unittest.TestCase):
    def test_normalize_rows_skips_empty_names_and_deduplicates_last_value(self):
        rows = import_catalog_items.normalize_catalog_rows(
            [
                {"Наименование работ": " Штукатурка стен ", "ед измерения": "м2", "цена за единицу": "1 200,50"},
                {"Наименование работ": "", "ед измерения": "м2", "цена за единицу": "100"},
                {"Наименование работ": "Штукатурка стен", "ед измерения": "м²", "цена за единицу": 1300},
                {"Наименование работ": "Грунтовка", "ед измерения": None, "цена за единицу": None},
            ]
        )

        self.assertEqual(
            rows,
            [
                {"name": "Штукатурка стен", "unit": "м²", "price": Decimal("1300"), "category": "Стены"},
                {"name": "Грунтовка", "unit": "", "price": None, "category": "Прочее"},
            ],
        )

    def test_resolve_excel_columns_accepts_existing_price_list_aliases(self):
        columns = import_catalog_items.resolve_excel_columns(
            ["Наименование работ", "Ед. изм.", "Цена за м2"]
        )

        self.assertEqual(
            columns,
            {
                import_catalog_items.NAME_COLUMN: "Наименование работ",
                import_catalog_items.UNIT_COLUMN: "Ед. изм.",
                import_catalog_items.PRICE_COLUMN: "Цена за м2",
            },
        )

    def test_upsert_catalog_items_counts_inserted_and_updated(self):
        conn = FakeConnection(rows=[("Штукатурка стен",)])
        items = [
            {"name": "Штукатурка стен", "unit": "м²", "price": Decimal("1300")},
            {"name": "Грунтовка", "unit": "м²", "price": Decimal("120")},
        ]

        result = import_catalog_items.upsert_catalog_items(conn, items)

        self.assertEqual(result.inserted, 1)
        self.assertEqual(result.updated, 1)
        self.assertEqual(conn.commits, 1)
        self.assertEqual(
            conn.cursor_obj.executemany_calls[0][1],
            [("Штукатурка стен", "м²", Decimal("1300"), "Стены"), ("Грунтовка", "м²", Decimal("120"), "Прочее")],
        )
        self.assertIn("ON CONFLICT (name) DO UPDATE", conn.cursor_obj.executemany_calls[0][0])


if __name__ == "__main__":
    unittest.main()
