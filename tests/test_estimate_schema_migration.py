from pathlib import Path
import unittest


MIGRATION_SQL = Path(
    "/opt/dekorcrm/app/CRM_OLD_BAD/migrations/20260429_create_standalone_estimates.sql"
)


class EstimateSchemaMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION_SQL.read_text(encoding="utf-8")

    def test_migration_creates_all_standalone_estimate_tables(self):
        for table_name in [
            "estimates",
            "estimate_items",
            "estimate_versions",
            "estimate_status_history",
            "estimate_documents",
        ]:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table_name}", self.sql)

    def test_estimates_table_supports_nullable_project_counterparty_and_version_links(self):
        required_fragments = [
            "project_id BIGINT NULL",
            "counterparty_id BIGINT NULL",
            "estimate_type TEXT NOT NULL DEFAULT 'primary'",
            "parent_estimate_id BIGINT NULL",
            "root_estimate_id BIGINT NULL",
            "origin_channel TEXT NOT NULL DEFAULT 'web'",
            "current_version_id BIGINT NULL",
            "approved_version_id BIGINT NULL",
            "final_document_id BIGINT NULL",
            "REFERENCES projects(id) ON DELETE SET NULL",
            "REFERENCES counterparties(id) ON DELETE SET NULL",
        ]
        for fragment in required_fragments:
            self.assertIn(fragment, self.sql)

    def test_version_table_keeps_stamp_and_signature_only_on_final_approved_versions(self):
        self.assertIn("stamp_applied BOOLEAN NOT NULL DEFAULT FALSE", self.sql)
        self.assertIn("signature_applied BOOLEAN NOT NULL DEFAULT FALSE", self.sql)
        self.assertIn("chk_estimate_versions_signature_stamp_final_only", self.sql)
        self.assertIn("version_kind = 'approved'", self.sql)
        self.assertIn("status_at_save = 'approved'", self.sql)
        self.assertIn("is_final = TRUE", self.sql)

    def test_estimate_documents_table_links_estimate_versions_and_documents(self):
        self.assertIn("estimate_version_id BIGINT NULL", self.sql)
        self.assertIn("document_id BIGINT NOT NULL", self.sql)
        self.assertIn("kind TEXT NOT NULL", self.sql)
        self.assertIn("REFERENCES estimate_versions(id) ON DELETE SET NULL", self.sql)
        self.assertIn("REFERENCES documents(id) ON DELETE CASCADE", self.sql)

    def test_migration_is_parallel_to_legacy_tables_and_contains_no_drop_statements(self):
        forbidden = [
            "DROP TABLE projects",
            "DROP TABLE documents",
            "DROP TABLE smeta_drafts",
            "ALTER TABLE projects",
            "ALTER TABLE documents",
            "ALTER TABLE smeta_drafts",
        ]
        for fragment in forbidden:
            self.assertNotIn(fragment, self.sql)


if __name__ == "__main__":
    unittest.main()
