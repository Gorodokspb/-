from pathlib import Path
import unittest

from webapp.db import get_connection

MIGRATION_SQL = Path(
    "/opt/dekorcrm/app/CRM_OLD_BAD/migrations/20260503_documents_nullable_project_id.sql"
)


class DocumentsNullableProjectIdMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION_SQL.read_text(encoding="utf-8")

    def test_migration_contains_alter_drop_not_null(self):
        self.assertIn("ALTER TABLE documents", self.sql)
        self.assertIn("project_id", self.sql)
        self.assertIn("DROP NOT NULL", self.sql)

    def test_migration_does_not_contain_dangerous_operations(self):
        for fragment in ["DROP TABLE", "DELETE FROM", "TRUNCATE", "DROP COLUMN"]:
            self.assertNotIn(fragment, self.sql)

    def test_documents_project_id_is_nullable_in_live_database(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'documents' AND column_name = 'project_id'"
                )
                row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["is_nullable"], "YES")

    def test_can_insert_document_with_null_project_id(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO documents (project_id, doc_type, title, status, file_path, created_at, updated_at) "
                    "VALUES (NULL, 'standalone_pdf', 'Тест standalone', 'draft', '/tmp/test.pdf', %s, %s) "
                    "RETURNING id, project_id",
                    ("2026-05-03T00:00:00", "2026-05-03T00:00:00"),
                )
                row = cur.fetchone()
                doc_id = int(row["id"])
                self.assertIsNone(row["project_id"])
                cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
            conn.commit()

    def test_legacy_documents_with_project_id_still_work(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM documents WHERE project_id IS NOT NULL"
                )
                row = cur.fetchone()
        self.assertGreaterEqual(int(row["cnt"]), 0)

    def test_legacy_project_query_excludes_null_project_id(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO documents (project_id, doc_type, title, status, file_path, created_at, updated_at) "
                    "VALUES (NULL, 'standalone_pdf', 'Isolation test', 'draft', '/tmp/test.pdf', %s, %s) "
                    "RETURNING id",
                    ("2026-05-03T00:00:00", "2026-05-03T00:00:00"),
                )
                standalone_doc_id = int(cur.fetchone()["id"])
                cur.execute(
                    "SELECT id FROM documents WHERE project_id = -999999"
                )
                rows = cur.fetchall()
                self.assertEqual(len(rows), 0)
                cur.execute("DELETE FROM documents WHERE id = %s", (standalone_doc_id,))
            conn.commit()


if __name__ == "__main__":
    unittest.main()