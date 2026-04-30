import unittest

from webapp.estimate_domain import (
    BOT_READY_ACTIONS,
    Estimate,
    EstimateDomainError,
    EstimateStatus,
    EstimateType,
    EstimateVersion,
    FinalVersionPolicyError,
    InvalidStatusTransition,
    OriginChannel,
    VersionKind,
    allowed_status_transitions,
    can_transition_status,
    finalize_approved_version,
    transition_estimate_status,
    validate_service_action,
)


class EstimateDomainTests(unittest.TestCase):
    def test_status_transition_matrix_matches_workflow_rules(self):
        self.assertEqual(
            allowed_status_transitions(EstimateStatus.DRAFT),
            frozenset(
                {
                    EstimateStatus.DRAFT,
                    EstimateStatus.SENT,
                    EstimateStatus.REJECTED,
                }
            ),
        )
        self.assertEqual(
            allowed_status_transitions(EstimateStatus.SENT),
            frozenset(
                {
                    EstimateStatus.SENT,
                    EstimateStatus.DRAFT,
                    EstimateStatus.APPROVED,
                    EstimateStatus.REJECTED,
                }
            ),
        )
        self.assertEqual(
            allowed_status_transitions(EstimateStatus.APPROVED),
            frozenset(
                {
                    EstimateStatus.APPROVED,
                    EstimateStatus.IN_PROGRESS,
                    EstimateStatus.REJECTED,
                }
            ),
        )
        self.assertEqual(
            allowed_status_transitions(EstimateStatus.IN_PROGRESS),
            frozenset({EstimateStatus.IN_PROGRESS}),
        )
        self.assertEqual(
            allowed_status_transitions(EstimateStatus.REJECTED),
            frozenset({EstimateStatus.REJECTED, EstimateStatus.DRAFT}),
        )

    def test_can_transition_status_accepts_and_rejects_expected_pairs(self):
        self.assertTrue(can_transition_status(EstimateStatus.DRAFT, EstimateStatus.SENT))
        self.assertTrue(can_transition_status(EstimateStatus.SENT, EstimateStatus.APPROVED))
        self.assertTrue(
            can_transition_status(EstimateStatus.APPROVED, EstimateStatus.IN_PROGRESS)
        )
        self.assertFalse(
            can_transition_status(EstimateStatus.DRAFT, EstimateStatus.IN_PROGRESS)
        )
        self.assertFalse(
            can_transition_status(EstimateStatus.REJECTED, EstimateStatus.APPROVED)
        )
        self.assertFalse(
            can_transition_status(EstimateStatus.IN_PROGRESS, EstimateStatus.DRAFT)
        )

    def test_estimate_defaults_support_standalone_draft_without_project_or_counterparty(self):
        estimate = Estimate()

        self.assertEqual(estimate.estimate_type, EstimateType.PRIMARY)
        self.assertEqual(estimate.status, EstimateStatus.DRAFT)
        self.assertEqual(estimate.origin_channel, OriginChannel.WEB)
        self.assertIsNone(estimate.project_id)
        self.assertIsNone(estimate.counterparty_id)
        self.assertIsNone(estimate.parent_estimate_id)
        self.assertIsNone(estimate.approved_version_number)

    def test_additional_and_supplement_estimates_can_reference_parent_estimate(self):
        additional = Estimate(
            estimate_type=EstimateType.ADDITIONAL,
            parent_estimate_id=10,
            origin_channel=OriginChannel.TELEGRAM,
        )
        supplement = Estimate(
            estimate_type=EstimateType.SUPPLEMENT,
            parent_estimate_id=10,
            origin_channel=OriginChannel.SYSTEM,
        )

        self.assertEqual(additional.parent_estimate_id, 10)
        self.assertEqual(additional.origin_channel, OriginChannel.TELEGRAM)
        self.assertEqual(supplement.parent_estimate_id, 10)
        self.assertEqual(supplement.origin_channel, OriginChannel.SYSTEM)

    def test_primary_estimate_cannot_have_parent(self):
        with self.assertRaises(EstimateDomainError):
            Estimate(estimate_type=EstimateType.PRIMARY, parent_estimate_id=99)

    def test_transition_to_in_progress_requires_approved_version_number(self):
        estimate = Estimate(status=EstimateStatus.APPROVED)

        with self.assertRaises(InvalidStatusTransition):
            transition_estimate_status(estimate, EstimateStatus.IN_PROGRESS)

    def test_transition_to_approved_and_in_progress_preserves_approved_version_number(self):
        draft = Estimate(status=EstimateStatus.SENT)
        approved = transition_estimate_status(
            draft,
            EstimateStatus.APPROVED,
            approved_version_number=3,
        )
        in_progress = transition_estimate_status(
            approved,
            EstimateStatus.IN_PROGRESS,
        )

        self.assertEqual(approved.status, EstimateStatus.APPROVED)
        self.assertEqual(approved.approved_version_number, 3)
        self.assertEqual(in_progress.status, EstimateStatus.IN_PROGRESS)
        self.assertEqual(in_progress.approved_version_number, 3)

    def test_transition_rejects_invalid_status_pairs(self):
        draft = Estimate(status=EstimateStatus.DRAFT)

        with self.assertRaises(InvalidStatusTransition):
            transition_estimate_status(draft, EstimateStatus.APPROVED)

    def test_estimate_version_disallows_stamp_or_signature_on_non_final_versions(self):
        with self.assertRaises(FinalVersionPolicyError):
            EstimateVersion(
                version_number=1,
                kind=VersionKind.DRAFT,
                status_at_save=EstimateStatus.DRAFT,
                is_final=False,
                stamp_applied=True,
            )

        with self.assertRaises(FinalVersionPolicyError):
            EstimateVersion(
                version_number=1,
                kind=VersionKind.SENT,
                status_at_save=EstimateStatus.SENT,
                is_final=False,
                signature_applied=True,
            )

    def test_finalize_approved_version_builds_final_snapshot_with_optional_stamp_and_signature(self):
        version = finalize_approved_version(
            version_number=7,
            stamp_applied=True,
            signature_applied=True,
        )

        self.assertEqual(version.version_number, 7)
        self.assertEqual(version.kind, VersionKind.APPROVED)
        self.assertEqual(version.status_at_save, EstimateStatus.APPROVED)
        self.assertTrue(version.is_final)
        self.assertTrue(version.stamp_applied)
        self.assertTrue(version.signature_applied)

    def test_only_approved_final_versions_are_allowed(self):
        with self.assertRaises(FinalVersionPolicyError):
            EstimateVersion(
                version_number=2,
                kind=VersionKind.SENT,
                status_at_save=EstimateStatus.SENT,
                is_final=True,
            )

    def test_bot_ready_actions_cover_web_telegram_and_project_creation_use_cases(self):
        self.assertIn("create_estimate", BOT_READY_ACTIONS)
        self.assertIn("create_additional_estimate", BOT_READY_ACTIONS)
        self.assertIn("append_items_to_estimate", BOT_READY_ACTIONS)
        self.assertIn("save_estimate_draft", BOT_READY_ACTIONS)
        self.assertIn("change_estimate_status", BOT_READY_ACTIONS)
        self.assertIn("prepare_estimate_for_client", BOT_READY_ACTIONS)
        self.assertIn("approve_estimate_with_final_snapshot", BOT_READY_ACTIONS)
        self.assertIn("generate_signed_pdf_for_approved_version", BOT_READY_ACTIONS)
        self.assertIn("create_project_from_estimate", BOT_READY_ACTIONS)
        self.assertEqual(validate_service_action("create_estimate"), "create_estimate")

        with self.assertRaises(EstimateDomainError):
            validate_service_action("destroy_estimate")


if __name__ == "__main__":
    unittest.main()
