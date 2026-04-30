import asyncio
import json
import unittest
from unittest.mock import patch

from starlette.requests import Request

import webapp.standalone_estimate_api as standalone_api
from webapp.db import get_connection


def make_request(path: str, *, method: str = "GET", query: dict | None = None, session: dict | None = None) -> Request:
    from urllib.parse import urlencode
    query_string = urlencode(query or {}, doseq=True).encode("utf-8")
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string,
        "headers": [(b"content-type", b"application/json")],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "session": session or {},
    }
    return Request(scope)


class StandaloneEstimateEditorRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        self._cleanup_tables()

    def tearDown(self):
        self._cleanup_tables()

    def _cleanup_tables(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM estimate_versions")
                cur.execute("DELETE FROM estimate_status_history")
                cur.execute("DELETE FROM estimate_documents")
                cur.execute("DELETE FROM estimate_items")
                cur.execute("DELETE FROM estimates")
            conn.commit()

    def _create_estimate(self):
        """Helper to create a test estimate."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO estimates (
                        estimate_number, title, status, estimate_type, origin_channel,
                        customer_name, object_name, company_name, created_by, updated_by, created_at, updated_at
                    ) VALUES (
                        'EDITOR-001', 'Test Editor Estimate', 'draft', 'primary', 'web',
                        'Test Customer', 'Test Object', 'ООО Декорартстрой', 'testuser', 'testuser', 
                        '2024-01-01T00:00:00', '2024-01-01T00:00:00'
                    )
                    RETURNING id
                """)
                estimate_id = int(cur.fetchone()["id"])
            conn.commit()
        return estimate_id

    def test_standalone_estimate_editor_requires_auth(self):
        estimate_id = self._create_estimate()
        request = make_request(f"/estimates/{estimate_id}/edit", session={})
        with self.assertRaises(Exception) as cm:
            standalone_api.standalone_estimate_editor(estimate_id, request)
        self.assertEqual(cm.exception.status_code, 302)

    @patch('webapp.standalone_estimate_api.templates.TemplateResponse')
    def test_standalone_estimate_editor_renders_template(self, mock_template_response):
        estimate_id = self._create_estimate()
        request = make_request(f"/estimates/{estimate_id}/edit", session={"is_authenticated": True, "username": "testuser"})
        
        response = standalone_api.standalone_estimate_editor(estimate_id, request)
        
        # Verify TemplateResponse was called with correct template
        mock_template_response.assert_called_once()
        args, kwargs = mock_template_response.call_args
        self.assertEqual(args[0], "standalone_estimate_editor.html")
        
        # Check context
        context = args[1]
        self.assertEqual(context["estimate"].id, estimate_id)
        self.assertEqual(context["estimate"].estimate_number, "EDITOR-001")
        self.assertEqual(context["username"], "testuser")
        self.assertIn("price_library_json", context)
        self.assertIn("estimate_calc_state_json", context)

    @patch('webapp.standalone_estimate_api.templates.TemplateResponse')
    def test_standalone_estimate_editor_context_values(self, mock_template_response):
        estimate_id = self._create_estimate()
        request = make_request(f"/estimates/{estimate_id}/edit", session={"is_authenticated": True, "username": "testuser"})
        
        standalone_api.standalone_estimate_editor(estimate_id, request)
        
        args, kwargs = mock_template_response.call_args
        context = args[1]
        
        # Verify that price_library_json is valid JSON
        try:
            price_lib = json.loads(context["price_library_json"])
            self.assertIsInstance(price_lib, list)
        except json.JSONDecodeError:
            self.fail("price_library_json is not valid JSON")
        
        # Verify calc_state_json is valid JSON
        try:
            calc_state = json.loads(context["estimate_calc_state_json"])
            self.assertIsInstance(calc_state, dict)
        except json.JSONDecodeError:
            self.fail("estimate_calc_state_json is not valid JSON")

    def test_standalone_estimate_editor_404_for_missing_estimate(self):
        request = make_request("/estimates/9999/edit", session={"is_authenticated": True, "username": "testuser"})
        with self.assertRaises(Exception):
            standalone_api.standalone_estimate_editor(9999, request)

    @patch('webapp.standalone_estimate_api.templates.TemplateResponse')
    def test_standalone_editor_does_not_require_project_data(self, mock_template_response):
        """Verify that standalone editor works with project_id=None."""
        estimate_id = self._create_estimate()
        request = make_request(f"/estimates/{estimate_id}/edit", session={"is_authenticated": True, "username": "testuser"})
        
        response = standalone_api.standalone_estimate_editor(estimate_id, request)
        
        args, kwargs = mock_template_response.call_args
        context = args[1]
        
        # Confirm estimate has no project_id
        self.assertIsNone(context["estimate"].project_id)
        # And template still renders successfully
        self.assertEqual(context["estimate"].id, estimate_id)

    def test_new_standalone_estimate_redirects_to_editor(self):
        request = make_request("/standalone-estimates/new", session={"is_authenticated": True, "username": "testuser"})
        response = standalone_api.standalone_estimate_new_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["location"].endswith("/edit"))

        estimate_id = int(response.headers["location"].split("/")[-2])
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, estimate_number FROM estimates WHERE id = %s", (estimate_id,))
                row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["id"], estimate_id)


if __name__ == "__main__":
    unittest.main()
