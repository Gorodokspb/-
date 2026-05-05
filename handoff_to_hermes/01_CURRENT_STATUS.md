# 01 — Current status

## Текущая серверная ветка
```text
hermes/integrate-origin-master-20260423
```

## Последние важные коммиты
```text
d09b1d2 Guard destructive tests from live database
631e42f Fix standalone workflow empty JSON payload
e8d525c Stage 8.3.3 standalone workflow UI
61aca5e Stage 8.3.2b link final PDF documents
de55c72 Stage 8.3.2a allow standalone documents
cc94701 Stage 8.3.1 standalone final PDF from approved snapshot
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

### Stage 8.4.6c: Real PNG stamp/signature in final PDF
- `_resolve_company_asset()` helper + `reportlab.platypus.Image` для реальных PNG.
- Stamp: 35mm × 35mm; Signature: 55mm × 20mm.
- Fallback текст «М.П.»/«Подпись» при отсутствии файла.
- API validation: `stamp_applied=True` без company/stamp_path → 400.
- 9 новых тестов.
- **Live-проверка пройдена**: estimate 881, company_id=2 (ИП Гордеев А.Н.), stamp.png + signature.png загружены. Final PDF содержит реквизиты, PNG-печать, PNG-подпись, строку «Финальная согласованная версия».

## Состояние после push
Рабочее дерево чистое, ветка отслеживает `origin/hermes/integrate-origin-master-20260423`.
