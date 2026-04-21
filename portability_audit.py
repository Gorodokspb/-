import json
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().with_name("dekorart_base.db")


def main() -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("TABLES")
    for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        print("-", row["name"])

    print("\nABSOLUTE PATH COUNTS IN DOCUMENTS")
    for column in ("file_path", "draft_path", "pdf_path"):
        count = cur.execute(
            f"SELECT COUNT(*) FROM documents WHERE {column} LIKE '%:%' OR {column} LIKE '\\\\%'"
        ).fetchone()[0]
        print(f"{column}: {count}")

    print("\nRECENT DOCUMENT PATHS")
    rows = cur.execute(
        """
        SELECT id,
               project_id,
               title,
               COALESCE(file_path, '') AS file_path,
               COALESCE(draft_path, '') AS draft_path,
               COALESCE(pdf_path, '') AS pdf_path
        FROM documents
        ORDER BY id DESC
        LIMIT 20
        """
    ).fetchall()
    for row in rows:
        print(json.dumps(dict(row), ensure_ascii=False))

    print("\nDOCUMENT PATH RESOLUTION CHECK")
    workspace_dir = DB_PATH.parent
    doc_rows = cur.execute(
        """
        SELECT id,
               project_id,
               title,
               COALESCE(file_path, '') AS file_path,
               COALESCE(draft_path, '') AS draft_path,
               COALESCE(pdf_path, '') AS pdf_path
        FROM documents
        ORDER BY id
        """
    ).fetchall()
    for row in doc_rows:
        missing = []
        for column in ("file_path", "draft_path", "pdf_path"):
            stored_path = str(row[column] or "").strip()
            if not stored_path:
                continue
            candidate = Path(stored_path)
            if not candidate.is_absolute():
                candidate = workspace_dir / candidate
            if not candidate.exists():
                missing.append(f"{column}={stored_path}")
        if missing:
            print(f"document {row['id']} ({row['title']}): {'; '.join(missing)}")

    print("\nTEXT COLUMNS WITH PATH-LIKE VALUES")
    tables = [
        row["name"]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    for table in tables:
        columns = cur.execute(f"PRAGMA table_info({table})").fetchall()
        text_columns = [column["name"] for column in columns if str(column["type"]).upper() in ("TEXT", "")]
        for column in text_columns:
            try:
                count = cur.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {table}
                    WHERE {column} LIKE '%:%'
                       OR {column} LIKE '\\\\%'
                       OR {column} LIKE '%Yandex%'
                       OR {column} LIKE '%CRM_OLD_BAD%'
                    """
                ).fetchone()[0]
            except sqlite3.DatabaseError:
                continue
            if count:
                print(f"{table}.{column}: {count}")

    print("\nSMETA DRAFTS WITH EXPLICIT DRIVE OR WORKSPACE HINTS")
    draft_rows = cur.execute(
        """
        SELECT id, data
        FROM smeta_drafts
        WHERE data LIKE '%C:\\%'
           OR data LIKE '%D:\\%'
           OR data LIKE '%Yandex%'
           OR data LIKE '%CRM_OLD_BAD%'
        ORDER BY id DESC
        """
    ).fetchall()
    print(f"count: {len(draft_rows)}")
    for row in draft_rows[:10]:
        print(f"draft {row['id']}: {row['data'][:220]}")

    print("\nPROJECT EVENTS WITH EXPLICIT DRIVE OR WORKSPACE HINTS")
    event_rows = cur.execute(
        """
        SELECT id, event_text
        FROM project_events
        WHERE event_text LIKE '%C:\\%'
           OR event_text LIKE '%D:\\%'
           OR event_text LIKE '%Yandex%'
           OR event_text LIKE '%CRM_OLD_BAD%'
        ORDER BY id DESC
        """
    ).fetchall()
    print(f"count: {len(event_rows)}")
    for row in event_rows[:10]:
        print(f"event {row['id']}: {row['event_text']}")

    conn.close()


if __name__ == "__main__":
    main()
