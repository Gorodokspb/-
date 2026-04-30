from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASE_TEMPLATE = ROOT / "webapp" / "templates" / "base.html"
LOGIN_TEMPLATE = ROOT / "webapp" / "templates" / "login.html"
MAIN_PY = ROOT / "webapp" / "main.py"
DB_PY = ROOT / "webapp" / "db.py"
APP_JS = ROOT / "webapp" / "static" / "app.js"
APP_CSS = ROOT / "webapp" / "static" / "app.css"


class NavigationAndCrudTemplateTests(unittest.TestCase):
    def test_global_navigation_uses_expected_labels_and_routes(self):
        template = BASE_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('href="/projects">Проекты</a>', template)
        self.assertIn('href="/estimates">Смета</a>', template)
        self.assertIn('href="/catalog">Прайс-лист</a>', template)
        self.assertIn('href="/calculator">Калькулятор</a>', template)
        self.assertIn('href="/finance">Финансы</a>', template)
        self.assertNotIn('>Справочник</a>', template)
        self.assertNotIn('href="/projects">Сметы</a>', template)

    def test_login_button_text_is_short(self):
        template = LOGIN_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('>Войти</button>', template)
        self.assertNotIn('Войти в CRM', template)

    def test_main_has_navigation_redirects_and_project_delete_route(self):
        main = MAIN_PY.read_text(encoding="utf-8")

        self.assertIn('@app.get("/estimates")', main)
        self.assertIn('@app.get("/calculator")', main)
        self.assertIn('@app.post("/projects/{project_id}/delete")', main)
        self.assertIn('return RedirectResponse(url=f"/projects/{project_id}/estimate", status_code=status.HTTP_302_FOUND)', main)
        self.assertIn('return RedirectResponse(url=f"/projects/{project_id}/estimate?tool=calculator", status_code=status.HTTP_302_FOUND)', main)

    def test_database_helpers_cover_project_delete_cleanup(self):
        db = DB_PY.read_text(encoding="utf-8")

        self.assertIn('def delete_project(', db)
        self.assertIn('UPDATE transactions SET project_id = NULL WHERE project_id = %s', db)
        self.assertIn('DELETE FROM documents WHERE project_id = %s', db)
        self.assertIn('DELETE FROM project_events WHERE project_id = %s', db)
        self.assertIn('DELETE FROM projects WHERE id = %s', db)
        self.assertIn('DELETE FROM smeta_drafts WHERE id = ANY(%s)', db)

    def test_modal_opening_supports_centered_quick_action_dialog(self):
        css = APP_CSS.read_text(encoding="utf-8")
        js = APP_JS.read_text(encoding="utf-8")
        template = BASE_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('class="catalog-modal modal-backdrop quick-action-modal"', template)
        self.assertIn('window.scrollTo({ top: 0, behavior: "smooth" });', js)
        self.assertIn('.modal-backdrop,', css)
        self.assertIn('.quick-action-modal {', css)
        self.assertIn('place-items: center;', css)


if __name__ == "__main__":
    unittest.main()
