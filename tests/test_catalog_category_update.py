import unittest
from pathlib import Path

import import_catalog_items
from import_catalog_items import CATEGORY_OPTIONS, normalize_category, categorize_catalog_item


class NormalizeCategoryPreservesValidTests(unittest.TestCase):
    def test_valid_category_potolok_preserved(self):
        self.assertEqual(normalize_category("Потолок", "штукатурка стен"), "Потолок")

    def test_valid_category_steny_preserved(self):
        self.assertEqual(normalize_category("Стены", "шпаклевка потолка"), "Стены")

    def test_valid_category_pol_preserved(self):
        self.assertEqual(normalize_category("Пол", "демонтаж стен"), "Пол")

    def test_valid_category_demontazh_preserved(self):
        self.assertEqual(normalize_category("Демонтаж/Монтаж", "укладка ламината"), "Демонтаж/Монтаж")

    def test_valid_category_santehnika_preserved(self):
        self.assertEqual(normalize_category("Сантехнические работы", "покраска стен"), "Сантехнические работы")

    def test_valid_category_elektro_preserved(self):
        self.assertEqual(normalize_category("Электромонтажные работы", "грунтовка пола"), "Электромонтажные работы")

    def test_valid_category_proche_preserved(self):
        self.assertEqual(normalize_category("Прочее", "шпаклевка потолка"), "Прочее")

    def test_empty_category_fallback_to_autocategorize(self):
        result = normalize_category("", "шпаклевка потолка")
        self.assertEqual(result, "Потолок")

    def test_none_category_fallback_to_autocategorize(self):
        result = normalize_category(None, "укладка ламината")
        self.assertEqual(result, "Пол")

    def test_whitespace_category_fallback(self):
        result = normalize_category("   ", "замена труб водоснабжения")
        self.assertEqual(result, "Сантехнические работы")

    def test_invalid_category_fallback_to_autocategorize(self):
        result = normalize_category("Несуществующая", "покраска стен")
        self.assertEqual(result, "Стены")

    def test_empty_category_empty_name_gives_proche(self):
        result = normalize_category("", "")
        self.assertEqual(result, "Прочее")


class UpdateCatalogItemCategoryTests(unittest.TestCase):
    def test_update_preserves_valid_category_potolok(self):
        from webapp.db import update_catalog_item
        src = Path("webapp/db.py").read_text(encoding="utf-8")
        self.assertIn("CATEGORY_OPTIONS", src)
        self.assertIn("if normalized_category not in CATEGORY_OPTIONS", src)

    def test_update_preserves_valid_category_steny(self):
        from webapp.db import update_catalog_item
        import inspect
        src = inspect.getsource(update_catalog_item)
        self.assertIn("CATEGORY_OPTIONS", src)
        self.assertIn("normalized_category not in CATEGORY_OPTIONS", src)


class CatalogTemplateFormFixTests(unittest.TestCase):
    def test_template_no_form_inside_tr(self):
        template = Path("webapp/templates/catalog.html").read_text(encoding="utf-8")
        self.assertNotIn('<form method="post" action="/catalog/items/{{ item.id }}">', template,
                         "Template should not have <form> inside <tr> for row edit")

    def test_template_has_row_save_button(self):
        template = Path("webapp/templates/catalog.html").read_text(encoding="utf-8")
        self.assertIn("catalog-row-save", template)

    def test_template_has_data_item_id_on_tr(self):
        template = Path("webapp/templates/catalog.html").read_text(encoding="utf-8")
        self.assertIn('data-item-id="{{ item.id }}"', template)

    def test_template_has_category_select(self):
        template = Path("webapp/templates/catalog.html").read_text(encoding="utf-8")
        self.assertIn('name="category"', template)
        self.assertIn('data-bulk-category-select', template)


class CatalogJsPerRowSaveTests(unittest.TestCase):
    def test_js_has_per_row_save_handler(self):
        script = Path("webapp/static/app.js").read_text(encoding="utf-8")
        self.assertIn("catalog-row-save", script)
        self.assertIn("X-Requested-With", script)

    def test_js_sends_category_in_form_data(self):
        script = Path("webapp/static/app.js").read_text(encoding="utf-8")
        self.assertIn('formData.append("category"', script)
        self.assertIn('formData.append("name"', script)
        self.assertIn('formData.append("unit"', script)
        self.assertIn('formData.append("price"', script)

    def test_js_bulk_update_still_present(self):
        script = Path("webapp/static/app.js").read_text(encoding="utf-8")
        self.assertIn("catalogCategoryChanges", script)
        self.assertIn("bulk-update-categories", script)


class CatalogRouteAjaxTests(unittest.TestCase):
    def test_catalog_item_update_returns_json_for_ajax(self):
        main = Path("webapp/main.py").read_text(encoding="utf-8")
        self.assertIn("x-requested-with", main.lower())
        self.assertIn("XMLHttpRequest", main)
        self.assertIn('"ok"', main)


if __name__ == "__main__":
    unittest.main()