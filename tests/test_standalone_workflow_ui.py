import unittest
from pathlib import Path

from webapp.estimate_domain import EstimateStatus, EstimateType, OriginChannel
from webapp.estimate_repository import EstimateSummary

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "webapp" / "templates"


def _make_estimate_summary(**overrides):
    defaults = {
        "id": 1,
        "estimate_number": "TEST-001",
        "title": "Тестовая смета",
        "status": EstimateStatus.DRAFT,
        "estimate_type": EstimateType.PRIMARY,
        "origin_channel": OriginChannel.WEB,
        "project_id": None,
        "counterparty_id": None,
        "parent_estimate_id": None,
        "root_estimate_id": None,
        "current_version_id": None,
        "approved_version_id": None,
        "final_document_id": None,
        "customer_name": "Клиент",
        "object_name": "Объект",
        "company_name": "ООО Декорартстрой",
        "contract_label": "Д-1",
        "discount": "0",
        "watermark": None,
        "is_archived": False,
        "created_by": "testuser",
        "updated_by": "testuser",
        "created_at": "2026-01-01",
        "updated_at": "2026-01-01",
        "sent_at": None,
        "approved_at": None,
        "rejected_at": None,
        "project_created_at": None,
    }
    defaults.update(overrides)
    return EstimateSummary(**defaults)


class StandaloneWorkflowUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.editor_html = (TEMPLATES_DIR / "standalone_estimate_editor.html").read_text(encoding="utf-8")
        cls.legacy_editor_html = (TEMPLATES_DIR / "estimate_editor.html").read_text(encoding="utf-8")

    def test_editor_contains_workflow_actions_container(self):
        self.assertIn("estimateWorkflowActions", self.editor_html)

    def test_editor_contains_send_action_for_draft(self):
        self.assertIn('data-action="send"', self.editor_html)

    def test_editor_contains_approve_action(self):
        self.assertIn('data-action="approve"', self.editor_html)

    def test_editor_contains_reject_action(self):
        self.assertIn('data-action="reject"', self.editor_html)

    def test_editor_contains_final_pdf_action(self):
        self.assertIn('data-action="final-pdf"', self.editor_html)

    def test_editor_status_conditional_blocks(self):
        self.assertIn("estimate.status.value == 'draft'", self.editor_html)
        self.assertIn("estimate.status.value == 'sent'", self.editor_html)
        self.assertIn("estimate.status.value == 'approved'", self.editor_html)
        self.assertIn("estimate.status.value == 'rejected'", self.editor_html)
        self.assertIn("estimate.status.value == 'in_progress'", self.editor_html)

    def test_editor_final_document_id_conditional(self):
        self.assertIn("estimate.final_document_id", self.editor_html)

    def test_editor_download_links(self):
        self.assertIn("/download/final-pdf", self.editor_html)
        self.assertIn("/download/json", self.editor_html)
        self.assertIn("/download/pdf", self.editor_html)

    def test_legacy_editor_does_not_contain_workflow_actions(self):
        self.assertNotIn('data-action="send"', self.legacy_editor_html)
        self.assertNotIn('data-action="approve"', self.legacy_editor_html)
        self.assertNotIn('data-action="reject"', self.legacy_editor_html)
        self.assertNotIn('data-action="final-pdf"', self.legacy_editor_html)
        self.assertNotIn("estimateWorkflowActions", self.legacy_editor_html)


if __name__ == "__main__":
    unittest.main()