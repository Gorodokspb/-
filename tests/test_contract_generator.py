"""Tests for contract DOCX generation service.

Covers:
- build_contract_replacements with various counterparty types
- number_to_words_ru and format_money_with_words
- replace_placeholders_in_docx (unit test with real template)
- generate_contract_docx (integration test with test DB)
- Route POST /projects/{id}/contract/generate-docx
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.db_guard import guard_live_database

from webapp.contract_generator import (
    build_contract_replacements,
    format_contract_date,
    format_deadline_text,
    format_long_date,
    format_money_with_words,
    number_to_words_ru,
    parse_money_value,
    pluralize,
    replace_placeholders_in_docx,
)
from webapp.db import (
    create_counterparty,
    create_project,
    fetch_contract_settings,
    fetch_project,
    get_connection,
    get_project_estimate_total,
)

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "webapp" / "templates"
MAIN_PY = Path(__file__).resolve().parents[1] / "webapp" / "main.py"
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "contract_template_physical.docx"


class NumberToWordsRuTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(number_to_words_ru(0), "ноль")

    def test_single_digit(self):
        self.assertEqual(number_to_words_ru(5), "пять")

    def test_teens(self):
        self.assertEqual(number_to_words_ru(13), "тринадцать")

    def test_tens(self):
        self.assertEqual(number_to_words_ru(42), "сорок два")

    def test_hundreds(self):
        self.assertEqual(number_to_words_ru(803), "восемьсот три")

    def test_thousands(self):
        self.assertEqual(number_to_words_ru(200000), "двести тысяч")

    def test_complex_number(self):
        result = number_to_words_ru(803494)
        self.assertIn("восемьсот", result)
        self.assertIn("тысяч", result)
        self.assertIn("четыреста", result)


class FormatMoneyWithWordsTests(unittest.TestCase):
    def test_simple_amount(self):
        result = format_money_with_words(803494.25)
        self.assertIn("803 494", result)
        self.assertIn("рубль" if "рубля" not in result else "рубля", result)
        self.assertIn("25", result)

    def test_zero_amount(self):
        result = format_money_with_words(0)
        self.assertEqual(result, "")

    def test_none_returns_string(self):
        result = format_money_with_words(None)
        self.assertEqual(result, "")


class ParseMoneyValueTests(unittest.TestCase):
    def test_integer_string(self):
        self.assertEqual(parse_money_value("1000"), 1000.0)

    def test_decimal_with_comma(self):
        self.assertEqual(parse_money_value("1000,50"), 1000.50)

    def test_formatted_with_spaces(self):
        self.assertEqual(parse_money_value("1 000 000"), 1000000.0)

    def test_empty_returns_none(self):
        self.assertIsNone(parse_money_value(""))

    def test_none_returns_none(self):
        self.assertIsNone(parse_money_value(None))


class FormatContractDateTests(unittest.TestCase):
    def test_valid_date(self):
        result = format_contract_date("15.03.2023")
        self.assertIn("15", result)
        self.assertIn("марта", result)
        self.assertIn("2023", result)

    def test_empty_uses_today(self):
        result = format_contract_date("")
        self.assertIn("г.", result)


class FormatLongDateTests(unittest.TestCase):
    def test_valid_date(self):
        result = format_long_date("28.04.2023")
        self.assertIn("28", result)
        self.assertIn("апреля", result)
        self.assertIn("2023", result)

    def test_iso_date(self):
        result = format_long_date("2023-04-28")
        self.assertIn("апреля", result)


class FormatDeadlineTextTests(unittest.TestCase):
    def test_valid_date(self):
        result = format_deadline_text("15.06.2023")
        self.assertIn("не позднее", result)
        self.assertIn("15", result)

    def test_empty(self):
        result = format_deadline_text("")
        self.assertIn("не указано", result)


class PluralizeTests(unittest.TestCase):
    def test_singular(self):
        self.assertEqual(pluralize(1, ("рубль", "рубля", "рублей")), "рубль")

    def test_few(self):
        self.assertEqual(pluralize(3, ("рубль", "рубля", "рублей")), "рубля")

    def test_many(self):
        self.assertEqual(pluralize(5, ("рубль", "рубля", "рублей")), "рублей")

    def test_teens(self):
        self.assertEqual(pluralize(11, ("рубль", "рубля", "рублей")), "рублей")


class BuildContractReplacementsTests(unittest.TestCase):
    def _make_project(self, **overrides):
        defaults = {
            "project_name": "Тестовый объект",
            "address": "г. Санкт-Петербург, ул. Тестовая, д. 1",
            "customer": "Тестов Тест Тестович",
            "contract": "15/03",
            "date": "15.03.2023",
        }
        defaults.update(overrides)
        return defaults

    def _make_counterparty_phys(self):
        return {
            "type": "Физическое лицо",
            "name": "Иванов Иван Иванович",
            "full_name": "Иванов Иван Иванович",
            "passport_series_number": "4015 467273",
            "passport_issued_by": "Миграционный пункт №32",
            "passport_department_code": "780-032",
            "registration_address": "г. Санкт-Петербург, ул. Тестовая, д. 1, кв. 10",
            "work_address": "г. Санкт-Петербург, ул. Рабочая, д. 5",
            "phone": "+7(999)123-45-67",
            "email": "ivanov@test.ru",
        }

    def _make_settings(self, **overrides):
        defaults = {
            "contract_number": "15/03",
            "contract_date": "15.03.2023",
            "contractor_mode": "ooo",
            "customer_gender": "auto",
            "customer_name": "Иванов Иван Иванович",
            "object_address": "г. Санкт-Петербург, ул. Рабочая, д. 5",
            "work_end_date": "30.06.2023",
            "price_total": "803494.25",
            "advance_amount": "200000",
            "final_payment_amount": "",
            "payments": [
                {"date": "28.04.2023", "amount": "200000"},
                {"date": "15.05.2023", "amount": "200000"},
                {"date": "01.06.2023", "amount": "100000"},
            ],
            "working_group_text": "",
            "materials_mode": "customer",
            "intro_override": "",
            "payments_override": "",
            "communications_override": "",
        }
        defaults.update(overrides)
        return defaults

    def test_physical_person_replacements(self):
        project = self._make_project()
        counterparty = self._make_counterparty_phys()
        settings = self._make_settings()
        result = build_contract_replacements(project, counterparty, settings, "803494.25")
        self.assertIn("Иванов Иван Иванович", result.get("[[CUSTOMER_NAME]]", ""))
        self.assertIn("4015 467273", result.get("[[PASSPORT]]", ""))
        self.assertIn("Миграционный пункт №32", result.get("[[PASSPORT_ISSUED_BY]]", ""))
        self.assertIn("15/03", result.get("[[CONTRACT_NUMBER]]", ""))
        self.assertIn("[[OBJECT_ADDRESS]]", result)

    def test_ooo_replacements(self):
        project = self._make_project()
        counterparty = {
            "type": "Юридическое лицо ООО",
            "name": "ООО Ромашка",
            "full_name": "ООО Ромашка",
            "company_name": "ООО Ромашка",
            "inn": "7811000000",
            "kpp": "781101001",
            "ogrn": "1027800000000",
            "phone": "+7(812)111-22-33",
            "email": "info@romashka.ru",
            "legal_address": "г. СПб, ул. Ленина, д. 1",
            "director_name": "Петров П.П.",
            "director_basis": "Устава",
        }
        settings = self._make_settings(customer_name="ООО Ромашка")
        result = build_contract_replacements(project, counterparty, settings, "500000")
        self.assertIn("ООО Ромашка", result.get("[[CUSTOMER_NAME]]", ""))
        self.assertIn("7811000000", result.get("[[PASSPORT]]", ""))

    def test_no_counterparty(self):
        project = self._make_project()
        settings = self._make_settings()
        result = build_contract_replacements(project, None, settings, "0")
        self.assertIn("[[CUSTOMER_NAME]]", result)
        self.assertEqual(result.get("[[PASSPORT]]"), "не указано")

    def test_price_total_with_words(self):
        project = self._make_project()
        settings = self._make_settings(price_total="803494.25")
        result = build_contract_replacements(project, None, settings, "803494.25")
        price_total = result.get("[[PRICE_TOTAL]]", "")
        self.assertIn("803 494", price_total)
        self.assertIn("рубл" if "рубл" in price_total else "", price_total)

    def test_materials_mode_replace(self):
        project = self._make_project()
        settings = self._make_settings(materials_mode="customer")
        result = build_contract_replacements(project, None, settings, "0")
        has_materials_key = any("Работы" in k for k in result)
        self.assertTrue(has_materials_key)

    def test_fizlitso_type_treated_as_physical_person(self):
        from webapp.contract_generator import _normalize_counterparty_type
        self.assertEqual(_normalize_counterparty_type("Физлицо"), "Физическое лицо")
        self.assertEqual(_normalize_counterparty_type("Физическое лицо"), "Физическое лицо")
        self.assertEqual(_normalize_counterparty_type("physical"), "Физическое лицо")

    def test_ip_type_normalized(self):
        from webapp.contract_generator import _normalize_counterparty_type
        self.assertEqual(_normalize_counterparty_type("ИП"), "ИП")
        self.assertEqual(_normalize_counterparty_type("ип"), "ИП")

    def test_ooo_type_normalized(self):
        from webapp.contract_generator import _normalize_counterparty_type
        self.assertEqual(_normalize_counterparty_type("ООО"), "Юридическое лицо ООО")
        self.assertEqual(_normalize_counterparty_type("Юридическое лицо ООО"), "Юридическое лицо ООО")
        self.assertEqual(_normalize_counterparty_type("юрлицо"), "Юридическое лицо ООО")

    def test_fizlitso_replacements_match_physical_person(self):
        project = self._make_project()
        counterparty = {
            "type": "Физлицо",
            "name": "Иванов Иван Иванович",
            "full_name": "Иванов Иван Иванович",
            "passport_series_number": "6100 235555",
            "passport_issued_by": "Тестовым ОВД",
            "passport_department_code": "780-032",
            "registration_address": "г. СПб, ул. Ленина, д. 10",
            "work_address": "г. СПб, ул. Рабочая, д. 5",
            "phone": "+7(999)123-45-67",
            "email": "ivanov@test.ru",
        }
        settings = self._make_settings(object_address="")
        result = build_contract_replacements(project, counterparty, settings, "0")
        self.assertIn("6100 235555", result.get("[[PASSPORT]]", ""))
        self.assertIn("Тестовым ОВД", result.get("[[PASSPORT_ISSUED_BY]]", ""))
        self.assertIn("780-032", result.get("[[PASSPORT_CODE]]", ""))
        self.assertEqual(result.get("[[CUSTOMER_EMAIL]]"), "ivanov@test.ru")
        self.assertEqual(result.get("[[CUSTOMER_PHONE]]"), "+7(999)123-45-67")
        intro = result.get("[[CUSTOMER_INTRO]]", "")
        self.assertIn("гражданин", intro)

    def test_object_address_prefers_counterparty_work_address(self):
        project = self._make_project()
        counterparty = {
            "type": "Физлицо",
            "name": "Иванов",
            "full_name": "Иванов Иван Иванович",
            "work_address": "г. СПб, ул. Рабочая, д. 5",
            "passport_series_number": "1234 567890",
            "passport_issued_by": "ОВД",
            "passport_department_code": "780-001",
            "registration_address": "г. СПб, ул. Рег, д. 1",
            "phone": "+7(999)000-00-00",
            "email": "test@test.ru",
        }
        settings = self._make_settings(object_address="")
        result = build_contract_replacements(project, counterparty, settings, "0")
        self.assertEqual(result.get("[[OBJECT_ADDRESS]]"), "г. СПб, ул. Рабочая, д. 5")
        self.assertEqual(result.get("[[WORK_ADDRESS]]"), "г. СПб, ул. Рабочая, д. 5")

    def test_object_address_prefers_project_address_over_project_name(self):
        project = self._make_project(address="г. СПб, ул. Проектная, д. 10")
        settings = self._make_settings(object_address="")
        result = build_contract_replacements(project, None, settings, "0")
        self.assertEqual(result.get("[[OBJECT_ADDRESS]]"), "г. СПб, ул. Проектная, д. 10")

    def test_object_address_fallback_to_project_name_when_no_address(self):
        project = self._make_project(address="")
        settings = self._make_settings(object_address="")
        result = build_contract_replacements(project, None, settings, "0")
        self.assertEqual(result.get("[[OBJECT_ADDRESS]]"), "Тестовый объект")


class ReplacePlaceholdersInDocxTests(unittest.TestCase):
    def setUp(self):
        if not TEMPLATE_PATH.exists():
            self.skipTest(f"Contract template not found at {TEMPLATE_PATH}")

    def test_template_exists_and_readable(self):
        doc = replace_placeholders_in_docx(TEMPLATE_PATH, {})
        self.assertIsNotNone(doc)

    def test_key_placeholders_present_in_template(self):
        from docx import Document as DocxDocument
        doc = DocxDocument(str(TEMPLATE_PATH))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text += "\n" + cell.text
        expected_placeholders = [
            "[[CONTRACT_NUMBER]]",
            "[[CONTRACT_DATE]]",
            "[[CUSTOMER_NAME]]",
            "[[OBJECT_ADDRESS]]",
            "[[PRICE_TOTAL]]",
        ]
        for ph in expected_placeholders:
            self.assertIn(ph, full_text, f"Placeholder {ph} not found in template")

    def test_replacement_modifies_document(self):
        replacements = {
            "[[CONTRACT_NUMBER]]": "ДОГОВОР № 999",
            "[[CONTRACT_DATE]]": '" 15 " марта 2023 г.',
            "[[CUSTOMER_NAME]]": "Иванов Иван Иванович",
            "[[OBJECT_ADDRESS]]": "г. Санкт-Петербург, ул. Тестовая, д. 1",
        }
        doc = replace_placeholders_in_docx(TEMPLATE_PATH, replacements)
        output_dir = Path(tempfile.mkdtemp())
        output_path = output_dir / "test_contract.docx"
        try:
            doc.save(str(output_path))
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_no_placeholder_left_after_full_replacement(self):
        project = {
            "project_name": "Тестовый объект",
            "address": "г. Санкт-Петербург, ул. Тестовая, д. 1",
            "customer": "Тестов Тест Тестович",
            "contract": "99/2023",
            "date": "01.01.2023",
        }
        counterparty = {
            "type": "Физическое лицо",
            "name": "Петров Петр Петрович",
            "full_name": "Петров Петр Петрович",
            "passport_series_number": "1234 567890",
            "passport_issued_by": "ОВД района",
            "passport_department_code": "780-001",
            "registration_address": "г. СПб, ул. Ленина, д. 10",
            "work_address": "г. СПб, ул. Рабочая, д. 5",
            "phone": "+7(999)000-00-00",
            "email": "petrov@test.ru",
        }
        settings = {
            "contract_number": "99/2023",
            "contract_date": "01.01.2023",
            "contractor_mode": "ooo",
            "customer_gender": "male",
            "customer_name": "Петров Петр Петрович",
            "object_address": "г. СПб, ул. Рабочая, д. 5",
            "work_end_date": "30.06.2023",
            "price_total": "500000",
            "advance_amount": "100000",
            "final_payment_amount": "",
            "payments": [
                {"date": "15.02.2023", "amount": "200000"},
                {"date": "15.03.2023", "amount": "200000"},
            ],
            "working_group_text": "",
            "materials_mode": "customer",
            "intro_override": "",
            "payments_override": "",
            "communications_override": "",
        }
        replacements = build_contract_replacements(project, counterparty, settings, "500000")
        doc = replace_placeholders_in_docx(TEMPLATE_PATH, replacements)
        output_dir = Path(tempfile.mkdtemp())
        output_path = output_dir / "test_full_contract.docx"
        try:
            doc.save(str(output_path))
            from docx import Document as DocxDocument
            saved = DocxDocument(str(output_path))
            full_text = "\n".join(p.text for p in saved.paragraphs)
            for table in saved.tables:
                for row in table.rows:
                    for cell in row.cells:
                        full_text += "\n" + cell.text
            all_placeholders = [
                "[[CONTRACT_NUMBER]]",
                "[[CONTRACT_DATE]]",
                "[[CUSTOMER_NAME]]",
                "[[CUSTOMER_EMAIL]]",
                "[[CUSTOMER_PHONE]]",
                "[[OBJECT_ADDRESS]]",
                "[[WORK_ADDRESS]]",
                "[[PASSPORT]]",
                "[[PASSPORT_ISSUED_BY]]",
                "[[PASSPORT_CODE]]",
                "[[REGISTRATION_ADDRESS]]",
                "[[PRICE_TOTAL]]",
            ]
            for ph in all_placeholders:
                self.assertNotIn(ph, full_text, f"Unreplaced placeholder: {ph}")
            self.assertIn("petrov@test.ru", full_text)
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_working_group_text_replaces_whatsapp_paragraph(self):
        replacements = {
            "[[WORKING_GROUP_TEXT]]": "Telegram группа - https://t.me/example",
        }
        doc = replace_placeholders_in_docx(TEMPLATE_PATH, replacements)
        from docx import Document as DocxDocument
        import re
        full_text = "\n".join(p.text for p in doc.paragraphs)
        self.assertNotIn("Рабочая группа WhatsApp", full_text)
        self.assertNotIn("chat.whatsapp.com", full_text)
        self.assertIn("Рабочая группа: Telegram группа - https://t.me/example", full_text)

    def test_working_group_text_empty_preserves_whatsapp_default(self):
        replacements = {}
        doc = replace_placeholders_in_docx(TEMPLATE_PATH, replacements)
        from docx import Document as DocxDocument
        full_text = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("Рабочая группа WhatsApp", full_text)

    def test_working_group_text_custom_replaces_whatsapp_in_xml(self):
        from zipfile import ZipFile
        custom_text = "Viber группа - https://viber.com/test"
        replacements = {
            "[[WORKING_GROUP_TEXT]]": custom_text,
        }
        output_dir = Path(tempfile.mkdtemp())
        output_path = output_dir / "test_wg_contract.docx"
        try:
            doc = replace_placeholders_in_docx(TEMPLATE_PATH, replacements)
            doc.save(str(output_path))
            with ZipFile(str(output_path)) as z:
                xml = ""
                for name in z.namelist():
                    if name.startswith("word/") and name.endswith(".xml"):
                        xml += z.read(name).decode("utf-8", errors="ignore")
            self.assertNotIn("chat.whatsapp.com", xml)
            self.assertIn("Рабочая группа: Viber группа", xml)
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_working_group_text_prefix_not_duplicated(self):
        replacements = {
            "[[WORKING_GROUP_TEXT]]": "Рабочая группа: https://t.me/example",
        }
        doc = replace_placeholders_in_docx(TEMPLATE_PATH, replacements)
        from docx import Document as DocxDocument
        full_text = "\n".join(p.text for p in doc.paragraphs)
        self.assertNotIn("Рабочая группа: Рабочая группа:", full_text)
        self.assertIn("Рабочая группа: https://t.me/example", full_text)

    def test_working_group_text_bare_url_gets_prefix(self):
        replacements = {
            "[[WORKING_GROUP_TEXT]]": "https://chat.whatsapp.com/abc123",
        }
        doc = replace_placeholders_in_docx(TEMPLATE_PATH, replacements)
        from docx import Document as DocxDocument
        full_text = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("Рабочая группа: https://chat.whatsapp.com/abc123", full_text)

    def test_working_group_text_has_black_font_color(self):
        from lxml import etree
        replacements = {
            "[[WORKING_GROUP_TEXT]]": "Telegram группа",
        }
        doc = replace_placeholders_in_docx(TEMPLATE_PATH, replacements)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for p in doc.paragraphs:
            if "Рабочая группа: Telegram группа" in p.text:
                color_found = False
                underline_none_found = False
                for run in p.runs:
                    rpr = run._element.find(f"{{{ns['w']}}}rPr")
                    if rpr is not None:
                        color_elem = rpr.find(f"{{{ns['w']}}}color")
                        if color_elem is not None:
                            color_val = color_elem.get(f"{{{ns['w']}}}val")
                            if color_val == "000000":
                                color_found = True
                        u_elem = rpr.find(f"{{{ns['w']}}}u")
                        if u_elem is not None and u_elem.get(f"{{{ns['w']}}}val") == "none":
                            underline_none_found = True
                self.assertTrue(color_found, "Working group text should have black font color (000000)")
                self.assertTrue(underline_none_found, "Working group text should have underline=none")
                break
        else:
            self.fail("Working group paragraph not found in document")

    def test_working_group_text_no_hyperlink_nor_rstyle(self):
        from lxml import etree
        replacements = {
            "[[WORKING_GROUP_TEXT]]": "Custom group",
        }
        doc = replace_placeholders_in_docx(TEMPLATE_PATH, replacements)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for p in doc.paragraphs:
            if "Рабочая группа: Custom group" in p.text:
                hyperlinks = p._element.findall(f"{{{ns['w']}}}hyperlink")
                self.assertEqual(len(hyperlinks), 0, "No hyperlink elements should remain")
                for run in p.runs:
                    rpr = run._element.find(f"{{{ns['w']}}}rPr")
                    if rpr is not None:
                        rstyle = rpr.find(f"{{{ns['w']}}}rStyle")
                        self.assertIsNone(rstyle, "No rStyle should be set on working group run")
                break
        else:
            self.fail("Working group paragraph not found in document")


class GenerateContractDocxIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        guard_live_database()

    def setUp(self):
        guard_live_database()
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        guard_live_database()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE doc_type = 'Договор' AND project_id > 2")
                cur.execute("DELETE FROM counterparties WHERE id > 2")
                cur.execute("DELETE FROM projects WHERE id > 2")
            conn.commit()

    def _create_test_project(self, name="Тест Договор Генерация"):
        pid = create_project(
            "tester",
            project_name=name,
            address="ул. Тестовая, д. 1",
            counterparty_id=None,
            status="В работе",
            contract="15/03",
            contract_date="2023-03-15",
            notes="",
        )
        return pid

    def test_generate_creates_document_record(self):
        pid = self._create_test_project()
        from webapp.contract_generator import generate_contract_docx
        result = generate_contract_docx(pid)
        self.assertIn("document_id", result)
        self.assertIn("file_path", result)
        self.assertTrue(result["file_path"].endswith(".docx"))

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT file_path FROM documents WHERE project_id = %s AND doc_type = 'Договор'",
                    (pid,),
                )
                row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertTrue(row["file_path"].endswith(".docx"))

    def test_generated_file_exists_on_disk(self):
        pid = self._create_test_project()
        from webapp.contract_generator import generate_contract_docx
        result = generate_contract_docx(pid)
        from webapp.storage import resolve_storage_path
        file_path = resolve_storage_path(result["file_path"])
        self.assertIsNotNone(file_path)
        self.assertTrue(file_path.exists())

    def test_template_not_modified(self):
        template_before = TEMPLATE_PATH.stat().st_mtime
        pid = self._create_test_project()
        from webapp.contract_generator import generate_contract_docx
        generate_contract_docx(pid)
        template_after = TEMPLATE_PATH.stat().st_mtime
        self.assertEqual(template_before, template_after)


class ContractRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        guard_live_database()

    def setUp(self):
        guard_live_database()
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        guard_live_database()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE doc_type = 'Договор' AND project_id > 2")
                cur.execute("DELETE FROM counterparties WHERE id > 2")
                cur.execute("DELETE FROM projects WHERE id > 2")
            conn.commit()

    def test_generate_docx_route_exists(self):
        source = MAIN_PY.read_text(encoding="utf-8")
        self.assertIn("/projects/{project_id}/contract/generate-docx", source)
        self.assertIn("contract_generate_docx", source)

    def test_route_imports_generate_contract_docx(self):
        source = MAIN_PY.read_text(encoding="utf-8")
        self.assertIn("update_document_file_path", source)


if __name__ == "__main__":
    unittest.main()