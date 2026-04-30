import unittest
from unittest.mock import patch

from starlette.requests import Request

import webapp.standalone_estimate_api as standalone_api
from webapp.config import get_settings
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


class StandaloneEstimatesListRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = get_settings()

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
                cur.execute("DELETE FROM estimates")

    def test_standalone_estimates_list_requires_auth(self):
        request = make_request("/standalone-estimates", session={})
        with self.assertRaises(Exception) as cm:
            standalone_api.standalone_estimates_list(request)
        self.assertEqual(cm.exception.status_code, 302)

    @patch('webapp.standalone_estimate_api.templates.TemplateResponse')
    def test_standalone_estimates_list_renders_template(self, mock_template_response):
        # Create a test estimate
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO estimates (
                        estimate_number, title, status, estimate_type, origin_channel,
                        customer_name, object_name, created_by, updated_by, created_at, updated_at
                    ) VALUES (
                        'TEST-001', 'Test Estimate', 'draft', 'primary', 'web',
                        'Test Customer', 'Test Object', 'testuser', 'testuser', '2024-01-01T00:00:00', '2024-01-01T00:00:00'
                    )
                    RETURNING id
                """)
                estimate_id = cur.fetchone()["id"]

        request = make_request("/standalone-estimates", session={"is_authenticated": True, "username": "testuser"})
        response = standalone_api.standalone_estimates_list(request)

        # Check that TemplateResponse was called with correct template and context
        mock_template_response.assert_called_once_with(
            "standalone_estimates_list.html",
            {
                "request": request,
                "estimates": unittest.mock.ANY,  # We don't check the exact list here
                "username": "testuser",
            },
        )

        # Verify the response is the mock
        self.assertEqual(response, mock_template_response.return_value)

    def test_standalone_estimates_list_empty(self):
        request = make_request("/standalone-estimates", session={"is_authenticated": True, "username": "testuser"})
        with patch('webapp.standalone_estimate_api.templates.TemplateResponse') as mock_template_response:
            response = standalone_api.standalone_estimates_list(request)
            mock_template_response.assert_called_once()
            args, kwargs = mock_template_response.call_args
            self.assertEqual(args[0], "standalone_estimates_list.html")
            context = args[1]
            self.assertEqual(len(context["estimates"]), 0)

    def test_standalone_estimates_list_new_button_uses_standalone_route(self):
        with open("/opt/dekorcrm/app/CRM_OLD_BAD/webapp/templates/standalone_estimates_list.html", "r", encoding="utf-8") as f:
            template = f.read()
        self.assertIn('href="/standalone-estimates/new"', template)
        self.assertNotIn('href="/estimates/new"', template)

    def test_standalone_estimates_list_open_link_uses_editor_route(self):
        with open("/opt/dekorcrm/app/CRM_OLD_BAD/webapp/templates/standalone_estimates_list.html", "r", encoding="utf-8") as f:
            template = f.read()
        # Verify that the "Open" link uses the /edit endpoint
        self.assertIn('href="/estimates/{{ estimate.id }}/edit"', template)
        # Ensure it's not pointing to the raw JSON endpoint
        self.assertNotIn('<a href="/estimates/{{ estimate.id }}">Открыть</a>', template)


if __name__ == "__main__":
    unittest.main()