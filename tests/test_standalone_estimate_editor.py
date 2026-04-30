import asyncio
import json
import unittest
from unittest.mock import patch

from starlette.requests import Request

import webapp.standalone_estimate_api as standalone_api
from webapp.db import get_connection


def make_request(path: str, *, method: str = "GET", query: dict | None = None, session: dict | None = None, headers: dict[str, str] | None = None) -> Request:
    from urllib.parse import urlencode
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
        with self.assertRaises(Exception) as cm:
            standalone_api.standalone_estimate_editor(9999, request)
        self.assertIn("Estimate 9999 not found", str(cm.exception))

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

    @patch('webapp.standalone_estimate_api.templates.TemplateResponse')
    def test_create_edit_save_reopen_editor_workflow(self, mock_template_response):
        """Test the full workflow: create → add section/items → save → reopen editor."""
        mock_template_response.return_value.status_code = 200
        
        # Step 1: Create new estimate
        create_request = make_request("/standalone-estimates/new", session={"is_authenticated": True, "username": "testuser"})
        create_response = standalone_api.standalone_estimate_new_redirect(create_request)
        self.assertEqual(create_response.status_code, 302)
        location = create_response.headers["location"]
        self.assertTrue(location.endswith("/edit"))
        estimate_id = int(location.split("/")[-2])

        # Step 2: Open editor (should work)
        edit_request = make_request(f"/estimates/{estimate_id}/edit", session={"is_authenticated": True, "username": "testuser"})
        edit_response = standalone_api.standalone_estimate_editor(estimate_id, edit_request)
        self.assertEqual(edit_response.status_code, 200)

        # Step 3: Save estimate
        rows = [
            {"row_type": "section", "name": "Демонтаж"},
            {
                "row_type": "item",
                "name": "Снятие старых обоев",
                "unit": "м2",
                "quantity": "10",
                "price": "120",
                "total": "1200",
                "discounted_total": "1200",
                "reference": "D-001",
            },
            {
                "row_type": "item",
                "name": "Вынос мусора",
                "unit": "усл",
                "quantity": "1",
                "price": "500",
                "total": "500",
                "discounted_total": "500",
                "reference": "D-002",
            },
        ]
        save_payload = {
            "title": "Updated Standalone Estimate",
            "customer_name": "Updated Customer",
            "object_name": "Updated Object",
            "items_payload": json.dumps(rows, ensure_ascii=False),
        }
        save_request = make_request(
            f"/estimates/{estimate_id}",
            method="POST",
            session={"is_authenticated": True, "username": "testuser"},
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        with patch("webapp.standalone_estimate_api._load_payload", return_value=save_payload):
            save_response = asyncio.run(standalone_api.standalone_estimate_update(estimate_id, save_request))
        self.assertEqual(save_response.status_code, 303)
        self.assertEqual(save_response.headers["location"], f"/estimates/{estimate_id}/edit")

        # Step 4: Reopen editor (should still work after save)
        reopen_request = make_request(f"/estimates/{estimate_id}/edit", session={"is_authenticated": True, "username": "testuser"})
        reopen_response = standalone_api.standalone_estimate_editor(estimate_id, reopen_request)
        self.assertEqual(reopen_response.status_code, 200)

        # Verify the estimate still exists and has updated rows.
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT title, customer_name, object_name FROM estimates WHERE id = %s", (estimate_id,))
                row = cur.fetchone()
                cur.execute(
                    "SELECT row_type, name, unit, quantity, price, total, discounted_total, reference "
                    "FROM estimate_items WHERE estimate_id = %s ORDER BY sort_order, id",
                    (estimate_id,),
                )
                item_rows = cur.fetchall()
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "Updated Standalone Estimate")
        self.assertEqual(row["customer_name"], "Updated Customer")
        self.assertEqual(row["object_name"], "Updated Object")
        self.assertEqual([item["row_type"] for item in item_rows], ["section", "item", "item"])
        self.assertEqual([item["name"] for item in item_rows], ["Демонтаж", "Снятие старых обоев", "Вынос мусора"])

        args, kwargs = mock_template_response.call_args
        context = args[1]
        editor_rows = json.loads(context["editor_rows_json"])
        self.assertEqual([item["row_type"] for item in editor_rows], ["section", "item", "item"])
        self.assertEqual([item["name"] for item in editor_rows], ["Демонтаж", "Снятие старых обоев", "Вынос мусора"])

    def test_blank_items_payload_does_not_clear_saved_rows(self):
        estimate_id = self._create_estimate()
        standalone_api.service.save_estimate_items(
            estimate_id,
            standalone_api._normalize_items(
                [
                    {"row_type": "section", "name": "Существующий раздел"},
                    {
                        "row_type": "item",
                        "name": "Существующая позиция",
                        "quantity": "1",
                        "price": "100",
                        "total": "100",
                        "discounted_total": "100",
                    },
                ]
            ),
        )

        save_payload = {
            "title": "Updated Standalone Estimate",
            "items_payload": "",
        }
        save_request = make_request(
            f"/estimates/{estimate_id}",
            method="POST",
            session={"is_authenticated": True, "username": "testuser"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        with patch("webapp.standalone_estimate_api._load_payload", return_value=save_payload):
            save_response = asyncio.run(standalone_api.standalone_estimate_update(estimate_id, save_request))
        self.assertEqual(save_response.status_code, 303)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT row_type, name FROM estimate_items WHERE estimate_id = %s ORDER BY sort_order, id",
                    (estimate_id,),
                )
                rows = cur.fetchall()
        self.assertEqual([row["row_type"] for row in rows], ["section", "item"])
        self.assertEqual([row["name"] for row in rows], ["Существующий раздел", "Существующая позиция"])


if __name__ == "__main__":
    unittest.main()
