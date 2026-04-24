import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "webapp" / "templates" / "project_detail.html"
CSS = ROOT / "webapp" / "static" / "app.css"


class ProjectDetailTemplateTests(unittest.TestCase):
    def test_topbar_keeps_only_home_navigation(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        header = template.split('<header class="topbar-card detail-topbar detail-topbar-classic detail-topbar-slim">', 1)[1].split("</header>", 1)[0]

        self.assertIn("На главную", header)
        self.assertIn('href="/projects"', header)
        self.assertNotIn("Проект: {{ project.project_name }}", header)
        self.assertNotIn("Назад к проектам", header)
        self.assertNotIn("Создать контрагента", header)
        self.assertNotIn("Открыть смету", header)

    def test_project_header_actions_removed_and_title_is_compact(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")

        self.assertNotIn("project-classic-actions", template)
        self.assertIn("detail-project-compact", template)
        self.assertIn(".detail-project-compact .project-classic-title h1", css)
        self.assertIn("font-size: clamp(24px, 2.1vw, 34px);", css)

    def test_progress_cards_show_estimate_status_and_project_finance(self):
        template = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("Статус сметы", template)
        self.assertIn("documents[0].status", template)
        self.assertNotIn("Готова", template)
        self.assertNotIn("2. Контрагент", template)
        self.assertIn("2. Финансы", template)
        self.assertIn("project-finance-visual", template)
        self.assertIn("Смета / оплачено / расход", template)


if __name__ == "__main__":
    unittest.main()
