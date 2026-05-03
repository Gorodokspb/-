import asyncio
import json
import shutil
import unittest
from urllib.parse import urlencode
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

import webapp.main as main
import webapp.standalone_estimate_api as standalone_api
from webapp.config import get_settings
from webapp.db import get_connection


def make_request(path: str, *, method: str = "GET", query: dict | None = None, session: dict | None = None, headers: dict[str, str] | None = None) -> Request:
    query_string = urlencode(query or {}, doseq=True).encode("utf-8")
    request_headers = [(b"content-type", b"application/json")]
    if headers:
        request_headers = [(name.encode("utf-8"), value.encode("utf-8")) for name, value in headers.items()]
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


class StandaloneEstimateRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = get_settings()
        cls.storage_dir = cls.settings.estimates_dir / "standalone-estimates"

    def setUp(self):
        self._cleanup_tables()
        self._cleanup_storage()

    def tearDown(self):
        self._cleanup_tables()
        self._cleanup_storage()

    def _cleanup_tables(self):
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

    def _create_estimate(self, payload=None):
        payload = payload or {
            "estimate_number": "ST-001",
            "title": "Самостоятельная смета",
            "customer_name": "Иван",
            "object_name": "Тестовый объект",
            "company_name": "ООО Декорартстрой",
            "contract_label": "Д-1",
            "items": [
                {
                    "name": "Штукатурка",
                    "sort_order": 10,
                    "quantity": "2",
                    "price": "100",
                    "total": "200",
                    "discounted_total": "180",
                }
            ],
        }
        request = make_request("/estimates", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="tester"
        ), patch("webapp.standalone_estimate_api._load_payload", return_value=payload):
            response = asyncio.run(standalone_api.standalone_estimate_create(request))
        self.assertEqual(response.status_code, 201)
        return response.body.decode("utf-8")

    def test_get_estimates_new_returns_backend_template_without_touching_legacy_redirect(self):
        request = make_request("/estimates/new")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None):
            response = standalone_api.standalone_estimate_new(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('"estimate_type":"primary"', response.body.decode("utf-8"))
        self.assertIn('"origin_channel":"web"', response.body.decode("utf-8"))

        with patch("webapp.main.require_auth", return_value=None), patch(
            "webapp.main.fetch_projects", return_value=[{"id": 6}]
        ):
            legacy = main.estimates_redirect(make_request("/estimates"))
        self.assertEqual(legacy.status_code, 302)
        self.assertEqual(legacy.headers["location"], "/projects/6/estimate")

    def test_create_and_get_standalone_estimate_routes(self):
        created_json = self._create_estimate()
        self.assertIn('"status":"draft"', created_json)
        self.assertIn('"download_urls":{"json":"/estimates/', created_json)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])

        request = make_request(f"/estimates/{estimate_id}")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None):
            fetched = standalone_api.standalone_estimate_get(estimate_id, request)
        body = fetched.body.decode("utf-8")
        self.assertEqual(fetched.status_code, 200)
        self.assertIn('"estimate_number":"ST-001"', body)
        self.assertIn('"items":[{', body)
        self.assertIn('"versions":[{', body)

    def test_standalone_estimate_save_form_redirects_to_editor(self):
        self._create_estimate()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="manager"
        ), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={"title": "Редактированная standalone-смета", "customer_name": "Петров", "items": []},
        ):
            response = asyncio.run(
                standalone_api.standalone_estimate_update(
                    estimate_id,
                    make_request(
                        f"/estimates/{estimate_id}",
                        method="POST",
                        headers={"content-type": "application/x-www-form-urlencoded"},
                    ),
                )
            )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], f"/estimates/{estimate_id}/edit")

    def test_update_send_approve_and_reject_routes_manage_versions_and_status_history(self):
        self._create_estimate()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="manager"
        ), patch(
            "webapp.standalone_estimate_api._load_payload",
            side_effect=[
                {
                    "title": "Обновлённая standalone-смета",
                    "customer_name": "Петров",
                    "items": [
                        {
                            "name": "Покраска",
                            "sort_order": 20,
                            "quantity": "5",
                            "price": "200",
                            "total": "1000",
                            "discounted_total": "900",
                        }
                    ],
                },
                {"stamp_applied": True, "signature_applied": True, "comment": "Клиент согласовал"},
                {"comment": "Архивный сценарий проверки reject route"},
            ],
        ):
            updated = asyncio.run(
                standalone_api.standalone_estimate_update(
                    estimate_id,
                    make_request(f"/estimates/{estimate_id}", method="POST"),
                )
            )
            sent = standalone_api.standalone_estimate_send(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/send", method="POST"),
            )
            approved = asyncio.run(
                standalone_api.standalone_estimate_approve(
                    estimate_id,
                    make_request(f"/estimates/{estimate_id}/approve", method="POST"),
                )
            )
            rejected = asyncio.run(
                standalone_api.standalone_estimate_reject(
                    estimate_id,
                    make_request(f"/estimates/{estimate_id}/reject", method="POST"),
                )
            )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(rejected.status_code, 200)
        self.assertIn('"status":"sent"', sent.body.decode("utf-8"))
        self.assertIn('"status":"approved"', approved.body.decode("utf-8"))
        self.assertIn('"status":"rejected"', rejected.body.decode("utf-8"))

        request = make_request(f"/estimates/{estimate_id}")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None):
            details = standalone_api.standalone_estimate_get(estimate_id, request)
        body = details.body.decode("utf-8")
        self.assertIn('"approved_version_id":', body)
        self.assertIn('"status_history":[', body)
        self.assertIn('"new_status":"sent"', body)
        self.assertIn('"new_status":"approved"', body)
        self.assertIn('"new_status":"rejected"', body)

    def test_send_creates_version_snapshot_with_sent_status(self):
        self._create_estimate()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="manager"
        ):
            response = standalone_api.standalone_estimate_send(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/send", method="POST"),
            )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.body.decode("utf-8"))
        details = standalone_api.service.get_estimate(estimate_id)
        sent_version = details.versions[-1]

        self.assertEqual(body["estimate"]["status"], "sent")
        self.assertEqual(details.estimate.status.value, "sent")
        self.assertEqual(details.estimate.current_version_id, sent_version["id"])
        self.assertEqual(sent_version["version_kind"].value, "sent")
        self.assertEqual(sent_version["status_at_save"].value, "sent")
        self.assertEqual(sent_version["snapshot_json"]["estimate"]["status"], "sent")
        self.assertEqual(details.status_history[-1]["old_status"], "draft")
        self.assertEqual(details.status_history[-1]["new_status"], "sent")

    def test_approve_creates_approved_version_snapshot_and_links(self):
        self._create_estimate()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="manager"
        ):
            standalone_api.standalone_estimate_send(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/send", method="POST"),
            )
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="manager"
        ), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={"stamp_applied": True, "signature_applied": True, "comment": "Согласовано клиентом"},
        ):
            response = asyncio.run(
                standalone_api.standalone_estimate_approve(
                    estimate_id,
                    make_request(f"/estimates/{estimate_id}/approve", method="POST"),
                )
            )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.body.decode("utf-8"))
        details = standalone_api.service.get_estimate(estimate_id)
        approved_version = details.versions[-1]

        self.assertEqual(body["estimate"]["status"], "approved")
        self.assertEqual(details.estimate.status.value, "approved")
        self.assertEqual(details.estimate.current_version_id, approved_version["id"])
        self.assertEqual(details.estimate.approved_version_id, approved_version["id"])
        self.assertEqual(body["estimate"]["approved_version_id"], approved_version["id"])
        self.assertEqual(approved_version["version_kind"].value, "approved")
        self.assertEqual(approved_version["status_at_save"].value, "approved")
        self.assertTrue(approved_version["is_final"])
        self.assertTrue(approved_version["stamp_applied"])
        self.assertTrue(approved_version["signature_applied"])
        self.assertEqual(approved_version["snapshot_json"]["estimate"]["status"], "approved")
        self.assertEqual(details.status_history[-1]["old_status"], "sent")
        self.assertEqual(details.status_history[-1]["new_status"], "approved")

    def test_json_export_contains_rows_and_current_status(self):
        self._create_estimate(
            {
                "estimate_number": "ST-JSON",
                "title": "JSON экспорт",
                "customer_name": "Клиент JSON",
                "object_name": "Объект JSON",
                "company_name": "ООО Декорартстрой",
                "contract_label": "J-1",
                "discount": "7.5",
                "watermark": "draft",
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
        )
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="manager"
        ):
            standalone_api.standalone_estimate_send(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/send", method="POST"),
            )
            response = standalone_api.standalone_estimate_download_json(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/download/json"),
            )

        payload = json.loads(response.path.read_text(encoding="utf-8"))
        self.assertEqual(payload["estimate"]["title"], "JSON экспорт")
        self.assertEqual(payload["estimate"]["customer_name"], "Клиент JSON")
        self.assertEqual(payload["estimate"]["object_name"], "Объект JSON")
        self.assertEqual(payload["estimate"]["discount"], "7.50")
        self.assertEqual(payload["estimate"]["watermark"], "draft")
        self.assertEqual(payload["estimate"]["status"], "sent")
        self.assertEqual([item["row_type"] for item in payload["items"]], ["section", "item", "item"])
        self.assertEqual([item["name"] for item in payload["items"]], ["Подготовка", "Грунтовка", "Шпатлевка"])

    def test_generic_status_route_changes_status_without_creating_version(self):
        self._create_estimate()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])
        before_count = len(standalone_api.service.get_estimate(estimate_id).versions)

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="manager"
        ), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={"status": "sent", "comment": "Служебная смена статуса"},
        ):
            response = asyncio.run(
                standalone_api.standalone_estimate_change_status(
                    estimate_id,
                    make_request(f"/estimates/{estimate_id}/status", method="POST"),
                )
            )

        details = standalone_api.service.get_estimate(estimate_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(details.estimate.status.value, "sent")
        self.assertEqual(len(details.versions), before_count)
        self.assertEqual(details.status_history[-1]["old_status"], "draft")
        self.assertEqual(details.status_history[-1]["new_status"], "sent")
        self.assertEqual(details.status_history[-1]["comment"], "Служебная смена статуса")

    def test_status_route_and_download_routes_work_for_standalone_estimate(self):
        self._create_estimate(
            {
                "estimate_number": "ST-DOWNLOAD",
                "title": "Смета на выгрузку",
                "customer_name": "Клиент",
                "object_name": "Объект на выгрузку",
                "company_name": "ООО Декорартстрой",
                "contract_label": "D-22",
                "items": [{"name": "Монтаж", "sort_order": 1, "quantity": "1", "price": "500", "total": "500", "discounted_total": "500"}],
            }
        )
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="manager"
        ), patch("webapp.standalone_estimate_api._load_payload", side_effect=[{"status": "sent", "comment": "Ручная смена статуса"}, {}]):
            status_response = asyncio.run(
                standalone_api.standalone_estimate_change_status(
                    estimate_id,
                    make_request(f"/estimates/{estimate_id}/status", method="POST"),
                )
            )
            pdf_response = asyncio.run(
                standalone_api.standalone_estimate_pdf(
                    estimate_id,
                    make_request(f"/estimates/{estimate_id}/pdf", method="POST"),
                )
            )
            json_download = standalone_api.standalone_estimate_download_json(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/download/json"),
            )
            pdf_download = standalone_api.standalone_estimate_download_pdf(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/download/pdf"),
            )

        self.assertEqual(status_response.status_code, 200)
        self.assertIn('"status":"sent"', status_response.body.decode("utf-8"))
        self.assertEqual(pdf_response.status_code, 200)
        self.assertIn(f'"download_url":"/estimates/{estimate_id}/download/pdf"', pdf_response.body.decode("utf-8"))
        self.assertEqual(json_download.status_code, 200)
        self.assertEqual(json_download.media_type, "application/json")
        self.assertTrue(str(json_download.path).endswith(".json"))
        self.assertEqual(pdf_download.status_code, 200)
        self.assertEqual(pdf_download.media_type, "application/pdf")
        self.assertTrue(str(pdf_download.path).endswith(".pdf"))
        self.assertTrue(any(self.storage_dir.rglob("*.json")))
        self.assertTrue(any(self.storage_dir.rglob("*.pdf")))

    def test_pdf_route_rejects_stamp_and_signature_before_approval(self):
        self._create_estimate({"estimate_number": "ST-PDF", "title": "PDF", "items": []})
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])

        request = make_request(f"/estimates/{estimate_id}/pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={"stamp_applied": True, "signature_applied": True},
        ):
            with self.assertRaises(Exception) as exc_context:
                asyncio.run(standalone_api.standalone_estimate_pdf(estimate_id, request))
        self.assertIn("Печать и подпись", str(exc_context.exception))

    def _create_and_approve_estimate(self, items=None):
        payload = {
            "estimate_number": "ST-FINAL",
            "title": "Финальная смета",
            "customer_name": "Клиент Финал",
            "object_name": "Объект Финал",
            "company_name": "ООО Декорартстрой",
            "contract_label": "F-1",
            "items": items or [
                {"name": "Монтаж", "sort_order": 10, "quantity": "5", "price": "200", "total": "1000", "discounted_total": "950"},
            ],
        }
        self._create_estimate(payload)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])

        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="manager"
        ):
            standalone_api.standalone_estimate_send(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/send", method="POST"),
            )
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="manager"
        ), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={"stamp_applied": True, "signature_applied": True, "comment": "Согласовано"},
        ):
            asyncio.run(
                standalone_api.standalone_estimate_approve(
                    estimate_id,
                    make_request(f"/estimates/{estimate_id}/approve", method="POST"),
                )
            )
        return estimate_id

    def test_final_pdf_rejected_before_approval(self):
        self._create_estimate({"estimate_number": "ST-FINAL-REJ", "title": "Ранняя смета", "items": []})
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                estimate_id = int(cur.fetchone()["id"])

        request = make_request(f"/estimates/{estimate_id}/final-pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={},
        ):
            with self.assertRaises(HTTPException) as exc_context:
                asyncio.run(standalone_api.standalone_estimate_final_pdf(estimate_id, request))
        self.assertEqual(exc_context.exception.status_code, 400)
        self.assertIn("approved", str(exc_context.exception.detail).lower())

    def test_final_pdf_created_after_approval(self):
        estimate_id = self._create_and_approve_estimate()
        request = make_request(f"/estimates/{estimate_id}/final-pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={"stamp_applied": True, "signature_applied": True},
        ):
            response = asyncio.run(standalone_api.standalone_estimate_final_pdf(estimate_id, request))
        body = json.loads(response.body.decode("utf-8"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["pdf_generated"])
        self.assertEqual(body["snapshot_status"], "approved")
        self.assertIn("/download/final-pdf", body["download_url"])
        self.assertTrue(body["filename"].endswith("-approved.pdf"))

    def test_final_pdf_uses_approved_snapshot_not_current_data(self):
        estimate_id = self._create_and_approve_estimate(
            items=[{"name": "Оригинальная работа", "sort_order": 10, "quantity": "3", "price": "100", "total": "300", "discounted_total": "280"}]
        )
        details = standalone_api.service.get_estimate(estimate_id)
        approved_version_id = details.estimate.approved_version_id
        self.assertIsNotNone(approved_version_id)
        approved_snapshot_items = None
        for version in details.versions:
            if version["id"] == approved_version_id:
                approved_snapshot_items = version["snapshot_json"]["items"]
                break
        self.assertIsNotNone(approved_snapshot_items)
        approved_item_names = [item.get("name") for item in approved_snapshot_items]

        standalone_api.service.save_estimate_items(
            estimate_id,
            [standalone_api._normalize_items([{"name": "Изменённая работа", "sort_order": 10, "quantity": "1", "price": "9999", "total": "9999", "discounted_total": "9999"}])][0],
        )

        request = make_request(f"/estimates/{estimate_id}/final-pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={},
        ):
            response = asyncio.run(standalone_api.standalone_estimate_final_pdf(estimate_id, request))
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.body.decode("utf-8"))
        self.assertEqual(body["snapshot_status"], "approved")
        self.assertIn("Оригинальная работа", approved_item_names)

    def test_download_final_pdf_serves_approved_file(self):
        estimate_id = self._create_and_approve_estimate()
        request_post = make_request(f"/estimates/{estimate_id}/final-pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={},
        ):
            asyncio.run(standalone_api.standalone_estimate_final_pdf(estimate_id, request_post))

        request_get = make_request(f"/estimates/{estimate_id}/download/final-pdf")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None):
            response = standalone_api.standalone_estimate_download_final_pdf(estimate_id, request_get)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertTrue(str(response.path).endswith("-approved.pdf"))

    def test_download_final_pdf_404_before_generation(self):
        estimate_id = self._create_and_approve_estimate()
        request = make_request(f"/estimates/{estimate_id}/download/final-pdf")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None):
            with self.assertRaises(HTTPException) as exc_context:
                standalone_api.standalone_estimate_download_final_pdf(estimate_id, request)
        self.assertEqual(exc_context.exception.status_code, 404)

    def test_final_pdf_creates_documents_row_with_null_project_id(self):
        estimate_id = self._create_and_approve_estimate()
        request = make_request(f"/estimates/{estimate_id}/final-pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={},
        ):
            response = asyncio.run(standalone_api.standalone_estimate_final_pdf(estimate_id, request))
        body = json.loads(response.body.decode("utf-8"))
        document_id = body["document_id"]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, project_id, doc_type, pdf_path FROM documents WHERE id = %s", (document_id,))
                doc = cur.fetchone()
        self.assertIsNotNone(doc)
        self.assertIsNone(doc["project_id"])
        self.assertIn("standalone_", doc["doc_type"])
        self.assertTrue(str(doc["pdf_path"]).endswith("-approved.pdf"))

    def test_final_pdf_creates_estimate_documents_row(self):
        estimate_id = self._create_and_approve_estimate()
        details = standalone_api.service.get_estimate(estimate_id)
        approved_version_id = details.estimate.approved_version_id
        request = make_request(f"/estimates/{estimate_id}/final-pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={},
        ):
            response = asyncio.run(standalone_api.standalone_estimate_final_pdf(estimate_id, request))
        body = json.loads(response.body.decode("utf-8"))
        document_id = body["document_id"]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM estimate_documents WHERE document_id = %s",
                    (document_id,),
                )
                est_doc = cur.fetchone()
        self.assertIsNotNone(est_doc)
        self.assertEqual(int(est_doc["estimate_id"]), estimate_id)
        self.assertEqual(int(est_doc["estimate_version_id"]), approved_version_id)
        self.assertEqual(est_doc["kind"], "approved_pdf")
        self.assertTrue(est_doc["is_current"])

    def test_final_pdf_updates_approved_version_pdf_document_id(self):
        estimate_id = self._create_and_approve_estimate()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates WHERE id = %s", (estimate_id,))
                cur.execute("SELECT id FROM estimate_versions WHERE estimate_id = %s AND version_kind = 'approved' ORDER BY id DESC LIMIT 1", (estimate_id,))
                version_row = cur.fetchone()
        approved_version_id = int(version_row["id"])
        request = make_request(f"/estimates/{estimate_id}/final-pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={},
        ):
            response = asyncio.run(standalone_api.standalone_estimate_final_pdf(estimate_id, request))
        body = json.loads(response.body.decode("utf-8"))
        document_id = body["document_id"]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pdf_document_id FROM estimate_versions WHERE id = %s", (approved_version_id,))
                version = cur.fetchone()
        self.assertIsNotNone(version["pdf_document_id"])
        self.assertEqual(int(version["pdf_document_id"]), document_id)

    def test_final_pdf_updates_estimate_final_document_id(self):
        estimate_id = self._create_and_approve_estimate()
        request = make_request(f"/estimates/{estimate_id}/final-pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={},
        ):
            response = asyncio.run(standalone_api.standalone_estimate_final_pdf(estimate_id, request))
        body = json.loads(response.body.decode("utf-8"))
        document_id = body["document_id"]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT final_document_id FROM estimates WHERE id = %s", (estimate_id,))
                row = cur.fetchone()
        self.assertIsNotNone(row["final_document_id"])
        self.assertEqual(int(row["final_document_id"]), document_id)

    def test_final_pdf_signed_creates_signed_pdf_document_kind(self):
        estimate_id = self._create_and_approve_estimate()
        request = make_request(f"/estimates/{estimate_id}/final-pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={"stamp_applied": True, "signature_applied": True},
        ):
            response = asyncio.run(standalone_api.standalone_estimate_final_pdf(estimate_id, request))
        body = json.loads(response.body.decode("utf-8"))
        document_id = body["document_id"]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT doc_type FROM documents WHERE id = %s", (document_id,))
                doc = cur.fetchone()
                cur.execute("SELECT kind FROM estimate_documents WHERE document_id = %s", (document_id,))
                est_doc = cur.fetchone()
        self.assertEqual(doc["doc_type"], "standalone_signed_pdf")
        self.assertEqual(est_doc["kind"], "signed_pdf")

    def test_download_final_pdf_serves_from_db_when_final_document_id_exists(self):
        estimate_id = self._create_and_approve_estimate()
        request_post = make_request(f"/estimates/{estimate_id}/final-pdf", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._load_payload",
            return_value={},
        ):
            asyncio.run(standalone_api.standalone_estimate_final_pdf(estimate_id, request_post))
        request_get = make_request(f"/estimates/{estimate_id}/download/final-pdf")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None):
            response = standalone_api.standalone_estimate_download_final_pdf(estimate_id, request_get)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "application/pdf")


if __name__ == "__main__":
    unittest.main()
