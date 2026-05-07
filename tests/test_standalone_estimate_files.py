import os
import shutil
import tempfile
import unittest

from reportlab.platypus import Image, Paragraph, Table

from webapp.config import get_settings
from webapp.company_repository import Company
from webapp.standalone_estimate_files import (
    _build_pdf_table,
    _build_pdf_elements,
    _draft_watermark_enabled,
    _resolve_company_asset,
    _resolve_watermark_text,
    export_final_approved_pdf,
    export_standalone_estimate_pdf,
)
from webapp.storage import storage_relative_path, resolve_storage_path


class StandaloneEstimateFileExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = get_settings()
        cls.storage_dir = cls.settings.estimates_dir / "standalone-estimates"

    def setUp(self):
        self._cleanup_storage()

    def tearDown(self):
        self._cleanup_storage()

    def _cleanup_storage(self):
        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)

    def _snapshot(self):
        return {
            "estimate": {
                "id": 88001,
                "estimate_number": "ST-PDF-DRAFT",
                "title": "Черновой PDF",
                "status": "draft",
                "customer_name": "Клиент",
                "object_name": "Объект",
                "company_name": "ООО Декорартстрой",
                "contract_label": "D-8",
                "discount": "7.50",
                "watermark": "on",
            },
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

    def test_draft_pdf_is_created_for_section_and_items(self):
        path = export_standalone_estimate_pdf(self._snapshot())

        self.assertTrue(path.exists())
        self.assertTrue(path.name.endswith("-draft.pdf"))
        self.assertGreater(path.stat().st_size, 0)

    def test_pdf_table_keeps_section_out_of_totals(self):
        table_data, section_styles, grand_total, discounted_total = _build_pdf_table(self._snapshot())

        section_name_cell = table_data[1][0]
        self.assertIsInstance(section_name_cell, Paragraph)
        self.assertIn("Подготовка", section_name_cell.text)
        self.assertEqual(table_data[1][1:], ["", "", "", "", ""])
        self.assertIn(("SPAN", (0, 1), (-1, 1)), section_styles)
        self.assertEqual(grand_total, 1500.0)
        self.assertEqual(discounted_total, 1387.5)

    def test_draft_pdf_rejects_stamp_and_signature(self):
        with self.assertRaises(ValueError):
            export_standalone_estimate_pdf(
                self._snapshot(),
                stamp_applied=True,
                signature_applied=True,
            )

    def test_watermark_is_enabled_only_for_marked_drafts(self):
        snapshot = self._snapshot()
        self.assertTrue(_draft_watermark_enabled(snapshot["estimate"], approved=False))
        self.assertFalse(_draft_watermark_enabled(snapshot["estimate"], approved=True))

        snapshot["estimate"]["watermark"] = ""
        self.assertFalse(_draft_watermark_enabled(snapshot["estimate"], approved=False))

    def _approved_snapshot(self):
        snapshot = self._snapshot()
        snapshot["estimate"]["status"] = "approved"
        snapshot["estimate"]["watermark"] = ""
        return snapshot

    def test_final_approved_pdf_is_created_from_approved_snapshot(self):
        snapshot = self._approved_snapshot()
        path = export_final_approved_pdf(snapshot)
        self.assertTrue(path.exists())
        self.assertTrue(path.name.endswith("-approved.pdf"))
        self.assertGreater(path.stat().st_size, 0)

    def test_final_approved_pdf_with_stamp_and_signature(self):
        snapshot = self._approved_snapshot()
        path = export_final_approved_pdf(snapshot, stamp_applied=True, signature_applied=True)
        self.assertTrue(path.exists())
        self.assertIn("-approved.pdf", path.name)

    def test_final_approved_pdf_rejects_non_approved_snapshot(self):
        with self.assertRaises(ValueError):
            export_final_approved_pdf(self._snapshot())

    def test_final_approved_pdf_rejects_stamp_for_non_approved_snapshot(self):
        with self.assertRaises(ValueError):
            export_final_approved_pdf(self._snapshot(), stamp_applied=True)

    def test_build_pdf_elements_includes_stamp_signature_block_for_final_approved(self):
        snapshot = self._approved_snapshot()
        elements = _build_pdf_elements(snapshot, stamp_applied=True, signature_applied=True, is_final_approved=True)
        table_count = sum(1 for elem in elements if isinstance(elem, Table))
        self.assertGreaterEqual(table_count, 2)

    def test_build_pdf_elements_no_stamp_signature_block_for_non_final(self):
        snapshot = self._approved_snapshot()
        elements = _build_pdf_elements(snapshot, stamp_applied=False, signature_applied=False, is_final_approved=False)
        table_count = sum(1 for elem in elements if isinstance(elem, Table))
        self.assertEqual(table_count, 1)


class CompanyDetailsInPdfTests(unittest.TestCase):
    def setUp(self):
        self._cleanup_storage()

    def tearDown(self):
        self._cleanup_storage()

    def _cleanup_storage(self):
        storage_dir = get_settings().estimates_dir / "standalone-estimates"
        if storage_dir.exists():
            shutil.rmtree(storage_dir)

    def _approved_snapshot(self):
        return {
            "estimate": {
                "id": 88002,
                "estimate_number": "ST-COMP-001",
                "title": "Смета с реквизитами",
                "status": "approved",
                "customer_name": "Клиент",
                "object_name": "Объект",
                "company_name": "ООО Декорартстрой",
                "contract_label": "D-9",
                "discount": "0",
                "watermark": "",
            },
            "items": [
                {"row_type": "item", "name": "Работа", "unit": "шт", "quantity": "1", "price": "100", "total": "100", "discounted_total": "100"},
            ],
        }

    def _full_company(self):
        return Company(
            id=1,
            legal_name='ООО «Декорартстрой»',
            short_name='ООО Декорартстрой',
            inn='7811111111',
            kpp='781101001',
            ogrn='1027800000001',
            legal_address='г. Санкт-Петербург, ул. Примерная, д. 1',
            phone='+7 (812) 111-11-11',
            email='info@decorartstroy.ru',
            website='https://decorartstroy.ru',
            bank_name='ПАО «Сбербанк»',
            bik='044030653',
            account='40702810100000000001',
            correspondent_account='30101810400000000653',
            signer_name='Иванов И.И.',
        )

    def _minimal_company(self):
        return Company(
            id=2,
            legal_name='ИП Гордеев А.Н.',
            short_name='ИП Гордеев А.Н.',
            inn='7822222222',
            ogrnip='304782222200000',
        )

    def _paragraph_texts(self, elements):
        return [e.text for e in elements if isinstance(e, Paragraph)]

    def test_company_details_appear_in_elements(self):
        company = self._full_company()
        elements = _build_pdf_elements(self._approved_snapshot(), company=company, is_final_approved=True)
        texts = self._paragraph_texts(elements)
        joined = " ".join(texts)
        self.assertIn('ООО «Декорартстрой»', joined)
        self.assertIn('ИНН: 7811111111', joined)
        self.assertIn('КПП: 781101001', joined)
        self.assertIn('ОГРН: 1027800000001', joined)
        self.assertIn('ПАО «Сбербанк»', joined)
        self.assertIn('БИК: 044030653', joined)
        self.assertIn('Р/с: 40702810100000000001', joined)
        self.assertIn('К/с: 30101810400000000653', joined)
        self.assertIn('Подписант: Иванов И.И.', joined)

    def test_minimal_company_no_extra_lines(self):
        company = self._minimal_company()
        elements = _build_pdf_elements(self._approved_snapshot(), company=company, is_final_approved=True)
        texts = self._paragraph_texts(elements)
        joined = " ".join(texts)
        self.assertIn('ИП Гордеев А.Н.', joined)
        self.assertIn('ИНН: 7822222222', joined)
        self.assertIn('ОГРНИП: 304782222200000', joined)
        self.assertNotIn('КПП:', joined)
        self.assertNotIn('Банк:', joined)
        self.assertNotIn('Р/с:', joined)

    def test_no_company_uses_company_name_fallback(self):
        elements = _build_pdf_elements(self._approved_snapshot(), company=None, is_final_approved=True)
        texts = self._paragraph_texts(elements)
        joined = " ".join(texts)
        self.assertIn('Компания: ООО Декорартстрой', joined)

    def test_final_pdf_generated_with_company(self):
        company = self._full_company()
        snapshot = self._approved_snapshot()
        path = export_final_approved_pdf(snapshot, company=company)
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 0)

    def test_final_pdf_without_company_still_works(self):
        snapshot = self._approved_snapshot()
        path = export_final_approved_pdf(snapshot, company=None)
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 0)


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _flatten_table_cells(elements):
    cells = []
    for e in elements:
        if isinstance(e, Table) and hasattr(e, "_cellvalues"):
            for row in e._cellvalues:
                for cell in row:
                    cells.append(cell)
    return cells


def _make_png_bytes() -> bytes:
    import struct, zlib
    width, height = 4, 4
    raw = b""
    for _ in range(height):
        raw += b"\x00" + b"\xff\x00\x00" * width
    compressed = zlib.compress(raw)

    def _chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = _PNG_MAGIC
    png += _chunk(b"IHDR", ihdr_data)
    png += _chunk(b"IDAT", compressed)
    png += _chunk(b"IEND", b"")
    return png


class StampSignaturePngTests(unittest.TestCase):
    def setUp(self):
        self.storage_dir = get_settings().estimates_dir / "standalone-estimates"
        self._tmp_dirs = []

    def tearDown(self):
        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)
        for d in self._tmp_dirs:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)

    def _approved_snapshot(self):
        return {
            "estimate": {
                "id": 88003,
                "estimate_number": "ST-STAMP-001",
                "title": "Смета с печатью",
                "status": "approved",
                "customer_name": "Клиент",
                "object_name": "Объект",
                "company_name": "ООО Декорартстрой",
                "contract_label": "D-10",
                "discount": "0",
                "watermark": "",
            },
            "items": [
                {"row_type": "item", "name": "Работа", "unit": "шт", "quantity": "1", "price": "100", "total": "100", "discounted_total": "100"},
            ],
        }

    def _write_png(self, name: str) -> str:
        settings = get_settings()
        asset_dir = settings.storage_root / "company-assets" / "99"
        asset_dir.mkdir(parents=True, exist_ok=True)
        self._tmp_dirs.append(str(asset_dir))
        png_path = asset_dir / name
        png_path.write_bytes(_make_png_bytes())
        return storage_relative_path(png_path)

    def _company_with_stamp(self, stamp_rel: str | None = None, sig_rel: str | None = None) -> Company:
        return Company(
            id=99,
            legal_name="ООО Тестовая Компания",
            short_name="ТестКо",
            inn="0000000000",
            stamp_path=stamp_rel,
            signature_path=sig_rel,
        )

    def test_stamp_applied_with_file_inserts_image(self):
        stamp_rel = self._write_png("stamp.png")
        company = self._company_with_stamp(stamp_rel=stamp_rel)
        elements = _build_pdf_elements(
            self._approved_snapshot(),
            stamp_applied=True,
            signature_applied=False,
            is_final_approved=True,
            company=company,
        )
        cells = _flatten_table_cells(elements)
        image_count = sum(1 for c in cells if isinstance(c, Image))
        self.assertEqual(image_count, 1)

    def test_signature_applied_with_file_inserts_image(self):
        sig_rel = self._write_png("signature.png")
        company = self._company_with_stamp(sig_rel=sig_rel)
        elements = _build_pdf_elements(
            self._approved_snapshot(),
            stamp_applied=False,
            signature_applied=True,
            is_final_approved=True,
            company=company,
        )
        cells = _flatten_table_cells(elements)
        image_count = sum(1 for c in cells if isinstance(c, Image))
        self.assertEqual(image_count, 1)

    def test_both_applied_with_files_inserts_two_images(self):
        stamp_rel = self._write_png("stamp.png")
        sig_rel = self._write_png("signature.png")
        company = self._company_with_stamp(stamp_rel=stamp_rel, sig_rel=sig_rel)
        elements = _build_pdf_elements(
            self._approved_snapshot(),
            stamp_applied=True,
            signature_applied=True,
            is_final_approved=True,
            company=company,
        )
        cells = _flatten_table_cells(elements)
        image_count = sum(1 for c in cells if isinstance(c, Image))
        self.assertEqual(image_count, 2)

    def test_stamp_applied_without_file_falls_back_to_text(self):
        company = self._company_with_stamp(stamp_rel=None, sig_rel=None)
        elements = _build_pdf_elements(
            self._approved_snapshot(),
            stamp_applied=True,
            signature_applied=True,
            is_final_approved=True,
            company=company,
        )
        cells = _flatten_table_cells(elements)
        cell_texts = [c.text for c in cells if isinstance(c, Paragraph)]
        joined = " ".join(cell_texts)
        self.assertIn("М.П.", joined)
        self.assertIn("Подпись", joined)
        image_count = sum(1 for c in cells if isinstance(c, Image))
        self.assertEqual(image_count, 0)

    def test_no_stamp_no_signature_no_images(self):
        elements = _build_pdf_elements(
            self._approved_snapshot(),
            stamp_applied=False,
            signature_applied=False,
            is_final_approved=True,
            company=None,
        )
        cells = _flatten_table_cells(elements)
        image_count = sum(1 for c in cells if isinstance(c, Image))
        self.assertEqual(image_count, 0)

    def test_resolve_company_asset_returns_path_for_existing_file(self):
        stamp_rel = self._write_png("stamp.png")
        company = self._company_with_stamp(stamp_rel=stamp_rel)
        result = _resolve_company_asset(company, "stamp_path")
        self.assertIsNotNone(result)
        self.assertTrue(result.exists())

    def test_resolve_company_asset_returns_none_for_missing_attr(self):
        company = self._company_with_stamp(stamp_rel=None, sig_rel=None)
        self.assertIsNone(_resolve_company_asset(company, "stamp_path"))
        self.assertIsNone(_resolve_company_asset(company, "signature_path"))

    def test_final_pdf_with_stamp_image_generates(self):
        stamp_rel = self._write_png("stamp.png")
        company = self._company_with_stamp(stamp_rel=stamp_rel)
        snapshot = self._approved_snapshot()
        path = export_final_approved_pdf(snapshot, stamp_applied=True, signature_applied=False, company=company)
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 0)

    def test_stamp_applied_company_none_falls_back_text(self):
        elements = _build_pdf_elements(
            self._approved_snapshot(),
            stamp_applied=True,
            signature_applied=True,
            is_final_approved=True,
            company=None,
        )
        cells = _flatten_table_cells(elements)
        cell_texts = [c.text for c in cells if isinstance(c, Paragraph)]
        joined = " ".join(cell_texts)
        self.assertIn("М.П.", joined)
        self.assertIn("Подпись", joined)
        image_count = sum(1 for c in cells if isinstance(c, Image))
        self.assertEqual(image_count, 0)

    def test_stamp_applied_path_missing_file_falls_back_text(self):
        company = Company(
            id=99, legal_name="Тест", short_name="Тест",
            stamp_path="company-assets/99/nonexistent_stamp.png",
            signature_path="company-assets/99/nonexistent_sig.png",
        )
        elements = _build_pdf_elements(
            self._approved_snapshot(),
            stamp_applied=True,
            signature_applied=True,
            is_final_approved=True,
            company=company,
        )
        cells = _flatten_table_cells(elements)
        cell_texts = [c.text for c in cells if isinstance(c, Paragraph)]
        joined = " ".join(cell_texts)
        self.assertIn("М.П.", joined)
        self.assertIn("Подпись", joined)
        image_count = sum(1 for c in cells if isinstance(c, Image))
        self.assertEqual(image_count, 0)


class WatermarkTextTests(unittest.TestCase):
    def test_watermark_text_from_company(self):
        company = Company(id=1, legal_name="ООО «Декорартстрой»", short_name="ООО Декорартстрой", watermark_text="КОМПАНИЯ ВОДЯНОЙ ЗНАК")
        result = _resolve_watermark_text("ООО Декорартстрой", company)
        self.assertEqual(result, "КОМПАНИЯ ВОДЯНОЙ ЗНАК")

    def test_watermark_text_fallback_without_company(self):
        result = _resolve_watermark_text("ООО Декорартстрой", None)
        self.assertEqual(result, "ДЕКОРАРТСТРОЙ")

    def test_watermark_text_ip_gordeev_fallback(self):
        result = _resolve_watermark_text("ИП Гордеев А.Н.", None)
        self.assertEqual(result, "ИП ГОРДЕЕВ А.Н.")

    def test_watermark_text_empty_company_watermark_falls_back(self):
        company = Company(id=1, legal_name="ООО Тест", short_name="Тест", watermark_text="")
        result = _resolve_watermark_text("ООО Тест", company)
        self.assertEqual(result, "ДЕКОРАРТСТРОЙ")

    def test_watermark_text_ip_gordeev_company_takes_priority(self):
        company = Company(id=2, legal_name="ИП Гордеев А.Н.", short_name="ИП Гордеев А.Н.", inn="123", watermark_text="ГОРДЕЕВ И ПОДРЯДЧИК")
        result = _resolve_watermark_text("ИП Гордеев А.Н.", company)
        self.assertEqual(result, "ГОРДЕЕВ И ПОДРЯДЧИК")

    def test_draft_pdf_uses_company_watermark(self):
        company = Company(id=1, legal_name="ООО «Декорартстрой»", short_name="ООО Декорартстрой", watermark_text="ДИКОРАРТСТРОЙ ТЕСТ")
        snapshot = {
            "estimate": {
                "id": 88004,
                "estimate_number": "ST-WM-001",
                "title": "Водяной знак тест",
                "status": "draft",
                "customer_name": "Клиент",
                "object_name": "Объект",
                "company_name": "ООО Декорартстрой",
                "contract_label": "D-11",
                "discount": "0",
                "watermark": "on",
            },
            "items": [
                {"row_type": "item", "name": "Работа", "unit": "шт", "quantity": "1", "price": "100", "total": "100", "discounted_total": "100"},
            ],
        }
        enabled = _draft_watermark_enabled(snapshot["estimate"], approved=False)
        self.assertTrue(enabled)
        wt = _resolve_watermark_text("ООО Декорартстрой", company)
        self.assertEqual(wt, "ДИКОРАРТСТРОЙ ТЕСТ")

    def test_draft_pdf_uses_fallback_watermark_without_company(self):
        snapshot = {
            "estimate": {
                "id": 88005,
                "status": "draft",
                "company_name": "ООО Декорартстрой",
                "watermark": "on",
            },
            "items": [],
        }
        wt = _resolve_watermark_text("ООО Декорартстрой", None)
        self.assertEqual(wt, "ДЕКОРАРТСТРОЙ")

    def test_pdf_with_long_name_generates_without_error(self):
        snapshot = {
            "estimate": {
                "id": 88006,
                "estimate_number": "LT-001",
                "title": "Длинные названия",
                "status": "draft",
                "customer_name": "Заказчик",
                "object_name": "Объект",
                "company_name": "ООО Декорартстрой",
                "contract_label": "Д-1",
                "discount": "0",
                "watermark": None,
            },
            "items": [
                {"row_type": "section", "name": "Раздел с длинным названием для проверки переноса текста в PDF", "sort_order": 1},
                {
                    "row_type": "item",
                    "name": "Выравнивание поверхности подоконника под искусственный камень с устройством откосов и гидроизоляцией",
                    "unit": "пог.м",
                    "quantity": "12",
                    "price": "2500",
                    "total": "30000",
                    "discounted_total": "27000",
                    "sort_order": 2,
                },
                {
                    "row_type": "item",
                    "name": "Ещё одно очень длинное название работы по отделке фасада здания с устройством декоративной штукатурки",
                    "unit": "м2",
                    "quantity": "150",
                    "price": "800",
                    "total": "120000",
                    "discounted_total": "108000",
                    "sort_order": 3,
                },
            ],
        }
        path = export_standalone_estimate_pdf(snapshot)
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 0)

    def test_pdf_table_uses_paragraph_for_item_names(self):
        snapshot = {
            "estimate": {
                "id": 88007,
                "estimate_number": "PP-001",
                "status": "draft",
                "company_name": "ООО Декорартстрой",
                "discount": "0",
                "watermark": None,
            },
            "items": [
                {
                    "row_type": "item",
                    "name": "Короткое название",
                    "unit": "шт",
                    "quantity": "1",
                    "price": "100",
                    "total": "100",
                    "discounted_total": "100",
                    "sort_order": 1,
                },
            ],
        }
        table_data, section_styles, grand_total, discounted_total = _build_pdf_table(snapshot)
        from reportlab.platypus import Paragraph
        name_cell = table_data[1][0]
        self.assertIsInstance(name_cell, Paragraph)
