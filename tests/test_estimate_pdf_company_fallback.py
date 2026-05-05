import unittest
from unittest.mock import patch, MagicMock

from webapp.company_repository import Company
from webapp.estimate_pdf import (
    _get_company_details,
    _hardcoded_company_details,
    _company_to_details_dict,
    _split_address,
    _HARDCODED_COMPANY_DETAILS,
)


def _make_company(
    *,
    short_name="ООО Декорартстрой",
    legal_name="ООО «Декорартстрой»",
    inn="7811530330",
    kpp="780501001",
    ogrn="1127847464942",
    ogrnip=None,
    legal_address="г. Санкт-Петербург, Ленинский пр-кт, д. 144, кор. 1, стр. 2, оф. 302",
    phone="+7 (911) 921-30-39, +7 (911) 031-61-01",
    email="info@dekorartstroy.ru",
    website="remontstroyspb.ru",
    **kwargs,
):
    defaults = dict(
        id=1,
        legal_name=legal_name,
        short_name=short_name,
        inn=inn,
        kpp=kpp,
        ogrn=ogrn,
        ogrnip=ogrnip,
        legal_address=legal_address,
        phone=phone,
        email=email,
        website=website,
        bank_name=None,
        bik=None,
        account=None,
        correspondent_account=None,
        director_name=None,
        signer_name=None,
        stamp_path=None,
        signature_path=None,
        watermark_text="ДЕКОРАРТСТРОЙ",
        is_active=True,
        created_at="",
        updated_at="",
    )
    defaults.update(kwargs)
    return Company(**defaults)


class TestHardcodedCompanyDetails(unittest.TestCase):
    def test_ooo_dekorartstroy_returns_expected_dict(self):
        result = _hardcoded_company_details("ООО Декорартстрой")
        self.assertEqual(result, _HARDCODED_COMPANY_DETAILS["ООО Декорартстрой"])

    def test_ip_gordeev_returns_expected_dict(self):
        result = _hardcoded_company_details("ИП Гордеев А.Н.")
        self.assertEqual(result, _HARDCODED_COMPANY_DETAILS["ИП Гордеев А.Н."])

    def test_unknown_company_falls_back_to_ooo(self):
        result = _hardcoded_company_details("ООО Несуществующая")
        self.assertEqual(result, _HARDCODED_COMPANY_DETAILS["ООО Декорартстрой"])

    def test_hardcoded_dicts_have_required_keys(self):
        for name, details in _HARDCODED_COMPANY_DETAILS.items():
            self.assertIn("title", details, f"Missing 'title' for {name}")
            self.assertIn("details", details, f"Missing 'details' for {name}")
            self.assertIsInstance(details["title"], str)
            self.assertIsInstance(details["details"], list)


class TestSplitAddress(unittest.TestCase):
    def test_short_address_returns_single_line(self):
        result = _split_address("г. Москва, ул. Ленина, д. 1")
        self.assertEqual(result, ["г. Москва, ул. Ленина, д. 1"])

    def test_long_address_splits_at_first_comma(self):
        long_addr = "г. Санкт-Петербург, Ленинский пр-кт, д. 144, кор. 1, стр. 2, оф. 302"
        result = _split_address(long_addr)
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0].startswith("г. Санкт-Петербург"))
        self.assertTrue(result[1].startswith("Ленинский пр-кт"))

    def test_empty_address_returns_empty_list(self):
        result = _split_address("")
        self.assertEqual(result, [])

    def test_exactly_50_chars_address_not_split(self):
        addr = "А" * 50
        result = _split_address(addr)
        self.assertEqual(result, [addr])

    def test_51_chars_address_split(self):
        addr = "А" * 25 + ", " + "Б" * 25
        result = _split_address(addr)
        self.assertEqual(len(result), 2)


class TestCompanyToDetailsDict(unittest.TestCase):
    def test_ooo_full_details(self):
        company = _make_company(
            short_name="ООО Декорартстрой",
            legal_name="ООО «Декорартстрой»",
            inn="7811530330",
            kpp="780501001",
            ogrn="1127847464942",
            ogrnip=None,
            legal_address="г. Санкт-Петербург, Ленинский пр-кт, д. 144, кор. 1, стр. 2, оф. 302",
            phone="+7 (911) 921-30-39, +7 (911) 031-61-01",
            email="info@dekorartstroy.ru",
            website="remontstroyspb.ru",
        )
        result = _company_to_details_dict(company)
        self.assertEqual(result["title"], "<b>ООО «Декорартстрой»</b>")
        self.assertIn("ИНН 7811530330 / КПП 780501001", result["details"])
        self.assertIn("ОГРН 1127847464942", result["details"])
        self.assertTrue(any("Юр. адрес:" in d for d in result["details"]))
        self.assertIn("Тел.: +7 (911) 921-30-39, +7 (911) 031-61-01", result["details"])
        self.assertIn("E-mail: info@dekorartstroy.ru", result["details"])
        self.assertIn("Сайт: remontstroyspb.ru", result["details"])

    def test_ip_full_details(self):
        company = _make_company(
            id=2,
            short_name="ИП Гордеев А.Н.",
            legal_name="ИП Гордеев А.Н.",
            inn="781144532689",
            kpp=None,
            ogrn=None,
            ogrnip="318784700361262",
            legal_address="г. Санкт-Петербург, Ленинский пр-кт, д. 144, кор. 1, стр. 2, оф. 302",
            phone="+7 (911) 921-30-39, +7 (911) 031-61-01",
            email="gorodok198@yandex.ru",
            website="remontstroyspb.ru",
        )
        result = _company_to_details_dict(company)
        self.assertEqual(result["title"], "<b>ИП Гордеев А.Н.</b>")
        inn_lines = [d for d in result["details"] if d.startswith("ИНН")]
        self.assertEqual(len(inn_lines), 1)
        self.assertIn("781144532689", inn_lines[0])
        self.assertNotIn("КПП", inn_lines[0])
        self.assertIn("ОГРНИП 318784700361262", result["details"])
        self.assertTrue(any("Адрес:" in d or "Юр. адрес:" in d for d in result["details"]))

    def test_empty_fields_are_skipped(self):
        company = _make_company(
            inn=None,
            kpp=None,
            ogrn=None,
            ogrnip=None,
            legal_address=None,
            phone=None,
            email=None,
            website=None,
        )
        result = _company_to_details_dict(company)
        self.assertEqual(result["title"], "<b>ООО «Декорартстрой»</b>")
        self.assertEqual(result["details"], [])

    def test_inn_without_kpp(self):
        company = _make_company(inn="1234567890", kpp=None)
        result = _company_to_details_dict(company)
        inn_lines = [d for d in result["details"] if d.startswith("ИНН")]
        self.assertEqual(len(inn_lines), 1)
        self.assertEqual(inn_lines[0], "ИНН 1234567890")

    def test_short_address_uses_address_label(self):
        company = _make_company(legal_address="Короткий адрес")
        result = _company_to_details_dict(company)
        addr_lines = [d for d in result["details"] if "Адрес:" in d or "Юр. адрес:" in d]
        self.assertEqual(len(addr_lines), 1)
        self.assertTrue(addr_lines[0].startswith("Адрес:"))

    def test_legal_name_fallback_to_short_name(self):
        company = _make_company(legal_name="")
        result = _company_to_details_dict(company)
        self.assertIn("ООО Декорартстрой", result["title"])


class TestGetCompanyDetailsDBLookup(unittest.TestCase):
    def test_found_by_short_name_ooo(self):
        company = _make_company(
            short_name="ООО Декорартстрой",
            legal_name="ООО «Декорартстрой»",
            inn="7811530330",
            kpp="780501001",
            ogrn="1127847464942",
        )
        mock_repo = MagicMock()
        mock_repo.get_company_by_short_name.return_value = company
        mock_repo.list_companies.return_value = [company]

        with patch("webapp.company_repository.CompanyRepository", return_value=mock_repo):
            result = _get_company_details("ООО Декорартстрой")

        self.assertEqual(result["title"], "<b>ООО «Декорартстрой»</b>")
        self.assertIn("ИНН 7811530330 / КПП 780501001", result["details"])
        mock_repo.get_company_by_short_name.assert_called_once_with("ООО Декорартстрой")

    def test_found_by_short_name_ip(self):
        company = _make_company(
            id=2,
            short_name="ИП Гордеев А.Н.",
            legal_name="ИП Гордеев А.Н.",
            inn="781144532689",
            kpp=None,
            ogrn=None,
            ogrnip="318784700361262",
        )
        mock_repo = MagicMock()
        mock_repo.get_company_by_short_name.return_value = company
        mock_repo.list_companies.return_value = [company]

        with patch("webapp.company_repository.CompanyRepository", return_value=mock_repo):
            result = _get_company_details("ИП Гордеев А.Н.")

        self.assertEqual(result["title"], "<b>ИП Гордеев А.Н.</b>")
        self.assertIn("ИНН 781144532689", result["details"])
        self.assertIn("ОГРНИП 318784700361262", result["details"])

    def test_found_by_legal_name_when_short_name_miss(self):
        company = _make_company(
            short_name="ООО Декорартстрой",
            legal_name="ООО «Декорартстрой»",
        )
        mock_repo = MagicMock()
        mock_repo.get_company_by_short_name.return_value = None
        mock_repo.list_companies.return_value = [company]

        with patch("webapp.company_repository.CompanyRepository", return_value=mock_repo):
            result = _get_company_details("ООО «Декорартстрой»")

        self.assertEqual(result["title"], "<b>ООО «Декорартстрой»</b>")
        mock_repo.get_company_by_short_name.assert_called_once_with("ООО «Декорартстрой»")
        mock_repo.list_companies.assert_called_once_with(include_inactive=False)

    def test_unknown_company_falls_back_to_hardcoded(self):
        mock_repo = MagicMock()
        mock_repo.get_company_by_short_name.return_value = None
        mock_repo.list_companies.return_value = []

        with patch("webapp.company_repository.CompanyRepository", return_value=mock_repo):
            result = _get_company_details("ООО Несуществующая")

        self.assertEqual(result, _HARDCODED_COMPANY_DETAILS["ООО Декорартстрой"])

    def test_db_exception_falls_back_to_hardcoded(self):
        mock_repo = MagicMock()
        mock_repo.get_company_by_short_name.side_effect = Exception("DB connection lost")

        with patch("webapp.company_repository.CompanyRepository", return_value=mock_repo):
            result = _get_company_details("ООО Декорартстрой")

        self.assertEqual(result, _HARDCODED_COMPANY_DETAILS["ООО Декорартстрой"])

    def test_db_not_found_falls_back_to_hardcoded(self):
        mock_repo = MagicMock()
        mock_repo.get_company_by_short_name.return_value = None
        mock_repo.list_companies.return_value = []

        with patch("webapp.company_repository.CompanyRepository", return_value=mock_repo):
            result = _get_company_details("ООО Декорартстрой")

        self.assertEqual(result, _HARDCODED_COMPANY_DETAILS["ООО Декорартстрой"])

    def test_import_error_falls_back_to_hardcoded(self):
        with patch.dict("sys.modules", {"webapp.company_repository": None}):
            result = _get_company_details("ООО Декорартстрой")

        self.assertEqual(result, _HARDCODED_COMPANY_DETAILS["ООО Декорартстрой"])

    def test_list_companies_exception_falls_back(self):
        mock_repo = MagicMock()
        mock_repo.get_company_by_short_name.return_value = None
        mock_repo.list_companies.side_effect = Exception("DB error on list")

        with patch("webapp.company_repository.CompanyRepository", return_value=mock_repo):
            result = _get_company_details("ООО «Декорартстрой»")

        self.assertEqual(result, _HARDCODED_COMPANY_DETAILS["ООО Декорартстрой"])


class TestGetCompanyDetailsLegacyFormat(unittest.TestCase):
    def test_ooo_hardcoded_matches_legacy_format(self):
        result = _hardcoded_company_details("ООО Декорартстрой")
        self.assertIn("title", result)
        self.assertIn("details", result)
        self.assertTrue(result["title"].startswith("<b>"))
        self.assertTrue(result["title"].endswith("</b>"))
        self.assertIsInstance(result["details"], list)
        for line in result["details"]:
            self.assertIsInstance(line, str)
            self.assertTrue(len(line) > 0)

    def test_ip_hardcoded_matches_legacy_format(self):
        result = _hardcoded_company_details("ИП Гордеев А.Н.")
        self.assertIn("title", result)
        self.assertIn("details", result)
        self.assertTrue(result["title"].startswith("<b>"))
        self.assertTrue(result["title"].endswith("</b>"))
        self.assertIsInstance(result["details"], list)
        for line in result["details"]:
            self.assertIsInstance(line, str)
            self.assertTrue(len(line) > 0)

    def test_ooo_from_db_structure_matches_hardcoded_keys(self):
        result = _hardcoded_company_details("ООО Декорартстрой")
        self.assertTrue(result["title"].startswith("<b>"))
        self.assertEqual(len(result["details"]), 7)
        self.assertTrue(any("ИНН" in d for d in result["details"]))
        self.assertTrue(any("ОГРН" in d for d in result["details"]))


if __name__ == "__main__":
    unittest.main()