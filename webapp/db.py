import json
from contextlib import contextmanager
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

from webapp.config import get_settings
from webapp.storage import (
    build_estimate_draft_path,
    resolve_storage_path,
    storage_relative_path,
)


SMETA_DOC_TYPE = "Смета (приложение № 1)"
DEFAULT_PROJECT_STATUS = "Черновик"
DEFAULT_DOCUMENT_STATUS = "Черновик"
DEFAULT_COMPANY_NAME = "ООО Декорартстрой"


@contextmanager
def get_connection():
    settings = get_settings()
    conn = psycopg.connect(settings.postgres_dsn, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_json_loads(raw_value):
    if not raw_value:
        return None
    try:
        return json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return None


def parse_contract_label(raw_value: str) -> tuple[str, str]:
    text = str(raw_value or "").strip()
    if not text:
        return "", ""
    normalized = text.replace("№", "").strip()
    number = normalized
    date_value = ""
    if " от " in normalized:
        number, date_value = normalized.split(" от ", 1)
    return number.strip(), date_value.strip()


def parse_tree_number(value) -> float:
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def format_tree_number(value, decimals: int = 2) -> str:
    number = round(float(value or 0), decimals)
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.{decimals}f}".rstrip("0").rstrip(".")


def _normalize_editor_row(row: dict, discount_value: float) -> dict:
    row_type = "section" if str(row.get("row_type") or "").strip() == "section" else "item"
    name = str(row.get("name") or "").strip()
    unit = str(row.get("unit") or "").strip()
    quantity_value = parse_tree_number(row.get("quantity"))
    price_value = parse_tree_number(row.get("price"))
    total_value = quantity_value * price_value
    discounted_total_value = total_value * max(0.0, 1.0 - (discount_value / 100.0))
    reference = str(row.get("reference") or "").strip()

    if row_type == "section":
        return {
            "row_type": "section",
            "name": name or "Новый раздел",
            "unit": "",
            "quantity": "",
            "price": "",
            "total": "",
            "discounted_total": "",
            "reference": "",
        }

    return {
        "row_type": "item",
        "name": name,
        "unit": unit,
        "quantity": format_tree_number(quantity_value) if quantity_value else "",
        "price": format_tree_number(price_value) if price_value else "",
        "total": format_tree_number(total_value) if total_value else "",
        "discounted_total": format_tree_number(discounted_total_value) if discounted_total_value else "",
        "reference": reference,
    }


def _normalize_editor_rows(rows: list[dict], discount_value: float) -> list[dict]:
    normalized = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        normalized_row = _normalize_editor_row(row, discount_value)
        if normalized_row["row_type"] == "section" and not normalized_row["name"]:
            continue
        if normalized_row["row_type"] == "item" and not normalized_row["name"]:
            continue
        normalized.append(normalized_row)
    return normalized


def _payload_item_to_editor_row(item: dict, discount_value: float) -> dict:
    tags = set(item.get("tags") or [])
    values = list(item.get("values") or [])
    if "room" in tags:
        return {
            "row_type": "section",
            "name": str(values[0] if len(values) > 0 else "").strip() or "Раздел",
            "unit": "",
            "quantity": "",
            "price": "",
            "total": "",
            "discounted_total": "",
            "reference": "",
        }

    quantity_value = parse_tree_number(values[2] if len(values) > 2 else "")
    price_value = parse_tree_number(values[3] if len(values) > 3 else "")
    total_value = parse_tree_number(values[4] if len(values) > 4 else "")
    discounted_total_value = parse_tree_number(values[5] if len(values) > 5 else "")
    if total_value == 0 and quantity_value and price_value:
        total_value = quantity_value * price_value
    if discounted_total_value == 0 and total_value:
        discounted_total_value = total_value * max(0.0, 1.0 - (discount_value / 100.0))

    return {
        "row_type": "item",
        "name": str(values[0] if len(values) > 0 else "").strip(),
        "unit": str(values[1] if len(values) > 1 else "").strip(),
        "quantity": format_tree_number(quantity_value) if quantity_value else "",
        "price": format_tree_number(price_value) if price_value else "",
        "total": format_tree_number(total_value) if total_value else "",
        "discounted_total": format_tree_number(discounted_total_value) if discounted_total_value else "",
        "reference": str(values[6] if len(values) > 6 else "").strip(),
    }


def _editor_row_to_payload_item(row: dict) -> dict:
    if row["row_type"] == "section":
        return {
            "values": [row["name"], "", "", "", "", "", ""],
            "tags": ["room"],
        }

    return {
        "values": [
            row["name"],
            row["unit"],
            row["quantity"],
            row["price"],
            row["total"],
            row["discounted_total"],
            row["reference"],
        ],
        "tags": [],
    }


def _compute_estimate_stats(rows: list[dict]) -> dict:
    section_count = sum(1 for row in rows if row["row_type"] == "section")
    item_count = sum(1 for row in rows if row["row_type"] == "item")
    total_sum = 0.0
    discounted_sum = 0.0
    for row in rows:
        if row["row_type"] != "item":
            continue
        total_sum += parse_tree_number(row.get("total"))
        discounted_sum += parse_tree_number(row.get("discounted_total"))
    return {
        "section_count": section_count,
        "item_count": item_count,
        "total_sum": total_sum,
        "discounted_sum": discounted_sum,
    }


def _fetch_latest_smeta_draft(cur, project_id: int) -> dict | None:
    cur.execute(
        """
        SELECT id, username, data, updated_at, created_by, created_at, updated_by
        FROM smeta_drafts
        ORDER BY updated_at DESC, id DESC
        """
    )
    for row in cur.fetchall():
        payload = _safe_json_loads(row.get("data"))
        if not isinstance(payload, dict):
            continue
        if payload.get("project_id") != project_id:
            continue
        return {"row": row, "payload": payload}
    return None


def _fetch_estimate_document(cur, project_id: int) -> dict | None:
    cur.execute(
        """
        SELECT
            id,
            project_id,
            COALESCE(doc_type, '') AS doc_type,
            COALESCE(title, '') AS title,
            COALESCE(status, %s) AS status,
            COALESCE(file_path, '') AS file_path,
            COALESCE(draft_path, '') AS draft_path,
            COALESCE(pdf_path, '') AS pdf_path,
            COALESCE(version, 1) AS version,
            COALESCE(created_at, '') AS created_at,
            COALESCE(updated_at, '') AS updated_at
        FROM documents
        WHERE project_id = %s AND doc_type = %s
        ORDER BY COALESCE(updated_at, created_at, '') DESC, id DESC
        LIMIT 1
        """,
        (DEFAULT_DOCUMENT_STATUS, project_id, SMETA_DOC_TYPE),
    )
    return cur.fetchone()


def _load_payload_from_document(document: dict | None) -> dict | None:
    if not document:
        return None
    absolute_path = resolve_storage_path(document.get("draft_path") or "")
    if not absolute_path:
        return None
    try:
        return json.loads(absolute_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _build_default_estimate_payload(project: dict | None) -> dict:
    project = project or {}
    object_name = str(project.get("address") or project.get("project_name") or "").strip()
    contract_value = str(project.get("contract") or "").strip()
    contract_date = str(project.get("contract_date") or "").strip()
    if contract_value and contract_date and " от " not in contract_value:
        contract_value = f"{contract_value} от {contract_date}"

    return {
        "project_id": project.get("id"),
        "company": DEFAULT_COMPANY_NAME,
        "contract": contract_value,
        "customer": str(project.get("customer") or "").strip(),
        "object": object_name,
        "discount": "",
        "watermark": True,
        "calc_state": {},
        "items": [],
        "draft_user": "",
        "saved_at": "",
    }


def fetch_projects():
    query = """
        SELECT
            p.id,
            COALESCE(NULLIF(p.project_name, ''), NULLIF(p.address, ''), 'Без названия') AS project_name,
            COALESCE(p.address, '') AS address,
            COALESCE(cp.company_name, cp.full_name, cp.name, '') AS counterparty_name,
            COALESCE(NULLIF(p.status, ''), %s) AS status,
            COALESCE(p.contract, '') AS contract,
            COALESCE(p.date, '') AS contract_date,
            COALESCE(p.updated_at, p.created_at, '') AS updated_at
        FROM projects p
        LEFT JOIN counterparties cp ON cp.id = p.counterparty_id
        ORDER BY COALESCE(p.updated_at, p.created_at, '') DESC, p.id DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (DEFAULT_PROJECT_STATUS,))
            return cur.fetchall()


def fetch_dashboard_counts():
    query = """
        SELECT
            (SELECT COUNT(*) FROM projects) AS projects_total,
            (SELECT COUNT(*) FROM counterparties) AS counterparties_total,
            (SELECT COUNT(*) FROM documents) AS documents_total,
            (SELECT COUNT(*)
             FROM projects
             WHERE COALESCE(NULLIF(status, ''), %s) = 'В работе') AS active_projects_total
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (DEFAULT_PROJECT_STATUS,))
            return cur.fetchone()


def fetch_project(project_id: int):
    query = """
        SELECT
            p.id,
            COALESCE(NULLIF(p.project_name, ''), NULLIF(p.address, ''), 'Без названия') AS project_name,
            COALESCE(p.address, '') AS address,
            COALESCE(p.customer, '') AS customer,
            COALESCE(p.contract, '') AS contract,
            COALESCE(p.date, '') AS contract_date,
            COALESCE(NULLIF(p.status, ''), %s) AS status,
            COALESCE(p.notes, '') AS notes,
            COALESCE(p.created_at, '') AS created_at,
            COALESCE(p.updated_at, '') AS updated_at,
            COALESCE(cp.company_name, cp.full_name, cp.name, '') AS counterparty_name,
            COALESCE(cp.phone, '') AS counterparty_phone,
            COALESCE(cp.email, '') AS counterparty_email,
            COALESCE(cp.type, '') AS counterparty_type
        FROM projects p
        LEFT JOIN counterparties cp ON cp.id = p.counterparty_id
        WHERE p.id = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (DEFAULT_PROJECT_STATUS, project_id))
            return cur.fetchone()


def fetch_project_documents(project_id: int):
    query = """
        SELECT
            id,
            project_id,
            COALESCE(doc_type, '') AS doc_type,
            COALESCE(title, '') AS title,
            COALESCE(status, %s) AS status,
            COALESCE(file_path, '') AS file_path,
            COALESCE(draft_path, '') AS draft_path,
            COALESCE(pdf_path, '') AS pdf_path,
            COALESCE(version, 1) AS version,
            COALESCE(updated_at, created_at, '') AS updated_at,
            COALESCE(created_at, '') AS created_at
        FROM documents
        WHERE project_id = %s
        ORDER BY COALESCE(updated_at, created_at, '') DESC, id DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (DEFAULT_DOCUMENT_STATUS, project_id))
            return cur.fetchall()


def fetch_project_events(project_id: int):
    query = """
        SELECT
            id,
            COALESCE(event_type, '') AS event_type,
            COALESCE(event_text, '') AS event_text,
            COALESCE(author, '') AS author,
            COALESCE(created_at, '') AS created_at
        FROM project_events
        WHERE project_id = %s
        ORDER BY COALESCE(created_at, '') DESC, id DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (project_id,))
            return cur.fetchall()


def fetch_document(document_id: int):
    query = """
        SELECT
            id,
            project_id,
            COALESCE(doc_type, '') AS doc_type,
            COALESCE(title, '') AS title,
            COALESCE(status, %s) AS status,
            COALESCE(file_path, '') AS file_path,
            COALESCE(draft_path, '') AS draft_path,
            COALESCE(pdf_path, '') AS pdf_path
        FROM documents
        WHERE id = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (DEFAULT_DOCUMENT_STATUS, document_id))
            return cur.fetchone()


def fetch_project_estimate(project_id: int):
    project = fetch_project(project_id)
    if not project:
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            estimate_document = _fetch_estimate_document(cur, project_id)
            latest_draft = _fetch_latest_smeta_draft(cur, project_id)

    payload = None
    draft_record_id = None
    draft_meta = None
    if latest_draft:
        payload = latest_draft["payload"]
        draft_record_id = latest_draft["row"]["id"]
        draft_meta = latest_draft["row"]
    if not payload:
        payload = _load_payload_from_document(estimate_document)
    if not payload:
        payload = _build_default_estimate_payload(project)

    discount_value = parse_tree_number(payload.get("discount"))
    editor_rows = _normalize_editor_rows(
        [_payload_item_to_editor_row(item, discount_value) for item in payload.get("items", [])],
        discount_value,
    )
    stats = _compute_estimate_stats(editor_rows)

    saved_at = str(payload.get("saved_at") or "").strip()
    if not saved_at and draft_meta:
        saved_at = str(draft_meta.get("updated_at") or "").strip()
    if not saved_at and estimate_document:
        saved_at = str(estimate_document.get("updated_at") or "").strip()

    return {
        "project": project,
        "payload": payload,
        "document": estimate_document,
        "draft_record_id": draft_record_id,
        "company": str(payload.get("company") or DEFAULT_COMPANY_NAME).strip() or DEFAULT_COMPANY_NAME,
        "object_name": str(payload.get("object") or project.get("address") or project.get("project_name") or "").strip(),
        "customer_name": str(payload.get("customer") or project.get("customer") or "").strip(),
        "contract_label": str(payload.get("contract") or "").strip(),
        "discount": format_tree_number(discount_value) if discount_value else "",
        "watermark": bool(payload.get("watermark", True)),
        "saved_at": saved_at,
        "editor_rows": editor_rows,
        "editor_rows_json": json.dumps(editor_rows, ensure_ascii=False),
        "section_count": stats["section_count"],
        "item_count": stats["item_count"],
        "total_sum": format_tree_number(stats["total_sum"]) if stats["total_sum"] else "0",
        "discounted_sum": format_tree_number(stats["discounted_sum"]) if stats["discounted_sum"] else "0",
        "draft_path": estimate_document.get("draft_path") if estimate_document else "",
        "pdf_path": estimate_document.get("pdf_path") if estimate_document else "",
        "has_draft_file": bool(resolve_storage_path((estimate_document or {}).get("draft_path") or "")),
        "has_pdf_file": bool(resolve_storage_path((estimate_document or {}).get("pdf_path") or "")),
    }


def save_project_estimate(
    project_id: int,
    username: str,
    company_name: str,
    object_name: str,
    customer_name: str,
    contract_label: str,
    discount_raw: str,
    watermark: bool,
    editor_rows: list[dict],
):
    project = fetch_project(project_id)
    if not project:
        return None

    estimate = fetch_project_estimate(project_id) or {}
    discount_value = parse_tree_number(discount_raw)
    normalized_rows = _normalize_editor_rows(editor_rows, discount_value)
    stats = _compute_estimate_stats(normalized_rows)
    now = _now_iso()

    payload = dict(_build_default_estimate_payload(project) | (estimate.get("payload") or {}))
    payload.update(
        {
            "project_id": project_id,
            "company": company_name or DEFAULT_COMPANY_NAME,
            "contract": contract_label,
            "customer": customer_name,
            "object": object_name,
            "discount": format_tree_number(discount_value) if discount_value else "",
            "watermark": bool(watermark),
            "calc_state": {
                "section_count": stats["section_count"],
                "item_count": stats["item_count"],
                "total_sum": format_tree_number(stats["total_sum"]),
                "discounted_sum": format_tree_number(stats["discounted_sum"]),
            },
            "items": [_editor_row_to_payload_item(row) for row in normalized_rows],
            "draft_user": username,
            "saved_at": now,
        }
    )

    absolute_draft_path, relative_draft_path = build_estimate_draft_path(
        project_id,
        project.get("project_name") or "",
        object_name,
    )
    absolute_draft_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    contract_number, contract_date = parse_contract_label(contract_label)

    with get_connection() as conn:
        with conn.cursor() as cur:
            latest_draft = _fetch_latest_smeta_draft(cur, project_id)
            estimate_document = _fetch_estimate_document(cur, project_id)

            if latest_draft:
                cur.execute(
                    """
                    UPDATE smeta_drafts
                    SET username = %s, data = %s, updated_at = %s, updated_by = %s
                    WHERE id = %s
                    """,
                    (
                        username,
                        json.dumps(payload, ensure_ascii=False),
                        now,
                        username,
                        latest_draft["row"]["id"],
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO smeta_drafts
                    (username, data, updated_at, created_by, created_at, updated_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        username,
                        json.dumps(payload, ensure_ascii=False),
                        now,
                        username,
                        now,
                        username,
                    ),
                )

            pdf_relative_path = ""
            if estimate_document and estimate_document.get("pdf_path"):
                pdf_absolute = resolve_storage_path(estimate_document["pdf_path"])
                pdf_relative_path = storage_relative_path(pdf_absolute) if pdf_absolute else estimate_document["pdf_path"]

            document_title = f"Смета - {object_name}" if object_name else "Смета"
            primary_file_path = pdf_relative_path or relative_draft_path

            if estimate_document:
                cur.execute(
                    """
                    UPDATE documents
                    SET
                        title = %s,
                        status = %s,
                        file_path = %s,
                        draft_path = %s,
                        pdf_path = %s,
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        document_title,
                        DEFAULT_DOCUMENT_STATUS,
                        primary_file_path,
                        relative_draft_path,
                        pdf_relative_path,
                        now,
                        estimate_document["id"],
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO documents
                    (project_id, doc_type, title, status, file_path, draft_path, pdf_path, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        project_id,
                        SMETA_DOC_TYPE,
                        document_title,
                        DEFAULT_DOCUMENT_STATUS,
                        primary_file_path,
                        relative_draft_path,
                        pdf_relative_path,
                        now,
                        now,
                    ),
                )

            cur.execute(
                """
                UPDATE projects
                SET project_name = %s, address = %s, customer = %s, contract = %s, date = %s, updated_at = %s
                WHERE id = %s
                """,
                (
                    object_name or project.get("project_name") or project.get("address") or "",
                    object_name or project.get("address") or project.get("project_name") or "",
                    customer_name,
                    contract_label or contract_number,
                    contract_date,
                    now,
                    project_id,
                ),
            )

            cur.execute(
                """
                INSERT INTO project_events (project_id, event_type, event_text, author, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    "document",
                    "Обновлен черновик сметы из web-редактора",
                    username,
                    now,
                ),
            )

        conn.commit()

    return fetch_project_estimate(project_id)
