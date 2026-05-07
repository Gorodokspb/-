import asyncio
import unittest
from urllib.parse import urlencode
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

import webapp.standalone_estimate_api as standalone_api


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


class StandaloneEstimateCreateProjectTests(unittest.TestCase):
    """Route tests for POST /estimates/{id}/create-project (Stage 8.6.1)."""

    _CLEANUP_NOTE = "auto-test-create-project-8.6.1"

    @classmethod
    def setUpClass(cls):
        from webapp.config import get_settings
        cls.settings = get_settings()
        cls.storage_dir = cls.settings.estimates_dir / "standalone-estimates"
        cls._cleanup_projects_now()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_projects_now()

    @classmethod
    def _cleanup_projects_now(cls):
        from webapp.db import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM project_events WHERE project_id IN (SELECT id FROM projects WHERE notes = %s)", (cls._CLEANUP_NOTE,))
                cur.execute("DELETE FROM projects WHERE notes = %s", (cls._CLEANUP_NOTE,))
            conn.commit()

    def setUp(self):
        self._cleanup_estimates()
        self._cleanup_storage()

    def tearDown(self):
        self._cleanup_estimates()
        self._cleanup_storage()

    def _cleanup_estimates(self):
        from tests.db_guard import guard_live_database
        guard_live_database()
        from webapp.db import get_connection
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
        import shutil
        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)

    def _create_estimate(self, payload=None):
        payload = payload or {
            "estimate_number": "ST-CREATE-PROJ",
            "title": "Смета для создания проекта",
            "customer_name": "Заказчик Проект",
            "object_name": "Объект для проекта",
            "company_name": "ООО Декорартстрой",
            "contract_label": "CP-1",
            "items": [
                {"name": "Работа", "sort_order": 10, "quantity": "1", "price": "1000", "total": "1000", "discounted_total": "950"},
            ],
        }
        request = make_request("/estimates", method="POST")
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="tester"
        ), patch("webapp.standalone_estimate_api._load_payload", return_value=payload):
            response = asyncio.run(standalone_api.standalone_estimate_create(request))
        self.assertEqual(response.status_code, 201)
        from webapp.db import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estimates ORDER BY id DESC LIMIT 1")
                return int(cur.fetchone()["id"])

    def _create_and_approve_estimate(self):
        estimate_id = self._create_estimate()
        self._send(estimate_id)
        self._approve(estimate_id)
        return estimate_id

    def _send(self, estimate_id):
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="tester"
        ):
            standalone_api.standalone_estimate_send(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/send", method="POST"),
            )

    def _approve(self, estimate_id):
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="tester"
        ), patch("webapp.standalone_estimate_api._load_payload", return_value={
            "stamp_applied": False, "signature_applied": False, "comment": "approved for create-project test"
        }):
            asyncio.run(standalone_api.standalone_estimate_approve(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/approve", method="POST"),
            ))

    def _create_and_send_estimate(self):
        estimate_id = self._create_estimate()
        self._send(estimate_id)
        return estimate_id

    def _post_create_project(self, estimate_id, *, auth_patch=True, username="tester"):
        request = make_request(f"/estimates/{estimate_id}/create-project", method="POST", session={"is_authenticated": True, "username": username})
        patches = {}
        if auth_patch:
            patches["webapp.standalone_estimate_api._require_auth"] = patch("webapp.standalone_estimate_api._require_auth", return_value=None)
            patches["webapp.standalone_estimate_api._username"] = patch("webapp.standalone_estimate_api._username", return_value=username)
        with context_or_none(patches):
            return standalone_api.standalone_estimate_create_project(estimate_id, request)

    def test_approved_estimate_creates_project_and_redirects(self):
        estimate_id = self._create_and_approve_estimate()
        response = self._post_create_project(estimate_id)
        self.assertEqual(response.status_code, 302)
        location = response.headers["location"]
        self.assertTrue(location.startswith("/projects/"))
        project_id = int(location.rsplit("/", 1)[-1])
        from webapp.db import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id, status FROM estimates WHERE id = %s", (estimate_id,))
                row = cur.fetchone()
                self.assertEqual(row["project_id"], project_id)
                self.assertEqual(row["status"], "in_progress")
                cur.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
                self.assertIsNotNone(cur.fetchone())
        self._mark_test_project(project_id)

    def test_create_project_twice_rejects_duplicate(self):
        estimate_id = self._create_and_approve_estimate()
        response1 = self._post_create_project(estimate_id)
        self.assertEqual(response1.status_code, 302)
        project_id = int(response1.headers["location"].rsplit("/", 1)[-1])
        self._mark_test_project(project_id)
        with self.assertRaises(HTTPException) as ctx:
            self._post_create_project(estimate_id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("already linked", str(ctx.exception.detail).lower())

    def test_draft_estimate_rejected(self):
        estimate_id = self._create_estimate()
        with self.assertRaises(HTTPException) as ctx:
            self._post_create_project(estimate_id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("approved", str(ctx.exception.detail).lower())

    def test_sent_estimate_rejected(self):
        estimate_id = self._create_and_send_estimate()
        with self.assertRaises(HTTPException) as ctx:
            self._post_create_project(estimate_id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("approved", str(ctx.exception.detail).lower())

    def test_rejected_estimate_rejected(self):
        estimate_id = self._create_estimate()
        self._send(estimate_id)
        with patch("webapp.standalone_estimate_api._require_auth", return_value=None), patch(
            "webapp.standalone_estimate_api._username", return_value="tester"
        ), patch("webapp.standalone_estimate_api._load_payload", return_value={"comment": "rejected"}):
            asyncio.run(standalone_api.standalone_estimate_reject(
                estimate_id,
                make_request(f"/estimates/{estimate_id}/reject", method="POST"),
            ))
        with self.assertRaises(HTTPException) as ctx:
            self._post_create_project(estimate_id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("approved", str(ctx.exception.detail).lower())

    def test_create_project_requires_auth(self):
        estimate_id = self._create_and_approve_estimate()
        request = make_request(f"/estimates/{estimate_id}/create-project", method="POST", session={})
        with self.assertRaises(HTTPException) as ctx:
            standalone_api.standalone_estimate_create_project(estimate_id, request)
        self.assertEqual(ctx.exception.status_code, 302)

    def _mark_test_project(self, project_id):
        from webapp.db import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE projects SET notes = %s WHERE id = %s", (self._CLEANUP_NOTE, project_id))
            conn.commit()


class context_or_none:
    def __init__(self, patches):
        self._patches = patches or {}
        self._entered = []

    def __enter__(self):
        for key, p in self._patches.items():
            p.start()
            self._entered.append(p)

    def __exit__(self, *args):
        for p in self._entered:
            p.stop()


if __name__ == "__main__":
    unittest.main()
