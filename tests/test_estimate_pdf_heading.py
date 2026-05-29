import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from reportlab.platypus import Paragraph, Spacer, Table

from webapp.estimate_pdf import generate_estimate_pdf


def _minimal_estimate(**overrides):
    estimate = {
        "project": {"id": 999, "project_name": "Тестовый объект"},
        "company": "ООО Декорартстрой",
        "object_name": "ул. Тестовая, д. 1",
        "customer_name": "Иванов И.И.",
        "contract_label": "Договор №1",
        "discount": "0",
        "watermark": False,
        "editor_rows": [
            {"row_type": "item", "name": "Покраска стен", "unit": "м²", "quantity": "10", "price": "500"},
        ],
    }
    estimate.update(overrides)
    return estimate


class TestEstimatePdfHeading(unittest.TestCase):
    @patch("webapp.estimate_pdf.build_estimate_pdf_path")
    @patch("webapp.estimate_pdf._update_estimate_pdf_document")
    @patch("webapp.estimate_pdf.SimpleDocTemplate")
    def test_heading_present_in_elements(self, mock_doc_cls, mock_update, mock_path):
        mock_path.return_value = (Path("/tmp/test.pdf"), "test.pdf")
        captured_elements = []

        def fake_build(elements, **kwargs):
            captured_elements.extend(elements)

        mock_doc = MagicMock()
        mock_doc.build.side_effect = fake_build
        mock_doc_cls.return_value = mock_doc

        generate_estimate_pdf(_minimal_estimate(), username="test")

        heading_paragraphs = [
            e for e in captured_elements
            if isinstance(e, Paragraph)
            and getattr(e, "style", None) is not None
            and getattr(e.style, "name", "") == "Heading"
        ]
        self.assertEqual(len(heading_paragraphs), 1)
        text = heading_paragraphs[0].text
        self.assertIn("Смета на выполнение отделочных работ", text)

    @patch("webapp.estimate_pdf.build_estimate_pdf_path")
    @patch("webapp.estimate_pdf._update_estimate_pdf_document")
    @patch("webapp.estimate_pdf.SimpleDocTemplate")
    def test_heading_uses_bold_font(self, mock_doc_cls, mock_update, mock_path):
        mock_path.return_value = (Path("/tmp/test.pdf"), "test.pdf")
        captured_elements = []

        def fake_build(elements, **kwargs):
            captured_elements.extend(elements)

        mock_doc = MagicMock()
        mock_doc.build.side_effect = fake_build
        mock_doc_cls.return_value = mock_doc

        generate_estimate_pdf(_minimal_estimate(), username="test")

        heading_paragraphs = [
            e for e in captured_elements
            if isinstance(e, Paragraph)
            and getattr(e, "style", None) is not None
            and getattr(e.style, "name", "") == "Heading"
        ]
        self.assertEqual(len(heading_paragraphs), 1)
        style = heading_paragraphs[0].style
        self.assertEqual(style.fontName, "DejaVuSans-Bold")

    @patch("webapp.estimate_pdf.build_estimate_pdf_path")
    @patch("webapp.estimate_pdf._update_estimate_pdf_document")
    @patch("webapp.estimate_pdf.SimpleDocTemplate")
    def test_heading_center_aligned(self, mock_doc_cls, mock_update, mock_path):
        mock_path.return_value = (Path("/tmp/test.pdf"), "test.pdf")
        captured_elements = []

        def fake_build(elements, **kwargs):
            captured_elements.extend(elements)

        mock_doc = MagicMock()
        mock_doc.build.side_effect = fake_build
        mock_doc_cls.return_value = mock_doc

        generate_estimate_pdf(_minimal_estimate(), username="test")

        heading_paragraphs = [
            e for e in captured_elements
            if isinstance(e, Paragraph)
            and getattr(e, "style", None) is not None
            and getattr(e.style, "name", "") == "Heading"
        ]
        self.assertEqual(len(heading_paragraphs), 1)
        self.assertEqual(heading_paragraphs[0].style.alignment, 1)

    @patch("webapp.estimate_pdf.build_estimate_pdf_path")
    @patch("webapp.estimate_pdf._update_estimate_pdf_document")
    @patch("webapp.estimate_pdf.SimpleDocTemplate")
    def test_heading_appears_after_header_and_before_data_table(self, mock_doc_cls, mock_update, mock_path):
        mock_path.return_value = (Path("/tmp/test.pdf"), "test.pdf")
        captured_elements = []

        def fake_build(elements, **kwargs):
            captured_elements.extend(elements)

        mock_doc = MagicMock()
        mock_doc.build.side_effect = fake_build
        mock_doc_cls.return_value = mock_doc

        generate_estimate_pdf(_minimal_estimate(), username="test")

        heading_idx = None
        header_table_idx = None
        for i, e in enumerate(captured_elements):
            if isinstance(e, Paragraph) and getattr(getattr(e, "style", None), "name", "") == "Heading":
                heading_idx = i
            if isinstance(e, Table) and header_table_idx is None:
                header_table_idx = i

        self.assertIsNotNone(heading_idx)
        self.assertIsNotNone(header_table_idx)
        self.assertGreater(heading_idx, header_table_idx)

        tables = [i for i, e in enumerate(captured_elements) if isinstance(e, Table)]
        self.assertGreaterEqual(len(tables), 2)
        self.assertGreater(heading_idx, tables[0])
        self.assertLess(heading_idx, tables[1])

    @patch("webapp.estimate_pdf.build_estimate_pdf_path")
    @patch("webapp.estimate_pdf._update_estimate_pdf_document")
    @patch("webapp.estimate_pdf.SimpleDocTemplate")
    def test_spacer_after_heading(self, mock_doc_cls, mock_update, mock_path):
        mock_path.return_value = (Path("/tmp/test.pdf"), "test.pdf")
        captured_elements = []

        def fake_build(elements, **kwargs):
            captured_elements.extend(elements)

        mock_doc = MagicMock()
        mock_doc.build.side_effect = fake_build
        mock_doc_cls.return_value = mock_doc

        generate_estimate_pdf(_minimal_estimate(), username="test")

        heading_idx = None
        for i, e in enumerate(captured_elements):
            if isinstance(e, Paragraph) and getattr(getattr(e, "style", None), "name", "") == "Heading":
                heading_idx = i
                break

        self.assertIsNotNone(heading_idx)
        next_elem = captured_elements[heading_idx + 1]
        self.assertIsInstance(next_elem, Spacer)

    @patch("webapp.estimate_pdf.build_estimate_pdf_path")
    @patch("webapp.estimate_pdf._update_estimate_pdf_document")
    @patch("webapp.estimate_pdf.SimpleDocTemplate")
    def test_heading_font_size_9(self, mock_doc_cls, mock_update, mock_path):
        mock_path.return_value = (Path("/tmp/test.pdf"), "test.pdf")
        captured_elements = []

        def fake_build(elements, **kwargs):
            captured_elements.extend(elements)

        mock_doc = MagicMock()
        mock_doc.build.side_effect = fake_build
        mock_doc_cls.return_value = mock_doc

        generate_estimate_pdf(_minimal_estimate(), username="test")

        heading_paragraphs = [
            e for e in captured_elements
            if isinstance(e, Paragraph)
            and getattr(e, "style", None) is not None
            and getattr(e.style, "name", "") == "Heading"
        ]
        self.assertEqual(len(heading_paragraphs), 1)
        self.assertEqual(heading_paragraphs[0].style.fontSize, 9)


if __name__ == "__main__":
    unittest.main()