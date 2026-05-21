# 07 — Next steps

## Stage 8.4 ✅ ЗАВЕРШЁН

### 8.4.1 ✅ Schema + repository
### 8.4.2 ✅ Repository/service
### 8.4.3 ✅ UI settings companies
### 8.4.4 ✅ Asset upload protected storage
### 8.4.5 ✅ estimates.company_id FK
### 8.4.6a ✅ Company details in final PDF
### 8.4.6b ✅ Final PDF stamp/signature checkboxes
### 8.4.6c ✅ Real PNG stamp/signature in final PDF (live-verified)
### 8.4.6d ✅ Watermark from company.watermark_text
### 8.4.7 ✅ Legacy _get_company_details() DB fallback

## Stage 8.5: Импорт Excel-смет в standalone-редактор

### 8.5.1 ✅ Parser module (выполнено)
- `webapp/excel_estimate_parser.py` + 62 теста.

### 8.5.1b ✅ Parser adapted to real format (выполнено)
- HEADER_SCAN_ROWS=25, discounted_total, _looks_like_summary.

### 8.5.2 ✅ Backend import routes (выполнено)
- `GET /estimates/{id}/import-excel` — страница загрузки.
- `POST /estimates/{id}/import-excel/preview` — парсинг → JSON без изменения БД.
- `POST /estimates/{id}/import-excel/apply` — `append_items_to_estimate()`.
- Только для draft-статуса; запрет sent/approved/final.
- Auth-gated.
- Файлы: `webapp/standalone_estimate_api.py`, `tests/test_excel_estimate_import_routes.py`, `webapp/templates/import_excel.html`.

### 8.5.3 ✅ Live/manual verification (выполнено)
- Draft-смета ID=888, preview 3 раздела/12 позиций, apply 15 строк.
- Негативные сценарии пройдены. Баг шаблона исправлен.
- Commit: `465aae8`.

### 8.5.4 ✅ UI integration + live verification (выполнено)
- Кнопка «Импорт из Excel» в редакторе standalone-сметы (draft only).
- 3 template-теста. Commit: `8c6f2a7`.

### 8.5.4 fix ✅ Excel import cleanup + PDF wrapping (выполнено)
- Фильтрация подписей/мусора, section с total, PDF wrapping длинных имён.
- Коммит: `a9d24b0`.

### 8.5.4c ✅ Fix standalone draft estimate number generation (выполнено)
- `estimate_number=""` → `draft-{timestamp}-{uuid}`. UniqueViolation больше не возникает.
- Коммит: `cb5b9b7`.

### 8.5.4d ✅ Filter mixed signature year rows in Excel import (выполнено)
- `_looks_like_signature_or_trash()` фильтрует строки вида `"___" __________ 2026 год`.
- 5 новых тестов (92 всего в парсере).
- Коммит: `54bf6a4`.

### 8.5.4 live verification ✅ (пройдена)
- Создана новая draft-смета через `/standalone-estimates/new`.
- Excel-импорт применён, мусорные строки отфильтрованы.
- PDF чистый, длинные названия переносятся.
- Скидка: поле в sidebar, дублирование внизу не планируется.

### 8.5.5 ✅ Финальная полировка UX импорта Excel (выполнено)
- Предупреждение «импорт добавляет строки, а не заменяет».
- `confirm()` диалог перед apply.
- Кнопка блокируется после успешного apply (UX-защита от повтора).
- 4 новых template-теста. Коммит: `e9392bb`.

## Stage 8.5 ✅ Функционально закрыт

## Stage 8.6: Создание проекта из approved standalone-сметы ✅ ЗАКРЫТ

### 8.6.1 ✅ Backend create-project route (выполнено)
- `POST /estimates/{id}/create-project` + service-метод.
- 6 route-тестов. Коммит: `1a1c6af`.

### 8.6.2 ✅ UI button (выполнено)
- Кнопка «Создать проект» / ссылка «Открыть проект» в approved-блоке.
- JS-хендлер с redirect. 24 UI-теста. Коммит: `4772c09`.

### 8.6.2b ✅ In-progress project link (выполнено)
- Ссылка «Открыть проект» в in_progress-блоке.
- Live-проверка: смета 881 → проект 9. 25 UI-тестов. Коммит: `bc58ade`.

### 8.6.3 ✅ Project status «В работе» (выполнено)
- Проект из approved standalone-сметы создаётся со статусом «В работе».
- Коммит: `e597a50`.

### Live verification 8.6 ✅
- Смета 881 → проект 9 (8.6.2). Смета 874 → проект 10 (8.6.3).
- Проект создаётся со статусом «В работе».
- После создания смета в in_progress, ссылка «Открыть проект» работает.

## Stage 8.6 ✅ Полностью закрыт

## Stage 8.7 ✅ ЗАКРЫТ

## Stage 8.8: Finance module integration ✅ ЗАКРЫТ

### 8.8 ✅ Finance integration verified (выполнено)
- Live-проверка: проект 11, доход 50 000 ₽, расход 15 000 ₽, прибыль 35 000 ₽.
- `/finance` баланс 45 000 ₽. Транзакции привязаны к проектам.

## Stage 8.8.1: Fix hardcoded finance totals ✅ ЗАКРЫТ

### 8.8.1 ✅ Real finance totals in project cards (выполнено)
- Верхние метрики и карточки баланса в `project_detail.html` используют `project_finance_summary`.
- Live-проверка: проект 11 показывает реальные суммы.
- Коммит: `f5beac7`.

## Stage 8.9.1: Counterparty CRUD pages ✅ ЗАКРЫТ

### 8.9.1a ✅ Extended counterparty creation fields (выполнено)
- `/counterparties/new` принимает 28 полей (паспорт, адреса, реквизиты, банк, директор).
- `create_counterparty()` в `webapp/db.py` — все 28 полей сохраняются.
- Live-проверка: «Тест Договор Физлицо» (id=3), расширенные поля сохранены корректно.
- Коммит: `7e590dd`.

### 8.9.1b ✅ Counterparty list/detail/edit pages (выполнено)
- `/counterparties` — список контрагентов с ID, тип, имя, телефон, email, ИНН.
- `/counterparties/{id}` — карточка контрагента (все 28 полей: основное, паспорт, реквизиты, банк, директор).
- `/counterparties/{id}/edit` — форма редактирования всех 28 полей (GET pre-fill, POST update).
- `fetch_counterparty()`, `update_counterparty(**fields)` добавлены в `webapp/db.py`.
- `ensure_counterparties_updated_at()` — миграция `updated_at TEXT DEFAULT ''` в `counterparties`.
- Ссылка «Контрагенты» в topbar `projects.html`.
- POST создания редиректит на `/counterparties/{id}`.
- 404 для несуществующего контрагента.
- 34 теста (16 template/route + 18 DB), все зелёные.
- Live-проверка пройдена.
- Коммит: `70b22b7`.

## Stage 8.9.2: Contract settings page and draft contract document ✅ ЗАКРЫТ

### 8.9.2 ✅ Contract settings page + draft document (выполнено)
- `/projects/{project_id}/contract` — GET отображает настройки, POST сохраняет.
- `contract_settings_json` в `projects` (TEXT, JSON blob) — без новой миграции.
- Document record `doc_type='Договор'`, `status='Черновик'`, `project_id` привязан.
- `fetch_contract_settings()`, `save_contract_settings()`, `create_or_update_contract_document()`, `get_project_estimate_total()` в `webapp/db.py`.
- Ссылка «Настройки договора» в `project_detail.html`.
- 22 теста (10 DB + 12 template/route).
- Коммит: `0ad9dd4`.

### 8.9.2b ✅ Improve contract payment UX (выполнено)
- Платёжные строки: collapsible (заполненные + минимум 2, остальные скрыты).
- Кнопка «+ Добавить платёж» (максимум 7 платежей).
- Форматирование сумм через точки: `formatMoney`/`stripMoney` в inline JS.
- `focus` → raw, `blur` → formatted, `submit` → strip separators.
- 29 тестов, все зелёные. Live-проверка пройдена.
- Коммит: `6e41294`.

DOCX/PDF generation не делалась в Stage 8.9.2/8.9.2b; перед Stage 8.9.3 нужна отдельная диагностика и отдельное подтверждение пользователя.

## Stage 8.9.3 — следующий логический этап: диагностика генерации договора из template

### Планируемое содержание 8.9.3
1. Диагностика `contract_template_physical.docx` — структура, 19 `[[PLACEHOLDER]]` полей, совместимость с python-docx.
2. Реализация `build_contract_replacements()` — маппинг project + counterparty + estimate данных → placeholder values.
3. Генерация DOCX из шаблона с заполненными плейсхолдерами.
4. Скачивание DOCX и/или конвертация в PDF.

### Ограничения (подтверждённые)
- DOCX/PDF generation не делалась в 8.9.2/8.9.2b; перед 8.9.3 нужна отдельная диагностика и подтверждение пользователя.
- Акты и приложения — не делались.
- Смеси, финансы, legacy routes — не затронуты.
- Mobile/adaptive layout — отложено.

## Test suite fixes ✅ ЗАКРЫТЫ
- `test_estimate_repository.py`: 13/13 pass.
- `test_standalone_estimate_routes.py`: 27/27 pass.
- Коммит: `9069b9d`.

## Функциональные блоки Stage 8.5–8.8.1 — все закрыты

### Будущий этап: UI-audit / UI-polish (после подтверждения пользователя)
- Привести import_excel.html и другие страницы к единому визуальному стилю CRM.
- Визуальная полировка страниц импорта, списков, редактора.
- Делать отдельными маленькими этапами, не одним большим рефакторингом.
- Начинать только после подтверждения пользователя.

### Будущий этап: Mobile/adaptive layout
- Не начат. Отдельный этап после завершения desktop-функционала.

## Ближайшие задачи по CRM/сметам (после 8.5)
1. Доводить редактор сметы до плотного desktop-подобного вида.
2. Проверить sticky header/actions визуально.
3. Решить по колонке кода/артикула.
4. Перенос калькулятора объёмов из desktop в web.
5. Проверить правую панель расценок на реальных данных.
6. Безопасный deploy workflow для crm198.ru.

## Handoff maintenance
После каждого значимого этапа:
1. Обновить relevant `.md` файлы в `handoff_to_hermes/`.
2. Проверить, что нет секретов.
3. Закоммитить изменения.
4. По возможности отправить на GitHub.

## Инфраструктура
- GitHub push через SSH.
- Ветка: `hermes/integrate-origin-master-20260423`.
- Сервис: `dekorcrm-web.service` на `127.0.0.1:8000`.
- БД: PostgreSQL `dekorcrm`, бэкапы в `/opt/dekorcrm/backups/`.
