# Changelog — handoff_to_hermes

## 2026-05-29 Stage 8.9.6a — PDF copy protection
- Для PDF сметы включена ReportLab encryption/permissions через `pdfencrypt.StandardEncryption`.
- `userPassword=""` — PDF открывается без пароля.
- `canPrint=1`, `canCopy=0`, `canModify=0`, `canAnnotate=0` — печать разрешена, копирование/изменение/аннотации запрещены.
- `strength=128` — 128-bit encryption.
- `_make_encryption()` фабрика — создаёт fresh `StandardEncryption` на каждую генерацию (объект одноразовый, нельзя переиспользовать).
- `_OWNER_PASSWORD = "DEKORCRM_ESTIMATE_PDF_OWNER_2026"` — owner password не виден в UI.
- Защита в `webapp/estimate_pdf.py` (project estimate) и `webapp/standalone_estimate_files.py` (standalone draft + final).
- Encryption первой строкой в `add_watermark` callback: `canvas._doc.encrypt = _make_encryption()`.
- Новых зависимостей не добавлено — `pdfencrypt` входит в `reportlab`.
- 21 тест в `tests/test_estimate_pdf_protection.py`.
- Коммит: `4c6e355`.
- Live-проверка пройдена: пользователь подтвердил, что копирование заблокировано.
- Защита применяется только к новым/переформированным PDF; старые PDF нужно переформировать.
- Ограничение: не абсолютная криптографическая защита, ограничивает обычное копирование в стандартных PDF-просмотрщиках.

## 2026-05-29 Stage 8.9.5b — PDF estimate heading
- Добавлен заголовок **«Смета на выполнение отделочных работ»** в PDF сметы проекта.
- Заголовок: centered, bold (DejaVuSans-Bold), fontSize=9, между блоком реквизитов и таблицей.
- Spacer 2mm после заголовка перед таблицей.
- `webapp/estimate_pdf.py`: добавлен `heading_style` `ParagraphStyle("Heading", ...)` и `Paragraph("Смета на выполнение отделочных работ", heading_style)`.
- 6 тестов в `tests/test_estimate_pdf_heading.py`: presence, bold font, center alignment, position, spacer, font size.
- Коммит: `d087b49`.
- Live-проверка пройдена: заголовок отображается при свежей генерации PDF.
- Диагностика: кнопка «Скачать PDF» (`/documents/{id}/download?kind=pdf`) отдаёт ранее сохранённый файл; если PDF был создан до добавления заголовка, нужно нажать «Сформировать PDF» заново. Stage 8.9.5c не нужен.

## 2026-05-29 Stage 8.9.5a — Fix catalog item category saving
- Баг: изменение категории работы в прайс-листе визуально сохранялось, но после обновления страницы возвращалось обратно.
- Причина: `<form>` внутри `<tr>` — невалидный HTML, браузер репарентит форму, category не отправлялась.
- Исправление: убран `<form>` из `<tr>`, добавлен per-row AJAX save handler в JS.
- Backend: `update_catalog_item()` и `create_catalog_item()` сохраняют валидные категории из `CATEGORY_OPTIONS` напрямую.
- Route `catalog_item_update` возвращает `{"ok": True}` для AJAX-запросов (`X-Requested-With: XMLHttpRequest`).
- 28 новых тестов в `tests/test_catalog_category_update.py`.
- Live-проверка пройдена: категория сохраняется, название работы редактируется.
- Коммит: `ff559d2`.

## 2026-05-26 Stage 8.9.4n — Remove remaining red font from contract DOCX
- `_remove_red_colors(doc)` — финальная замена всех `w:color val="FF0000"/"ff0000"` на `000000`.
- Удаление `w:themeColor`, `w:themeTint`, `w:themeShade`.
- 6 новых тестов в классе `RemoveRedColorsTests`.
- Коммит: `773663d`.

## 2026-05-26 Stage 8.9.4m — Set contract replacement text color black
- `_normalize_replacement_colors()` — нормализация цвета подставленных данных: параграфы/ячейки с replacement values перекрашиваются в чёрный.
- `_normalize_run_color_to_black()` + `_normalize_run_color_in_element()` — XML-level color normalization.
- `w:color=000000`, удаление `themeColor/themeTint/themeShade`.
- Обработка скрытых runs (`rStyle="af2"`) через `_normalize_xml_paragraph()`.
- 9 новых тестов + `_find_xml_runs_containing` helper.
- Коммит: `72ca825`.

## 2026-05-26 Stage 8.9.4l — Disable proofing for contract working group text
- `w:noProof` добавлен в rPr нового run рабочей группы — отключает проверку орфографии/грамматики Word.
- Коммит: `dc6cae1`.

## 2026-05-26 Stage 8.9.4k — Remove hyperlink styling from contract working group text
- `w:u val="none"` явно отключает подчёркивание; нет `w:hyperlink`, нет `w:rStyle`.
- Коммит: `1633f7d`.

## 2026-05-26 Stage 8.9.4j — Set contract working group text color black
- Явный `w:color val="000000"` вместо `deepcopy(rPr)`.
- Коммит: `e94eb36`.

## 2026-05-26 Stage 8.9.4i — Prefix contract working group text
- "Рабочая группа: " автоматически добавляется, не дублируется.
- Коммит: `618f332`.

## 2026-05-26 Stage 8.9.4h — Fix contract working group text replacement
- `_replace_working_group_paragraph()` — paragraph-level replacement вместо placeholder-based.
- Template P115 содержит статическую WhatsApp-строку, не `[[PLACEHOLDER]]`.
- `_W_NS` вынесен в module-level constant.
- Коммит: `fd2d471`.

## 2026-05-26 Stage 8.9.4g — Add cache busting to contract DOCX download link
- `&_t={{ contract_document.updated_at }}` в ссылке скачивания DOCX.
- Коммит: `f24b2d2`.

## 2026-05-26 Stage 8.9.4f — Prevent cached document downloads
- Cache-Control: no-store, no-cache, must-revalidate + Pragma: no-cache + Expires: 0.
- Коммит: `c53f617`.

## 2026-05-26 Stage 8.9.4e — Fix contract DOCX customer data replacements
- `[[CUSTOMER_EMAIL]]` заменяется через `_replace_in_xml_text_nodes()` (fallback для hidden runs с `rStyle="af2"`).
- `_normalize_counterparty_type()`: Физлицо→Физическое лицо, ИП→ИП, ООО→Юридическое лицо ООО.
- `object_address` приоритет: settings → counterparty.work_address → project.address → project.project_name.
- Коммит: `80de1c3`.

## 2026-05-26 Stage 8.9.4c — Fix document download fetch_document import
- Исправлен `FetchDocument` import в `main.py`, вызвавший 500 на `/documents/{id}/download?kind=file`.
- Коммит: `3eab5ef`.

## 2026-05-26 Stage 8.9.4b — Add contract DOCX generation UI
- Кнопка «Сформировать DOCX договора» на странице `/projects/{id}/contract`.
- Ссылка «Скачать DOCX договора» после генерации.
- Баннер `created=contract-docx`.
- Коммит: `959d683`.

## 2026-05-26 Stage 8.9.4a — Implement DOCX contract generation service
- `webapp/contract_generator.py`: `build_contract_replacements()`, `replace_placeholders_in_docx()`, `generate_contract_docx()`.
- `python-docx==1.2.0` добавлен в requirements.txt.
- `POST /projects/{id}/contract/generate-docx` — генерация DOCX.
- 19 placeholder-полей + replacement logic.
- Двухпроходная замена: paragraph.runs → XML `w:t` nodes.
- Коммит: `b290592`.

## 2026-05-21 Stage 8.9.2b — Improve contract payment UX
- Платёжные строки: collapsible — показаны заполненные + минимум 2, остальные скрыты через `style="display:none"`.
- Кнопка «+ Добавить платёж» показывает следующую скрытую строку (максимум 7 платежей).
- Форматирование сумм через точки-разделители: 1000000 → 1.000.000 (`formatMoney`/`stripMoney` в inline JS).
- `focus` показывает raw число, `blur` форматирует, `submit` очищает разделители.
- Jinja `{% for i in range(1,8) %}` с `data-row` атрибутом для управления видимостью.
- 29 тестов, все зелёные. Live-проверка пользователем пройдена.
- Коммит: `6e41294`.

## 2026-05-21 Stage 8.9.2 — Contract settings page and draft contract document
- `/projects/{project_id}/contract` — страница настроек договора (GET отображает, POST сохраняет).
- `contract_settings_json` сохраняется в `projects.contract_settings_json` (существующая TEXT-колонка, JSON blob, совместима с desktop CRM.py).
- Document record создаётся/обновляется: `doc_type='Договор'`, `status='Черновик'`, `project_id` привязан.
- `fetch_contract_settings()`, `save_contract_settings()`, `create_or_update_contract_document()`, `get_project_estimate_total()` в `webapp/db.py`.
- `get_project_estimate_total()` — сумма `estimate_items.discounted_total` первой сметы проекта; возвращает `"0"` если сметы нет.
- Ссылка «Настройки договора» в `project_detail.html` (progress card + documents section).
- Шаблон `contract_settings.html`: данные проекта, данные контрагента, платёжные строки, inline JS.
- 22 теста (10 DB + 12 template/route), все зелёные.
- Коммит: `0ad9dd4`.

## 2026-05-21 Stage 8.9.1b — Counterparty list/detail/edit pages
- `/counterparties` — список контрагентов (ID, тип, имя, телефон, email, ИНН, действия).
- `/counterparties/{id}` — карточка контрагента со всеми 28 полями (основное, паспорт, реквизиты ООО/ИП, банк, директор/представитель, заметки).
- `/counterparties/{id}/edit` — форма редактирования 28 полей (GET pre-fill из БД, POST обновление с редиректом на карточку).
- `fetch_counterparty()`, `update_counterparty(**fields)` добавлены в `webapp/db.py`.
- `ensure_counterparties_updated_at()` — миграция `ALTER TABLE counterparties ADD COLUMN updated_at TEXT DEFAULT ''`.
- Ссылка «Контрагенты» в topbar `projects.html`.
- POST `/counterparties/new` редиректит на `/counterparties/{cp_id}` вместо `/projects?created=counterparty`.
- 404 для несуществующего контрагента (detail и edit).
- 34 теста (16 template/route + 18 DB), все зелёные.
- Live-проверка пройдена: список, карточка, редактирование — все работают.
- Коммит: `70b22b7`.

## 2026-05-21 Stage 8.9.1a — Extended counterparty creation fields for contracts
- `/counterparties/new` расширен с 9 до 28 полей: паспорт (серия/номер, кем выдан, код подразделения, дата рождения), адреса (регистрации, работ, юридический, почтовый, фактический), реквизиты (КПП, ОГРН, ОГРНИП), банк (наименование, БИК, расчётный счёт, корр. счёт), директор (ФИО, основание).
- `create_counterparty()` в `webapp/db.py` принимает все 28 полей.
- 8 DB-level тестов в `tests/test_counterparty_web.py`.
- Live-проверка: «Тест Договор Физлицо» (id=3), все расширенные поля сохранены.
- Коммит: `7e590dd`.

## 2026-05-20 Stage 8.8.1 — Fix hardcoded finance totals in project detail
- Верхние метрики и карточки баланса в `project_detail.html` теперь используют `project_finance_summary.income_label/expense_label/balance_label` вместо «0 руб.».
- Коммит: `f5beac7`.
- Live verification: проект 11 показывает реальные суммы (доход 50 000 ₽, расход 15 000 ₽, баланс 35 000 ₽).

## 2026-05-20 Stage 8.8 — Finance module integration verified
- Live-проверка на проекте 11: доход 50 000 ₽, расход 15 000 ₽, прибыль 35 000 ₽.
- `/finance`: доходы 60 000 ₽, расходы 15 000 ₽, баланс 45 000 ₽.
- Транзакции привязаны к проекту через `project_id`. Общая касса работает.

## 2026-05-20 Test suite fixes
- `test_estimate_repository.py`: 13/13 pass (ранее 9/13 из-за запуска против live DB).
- `test_standalone_estimate_routes.py`: 27/27 pass (ранее 25/27 из-за `company_id=None` в final-pdf тестах).
- Исправление: добавлен `company_id` в `_create_and_approve_estimate()` + mock `CompanyService`/`resolve_storage_path`.
- Коммит: `9069b9d`.

## 2026-05-20 Stage 8.7 — Carry customer and final PDF into project (закрыт)
- `customer_name` из standalone-сметы переносится в `projects.customer`, если `counterparty_id` отсутствует.
- `final_document_id` standalone-сметы привязывается к проекту через `documents.project_id`.
- Коммит: `4be399d`.
- Live verification: проект 11, заказчик «Заказчик Проект 8.7», Final PDF в документах проекта.

## 2026-05-20 Stage 8.6 — Create project from approved estimate (полностью закрыт)
- 8.6.1 ✅ Backend (`1a1c6af`): `POST /estimates/{id}/create-project` + service-метод, 6 route-тестов.
- 8.6.2 ✅ UI (`4772c09`): кнопка «Создать проект» / ссылка «Открыть проект» в approved-блоке, JS обработчик, JSONResponse. 24 UI-теста.
- 8.6.2b ✅ In-progress link (`bc58ade`): ссылка «Открыть проект» в in_progress-блоке. 25 UI-тестов.
- 8.6.3 ✅ Active status (`e597a50`): проект из approved сметы создаётся со статусом «В работе».
- Live verification: смета 881 → проект 9, смета 874 → проект 10, статус проекта «В работе». Ссылка «Открыть проект» работает.

## 2026-05-07 Stage 8.5.5 — Excel import UX polish
- Предупреждение «импорт добавляет строки» (alert-info) на странице import-excel.
- `confirm()` диалог: «Импорт добавит строки из preview к текущей смете. Продолжить?»
- Кнопка применять: дизейблится во время запроса, после успеха показывает «Импорт применён».
- Новый preview перезапускает кнопку (`disabled=false`, `_previewApplied=false`).
- 4 новых template-теста в `ImportExcelPageTemplateTests`.
- Визуальная полировка import_excel.html отложена до общего UI-audit этапа.
- Коммит: `e9392bb`.

## Stage 8.5 — Excel import (функционально закрыт)
- 8.5.1 ✅ Parser (`55293ce`) | 8.5.1b ✅ Real format (`0586e6e`) | 8.5.2 ✅ Routes (`e28872b`)
- 8.5.3 ✅ Live verify (`465aae8`) | 8.5.4 ✅ Button (`8c6f2a7`) | 8.5.4 fix ✅ Cleanup+PDF (`a9d24b0`)
- 8.5.4c ✅ Estimate# (`cb5b9b7`) | 8.5.4d ✅ Filter year (`54bf6a4`) | 8.5.5 ✅ UX polish (`e9392bb`)
- 92 parser теста, 22 import route теста, 18 UI тестов — все зелёные.

## 2026-05-07 Stage 8.5.4d — filter mixed signature year rows in Excel import
- `_looks_like_signature_or_trash()` расширена эвристикой: строки с годом (г./год) и punctuation/underscores/quotes после удаления года → trash.
- Фильтрует `"___" __________ 2026 год`, `____ __________ 2025 г.`, `«__________» ______ 2026 г.`.
- Защита от ложного срабатывания: строки с qty/price/total или нормальным текстом не фильтруются.
- 5 новых тестов (3 позитивных, 2 негативных). 92 теста парсера, все зелёные.
- Коммит: `54bf6a4`.

## 2026-05-07 Stage 8.5.4c — fix standalone draft estimate number generation
- `standalone_estimate_new_redirect()`: `estimate_number=""` → `f"draft-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"`.
- Предотвращает `UniqueViolation` на `idx_estimates_estimate_number` при наличии существующих draft с пустым номером.
- Добавлен `import uuid` и `from datetime import datetime, timezone`.
- Новый тест `test_two_consecutive_draft_estimates_have_unique_numbers`.
- Коммит: `cb5b9b7`.

## 2026-05-07 Stage 8.5.4 fix — excel import cleanup and PDF wrapping
- `_looks_like_signature_or_trash()` — фильтрует строки «Генеральный директор», «Печать», «М.П.», подчёркивания, год.
- `_looks_like_section()` — строки с name+total, но без qty/price/unit → section, не item.
- `_build_pdf_table()` — длинные имена переносятся через `Paragraph()`/`ParagraphStyle`.
- Возвращаемый тип `_build_pdf_table` изменён на `list[list[Any]]`.
- Коммит: `a9d24b0`.

## 2026-05-07 Stage 8.5.4 — UI integration Excel import button
- Кнопка «Импорт из Excel» (ghost-button) добавлена в `estimate-workflow-actions` редактора standalone-сметы.
- Видна только для draft-статуса. Non-draft — кнопка скрыта.
- Ссылка ведёт на `/estimates/{id}/import-excel`.
- Ссылка «Назад к редактору» уже была на странице import-excel.
- 3 новых template-теста: link present, inside draft block, absent in legacy.
- 97 тестов, 1 known false positive. Commit: `8c6f2a7`.

## 2026-05-07 Stage 8.5.3 — live/manual verification
- Draft standalone-смета ID=888 создана на crm198.ru.
- Preview: 3 раздела, 12 позиций корректно распознаны; итоговые строки пропущены; discounted_total из колонки «Ст. со скидкой».
- Apply: 15 строк добавлено через `append_items_to_estimate()`, redirect на редактор.
- Редактор и draft PDF работают после импорта.
- Негативные сценарии: invalid ID→404, non-xlsx→400, no file→400, sent→400.
- Баг: `import_excel.html` использовал `{% block content %}` вместо `{% block body %}` — исправлено.
- 79 тестов (18 import routes + 62 parser), 1 known false positive.
- Commit: `465aae8`.

## 2026-05-07 Stage 8.5.2 — excel import preview/apply routes
- `GET /estimates/{id}/import-excel` — страница загрузки (draft only).
- `POST /estimates/{id}/import-excel/preview` — парсинг .xlsx → JSON, без изменения БД.
- `POST /estimates/{id}/import-excel/apply` — приём JSON rows из preview, `append_items_to_estimate()`.
- Import forbidden для sent/approved/in_progress/rejected.
- File validation: .xlsx, max 2MB, valid openpyxl.
- `webapp/templates/import_excel.html` — форма + JS preview/apply.
- 18 route tests. Commit: `e28872b`.

## 2026-05-05 Stage 8.5.1b — parser adapted to real estimate format
- `HEADER_SCAN_ROWS`: 10 → 25 (реальные сметы: заголовок на строке 14–15).
- `discounted_total` колонка с алиасами (Ст. со скидкой, Ск-ка, со скидкой).
- `ColumnMapping.discounted_total` поле.
- `_looks_like_summary()` — пропуск «Итого по разделу», «Всего по смете».
- 9 новых тестов (LookalikeSummaryTests + RealFormatParseTests). Всего 62 теста.

## 2026-05-05 Stage 8.5.1 — excel estimate parser module
- `webapp/excel_estimate_parser.py`: `parse_estimate_xlsx()`, `resolve_estimate_columns()`, `parsed_rows_to_estimate_items()`.
- 53 теста, 117 регрессия — все зелёные.

## 2026-05-05 Stage 8.4 завершён — компании, реквизиты, печать/подпись, watermark, legacy fallback

### Stage 8.4.7 — legacy _get_company_details() DB fallback
- `_get_company_details(company_name)` в `estimate_pdf.py` сначала ищет компанию в DB (`CompanyRepository.get_company_by_short_name` → fallback по `legal_name`).
- При нахождении — строит dict `{title, details}` через `_company_to_details_dict()` из полей Company (ИНН/КПП, ОГРН/ОГРНИП, адрес, телефон, email, сайт). Пустые поля пропускаются.
- При любой ошибке — возвращает `_hardcoded_company_details()` (исходный hardcoded dict без изменений).
- Добавлены `_HARDCODED_COMPANY_DETAILS`, `_hardcoded_company_details()`, `_split_address()`, `_company_to_details_dict()`.
- 26 тестов в `tests/test_estimate_pdf_company_fallback.py`.
- Legacy project-based PDF визуально не сломан; standalone PDF не затронут.

### Stage 8.4.6d — watermark из companies.watermark_text
- `_resolve_watermark_text(company_name, company)` в `standalone_estimate_files.py`.
- `company.watermark_text` из DB приоритетнее hardcoded fallback.
- Final PDF watermark намеренно отключён (пустой callback).
- 7 новых тестов.

## 2026-05-05 Stage 8.4.6c — live verification пройдена
- **Live-проверка**: estimate_id=881, status=approved, company_id=2 (ИП Гордеев А.Н.), approved_version_id=743.
- stamp_path=`company-assets/2/stamp.png`, signature_path=`company-assets/2/signature.png` — оба PNG существуют на диске.
- Final PDF успешно отображает: реквизиты ИП Гордеев А.Н., реальная PNG-печать, реальная PNG-подпись, строку «Финальная согласованная версия: печать=да, подпись=да».
- Draft/sent PDF не затронуты. Legacy `estimate_pdf.py` не тронут. Project-based PDF/JSON не тронуты.
- 25 тестов `test_standalone_estimate_files` (включая 9 новых `StampSignaturePngTests`), 15 `test_standalone_workflow_ui`, 17 `test_company_api`, 16 `test_company_repository`, 12 `test_estimate_domain` — все зелёные.

## 2026-05-05 Stage 8.4.6b — final PDF stamp/signature checkboxes
- Добавлены чекбоксы `stamp_applied` / `signature_applied` в approved editor (только если `final_document_id` отсутствует).
- JS: `final-pdf` action считывает checkbox state и отправляет JSON body.
- 6 новых UI+JS тестов.

## 2026-05-05 Stage 8.4.6a — company details in final PDF
- Если у сметы `company_id` → блок реквизитов (ИНН, КПП, ОГРН, адрес, банк, подписант).
- Если `company_id` нет → fallback `Компания: {company_name}`.
- 5 новых тестов.

## 2026-05-05 Stage 8.4.5 — estimates.company_id FK
- `estimates.company_id BIGINT NULL REFERENCES companies(id) ON DELETE SET NULL`.
- `EstimateSummary`, `EstimateCreateInput`, `EstimateUpdateInput` — проброс `company_id`.
- 7 migration-тестов.

## 2026-05-05 Stages 8.4.1–8.4.4 — companies module + company settings + asset upload
- Таблица `companies`, seed ООО «Декорартстрой» (id=1) и ИП Гордеев А.Н. (id=2).
- `CompanyRepository`, `CompanyService`, 16 тестов.
- APIRouter `/settings/companies`: CRUD, upload stamp/signature PNG (validate content_type, extension, magic bytes, max 2MB), auth-gated serve.
- Templates `companies_list.html`, `company_detail.html`.
- Protected storage `/opt/dekorcrm/storage/company-assets/{company_id}/`.
- 17 тестов `test_company_api`.

## 2026-05-05 Stage 8.3.3 — live verification и bugfix
- Live-проверка полного UI workflow: создание сметы → шапка → раздел → 2 позиции → сохранить → отправить → согласовать → final PDF → скачать.
- Исправлен баг: `_load_payload()` в `standalone_estimate_api.py` вызывал `request.json()` при пустом body с `Content-Type: application/json`, что давало 500. Теперь оборачивает в try/except, возвращает `{}`.
- Добавлена защита тестов от live-БД: `tests/db_guard.py` — `guard_live_database()` блокирует destructive cleanup на database `dekorcrm`.
- 6 новых тестов `_load_payload` (пустое тело, malformed, array, no content-type, form data).
- 6 новых тестов `test_db_guard` (блокировка на live, пропуск на test, case-insensitive).
- Итого: 135 тестов, все зелёные; destructive-тесты блокируются на dekorcrm.

## 2026-05-04 Stage 8.3.3 — standalone workflow UI
- В standalone editor добавлены кнопки workflow по статусам: Отправить клиенту, Согласовать, Отклонить, Сформировать final PDF, Скачать final PDF, Скачать JSON.
- JS-обработчики `data-action` делают `fetch + reload`; legacy editor не затронут.
- 9 текстовых проверок шаблона в `tests/test_standalone_workflow_ui.py`; 129 тестов всего — все зелёные.
- Документация handoff обновлена.

## 2026-05-04 Stages 8.3.1–8.3.2b — final approved PDF и document linkage
- Final PDF строится из approved snapshot, а не из текущих живых данных.
- Маршруты final PDF: `POST /final-pdf`, `GET /download/final-pdf`.
- Final PDF привязан к `documents`, `estimate_documents`, `estimate_versions.pdf_document_id`, `estimates.final_document_id`.
- `documents.project_id` допускает NULL (миграция `20260503_documents_nullable_project_id.sql`).
- Workflow `draft → sent → approved → final PDF → download` проверен на live.

## 2026-05-04 Stage 8.2 — standalone draft PDF
- Standalone draft PDF формируется отдельно от legacy.
- Разделы, итоги, скидка, watermark для черновика; печать/подпись запрещены в draft.

## 2026-05-04 Stage 8.1 — standalone estimate status snapshots
- Исправлен порядок send/approve; snapshots содержат актуальный status.
- `approved_version_id` и `current_version_id` работают корректно.

## 2026-05-04 Stages 6–7 — standalone estimates registry and editor
- Создан реестр самостоятельных смет `/standalone-estimates`.
- Создание сметы без проекта и без контрагента.
- Редактор `/estimates/{id}/edit`; сохранение шапки, разделов, позиций; повторное открытие сохраняет данные.

## 2026-04-26 20:02 UTC
- Добавлен глобальный `base.html`: sticky header, логотип `Декорартстрой`, навигация, `+ Действие`, flash messages и единая модалка создания транзакции.
- Реализован модуль `/finance` со сквозной кассой: `transactions`, баланс = доходы − расходы, добавление транзакций из любого раздела.
- Таблица `transactions` использует `amount DECIMAL(12, 2)`, `status DEFAULT 'completed'`, `project_id ... ON DELETE SET NULL`, индекс `idx_transactions_project_id`.
- Карточка проекта `/projects/<id>` показывает `Финансы объекта`: только транзакции этого проекта и прибыль/ROI = доходы − расходы; модалка автоподставляет текущий проект.
- Добавлены `tests/test_finance_module.py`; проверено 24 unittest OK, `py_compile` OK, `dekorcrm-web` active, live smoke `/finance` и зеркалирование транзакции в проект с последующим удалением smoke-записи.
- Детали сохранены в `09_FINANCE_MODULE_NOTES.md`; секреты не сохранялись.

## 2026-04-26 18:49 UTC
- Реализован структурированный справочник работ `/catalog`: категории, CRUD, копирование, живой поиск, компактная таблица, sticky header/category rows.
- `catalog_items` расширен полем `category`; обеспечены `name UNIQUE` и миграция автокатегоризации существующих строк.
- Excel импорт обновлён: категории, тестовый `--limit`, миграция `--migrate-categories`, сравнение входящих строк с БД.
- Добавлен smart upload `/catalog/upload`: новые строки добавляются автоматически, конфликты по `name` выводятся на страницу разрешения с действиями применить/пропустить.
- Добавлены `tests/test_catalog_management.py` и расширены тесты импорта; проверено 17 unittest OK, `py_compile` OK, импорт 10 строк, миграция категорий, полный импорт 107 строк, smart upload smoke, `/catalog` 200 после рестарта `dekorcrm-web`.
- Детали сохранены в `08_CATALOG_IMPORT_NOTES.md`; секреты не сохранялись.

## 2026-04-24 21:49 UTC
- По скриншоту пользователя доработана карточка проекта `/projects/<id>`.
- Убрана верхняя строка с `Dekorartstroy CRM / Проект: ...`; в topbar оставлена только кнопка `На главную` и пользовательский блок.
- Убран правый блок быстрых действий возле заголовка проекта.
- Уменьшены крупные шрифты и отступы на странице карточки проекта.
- Карточка `1. Смета` теперь показывает `Статус сметы`; карточка `Контрагент` заменена на визуальный блок `Финансы`.
- Добавлен `tests/test_project_detail_template.py`; проверено 10 unittest OK, `py_compile` OK, `dekorcrm-web` active, authenticated smoke `/login`, `/projects/6`, `/projects/6/estimate` 200.

## 2026-04-24 21:26 UTC
- По просьбе пользователя заменён файл логотипа в topbar `/projects` на новый вариант без текстовой части (`webapp/static/img/crm198-logo.jpg`).
- Проверено: template regression test OK, `py_compile` OK, `dekorcrm-web` active, `/login` и `/projects` 200, статический логотип отдаётся как `image/jpeg`.

## 2026-04-24 21:19 UTC
- По новому скриншоту заменён левый текстовый бренд в topbar `/projects` на логотип `crm198.ru` (`webapp/static/img/crm198-logo.jpg`).
- Вместо верхних статистических карточек добавлен финансовый блок: `За сегодня`, `За месяц`, `Задолженность заказчиков`.
- Добавлена серверная функция `fetch_dashboard_finance()`: финансовый блок берёт суммы из сохранённых смет; прибыль пока `0 ₽` до отдельного учёта расходов/платежей.
- Расширен regression test `tests/test_projects_dashboard_template.py`.
- Проверено: 7 unittest OK, `py_compile` OK, `dekorcrm-web` active, authenticated smoke `/login`, `/projects`, `/projects/7/estimate` 200; на `/projects` есть логотип и finance strip, старых метрик нет.

## 2026-04-24 20:56 UTC
- По следующему скриншоту доработана страница `/projects`.
- Убран `Синхронизация OK` из sidebar.
- Sidebar `Мои объекты` теперь выводит все проекты, кроме `Завершен`, без лимита первых 6.
- Верхние основные кнопки выстроены в один центрированный ряд; `Сменить пароль` вынесен в правый пользовательский блок.
- Расширен `tests/test_projects_dashboard_template.py`; проверено 5 unittest, `py_compile`, restart `dekorcrm-web`, authenticated smoke `/login`, `/projects`, `/projects/7/estimate`.

## 2026-04-24 20:41 UTC
- По скриншоту пользователя доработана страница `Объекты и сметы` (`/projects`).
- Убран большой информационный баннер, sidebar-блок `Быстрые действия` и дублирующий блок `Выбранный объект`.
- Основные действия перенесены в верхнюю панель и визуально выделены: создание проекта/контрагента, смета, карточка проекта, финансы, прайс-лист.
- Добавлен regression test `tests/test_projects_dashboard_template.py`.
- Проверено: `unittest discover` через `/opt/dekorcrm/venv/bin/python`, `py_compile`, restart `dekorcrm-web`, authenticated smoke `/login`, `/projects`, `/projects/7/estimate`.

## 2026-04-24 20:01 UTC
- Усилен сервер `crm198.ru` без изменения root/SSH password login.
- Установлен и включён `fail2ban`, активен jail `sshd`.
- Добавлены базовые security headers в nginx для `crm198.ru`.
- Права `.env.web` изменены на `600 crmadmin:crmadmin`.
- Проверено: nginx/fail2ban/dekorcrm-web активны, `/login`, `/projects`, `/projects/7/estimate` возвращают 200 после авторизации.
- Root/SSH password hardening отложен до отдельной команды пользователя.

## 2026-04-24 19:40 UTC
- Создана серверная handoff-папка `handoff_to_hermes/` в `/opt/dekorcrm/app/CRM_OLD_BAD`.
- Добавлены очищенные проектные заметки без логинов, паролей и токенов.
- Зафиксирован текущий статус ветки `hermes/integrate-origin-master-20260423` и последних UX-правок редактора сметы.
