import shutil
import unittest

from reportlab.platypus import Table

from webapp.config import get_settings
from webapp.standalone_estimate_files import (
    _build_pdf_table,
    _draft_watermark_enabled,
    _build_pdf_elements,
    export_final_approved_pdf,
    export_standalone_estimate_pdf,
)


class StandaloneEstimateFileExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = get_settings()
        cls.storage_dir = cls.settings.estimates_dir / "standalone-estimates"

    def setUp(self):
        self._cleanup_storage()

    def tearDown(self):
        self._cleanup_storage()

    def _cleanup_storage(self):
        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)

    def _snapshot(self):
        return {
            "estimate": {
                "id": 88001,
                "estimate_number": "ST-PDF-DRAFT",
                "title": "Черновой PDF",
                "status": "draft",
                "customer_name": "Клиент",
                "object_name": "Объект",
                "company_name": "ООО Декорартстрой",
                "contract_label": "D-8",
                "discount": "7.50",
                "watermark": "on",
            },
            "items": [
                {"row_type": "section", "name": "Подготовка", "sort_order": 1},
                {
                    "row_type": "item",
                    "name": "Грунтовка",
                    "unit": "м2",
                    "quantity": "10",
                    "price": "50",
                    "total": "500",
                    "discounted_total": "462.5",
                    "sort_order": 2,
                },
                {
                    "row_type": "item",
                    "name": "Шпатлевка",
                    "unit": "м2",
                    "quantity": "10",
                    "price": "100",
                    "total": "1000",
                    "discounted_total": "925",
                    "sort_order": 3,
                },
            ],
        }

    def test_draft_pdf_is_created_for_section_and_items(self):
        path = export_standalone_estimate_pdf(self._snapshot())

        self.assertTrue(path.exists())
        self.assertTrue(path.name.endswith("-draft.pdf"))
        self.assertGreater(path.stat().st_size, 0)

    def test_pdf_table_keeps_section_out_of_totals(self):
        table_data, section_styles, grand_total, discounted_total = _build_pdf_table(self._snapshot())

        self.assertEqual(table_data[1], ["Подготовка", "", "", "", "", ""])
        self.assertIn(("SPAN", (0, 1), (-1, 1)), section_styles)
        self.assertEqual(grand_total, 1500.0)
        self.assertEqual(discounted_total, 1387.5)

    def test_draft_pdf_rejects_stamp_and_signature(self):
        with self.assertRaises(ValueError):
            export_standalone_estimate_pdf(
                self._snapshot(),
                stamp_applied=True,
                signature_applied=True,
            )

    def test_watermark_is_enabled_only_for_marked_drafts(self):
        snapshot = self._snapshot()
        self.assertTrue(_draft_watermark_enabled(snapshot["estimate"], approved=False))
        self.assertFalse(_draft_watermark_enabled(snapshot["estimate"], approved=True))

        snapshot["estimate"]["watermark"] = ""
        self.assertFalse(_draft_watermark_enabled(snapshot["estimate"], approved=False))

    def _approved_snapshot(self):
        snapshot = self._snapshot()
        snapshot["estimate"]["status"] = "approved"
        snapshot["estimate"]["watermark"] = ""
        return snapshot

    def test_final_approved_pdf_is_created_from_approved_snapshot(self):
        snapshot = self._approved_snapshot()
        path = export_final_approved_pdf(snapshot)
        self.assertTrue(path.exists())
        self.assertTrue(path.name.endswith("-approved.pdf"))
        self.assertGreater(path.stat().st_size, 0)

    def test_final_approved_pdf_with_stamp_and_signature(self):
        snapshot = self._approved_snapshot()
        path = export_final_approved_pdf(snapshot, stamp_applied=True, signature_applied=True)
        self.assertTrue(path.exists())
        self.assertIn("-approved.pdf", path.name)

    def test_final_approved_pdf_rejects_non_approved_snapshot(self):
        with self.assertRaises(ValueError):
            export_final_approved_pdf(self._snapshot())

    def test_final_approved_pdf_rejects_stamp_for_non_approved_snapshot(self):
        with self.assertRaises(ValueError):
            export_final_approved_pdf(self._snapshot(), stamp_applied=True)

    def test_build_pdf_elements_includes_stamp_signature_block_for_final_approved(self):
        snapshot = self._approved_snapshot()
        elements = _build_pdf_elements(snapshot, stamp_applied=True, signature_applied=True, is_final_approved=True)
        table_count = sum(1 for elem in elements if isinstance(elem, Table))
        self.assertGreaterEqual(table_count, 2)

    def test_build_pdf_elements_no_stamp_signature_block_for_non_final(self):
        snapshot = self._approved_snapshot()
        elements = _build_pdf_elements(snapshot, stamp_applied=False, signature_applied=False, is_final_approved=False)
        table_count = sum(1 for elem in elements if isinstance(elem, Table))
        self.assertEqual(table_count, 1)


if __name__ == "__main__":
    unittest.main()
