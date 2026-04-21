from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from webapp.config import get_settings


@contextmanager
def get_connection():
    settings = get_settings()
    conn = psycopg.connect(settings.postgres_dsn, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def fetch_projects():
    query = """
        SELECT
            p.id,
            COALESCE(NULLIF(p.project_name, ''), NULLIF(p.address, ''), 'Без названия') AS project_name,
            COALESCE(p.address, '') AS address,
            COALESCE(cp.company_name, cp.full_name, cp.name, '') AS counterparty_name,
            COALESCE(NULLIF(p.status, ''), 'Черновик') AS status,
            COALESCE(p.contract, '') AS contract,
            COALESCE(p.date, '') AS contract_date,
            COALESCE(p.updated_at, p.created_at, '') AS updated_at
        FROM projects p
        LEFT JOIN counterparties cp ON cp.id = p.counterparty_id
        ORDER BY COALESCE(p.updated_at, p.created_at, ''), p.id DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
    return list(reversed(rows))


def fetch_dashboard_counts():
    query = """
        SELECT
            (SELECT COUNT(*) FROM projects) AS projects_total,
            (SELECT COUNT(*) FROM counterparties) AS counterparties_total,
            (SELECT COUNT(*) FROM documents) AS documents_total,
            (SELECT COUNT(*)
             FROM projects
             WHERE COALESCE(NULLIF(status, ''), 'Черновик') = 'В работе') AS active_projects_total
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
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
            COALESCE(NULLIF(p.status, ''), 'Черновик') AS status,
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
            cur.execute(query, (project_id,))
            return cur.fetchone()


def fetch_project_documents(project_id: int):
    query = """
        SELECT
            id,
            project_id,
            COALESCE(doc_type, '') AS doc_type,
            COALESCE(title, '') AS title,
            COALESCE(status, 'Черновик') AS status,
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
            cur.execute(query, (project_id,))
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
            COALESCE(status, 'Черновик') AS status,
            COALESCE(file_path, '') AS file_path,
            COALESCE(draft_path, '') AS draft_path,
            COALESCE(pdf_path, '') AS pdf_path
        FROM documents
        WHERE id = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (document_id,))
            return cur.fetchone()
