"""Repository and service layer for standalone estimates.

This module works only with the new standalone estimate tables introduced in
stage 3 and stays isolated from the legacy project-bound estimate flow.
It is designed so the same service methods can later be called from web routes,
background jobs, or a Telegram/Hermes integration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from webapp.db import get_connection
from webapp.estimate_domain import (
    Estimate,
    EstimateDomainError,
    EstimateStatus,
    EstimateType,
    EstimateVersion,
    OriginChannel,
    VersionKind,
    transition_estimate_status,
    validate_service_action,
)


class EstimateRepositoryError(RuntimeError):
    """Raised for repository-level estimate lookup/update failures."""


@dataclass(frozen=True)
class EstimateItemInput:
    name: str
    sort_order: int
    row_type: str = "item"
    unit: str | None = None
    quantity: Decimal | float | int | str | None = None
    price: Decimal | float | int | str | None = None
    total: Decimal | float | int | str | None = None
    discounted_total: Decimal | float | int | str | None = None
    parent_section_id: int | None = None
    section_key: str | None = None
    reference: str | None = None
    price_source_type: str | None = None
    price_source_id: int | None = None
    is_manual_price: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class EstimateCreateInput:
    estimate_number: str
    title: str | None = None
    estimate_type: EstimateType = EstimateType.PRIMARY
    origin_channel: OriginChannel = OriginChannel.WEB
    project_id: int | None = None
    counterparty_id: int | None = None
    parent_estimate_id: int | None = None
    root_estimate_id: int | None = None
    customer_name: str | None = None
    object_name: str | None = None
    company_name: str | None = None
    contract_label: str | None = None
    discount: Decimal | float | int | str = Decimal("0")
    watermark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None


@dataclass(frozen=True)
class EstimateUpdateInput:
    title: str | None = None
    counterparty_id: int | None = None
    customer_name: str | None = None
    object_name: str | None = None
    company_name: str | None = None
    contract_label: str | None = None
    discount: Decimal | float | int | str | None = None
    watermark: str | None = None
    updated_by: str | None = None
    current_version_id: int | None = None
    approved_version_id: int | None = None
    final_document_id: int | None = None
    is_archived: bool | None = None


@dataclass(frozen=True)
class EstimateVersionCreateInput:
    estimate_id: int
    version_number: int
    version_kind: VersionKind
    status_at_save: EstimateStatus
    snapshot_json: dict[str, Any] | list[Any]
    calc_state_json: dict[str, Any] | list[Any] | None = None
    is_final: bool = False
    stamp_applied: bool = False
    signature_applied: bool = False
    document_id: int | None = None
    pdf_document_id: int | None = None
    change_comment: str | None = None
    source_event: str | None = None
    created_by: str | None = None


@dataclass(frozen=True)
class EstimateSummary:
    id: int
    estimate_number: str
    title: str | None
    status: EstimateStatus
    estimate_type: EstimateType
    origin_channel: OriginChannel
    project_id: int | None
    counterparty_id: int | None
    parent_estimate_id: int | None
    root_estimate_id: int | None
    current_version_id: int | None
    approved_version_id: int | None
    final_document_id: int | None
    customer_name: str | None
    object_name: str | None
    company_name: str | None
    contract_label: str | None
    discount: Decimal
    watermark: str | None
    is_archived: bool
    created_by: str | None
    updated_by: str | None
    created_at: str
    updated_at: str
    sent_at: str | None
    approved_at: str | None
    rejected_at: str | None
    project_created_at: str | None


@dataclass(frozen=True)
class EstimateDetails:
    estimate: EstimateSummary
    items: list[dict[str, Any]]
    versions: list[dict[str, Any]]
    status_history: list[dict[str, Any]]
    documents: list[dict[str, Any]]


@dataclass(frozen=True)
class EstimateRepository:
    """Thin repository over standalone estimate tables."""

    def create_estimate(self, data: EstimateCreateInput) -> EstimateSummary:
        now = _now_iso()
        root_estimate_id = data.root_estimate_id
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO estimates (
                        estimate_number, title, status, estimate_type, origin_channel,
                        project_id, counterparty_id, parent_estimate_id, root_estimate_id,
                        customer_name, object_name, company_name, contract_label,
                        discount, watermark, created_by, updated_by,
                        created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s
                    )
                    RETURNING *
                    """,
                    (
                        data.estimate_number,
                        data.title,
                        EstimateStatus.DRAFT.value,
                        data.estimate_type.value,
                        data.origin_channel.value,
                        data.project_id,
                        data.counterparty_id,
                        data.parent_estimate_id,
                        root_estimate_id,
                        data.customer_name,
                        data.object_name,
                        data.company_name,
                        data.contract_label,
                        _to_decimal(data.discount),
                        data.watermark,
                        data.created_by,
                        data.updated_by or data.created_by,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
                estimate_id = int(row["id"])
                if data.estimate_type is EstimateType.PRIMARY and row["root_estimate_id"] is None:
                    cur.execute(
                        "UPDATE estimates SET root_estimate_id = %s WHERE id = %s RETURNING *",
                        (estimate_id, estimate_id),
                    )
                    row = cur.fetchone()
                elif data.estimate_type is not EstimateType.PRIMARY and row["root_estimate_id"] is None:
                    resolved_root = data.parent_estimate_id or estimate_id
                    cur.execute(
                        "UPDATE estimates SET root_estimate_id = %s WHERE id = %s RETURNING *",
                        (resolved_root, estimate_id),
                    )
                    row = cur.fetchone()
            conn.commit()
        return _row_to_summary(row)

    def get_estimate(self, estimate_id: int) -> EstimateDetails:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM estimates WHERE id = %s", (estimate_id,))
                estimate_row = cur.fetchone()
                if not estimate_row:
                    raise EstimateRepositoryError(f"Estimate {estimate_id} not found.")

                cur.execute(
                    "SELECT * FROM estimate_items WHERE estimate_id = %s ORDER BY sort_order, id",
                    (estimate_id,),
                )
                items = [dict(row) for row in cur.fetchall()]

                cur.execute(
                    "SELECT * FROM estimate_versions WHERE estimate_id = %s ORDER BY version_number, id",
                    (estimate_id,),
                )
                versions = [_decode_version_row(dict(row)) for row in cur.fetchall()]

                cur.execute(
                    """
                    SELECT * FROM estimate_status_history
                    WHERE estimate_id = %s
                    ORDER BY changed_at, id
                    """,
                    (estimate_id,),
                )
                history = [dict(row) for row in cur.fetchall()]

                cur.execute(
                    """
                    SELECT * FROM estimate_documents
                    WHERE estimate_id = %s
                    ORDER BY created_at, id
                    """,
                    (estimate_id,),
                )
                documents = [dict(row) for row in cur.fetchall()]

        return EstimateDetails(
            estimate=_row_to_summary(estimate_row),
            items=items,
            versions=versions,
            status_history=history,
            documents=documents,
        )

    def list_estimates(
        self,
        *,
        project_id: int | None = None,
        estimate_type: EstimateType | None = None,
        include_archived: bool = False,
    ) -> list[EstimateSummary]:
        clauses: list[str] = []
        params: list[Any] = []
        if project_id is not None:
            clauses.append("project_id = %s")
            params.append(project_id)
        if estimate_type is not None:
            clauses.append("estimate_type = %s")
            params.append(estimate_type.value)
        if not include_archived:
            clauses.append("is_archived = FALSE")

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = (
            "SELECT * FROM estimates "
            f"{where_clause} "
            "ORDER BY COALESCE(updated_at, created_at) DESC, id DESC"
        )
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
        return [_row_to_summary(row) for row in rows]

    def update_estimate(self, estimate_id: int, data: EstimateUpdateInput) -> EstimateSummary:
        current = self.get_estimate(estimate_id).estimate
        payload = {
            "title": data.title if data.title is not None else current.title,
            "counterparty_id": data.counterparty_id if data.counterparty_id is not None else current.counterparty_id,
            "customer_name": data.customer_name if data.customer_name is not None else current.customer_name,
            "object_name": data.object_name if data.object_name is not None else current.object_name,
            "company_name": data.company_name if data.company_name is not None else current.company_name,
            "contract_label": data.contract_label if data.contract_label is not None else current.contract_label,
            "discount": _to_decimal(data.discount) if data.discount is not None else current.discount,
            "watermark": data.watermark if data.watermark is not None else current.watermark,
            "updated_by": data.updated_by if data.updated_by is not None else current.updated_by,
            "current_version_id": data.current_version_id if data.current_version_id is not None else current.current_version_id,
            "approved_version_id": data.approved_version_id if data.approved_version_id is not None else current.approved_version_id,
            "final_document_id": data.final_document_id if data.final_document_id is not None else current.final_document_id,
            "is_archived": data.is_archived if data.is_archived is not None else current.is_archived,
            "updated_at": _now_iso(),
        }
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE estimates
                    SET title = %s,
                        counterparty_id = %s,
                        customer_name = %s,
                        object_name = %s,
                        company_name = %s,
                        contract_label = %s,
                        discount = %s,
                        watermark = %s,
                        updated_by = %s,
                        current_version_id = %s,
                        approved_version_id = %s,
                        final_document_id = %s,
                        is_archived = %s,
                        updated_at = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        payload["title"],
                        payload["counterparty_id"],
                        payload["customer_name"],
                        payload["object_name"],
                        payload["company_name"],
                        payload["contract_label"],
                        payload["discount"],
                        payload["watermark"],
                        payload["updated_by"],
                        payload["current_version_id"],
                        payload["approved_version_id"],
                        payload["final_document_id"],
                        payload["is_archived"],
                        payload["updated_at"],
                        estimate_id,
                    ),
                )
                row = cur.fetchone()
                if not row:
                    raise EstimateRepositoryError(f"Estimate {estimate_id} not found.")
            conn.commit()
        return _row_to_summary(row)

    def save_estimate_items(self, estimate_id: int, items: list[EstimateItemInput]) -> list[dict[str, Any]]:
        self._require_estimate(estimate_id)
        rows = [_item_input_to_row(item) for item in items]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM estimate_items WHERE estimate_id = %s", (estimate_id,))
                for row in rows:
                    cur.execute(
                        """
                        INSERT INTO estimate_items (
                            estimate_id, sort_order, row_type, parent_section_id, section_key,
                            name, unit, quantity, price, total, discounted_total,
                            reference, price_source_type, price_source_id,
                            is_manual_price, notes, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        """,
                        (
                            estimate_id,
                            row["sort_order"],
                            row["row_type"],
                            row["parent_section_id"],
                            row["section_key"],
                            row["name"],
                            row["unit"],
                            row["quantity"],
                            row["price"],
                            row["total"],
                            row["discounted_total"],
                            row["reference"],
                            row["price_source_type"],
                            row["price_source_id"],
                            row["is_manual_price"],
                            row["notes"],
                            row["created_at"],
                            row["updated_at"],
                        ),
                    )
                cur.execute(
                    "SELECT * FROM estimate_items WHERE estimate_id = %s ORDER BY sort_order, id",
                    (estimate_id,),
                )
                saved = [dict(item) for item in cur.fetchall()]
                cur.execute(
                    "UPDATE estimates SET updated_at = %s WHERE id = %s",
                    (_now_iso(), estimate_id),
                )
            conn.commit()
        return saved

    def append_items_to_estimate(
        self, estimate_id: int, items: list[EstimateItemInput]
    ) -> list[dict[str, Any]]:
        self._require_estimate(estimate_id)
        if not items:
            return self.get_estimate(estimate_id).items
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COALESCE(MAX(sort_order), 0) AS max_sort_order FROM estimate_items WHERE estimate_id = %s",
                    (estimate_id,),
                )
                start = int(cur.fetchone()["max_sort_order"] or 0)
                now = _now_iso()
                for index, item in enumerate(items, start=1):
                    row = _item_input_to_row(item, force_sort_order=start + index, now=now)
                    cur.execute(
                        """
                        INSERT INTO estimate_items (
                            estimate_id, sort_order, row_type, parent_section_id, section_key,
                            name, unit, quantity, price, total, discounted_total,
                            reference, price_source_type, price_source_id,
                            is_manual_price, notes, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        """,
                        (
                            estimate_id,
                            row["sort_order"],
                            row["row_type"],
                            row["parent_section_id"],
                            row["section_key"],
                            row["name"],
                            row["unit"],
                            row["quantity"],
                            row["price"],
                            row["total"],
                            row["discounted_total"],
                            row["reference"],
                            row["price_source_type"],
                            row["price_source_id"],
                            row["is_manual_price"],
                            row["notes"],
                            row["created_at"],
                            row["updated_at"],
                        ),
                    )
                cur.execute(
                    "SELECT * FROM estimate_items WHERE estimate_id = %s ORDER BY sort_order, id",
                    (estimate_id,),
                )
                saved = [dict(item) for item in cur.fetchall()]
                cur.execute(
                    "UPDATE estimates SET updated_at = %s WHERE id = %s",
                    (_now_iso(), estimate_id),
                )
            conn.commit()
        return saved

    def create_estimate_version(self, data: EstimateVersionCreateInput) -> dict[str, Any]:
        self._require_estimate(data.estimate_id)
        now = _now_iso()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO estimate_versions (
                        estimate_id, version_number, version_kind, status_at_save,
                        snapshot_json, calc_state_json, is_final, stamp_applied,
                        signature_applied, document_id, pdf_document_id,
                        change_comment, source_event, created_by, created_at
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    RETURNING *
                    """,
                    (
                        data.estimate_id,
                        data.version_number,
                        data.version_kind.value,
                        data.status_at_save.value,
                        json.dumps(data.snapshot_json, ensure_ascii=False),
                        json.dumps(data.calc_state_json, ensure_ascii=False)
                        if data.calc_state_json is not None
                        else None,
                        data.is_final,
                        data.stamp_applied,
                        data.signature_applied,
                        data.document_id,
                        data.pdf_document_id,
                        data.change_comment,
                        data.source_event,
                        data.created_by,
                        now,
                    ),
                )
                row = dict(cur.fetchone())
                current_version_id = row["id"]
                approved_version_id = row["id"] if row["status_at_save"] == EstimateStatus.APPROVED.value else None
                cur.execute(
                    """
                    UPDATE estimates
                    SET current_version_id = %s,
                        approved_version_id = COALESCE(%s, approved_version_id),
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (current_version_id, approved_version_id, now, data.estimate_id),
                )
            conn.commit()
        return _decode_version_row(row)

    def change_estimate_status(
        self,
        estimate_id: int,
        new_status: EstimateStatus,
        *,
        changed_by: str | None = None,
        comment: str | None = None,
        approved_version_id: int | None = None,
    ) -> EstimateSummary:
        current = self.get_estimate(estimate_id).estimate
        transitioned = transition_estimate_status(
            _summary_to_domain(current),
            new_status,
            approved_version_number=approved_version_id,
        )
        now = _now_iso()
        sent_at = current.sent_at
        approved_at = current.approved_at
        rejected_at = current.rejected_at
        project_created_at = current.project_created_at
        if new_status is EstimateStatus.SENT:
            sent_at = now
        if new_status is EstimateStatus.APPROVED:
            approved_at = now
        elif new_status is EstimateStatus.REJECTED:
            approved_at = None
        if new_status is EstimateStatus.REJECTED:
            rejected_at = now
        elif new_status is not EstimateStatus.REJECTED:
            rejected_at = current.rejected_at
        if new_status is EstimateStatus.IN_PROGRESS and current.project_id is not None:
            project_created_at = now
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE estimates
                    SET status = %s,
                        approved_version_id = COALESCE(%s, approved_version_id),
                        updated_by = %s,
                        updated_at = %s,
                        sent_at = %s,
                        approved_at = %s,
                        rejected_at = %s,
                        project_created_at = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        transitioned.status.value,
                        approved_version_id,
                        changed_by,
                        now,
                        sent_at,
                        approved_at,
                        rejected_at,
                        project_created_at,
                        estimate_id,
                    ),
                )
                row = cur.fetchone()
                cur.execute(
                    """
                    INSERT INTO estimate_status_history (
                        estimate_id, old_status, new_status, comment, changed_by, changed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        estimate_id,
                        current.status.value,
                        transitioned.status.value,
                        comment,
                        changed_by,
                        now,
                    ),
                )
            conn.commit()
        return _row_to_summary(row)

    def link_estimate_to_project(self, estimate_id: int, project_id: int) -> EstimateSummary:
        self._require_estimate(estimate_id)
        now = _now_iso()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE estimates
                    SET project_id = %s,
                        updated_at = %s,
                        project_created_at = COALESCE(project_created_at, %s)
                    WHERE id = %s
                    RETURNING *
                    """,
                    (project_id, now, now, estimate_id),
                )
                row = cur.fetchone()
                if not row:
                    raise EstimateRepositoryError(f"Estimate {estimate_id} not found.")
            conn.commit()
        return _row_to_summary(row)

    def add_estimate_document(
        self,
        *,
        estimate_id: int,
        document_id: int,
        kind: str,
        estimate_version_id: int | None = None,
        is_current: bool = True,
    ) -> dict[str, Any]:
        self._require_estimate(estimate_id)
        now = _now_iso()
        with get_connection() as conn:
            with conn.cursor() as cur:
                if is_current:
                    cur.execute(
                        "UPDATE estimate_documents SET is_current = FALSE WHERE estimate_id = %s AND kind = %s",
                        (estimate_id, kind),
                    )
                cur.execute(
                    """
                    INSERT INTO estimate_documents (
                        estimate_id, estimate_version_id, document_id, kind, is_current, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (estimate_id, estimate_version_id, document_id, kind, is_current, now),
                )
                row = dict(cur.fetchone())
            conn.commit()
        return row

    def _require_estimate(self, estimate_id: int) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM estimates WHERE id = %s", (estimate_id,))
                if not cur.fetchone():
                    raise EstimateRepositoryError(f"Estimate {estimate_id} not found.")


class StandaloneEstimateService:
    """Bot-ready service layer for standalone estimates."""

    def __init__(self, repository: EstimateRepository | None = None):
        self.repository = repository or EstimateRepository()

    def build_estimate_snapshot(self, estimate_id: int) -> dict[str, Any]:
        details = self.repository.get_estimate(estimate_id)
        return {
            "estimate": {
                "id": details.estimate.id,
                "estimate_number": details.estimate.estimate_number,
                "title": details.estimate.title,
                "status": details.estimate.status.value,
                "estimate_type": details.estimate.estimate_type.value,
                "origin_channel": details.estimate.origin_channel.value,
                "project_id": details.estimate.project_id,
                "counterparty_id": details.estimate.counterparty_id,
                "parent_estimate_id": details.estimate.parent_estimate_id,
                "root_estimate_id": details.estimate.root_estimate_id,
                "current_version_id": details.estimate.current_version_id,
                "approved_version_id": details.estimate.approved_version_id,
                "final_document_id": details.estimate.final_document_id,
                "customer_name": details.estimate.customer_name,
                "object_name": details.estimate.object_name,
                "company_name": details.estimate.company_name,
                "contract_label": details.estimate.contract_label,
                "discount": str(details.estimate.discount),
                "watermark": details.estimate.watermark,
                "created_by": details.estimate.created_by,
                "updated_by": details.estimate.updated_by,
                "created_at": details.estimate.created_at,
                "updated_at": details.estimate.updated_at,
                "sent_at": details.estimate.sent_at,
                "approved_at": details.estimate.approved_at,
                "rejected_at": details.estimate.rejected_at,
                "project_created_at": details.estimate.project_created_at,
            },
            "items": details.items,
            "versions": details.versions,
            "status_history": details.status_history,
            "documents": details.documents,
        }

    def get_next_version_number(self, estimate_id: int) -> int:
        details = self.repository.get_estimate(estimate_id)
        if not details.versions:
            return 1
        return max(int(version["version_number"]) for version in details.versions) + 1

    def create_estimate(self, **kwargs) -> EstimateSummary:
        validate_service_action("create_estimate")
        domain_estimate = Estimate(
            estimate_type=kwargs.get("estimate_type", EstimateType.PRIMARY),
            status=EstimateStatus.DRAFT,
            origin_channel=kwargs.get("origin_channel", OriginChannel.WEB),
            project_id=kwargs.get("project_id"),
            counterparty_id=kwargs.get("counterparty_id"),
            parent_estimate_id=kwargs.get("parent_estimate_id"),
        )
        payload = EstimateCreateInput(
            estimate_number=kwargs["estimate_number"],
            title=kwargs.get("title"),
            estimate_type=domain_estimate.estimate_type,
            origin_channel=domain_estimate.origin_channel,
            project_id=domain_estimate.project_id,
            counterparty_id=domain_estimate.counterparty_id,
            parent_estimate_id=domain_estimate.parent_estimate_id,
            root_estimate_id=kwargs.get("root_estimate_id"),
            customer_name=kwargs.get("customer_name"),
            object_name=kwargs.get("object_name"),
            company_name=kwargs.get("company_name"),
            contract_label=kwargs.get("contract_label"),
            discount=kwargs.get("discount", Decimal("0")),
            watermark=kwargs.get("watermark"),
            created_by=kwargs.get("created_by"),
            updated_by=kwargs.get("updated_by"),
        )
        return self.repository.create_estimate(payload)

    def create_additional_estimate(self, *, parent_estimate_id: int, estimate_number: str, **kwargs) -> EstimateSummary:
        validate_service_action("create_additional_estimate")
        parent = self.repository.get_estimate(parent_estimate_id).estimate
        estimate_type = kwargs.get("estimate_type", EstimateType.ADDITIONAL)
        if estimate_type is EstimateType.PRIMARY:
            raise EstimateDomainError("Additional estimate cannot use primary type.")
        return self.create_estimate(
            estimate_number=estimate_number,
            title=kwargs.get("title"),
            estimate_type=estimate_type,
            origin_channel=kwargs.get("origin_channel", parent.origin_channel),
            project_id=kwargs.get("project_id", parent.project_id),
            counterparty_id=kwargs.get("counterparty_id", parent.counterparty_id),
            parent_estimate_id=parent_estimate_id,
            root_estimate_id=kwargs.get("root_estimate_id", parent.root_estimate_id or parent.id),
            customer_name=kwargs.get("customer_name", parent.customer_name),
            object_name=kwargs.get("object_name", parent.object_name),
            company_name=kwargs.get("company_name", parent.company_name),
            contract_label=kwargs.get("contract_label", parent.contract_label),
            discount=kwargs.get("discount", parent.discount),
            watermark=kwargs.get("watermark", parent.watermark),
            created_by=kwargs.get("created_by"),
            updated_by=kwargs.get("updated_by"),
        )

    def get_estimate(self, estimate_id: int) -> EstimateDetails:
        return self.repository.get_estimate(estimate_id)

    def list_estimates(self, **kwargs) -> list[EstimateSummary]:
        return self.repository.list_estimates(**kwargs)

    def update_estimate(self, estimate_id: int, **kwargs) -> EstimateSummary:
        return self.repository.update_estimate(estimate_id, EstimateUpdateInput(**kwargs))

    def save_estimate_items(self, estimate_id: int, items: list[EstimateItemInput]) -> list[dict[str, Any]]:
        validate_service_action("save_estimate_draft")
        return self.repository.save_estimate_items(estimate_id, items)

    def append_items_to_estimate(self, estimate_id: int, items: list[EstimateItemInput]) -> list[dict[str, Any]]:
        validate_service_action("append_items_to_estimate")
        return self.repository.append_items_to_estimate(estimate_id, items)

    def create_estimate_version(self, estimate_id: int, **kwargs) -> dict[str, Any]:
        domain_version = EstimateVersion(
            version_number=kwargs["version_number"],
            kind=kwargs["version_kind"],
            status_at_save=kwargs["status_at_save"],
            is_final=kwargs.get("is_final", False),
            stamp_applied=kwargs.get("stamp_applied", False),
            signature_applied=kwargs.get("signature_applied", False),
        )
        return self.repository.create_estimate_version(
            EstimateVersionCreateInput(
                estimate_id=estimate_id,
                version_number=domain_version.version_number,
                version_kind=domain_version.kind,
                status_at_save=domain_version.status_at_save,
                snapshot_json=kwargs["snapshot_json"],
                calc_state_json=kwargs.get("calc_state_json"),
                is_final=domain_version.is_final,
                stamp_applied=domain_version.stamp_applied,
                signature_applied=domain_version.signature_applied,
                document_id=kwargs.get("document_id"),
                pdf_document_id=kwargs.get("pdf_document_id"),
                change_comment=kwargs.get("change_comment"),
                source_event=kwargs.get("source_event"),
                created_by=kwargs.get("created_by"),
            )
        )

    def change_estimate_status(self, estimate_id: int, new_status: EstimateStatus, **kwargs) -> EstimateSummary:
        validate_service_action("change_estimate_status")
        return self.repository.change_estimate_status(
            estimate_id,
            new_status,
            changed_by=kwargs.get("changed_by"),
            comment=kwargs.get("comment"),
            approved_version_id=kwargs.get("approved_version_id"),
        )

    def link_estimate_to_project(self, estimate_id: int, project_id: int) -> EstimateSummary:
        validate_service_action("create_project_from_estimate")
        return self.repository.link_estimate_to_project(estimate_id, project_id)

    def list_estimates(
        self,
        *,
        project_id: int | None = None,
        estimate_type: EstimateType | None = None,
        include_archived: bool = False,
    ) -> list[EstimateSummary]:
        return self.repository.list_estimates(
            project_id=project_id,
            estimate_type=estimate_type,
            include_archived=include_archived,
        )

    def add_estimate_document(self, **kwargs) -> dict[str, Any]:
        return self.repository.add_estimate_document(**kwargs)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _to_decimal(value: Decimal | float | int | str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _item_input_to_row(
    item: EstimateItemInput,
    *,
    force_sort_order: int | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    if not item.name.strip():
        raise EstimateRepositoryError("Estimate item name is required.")
    timestamp = now or _now_iso()
    return {
        "sort_order": force_sort_order if force_sort_order is not None else int(item.sort_order),
        "row_type": item.row_type,
        "parent_section_id": item.parent_section_id,
        "section_key": item.section_key,
        "name": item.name.strip(),
        "unit": item.unit,
        "quantity": _to_decimal(item.quantity),
        "price": _to_decimal(item.price),
        "total": _to_decimal(item.total),
        "discounted_total": _to_decimal(item.discounted_total),
        "reference": item.reference,
        "price_source_type": item.price_source_type,
        "price_source_id": item.price_source_id,
        "is_manual_price": bool(item.is_manual_price),
        "notes": item.notes,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _row_to_summary(row: dict[str, Any]) -> EstimateSummary:
    return EstimateSummary(
        id=int(row["id"]),
        estimate_number=row["estimate_number"],
        title=row.get("title"),
        status=EstimateStatus(row["status"]),
        estimate_type=EstimateType(row["estimate_type"]),
        origin_channel=OriginChannel(row["origin_channel"]),
        project_id=row.get("project_id"),
        counterparty_id=row.get("counterparty_id"),
        parent_estimate_id=row.get("parent_estimate_id"),
        root_estimate_id=row.get("root_estimate_id"),
        current_version_id=row.get("current_version_id"),
        approved_version_id=row.get("approved_version_id"),
        final_document_id=row.get("final_document_id"),
        customer_name=row.get("customer_name"),
        object_name=row.get("object_name"),
        company_name=row.get("company_name"),
        contract_label=row.get("contract_label"),
        discount=row.get("discount") if isinstance(row.get("discount"), Decimal) else Decimal(str(row.get("discount") or "0")),
        watermark=row.get("watermark"),
        is_archived=bool(row.get("is_archived")),
        created_by=row.get("created_by"),
        updated_by=row.get("updated_by"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        sent_at=row.get("sent_at"),
        approved_at=row.get("approved_at"),
        rejected_at=row.get("rejected_at"),
        project_created_at=row.get("project_created_at"),
    )


def _summary_to_domain(summary: EstimateSummary) -> Estimate:
    return Estimate(
        estimate_type=summary.estimate_type,
        status=summary.status,
        origin_channel=summary.origin_channel,
        project_id=summary.project_id,
        counterparty_id=summary.counterparty_id,
        parent_estimate_id=summary.parent_estimate_id,
        approved_version_number=summary.approved_version_id,
    )


def _decode_version_row(row: dict[str, Any]) -> dict[str, Any]:
    row["version_kind"] = VersionKind(row["version_kind"])
    row["status_at_save"] = EstimateStatus(row["status_at_save"])
    row["snapshot_json"] = json.loads(row["snapshot_json"])
    row["calc_state_json"] = json.loads(row["calc_state_json"]) if row.get("calc_state_json") else None
    return row
