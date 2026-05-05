import asyncio
import io
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.datastructures import UploadFile
from starlette.requests import Request

import webapp.company_api as company_api
from webapp.company_api import _PNG_MAGIC, _MAX_UPLOAD_SIZE, _validate_png
from webapp.company_repository import CompanyCreateInput, CompanyService
from webapp.config import get_settings
from webapp.db import get_connection


def _make_png_bytes(size_bytes: int = 100) -> bytes:
    return _PNG_MAGIC + b"\x00" * max(0, size_bytes - len(_PNG_MAGIC))


def _make_request(path: str, *, method: str = "GET", session: dict | None = None) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "session": session or {},
    }
    return Request(scope)


class PngValidationTests(unittest.TestCase):
    def test_valid_png_passes(self):
        f = UploadFile(filename="stamp.png", file=io.BytesIO(_make_png_bytes(500)))
        f.headers = {"content-type": "image/png"}
        _validate_png(f, _make_png_bytes(500))

    def test_rejects_jpeg_content_type(self):
        f = UploadFile(filename="stamp.jpg", file=io.BytesIO(b"\xff\xd8\xff"))
        f.headers = {"content-type": "image/jpeg"}
        with self.assertRaises(HTTPException) as cm:
            _validate_png(f, b"\xff\xd8\xff")
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("PNG", cm.exception.detail)

    def test_rejects_wrong_extension(self):
        f = UploadFile(filename="stamp.gif", file=io.BytesIO(_PNG_MAGIC + b"\x00" * 10))
        f.headers = {"content-type": "image/png"}
        with self.assertRaises(HTTPException) as cm:
            _validate_png(f, _PNG_MAGIC + b"\x00" * 10)
        self.assertIn(".png", cm.exception.detail)

    def test_rejects_bad_magic_bytes(self):
        f = UploadFile(filename="stamp.png", file=io.BytesIO(b"\x00" * 100))
        f.headers = {"content-type": "image/png"}
        with self.assertRaises(HTTPException) as cm:
            _validate_png(f, b"\x00" * 100)
        self.assertIn("PNG", cm.exception.detail)

    def test_rejects_oversized(self):
        f = UploadFile(filename="stamp.png", file=io.BytesIO(_make_png_bytes(3 * 1024 * 1024)))
        f.headers = {"content-type": "image/png"}
        with self.assertRaises(HTTPException) as cm:
            _validate_png(f, _make_png_bytes(3 * 1024 * 1024))
        self.assertIn("слишком большой", cm.exception.detail)

    def test_allows_missing_content_type(self):
        f = UploadFile(filename="stamp.png", file=io.BytesIO(_make_png_bytes(500)))
        f.headers = {}
        _validate_png(f, _make_png_bytes(500))


class CompanyApiRouteTests(unittest.TestCase):
    def setUp(self):
        self.service = CompanyService()
        self._created_company_ids = []
        self._created_asset_dirs = []

    def tearDown(self):
        for cid in self._created_company_ids:
            self.service.update_company(cid, company_api.CompanyUpdateInput(is_active=False))
        for d in self._created_asset_dirs:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)

    def _create_test_company(self, **kwargs):
        defaults = {
            "legal_name": "Тест API компания",
            "short_name": f"UTEST_API_{id(self)}_{len(self._created_company_ids)}",
            "inn": "1111111111",
        }
        defaults.update(kwargs)
        company = self.service.create_company(CompanyCreateInput(**defaults))
        self._created_company_ids.append(company.id)
        return company

    def test_companies_list_requires_auth(self):
        request = _make_request("/settings/companies", session={})
        with self.assertRaises(HTTPException) as cm:
            company_api.companies_list(request)
        self.assertEqual(cm.exception.status_code, 302)

    def test_companies_list_returns_template(self):
        request = _make_request("/settings/companies", session={"is_authenticated": True, "username": "test"})
        with patch("webapp.company_api.templates.TemplateResponse") as mock_tr:
            company_api.companies_list(request)
            mock_tr.assert_called_once()
            ctx = mock_tr.call_args[0][1]
            self.assertIn("companies", ctx)

    def test_company_detail_requires_auth(self):
        request = _make_request("/settings/companies/1", session={})
        with self.assertRaises(HTTPException):
            company_api.company_detail(1, request)

    def test_company_detail_not_found(self):
        request = _make_request("/settings/companies/999999", session={"is_authenticated": True, "username": "test"})
        with self.assertRaises(HTTPException) as cm:
            company_api.company_detail(999999, request)
        self.assertEqual(cm.exception.status_code, 404)

    def test_company_detail_returns_template(self):
        company = self._create_test_company()
        request = _make_request(f"/settings/companies/{company.id}", session={"is_authenticated": True, "username": "test"})
        with patch("webapp.company_api.templates.TemplateResponse") as mock_tr:
            company_api.company_detail(company.id, request)
            ctx = mock_tr.call_args[0][1]
            self.assertEqual(ctx["company"].id, company.id)

    def test_serve_stamp_requires_auth(self):
        request = _make_request("/settings/companies/1/stamp", session={})
        with self.assertRaises(HTTPException) as cm:
            company_api.company_serve_stamp(1, request)
        self.assertEqual(cm.exception.status_code, 302)

    def test_serve_stamp_not_found_without_file(self):
        company = self._create_test_company()
        request = _make_request(f"/settings/companies/{company.id}/stamp", session={"is_authenticated": True, "username": "test"})
        with self.assertRaises(HTTPException) as cm:
            company_api.company_serve_stamp(company.id, request)
        self.assertEqual(cm.exception.status_code, 404)

    def test_serve_stamp_returns_png_after_upload(self):
        company = self._create_test_company()
        assets_dir = get_settings().storage_root / "company-assets" / str(company.id)
        self._created_asset_dirs.append(str(assets_dir))
        png_data = _make_png_bytes(500)
        assets_dir.mkdir(parents=True, exist_ok=True)
        stamp_path = assets_dir / "stamp.png"
        stamp_path.write_bytes(png_data)
        from webapp.storage import storage_relative_path
        self.service.set_company_asset_paths(company.id, stamp_path=storage_relative_path(stamp_path))

        request = _make_request(f"/settings/companies/{company.id}/stamp", session={"is_authenticated": True, "username": "test"})
        response = company_api.company_serve_stamp(company.id, request)
        self.assertEqual(response.media_type, "image/png")

    def test_asset_file_not_in_static(self):
        company = self._create_test_company()
        assets_dir = get_settings().storage_root / "company-assets" / str(company.id)
        static_dir = Path(__file__).resolve().parent.parent / "webapp" / "static"
        self.assertFalse(str(assets_dir).startswith(str(static_dir)))

    def test_upload_stamp_writes_file_and_updates_db(self):
        company = self._create_test_company()
        assets_dir = get_settings().storage_root / "company-assets" / str(company.id)
        self._created_asset_dirs.append(str(assets_dir))
        png_data = _make_png_bytes(500)

        async def _run():
            fake_file = UploadFile(filename="stamp.png", file=io.BytesIO(png_data))
            scope = {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": f"/settings/companies/{company.id}/stamp",
                "raw_path": f"/settings/companies/{company.id}/stamp".encode(),
                "query_string": b"",
                "headers": [(b"content-type", b"multipart/form-data")],
                "client": ("testclient", 123),
                "server": ("testserver", 80),
                "session": {"is_authenticated": True, "username": "test"},
            }
            request = Request(scope)
            request._form = {"file": fake_file}
            response = await company_api.company_upload_stamp(company.id, request)
            self.assertEqual(response.status_code, 303)

        asyncio.run(_run())
        updated = self.service.get_company(company.id)
        self.assertIsNotNone(updated.stamp_path)
        self.assertIn("stamp.png", updated.stamp_path)

    def test_upload_signature_writes_file_and_updates_db(self):
        company = self._create_test_company()
        assets_dir = get_settings().storage_root / "company-assets" / str(company.id)
        self._created_asset_dirs.append(str(assets_dir))
        png_data = _make_png_bytes(500)

        async def _run():
            fake_file = UploadFile(filename="signature.png", file=io.BytesIO(png_data))
            scope = {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": f"/settings/companies/{company.id}/signature",
                "raw_path": f"/settings/companies/{company.id}/signature".encode(),
                "query_string": b"",
                "headers": [(b"content-type", b"multipart/form-data")],
                "client": ("testclient", 123),
                "server": ("testserver", 80),
                "session": {"is_authenticated": True, "username": "test"},
            }
            request = Request(scope)
            request._form = {"file": fake_file}
            response = await company_api.company_upload_signature(company.id, request)
            self.assertEqual(response.status_code, 303)

        asyncio.run(_run())
        updated = self.service.get_company(company.id)
        self.assertIsNotNone(updated.signature_path)
        self.assertIn("signature.png", updated.signature_path)


if __name__ == "__main__":
    unittest.main()