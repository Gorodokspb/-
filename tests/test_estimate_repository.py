import unittest
from decimal import Decimal

from webapp.db import get_connection
from webapp.estimate_domain import EstimateDomainError, EstimateStatus, EstimateType, OriginChannel, VersionKind
from webapp.estimate_repository import (
    EstimateItemInput,
    EstimateRepository,
    EstimateRepositoryError,
    StandaloneEstimateService,
)


class StandaloneEstimateRepositoryServiceTests(unittest.TestCase):
    def setUp(self):
        self._cleanup_tables()
        self.repository = EstimateRepository()
        self.service = StandaloneEstimateService(self.repository)
        self.existing_project_id = self._fetch_existing_project_id()

    def tearDown(self):
        self._cleanup_tables()

    def _cleanup_tables(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM estimate_documents")
                cur.execute("DELETE FROM estimate_status_history")
                cur.execute("DELETE FROM estimate_items")
                cur.execute("DELETE FROM estimate_versions")
                cur.execute("DELETE FROM estimates")
                cur.execute("DELETE FROM documents WHERE project_id IS NULL")
            conn.commit()

    def _fetch_existing_project_id(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM projects ORDER BY id LIMIT 1")
                row = cur.fetchone()
        self.assertIsNotNone(row, "Expected at least one existing legacy project for link tests")
        return int(row["id"])

    def test_create_estimate_creates_standalone_draft_with_nullable_project_and_counterparty(self):
        estimate = self.service.create_estimate(
            estimate_number="EST-001",
            title="Самостоятельная смета",
            origin_channel=OriginChannel.TELEGRAM,
            created_by="hermes",
        )

        self.assertEqual(estimate.status, EstimateStatus.DRAFT)
        self.assertEqual(estimate.estimate_type, EstimateType.PRIMARY)
        self.assertEqual(estimate.origin_channel, OriginChannel.TELEGRAM)
        self.assertIsNone(estimate.project_id)
        self.assertIsNone(estimate.counterparty_id)
        self.assertEqual(estimate.root_estimate_id, estimate.id)

    def test_create_additional_estimate_inherits_parent_context_and_sets_parent_links(self):
        parent = self.service.create_estimate(
            estimate_number="EST-BASE",
            title="Основная смета",
            project_id=self.existing_project_id,
            customer_name="Иван",
            object_name="Объект",
        )

        child = self.service.create_additional_estimate(
            parent_estimate_id=parent.id,
            estimate_number="EST-ADD-01",
            title="Допработы",
            estimate_type=EstimateType.ADDITIONAL,
        )

        self.assertEqual(child.estimate_type, EstimateType.ADDITIONAL)
        self.assertEqual(child.parent_estimate_id, parent.id)
        self.assertEqual(child.root_estimate_id, parent.id)
        self.assertEqual(child.project_id, parent.project_id)
        self.assertEqual(child.customer_name, parent.customer_name)

    def test_create_additional_estimate_rejects_primary_type(self):
        parent = self.service.create_estimate(estimate_number="EST-PARENT")
        with self.assertRaises(EstimateDomainError):
            self.service.create_additional_estimate(
                parent_estimate_id=parent.id,
                estimate_number="EST-BAD",
                estimate_type=EstimateType.PRIMARY,
            )

    def test_save_and_append_items_persist_only_new_estimate_items(self):
        estimate = self.service.create_estimate(estimate_number="EST-ITEMS")

        saved = self.service.save_estimate_items(
            estimate.id,
            [
                EstimateItemInput(name="Стены", sort_order=10, quantity="20", price="100", total="2000"),
                EstimateItemInput(name="Пол", sort_order=20, quantity="10", price="300", total="3000"),
            ],
        )
        self.assertEqual(len(saved), 2)
        self.assertEqual([row["sort_order"] for row in saved], [10, 20])

        appended = self.service.append_items_to_estimate(
            estimate.id,
            [EstimateItemInput(name="Плинтус", sort_order=1, quantity="8", price="50", total="400")],
        )
        self.assertEqual(len(appended), 3)
        self.assertEqual(appended[-1]["name"], "Плинтус")
        self.assertEqual(appended[-1]["sort_order"], 21)

    def test_update_estimate_changes_metadata_without_touching_legacy_tables(self):
        estimate = self.service.create_estimate(
            estimate_number="EST-UPD",
            title="Черновик",
            customer_name="Старый клиент",
            discount="0",
        )

        updated = self.service.update_estimate(
            estimate.id,
            title="Обновлённая смета",
            customer_name="Новый клиент",
            object_name="Новый объект",
            discount="12.5",
            watermark="for-client",
            updated_by="manager",
        )

        self.assertEqual(updated.title, "Обновлённая смета")
        self.assertEqual(updated.customer_name, "Новый клиент")
        self.assertEqual(updated.object_name, "Новый объект")
        self.assertEqual(updated.discount, Decimal("12.5"))
        self.assertEqual(updated.watermark, "for-client")
        self.assertEqual(updated.updated_by, "manager")

    def test_create_version_updates_current_and_approved_version_links(self):
        estimate = self.service.create_estimate(estimate_number="EST-VERS")

        draft_version = self.service.create_estimate_version(
            estimate.id,
            version_number=1,
            version_kind=VersionKind.DRAFT,
            status_at_save=EstimateStatus.DRAFT,
            snapshot_json={"items": []},
            calc_state_json={"area": 10},
            source_event="manual_save",
            created_by="manager",
        )
        self.assertEqual(draft_version["version_number"], 1)
        self.assertEqual(draft_version["version_kind"], VersionKind.DRAFT)

        approved_version = self.service.create_estimate_version(
            estimate.id,
            version_number=2,
            version_kind=VersionKind.APPROVED,
            status_at_save=EstimateStatus.APPROVED,
            snapshot_json={"items": [{"name": "Стены"}]},
            is_final=True,
            stamp_applied=True,
            signature_applied=True,
            source_event="approve",
            created_by="manager",
        )
        details = self.service.get_estimate(estimate.id)
        self.assertEqual(details.estimate.current_version_id, approved_version["id"])
        self.assertEqual(details.estimate.approved_version_id, approved_version["id"])
        self.assertTrue(approved_version["is_final"])
        self.assertTrue(approved_version["stamp_applied"])
        self.assertTrue(approved_version["signature_applied"])

    def test_change_estimate_status_writes_history_and_enforces_domain_rules(self):
        estimate = self.service.create_estimate(estimate_number="EST-STATUS")

        sent = self.service.change_estimate_status(
            estimate.id,
            EstimateStatus.SENT,
            changed_by="manager",
            comment="Отправили клиенту",
        )
        self.assertEqual(sent.status, EstimateStatus.SENT)
        self.assertIsNotNone(sent.sent_at)

        approved_version = self.service.create_estimate_version(
            estimate.id,
            version_number=1,
            version_kind=VersionKind.APPROVED,
            status_at_save=EstimateStatus.APPROVED,
            snapshot_json={"items": []},
            is_final=True,
            stamp_applied=True,
            signature_applied=True,
        )
        approved = self.service.change_estimate_status(
            estimate.id,
            EstimateStatus.APPROVED,
            changed_by="manager",
            approved_version_id=approved_version["id"],
        )
        self.assertEqual(approved.status, EstimateStatus.APPROVED)
        self.assertEqual(approved.approved_version_id, approved_version["id"])
        self.assertIsNotNone(approved.approved_at)

        in_progress = self.service.change_estimate_status(
            estimate.id,
            EstimateStatus.IN_PROGRESS,
            changed_by="manager",
            approved_version_id=approved_version["id"],
        )
        self.assertEqual(in_progress.status, EstimateStatus.IN_PROGRESS)

        details = self.service.get_estimate(estimate.id)
        self.assertEqual(len(details.status_history), 3)
        self.assertEqual(details.status_history[0]["new_status"], EstimateStatus.SENT.value)
        self.assertEqual(details.status_history[-1]["new_status"], EstimateStatus.IN_PROGRESS.value)

    def test_change_estimate_status_rejects_invalid_transition(self):
        estimate = self.service.create_estimate(estimate_number="EST-BAD-STATUS")
        with self.assertRaises(EstimateDomainError):
            self.service.change_estimate_status(estimate.id, EstimateStatus.IN_PROGRESS)

    def test_link_estimate_to_project_updates_project_reference(self):
        estimate = self.service.create_estimate(estimate_number="EST-LINK")
        linked = self.service.link_estimate_to_project(estimate.id, self.existing_project_id)
        self.assertEqual(linked.project_id, self.existing_project_id)
        self.assertIsNotNone(linked.project_created_at)

    def test_list_estimates_supports_filters_and_archived_flag(self):
        standalone = self.service.create_estimate(estimate_number="EST-LIST-1")
        project_bound = self.service.create_estimate(
            estimate_number="EST-LIST-2",
            project_id=self.existing_project_id,
        )
        additional = self.service.create_additional_estimate(
            parent_estimate_id=standalone.id,
            estimate_number="EST-LIST-3",
            estimate_type=EstimateType.ADDITIONAL,
        )
        self.service.update_estimate(standalone.id, is_archived=True)

        default_rows = self.service.list_estimates()
        self.assertEqual([row.id for row in default_rows], [additional.id, project_bound.id])

        all_rows = self.service.list_estimates(include_archived=True)
        self.assertEqual(len(all_rows), 3)

        by_project = self.service.list_estimates(project_id=self.existing_project_id)
        self.assertEqual([row.id for row in by_project], [project_bound.id])

        additional_only = self.service.list_estimates(
            include_archived=True,
            estimate_type=EstimateType.ADDITIONAL,
        )
        self.assertEqual([row.id for row in additional_only], [additional.id])

    def test_get_estimate_raises_for_missing_id(self):
        with self.assertRaises(EstimateRepositoryError):
            self.repository.get_estimate(999999)

    def test_create_standalone_document_inserts_with_null_project_id(self):
        doc_id = self.repository.create_standalone_document(
            file_path="Сметы/standalone-estimates/000001_Смета/Смета-approved.pdf",
            pdf_path="Сметы/standalone-estimates/000001_Смета/Смета-approved.pdf",
            title="Final PDF: Смета",
            doc_type="standalone_approved_pdf",
            status="approved",
        )
        self.assertIsInstance(doc_id, int)
        self.assertGreater(doc_id, 0)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, project_id, doc_type, title FROM documents WHERE id = %s", (doc_id,))
                row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row["project_id"])
        self.assertEqual(row["doc_type"], "standalone_approved_pdf")

    def test_update_version_pdf_document_id_links_document_to_version(self):
        estimate = self.service.create_estimate(
            estimate_number="EST-DOCVER",
            title="Test version doc",
            created_by="tester",
        )
        version = self.service.create_estimate_version(
            estimate.id,
            version_number=1,
            version_kind=VersionKind.DRAFT,
            status_at_save=EstimateStatus.DRAFT,
            snapshot_json={"estimate": {"id": estimate.id}},
            calc_state_json={},
            source_event="test",
            created_by="tester",
        )
        doc_id = self.repository.create_standalone_document(
            file_path="test.pdf",
            pdf_path="test.pdf",
            title="Test PDF",
        )
        self.repository.update_version_pdf_document_id(version_id=int(version["id"]), document_id=doc_id)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pdf_document_id FROM estimate_versions WHERE id = %s", (int(version["id"]),))
                row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(int(row["pdf_document_id"]), doc_id)


if __name__ == "__main__":
    unittest.main()
