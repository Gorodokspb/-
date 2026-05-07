import asyncio
import io
import json
import shutil
import unittest
from unittest.mock import patch

import openpyxl

from fastapi import HTTPException

import webapp.standalone_estimate_api as standalone_api
from tests.db_guard import guard_live_database
from webapp.config import get_settings
from webapp.db import get_connection
from webapp.estimate_domain import EstimateStatus
from webapp.excel_estimate_parser import MAX_XLSX_BYTES


def make_request(path: str, *, method: str = "GET", query: dict | None = None, session: dict | None = None, headers: dict[str, str] | None = None) -> "Request":
    from starlette.requests import Request
    from urllib.parse import urlencode
    query_string = urlencode(query or {}, doseq=True).encode("utf-8")
    request_headers = [(name.encode("utf-8"), value.encode("utf-8")) for name, value in (headers or {"content-type": "application/json"}).items()]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string,
        "headers": request_headers,
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "session": session or {},
    }
    return Request(scope)


def _build_xlsx_bytes(rows: list[list], headers_row: list[str] | None = None) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Смета"
    start_row = 1
    if headers_row:
        ws.append(headers_row)
        start_row = 2
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


BASIC_HEADERS = ["Наименование", "Ед.", "Кол-во", "Цена", "Стоимость"]
BASIC_ROWS = [
    ["Штукатурка", "м2", 10, 500, 5000],
    ["Малярные работы", "м2", 15, 300, 4500],
]


class ExcelImportRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = get_settings()
        cls.storage_dir = cls.settings.estimates_dir / "standalone-estimates"

    def setUp(self):
        guard_live_database()
        self._cleanup_tables()
        self._cleanup_storage()

    def tearDown(self):
        self._cleanup_tables()
        self._cleanup_storage()

    def _cleanup_tables(self):
        guard_live_database()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM estimate_documents")
                cur.execute("DELETE FROM estimate_status_history")
                cur.execute("DELETE FROM estimate_items")
                cur.execute("DELETE FROM estimate_versions")
                cur.execute("DELETE FROM estimates")
                cur.execute("DELETE FROM documents WHERE project_id IS NULL")
            conn.commit()

    def _cleanup_storage(self):
        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)

    def _create_draft_estimate(self, *, items: list[dict] | None = None):
        payload = {
            "estimate_number": "IMP-001",
            "title": "Смета для импорта",
            "customer_name": "Тестовый заказчик",
            "object_name": "Тестовый объект",
            "company_name": "ООО Декорартстрой",
            "items": items or [],
        }
        request = make_request("/estimates", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("webapp.standalone_estimate_api._username", return_value="tester"), \
             patch("webapp.standalone_estimate_api._load_payload", return_value=payload):
            response = asyncio.run(standalone_api.standalone_estimate_create(request))
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.body)
        return data["estimate"]["id"]

    def _create_and_send_estimate(self, *, items: list[dict] | None = None):
        estimate_id = self._create_draft_estimate(items=items)
        send_request = make_request(f"/estimates/{estimate_id}/send", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("webapp.standalone_estimate_api._username", return_value="tester"):
            standalone_api.standalone_estimate_send(estimate_id, send_request)
        return estimate_id

    def _create_and_approve_estimate(self, *, items: list[dict] | None = None):
        estimate_id = self._create_and_send_estimate(items=items)
        approve_request = make_request(f"/estimates/{estimate_id}/approve", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("webapp.standalone_estimate_api._username", return_value="tester"), \
             patch("webapp.standalone_estimate_api._load_payload", return_value={"stamp_applied": False, "signature_applied": False}):
            asyncio.run(standalone_api.standalone_estimate_approve(estimate_id, approve_request))
        return estimate_id

    def _make_upload_request(self, estimate_id: int, file_bytes: bytes, filename: str = "test.xlsx"):
        from starlette.datastructures import UploadFile
        buf = io.BytesIO(file_bytes)
        upload = UploadFile(filename=filename, file=buf)
        form_data = {"file": upload}

        class MockRequest:
            def __init__(self):
                self.session = {"is_authenticated": True, "username": "tester"}
                self._form = form_data
                self.headers = {"content-type": "multipart/form-data"}

            async def form(self):
                return self._form

            def get(self, key, default=None):
                return self.headers.get(key, default)

        scope = {
            "type": "http",
            "method": "POST",
            "path": f"/estimates/{estimate_id}/import-excel/preview",
            "raw_path": f"/estimates/{estimate_id}/import-excel/preview".encode(),
            "query_string": b"",
            "headers": [(b"content-type", b"multipart/form-data")],
            "client": ("testclient", 123),
            "server": ("testserver", 80),
            "session": {"is_authenticated": True, "username": "tester"},
        }
        from starlette.requests import Request
        return Request(scope)


class ImportPreviewTests(ExcelImportRouteTests):

    def test_preview_draft_returns_sections_items_diagnostics(self):
        estimate_id = self._create_draft_estimate()
        xlsx_bytes = _build_xlsx_bytes(BASIC_ROWS, headers_row=BASIC_HEADERS)

        async def mock_form(self_ignored):
            from starlette.datastructures import UploadFile
            buf = io.BytesIO(xlsx_bytes)
            upload = UploadFile(filename="estimate.xlsx", file=buf)
            from starlette.datastructures import FormData
            return FormData([("file", upload)])

        request = make_request(f"/estimates/{estimate_id}/import-excel/preview", method="POST", headers={"content-type": "multipart/form-data"})
        request._form = None
        request._files = None

        import starlette.requests
        original_form = starlette.requests.Request.form

        async def patched_form(req):
            from starlette.datastructures import FormData, UploadFile
            buf = io.BytesIO(xlsx_bytes)
            upload = UploadFile(filename="estimate.xlsx", file=buf)
            await upload.write(xlsx_bytes)
            await upload.seek(0)
            return FormData([("file", upload)])

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("starlette.requests.Request.form", patched_form):
            response = asyncio.run(standalone_api.import_excel_preview(estimate_id, request))

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.body)
        self.assertEqual(data["estimate_id"], estimate_id)
        self.assertGreater(data["items_count"], 0)
        self.assertIn("rows", data)
        self.assertIn("diagnostics", data)
        self.assertIn("sections_count", data)

    def test_preview_does_not_modify_estimate_items_in_db(self):
        estimate_id = self._create_draft_estimate(items=[
            {"name": "Существующая позиция", "sort_order": 1, "row_type": "item", "quantity": "3", "price": "100", "total": "300"},
        ])
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM estimate_items WHERE estimate_id = %s", (estimate_id,))
                count_before = cur.fetchone()["cnt"]

        xlsx_bytes = _build_xlsx_bytes(BASIC_ROWS, headers_row=BASIC_HEADERS)

        async def patched_form(req):
            from starlette.datastructures import FormData, UploadFile
            buf = io.BytesIO(xlsx_bytes)
            upload = UploadFile(filename="estimate.xlsx", file=buf)
            await upload.write(xlsx_bytes)
            await upload.seek(0)
            return FormData([("file", upload)])

        request = make_request(f"/estimates/{estimate_id}/import-excel/preview", method="POST", headers={"content-type": "multipart/form-data"})

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("starlette.requests.Request.form", patched_form):
            response = asyncio.run(standalone_api.import_excel_preview(estimate_id, request))

        self.assertEqual(response.status_code, 200)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM estimate_items WHERE estimate_id = %s", (estimate_id,))
                count_after = cur.fetchone()["cnt"]

        self.assertEqual(count_before, count_after, "Preview should not modify database items")

    def test_preview_reject_non_xlsx(self):
        estimate_id = self._create_draft_estimate()

        async def patched_form(req):
            from starlette.datastructures import FormData, UploadFile
            buf = io.BytesIO(b"not an excel file")
            upload = UploadFile(filename="test.csv", file=buf)
            await upload.write(b"not an excel file")
            await upload.seek(0)
            return FormData([("file", upload)])

        request = make_request(f"/estimates/{estimate_id}/import-excel/preview", method="POST", headers={"content-type": "multipart/form-data"})

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("starlette.requests.Request.form", patched_form):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(standalone_api.import_excel_preview(estimate_id, request))
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn(".xlsx", ctx.exception.detail)

    def test_preview_reject_oversized_file(self):
        estimate_id = self._create_draft_estimate()
        large_bytes = b"x" * (MAX_XLSX_BYTES + 1)

        async def patched_form(req):
            from starlette.datastructures import FormData, UploadFile
            buf = io.BytesIO(large_bytes)
            upload = UploadFile(filename="big.xlsx", file=buf)
            await upload.write(large_bytes)
            await upload.seek(0)
            return FormData([("file", upload)])

        request = make_request(f"/estimates/{estimate_id}/import-excel/preview", method="POST", headers={"content-type": "multipart/form-data"})

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("starlette.requests.Request.form", patched_form):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(standalone_api.import_excel_preview(estimate_id, request))
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("слишком большой", ctx.exception.detail.lower())

    def test_preview_invalid_xlsx_gives_400(self):
        estimate_id = self._create_draft_estimate()
        invalid_bytes = b"this is not a valid xlsx file at all"

        async def patched_form(req):
            from starlette.datastructures import FormData, UploadFile
            buf = io.BytesIO(invalid_bytes)
            upload = UploadFile(filename="corrupt.xlsx", file=buf)
            await upload.write(invalid_bytes)
            await upload.seek(0)
            return FormData([("file", upload)])

        request = make_request(f"/estimates/{estimate_id}/import-excel/preview", method="POST", headers={"content-type": "multipart/form-data"})

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("starlette.requests.Request.form", patched_form):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(standalone_api.import_excel_preview(estimate_id, request))
            self.assertEqual(ctx.exception.status_code, 400)


class ImportApplyTests(ExcelImportRouteTests):

    def test_apply_adds_rows_to_estimate(self):
        estimate_id = self._create_draft_estimate()

        apply_payload = {
            "rows": [
                {"row_type": "section", "name": "Раздел 1", "sort_order": 1},
                {"row_type": "item", "name": "Штукатурка", "sort_order": 2, "unit": "м2", "quantity": "10", "price": "500", "total": "5000"},
                {"row_type": "item", "name": "Малярные работы", "sort_order": 3, "unit": "м2", "quantity": "15", "price": "300", "total": "4500"},
            ]
        }

        request = make_request(f"/estimates/{estimate_id}/import-excel/apply", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("webapp.standalone_estimate_api._username", return_value="tester"), \
             patch("webapp.standalone_estimate_api._load_payload", return_value=apply_payload):
            response = asyncio.run(standalone_api.import_excel_apply(estimate_id, request))

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.body)
        self.assertEqual(data["estimate_id"], estimate_id)
        self.assertEqual(data["imported_count"], 3)
        self.assertIn(f"/estimates/{estimate_id}/edit", data["redirect_url"])

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM estimate_items WHERE estimate_id = %s", (estimate_id,))
                self.assertEqual(cur.fetchone()["cnt"], 3)

    def test_apply_does_not_remove_existing_rows(self):
        estimate_id = self._create_draft_estimate(items=[
            {"name": "Существующая позиция", "sort_order": 10, "row_type": "item", "quantity": "3", "price": "100", "total": "300"},
        ])

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM estimate_items WHERE estimate_id = %s", (estimate_id,))
                count_before = cur.fetchone()["cnt"]
        self.assertEqual(count_before, 1)

        apply_payload = {
            "rows": [
                {"row_type": "item", "name": "Новая позиция", "sort_order": 1, "unit": "шт", "quantity": "5", "price": "200", "total": "1000"},
            ]
        }

        request = make_request(f"/estimates/{estimate_id}/import-excel/apply", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("webapp.standalone_estimate_api._username", return_value="tester"), \
             patch("webapp.standalone_estimate_api._load_payload", return_value=apply_payload):
            response = asyncio.run(standalone_api.import_excel_apply(estimate_id, request))

        self.assertEqual(response.status_code, 200)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM estimate_items WHERE estimate_id = %s", (estimate_id,))
                count_after = cur.fetchone()["cnt"]

        self.assertEqual(count_after, 2, "Apply should append, not replace")

    def test_apply_rejects_empty_rows(self):
        estimate_id = self._create_draft_estimate()

        apply_payload = {"rows": []}

        request = make_request(f"/estimates/{estimate_id}/import-excel/apply", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("webapp.standalone_estimate_api._username", return_value="tester"), \
             patch("webapp.standalone_estimate_api._load_payload", return_value=apply_payload):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(standalone_api.import_excel_apply(estimate_id, request))
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("rows", ctx.exception.detail.lower())


class ImportStatusGuardTests(ExcelImportRouteTests):

    def test_import_forbidden_for_sent_status(self):
        estimate_id = self._create_and_send_estimate()

        xlsx_bytes = _build_xlsx_bytes(BASIC_ROWS, headers_row=BASIC_HEADERS)

        async def patched_form(req):
            from starlette.datastructures import FormData, UploadFile
            buf = io.BytesIO(xlsx_bytes)
            upload = UploadFile(filename="estimate.xlsx", file=buf)
            await upload.write(xlsx_bytes)
            await upload.seek(0)
            return FormData([("file", upload)])

        request = make_request(f"/estimates/{estimate_id}/import-excel/preview", method="POST", headers={"content-type": "multipart/form-data"})

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("starlette.requests.Request.form", patched_form):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(standalone_api.import_excel_preview(estimate_id, request))
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("черновик", ctx.exception.detail.lower())

    def test_import_forbidden_for_approved_status(self):
        estimate_id = self._create_and_approve_estimate()

        xlsx_bytes = _build_xlsx_bytes(BASIC_ROWS, headers_row=BASIC_HEADERS)

        async def patched_form(req):
            from starlette.datastructures import FormData, UploadFile
            buf = io.BytesIO(xlsx_bytes)
            upload = UploadFile(filename="estimate.xlsx", file=buf)
            await upload.write(xlsx_bytes)
            await upload.seek(0)
            return FormData([("file", upload)])

        request = make_request(f"/estimates/{estimate_id}/import-excel/preview", method="POST", headers={"content-type": "multipart/form-data"})

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("starlette.requests.Request.form", patched_form):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(standalone_api.import_excel_preview(estimate_id, request))
            self.assertEqual(ctx.exception.status_code, 400)

    def test_apply_forbidden_for_sent_status(self):
        estimate_id = self._create_and_send_estimate()

        apply_payload = {
            "rows": [
                {"row_type": "item", "name": "Позиция", "sort_order": 1, "unit": "шт", "quantity": "1", "price": "100", "total": "100"},
            ]
        }

        request = make_request(f"/estimates/{estimate_id}/import-excel/apply", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("webapp.standalone_estimate_api._username", return_value="tester"), \
             patch("webapp.standalone_estimate_api._load_payload", return_value=apply_payload):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(standalone_api.import_excel_apply(estimate_id, request))
            self.assertEqual(ctx.exception.status_code, 400)

    def test_apply_forbidden_for_approved_status(self):
        estimate_id = self._create_and_approve_estimate()

        apply_payload = {
            "rows": [
                {"row_type": "item", "name": "Позиция", "sort_order": 1, "unit": "шт", "quantity": "1", "price": "100", "total": "100"},
            ]
        }

        request = make_request(f"/estimates/{estimate_id}/import-excel/apply", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("webapp.standalone_estimate_api._username", return_value="tester"), \
             patch("webapp.standalone_estimate_api._load_payload", return_value=apply_payload):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(standalone_api.import_excel_apply(estimate_id, request))
            self.assertEqual(ctx.exception.status_code, 400)


class ImportPageTests(ExcelImportRouteTests):

    def test_import_excel_page_draft_returns_200(self):
        estimate_id = self._create_draft_estimate()
        request = make_request(f"/estimates/{estimate_id}/import-excel")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("webapp.standalone_estimate_api._username", return_value="tester"), \
             patch("webapp.standalone_estimate_api.templates.TemplateResponse") as mock_tr:
            response = standalone_api.import_excel_page(estimate_id, request)
            mock_tr.assert_called_once()
            call_args = mock_tr.call_args
            self.assertEqual(call_args[0][0], "import_excel.html")
            context = call_args[0][1]
            self.assertEqual(context["estimate"].id, estimate_id)

    def test_import_excel_page_non_draft_returns_400(self):
        estimate_id = self._create_and_send_estimate()
        request = make_request(f"/estimates/{estimate_id}/import-excel")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), \
             patch("webapp.standalone_estimate_api._username", return_value="tester"):
            with self.assertRaises(HTTPException) as ctx:
                standalone_api.import_excel_page(estimate_id, request)
            self.assertEqual(ctx.exception.status_code, 400)


class ImportAuthTests(ExcelImportRouteTests):

    def test_import_page_requires_auth(self):
        estimate_id = self._create_draft_estimate()
        request = make_request(f"/estimates/{estimate_id}/import-excel")
        with self.assertRaises(HTTPException) as ctx:
            standalone_api.import_excel_page(estimate_id, request)
        self.assertEqual(ctx.exception.status_code, 302)

    def test_preview_requires_auth(self):
        estimate_id = self._create_draft_estimate()
        request = make_request(f"/estimates/{estimate_id}/import-excel/preview", method="POST", headers={"content-type": "multipart/form-data"})
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(standalone_api.import_excel_preview(estimate_id, request))
        self.assertEqual(ctx.exception.status_code, 302)

    def test_apply_requires_auth(self):
        estimate_id = self._create_draft_estimate()
        request = make_request(f"/estimates/{estimate_id}/import-excel/apply", method="POST")
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(standalone_api.import_excel_apply(estimate_id, request))
        self.assertEqual(ctx.exception.status_code, 302)


class LegacyUntouchedTests(ExcelImportRouteTests):

    def test_legacy_estimate_routes_not_affected(self):
        with patch("webapp.main.require_auth", return_value=None), \
             patch("webapp.main.fetch_projects", return_value=[{"id": 6}]):
            import webapp.main as main
            legacy_response = main.estimates_redirect(make_request("/estimates"))
        self.assertEqual(legacy_response.status_code, 302)
        self.assertIn("/projects/", legacy_response.headers["location"])


class ImportExcelPageTemplateTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        cls.template_html = (Path(__file__).resolve().parent.parent / "webapp" / "templates" / "import_excel.html").read_text(encoding="utf-8")

    def test_append_warning_message_present(self):
        self.assertIn("импорт добавляет строки", self.template_html)

    def test_append_warning_is_alert_info(self):
        self.assertIn('class="alert alert-info', self.template_html)

    def test_apply_button_says_apply_import(self):
        self.assertIn('Применить импорт', self.template_html)

    def test_import_form_not_shown_for_non_draft(self):
        self.assertIn("estimate.status.value != 'draft'", self.template_html)


if __name__ == "__main__":
    unittest.main()