# 08 — Catalog and Excel import notes

## Структурированный каталог работ
Файлы:
```text
import_catalog_items.py
webapp/db.py
webapp/main.py
webapp/templates/catalog.html
webapp/templates/catalog_conflicts.html
webapp/static/app.css
webapp/static/app.js
tests/test_catalog_management.py
tests/test_import_catalog_items.py
```

## Схема БД
`catalog_items` содержит:
- `id SERIAL PRIMARY KEY`
- `name VARCHAR(500) NOT NULL UNIQUE`
- `unit VARCHAR(100)`
- `price DOUBLE PRECISION`
- `category VARCHAR(100) NOT NULL DEFAULT 'Прочее'`

Разрешённые категории:
```text
Потолок
Стены
Пол
Демонтаж/Монтаж
Сантехнические работы
Электромонтажные работы
Прочее
```

## Автокатегоризация
Логика находится в `import_catalog_items.categorize_catalog_item()`.
Приоритет категорий соответствует ТЗ: сначала `Демонтаж/Монтаж`, затем электрика, сантехника, пол, потолок, стены, иначе `Прочее`.

Команда миграции существующих строк:
```bash
cd /opt/dekorcrm/app/CRM_OLD_BAD
python import_catalog_items.py --migrate-categories
```

## Web UI
Маршрут `/catalog`:
- компактная таблица с группировкой по категориям;
- sticky topbar, toolbar, заголовки таблицы и строки категорий;
- живой поиск по названию/единице/категории;
- добавление через модальное окно;
- inline редактирование полей `name`, `unit`, `price`, `category`;
- удаление с подтверждением;
- копирование строки;
- импорт `.xlsx`.

## Умный импорт
Маршрут `POST /catalog/upload`:
- читает `.xlsx` через pandas/openpyxl;
- новые записи добавляет автоматически;
- совпадения по `name` сравнивает по `unit`, `price`, `category`;
- отличающиеся записи показывает на странице `catalog_conflicts.html`;
- конфликт можно пропустить, применить все новые или применить выбранные.

## Проверка, выполненная 2026-04-26
- Тестовый импорт первых 10 строк: `добавлено=0`, `обновлено=9`, `всего_строк=9`.
- Миграция категорий: `обновлено=42`.
- Полный импорт: `добавлено=0`, `обновлено=107`, `всего_строк=107`.
- В БД: `107` строк, `107` уникальных name, пустых category нет.
- Smart upload smoke: тестовый `.xlsx` с одной новой строкой и одним конфликтом вернул страницу разрешения конфликтов; тестовая строка удалена после проверки.
- `/opt/dekorcrm/venv/bin/python -m unittest discover -s tests -v` — 17 tests OK.
- `/opt/dekorcrm/venv/bin/python -m py_compile import_catalog_items.py webapp/main.py webapp/db.py` — OK.
- `dekorcrm-web` перезапущен и активен; authenticated smoke `/login`, `/projects`, `/catalog` возвращает 200.

## Важные замечания
- Не печатать `.env.web` и DSN в чат/документы.
- Для production web app pandas должен быть установлен в `/opt/dekorcrm/venv`; сейчас установлен `pandas==2.2.3`.
- `requirements.txt` обновлён: добавлен `pandas==2.2.3`.
