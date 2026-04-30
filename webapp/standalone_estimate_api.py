from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from webapp.config import get_settings
from webapp.estimate_domain import EstimateStatus, EstimateType, OriginChannel, VersionKind
from webapp.estimate_repository import (
    EstimateDomainError,
    EstimateItemInput,
    EstimateRepositoryError,
    StandaloneEstimateService,
)
from webapp.standalone_estimate_files import (
    export_standalone_estimate_json,
    export_standalone_estimate_pdf,
)

router = APIRouter()
settings = get_settings()
service = StandaloneEstimateService()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _require_auth(request: Request) -> None:
    if not request.session.get("is_authenticated"):
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
        )


def _username(request: Request) -> str:
    return str(request.session.get("username") or settings.admin_username)


async def _load_payload(request: Request) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        return payload if isinstance(payload, dict) else {}
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        return dict(form)
    try:
        payload = await request.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_estimate_type(value: Any) -> EstimateType:
    if isinstance(value, EstimateType):
        return value
    return EstimateType(str(value or EstimateType.PRIMARY.value))


def _parse_origin_channel(value: Any) -> OriginChannel:
    if isinstance(value, OriginChannel):
        return value
    return OriginChannel(str(value or OriginChannel.WEB.value))


def _parse_status(value: Any) -> EstimateStatus:
    if isinstance(value, EstimateStatus):
        return value
    return EstimateStatus(str(value))


def _version_kind_for_status(status_value: EstimateStatus) -> VersionKind:
    if status_value is EstimateStatus.SENT:
        return VersionKind.SENT
    if status_value in {EstimateStatus.APPROVED, EstimateStatus.IN_PROGRESS}:
        return VersionKind.APPROVED
    return VersionKind.DRAFT


def _normalize_items(raw_items: list[Any]) -> list[EstimateItemInput]:
    items: list[EstimateItemInput] = []
    for index, raw_item in enumerate(raw_items or [], start=1):
        if not isinstance(raw_item, dict):
            continue
        items.append(
            EstimateItemInput(
                name=str(raw_item.get("name") or "").strip(),
                sort_order=int(raw_item.get("sort_order") or index),
                row_type=str(raw_item.get("row_type") or "item"),
                unit=(str(raw_item.get("unit")) if raw_item.get("unit") is not None else None),
                quantity=raw_item.get("quantity"),
                price=raw_item.get("price"),
                total=raw_item.get("total"),
                discounted_total=raw_item.get("discounted_total"),
                parent_section_id=raw_item.get("parent_section_id"),
                section_key=raw_item.get("section_key"),
                reference=raw_item.get("reference"),
                price_source_type=raw_item.get("price_source_type"),
                price_source_id=raw_item.get("price_source_id"),
                is_manual_price=bool(raw_item.get("is_manual_price")),
                notes=raw_item.get("notes"),
            )
        )
    return items


def _serialize_summary(summary) -> dict[str, Any]:
    return {
        "id": summary.id,
        "estimate_number": summary.estimate_number,
        "title": summary.title,
        "status": summary.status.value,
        "estimate_type": summary.estimate_type.value,
        "origin_channel": summary.origin_channel.value,
        "project_id": summary.project_id,
        "counterparty_id": summary.counterparty_id,
        "parent_estimate_id": summary.parent_estimate_id,
        "root_estimate_id": summary.root_estimate_id,
        "current_version_id": summary.current_version_id,
        "approved_version_id": summary.approved_version_id,
        "final_document_id": summary.final_document_id,
        "customer_name": summary.customer_name,
        "object_name": summary.object_name,
        "company_name": summary.company_name,
        "contract_label": summary.contract_label,
        "discount": str(summary.discount),
        "watermark": summary.watermark,
        "is_archived": summary.is_archived,
        "created_by": summary.created_by,
        "updated_by": summary.updated_by,
        "created_at": summary.created_at,
        "updated_at": summary.updated_at,
        "sent_at": summary.sent_at,
        "approved_at": summary.approved_at,
        "rejected_at": summary.rejected_at,
        "project_created_at": summary.project_created_at,
    }


def _serialize_details(details) -> dict[str, Any]:
    versions = []
    for version in details.versions:
        version_row = dict(version)
        version_row["version_kind"] = version_row["version_kind"].value
        version_row["status_at_save"] = version_row["status_at_save"].value
        versions.append(_json_safe(version_row))
    return {
        "estimate": _json_safe(_serialize_summary(details.estimate)),
        "items": _json_safe(details.items),
        "versions": versions,
        "status_history": _json_safe(details.status_history),
        "documents": _json_safe(details.documents),
    }


def _json_safe(value: Any):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _create_snapshot_version(
    estimate_id: int,
    *,
    actor: str,
    status_value: EstimateStatus,
    source_event: str,
    is_final: bool = False,
    stamp_applied: bool = False,
    signature_applied: bool = False,
    change_comment: str | None = None,
):
    snapshot = _json_safe(service.build_estimate_snapshot(estimate_id))
    return service.create_estimate_version(
        estimate_id,
        version_number=service.get_next_version_number(estimate_id),
        version_kind=_version_kind_for_status(status_value),
        status_at_save=status_value,
        snapshot_json=snapshot,
        calc_state_json={},
        is_final=is_final,
        stamp_applied=stamp_applied,
        signature_applied=signature_applied,
        source_event=source_event,
        change_comment=change_comment,
        created_by=actor,
    )


@router.get("/standalone-estimates/new")
def standalone_estimate_new_redirect(request: Request):
    _require_auth(request)
    actor = _username(request)
    estimate = service.create_estimate(
        estimate_number="",
        title=None,
        estimate_type=EstimateType.PRIMARY,
        origin_channel=OriginChannel.WEB,
        project_id=None,
        counterparty_id=None,
        parent_estimate_id=None,
        root_estimate_id=None,
        customer_name=None,
        object_name=None,
        company_name="ООО Декорартстрой",
        contract_label=None,
        discount=Decimal("0"),
        watermark=None,
        created_by=actor,
        updated_by=actor,
    )
    return RedirectResponse(url=f"/estimates/{estimate.id}/edit", status_code=status.HTTP_302_FOUND)


@router.get("/estimates/new")
def standalone_estimate_new(request: Request):
    _require_auth(request)
    return JSONResponse(
        {
            "estimate": {
                "estimate_number": "",
                "title": "",
                "estimate_type": EstimateType.PRIMARY.value,
                "origin_channel": OriginChannel.WEB.value,
                "project_id": None,
                "counterparty_id": None,
                "parent_estimate_id": None,
                "customer_name": "",
                "object_name": "",
                "company_name": "ООО Декорартстрой",
                "contract_label": "",
                "discount": "0",
                "watermark": None,
            },
            "items": [],
        }
    )


@router.post("/estimates")
async def standalone_estimate_create(request: Request):
    _require_auth(request)
    payload = await _load_payload(request)
    actor = _username(request)
    items = _normalize_items(payload.get("items") or [])
    estimate = service.create_estimate(
        estimate_number=str(payload.get("estimate_number") or "").strip(),
        title=str(payload.get("title") or "").strip() or None,
        estimate_type=_parse_estimate_type(payload.get("estimate_type")),
        origin_channel=_parse_origin_channel(payload.get("origin_channel")),
        project_id=payload.get("project_id"),
        counterparty_id=payload.get("counterparty_id"),
        parent_estimate_id=payload.get("parent_estimate_id"),
        root_estimate_id=payload.get("root_estimate_id"),
        customer_name=str(payload.get("customer_name") or "").strip() or None,
        object_name=str(payload.get("object_name") or "").strip() or None,
        company_name=str(payload.get("company_name") or "").strip() or None,
        contract_label=str(payload.get("contract_label") or "").strip() or None,
        discount=payload.get("discount", Decimal("0")),
        watermark=payload.get("watermark"),
        created_by=actor,
        updated_by=actor,
    )
    if items:
        service.save_estimate_items(estimate.id, items)
    version = _create_snapshot_version(
        estimate.id,
        actor=actor,
        status_value=EstimateStatus.DRAFT,
        source_event="create_estimate",
    )
    export_standalone_estimate_json(_json_safe(service.build_estimate_snapshot(estimate.id)))
    details = service.get_estimate(estimate.id)
    return JSONResponse(
        {
            **_serialize_details(details),
            "created_version_id": version["id"],
            "download_urls": {
                "json": f"/estimates/{estimate.id}/download/json",
                "pdf": f"/estimates/{estimate.id}/download/pdf",
            },
        },
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/estimates/{estimate_id}/edit")
def standalone_estimate_editor(estimate_id: int, request: Request):
    _require_auth(request)
    details = service.get_estimate(estimate_id)
    price_library = _json_safe(
        {item["name"]: {"unit": item.get("unit"), "price": item.get("price")} 
         for item in details.items}
    )
    return templates.TemplateResponse(
        "standalone_estimate_editor.html",
        {
            "request": request,
            "estimate": details.estimate,
            "items": details.items,
            "price_library_json": json.dumps(_json_safe(details.items) or [], ensure_ascii=False),
            "estimate_calc_state_json": json.dumps({}, ensure_ascii=False),
            "username": _username(request),
        },
    )


@router.get("/estimates/{estimate_id}")
def standalone_estimate_get(estimate_id: int, request: Request):
    _require_auth(request)
    details = service.get_estimate(estimate_id)
    return JSONResponse(_serialize_details(details))


@router.post("/estimates/{estimate_id}")
async def standalone_estimate_update(estimate_id: int, request: Request):
    _require_auth(request)
    payload = await _load_payload(request)
    actor = _username(request)
    current = service.get_estimate(estimate_id).estimate
    service.update_estimate(
        estimate_id,
        title=str(payload.get("title") or current.title or "").strip() or None,
        counterparty_id=payload.get("counterparty_id", current.counterparty_id),
        customer_name=str(payload.get("customer_name") or current.customer_name or "").strip() or None,
        object_name=str(payload.get("object_name") or current.object_name or "").strip() or None,
        company_name=str(payload.get("company_name") or current.company_name or "").strip() or None,
        contract_label=str(payload.get("contract_label") or current.contract_label or "").strip() or None,
        discount=payload.get("discount", str(current.discount)),
        watermark=payload.get("watermark", current.watermark),
        updated_by=actor,
    )
    if "items" in payload:
        service.save_estimate_items(estimate_id, _normalize_items(payload.get("items") or []))
    refreshed = service.get_estimate(estimate_id)
    version = _create_snapshot_version(
        estimate_id,
        actor=actor,
        status_value=refreshed.estimate.status,
        source_event="update_estimate",
    )
    export_standalone_estimate_json(_json_safe(service.build_estimate_snapshot(estimate_id)))
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        return RedirectResponse(url=f"/estimates/{estimate_id}/edit", status_code=status.HTTP_303_SEE_OTHER)
    return JSONResponse({**_serialize_details(service.get_estimate(estimate_id)), "updated_version_id": version["id"]})


@router.post("/estimates/{estimate_id}/status")
async def standalone_estimate_change_status(estimate_id: int, request: Request):
    _require_auth(request)
    payload = await _load_payload(request)
    new_status = _parse_status(payload.get("status"))
    summary = service.change_estimate_status(
        estimate_id,
        new_status,
        changed_by=_username(request),
        comment=str(payload.get("comment") or "").strip() or None,
        approved_version_id=payload.get("approved_version_id"),
    )
    return JSONResponse({"estimate": _serialize_summary(summary)})


@router.post("/estimates/{estimate_id}/send")
def standalone_estimate_send(estimate_id: int, request: Request):
    _require_auth(request)
    actor = _username(request)
    version = _create_snapshot_version(
        estimate_id,
        actor=actor,
        status_value=EstimateStatus.SENT,
        source_event="send_estimate",
    )
    summary = service.change_estimate_status(
        estimate_id,
        EstimateStatus.SENT,
        changed_by=actor,
        comment="Отправлено клиенту",
    )
    export_standalone_estimate_json(_json_safe(service.build_estimate_snapshot(estimate_id)))
    return JSONResponse({"estimate": _serialize_summary(summary), "version_id": version["id"]})


@router.post("/estimates/{estimate_id}/approve")
async def standalone_estimate_approve(estimate_id: int, request: Request):
    _require_auth(request)
    payload = await _load_payload(request)
    actor = _username(request)
    stamp_applied = bool(payload.get("stamp_applied"))
    signature_applied = bool(payload.get("signature_applied"))
    version = _create_snapshot_version(
        estimate_id,
        actor=actor,
        status_value=EstimateStatus.APPROVED,
        source_event="approve_estimate",
        is_final=bool(payload.get("is_final", True)),
        stamp_applied=stamp_applied,
        signature_applied=signature_applied,
        change_comment=str(payload.get("comment") or "").strip() or None,
    )
    summary = service.change_estimate_status(
        estimate_id,
        EstimateStatus.APPROVED,
        changed_by=actor,
        comment=str(payload.get("comment") or "").strip() or "Согласовано",
        approved_version_id=version["id"],
    )
    export_standalone_estimate_json(_json_safe(service.build_estimate_snapshot(estimate_id)))
    return JSONResponse({"estimate": _serialize_summary(summary), "version_id": version["id"]})


@router.post("/estimates/{estimate_id}/reject")
async def standalone_estimate_reject(estimate_id: int, request: Request):
    _require_auth(request)
    payload = await _load_payload(request)
    summary = service.change_estimate_status(
        estimate_id,
        EstimateStatus.REJECTED,
        changed_by=_username(request),
        comment=str(payload.get("comment") or "").strip() or "Отклонено",
    )
    export_standalone_estimate_json(_json_safe(service.build_estimate_snapshot(estimate_id)))
    return JSONResponse({"estimate": _serialize_summary(summary)})


@router.post("/estimates/{estimate_id}/pdf")
async def standalone_estimate_pdf(estimate_id: int, request: Request):
    _require_auth(request)
    payload = await _load_payload(request)
    details = service.get_estimate(estimate_id)
    stamp_applied = bool(payload.get("stamp_applied"))
    signature_applied = bool(payload.get("signature_applied"))
    if (stamp_applied or signature_applied) and details.estimate.status is not EstimateStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Печать и подпись допустимы только для согласованной standalone-сметы.",
        )
    pdf_path = export_standalone_estimate_pdf(
        _json_safe(service.build_estimate_snapshot(estimate_id)),
        stamp_applied=stamp_applied,
        signature_applied=signature_applied,
    )
    return JSONResponse(
        {
            "estimate_id": estimate_id,
            "pdf_generated": True,
            "download_url": f"/estimates/{estimate_id}/download/pdf",
            "filename": pdf_path.name,
        }
    )


@router.get("/estimates/{estimate_id}/download/json")
def standalone_estimate_download_json(estimate_id: int, request: Request):
    _require_auth(request)
    snapshot = _json_safe(service.build_estimate_snapshot(estimate_id))
    path = export_standalone_estimate_json(snapshot)
    return FileResponse(path=path, filename=path.name, media_type="application/json")


@router.get("/estimates/{estimate_id}/download/pdf")
def standalone_estimate_download_pdf(estimate_id: int, request: Request):
    _require_auth(request)
    details = service.get_estimate(estimate_id)
    snapshot = _json_safe(service.build_estimate_snapshot(estimate_id))
    path = export_standalone_estimate_pdf(
        snapshot,
        stamp_applied=False,
        signature_applied=False,
    )
    if not Path(path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF-файл не найден.")
    media_type = "application/pdf"
    filename = path.name
    if details.estimate.status is EstimateStatus.APPROVED:
        filename = path.name
    return FileResponse(path=path, filename=filename, media_type=media_type)


@router.get("/standalone-estimates")
def standalone_estimates_list(request: Request):
    _require_auth(request)
    estimates = service.list_estimates()
    return templates.TemplateResponse(
        "standalone_estimates_list.html",
        {
            "request": request,
            "estimates": estimates,
            "username": _username(request),
        },
    )


def register_standalone_estimate_exception_handlers(app) -> None:
    @app.exception_handler(EstimateRepositoryError)
    async def _repository_error_handler(request: Request, exc: EstimateRepositoryError):
        accept = request.headers.get("accept", "").lower()
        if "text/html" in accept:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": str(exc), "status_code": 404},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_404_NOT_FOUND)

    @app.exception_handler(EstimateDomainError)
    async def _domain_error_handler(request: Request, exc: EstimateDomainError):
        accept = request.headers.get("accept", "").lower()
        if "text/html" in accept:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": str(exc), "status_code": 400},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_400_BAD_REQUEST)
