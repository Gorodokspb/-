from pathlib import Path
import unittest


PROJECTS_TEMPLATE = Path(__file__).resolve().parents[1] / "webapp" / "templates" / "projects.html"
APP_CSS = Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.css"


class ProjectsDashboardTemplateTests(unittest.TestCase):
    def test_dashboard_removes_marketing_banner_and_duplicate_focus_panel(self):
        template = PROJECTS_TEMPLATE.read_text(encoding="utf-8")

        self.assertNotIn("classic-hero-card", template)
        self.assertNotIn("Все ключевое по проектам", template)
        self.assertNotIn("Центр управления объектами", template)
        self.assertNotIn("classic-focus-panel", template)
        self.assertNotIn("Быстрые действия", template)

    def test_primary_actions_are_prominent_in_topbar(self):
        template = PROJECTS_TEMPLATE.read_text(encoding="utf-8")
        css = APP_CSS.read_text(encoding="utf-8")

        self.assertIn("projects-topbar-actions", template)
        self.assertIn("topbar-primary-action", template)
        self.assertIn("topbar-finance-action", template)
        self.assertIn("Финансы", template)
        self.assertIn("Прайс-лист", template)
        self.assertIn("Открыть смету", template)
        self.assertIn(".projects-topbar-actions", css)
        self.assertIn(".topbar-primary-action", css)
        self.assertIn(".topbar-finance-action", css)


if __name__ == "__main__":
    unittest.main()
