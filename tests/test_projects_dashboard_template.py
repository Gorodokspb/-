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
        self.assertIn("flex-wrap: nowrap;", css)
        self.assertIn("justify-content: center;", css)

    def test_sidebar_omits_sync_status_and_completed_projects(self):
        template = PROJECTS_TEMPLATE.read_text(encoding="utf-8")

        self.assertNotIn("Синхронизация OK", template)
        self.assertIn('project.status != "Завершен"', template)
        self.assertNotIn("projects[:6]", template)

    def test_topbar_uses_logo_slot_instead_of_text_brand(self):
        template = PROJECTS_TEMPLATE.read_text(encoding="utf-8")
        header = template.split('<header class="topbar-card topbar-card-projects topbar-card-classic">', 1)[1]
        topbar_head = header.split('<div class="topbar-meta projects-topbar-actions">', 1)[0]

        self.assertIn("topbar-logo-slot", topbar_head)
        self.assertIn("/static/img/crm198-logo.jpg", topbar_head)
        self.assertIn("CRM198.ru", topbar_head)
        self.assertNotIn("Dekorartstroy CRM", topbar_head)
        self.assertNotIn("<strong>Объекты и сметы</strong>", topbar_head)

    def test_finance_dashboard_replaces_metric_cards(self):
        template = PROJECTS_TEMPLATE.read_text(encoding="utf-8")
        css = APP_CSS.read_text(encoding="utf-8")

        self.assertIn("finance-dashboard-strip", template)
        self.assertIn("За сегодня", template)
        self.assertIn("За месяц", template)
        self.assertIn("Задолженность заказчиков", template)
        self.assertIn("finance.today.work_done", template)
        self.assertIn("finance.month.work_done", template)
        self.assertIn("finance.customer_debt", template)
        self.assertNotIn("stats-grid stats-grid-v2 stats-grid-compact", template)
        self.assertNotIn("counts.projects_total", template)
        self.assertIn(".finance-dashboard-strip", css)
        self.assertIn(".finance-card", css)


if __name__ == "__main__":
    unittest.main()
