"""Domain model for standalone estimates.

This module is intentionally isolated from FastAPI routes, templates, and the
current legacy project-bound estimate persistence. It defines the future-safe
backend concepts needed for a standalone estimate lifecycle and for a bot-ready
service layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import FrozenSet


class EstimateDomainError(ValueError):
    """Base exception for estimate domain validation errors."""


class InvalidStatusTransition(EstimateDomainError):
    """Raised when an estimate status transition is not allowed."""


class FinalVersionPolicyError(EstimateDomainError):
    """Raised when final-version metadata violates domain rules."""


class EstimateStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    REJECTED = "rejected"


class EstimateType(str, Enum):
    PRIMARY = "primary"
    ADDITIONAL = "additional"
    SUPPLEMENT = "supplement"


class OriginChannel(str, Enum):
    WEB = "web"
    TELEGRAM = "telegram"
    SYSTEM = "system"


class VersionKind(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    APPROVED = "approved"
    PROJECT_COPY = "project_copy"
    SUPPLEMENT = "supplement"


_ALLOWED_STATUS_TRANSITIONS: dict[EstimateStatus, FrozenSet[EstimateStatus]] = {
    EstimateStatus.DRAFT: frozenset(
        {
            EstimateStatus.DRAFT,
            EstimateStatus.SENT,
            EstimateStatus.REJECTED,
        }
    ),
    EstimateStatus.SENT: frozenset(
        {
            EstimateStatus.SENT,
            EstimateStatus.DRAFT,
            EstimateStatus.APPROVED,
            EstimateStatus.REJECTED,
        }
    ),
    EstimateStatus.APPROVED: frozenset(
        {
            EstimateStatus.APPROVED,
            EstimateStatus.IN_PROGRESS,
            EstimateStatus.REJECTED,
        }
    ),
    EstimateStatus.IN_PROGRESS: frozenset(
        {
            EstimateStatus.IN_PROGRESS,
        }
    ),
    EstimateStatus.REJECTED: frozenset(
        {
            EstimateStatus.REJECTED,
            EstimateStatus.DRAFT,
        }
    ),
}


def allowed_status_transitions(status: EstimateStatus) -> FrozenSet[EstimateStatus]:
    """Return the statuses that can follow the given status.

    Self-transitions are allowed to support idempotent service calls.
    """

    return _ALLOWED_STATUS_TRANSITIONS[status]


def can_transition_status(current: EstimateStatus, new: EstimateStatus) -> bool:
    return new in allowed_status_transitions(current)


@dataclass(frozen=True)
class EstimateVersion:
    version_number: int
    kind: VersionKind
    status_at_save: EstimateStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_final: bool = False
    stamp_applied: bool = False
    signature_applied: bool = False

    def __post_init__(self) -> None:
        if self.version_number < 1:
            raise FinalVersionPolicyError("Estimate version_number must be >= 1.")

        if self.is_final:
            if self.kind is not VersionKind.APPROVED:
                raise FinalVersionPolicyError(
                    "Only approved versions can be marked as final."
                )
            if self.status_at_save is not EstimateStatus.APPROVED:
                raise FinalVersionPolicyError(
                    "Final version must capture approved estimate status."
                )
        else:
            if self.stamp_applied or self.signature_applied:
                raise FinalVersionPolicyError(
                    "Stamp/signature are allowed only for final approved versions."
                )

        if self.stamp_applied or self.signature_applied:
            if not self.is_final:
                raise FinalVersionPolicyError(
                    "Stamp/signature require a final approved version."
                )
            if self.kind is not VersionKind.APPROVED:
                raise FinalVersionPolicyError(
                    "Stamp/signature require approved version kind."
                )
            if self.status_at_save is not EstimateStatus.APPROVED:
                raise FinalVersionPolicyError(
                    "Stamp/signature require approved estimate status."
                )


@dataclass(frozen=True)
class Estimate:
    estimate_type: EstimateType = EstimateType.PRIMARY
    status: EstimateStatus = EstimateStatus.DRAFT
    origin_channel: OriginChannel = OriginChannel.WEB
    project_id: int | None = None
    counterparty_id: int | None = None
    parent_estimate_id: int | None = None
    approved_version_number: int | None = None

    def __post_init__(self) -> None:
        if self.estimate_type is EstimateType.PRIMARY and self.parent_estimate_id is not None:
            raise EstimateDomainError(
                "Primary estimate cannot have parent_estimate_id."
            )
        if self.status is EstimateStatus.IN_PROGRESS and self.approved_version_number is None:
            raise EstimateDomainError(
                "In-progress estimate must reference an approved version."
            )


@dataclass(frozen=True)
class EstimateServiceCommand:
    """Minimal service-layer command descriptor for future Hermes integration."""

    action: str
    origin_channel: OriginChannel


BOT_READY_ACTIONS: FrozenSet[str] = frozenset(
    {
        "create_estimate",
        "create_additional_estimate",
        "append_items_to_estimate",
        "save_estimate_draft",
        "change_estimate_status",
        "prepare_estimate_for_client",
        "approve_estimate_with_final_snapshot",
        "generate_signed_pdf_for_approved_version",
        "create_project_from_estimate",
    }
)


def validate_service_action(action: str) -> str:
    if action not in BOT_READY_ACTIONS:
        raise EstimateDomainError(f"Unsupported estimate service action: {action}")
    return action


def transition_estimate_status(
    estimate: Estimate,
    new_status: EstimateStatus,
    *,
    approved_version_number: int | None = None,
) -> Estimate:
    """Return a new estimate instance with a validated status transition."""

    if not can_transition_status(estimate.status, new_status):
        raise InvalidStatusTransition(
            f"Cannot transition estimate from {estimate.status.value} to {new_status.value}."
        )

    if new_status is EstimateStatus.IN_PROGRESS:
        effective_version_number = (
            approved_version_number
            if approved_version_number is not None
            else estimate.approved_version_number
        )
        if effective_version_number is None:
            raise InvalidStatusTransition(
                "Cannot move estimate to in_progress without approved_version_number."
            )
        return Estimate(
            estimate_type=estimate.estimate_type,
            status=new_status,
            origin_channel=estimate.origin_channel,
            project_id=estimate.project_id,
            counterparty_id=estimate.counterparty_id,
            parent_estimate_id=estimate.parent_estimate_id,
            approved_version_number=effective_version_number,
        )

    if approved_version_number is not None and new_status is not EstimateStatus.APPROVED:
        raise InvalidStatusTransition(
            "approved_version_number can be supplied only for approved/in_progress states."
        )

    return Estimate(
        estimate_type=estimate.estimate_type,
        status=new_status,
        origin_channel=estimate.origin_channel,
        project_id=estimate.project_id,
        counterparty_id=estimate.counterparty_id,
        parent_estimate_id=estimate.parent_estimate_id,
        approved_version_number=(
            approved_version_number
            if new_status is EstimateStatus.APPROVED
            else estimate.approved_version_number
        ),
    )


def finalize_approved_version(
    *,
    version_number: int,
    stamp_applied: bool,
    signature_applied: bool,
) -> EstimateVersion:
    """Build the immutable final version eligible for project creation and PDF sealing."""

    return EstimateVersion(
        version_number=version_number,
        kind=VersionKind.APPROVED,
        status_at_save=EstimateStatus.APPROVED,
        is_final=True,
        stamp_applied=stamp_applied,
        signature_applied=signature_applied,
    )
