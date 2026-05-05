# 01 — Current status

## Текущая серверная ветка
```text
hermes/integrate-origin-master-20260423
```

## Последние важные коммиты
```text
0586e6e Stage 8.5.1b adapt parser to real estimate format
55293ce Stage 8.5.1 excel estimate parser module
cf5324b Stage 8.4.7 legacy company details fallback
c2a3e47 Document Stage 8.4 completion
e8d525c Stage 8.3.3 standalone workflow UI
```

Все отправлены на GitHub: `origin/hermes/integrate-origin-master-20260423`.

## Выполненные этапы standalone-смет

### Stage 6–7: Реестр и редактор standalone-смет
- Создан реестр самостоятельных смет `/standalone-estimates`.
- Работает создание сметы без проекта и без контрагента.
- Работает открытие standalone-сметы в редакторе `/estimates/{id}/edit`.
- Исправлено сохранение шапки, разделов и позиций; повторное открытие сохраняет данные.

### Stage 8.1: JSON / snapshots / statuses
- Исправлен порядок send/approve.
- sent/approved snapshots содержат актуальный status.
- `approved_version_id` и `current_version_id` работают корректно.

### Stage 8.2: Draft PDF
- Standalone draft PDF формируется отдельно от legacy.
- Разделы отображаются как разделы, итоги и скидка выводятся.
- Watermark для черновика добавлен; печать/подпись запрещены в draft.

### Stage 8.3.1–8.3.2b: Final approved PDF
- Final PDF строится из approved snapshot, а не из текущих живых данных.
- Добавлены маршруты final PDF (`POST /final-pdf`, `GET /download/final-pdf`).
- Final PDF привязан к `documents`, `estimate_documents`, `estimate_versions.pdf_document_id`, `estimates.final_document_id`.
- `documents.project_id` допускает NULL для standalone-документов (миграция `20260503_documents_nullable_project_id.sql`).
- Workflow `draft → sent → approved → final PDF → download` проверен на live (estimate 683).

### Stage 8.3.3: UI workflow
- В standalone editor добавлены кнопки: Отправить клиенту, Согласовать, Отклонить, Сформировать final PDF, Скачать final PDF, Скачать JSON.
- JS делает `fetch + reload`; legacy editor не затронут.
- 9 текстовых проверок шаблона, 135 тестов — все зелёные.
- **Live-проверка пройдена**: полный workflow `создание → шапка → раздел → 2 позиции → сохранить → отправить → согласовать → final PDF → скачать` работает на crm198.ru.
- Final PDF содержит: status=approved, раздел, 2 позиции, итоги до/после скидки.
- Исправлен баг: пустое JSON body при `POST /final-pdf` вызывал 500 (`_load_payload` теперь tolerant к пустому body).
- Добавлена защита тестов от live-БД: `guard_live_database()` блокирует `DELETE FROM` на database `dekorcrm`.

### Stage 8.4.1–8.4.2: Companies schema + repository
- Таблица `companies`, seed-данные ООО «Декорартстрой» (id=1) и ИП Гордеев А.Н. (id=2).
- `CompanyRepository`, `CompanyService`, 16 тестов.

### Stage 8.4.3–8.4.4: Company settings UI + protected asset upload
- APIRouter `/settings/companies` — CRUD, upload stamp/signature, serve assets.
- Templates `companies_list.html`, `company_detail.html`.
- PNG-only upload: validate content_type, extension, magic bytes, max 2MB.
- Protected storage: `/opt/dekorcrm/storage/company-assets/{company_id}/`.
- Auth-gated GET routes для stamp/signature.
- 17 тестов `test_company_api`.

### Stage 8.4.5: estimates.company_id FK
- `estimates.company_id BIGINT NULL REFERENCES companies(id) ON DELETE SET NULL`.
- `EstimateSummary`, `EstimateCreateInput`, `EstimateUpdateInput` — проброс `company_id`.

### Stage 8.4.6a: Company details in final PDF
- Если у сметы `company_id` → блок реквизитов (ИНН, КПП, ОГРН, адрес, банк, подписант).
- Если `company_id` нет → fallback `Компания: {company_name}`.
- 5 новых тестов.

### Stage 8.4.6b: Final PDF stamp/signature checkboxes
- Чекбоксы «Добавить печать» / «Добавить подпись» в approved editor (только если `final_document_id` отсутствует).
- JS отправляет `stamp_applied`/`signature_applied` в `POST /final-pdf`.
- 6 новых тестов UI + JS.

### Stage 8.4.6d: Watermark from companies.watermark_text
- `_resolve_watermark_text(company_name, company)` в `standalone_estimate_files.py`.
- Если `company` задан и `watermark_text` не пуст — берёт из DB.
- Fallback: `"ИП ГОРДЕЕВ А.Н."` / `"ДЕКОРАРТСТРОЙ"` по `company_name`.
- Final PDF watermark намеренно отключён (пустой callback `return`).
- 7 новых тестов.

### Stage 8.4.7: Legacy _get_company_details() DB fallback
- `_get_company_details(company_name)` в `estimate_pdf.py` сначала пытается найти компанию в DB (по `short_name`, затем `legal_name`).
- Если компания найдена — возвращает dict `{title, details}` в legacy-формате через `_company_to_details_dict()`.
- При любой ошибке (DB недоступна, ImportError, company не найдена) — возвращает hardcoded fallback из `_HARDCODED_COMPANY_DETAILS`.
- Добавлены `_hardcoded_company_details()`, `_split_address()`, `_company_to_details_dict()`.
- 26 тестов в `test_estimate_pdf_company_fallback.py`.

## Stage 8.4 — полный перечень выполненного

1. **companies table + seed**: ООО «Декорартстрой» (id=1), ИП Гордеев А.Н. (id=2).
2. **CompanyRepository / CompanyService**: CRUD, get_by_short_name, list, deactivate, set_asset_paths.
3. **Settings UI для компаний**: `/settings/companies` — список, детали, CRUD.
4. **Protected upload stamp/signature PNG**: content_type, extension, magic bytes, max 2MB; auth-gated serve.
5. **estimates.company_id**: `BIGINT NULL REFERENCES companies(id) ON DELETE SET NULL`.
6. **Реквизиты компании в standalone final PDF**: ИНН, КПП, ОГРН, адрес, банк, подписант — из DB по `company_id`.
7. **Checkbox «Добавить печать» / «Добавить подпись»**: только для approved, только до формирования final PDF.
8. **Реальные PNG печати/подписи**: `_resolve_company_asset()`, `reportlab.platypus.Image`, fallback «М.П.»/«Подпись».
9. **Watermark draft PDF из companies.watermark_text**: с fallback на hardcoded.
10. **Legacy _get_company_details() DB lookup**: с hardcoded fallback, `try/except` вокруг DB.

## Live-проверки
- Standalone final PDF для estimate 881 (company_id=2, ИП Гордеев А.Н.): реквизиты, печать, подпись отображаются корректно.
- Legacy project-based PDF: реквизиты ООО Декорартстрой отображаются корректно, watermark ДЕКОРАРТСТРОЙ работает, PDF визуально не сломан.

## Подтверждённые гарантии
- Protected storage используется (`/opt/dekorcrm/storage/company-assets/`).
- Печать/подпись не лежат в `static/`.
- Hardcoded fallback для legacy сохранён на 100%.
- Project-based PDF/JSON не затронуты (только `_get_company_details()` с fallback).
- Standalone PDF/JSON не затронуты.
- Все 130 тестов зелёные.

## Состояние после push
Рабочее дерево чистое, ветка отслеживает `origin/hermes/integrate-origin-master-20260423`.

Stage 8.4 полностью завершён. Stage 8.5.1 parser module реализован и запушен.
Следующий этап — Stage 8.5.2 import preview/apply routes (ожидает подтверждения пользователя).

### Stage 8.5.1–8.5.1b: Excel estimate parser module
- `webapp/excel_estimate_parser.py` — чистый парсер .xlsx (openpyxl, без pandas, без DB).
- `ColumnMapping`, `ParsedEstimateRow`, `ExcelEstimateParseResult` dataclasses.
- 6 определений колонок с русскими/английскими алиасами (name, unit, quantity, price, total, discounted_total).
- Auto-detect header row в первых 25 строках (реальные сметы: строка 14–15).
- Fallback A–E при отсутствии заголовка.
- Распознавание section/item строк, вычисление total = quantity × price.
- Поддержка discounted_total из колонок «Ст. со скидкой» / «Ск-ка»; fallback = total.
- Пропуск итоговых строк («Итого по разделу:», «Всего по смете»).
- Обработка merged cells, decimal с запятой, NBSP.
- `parsed_rows_to_estimate_items()` — мост к `EstimateItemInput`-совместимым dict.
- Макс 2MB, макс 500 строк.
- 62 теста, 117 регрессия — все зелёные.
