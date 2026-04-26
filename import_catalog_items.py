#!/usr/bin/env python3
"""Import and manage catalog items from Excel in PostgreSQL."""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Mapping

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_EXCEL_PATH = PROJECT_DIR / "Cleaned_Price_List_2026.xlsx"
DEFAULT_ENV_FILE = PROJECT_DIR / ".env.web"

NAME_COLUMN = "Наименование работ"
UNIT_COLUMN = "ед измерения"
PRICE_COLUMN = "цена за единицу"
CATEGORY_COLUMN = "category"

CATEGORY_OPTIONS = [
    "Потолок",
    "Стены",
    "Пол",
    "Демонтаж/Монтаж",
    "Сантехнические работы",
    "Электромонтажные работы",
    "Прочее",
]
DEFAULT_CATEGORY = "Прочее"

COLUMN_ALIASES = {
    NAME_COLUMN: (NAME_COLUMN, "Наименование", "Работа", "Название", "name"),
    UNIT_COLUMN: (UNIT_COLUMN, "Ед. изм.", "Ед. изм", "ед. изм.", "единица измерения", "unit"),
    PRICE_COLUMN: (PRICE_COLUMN, "Цена за м2", "Цена за м²", "Цена", "price"),
    CATEGORY_COLUMN: (CATEGORY_COLUMN, "Категория", "категория", "category"),
}

CATEGORY_KEYWORDS = [
    ("Демонтаж/Монтаж", ("демонтаж", "монтаж стен", "проема", "проёма", "создание проема", "создание проёма")),
    ("Электромонтажные работы", ("кабел", "кабель", "розетка", "щит", "выключатель", "светильник", "люстра", "электрика")),
    ("Сантехнические работы", ("труб", "смеситель", "унитаз", "ванна", "раковина", "инсталляция", "водоснабжение", "канализация")),
    ("Пол", ("пол", "ламинат", "кварцвинил", "стяжка", "плинтус напольный", "линолеум", "ковролин")),
    ("Потолок", ("потол", "потолок", "галтель", "карниз потолочный", "натяжной")),
    ("Стены", ("стен", "стена", "стены", "обои", "шпаклевка", "шпаклёвка", "штукатурка", "покраска стен", "плитка на стены")),
]


@dataclass(frozen=True)
class ImportResult:
    inserted: int
    updated: int
    total: int


@dataclass(frozen=True)
class ImportComparison:
    new_items: list[dict]
    conflicts: list[dict]
    unchanged_items: list[dict]


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_postgres_dsn(cli_dsn: str | None = None) -> str:
    if cli_dsn:
        return cli_dsn.strip()
    env_file = Path(os.environ.get("DEKORCRM_WEB_ENV_FILE", str(DEFAULT_ENV_FILE)))
    load_env_file(env_file)
    dsn = (os.environ.get("DEKORCRM_POSTGRES_DSN") or os.environ.get("POSTGRES_DSN") or "").strip()
    if not dsn:
        raise SystemExit("Не задан PostgreSQL DSN. Укажите --pg-dsn, DEKORCRM_POSTGRES_DSN или POSTGRES_DSN.")
    return dsn


def parse_price(value) -> Decimal | None:
    if value is None:
        return None
    try:
        if value != value:  # noqa: PLR0124
            return None
    except TypeError:
        pass
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Некорректная цена: {value!r}") from exc


def normalize_text(value) -> str:
    if value is None:
        return ""
    try:
        if value != value:  # noqa: PLR0124
            return ""
    except TypeError:
        pass
    return str(value).strip()


def normalize_category(value: str | None, fallback_name: str = "") -> str:
    category = normalize_text(value)
    if category in CATEGORY_OPTIONS:
        return category
    return categorize_catalog_item(fallback_name)


def categorize_catalog_item(name: str) -> str:
    haystack = normalize_text(name).casefold().replace("ё", "е")
    if not haystack:
        return DEFAULT_CATEGORY
    for category, keywords in CATEGORY_KEYWORDS:
        for keyword in keywords:
            if keyword.casefold().replace("ё", "е") in haystack:
                return category
    return DEFAULT_CATEGORY


def normalize_catalog_rows(rows: Iterable[Mapping]) -> list[dict]:
    """Normalize Excel rows and deduplicate by exact non-empty name; last occurrence wins."""
    items_by_name: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        name = normalize_text(row.get(NAME_COLUMN))
        if not name:
            continue
        if name not in items_by_name:
            order.append(name)
        category_value = row.get(CATEGORY_COLUMN)
        items_by_name[name] = {
            "name": name,
            "unit": normalize_text(row.get(UNIT_COLUMN)),
            "price": parse_price(row.get(PRICE_COLUMN)),
            "category": normalize_category(category_value, name),
        }
    return [items_by_name[name] for name in order]


def resolve_excel_columns(columns: Iterable[str], *, require_category: bool = False) -> dict[str, str]:
    available = {str(column).strip().casefold(): str(column) for column in columns}
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical == CATEGORY_COLUMN and not require_category:
            optional = True
        else:
            optional = False
        for alias in aliases:
            match = available.get(alias.strip().casefold())
            if match is not None:
                resolved[canonical] = match
                break
        else:
            if not optional:
                missing.append(canonical)
    if missing:
        raise ValueError("В Excel-файле нет обязательных колонок: " + ", ".join(missing))
    return resolved


def read_catalog_items(excel_path: Path, *, nrows: int | None = None) -> list[dict]:
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel-файл не найден: {excel_path}")
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("Не установлен pandas. Установите зависимости: pip install -r requirements.txt") from exc
    dataframe = pd.read_excel(excel_path, nrows=nrows)
    columns = resolve_excel_columns(dataframe.columns)
    normalized_dataframe = dataframe.rename(columns={source: canonical for canonical, source in columns.items()})
    return normalize_catalog_rows(normalized_dataframe.to_dict(orient="records"))


def ensure_catalog_items_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_items (
                id SERIAL PRIMARY KEY,
                name VARCHAR(500) NOT NULL UNIQUE,
                unit VARCHAR(100),
                price DOUBLE PRECISION,
                category VARCHAR(100) NOT NULL DEFAULT 'Прочее'
            )
            """
        )
        cur.execute("ALTER TABLE catalog_items ADD COLUMN IF NOT EXISTS name VARCHAR(500)")
        cur.execute("ALTER TABLE catalog_items ADD COLUMN IF NOT EXISTS unit VARCHAR(100)")
        cur.execute("ALTER TABLE catalog_items ADD COLUMN IF NOT EXISTS price DOUBLE PRECISION")
        cur.execute("ALTER TABLE catalog_items ADD COLUMN IF NOT EXISTS category VARCHAR(100) NOT NULL DEFAULT 'Прочее'")
        cur.execute("ALTER TABLE catalog_items ALTER COLUMN name SET NOT NULL")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS catalog_items_name_unique_idx ON catalog_items (name)")
    conn.commit()


def migrate_catalog_categories(conn) -> int:
    ensure_catalog_items_table(conn)
    updated = 0
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, category FROM catalog_items")
        rows = cur.fetchall()
        for row in rows:
            item_id = row["id"] if isinstance(row, dict) else row[0]
            name = row["name"] if isinstance(row, dict) else row[1]
            current = row["category"] if isinstance(row, dict) else row[2]
            category = categorize_catalog_item(name)
            if current != category:
                cur.execute("UPDATE catalog_items SET category = %s WHERE id = %s", (category, item_id))
                updated += 1
    conn.commit()
    return updated


def fetch_existing_catalog_items(conn, names: list[str] | None = None) -> list[dict]:
    with conn.cursor() as cur:
        if names is None:
            cur.execute("SELECT id, name, unit, price, category FROM catalog_items ORDER BY category, lower(name), id")
        else:
            cur.execute("SELECT id, name, unit, price, category FROM catalog_items WHERE name = ANY(%s)", (names,))
        rows = cur.fetchall()
    return [dict(row) if isinstance(row, dict) else {"id": row[0], "name": row[1], "unit": row[2], "price": row[3], "category": row[4]} for row in rows]


def _price_key(value) -> Decimal | None:
    return parse_price(value)


def compare_catalog_import(existing_rows: list[dict], incoming_items: list[dict]) -> ImportComparison:
    existing_by_name = {row["name"]: row for row in existing_rows}
    new_items: list[dict] = []
    conflicts: list[dict] = []
    unchanged_items: list[dict] = []
    for item in incoming_items:
        old = existing_by_name.get(item["name"])
        if not old:
            new_items.append(item)
            continue
        changed = (
            normalize_text(old.get("unit")) != normalize_text(item.get("unit"))
            or _price_key(old.get("price")) != _price_key(item.get("price"))
            or normalize_category(old.get("category"), old.get("name", "")) != normalize_category(item.get("category"), item.get("name", ""))
        )
        if changed:
            conflicts.append({"id": old.get("id"), "name": item["name"], "old": old, "new": item})
        else:
            unchanged_items.append(item)
    return ImportComparison(new_items=new_items, conflicts=conflicts, unchanged_items=unchanged_items)


def upsert_catalog_items(conn, items: list[dict]) -> ImportResult:
    if not items:
        return ImportResult(inserted=0, updated=0, total=0)
    names = [item["name"] for item in items]
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM catalog_items WHERE name = ANY(%s)", (names,))
        existing_names = {row[0] if not isinstance(row, dict) else row["name"] for row in cur.fetchall()}
        params = [(item["name"], item.get("unit", ""), item.get("price"), normalize_category(item.get("category"), item["name"])) for item in items]
        cur.executemany(
            """
            INSERT INTO catalog_items (name, unit, price, category)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE
            SET unit = EXCLUDED.unit,
                price = EXCLUDED.price,
                category = EXCLUDED.category
            """,
            params,
        )
    conn.commit()
    updated = sum(1 for name in names if name in existing_names)
    inserted = len(items) - updated
    return ImportResult(inserted=inserted, updated=updated, total=len(items))


def import_catalog_items(pg_dsn: str, excel_path: Path, *, nrows: int | None = None) -> ImportResult:
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Не установлен psycopg. Установите зависимости: pip install -r requirements.txt") from exc
    items = read_catalog_items(excel_path, nrows=nrows)
    with psycopg.connect(pg_dsn) as conn:
        ensure_catalog_items_table(conn)
        return upsert_catalog_items(conn, items)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Импортировать Excel-прайс в PostgreSQL catalog_items.")
    parser.add_argument("--excel", default=str(DEFAULT_EXCEL_PATH), help=f"Путь к Excel-файлу. По умолчанию: {DEFAULT_EXCEL_PATH}")
    parser.add_argument("--pg-dsn", default=None, help="PostgreSQL DSN. Также можно задать DEKORCRM_POSTGRES_DSN или POSTGRES_DSN.")
    parser.add_argument("--migrate-categories", action="store_true", help="Только заполнить/обновить category у существующих записей.")
    parser.add_argument("--limit", type=int, default=None, help="Импортировать только первые N строк Excel для теста.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    pg_dsn = get_postgres_dsn(args.pg_dsn)
    if args.migrate_categories:
        import psycopg
        with psycopg.connect(pg_dsn) as conn:
            updated = migrate_catalog_categories(conn)
        logging.info("Миграция категорий catalog_items завершена: обновлено=%s", updated)
        return
    excel_path = Path(args.excel).expanduser().resolve()
    result = import_catalog_items(pg_dsn, excel_path, nrows=args.limit)
    logging.info("Импорт catalog_items завершён: добавлено=%s, обновлено=%s, всего_строк=%s", result.inserted, result.updated, result.total)


if __name__ == "__main__":
    main()
