import unittest
from decimal import Decimal
from pathlib import Path

import import_catalog_items


class CatalogManagementTests(unittest.TestCase):
    def test_auto_category_priority_and_keywords(self):
        self.assertEqual(import_catalog_items.categorize_catalog_item("Демонтаж потолка"), "Демонтаж/Монтаж")
        self.assertEqual(import_catalog_items.categorize_catalog_item("Прокладка кабеля для люстры"), "Электромонтажные работы")
        self.assertEqual(import_catalog_items.categorize_catalog_item("Замена труб водоснабжения"), "Сантехнические работы")
        self.assertEqual(import_catalog_items.categorize_catalog_item("Укладка ламината"), "Пол")
        self.assertEqual(import_catalog_items.categorize_catalog_item("Покраска потолка"), "Потолок")
        self.assertEqual(import_catalog_items.categorize_catalog_item("Шпаклевка стены"), "Стены")
        self.assertEqual(import_catalog_items.categorize_catalog_item("Вывоз мусора"), "Прочее")

    def test_normalize_rows_adds_category_and_accepts_excel_category(self):
        rows = import_catalog_items.normalize_catalog_rows(
            [
                {"Наименование работ": "Кабель ВВГ", "ед измерения": "м", "цена за единицу": "100"},
                {"Наименование работ": "Ламинат на стену", "ед измерения": "м2", "цена за единицу": "900", "category": "Стены"},
            ]
        )

        self.assertEqual(rows[0]["category"], "Электромонтажные работы")
        self.assertEqual(rows[1]["category"], "Стены")

    def test_compare_catalog_import_splits_new_conflicts_and_unchanged(self):
        existing = [
            {"id": 1, "name": "Штукатурка", "unit": "м2", "price": 700, "category": "Стены"},
            {"id": 2, "name": "Грунтовка", "unit": "м2", "price": 120, "category": "Стены"},
        ]
        incoming = [
            {"name": "Штукатурка", "unit": "м2", "price": Decimal("750"), "category": "Стены"},
            {"name": "Грунтовка", "unit": "м2", "price": Decimal("120"), "category": "Стены"},
            {"name": "Монтаж стен", "unit": "м2", "price": Decimal("3200"), "category": "Демонтаж/Монтаж"},
        ]

        comparison = import_catalog_items.compare_catalog_import(existing, incoming)

        self.assertEqual([item["name"] for item in comparison.new_items], ["Монтаж стен"])
        self.assertEqual([item["name"] for item in comparison.unchanged_items], ["Грунтовка"])
        self.assertEqual(len(comparison.conflicts), 1)
        self.assertEqual(comparison.conflicts[0]["name"], "Штукатурка")
        self.assertEqual(comparison.conflicts[0]["old"]["price"], 700)
        self.assertEqual(comparison.conflicts[0]["new"]["price"], Decimal("750"))

    def test_catalog_template_contains_required_controls(self):
        template = Path("webapp/templates/catalog.html").read_text(encoding="utf-8")

        self.assertIn("Добавить работу", template)
        self.assertIn("catalogSearch", template)
        self.assertIn("catalog-category-heading", template)
        self.assertIn("Копировать", template)
        self.assertIn("/catalog/upload", template)
        self.assertIn("<select", template)


if __name__ == "__main__":
    unittest.main()
