# Finance Module Notes

Updated: 2026-04-26 20:02 UTC

## Scope

Implemented the global base layout and the first pass of the cross-cutting finance module.

## Database

Table: `transactions`

Fields:
- `id SERIAL PRIMARY KEY`
- `type VARCHAR(20) NOT NULL` — `income` or `expense`
- `amount DECIMAL(12, 2) NOT NULL DEFAULT 0`
- `description TEXT`
- `date TIMESTAMP NOT NULL DEFAULT NOW()`
- `project_id INTEGER NULL REFERENCES projects(id) ON DELETE SET NULL`
- `category VARCHAR(100) NOT NULL DEFAULT 'Прочее'`
- `status VARCHAR(30) NOT NULL DEFAULT 'completed'`

Indexes:
- `idx_transactions_date` on `(date DESC, id DESC)`
- `idx_transactions_project_id` on `project_id`

The helper `ensure_transactions_table()` is guarded by an in-process readiness flag after migration to avoid repeated DDL locks during normal page reads.

## Backend

Routes:
- `GET /finance` — global cashbox with all transactions and total balance.
- `POST /finance/transactions` — creates income/expense transaction and redirects back with a flash message.

Project page integration:
- `GET /projects/{id}` now fetches only transactions with matching `project_id`.
- Project finance summary uses `summarize_transactions()`:
  - income sum
  - expense sum
  - balance/profit = income - expense

Validation:
- transaction type must be `income` or `expense`.
- amount must be greater than zero.
- `project_id` is nullable; if a project is deleted, FK is `ON DELETE SET NULL` to preserve money history.

## UI

`base.html` now includes:
- sticky global header;
- logo link to `/projects`;
- center navigation: Проекты, Сметы, Справочник, Калькулятор, Финансы;
- right `+ Действие` button;
- one shared transaction modal available on every page;
- flash message area.

Mobile:
- navigation becomes a horizontal scroll strip to prevent buttons overlapping.

Auto-project behavior:
- if a page sets `current_project_id`, the shared transaction modal auto-selects that project.

## Verification

Commands used:

```bash
/opt/dekorcrm/venv/bin/python -m py_compile webapp/main.py webapp/db.py
/opt/dekorcrm/venv/bin/python -m unittest discover -s tests -v
systemctl restart dekorcrm-web && systemctl is-active dekorcrm-web
```

Live smoke:
- `/finance` returns the global cashbox.
- `/projects` renders the global header.
- test transaction with `project_id` appears in `/projects/{id}` finance block.
- smoke transaction was deleted after verification.

No secrets, DSN values, tokens, usernames, or passwords are stored in this file.
