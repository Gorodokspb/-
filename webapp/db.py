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


def _counterparty_display_name(row: dict | None) -> str:
    if not row:
        return ""
    return str(
        row.get("company_name")
        or row.get("full_name")
        or row.get("name")
        or ""
    ).strip()


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


def _looks_like_broken_compat_payload(values: list) -> bool:
    joined = " ".join(str(value or "").strip() for value in values if value not in (None, ""))
    if not joined:
        return False
    normalized = joined.lower()
    suspicious_tokens = (
        "compatrow(",
        "'name':",
        '"name":',
        "'values':",
        '"values":',
        "'tags':",
        '"tags":',
        "'row_type':",
        '"row_type":',
    )
    if any(token in normalized for token in suspicious_tokens):
        return True
    name = str(values[0] if len(values) > 0 else "").strip()
    unit = str(values[1] if len(values) > 1 else "").strip()
    reference = str(values[6] if len(values) > 6 else "").strip()
    if reference.startswith("CompatRow("):
        return True
    if unit in {"'name':", '"name":'}:
        return True
    if name and all(char in "0123456789.,- " for char in name) and (unit or reference):
        return True
    return False


def _sanitize_payload_values(values: list[str]) -> list[str]:
    normalized = [str(value or "").strip() for value in values]
    if _looks_like_broken_compat_payload(normalized):
        return [""] * 7
    return normalized


def _normalize_price_library_entries(rows: list[dict]) -> list[dict]:
    entries_by_key = {}
    for row in rows or []:
        name = str((row or {}).get("name") or "").strip()
        if not name:
            continue
        key = name.casefold()
        if key in entries_by_key:
            continue
        entries_by_key[key] = {
            "name": name,
            "unit": str((row or {}).get("unit") or "").strip(),
            "price": format_tree_number((row or {}).get("price")) if (row or {}).get("price") not in (None, "") else "",
        }
    return sorted(entries_by_key.values(), key=lambda item: item["name"].casefold())


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
    values = _sanitize_payload_values(list(item.get("values") or []))
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


def _format_rubles(value: float) -> str:
    return f"{round(value):,} ₽".replace(",", " ")


def _parse_dashboard_date(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    value = str(raw_value).strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def fetch_dashboard_finance(projects: list[dict] | None = None) -> dict:
    """Build the projects-dashboard finance strip from saved estimate totals.

    The CRM does not yet have a separate payments/costs module, so this summary
    is deliberately tied to real estimate drafts/documents: work done and debt
    use saved estimate totals, while profit remains zero until expenses/payments
    are implemented.
    """
    projects = projects if projects is not None else fetch_projects()
    now = datetime.now()
    today_total = 0.0
    month_total = 0.0
    all_estimates_total = 0.0
    latest_update: datetime | None = None

    for project in projects or []:
        try:
            estimate = fetch_project_estimate(int(project.get("id")))
        except (TypeError, ValueError):
            continue
        if not estimate:
            continue
        estimate_total = parse_tree_number(estimate.get("discounted_sum") or estimate.get("total_sum"))
        all_estimates_total += estimate_total
        saved_at = _parse_dashboard_date(estimate.get("saved_at") or project.get("updated_at"))
        if saved_at:
            latest_update = max(latest_update, saved_at) if latest_update else saved_at
            if saved_at.date() == now.date():
                today_total += estimate_total
            if saved_at.year == now.year and saved_at.month == now.month:
                month_total += estimate_total

    last_updated = latest_update.strftime("%Y-%m-%d в %H:%M") if latest_update else "нет сохранённых смет"
    return {
        "today": {
            "work_done": _format_rubles(today_total),
            "profit": _format_rubles(0),
            "last_updated": last_updated,
        },
        "month": {
            "work_done": _format_rubles(month_total),
            "profit": _format_rubles(0),
            "profit_percent": "0 %",
            "last_updated": last_updated,
        },
        "customer_debt": _format_rubles(all_estimates_total),
        "debt_project": (projects or [{}])[0].get("project_name", "Объекты") if projects else "Объекты",
        "last_updated": last_updated,
    }


def fetch_counterparties():
    query = """
        SELECT
            id,
            COALESCE(type, '') AS type,
            COALESCE(name, '') AS name,
            COALESCE(full_name, '') AS full_name,
            COALESCE(company_name, '') AS company_name,
            COALESCE(phone, '') AS phone,
            COALESCE(email, '') AS email,
            COALESCE(inn, '') AS inn,
            COALESCE(notes, '') AS notes,
            COALESCE(created_at, '') AS created_at
        FROM counterparties
        ORDER BY
            COALESCE(NULLIF(company_name, ''), NULLIF(full_name, ''), NULLIF(name, ''), '') ASC,
            id DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    for row in rows:
        row["display_name"] = _counterparty_display_name(row) or "Без названия"
    return rows


def fetch_price_library(limit: int = 200) -> list[dict]:
    query = """
        SELECT
            COALESCE(name, '') AS name,
            COALESCE(unit, '') AS unit,
            price
        FROM prices
        WHERE COALESCE(name, '') <> ''
        ORDER BY LOWER(TRIM(name)) ASC, id ASC
        LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (max(1, int(limit)),))
            rows = cur.fetchall()
    return _normalize_price_library_entries(rows)


def fetch_project(project_id: int):
    query = """
        SELECT
            p.id,
            COALESCE(NULLIF(p.project_name, ''), NULLIF(p.address, ''), 'Без названия') AS project_name,
            COALESCE(p.address, '') AS address,
            COALESCE(p.customer, '') AS customer,
            COALESCE(p.contract, '') AS contract,
            COALESCE(p.date, '') AS contract_date,
            p.counterparty_id,
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


def update_project_card(
    project_id: int,
    username: str,
    *,
    project_name: str,
    address: str,
    customer: str,
    counterparty_id: int | None,
    status: str,
    contract: str,
    contract_date: str,
    notes: str,
):
    project = fetch_project(project_id)
    if not project:
        return None

    now = _now_iso()
    normalized_project_name = str(project_name or "").strip()
    normalized_address = str(address or "").strip()
    normalized_customer = str(customer or "").strip()
    normalized_status = str(status or "").strip() or DEFAULT_PROJECT_STATUS
    normalized_contract = str(contract or "").strip()
    normalized_contract_date = str(contract_date or "").strip()
    normalized_notes = str(notes or "").strip()
    normalized_counterparty_id = int(counterparty_id) if counterparty_id else None

    if not normalized_project_name:
        normalized_project_name = normalized_address or project.get("project_name") or "Без названия"
    if not normalized_address:
        normalized_address = normalized_project_name

    counterparty_row = None
    if normalized_counterparty_id:
        for row in fetch_counterparties():
            if int(row["id"]) == normalized_counterparty_id:
                counterparty_row = row
                break
    linked_counterparty_name = _counterparty_display_name(counterparty_row)
    if linked_counterparty_name and not normalized_customer:
        normalized_customer = linked_counterparty_name

    changes = []
    comparisons = [
        ("Название", project.get("project_name") or "", normalized_project_name),
        ("Адрес", project.get("address") or "", normalized_address),
        ("Заказчик", project.get("customer") or "", normalized_customer),
        ("Контрагент", str(project.get("counterparty_id") or ""), str(normalized_counterparty_id or "")),
        ("Статус", project.get("status") or "", normalized_status),
        ("Договор", project.get("contract") or "", normalized_contract),
        ("Дата договора", project.get("contract_date") or "", normalized_contract_date),
        ("Заметки", project.get("notes") or "", normalized_notes),
    ]
    for label, old_value, new_value in comparisons:
        if str(old_value).strip() != str(new_value).strip():
            changes.append(label)

    event_text = (
        "Обновлена карточка проекта через web-интерфейс"
        if not changes
        else f"Обновлена карточка проекта через web-интерфейс: {', '.join(changes)}"
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE projects
                SET
                    project_name = %s,
                    address = %s,
                    customer = %s,
                    counterparty_id = %s,
                    status = %s,
                    contract = %s,
                    date = %s,
                    notes = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    normalized_project_name,
                    normalized_address,
                    normalized_customer,
                    normalized_counterparty_id,
                    normalized_status,
                    normalized_contract,
                    normalized_contract_date,
                    normalized_notes,
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
                    "project",
                    event_text,
                    username,
                    now,
                ),
            )
        conn.commit()

    return fetch_project(project_id)


def create_counterparty(
    username: str,
    *,
    counterparty_type: str,
    display_name: str,
    full_name: str,
    company_name: str,
    phone: str,
    email: str,
    inn: str,
    notes: str,
):
    normalized_type = str(counterparty_type or "").strip() or "Физлицо"
    normalized_display_name = str(display_name or "").strip()
    normalized_full_name = str(full_name or "").strip()
    normalized_company_name = str(company_name or "").strip()
    normalized_phone = str(phone or "").strip()
    normalized_email = str(email or "").strip()
    normalized_inn = str(inn or "").strip()
    normalized_notes = str(notes or "").strip()

    resolved_name = normalized_display_name or normalized_company_name or normalized_full_name
    if not resolved_name:
        raise ValueError("Укажите имя контрагента, ФИО или название компании.")

    if normalized_type in {"ООО", "ИП"} and not normalized_company_name:
        normalized_company_name = resolved_name
    if normalized_type == "Физлицо" and not normalized_full_name:
        normalized_full_name = resolved_name

    now = _now_iso()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO counterparties (
                    type, name, full_name, phone, email, inn, company_name, notes, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    normalized_type,
                    resolved_name,
                    normalized_full_name,
                    normalized_phone,
                    normalized_email,
                    normalized_inn,
                    normalized_company_name,
                    normalized_notes,
                    now,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return int(row["id"])


def create_project(
    username: str,
    *,
    project_name: str,
    address: str,
    counterparty_id: int | None,
    status: str,
    contract: str,
    contract_date: str,
    notes: str,
):
    normalized_project_name = str(project_name or "").strip()
    normalized_address = str(address or "").strip()
    normalized_status = str(status or "").strip() or DEFAULT_PROJECT_STATUS
    normalized_contract = str(contract or "").strip()
    normalized_contract_date = str(contract_date or "").strip()
    normalized_notes = str(notes or "").strip()
    normalized_counterparty_id = int(counterparty_id) if counterparty_id else None

    if not normalized_project_name and not normalized_address:
        raise ValueError("Укажите название проекта или адрес.")

    if not normalized_project_name:
        normalized_project_name = normalized_address
    if not normalized_address:
        normalized_address = normalized_project_name

    counterparty_name = ""
    if normalized_counterparty_id:
        for row in fetch_counterparties():
            if int(row["id"]) == normalized_counterparty_id:
                counterparty_name = _counterparty_display_name(row)
                break

    now = _now_iso()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO projects (
                    project_name, address, customer, contract, date, counterparty_id, status, notes, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    normalized_project_name,
                    normalized_address,
                    counterparty_name,
                    normalized_contract,
                    normalized_contract_date,
                    normalized_counterparty_id,
                    normalized_status,
                    normalized_notes,
                    now,
                    now,
                ),
            )
            row = cur.fetchone()
            project_id = int(row["id"])
            cur.execute(
                """
                INSERT INTO project_events (project_id, event_type, event_text, author, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    "project",
                    f"Создан проект: {normalized_project_name}",
                    username,
                    now,
                ),
            )
        conn.commit()
    return project_id


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
        "calc_state": payload.get("calc_state") if isinstance(payload.get("calc_state"), dict) else {},
        "calc_state_json": json.dumps(payload.get("calc_state") if isinstance(payload.get("calc_state"), dict) else {}, ensure_ascii=False),
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
    calc_state: dict | None = None,
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
            "calc_state": calc_state if isinstance(calc_state, dict) else (payload.get("calc_state") if isinstance(payload.get("calc_state"), dict) else {}),
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


def ensure_web_users_table() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS web_users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'admin',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    updated_by TEXT NOT NULL
                )
                """
            )
        conn.commit()


def fetch_web_user(username: str) -> dict | None:
    normalized_username = str(username or "").strip()
    if not normalized_username:
        return None

    ensure_web_users_table()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    username,
                    password_hash,
                    role,
                    created_at,
                    updated_at,
                    updated_by
                FROM web_users
                WHERE username = %s
                """,
                (normalized_username,),
            )
            return cur.fetchone()


def ensure_web_user(username: str, password_hash: str, updated_by: str) -> dict:
    normalized_username = str(username or "").strip()
    normalized_password_hash = str(password_hash or "").strip()
    normalized_updated_by = str(updated_by or normalized_username or "system").strip()
    if not normalized_username:
        raise ValueError("Username is required.")
    if not normalized_password_hash:
        raise ValueError("Password hash is required.")

    existing = fetch_web_user(normalized_username)
    if existing:
        return existing

    now = _now_iso()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO web_users (
                    username,
                    password_hash,
                    role,
                    created_at,
                    updated_at,
                    updated_by
                )
                VALUES (%s, %s, 'admin', %s, %s, %s)
                """,
                (
                    normalized_username,
                    normalized_password_hash,
                    now,
                    now,
                    normalized_updated_by,
                ),
            )
        conn.commit()
    return fetch_web_user(normalized_username)


def update_web_user_password(username: str, password_hash: str, updated_by: str) -> dict | None:
    normalized_username = str(username or "").strip()
    normalized_password_hash = str(password_hash or "").strip()
    normalized_updated_by = str(updated_by or normalized_username or "system").strip()
    if not normalized_username:
        raise ValueError("Username is required.")
    if not normalized_password_hash:
        raise ValueError("Password hash is required.")

    ensure_web_users_table()
    now = _now_iso()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE web_users
                SET
                    password_hash = %s,
                    updated_at = %s,
                    updated_by = %s
                WHERE username = %s
                """,
                (
                    normalized_password_hash,
                    now,
                    normalized_updated_by,
                    normalized_username,
                ),
            )
        conn.commit()
    return fetch_web_user(normalized_username)


# --- Finance transactions -----------------------------------------------------

FINANCE_CATEGORIES = ["Материалы", "Зарплата", "Аванс", "Налоги", "Оплата", "Прочее"]
TRANSACTION_TYPES = {"income", "expense"}
_TRANSACTIONS_TABLE_READY = False


def ensure_transactions_table() -> None:
    global _TRANSACTIONS_TABLE_READY
    if _TRANSACTIONS_TABLE_READY:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    type VARCHAR(20) NOT NULL,
                    amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
                    description TEXT,
                    date TIMESTAMP NOT NULL DEFAULT NOW(),
                    project_id INTEGER NULL REFERENCES projects(id) ON DELETE SET NULL,
                    category VARCHAR(100) NOT NULL DEFAULT 'Прочее',
                    status VARCHAR(30) NOT NULL DEFAULT 'completed'
                )
                """
            )
            cur.execute("ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(12, 2) USING amount::DECIMAL(12, 2)")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'completed'")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date DESC, id DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_project_id ON transactions(project_id)")
        conn.commit()
    _TRANSACTIONS_TABLE_READY = True


def _normalize_transaction_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in TRANSACTION_TYPES:
        raise ValueError("Тип транзакции должен быть income или expense.")
    return normalized


def _normalize_transaction_category(value: str) -> str:
    category = str(value or "").strip()
    return category or "Прочее"


def create_transaction(transaction_type: str, amount, description: str, category: str, project_id=None, tx_status: str = "completed") -> int:
    ensure_transactions_table()
    normalized_type = _normalize_transaction_type(transaction_type)
    amount_value = parse_tree_number(amount)
    if amount_value <= 0:
        raise ValueError("Сумма должна быть больше нуля.")
    normalized_project_id = int(project_id) if str(project_id or "").strip() else None
    normalized_status = str(tx_status or "completed").strip() or "completed"
    now = datetime.now()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (type, amount, description, category, project_id, status, date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    normalized_type,
                    amount_value,
                    str(description or "").strip(),
                    _normalize_transaction_category(category),
                    normalized_project_id,
                    normalized_status,
                    now,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return int(row["id"] if isinstance(row, dict) else row[0])


def fetch_transactions(project_id: int | None = None) -> list[dict]:
    ensure_transactions_table()
    where = ""
    params: tuple = ()
    if project_id is not None:
        where = "WHERE t.project_id = %s"
        params = (int(project_id),)
    query = f"""
        SELECT
            t.id,
            t.type,
            t.amount,
            COALESCE(t.description, '') AS description,
            t.date,
            t.project_id,
            COALESCE(t.category, 'Прочее') AS category,
            COALESCE(t.status, 'completed') AS status,
            COALESCE(NULLIF(p.project_name, ''), NULLIF(p.address, ''), '') AS project_name
        FROM transactions t
        LEFT JOIN projects p ON p.id = t.project_id
        {where}
        ORDER BY t.date DESC, t.id DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    for row in rows:
        row["amount_label"] = _format_rubles(parse_tree_number(row.get("amount")))
        row["type_label"] = "Доход" if row.get("type") == "income" else "Расход"
    return rows


def fetch_project_transactions(project_id: int) -> list[dict]:
    return fetch_transactions(project_id=int(project_id))


def summarize_transactions(transactions: list[dict]) -> dict:
    income = 0.0
    expense = 0.0
    for item in transactions or []:
        amount = parse_tree_number((item or {}).get("amount"))
        if (item or {}).get("type") == "income":
            income += amount
        elif (item or {}).get("type") == "expense":
            expense += amount
    balance = income - expense
    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "balance": round(balance, 2),
        "income_label": _format_rubles(income),
        "expense_label": _format_rubles(expense),
        "balance_label": _format_rubles(balance),
    }


# --- Catalog items management -------------------------------------------------

def ensure_catalog_items_table() -> None:
    from import_catalog_items import ensure_catalog_items_table as _ensure

    with get_connection() as conn:
        _ensure(conn)


def migrate_catalog_item_categories() -> int:
    from import_catalog_items import migrate_catalog_categories

    with get_connection() as conn:
        return migrate_catalog_categories(conn)


def fetch_catalog_items() -> list[dict]:
    ensure_catalog_items_table()
    query = """
        SELECT id, name, COALESCE(unit, '') AS unit, price, COALESCE(category, 'Прочее') AS category
        FROM catalog_items
        ORDER BY category ASC, LOWER(name) ASC, id ASC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()


def fetch_catalog_items_by_names(names: list[str]) -> list[dict]:
    ensure_catalog_items_table()
    if not names:
        return []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, COALESCE(unit, '') AS unit, price, COALESCE(category, 'Прочее') AS category
                FROM catalog_items
                WHERE name = ANY(%s)
                """,
                (names,),
            )
            return cur.fetchall()


def create_catalog_item(name: str, unit: str, price, category: str) -> int:
    from import_catalog_items import normalize_category, parse_price

    normalized_name = str(name or '').strip()
    if not normalized_name:
        raise ValueError('Название работы обязательно.')
    normalized_category = normalize_category(category, normalized_name)
    price_value = parse_price(price)
    ensure_catalog_items_table()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO catalog_items (name, unit, price, category)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (normalized_name, str(unit or '').strip(), price_value, normalized_category),
            )
            row = cur.fetchone()
        conn.commit()
    return int(row['id'] if isinstance(row, dict) else row[0])


def update_catalog_item(item_id: int, name: str, unit: str, price, category: str) -> None:
    from import_catalog_items import normalize_category, parse_price

    normalized_name = str(name or '').strip()
    if not normalized_name:
        raise ValueError('Название работы обязательно.')
    normalized_category = normalize_category(category, normalized_name)
    price_value = parse_price(price)
    ensure_catalog_items_table()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE catalog_items
                SET name = %s, unit = %s, price = %s, category = %s
                WHERE id = %s
                """,
                (normalized_name, str(unit or '').strip(), price_value, normalized_category, int(item_id)),
            )
        conn.commit()


def delete_catalog_item(item_id: int) -> None:
    ensure_catalog_items_table()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM catalog_items WHERE id = %s', (int(item_id),))
        conn.commit()


def duplicate_catalog_item(item_id: int) -> int:
    ensure_catalog_items_table()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT name, unit, price, category FROM catalog_items WHERE id = %s', (int(item_id),))
            row = cur.fetchone()
            if not row:
                raise ValueError('Работа не найдена.')
            name = row['name'] if isinstance(row, dict) else row[0]
            unit = row['unit'] if isinstance(row, dict) else row[1]
            price = row['price'] if isinstance(row, dict) else row[2]
            category = row['category'] if isinstance(row, dict) else row[3]
            base_name = f"{name} (копия)"
            candidate = base_name
            suffix = 2
            while True:
                cur.execute('SELECT 1 FROM catalog_items WHERE name = %s', (candidate,))
                if not cur.fetchone():
                    break
                candidate = f"{base_name} {suffix}"
                suffix += 1
            cur.execute(
                """
                INSERT INTO catalog_items (name, unit, price, category)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (candidate, unit, price, category),
            )
            inserted = cur.fetchone()
        conn.commit()
    return int(inserted['id'] if isinstance(inserted, dict) else inserted[0])


def upsert_new_catalog_items(items: list[dict]):
    from import_catalog_items import upsert_catalog_items

    ensure_catalog_items_table()
    with get_connection() as conn:
        return upsert_catalog_items(conn, items)


def apply_catalog_conflict_items(items: list[dict]):
    from import_catalog_items import upsert_catalog_items

    ensure_catalog_items_table()
    with get_connection() as conn:
        return upsert_catalog_items(conn, items)


def bulk_update_catalog_categories(updates: list[dict]) -> int:
    from import_catalog_items import CATEGORY_OPTIONS

    ensure_catalog_items_table()
    normalized: dict[int, str] = {}
    for item in updates or []:
        if not isinstance(item, dict):
            raise ValueError('Каждое изменение должно быть объектом.')
        try:
            item_id = int(item.get('id'))
        except (TypeError, ValueError) as exc:
            raise ValueError('Некорректный id работы.') from exc
        category = str(item.get('category') or '').strip()
        if category not in CATEGORY_OPTIONS:
            raise ValueError(f'Некорректная категория: {category}')
        normalized[item_id] = category

    if not normalized:
        return 0

    case_parts = []
    params: list = []
    ids = list(normalized.keys())
    for item_id, category in normalized.items():
        case_parts.append('WHEN %s THEN %s')
        params.extend([item_id, category])
    params.append(ids)
    query = f"""
        UPDATE catalog_items
        SET category = CASE id {' '.join(case_parts)} ELSE category END
        WHERE id = ANY(%s)
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            updated = cur.rowcount if cur.rowcount is not None else 0
        conn.commit()
    return int(updated)
