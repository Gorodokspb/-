import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pypdf import PdfReader
from reportlab.lib import pdfencrypt
from reportlab.platypus import Paragraph

from webapp.estimate_pdf import _make_encryption, _OWNER_PASSWORD, generate_estimate_pdf


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
            {"row_type": "item", "name": "Покраска стен", "unit": "м2", "quantity": "10", "price": "500"},
        ],
    }
    estimate.update(overrides)
    return estimate


class TestEncryptionFactory(unittest.TestCase):
    def test_make_encryption_returns_standard_encryption(self):
        enc = _make_encryption()
        self.assertIsInstance(enc, pdfencrypt.StandardEncryption)

    def test_user_password_is_empty(self):
        enc = _make_encryption()
        self.assertEqual(enc.userPassword, "")

    def test_owner_password_is_set(self):
        self.assertTrue(len(_OWNER_PASSWORD) > 0)

    def test_can_print(self):
        enc = _make_encryption()
        self.assertEqual(enc.canPrint, 1)

    def test_cannot_modify(self):
        enc = _make_encryption()
        self.assertEqual(enc.canModify, 0)

    def test_cannot_copy(self):
        enc = _make_encryption()
        self.assertEqual(enc.canCopy, 0)

    def test_cannot_annotate(self):
        enc = _make_encryption()
        self.assertEqual(enc.canAnnotate, 0)

    def test_each_call_returns_new_instance(self):
        enc1 = _make_encryption()
        enc2 = _make_encryption()
        self.assertIsNot(enc1, enc2)


class TestProjectEstimatePdfEncryption(unittest.TestCase):
    @patch("webapp.estimate_pdf.build_estimate_pdf_path")
    @patch("webapp.estimate_pdf._update_estimate_pdf_document")
    @patch("webapp.estimate_pdf.SimpleDocTemplate")
    def test_encryption_applied_in_callback(self, mock_doc_cls, mock_update, mock_path):
        mock_path.return_value = (Path("/tmp/test.pdf"), "test.pdf")
        captured_elements = []

        def fake_build(elements, **kwargs):
            captured_elements.extend(elements)

        mock_doc = MagicMock()
        mock_doc.build.side_effect = fake_build
        mock_doc_cls.return_value = mock_doc

        generate_estimate_pdf(_minimal_estimate(), username="test")

        call_kwargs = mock_doc.build.call_args
        on_first_page = call_kwargs.kwargs.get("onFirstPage") or call_kwargs[1].get("onFirstPage")
        self.assertIsNotNone(on_first_page)

        mock_canvas = MagicMock()
        mock_canvas._doc = MagicMock()
        on_first_page(mock_canvas, MagicMock())
        self.assertIsInstance(mock_canvas._doc.encrypt, pdfencrypt.StandardEncryption)
        self.assertEqual(mock_canvas._doc.encrypt.canCopy, 0)


class TestGeneratedPdfEncryption(unittest.TestCase):
    def _generate_pdf(self, **overrides):
        from webapp.estimate_pdf import generate_estimate_pdf as _gen

        with patch("webapp.estimate_pdf._update_estimate_pdf_document"):
            return _gen(_minimal_estimate(**overrides), username="test")

    def test_pdf_is_encrypted(self):
        pdf_path = self._generate_pdf()
        try:
            reader = PdfReader(str(pdf_path))
            self.assertTrue(reader.is_encrypted)
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_pdf_decrypts_with_empty_user_password(self):
        pdf_path = self._generate_pdf()
        try:
            reader = PdfReader(str(pdf_path))
            result = reader.decrypt("")
            self.assertGreater(result, 0)
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_permissions_deny_copy(self):
        pdf_path = self._generate_pdf()
        try:
            reader = PdfReader(str(pdf_path))
            reader.decrypt("")
            p_val = reader.trailer["/Encrypt"].get_object()["/P"]
            can_copy = bool(p_val & (1 << 4))
            self.assertFalse(can_copy)
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_permissions_deny_modify(self):
        pdf_path = self._generate_pdf()
        try:
            reader = PdfReader(str(pdf_path))
            reader.decrypt("")
            p_val = reader.trailer["/Encrypt"].get_object()["/P"]
            can_modify = bool(p_val & (1 << 3))
            self.assertFalse(can_modify)
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_permissions_allow_print(self):
        pdf_path = self._generate_pdf()
        try:
            reader = PdfReader(str(pdf_path))
            reader.decrypt("")
            p_val = reader.trailer["/Encrypt"].get_object()["/P"]
            can_print = bool(p_val & (1 << 2))
            self.assertTrue(can_print)
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_heading_still_present_in_encrypted_pdf(self):
        pdf_path = self._generate_pdf()
        try:
            reader = PdfReader(str(pdf_path))
            reader.decrypt("")
            page = reader.pages[0]
            text = page.extract_text()
            self.assertIn("Смета на выполнение", text)
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_encryption_with_watermark_enabled(self):
        pdf_path = self._generate_pdf(watermark=True)
        try:
            reader = PdfReader(str(pdf_path))
            self.assertTrue(reader.is_encrypted)
            reader.decrypt("")
            p_val = reader.trailer["/Encrypt"].get_object()["/P"]
            self.assertFalse(bool(p_val & (1 << 4)))
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_multiple_generations_do_not_raise(self):
        with patch("webapp.estimate_pdf._update_estimate_pdf_document"):
            p1 = generate_estimate_pdf(_minimal_estimate(), username="test")
            p2 = generate_estimate_pdf(_minimal_estimate(), username="test")
        try:
            r1 = PdfReader(str(p1))
            r2 = PdfReader(str(p2))
            self.assertTrue(r1.is_encrypted)
            self.assertTrue(r2.is_encrypted)
        finally:
            p1.unlink(missing_ok=True)
            p2.unlink(missing_ok=True)


class TestStandaloneEncryptionFactory(unittest.TestCase):
    def test_standalone_make_encryption_exists(self):
        from webapp.standalone_estimate_files import _make_encryption as standalone_make
        enc = standalone_make()
        self.assertIsInstance(enc, pdfencrypt.StandardEncryption)

    def test_standalone_same_owner_password(self):
        from webapp.standalone_estimate_files import _OWNER_PASSWORD as standalone_owner
        self.assertEqual(standalone_owner, _OWNER_PASSWORD)

    def test_standalone_cannot_copy(self):
        from webapp.standalone_estimate_files import _make_encryption as standalone_make
        enc = standalone_make()
        self.assertEqual(enc.canCopy, 0)

    def test_standalone_can_print(self):
        from webapp.standalone_estimate_files import _make_encryption as standalone_make
        enc = standalone_make()
        self.assertEqual(enc.canPrint, 1)


if __name__ == "__main__":
    unittest.main()