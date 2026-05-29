import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from webapp.contract_generator import (
    _build_soffice_cmd,
    _find_soffice,
    _CONVERSION_TIMEOUT,
)


class TestFindSoffice(unittest.TestCase):
    def test_finds_soffice(self):
        with patch("shutil.which", side_effect=lambda c: f"/usr/bin/{c}" if c == "soffice" else None):
            result = _find_soffice()
            self.assertEqual(result, "/usr/bin/soffice")

    def test_finds_libreoffice_when_no_soffice(self):
        with patch("shutil.which", side_effect=lambda c: f"/usr/bin/{c}" if c == "libreoffice" else None):
            result = _find_soffice()
            self.assertEqual(result, "/usr/bin/libreoffice")

    def test_prefers_soffice_over_libreoffice(self):
        with patch("shutil.which", side_effect=lambda c: f"/usr/bin/{c}"):
            result = _find_soffice()
            self.assertEqual(result, "/usr/bin/soffice")

    def test_raises_when_not_found(self):
        with patch("shutil.which", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                _find_soffice()
            self.assertIn("LibreOffice", str(ctx.exception))


class TestBuildSofficeCmd(unittest.TestCase):
    def test_command_contains_required_args(self):
        cmd = _build_soffice_cmd(
            "/usr/bin/soffice",
            "/path/to/contract.docx",
            "/path/to/outdir",
            "file:///tmp/lo-profile-test",
        )
        self.assertEqual(cmd[0], "/usr/bin/soffice")
        self.assertIn("--headless", cmd)
        self.assertIn("--norestore", cmd)
        self.assertIn("--convert-to", cmd)
        self.assertIn("pdf", cmd)
        self.assertIn("--outdir", cmd)
        self.assertIn("/path/to/outdir", cmd)
        self.assertIn("/path/to/contract.docx", cmd)

    def test_command_contains_user_profile(self):
        cmd = _build_soffice_cmd(
            "/usr/bin/soffice",
            "/path/contract.docx",
            "/out",
            "file:///tmp/lo-profile-abc",
        )
        profile_arg = [a for a in cmd if a.startswith("-env:UserInstallation")]
        self.assertEqual(len(profile_arg), 1)
        self.assertIn("file:///tmp/lo-profile-abc", profile_arg[0])

    def test_command_is_list_not_string(self):
        cmd = _build_soffice_cmd("/usr/bin/soffice", "/a.docx", "/out", "file:///tmp/p")
        self.assertIsInstance(cmd, list)


def _make_docx_on_disk(tmpdir, name="Договор_1.docx"):
    docx_path = Path(tmpdir) / name
    docx_path.write_bytes(b"PK" + b"\x00" * 100)
    return docx_path


class TestGenerateContractPdf(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    @patch("webapp.contract_generator._find_soffice", return_value="/usr/bin/soffice")
    @patch("webapp.contract_generator.subprocess.run")
    @patch("webapp.contract_generator.generate_contract_docx")
    @patch("webapp.contract_generator.resolve_storage_path")
    @patch("webapp.contract_generator.storage_relative_path", side_effect=lambda p: str(p).lstrip("/"))
    @patch("webapp.db.update_document_pdf_path")
    @patch("webapp.db.fetch_document")
    def test_successful_conversion_updates_pdf_path(
        self, mock_fetch_doc, mock_update_pdf, mock_rel_path, mock_resolve, mock_gen_docx, mock_subprocess, mock_soffice
    ):
        docx_path = _make_docx_on_disk(self._tmpdir)
        mock_resolve.return_value = docx_path
        mock_gen_docx.return_value = {"document_id": 42, "project_id": 1, "file_path": "Договоры/test.docx"}
        mock_fetch_doc.return_value = {"id": 42, "file_path": str(docx_path)}
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        pdf_path = docx_path.with_suffix(".pdf")
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from webapp.contract_generator import generate_contract_pdf
        result = generate_contract_pdf(1)

        self.assertEqual(result["document_id"], 42)
        mock_update_pdf.assert_called_once()

    @patch("webapp.contract_generator._find_soffice", return_value="/usr/bin/soffice")
    @patch("webapp.contract_generator.subprocess.run")
    @patch("webapp.contract_generator.generate_contract_docx")
    @patch("webapp.contract_generator.resolve_storage_path")
    @patch("webapp.contract_generator.storage_relative_path")
    @patch("webapp.db.fetch_document")
    def test_subprocess_timeout_raises(self, mock_fetch_doc, mock_rel_path, mock_resolve, mock_gen_docx, mock_subprocess, mock_soffice
    ):
        docx_path = _make_docx_on_disk(self._tmpdir)
        mock_resolve.return_value = docx_path
        mock_gen_docx.return_value = {"document_id": 42, "project_id": 1, "file_path": "test.docx"}
        mock_fetch_doc.return_value = {"id": 42, "file_path": str(docx_path)}
        mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd="soffice", timeout=30)

        from webapp.contract_generator import generate_contract_pdf
        with self.assertRaises(RuntimeError) as ctx:
            generate_contract_pdf(1)
        self.assertIn("таймаут", str(ctx.exception))

    @patch("webapp.contract_generator._find_soffice", return_value="/usr/bin/soffice")
    @patch("webapp.contract_generator.subprocess.run")
    @patch("webapp.contract_generator.generate_contract_docx")
    @patch("webapp.contract_generator.resolve_storage_path")
    @patch("webapp.contract_generator.storage_relative_path")
    @patch("webapp.db.fetch_document")
    def test_subprocess_nonzero_returncode_raises(self, mock_fetch_doc, mock_rel_path, mock_resolve, mock_gen_docx, mock_subprocess, mock_soffice
    ):
        docx_path = _make_docx_on_disk(self._tmpdir)
        mock_resolve.return_value = docx_path
        mock_gen_docx.return_value = {"document_id": 42, "project_id": 1, "file_path": "test.docx"}
        mock_fetch_doc.return_value = {"id": 42, "file_path": str(docx_path)}
        mock_subprocess.return_value = MagicMock(returncode=1, stdout="", stderr="conversion failed")

        from webapp.contract_generator import generate_contract_pdf
        with self.assertRaises(RuntimeError) as ctx:
            generate_contract_pdf(1)
        self.assertIn("ошибку", str(ctx.exception))

    @patch("webapp.contract_generator._find_soffice")
    @patch("webapp.contract_generator.generate_contract_docx")
    @patch("webapp.contract_generator.resolve_storage_path")
    @patch("webapp.db.fetch_document")
    def test_libreoffice_not_found_raises(self, mock_fetch_doc, mock_resolve, mock_gen_docx, mock_soffice
    ):
        docx_path = _make_docx_on_disk(self._tmpdir)
        mock_resolve.return_value = docx_path
        mock_gen_docx.return_value = {"document_id": 42, "project_id": 1, "file_path": "test.docx"}
        mock_fetch_doc.return_value = {"id": 42, "file_path": str(docx_path)}
        mock_soffice.side_effect = RuntimeError("LibreOffice не найден.")

        from webapp.contract_generator import generate_contract_pdf
        with self.assertRaises(RuntimeError) as ctx:
            generate_contract_pdf(1)
        self.assertIn("LibreOffice", str(ctx.exception))

    @patch("webapp.contract_generator.generate_contract_docx")
    @patch("webapp.contract_generator.resolve_storage_path", return_value=None)
    @patch("webapp.db.fetch_document")
    def test_docx_not_on_disk_raises(self, mock_fetch_doc, mock_resolve, mock_gen_docx
    ):
        mock_gen_docx.return_value = {"document_id": 42, "project_id": 1, "file_path": "missing.docx"}
        mock_fetch_doc.return_value = {"id": 42, "file_path": "missing.docx"}

        from webapp.contract_generator import generate_contract_pdf
        with self.assertRaises(FileNotFoundError) as ctx:
            generate_contract_pdf(1)
        self.assertIn("не найден", str(ctx.exception))

    @patch("webapp.contract_generator._find_soffice", return_value="/usr/bin/soffice")
    @patch("webapp.contract_generator.subprocess.run")
    @patch("webapp.contract_generator.generate_contract_docx")
    @patch("webapp.contract_generator.resolve_storage_path")
    @patch("webapp.contract_generator.storage_relative_path")
    @patch("webapp.db.update_document_pdf_path")
    @patch("webapp.db.fetch_document")
    def test_subprocess_called_with_timeout(self, mock_fetch_doc, mock_update_pdf, mock_rel_path, mock_resolve, mock_gen_docx, mock_subprocess, mock_soffice
    ):
        docx_path = _make_docx_on_disk(self._tmpdir)
        mock_resolve.return_value = docx_path
        mock_gen_docx.return_value = {"document_id": 42, "project_id": 1, "file_path": "test.docx"}
        mock_fetch_doc.return_value = {"id": 42, "file_path": str(docx_path)}
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        pdf_path = docx_path.with_suffix(".pdf")
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from webapp.contract_generator import generate_contract_pdf
        generate_contract_pdf(1)

        call_kwargs = mock_subprocess.call_args.kwargs
        self.assertEqual(call_kwargs["timeout"], _CONVERSION_TIMEOUT)


class TestContractPdfRoute(unittest.TestCase):
    def test_route_exists_in_source(self):
        source = Path("webapp/main.py").read_text()
        self.assertIn("/projects/{project_id}/contract/generate-pdf", source)

    def test_route_imports_generate_contract_pdf(self):
        source = Path("webapp/main.py").read_text()
        self.assertIn("from webapp.contract_generator import generate_contract_pdf", source)

    def test_route_returns_contract_pdf_created(self):
        source = Path("webapp/main.py").read_text()
        self.assertIn("created=contract-pdf", source)


class TestContractPdfUi(unittest.TestCase):
    def test_template_has_generate_pdf_form(self):
        source = Path("webapp/templates/contract_settings.html").read_text()
        self.assertIn("/contract/generate-pdf", source)

    def test_template_has_download_pdf_link(self):
        source = Path("webapp/templates/contract_settings.html").read_text()
        self.assertIn("kind=pdf", source)
        self.assertIn("Скачать PDF", source)

    def test_template_has_pdf_created_banner(self):
        source = Path("webapp/templates/contract_settings.html").read_text()
        self.assertIn("pdf_created", source)

    def test_template_pdf_download_uses_document_id(self):
        source = Path("webapp/templates/contract_settings.html").read_text()
        self.assertIn("contract_document.id }}/download?kind=pdf", source)

    def test_main_passes_pdf_created_context(self):
        source = Path("webapp/main.py").read_text()
        self.assertIn('"pdf_created"', source)


class TestUpdateDocumentPdfPath(unittest.TestCase):
    def test_function_exists_in_db(self):
        from webapp.db import update_document_pdf_path
        self.assertTrue(callable(update_document_pdf_path))


if __name__ == "__main__":
    unittest.main()