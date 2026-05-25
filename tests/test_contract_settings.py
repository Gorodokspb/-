import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.db_guard import guard_live_database
from webapp.db import (
    get_connection,
    create_project,
    fetch_project,
    fetch_contract_settings,
    save_contract_settings,
    create_or_update_contract_document,
    get_project_estimate_total,
    fetch_counterparty,
    create_counterparty,
)

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "webapp" / "templates"
MAIN_PY = Path(__file__).resolve().parents[1] / "webapp" / "main.py"


class ContractSettingsDBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        guard_live_database()

    def setUp(self):
        guard_live_database()
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        guard_live_database()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE doc_type = 'Договор' AND project_id > 2")
                cur.execute("DELETE FROM counterparties WHERE id > 2")
                cur.execute("DELETE FROM projects WHERE id > 2")
            conn.commit()

    def _create_test_project(self, name="Тест Договор"):
        pid = create_project(
            "tester",
            project_name=name,
            address="ул. Тестовая, д. 1",
            counterparty_id=None,
            status="В работе",
            contract="Д-100",
            contract_date="01.01.2026",
            notes="",
        )
        return pid

    def test_fetch_contract_settings_empty(self):
        pid = self._create_test_project()
        settings = fetch_contract_settings(pid)
        self.assertIsInstance(settings, dict)
        self.assertEqual(len(settings), 0)

    def test_save_and_fetch_contract_settings(self):
        pid = self._create_test_project()
        settings = {
            "work_end_date": "30.06.2026",
            "advance_amount": "50000",
            "payments": [{"date": "01.04.2026", "amount": "30000"}],
            "working_group_text": "Рабочая группа WhatsApp",
            "materials_mode": "customer",
            "contractor_mode": "ooo",
        }
        save_contract_settings(pid, settings)
        result = fetch_contract_settings(pid)
        self.assertEqual(result["work_end_date"], "30.06.2026")
        self.assertEqual(result["advance_amount"], "50000")
        self.assertEqual(len(result["payments"]), 1)
        self.assertEqual(result["payments"][0]["date"], "01.04.2026")
        self.assertEqual(result["working_group_text"], "Рабочая группа WhatsApp")

    def test_save_contract_settings_preserves_other_fields(self):
        pid = self._create_test_project()
        project_before = fetch_project(pid)
        save_contract_settings(pid, {"work_end_date": "31.12.2026"})
        project_after = fetch_project(pid)
        self.assertEqual(project_after["contract"], project_before["contract"])
        self.assertEqual(project_after["project_name"], project_before["project_name"])
        self.assertEqual(project_after["customer"], project_before["customer"])

    def test_fetch_contract_settings_corrupt_json(self):
        pid = self._create_test_project()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE projects SET contract_settings_json = %s WHERE id = %s",
                    ("not valid json{{{", pid),
                )
            conn.commit()
        result = fetch_contract_settings(pid)
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)

    def test_fetch_contract_settings_null(self):
        pid = self._create_test_project()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE projects SET contract_settings_json = NULL WHERE id = %s",
                    (pid,),
                )
            conn.commit()
        result = fetch_contract_settings(pid)
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)

    def test_create_contract_document_creates_record(self):
        pid = self._create_test_project()
        doc = create_or_update_contract_document(pid)
        self.assertIsNotNone(doc)
        self.assertEqual(doc["doc_type"], "Договор")
        self.assertEqual(doc["status"], "Черновик")
        self.assertEqual(doc["project_id"], pid)
        self.assertEqual(doc["title"], "Договор")

    def test_create_contract_document_no_duplicate(self):
        pid = self._create_test_project()
        doc1 = create_or_update_contract_document(pid)
        doc2 = create_or_update_contract_document(pid)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM documents WHERE project_id = %s AND doc_type = 'Договор'",
                    (pid,),
                )
                count = cur.fetchone()["cnt"]
        self.assertEqual(count, 1)

    def test_contract_document_has_no_file_paths(self):
        pid = self._create_test_project()
        create_or_update_contract_document(pid)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT file_path, draft_path, pdf_path FROM documents WHERE project_id = %s AND doc_type = 'Договор'",
                    (pid,),
                )
                row = cur.fetchone()
        self.assertIsNone(row["file_path"])
        self.assertIsNone(row["draft_path"])
        self.assertIsNone(row["pdf_path"])

    def test_get_project_estimate_total_no_estimate(self):
        pid = self._create_test_project()
        total = get_project_estimate_total(pid)
        self.assertEqual(total, "0")

    def test_save_contract_settings_updates_fields(self):
        pid = self._create_test_project()
        save_contract_settings(pid, {"work_end_date": "01.01.2026"})
        save_contract_settings(pid, {"work_end_date": "31.12.2026", "advance_amount": "100000"})
        result = fetch_contract_settings(pid)
        self.assertEqual(result["work_end_date"], "31.12.2026")
        self.assertEqual(result["advance_amount"], "100000")


class ContractSettingsTemplateTests(unittest.TestCase):
    def setUp(self):
        self.template = TEMPLATES_DIR / "contract_settings.html"
        self.project_detail = TEMPLATES_DIR / "project_detail.html"

    def test_contract_settings_template_exists(self):
        self.assertTrue(self.template.exists())

    def test_contract_settings_template_has_form_fields(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn('name="work_end_date"', content)
        self.assertIn('name="advance_amount"', content)
        self.assertIn('name="final_payment_amount"', content)
        self.assertIn('name="working_group_text"', content)
        self.assertIn('name="materials_mode"', content)
        self.assertIn('name="contractor_mode"', content)
        self.assertIn('name="customer_gender"', content)
        self.assertIn('name="payments_date_{{ i }}"', content)
        self.assertIn('name="payments_amount_{{ i }}"', content)

    def test_contract_settings_template_has_add_payment_button(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn('id="add-payment-btn"', content)
        self.assertIn("Добавить платёж", content)

    def test_contract_settings_template_has_seven_payment_rows(self):
        content = self.template.read_text(encoding="utf-8")
        for i in range(1, 8):
            self.assertIn(f'name="payments_date_{{{{ i }}}}"', content, f"Missing date field for row {i} in Jinja loop")
            self.assertIn(f'name="payments_amount_{{{{ i }}}}"', content, f"Missing amount field for row {i} in Jinja loop")
        self.assertIn("data-row=", content)

    def test_contract_settings_template_has_money_format_class(self):
        content = self.template.read_text(encoding="utf-8")
        summary_count = content.count('class="money-format"')
        self.assertGreaterEqual(summary_count, 2, "Should have money-format on advance_amount and final_payment_amount")
        payment_money = content.count('class="money-format"') - summary_count
        total_classes = content.count("money-format")
        self.assertGreaterEqual(total_classes, 2, "Should have at least 2 money-format classes")

    def test_contract_settings_template_has_money_formatting_js(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn("formatMoney", content)
        self.assertIn("stripMoney", content)
        self.assertIn("replace(/\\./g", content)

    def test_contract_settings_template_has_submit_cleanup(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn("stripMoney", content)
        submit_block_found = False
        idx = content.find("form.addEventListener('submit'")
        if idx > 0:
            section = content[idx:idx + 500]
            submit_block_found = "stripMoney" in section
        self.assertTrue(submit_block_found, "Submit handler should strip money formatting")

    def test_contract_settings_template_has_collapsed_payment_rows(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn('payment-row', content)
        self.assertIn("display:none", content)

    def test_contract_settings_template_has_money_hint(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn("Можно вводить 1000000", content)

    def test_contract_settings_template_shows_project_data(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn("project.project_name", content)
        self.assertIn("project.contract", content)
        self.assertIn("estimate_total", content)
        self.assertIn("contract_document", content)

    def test_contract_settings_template_shows_counterparty_data(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn("counterparty.type", content)
        self.assertIn("counterparty.display_name", content)
        self.assertIn("counterparty.passport_series_number", content)
        self.assertIn("counterparty.inn", content)
        self.assertIn("counterparty.phone", content)
        self.assertIn("counterparty.email", content)

    def test_contract_settings_template_has_post_action(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn('action="/projects/{{ project.id }}/contract-settings"', content)

    def test_contract_settings_template_has_saved_banner(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn("{% if saved %}", content)

    def test_project_detail_has_contract_link_in_progress_card(self):
        content = self.project_detail.read_text(encoding="utf-8")
        self.assertIn("Настройки договора", content)

    def test_contract_settings_shows_generate_docx_button(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn("/contract/generate-docx", content)
        self.assertIn("Сформировать DOCX договора", content)

    def test_contract_settings_shows_download_link_when_file_path(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn("/download?kind=file", content)
        self.assertIn("Скачать DOCX договора", content)

    def test_contract_settings_shows_docx_created_banner(self):
        content = self.template.read_text(encoding="utf-8")
        self.assertIn("docx_created", content)
        self.assertIn("DOCX договора сформирован", content)

    def test_main_py_has_generate_docx_route(self):
        content = MAIN_PY.read_text(encoding="utf-8")
        self.assertIn("/projects/{project_id}/contract/generate-docx", content)

    def test_main_py_imports_fetch_document(self):
        content = MAIN_PY.read_text(encoding="utf-8")
        self.assertIn("fetch_document", content)


if __name__ == "__main__":
    unittest.main()