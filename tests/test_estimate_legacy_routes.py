import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from starlette.requests import Request

import webapp.main as main


def make_request(path: str = "/", *, method: str = "GET", query: dict | None = None, session: dict | None = None) -> Request:
    query_string = urlencode(query or {}, doseq=True).encode("utf-8")
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string,
        "headers": [],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "session": session or {},
    }
    return Request(scope)


class LegacyEstimateRouteTests(unittest.TestCase):
    def test_estimates_redirects_to_first_project_estimate(self):
        request = make_request("/estimates")

        with patch("webapp.main.require_auth", return_value=None), patch(
            "webapp.main.fetch_projects", return_value=[{"id": 7}]
        ):
            response = main.estimates_redirect(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/projects/7/estimate")

    def test_estimates_redirects_to_projects_when_no_project_exists(self):
        request = make_request("/estimates")

        with patch("webapp.main.require_auth", return_value=None), patch(
            "webapp.main.fetch_projects", return_value=[]
        ):
            response = main.estimates_redirect(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/projects")

    def test_calculator_redirects_to_first_project_estimate_with_tool_flag(self):
        request = make_request("/calculator")

        with patch("webapp.main.require_auth", return_value=None), patch(
            "webapp.main.fetch_projects", return_value=[{"id": 6}]
        ):
            response = main.calculator_redirect(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/projects/6/estimate?tool=calculator")

    def test_project_estimate_page_passes_saved_flag_to_renderer(self):
        captured = {}
        estimate = {"project": {"id": 6, "project_name": "Test", "address": "Addr"}}
        request = make_request("/projects/6/estimate", query={"saved": "1"})

        def fake_render(request, estimate_arg, *, saved=False, error=None, status_code=200):
            captured.update(
                {
                    "estimate": estimate_arg,
                    "saved": saved,
                    "error": error,
                    "status_code": status_code,
                }
            )
            return {"saved": saved, "project_id": estimate_arg["project"]["id"]}

        with patch("webapp.main.require_auth", return_value=None), patch(
            "webapp.main.fetch_project_estimate", return_value=estimate
        ), patch("webapp.main.render_estimate_editor", side_effect=fake_render):
            response = main.project_estimate_page(6, request)

        self.assertEqual(response, {"saved": True, "project_id": 6})
        self.assertIs(captured["estimate"], estimate)
        self.assertTrue(captured["saved"])
        self.assertIsNone(captured["error"])

    def test_project_estimate_save_rejects_empty_object_before_persist(self):
        estimate = {"project": {"id": 6, "project_name": "Legacy", "address": ""}}
        draft_estimate = {
            **estimate,
            "company": "ООО Декорартстрой",
            "object_name": "",
            "customer_name": "",
            "contract_label": "",
            "discount": "",
            "watermark": True,
            "calc_state": {},
            "editor_rows": [],
            "editor_rows_json": "[]",
        }
        render_calls = {}
        request = make_request("/projects/6/estimate", method="POST")

        def fake_render(request, estimate_arg, *, saved=False, error=None, status_code=200):
            render_calls.update({"estimate": estimate_arg, "error": error, "status_code": status_code})
            return {"error": error, "status_code": status_code}

        with patch("webapp.main.require_auth", return_value=None), patch(
            "webapp.main.fetch_project_estimate", return_value=estimate
        ), patch(
            "webapp.main.normalize_estimate_form_data", return_value=(draft_estimate, [], {})
        ), patch("webapp.main.render_estimate_editor", side_effect=fake_render), patch(
            "webapp.main.save_project_estimate"
        ) as save_mock:
            response = main.project_estimate_save(
                6,
                request,
                company_name="ООО Декорартстрой",
                object_name="",
                customer_name="",
                contract_label="",
                discount="",
                items_payload="[]",
                calc_state_payload="{}",
                watermark=None,
            )

        self.assertEqual(response["status_code"], 400)
        self.assertEqual(response["error"], "Укажите объект сметы перед сохранением.")
        save_mock.assert_not_called()
        self.assertEqual(render_calls["status_code"], 400)

    def test_project_estimate_save_persists_normalized_payload_and_redirects(self):
        estimate = {"project": {"id": 6, "project_name": "Legacy", "address": "Адрес"}}
        editor_rows = [{"row_type": "item", "name": "Штукатурка", "quantity": "2", "price": "100"}]
        calc_state = {"wall_height": "3"}
        draft_estimate = {
            **estimate,
            "company": "ООО Декорартстрой",
            "object_name": "Адрес",
            "customer_name": "Иван",
            "contract_label": "01/24",
            "discount": "10",
            "watermark": True,
            "calc_state": calc_state,
            "editor_rows": editor_rows,
            "editor_rows_json": "[]",
        }
        request = make_request("/projects/6/estimate", method="POST")

        with patch("webapp.main.require_auth", return_value=None), patch(
            "webapp.main.fetch_project_estimate", return_value=estimate
        ), patch(
            "webapp.main.normalize_estimate_form_data", return_value=(draft_estimate, editor_rows, calc_state)
        ), patch("webapp.main.save_project_estimate", return_value={"id": 99}) as save_mock:
            response = main.project_estimate_save(
                6,
                request,
                company_name="ООО Декорартстрой",
                object_name="Адрес",
                customer_name="Иван",
                contract_label="01/24",
                discount="10",
                items_payload="[]",
                calc_state_payload="{}",
                watermark="on",
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/projects/6/estimate?saved=1")
        save_mock.assert_called_once_with(
            project_id=6,
            username=main.settings.admin_username,
            company_name="ООО Декорартстрой",
            object_name="Адрес",
            customer_name="Иван",
            contract_label="01/24",
            discount_raw="10",
            watermark=True,
            editor_rows=editor_rows,
            calc_state=calc_state,
        )

    def test_project_estimate_pdf_requires_object_customer_and_contract(self):
        estimate = {"project": {"id": 7, "project_name": "Legacy", "address": "Тамбасова"}}
        draft_estimate = {
            **estimate,
            "company": "ООО Декорартстрой",
            "object_name": "",
            "customer_name": "",
            "contract_label": "",
            "discount": "",
            "watermark": True,
            "calc_state": {},
            "editor_rows": [],
            "editor_rows_json": "[]",
        }
        request = make_request("/projects/7/estimate/pdf", method="POST")

        def fake_render(request, estimate_arg, *, saved=False, error=None, status_code=200):
            return {"error": error, "status_code": status_code}

        with patch("webapp.main.require_auth", return_value=None), patch(
            "webapp.main.fetch_project_estimate", return_value=estimate
        ), patch(
            "webapp.main.normalize_estimate_form_data", return_value=(draft_estimate, [], {})
        ), patch("webapp.main.render_estimate_editor", side_effect=fake_render), patch(
            "webapp.main.save_project_estimate"
        ) as save_mock, patch("webapp.main.generate_estimate_pdf") as pdf_mock:
            response = main.project_estimate_pdf(
                7,
                request,
                company_name="ООО Декорартстрой",
                object_name="",
                customer_name="",
                contract_label="",
                discount="",
                items_payload="[]",
                calc_state_payload="{}",
                watermark=None,
            )

        self.assertEqual(response["status_code"], 400)
        self.assertEqual(response["error"], "Для PDF заполните: объект, заказчика, договор.")
        save_mock.assert_not_called()
        pdf_mock.assert_not_called()

    def test_project_estimate_pdf_saves_and_streams_generated_file(self):
        estimate = {"project": {"id": 7, "project_name": "Legacy", "address": "Тамбасова"}}
        editor_rows = [{"row_type": "item", "name": "Монтаж", "quantity": "1", "price": "500"}]
        calc_state = {"floor_length": "4"}
        saved_estimate = {"id": 8, "project": estimate["project"]}
        draft_estimate = {
            **estimate,
            "company": "ООО Декорартстрой",
            "object_name": "Тамбасова 7",
            "customer_name": "Петров",
            "contract_label": "12/26",
            "discount": "",
            "watermark": True,
            "calc_state": calc_state,
            "editor_rows": editor_rows,
            "editor_rows_json": "[]",
        }
        request = make_request("/projects/7/estimate/pdf", method="POST")

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "legacy-estimate.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nlegacy test pdf")

            with patch("webapp.main.require_auth", return_value=None), patch(
                "webapp.main.fetch_project_estimate", return_value=estimate
            ), patch(
                "webapp.main.normalize_estimate_form_data", return_value=(draft_estimate, editor_rows, calc_state)
            ), patch("webapp.main.save_project_estimate", return_value=saved_estimate) as save_mock, patch(
                "webapp.main.generate_estimate_pdf", return_value=pdf_path
            ) as pdf_mock:
                response = main.project_estimate_pdf(
                    7,
                    request,
                    company_name="ООО Декорартстрой",
                    object_name="Тамбасова 7",
                    customer_name="Петров",
                    contract_label="12/26",
                    discount="",
                    items_payload="[]",
                    calc_state_payload="{}",
                    watermark="on",
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Path(response.path), pdf_path)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertIn("legacy-estimate.pdf", response.headers.get("content-disposition", ""))
        save_mock.assert_called_once()
        pdf_mock.assert_called_once_with(saved_estimate, main.settings.admin_username)

    def test_download_document_returns_requested_draft_and_pdf_variants(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            draft_path = Path(tmpdir) / "legacy.json"
            pdf_path = Path(tmpdir) / "legacy.pdf"
            draft_path.write_text('{"legacy": true}', encoding="utf-8")
            pdf_path.write_bytes(b"%PDF-1.4\nlegacy download")
            document = {
                "id": 5,
                "file_path": "primary.bin",
                "draft_path": "draft.json",
                "pdf_path": "estimate.pdf",
            }
            request = make_request("/documents/5/download")

            def fake_resolve(path: str):
                if path == "draft.json":
                    return draft_path
                if path == "estimate.pdf":
                    return pdf_path
                return None

            with patch("webapp.main.require_auth", return_value=None), patch(
                "webapp.main.fetch_document", return_value=document, create=True
            ), patch("webapp.main.resolve_storage_path", side_effect=fake_resolve):
                draft_response = main.download_document(5, request, kind="draft")
                pdf_response = main.download_document(5, request, kind="pdf")

        self.assertEqual(draft_response.status_code, 200)
        self.assertEqual(Path(draft_response.path), draft_path)
        self.assertIn("legacy.json", draft_response.headers.get("content-disposition", ""))
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(Path(pdf_response.path), pdf_path)
        self.assertIn("legacy.pdf", pdf_response.headers.get("content-disposition", ""))

    def test_download_document_returns_404_when_requested_variant_is_missing(self):
        document = {"id": 5, "file_path": "", "draft_path": "", "pdf_path": ""}
        request = make_request("/documents/5/download")

        with patch("webapp.main.require_auth", return_value=None), patch(
            "webapp.main.fetch_document", return_value=document, create=True
        ), patch("webapp.main.resolve_storage_path", return_value=None):
            with self.assertRaises(main.HTTPException) as exc:
                main.download_document(5, request, kind="pdf")

        self.assertEqual(exc.exception.status_code, 404)
        self.assertEqual(exc.exception.detail, "Файл отсутствует в серверном хранилище.")


class LegacyEstimateFormNormalizationTests(unittest.TestCase):
    def test_normalize_estimate_form_data_falls_back_to_project_fields_and_existing_calc_state(self):
        estimate = {
            "project": {"project_name": "Объект проекта", "address": "Адрес проекта"},
            "calc_state": {"wall_height": "2.7"},
        }

        draft_estimate, editor_rows, calc_state = main.normalize_estimate_form_data(
            estimate=estimate,
            company_name="",
            object_name="",
            customer_name=" Петров ",
            contract_label=" 12/26 ",
            discount="5",
            items_payload="not-json",
            calc_state_payload="[]",
            watermark="on",
        )

        self.assertEqual(draft_estimate["company"], "ООО Декорартстрой")
        self.assertEqual(draft_estimate["object_name"], "Адрес проекта")
        self.assertEqual(draft_estimate["customer_name"], "Петров")
        self.assertEqual(draft_estimate["contract_label"], "12/26")
        self.assertEqual(draft_estimate["discount"], "5")
        self.assertTrue(draft_estimate["watermark"])
        self.assertEqual(editor_rows, [])
        self.assertEqual(calc_state, {"wall_height": "2.7"})
        self.assertEqual(draft_estimate["calc_state"], {"wall_height": "2.7"})


if __name__ == "__main__":
    unittest.main()
