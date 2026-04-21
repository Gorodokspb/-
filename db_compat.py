import os
import re
import sqlite3

try:
    import psycopg
except ImportError:  # pragma: no cover - optional dependency on local Windows installs
    psycopg = None


def get_postgres_dsn():
    return (
        os.environ.get("DEKORCRM_POSTGRES_DSN")
        or os.environ.get("POSTGRES_DSN")
        or ""
    ).strip()


def is_postgres_enabled():
    return bool(get_postgres_dsn())


def get_state_connection(sqlite_path):
    return _get_connection(sqlite_path)


def get_price_connection(sqlite_path):
    return _get_connection(sqlite_path)


def connect(sqlite_path, *args, **kwargs):
    return _get_connection(sqlite_path)


def _get_connection(sqlite_path):
    dsn = get_postgres_dsn()
    if not dsn:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn
    if psycopg is None:
        raise RuntimeError(
            "Для подключения к PostgreSQL нужен пакет psycopg. "
            "Установите зависимости из requirements.txt."
        )
    return PostgresConnection(dsn)


class CompatRow:
    def __init__(self, values, columns):
        self._values = tuple(values)
        self._columns = list(columns)
        self._index = {name: idx for idx, name in enumerate(self._columns)}

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._index[key]]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return list(self._columns)

    def items(self):
        return [(name, self[name]) for name in self._columns]

    def values(self):
        return list(self._values)

    def get(self, key, default=None):
        return self[key] if key in self._index else default

    def __repr__(self):
        return f"CompatRow({dict(self.items())!r})"


class PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, query, params=None):
        translated_query, translated_params, meta = translate_sql(query, params)
        self.lastrowid = None
        self._cursor.execute(translated_query, translated_params)
        if meta.get("capture_lastrowid"):
            row = self._cursor.fetchone()
            self.lastrowid = row[0] if row else None
        return self

    def executemany(self, query, seq_of_params):
        translated_query, _, meta = translate_sql(query, None)
        if meta.get("capture_lastrowid"):
            self.lastrowid = None
            for params in seq_of_params:
                self.execute(query, params)
            return self
        prepared_params = [normalize_params(params) for params in seq_of_params]
        self._cursor.executemany(translated_query, prepared_params)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return wrap_row(row, self._cursor.description)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [wrap_row(row, self._cursor.description) for row in rows]

    def close(self):
        self._cursor.close()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def __iter__(self):
        return iter(self.fetchall())


class PostgresConnection:
    def __init__(self, dsn):
        self._conn = psycopg.connect(dsn)
        self.row_factory = None

    def cursor(self):
        return PostgresCursor(self._conn.cursor())

    def execute(self, query, params=None):
        return self.cursor().execute(query, params)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()


def wrap_row(row, description):
    if row is None:
        return None
    columns = []
    for item in description or []:
        name = getattr(item, "name", None)
        if name is None:
            name = item[0]
        columns.append(name)
    return CompatRow(row, columns)


def normalize_params(params):
    if params is None:
        return None
    if isinstance(params, dict):
        return params
    if isinstance(params, tuple):
        return params
    if isinstance(params, list):
        return tuple(params)
    return (params,)


def translate_sql(query, params):
    stripped = str(query or "").strip()
    translated_params = normalize_params(params)
    meta = {"capture_lastrowid": False}

    pragma_match = re.match(r"(?is)^PRAGMA\s+table_info\(([^)]+)\)\s*;?\s*$", stripped)
    if pragma_match:
        table_name = pragma_match.group(1).strip().strip("'\"")
        return build_pg_table_info_query(), (table_name,), meta

    if "sqlite_master" in stripped.lower():
        return "SELECT tablename AS name FROM pg_tables WHERE schemaname='public'", None, meta

    translated = stripped
    translated = re.sub(
        r"(?is)\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY",
        translated,
    )
    translated = re.sub(
        r"(?is)^INSERT\s+OR\s+IGNORE\s+INTO\b",
        "INSERT INTO",
        translated,
    )
    if stripped.upper().startswith("INSERT OR IGNORE INTO"):
        translated = translated.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

    translated = replace_qmark_placeholders(translated)

    if re.match(r"(?is)^INSERT\s+INTO\s+", translated) and "RETURNING" not in translated.upper() and "ON CONFLICT" not in translated.upper():
        translated = translated.rstrip().rstrip(";") + " RETURNING id"
        meta["capture_lastrowid"] = True

    return translated, translated_params, meta


def build_pg_table_info_query():
    return """
        SELECT
            c.ordinal_position - 1 AS cid,
            c.column_name AS name,
            c.data_type AS type,
            CASE WHEN c.is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull,
            c.column_default AS dflt_value,
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM pg_index i
                    JOIN pg_class t ON t.oid = i.indrelid
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(i.indkey)
                    WHERE i.indisprimary
                      AND t.relname = c.table_name
                      AND a.attname = c.column_name
                ) THEN 1
                ELSE 0
            END AS pk
        FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.table_name = %s
        ORDER BY c.ordinal_position
    """


def replace_qmark_placeholders(query):
    result = []
    in_single_quote = False
    in_double_quote = False
    for char in query:
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            result.append(char)
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            result.append(char)
            continue
        if char == "?" and not in_single_quote and not in_double_quote:
            result.append("%s")
            continue
        result.append(char)
    return "".join(result)
