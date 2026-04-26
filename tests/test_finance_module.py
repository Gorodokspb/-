from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASE_TEMPLATE = ROOT / "webapp" / "templates" / "base.html"
FINANCE_TEMPLATE = ROOT / "webapp" / "templates" / "finance.html"
PROJECT_TEMPLATE = ROOT / "webapp" / "templates" / "project_detail.html"
MAIN_PY = ROOT / "webapp" / "main.py"
DB_PY = ROOT / "webapp" / "db.py"
APP_CSS = ROOT / "webapp" / "static" / "app.css"
APP_JS = ROOT / "webapp" / "static" / "app.js"


class FinanceModuleTests(unittest.TestCase):
    def test_base_layout_has_global_navigation_and_quick_transaction_modal(self):
        template = BASE_TEMPLATE.read_text(encoding="utf-8")
        css = APP_CSS.read_text(encoding="utf-8")
        script = APP_JS.read_text(encoding="utf-8")

        self.assertIn("global-header", template)
        self.assertIn("Декорартстрой", template)
        for label in ["Проекты", "Сметы", "Справочник", "Калькулятор", "Финансы"]:
            self.assertIn(label, template)
        self.assertIn("+ Действие", template)
        self.assertIn("quickTransactionModal", template)
        self.assertIn('action="/finance/transactions"', template)
        self.assertIn("quick_action_projects", template)
        self.assertIn("flash_messages", template)
        self.assertIn("data-current-project-id", template)
        self.assertIn("global-nav-link", template)
        self.assertIn("active_section", template)
        self.assertIn(":active", css)
        self.assertIn("scale(0.98)", css)
        self.assertIn("global-action-open", script)

    def test_finance_database_helpers_and_routes_exist(self):
        db = DB_PY.read_text(encoding="utf-8")
        main = MAIN_PY.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE IF NOT EXISTS transactions", db)
        for column in ["project_id INTEGER", "type VARCHAR", "amount DECIMAL(12, 2)", "category VARCHAR", "description TEXT", "status VARCHAR"]:
            self.assertIn(column, db)
        self.assertIn("DEFAULT 'completed'", db)
        self.assertIn("REFERENCES projects(id) ON DELETE SET NULL", db)
        self.assertIn("idx_transactions_project_id", db)
        self.assertIn("def ensure_transactions_table", db)
        self.assertIn("def create_transaction", db)
        self.assertIn("def fetch_transactions", db)
        self.assertIn("def fetch_project_transactions", db)
        self.assertIn("def summarize_transactions", db)
        self.assertIn("@app.get(\"/finance\")", main)
        self.assertIn("@app.post(\"/finance/transactions\")", main)
        self.assertIn("ensure_transactions_table", main)

    def test_finance_page_template_shows_cashbox_balance_and_transactions(self):
        self.assertTrue(FINANCE_TEMPLATE.exists())
        template = FINANCE_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("{% extends \"base.html\" %}", template)
        self.assertIn("Общая касса", template)
        self.assertIn("finance_summary.balance", template)
        self.assertIn("finance_summary.income", template)
        self.assertIn("finance_summary.expense", template)
        self.assertIn("transactions", template)
        self.assertIn("project_name", template)

    def test_project_detail_contains_project_finance_transactions(self):
        template = PROJECT_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("Финансы объекта", template)
        self.assertIn("project_transactions", template)
        self.assertIn("project_finance_summary.balance", template)
        self.assertIn("project_finance_summary.balance_label", template)
        self.assertIn("Прибыль", template)
        self.assertIn("data-project-id=\"{{ project.id }}\"", template)
        self.assertIn("/finance/transactions", template)

    def test_summarize_transactions_calculates_balance(self):
        import webapp.db as db

        summary = db.summarize_transactions([
            {"type": "income", "amount": 1000},
            {"type": "expense", "amount": 250.5},
            {"type": "expense", "amount": "49.5"},
        ])

        self.assertEqual(summary["income"], 1000.0)
        self.assertEqual(summary["expense"], 300.0)
        self.assertEqual(summary["balance"], 700.0)
        self.assertEqual(summary["balance_label"], "700 ₽")


if __name__ == "__main__":
    unittest.main()
