import unittest

from webapp.company_repository import (
    Company,
    CompanyCreateInput,
    CompanyRepository,
    CompanyService,
    CompanyUpdateInput,
)
from webapp.db import get_connection


_COMPANY_TEST_PREFIX = "UTEST_"


class CompanyRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repo = CompanyRepository()
        self.service = CompanyService(self.repo)
        self._created_ids = []

    def tearDown(self):
        if self._created_ids:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    for cid in self._created_ids:
                        cur.execute("DELETE FROM companies WHERE id = %s", (cid,))
                conn.commit()

    def _create_test_company(self, **kwargs):
        defaults = {
            "legal_name": "Тестовая компания",
            "short_name": f"{_COMPANY_TEST_PREFIX}{id(self)}_{len(self._created_ids)}",
            "inn": "1234567890",
        }
        defaults.update(kwargs)
        company = self.repo.create_company(CompanyCreateInput(**defaults))
        self._created_ids.append(company.id)
        return company

    def test_seed_ooo_dekorartstroy_exists(self):
        company = self.repo.get_company_by_short_name("ООО Декорартстрой")
        self.assertIsNotNone(company)
        self.assertEqual(company.legal_name, "ООО «Декорартстрой»")
        self.assertEqual(company.inn, "7811530330")
        self.assertEqual(company.kpp, "780501001")
        self.assertEqual(company.ogrn, "1127847464942")
        self.assertTrue(company.is_active)
        self.assertEqual(company.watermark_text, "ДЕКОРАРТСТРОЙ")

    def test_seed_ip_gordeev_exists(self):
        company = self.repo.get_company_by_short_name("ИП Гордеев А.Н.")
        self.assertIsNotNone(company)
        self.assertEqual(company.legal_name, "ИП Гордеев А.Н.")
        self.assertEqual(company.inn, "781144532689")
        self.assertEqual(company.ogrnip, "318784700361262")
        self.assertEqual(company.director_name, "Гордеев Алексей Николаевич")
        self.assertEqual(company.watermark_text, "ИП ГОРДЕЕВ А.Н.")
        self.assertTrue(company.is_active)

    def test_list_companies_returns_active(self):
        companies = self.repo.list_companies()
        short_names = [c.short_name for c in companies]
        self.assertIn("ООО Декорартстрой", short_names)
        self.assertIn("ИП Гордеев А.Н.", short_names)

    def test_list_companies_includes_inactive(self):
        active = self.repo.list_companies()
        all_companies = self.repo.list_companies(include_inactive=True)
        self.assertGreaterEqual(len(all_companies), len(active))

    def test_get_company_by_id(self):
        by_short = self.repo.get_company_by_short_name("ООО Декорартстрой")
        by_id = self.repo.get_company(by_short.id)
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id.short_name, "ООО Декорартстрой")

    def test_create_company(self):
        company = self._create_test_company(
            legal_name="Тест ООО Ромашка",
            short_name="ООО Ромашка",
            inn="9876543210",
            kpp="123456789",
            watermark_text="РОМАШКА",
        )
        self.assertEqual(company.legal_name, "Тест ООО Ромашка")
        self.assertEqual(company.short_name, "ООО Ромашка")
        self.assertEqual(company.inn, "9876543210")
        self.assertEqual(company.watermark_text, "РОМАШКА")
        self.assertTrue(company.is_active)

    def test_update_company(self):
        company = self._create_test_company()
        updated = self.repo.update_company(
            company.id,
            CompanyUpdateInput(legal_name="Обновлённое название", inn="1111111111"),
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.legal_name, "Обновлённое название")
        self.assertEqual(updated.inn, "1111111111")

    def test_set_company_asset_paths(self):
        company = self._create_test_company()
        updated = self.repo.set_company_asset_paths(
            company.id,
            stamp_path="company-assets/1/stamp.png",
            signature_path="company-assets/1/signature.png",
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.stamp_path, "company-assets/1/stamp.png")
        self.assertEqual(updated.signature_path, "company-assets/1/signature.png")

    def test_set_stamp_path_only(self):
        company = self._create_test_company()
        updated = self.repo.set_company_asset_paths(company.id, stamp_path="company-assets/1/stamp.png")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.stamp_path, "company-assets/1/stamp.png")
        self.assertIsNone(updated.signature_path)

    def test_deactivate_company(self):
        company = self._create_test_company()
        self.assertTrue(company.is_active)
        deactivated = self.repo.deactivate_company(company.id)
        self.assertIsNotNone(deactivated)
        self.assertFalse(deactivated.is_active)

    def test_deactivate_hides_from_list(self):
        company = self._create_test_company()
        self.repo.deactivate_company(company.id)
        active = self.repo.list_companies(include_inactive=False)
        found = [c for c in active if c.id == company.id]
        self.assertEqual(len(found), 0)

    def test_deactivate_visible_in_all_list(self):
        company = self._create_test_company()
        self.repo.deactivate_company(company.id)
        all_companies = self.repo.list_companies(include_inactive=True)
        found = [c for c in all_companies if c.id == company.id]
        self.assertEqual(len(found), 1)

    def test_get_nonexistent_company(self):
        result = self.repo.get_company(999999)
        self.assertIsNone(result)

    def test_get_by_short_name_nonexistent(self):
        result = self.repo.get_company_by_short_name("Несуществующая компания")
        self.assertIsNone(result)

    def test_update_nonexistent_company(self):
        result = self.repo.update_company(999999, CompanyUpdateInput(legal_name="Не существует"))
        self.assertIsNone(result)

    def test_service_delegates_to_repository(self):
        company = self._create_test_company(short_name="СервисТест")
        found = self.service.get_company_by_short_name("СервисТест")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, company.id)
        listed = self.service.list_companies()
        self.assertTrue(any(c.id == company.id for c in listed))


if __name__ == "__main__":
    unittest.main()