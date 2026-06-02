# 01 — Current status

## Текущая серверная ветка
```text
hermes/integrate-origin-master-20260423
```

## Последние важные коммиты
```text
5c2c558 Enable Secure flag on session cookie
990717d Add contract PDF generation and UI
4c6e355 Protect estimate PDFs from copying
d087b49 Add heading 'Смета на выполнение отделочных работ' to estimate PDF
a2f8f99 Document Stage 8.9.5 catalog category fix
ff559d2 Fix catalog item category saving
383faf1 Document Stage 8.9.4 DOCX contract completion
773663d Remove remaining red font from contract DOCX
72ca825 Set contract replacement text color black
dc6cae1 Disable proofing for contract working group text
1633f7d Remove hyperlink styling from contract working group text
e94eb36 Set contract working group text color black
618f332 Prefix contract working group text
fd2d471 Fix contract working group text replacement
f24b2d2 Add cache busting to contract DOCX download link
c53f617 Prevent cached document downloads
3eab5af Fix document download fetch_document import
80de1c3 Fix contract DOCX customer data replacements
959d683 Add contract DOCX generation UI
b290592 Implement DOCX contract generation service
6e41294 Stage 8.9.2b: improve contract payment inputs
0ad9dd4 Stage 8.9.2: add project contract settings page and draft contract document
56153b9 Document Stage 8.9.1 counterparty pages completion
70b22b7 Stage 8.9.1b: counterparty list/detail/edit pages, updated_at migration, route tests
7e590dd Stage 8.9.1a: extend counterparty creation fields for contracts
9069b9d Fix standalone estimate final PDF route tests
f5beac7 Stage 8.8.1: show real finance totals in project cards
4be399d Stage 8.7: carry estimate customer and final PDF into project
bc58ade Stage 8.6.2b: show project link for in-progress estimates
4772c09 Stage 8.6.2: add UI button for create project from approved estimate
1a1c6af Stage 8.6.1: add backend project creation from approved estimate
9759401 Document session 2026-05-20
f396737 Document session 2026-05-07
e9392bb Stage 8.5.5: polish Excel import UX
a2590e9 Document Stage 8.5.4 Excel import completion
54bf6a4 Stage 8.5.4d: filter mixed signature year rows in Excel import
cb5b9b7 Stage 8.5.4c: fix standalone draft estimate number generation
a9d24b0 Stage 8.5.4: fix excel import cleanup and PDF wrapping
8c6f2a7 Stage 8.5.4 add Excel import button to estimate editor
465aae8 Stage 8.5.3 fix import_excel.html template block name
e28872b Stage 8.5.2 excel estimate import preview/apply routes
0586e6e Stage 8.5.1b adapt parser to real estimate format
55293ce Stage 8.5.1 excel estimate parser module
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

**Все текущие задачи Stage 8.9 по DOCX/PDF/прайсу закрыты.**
Security diagnostics (8.10.0) выполнена — общий риск средний, критичных находок нет.
Следующие задачи не начинать без отдельного решения пользователя.

### Stage 8.10.0 — Security diagnostics (выполнена)

Общий уровень риска: **средний**. Критичных находок нет.

Findings:
| # | Severity | Что | Где |
|---|----------|-----|-----|
| F-1 | Medium | Нет CSRF-защиты | Все POST формы + routes |
| F-2 | Medium | Session cookie без `Secure` флага | `webapp/main.py:87-89` |
| F-3 | Low | Default fallback secrets `"change-me..."` | `webapp/config.py:68-72` |
| F-4 | Low | Owner password в markdown docs | handoff_to_hermes/*.md |
| F-5 | Low | Нет Content-Security-Policy | nginx config |
| F-6 | Info | Устаревшие пакеты | requirements.txt |
| F-7 | Low | SSH PasswordAuth/RootLogin enabled | sshd_config (осознанно) |

Что проверено: auth (✅ все приватные → 302→login), POST routes (✅ все require_auth), SQL injection (✅ parameterized queries), XSS (✅ |safe только для JSON scripts), debug mode (✅ reload=False), secrets in git (✅ .env.web в .gitignore), nginx (✅ HSTS/X-Frame/X-CT-O/Referrer/Permissions-Policy, HTTP→HTTPS, TLS 1.2+), storage (✅ не обслуживается nginx), documents (✅ auth-gated route).

### Roadmap после Stage 8.10.0

1. Stage 8.10.1 — Session cookie Secure flag (`https_only=True`)
2. Stage 8.10.2 — Mask owner password in docs
3. Stage 8.10.3 — CSP nginx diagnostics/header
4. Stage 8.10.4 — CSRF diagnostics/fix
5. Stage 8.10.5 — Default secrets hardening
6. Stage 8.11 — Full functional smoke test checklist
7. Stage 8.12 — UI inventory before redesign
8. Stage 9.0 — Visual/UI polish по разделам
9. Stage 9.x — Responsive/mobile/tablet adaptation

Stage 8.5.1–8.5.5 завершены. Live verification пройдена.
**Stage 8.5 Excel import — функционально закрыт.**

Stage 8.6.1–8.6.2b завершены. Live verification пройдена.
**Stage 8.6 Create project from approved estimate — функционально закрыт.**

Stage 8.7 завершён. Live verification пройдена.
**Stage 8.7 Carry customer and final PDF — закрыт.**

Stage 8.8 live-проверка финансов/кассы прошла.
**Stage 8.8 Finance module integration — закрыт.**

Stage 8.8.1 fix hardcoded finance metrics прошёл live-проверку.
**Stage 8.8.1 Real finance totals in project cards — закрыт.**

### Stage 8.9.4: DOCX contract generation (ЗАКРЫТ)

| Подэтап | Статус | Коммит |
|---------|--------|--------|
| 8.9.4a | ✅ DOCX generation service | `b290592` |
| 8.9.4b | ✅ Contract DOCX generation UI | `959d683` |
| 8.9.4c | ✅ Fix document download import | `3eab5ef` |
| 8.9.4e | ✅ Fix customer data replacements | `80de1c3` |
| 8.9.4f | ✅ Prevent cached document downloads | `c53f617` |
| 8.9.4g | ✅ Cache busting download link | `f24b2d2` |
| 8.9.4h | ✅ Fix working group text replacement | `fd2d471` |
| 8.9.4i | ✅ Prefix working group text | `618f332` |
| 8.9.4j | ✅ Working group text color black | `e94eb36` |
| 8.9.4k | ✅ Remove hyperlink styling | `1633f7d` |
| 8.9.4l | ✅ Disable proofing for working group | `dc6cae1` |
| 8.9.4m | ✅ Set replacement text color black | `72ca825` |
| 8.9.4n | ✅ Remove remaining red font | `773663d` |

Ключевые файлы:
- `webapp/contract_generator.py` — DOCX generation: `build_contract_replacements`, `replace_placeholders_in_docx`, `generate_contract_docx`, `_replace_in_xml_text_nodes`, `_normalize_counterparty_type`, `_replace_working_group_paragraph`, `_normalize_replacement_colors`, `_remove_red_colors`, `_build_communications_block`, `_W_NS`
- `webapp/main.py` — routes: POST `/projects/{id}/contract/generate-docx`, GET `/documents/{id}/download` with Cache-Control headers
- `webapp/db.py` — `fetch_contract_settings()`, `save_contract_settings()`, `create_or_update_contract_document()`, `update_document_file_path()`, counterparty CRUD
- `webapp/templates/contract_settings.html` — contract settings page with download link (cache-busting `&_t={{ updated_at }}`)
- `webapp/storage.py` — `resolve_storage_path()`, `sanitize_filename()`
- `requirements.txt` — `python-docx==1.2.0`
- `tests/test_contract_generator.py` — 64 tests (unit + integration)
- `tests/test_contract_settings.py` — 21 tests (template/route + DB)
- `contract_template_physical.docx` — 19 placeholders + static WhatsApp text in P115, NOT MODIFIED

Live-проверка на project 11: DOCX генерируется, скачивается, данные заказчика корректны, email подставлен, адрес объекта корректен, рабочая группа из CRM, цвет шрифта чёрный, красных элементов нет.

Routes:
- `POST /projects/{project_id}/contract/generate-docx` — generate and download DOCX
- `GET /documents/{document_id}/download?kind=file&_t={updated_at}` — download with cache-busting

### Stage 8.9.5a: Fix catalog item category saving (ЗАКРЫТ)

- Баг: изменение категории работы в прайс-листе визуально сохранялось, но после обновления страницы возвращалось обратно.
- Причина: `<form>` внутри `<tr>` — невалидный HTML, браузер репарентит форму, category не отправлялась.
- Исправление: убран `<form>` из `<tr>`, добавлен per-row AJAX save через JS.
- Кнопка «Сохранить» собирает `name/unit/price/category` из текущей строки, отправляет `FormData` POST.
- Backend: `update_catalog_item()` и `create_catalog_item()` сохраняют валидные категории из `CATEGORY_OPTIONS` напрямую, `normalize_category` используется только при пустой/невалидной категории.
- Route `catalog_item_update` возвращает `{"ok": True}` для AJAX-запросов.
- Live-проверка пройдена: категория сохраняется корректно, название работы редактируется.
- Коммит: `ff559d2`.
- Файлы: `webapp/templates/catalog.html`, `webapp/static/app.js`, `webapp/db.py`, `webapp/main.py`, `tests/test_catalog_category_update.py` (28 tests).

### Stage 8.9.5b: PDF estimate heading (ЗАКРЫТ)

- Добавлен заголовок **«Смета на выполнение отделочных работ»** в PDF сметы проекта.
- Заголовок: centered, bold (DejaVuSans-Bold), fontSize=9, расположен между блоком реквизитов и таблицей сметы.
- Spacer 2mm после заголовка перед таблицей.
- `webapp/estimate_pdf.py`: добавлен `heading_style` и `Paragraph("Смета на выполнение отделочных работ", heading_style)` в `generate_estimate_pdf()`.
- 6 новых тестов в `tests/test_estimate_pdf_heading.py`.
- Коммит: `d087b49`.
- Live-проверка пройдена: заголовок отображается при свежей генерации PDF.
- **Уточнение**: кнопка «Скачать PDF» (`/documents/{id}/download?kind=pdf`) отдаёт ранее сохранённый файл; если PDF был сформирован до добавления заголовка, нужно нажать «Сформировать PDF» заново, после чего «Скачать PDF» отдаст обновлённый файл. Stage 8.9.5c не нужен — проблема была не в генераторе, а в скачивании старого файла.

### Stage 8.9.6a: PDF copy protection (ЗАКРЫТ)

- Для PDF сметы включена ReportLab encryption/permissions через `pdfencrypt.StandardEncryption`.
- `userPassword=""` — PDF открывается без пароля.
- `canPrint=1` — печать разрешена.
- `canCopy=0`, `canModify=0`, `canAnnotate=0` — копирование, изменение, аннотации запрещены в стандартных PDF-просмотрщиках.
- `strength=128` — 128-bit encryption.
- `_make_encryption()` — фабрика, создаёт fresh `StandardEncryption` на каждую генерацию (объект одноразовый).
- `_OWNER_PASSWORD = "DEKORCRM_ESTIMATE_PDF_OWNER_***"` — owner password не виден в UI (значение намеренно замаскировано в docs).
- Защита применена в `webapp/estimate_pdf.py` (project estimate) и `webapp/standalone_estimate_files.py` (standalone draft + final approved).
- Encryption устанавливается первой строкой `add_watermark` callback: `canvas._doc.encrypt = _make_encryption()`.
- Новых зависимостей не добавлено — `pdfencrypt` входит в `reportlab`.
- 21 тест в `tests/test_estimate_pdf_protection.py`.
- Коммит: `4c6e355`.
- Live-проверка пройдена: пользователь подтвердил, что копирование текста из PDF заблокировано.
- **Уточнение**: защита применяется только к новым/переформированным PDF; старые PDF, созданные до Stage 8.9.6a, останутся без защиты, пока их заново не сформировать.
- **Ограничение**: PDF permissions/encryption не является абсолютной криптографической защитой от продвинутого обхода, но ограничивает обычное копирование в стандартных PDF-просмотрщиках (Adobe Reader и др.).

### Stage 8.9.7: Contract PDF generation via LibreOffice (ЗАКРЫТ)

| Подэтап | Статус | Описание | Коммит |
|---------|--------|----------|--------|
| 8.9.7a | ✅ LibreOffice installed | `libreoffice-writer` + `fonts-liberation`, `/usr/bin/soffice` 24.2.7.2 | — |
| 8.9.7b | ✅ Backend PDF generation | `generate_contract_pdf()`, `POST /projects/{id}/contract/generate-pdf`, `update_document_pdf_path` | `990717d` |
| 8.9.7c | ✅ UI buttons | «Сформировать PDF договора», «Скачать PDF договора», banner | `990717d` |
| 8.9.7d | ✅ Fix LibreOffice URI timeout | Двойной `file://` в `-env:UserInstallation`, добавлены `--nodefault --nofirststartwizard --nolockcheck`, timeout 30→60 сек | `5ac15f9` |

Ключевые детали:
- `generate_contract_pdf()` сначала вызывает `generate_contract_docx()`, затем конвертирует DOCX→PDF через `soffice --headless`.
- Уникальный `UserInstallation` profile per invocation через `tempfile.TemporaryDirectory` + `Path.as_uri()`.
- `_build_soffice_cmd()` формирует команду: soffice + `-env:UserInstallation={uri}` + `--headless --norestore --nodefault --nofirststartwizard --nolockcheck --convert-to pdf --outdir {dir} {docx}`.
- `_CONVERSION_TIMEOUT = 60` секунд.
- `_find_soffice()` ищет `soffice` затем `libreoffice` через `shutil.which()`.
- PDF сохраняется в `documents.pdf_path`, скачивается через `GET /documents/{id}/download?kind=pdf`.
- 23 теста в `tests/test_contract_pdf_generation.py`.
- Live-проверка проект 11: PDF 6 страниц, кириллица корректна, данные заказчика/объекта/рабочей группы на месте, реквизиты и подписи на последней странице.
- Пользователь подтвердил: «По моему всё хорошо»

Ключевые файлы:
- `webapp/contract_generator.py` — `generate_contract_pdf()`, `_find_soffice()`, `_build_soffice_cmd()`, `_CONVERSION_TIMEOUT`
- `webapp/db.py` — `update_document_pdf_path()`
- `webapp/main.py` — `POST /projects/{id}/contract/generate-pdf` route, `pdf_created` context
- `webapp/templates/contract_settings.html` — PDF button, download link, success banner
- `tests/test_contract_pdf_generation.py` — 23 тестов

### Stage 8.9.1a: Extended counterparty creation fields (закрыт)
- `/counterparties/new` теперь принимает 28 полей (было 9): паспорт, адреса, реквизиты, банк, директор.
- `create_counterparty()` расширен — все 28 полей сохраняются в БД.
- Live-проверка: «Тест Договор Физлицо» (id=3), все расширенные поля сохранены.
- Коммит: `7e590dd`.

### Stage 8.9.1b: Counterparty list/detail/edit pages (закрыт)
- `/counterparties` — список контрагентов (ID, тип, имя, телефон, email, ИНН, действия).
- `/counterparties/{id}` — карточка со всеми 28 полями.
- `/counterparties/{id}/edit` — форма редактирования всех 28 полей.
- `fetch_counterparty()`, `update_counterparty(**fields)` в db.py.
- `ensure_counterparties_updated_at()` — миграция `updated_at TEXT DEFAULT ''`.
- Ссылка «Контрагенты» в topbar. POST редиректит на detail.
- 404 для несуществующего контрагента.
- 34 теста (16 template/route + 18 DB), все зелёные.
- Live-проверка пройдена.
- Коммит: `70b22b7`.

### Stage 8.9.1 — итог (статус: закрыт)
| Подэтап | Статус | Коммит |
|---------|--------|--------|
| 8.9.1a | ✅ Extended creation fields | `7e590dd` |
| 8.9.1b | ✅ List/detail/edit pages | `70b22b7` |

Данные контрагента для генерации договора теперь доступны через web: ФИО, паспорт, адрес, реквизиты, банк, директор.

### Stage 8.9.2: Contract settings page and draft contract document (закрыт)

- `/projects/{project_id}/contract` — страница настроек договора (GET отображает, POST сохраняет).
- `contract_settings_json` сохраняется в `projects.contract_settings_json` (существующая TEXT-колонка, JSON blob).
- Document record создаётся/обновляется: `doc_type='Договор'`, `status='Черновик'`, `project_id` привязан.
- `fetch_contract_settings()`, `save_contract_settings()`, `create_or_update_contract_document()`, `get_project_estimate_total()` в `webapp/db.py`.
- Ссылка «Настройки договора» в `project_detail.html` (progress card + documents section).
- 22 теста (10 DB + 12 template/route), все зелёные.
- Коммит: `0ad9dd4`.

### Stage 8.9.2b: Improve contract payment UX (закрыт)

- Платёжные строки: collapsible rows (показаны заполненные + минимум 2, остальные скрыты).
- Кнопка «+ Добавить платёж» показывает следующую скрытую строку (максимум 7 платежей).
- Форматирование сумм через точки: 1000000 → 1.000.000 (`formatMoney`/`stripMoney` в inline JS).
- `focus` показывает raw число, `blur` форматирует, `submit` очищает разделители.
- 29 тестов, все зелёные.
- Live-проверка пользователем пройдена: всё работает.
- Коммит: `6e41294`.

### Stage 8.9.2 — итог (статус: закрыт)
| Подэтап | Статус | Коммит |
|---------|--------|--------|
| 8.9.2 | ✅ Contract settings page + draft document | `0ad9dd4` |
| 8.9.2b | ✅ Payment UX (collapsible, formatting) | `6e41294` |

DOCX/PDF generation не делалась в Stage 8.9.2/8.9.2b; перед Stage 8.9.3 нужна отдельная диагностика и отдельное подтверждение пользователя.

Test suite fixes: test_estimate_repository.py 13/13, test_standalone_estimate_routes.py 27/27.

Визуальная полировка import_excel.html отложена до общего UI-аудита/UI-polish этапа
после завершения работоспособности всех ключевых функций CRM.

### Stage 8.6.1: Backend create project from approved estimate (выполнено)
- `StandaloneEstimateService.create_project_from_estimate()` — service-метод.
- Route `POST /estimates/{id}/create-project` — auth-gated, только approved.
- Создаёт проект через legacy `create_project()`, линкует `estimates.project_id`.
- Переводит смету в `in_progress`.
- 6 route-тестов в `tests/test_standalone_estimate_create_project.py`.
- Коммит: `1a1c6af`.

### Stage 8.6.2: UI button for create project (выполнено)
- Роут адаптирован под AJAX: `RedirectResponse` → `JSONResponse({"redirect_url": ...})`.
- Кнопка «Создать проект» в approved-блоке (когда `project_id` пусто).
- Ссылка «Открыть проект» в approved-блоке (когда `project_id` есть).
- JS-обработчик `create-project` с redirect на `/projects/{id}`.
- 6 новых UI-тестов (24 всего в workflow suite).
- Коммит: `4772c09`.

### Stage 8.6.2b: Show project link for in-progress estimates (выполнено)
- Ссылка «Открыть проект» добавлена в `in_progress`-блок (когда `project_id` есть).
- После создания проекта смета переходит в `in_progress` → ссылка сохраняется.
- 1 новый UI-тест (25 всего в workflow suite).
- Коммит: `bc58ade`.

### Stage 8.6.3: Project status set to «В работе» (выполнено)
- Проект, созданный из approved standalone-сметы, получает статус «В работе» (было «Черновик»).
- 1 строка кода + 1 строка в тесте.
- Коммит: `e597a50`.

### Stage 8.6.3 live verification (итого)
- Смета 874 (approved, без project_id) → кнопка «Создать проект».
- Создан проект 10, статус проекта: «В работе».
- На `project_view.html` «Статус сметы: Черновик» — legacy project-based estimate, не ошибка Stage 8.6.3.
- Статус самого проекта корректный: «В работе».

### Stage 8.6 — итого (статус: полностью закрыт)
| Подэтап | Статус | Коммит |
|---------|--------|--------|
| 8.6.1 | ✅ Backend | `1a1c6af` |
| 8.6.2 | ✅ UI | `4772c09` |
| 8.6.2b | ✅ In-progress link | `bc58ade` |
| 8.6.3 | ✅ Active status | `e597a50` |

### Stage 8.7: Carry customer and final PDF into project (выполнено)
- `customer_name` из standalone-сметы переносится в `projects.customer`, если `counterparty_id` отсутствует.
- `final_document_id` standalone-сметы привязывается к проекту через `documents.project_id`.
- Коммит: `4be399d`.

### Stage 8.7 live verification (итого)
- Создан проект 11.
- Статус проекта: «В работе».
- Заказчик в проекте: «Заказчик Проект 8.7».
- В проекте отображается 1 документ (Final PDF).
- Итог workflow: approved standalone-смета → create project → customer перенесён → final PDF привязан → проект полноценный.

### Stage 8.7 — итого (статус: закрыт)
| Подэтап | Статус | Коммит |
|---------|--------|--------|
| 8.7 | ✅ Customer + documents | `4be399d` |

### Stage 8.8: Finance module integration (выполнено)
- Live-проверка транзакций и кассы на проекте 11.
- Доход проекта: 50 000 ₽, расход: 15 000 ₽, прибыль: 35 000 ₽.
- `/finance`: доходы 60 000 ₽, расходы 15 000 ₽, баланс 45 000 ₽.
- Транзакции привязаны к проекту через `project_id`.
- Общая касса работает корректно.

### Stage 8.8 live verification (итого)
- Проект 11: доход 50 000 ₽, расход 15 000 ₽, прибыль 35 000 ₽.
- `/finance` баланс: 45 000 ₽.
- Транзакции привязаны к проекту.

### Stage 8.8.1: Fix hardcoded finance totals in project detail (выполнено)
- Верхние метрики и нижние карточки баланса в `project_detail.html` теперь используют `project_finance_summary.income_label/expense_label/balance_label` вместо захардкоженных «0 руб.».
- Коммит: `f5beac7`.

### Stage 8.8.1 live verification (итого)
- Проект 11: карточки показывают реальные суммы (доход 50 000 ₽, расход 15 000 ₽, баланс 35 000 ₽).
- Верхние метрики корректны.

### Stage 8.8/8.8.1 — итого (статус: закрыт)
| Подэтап | Статус | Коммит |
|---------|--------|--------|
| 8.8 | ✅ Finance integration | — |
| 8.8.1 | ✅ Real totals | `f5beac7` |

### Test suite fixes (выполнено)
- `test_estimate_repository.py`: 13/13 pass (было 9/13 — исправлено через правильный DSN для test DB).
- `test_standalone_estimate_routes.py`: 27/27 pass (было 25/27 — исправлены 2 final-pdf теста).
- Исправление: добавлен `company_id` в `_create_and_approve_estimate()` + mock `CompanyService`/`resolve_storage_path` в тестах `test_final_pdf_created_after_approval` и `test_final_pdf_signed_creates_signed_pdf_document_kind`.
- Коммит: `9069b9d`.

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

### Stage 8.5.2: Excel import preview/apply routes
- `GET /estimates/{id}/import-excel` — страница загрузки (draft only, auth required).
- `POST /estimates/{id}/import-excel/preview` — парсинг .xlsx → JSON (rows, sections_count, items_count, diagnostics); БД не меняется.
- `POST /estimates/{id}/import-excel/apply` — приём JSON `rows` из preview, валидация, `append_items_to_estimate()` (не удаляет существующие строки).
- Import forbidden для sent/approved/in_progress/rejected.
- File validation: .xlsx extension, max 2MB, valid openpyxl parse.
- `webapp/templates/import_excel.html` — форма загрузки + JS preview/apply.
- 18 route tests: preview, apply, status guards, auth, legacy untouched.

### Stage 8.5.3: Live/manual verification
- Draft standalone-смета ID=888 создана на crm198.ru.
- Preview: корректно распознал 3 раздела, 12 позиций; итоговые строки пропущены; мусор не попал; discounted_total корректен.
- Apply: 15 строк добавлено, redirect на редактор.
- Редактор: все строки отображаются корректно (name, unit, qty, price, total, discounted_total).
- Draft PDF после импорта сформирован без ошибки (50KB).
- Негативные сценарии: invalid ID→404, non-xlsx→400, no file→400, sent estimate→400.
- Исправлен баг: `import_excel.html` использовал `{% block content %}` вместо `{% block body %}` (base.html использует `body`).
- Тесты: 79 passed (18 import routes + 62 parser), 1 known false positive.
- Логи: чисто, нет traceback/500.

### Stage 8.5.4: UI integration Excel import button
- Кнопка «Импорт из Excel» (ghost-button) добавлена в `estimate-workflow-actions` редактора standalone-сметы.
- Видна только для draft (`{% if estimate.status.value == 'draft' %}`).
- Ссылка ведёт на `/estimates/{id}/import-excel`.
- Non-draft-сметы не показывают кнопку.
- Ссылка «Назад к редактору» на странице import-excel уже была.
- 3 новых template-теста: import link present, inside draft block, absent in legacy.
- Тесты: 97 passed, 1 known false positive.
- Commit: `8c6f2a7`.

### Stage 8.5.4 fix: Excel import cleanup + PDF wrapping
- `_looks_like_signature_or_trash()` — фильтрует строки «Генеральный директор», «Печать», «М.П.», подчёркивания, годовые строки.
- `_looks_like_section()` — строки с name+total, но без qty/price/unit, классифицируются как section, не item.
- `_build_pdf_table()` — длинные имена в колонке «Наименование» переносятся через `Paragraph()`/`ParagraphStyle`.
- `_build_pdf_table` возвращает `list[list[Any]]` вместо `list[list[str]]`.
- Коммит: `a9d24b0`.

### Stage 8.5.4c: Fix standalone draft estimate number generation
- `standalone_estimate_new_redirect()` заменён `estimate_number=""` на `f"draft-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"`.
- Предотвращает `UniqueViolation` на `idx_estimates_estimate_number` при наличии других draft с пустым номером.
- Добавлен тест `test_two_consecutive_draft_estimates_have_unique_numbers`.
- Коммит: `cb5b9b7`.

### Stage 8.5.4d: Filter mixed signature year rows in Excel import
- `_looks_like_signature_or_trash()` расширена новой эвристикой: строки с годом (г./год) и только punctuation/underscores/quotes после удаления года → trash.
- Фильтрует `"___" __________ 2026 год`, `____ __________ 2025 г.`, `«__________» ______ 2026 г.`.
- Защита от ложного срабатывания: строки с qty/price/total или с нормальным текстовым названием не фильтруются.
- 5 новых тестов (3 позитивных, 2 негативных). Всего 92 теста парсера.
- Коммит: `54bf6a4`.

### Stage 8.5.4 live verification (итого)
- Новая draft-смета создана через `/standalone-estimates/new` (после fix 8.5.4c).
- Excel-импорт применён: разделы, позиции, discounted_total корректны.
- Мусорные строки (подписи, печати, подчёркивания, годовые строки вида `"___" __________ 2026 год`) больше не попадают в редактор и PDF.
- Длинные названия переносятся в PDF.
- Скидка: поле «Скидка, %» находится в sidebar редактора — дублирование внизу не планируется.

### Stage 8.5.5: Excel import UX polish
- Предупреждение «импорт добавляет строки, а не заменяет существующие» на странице import-excel.
- `confirm()` диалог перед apply.
- Кнопка блокируется после успешного применения (защита от повторного apply, UX-level).
- Кнопка перезапускается при новом preview.
- 4 новых template-теста.
- Коммит: `e9392bb`.
- Визуальная полировка import_excel.html отложена до общего UI-audit этапа.

### Stage 8.5 — итого (статус: функционально закрыт)
| Подэтап | Статус | Коммит |
|---------|--------|--------|
| 8.5.1 | ✅ Parser | `55293ce` |
| 8.5.1b | ✅ Real format | `0586e6e` |
| 8.5.2 | ✅ Routes | `e28872b` |
| 8.5.3 | ✅ Live verify | `465aae8` |
| 8.5.4 | ✅ Button | `8c6f2a7` |
| 8.5.4 fix | ✅ Cleanup+PDF | `a9d24b0` |
| 8.5.4c | ✅ Estimate# | `cb5b9b7` |
| 8.5.4d | ✅ Filter year | `54bf6a4` |
| 8.5.5 | ✅ UX polish | `e9392bb` |
