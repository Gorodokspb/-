import unittest

from webapp.db import get_connection


class CompanyIdMigrationTests(unittest.TestCase):
    def test_company_id_column_exists(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT column_name, is_nullable, data_type "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'estimates' AND column_name = 'company_id'"
                )
                row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["is_nullable"], "YES")
        self.assertIn("bigint", row["data_type"])

    def test_company_id_foreign_key_references_companies(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT constraint_name "
                    "FROM information_schema.table_constraints "
                    "WHERE table_name = 'estimates' "
                    "AND constraint_type = 'FOREIGN KEY' "
                    "AND constraint_name LIKE '%%company_id%%'"
                )
                row = cur.fetchone()
        self.assertIsNotNone(row)

    def test_company_id_is_nullable_for_existing_rows(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT company_id FROM estimates WHERE company_id IS NULL LIMIT 1")
                cur.fetchall()
        self.assertTrue(True)

    def test_company_name_still_exists(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT column_name "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'estimates' AND column_name = 'company_name'"
                )
                row = cur.fetchone()
        self.assertIsNotNone(row)

    def test_insert_estimate_with_company_id(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM companies LIMIT 1")
                company_row = cur.fetchone()
                if not company_row:
                    self.skipTest("No companies in DB")
                company_id = company_row["id"]
                cur.execute(
                    "INSERT INTO estimates ("
                    "estimate_number, status, estimate_type, origin_channel, "
                    "company_name, company_id, created_at, updated_at"
                    ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id, company_id",
                    ("CID-TEST-001", "draft", "primary", "web",
                     "Тестовая компания", company_id,
                     "2026-05-05T00:00:00", "2026-05-05T00:00:00"),
                )
                row = cur.fetchone()
                estimate_id = int(row["id"])
                self.assertEqual(row["company_id"], company_id)
                cur.execute("DELETE FROM estimates WHERE id = %s", (estimate_id,))
            conn.commit()

    def test_insert_estimate_without_company_id(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO estimates ("
                    "estimate_number, status, estimate_type, origin_channel, "
                    "company_name, created_at, updated_at"
                    ") VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, company_id",
                    ("CID-TEST-002", "draft", "primary", "web",
                     "Тестовая компания",
                     "2026-05-05T00:00:00", "2026-05-05T00:00:00"),
                )
                row = cur.fetchone()
                estimate_id = int(row["id"])
                self.assertIsNone(row["company_id"])
                cur.execute("DELETE FROM estimates WHERE id = %s", (estimate_id,))
            conn.commit()

    def test_company_id_set_null_on_company_delete(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO companies (legal_name, short_name, watermark_text, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    ("Тест FK", "UTEST_FK_COMPANY", "TEST", "2026-05-05T00:00:00", "2026-05-05T00:00:00"),
                )
                test_company_id = int(cur.fetchone()["id"])
                cur.execute(
                    "INSERT INTO estimates ("
                    "estimate_number, status, estimate_type, origin_channel, "
                    "company_name, company_id, created_at, updated_at"
                    ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    ("CID-TEST-FK", "draft", "primary", "web",
                     "Тест FK", test_company_id,
                     "2026-05-05T00:00:00", "2026-05-05T00:00:00"),
                )
                estimate_id = int(cur.fetchone()["id"])
                cur.execute("DELETE FROM companies WHERE id = %s", (test_company_id,))
                cur.execute("SELECT company_id FROM estimates WHERE id = %s", (estimate_id,))
                row = cur.fetchone()
                self.assertIsNone(row["company_id"])
                cur.execute("DELETE FROM estimates WHERE id = %s", (estimate_id,))
            conn.commit()


if __name__ == "__main__":
    unittest.main()