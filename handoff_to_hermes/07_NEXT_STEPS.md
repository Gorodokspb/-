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

## Stage 8.9.6a: PDF copy protection ✅ ЗАВЕРШЁН

### 8.9.6a ✅ Protect estimate PDFs from copying (выполнено)
- ReportLab `pdfencrypt.StandardEncryption` — 128-bit encryption.
- `userPassword=""` — PDF открывается без пароля.
- `canPrint=1`, `canCopy=0`, `canModify=0`, `canAnnotate=0`.
- `_make_encryption()` фабрика (fresh instance на каждую генерацию).
- Project estimate PDF + standalone draft/final — все защищены.
- Encryption в `add_watermark` callback: `canvas._doc.encrypt = _make_encryption()`.
- Новых зависимостей нет — `pdfencrypt` в составе `reportlab`.
- 21 тест в `tests/test_estimate_pdf_protection.py`.
- Live-проверка пройдена: копирование текста из PDF заблокировано.
- Коммит: `4c6e355`.
- **Важно**: защита применяется только к новым/переформированным PDF; старые PDF нужно переформировать.
- **Ограничение**: не является абсолютной криптографической защитой, ограничивает обычное копирование в стандартных PDF-просмотрщиках.

## Stage 8.9.5b: PDF estimate heading ✅ ЗАВЕРШЁН

### 8.9.5b ✅ Add heading «Смета на выполнение отделочных работ» (выполнено)
- Заголовок добавлен в `generate_estimate_pdf()` (centered bold, fontSize=9).
- Spacer 2mm между блоком реквизитов и таблицей.
- 6 тестов в `tests/test_estimate_pdf_heading.py`.
- Live-проверка пройдена: заголовок отображается при свежей генерации PDF.
- Коммит: `d087b49`.
- **Важно**: кнопка «Скачать PDF» отдаёт ранее сохранённый файл. Если PDF был создан до добавления заголовка, нужно нажать «Сформировать PDF» заново.

## Stage 8.9.5a: Fix catalog item category saving ✅ ЗАВЕРШЁН

### 8.9.5a ✅ Fix catalog category persistence (выполнено)
- Убран невалидный `<form>` из `<tr>` в `catalog.html`.
- Per-row AJAX save: кнопка «Сохранить» отправляет `FormData` на `POST /catalog/items/{id}`.
- Backend `update_catalog_item()` и `create_catalog_item()` сохраняют валидные категории напрямую без `normalize_category`.
- Route `catalog_item_update` возвращает `{"ok": True}` для AJAX.
- 28 новых тестов в `tests/test_catalog_category_update.py`.
- Live-проверка пройдена: категория сохраняется, название редактируется.
- Коммит: `ff559d2`.

## Stage 8.9.4 ✅ Полностью закрыт

### 8.9.4a ✅ DOCX generation service (выполнено)
- `webapp/contract_generator.py`: `build_contract_replacements()`, `replace_placeholders_in_docx()`, `generate_contract_docx()`.
- `python-docx==1.2.0` добавлен в requirements.txt.
- `POST /projects/{id}/contract/generate-docx` — генерация и скачивание DOCX.
- 19 placeholder-полей + replacement logic.
- Двухпроходная замена: paragraph.runs → XML `w:t` nodes.
- Коммит: `b290592`.

### 8.9.4b ✅ Contract DOCX generation UI (выполнено)
- Кнопка «Сформировать DOCX договора» на странице настроек договора.
- Ссылка «Скачать DOCX договора» после генерации.
- Баннер `created=contract-docx`.
- Коммит: `959d683`.

### 8.9.4c ✅ Fix document download (выполнено)
- Исправлена ошибка 500: `fetch_document` import отсутствовал.
- Коммит: `3eab5ef`.

### 8.9.4e ✅ Fix contract DOCX customer data replacements (выполнено)
- `[[CUSTOMER_EMAIL]]` заменяется через `_replace_in_xml_text_nodes()` (hidden `rStyle="af2"`).
- `_normalize_counterparty_type()`: Физлицо→Физическое лицо, ИП→ИП, ООО→Юридическое лицо ООО.
- `object_address` приоритет: settings → counterparty.work_address → project.address → project.project_name.
- Коммит: `80de1c3`.

### 8.9.4f ✅ Prevent cached document downloads (выполнено)
- Cache-Control: no-store, no-cache, must-revalidate + Pragma: no-cache + Expires: 0.
- Коммит: `c53f617`.

### 8.9.4g ✅ Cache busting download link (выполнено)
- `&_t={{ contract_document.updated_at }}` в ссылке скачивания.
- Коммит: `f24b2d2`.

### 8.9.4h ✅ Fix working group text replacement (выполнено)
- Template P115 содержит статическую WhatsApp-строку, не placeholder.
- `_replace_working_group_paragraph()` — paragraph-level replacement.
- Коммит: `fd2d471`.

### 8.9.4i ✅ Prefix contract working group text (выполнено)
- Префикс "Рабочая группа: " добавляется автоматически, не дублируется.
- Коммит: `618f332`.

### 8.9.4j–8.9.4l ✅ Working group text styling (выполнено)
- `w:color=000000`, `w:u=none`, `w:rFonts` Times New Roman, `w:sz=24`, no `w:hyperlink`, no `w:rStyle`, `w:noProof`.
- Коммиты: `e94eb36`, `1633f7d`, `dc6cae1`.

### 8.9.4m ✅ Set contract replacement text color black (выполнено)
- `_normalize_replacement_colors()` — нормализация цвета подставленных данных.
- `_normalize_run_color_to_black()` + `_normalize_run_color_in_element()` — `w:color=000000`, удаление themeColor/themeTint/themeShade.
- Коммит: `72ca825`.

### 8.9.4n ✅ Remove remaining red font from contract DOCX (выполнено)
- `_remove_red_colors()` — финальная замена всех `w:color val="FF0000"/"ff0000"` на `000000`.
- Удаление `w:themeColor`, `w:themeTint`, `w:themeShade`.
- Коммит: `773663d`.

### Live verification 8.9.4 ✅
- Project 11: DOCX генерируется, скачивается, данные корректны.
- Красных элементов нет, все подставленные данные чёрным шрифтом.
- Working group text: "Рабочая группа: ..." чёрным, без hyperlink, без проверки орфографии.

## Stage 8.9.4 ✅ Полностью закрыт

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

DOCX/PDF generation: DOCX contract generation завершён (Stage 8.9.4). PDF conversion — следующий отдельный этап только после отдельного подтверждения пользователя.

## Backlog: обнаруженные задачи (НЕ начинать без подтверждения)

### A. PDF сметы — заголовок ✅ FIXED
Исправлено в Stage 8.9.5b. Заголовок «Смета на выполнение отделочных работ» добавлен по центру перед таблицей. Уточнение: «Скачать PDF» отдаёт ранее сохранённый файл; для обновления нужно нажать «Сформировать PDF» заново.

### B. Прайс-лист — категория не сохранялась ✅ FIXED
Исправлено в Stage 8.9.5a. Причина: невалидный HTML (`<form>` внутри `<tr>`). Fix: per-row AJAX save + backend preserves valid categories.

### C. PDF сметы — защита от копирования ✅ FIXED
Исправлено в Stage 8.9.6a. ReportLab `pdfencrypt.StandardEncryption` с 128-bit encryption. `canCopy=0`, `canModify=0`, `canAnnotate=0`, `canPrint=1`. PDF открывается без пароля. Защита не абсолютная, но ограничивает обычное копирование в стандартных просмотрщиках.

### D. PDF conversion договора через LibreOffice headless ✅ FIXED
Реализовано в Stage 8.9.7. LibreOffice 24.2.7.2 установлен. `generate_contract_pdf()` конвертирует DOCX→PDF через `soffice --headless`. Уникальный UserInstallation profile per invocation. Timeout 60 сек. Live-проверка проект 11 пройдена. Коммиты: `990717d`, `5ac15f9`.

## Stage 8.9.7: Contract PDF generation via LibreOffice ✅ ЗАКРЫТ

### 8.9.7a ✅ LibreOffice installed
- `libreoffice-writer` + `fonts-liberation` на Ubuntu 24.04.4 LTS.
- `/usr/bin/soffice` и `/usr/bin/libreoffice` доступны (24.2.7.2).
- Код приложения не менялся.

### 8.9.7b ✅ Backend contract PDF generation (выполнено)
- `generate_contract_pdf()` в `webapp/contract_generator.py`.
- `POST /projects/{id}/contract/generate-pdf` route.
- `update_document_pdf_path()` в `webapp/db.py`.
- Конвертация DOCX→PDF через LibreOffice headless subprocess.
- Коммит: `990717d`.

### 8.9.7c ✅ UI contract PDF buttons (выполнено)
- Кнопка «Сформировать PDF договора» (POST, показывается если есть DOCX).
- Ссылка «Скачать PDF договора» (GET, показывается если есть PDF).
- Banner «PDF договора сформирован.»
- `pdf_created` context variable в `main.py`.
- Коммит: `990717d`.

### 8.9.7d ✅ Fix LibreOffice profile URI timeout (выполнено)
- Баг: `Path.as_uri()` возвращал `file:///tmp/...`, `_build_soffice_cmd` добавлял `file://` ещё раз → `file://file:///tmp/...`.
- LibreOffice не парсил URI → зависание → timeout 30 сек.
- Fix: `"-env:UserInstallation=" + profile_dir` (без дублирующего `file://`).
- Добавлены flags: `--nodefault`, `--nofirststartwizard`, `--nolockcheck`.
- Timeout увеличен с 30 до 60 секунд.
- 23 теста в `tests/test_contract_pdf_generation.py`.
- Коммит: `5ac15f9`.
- Live-проверка проект 11: PDF сформирован за ~1.5 сек, 6 страниц, кириллица корректна.

## Все задачи Stage 8.9 по DOCX/PDF/прайсу — ЗАКРЫТЫ

Следующие задачи не начинать без отдельного решения пользователя.

## Stage 8.10.0 — Security diagnostics ✅ ВЫПОЛНЕНА

Общий уровень риска: **средний**. Критичных находок нет.

Проверенные области: auth, documents, POST routes, CSRF, security headers, nginx, storage, secrets, logs, dependencies, SQL/XSS.

Findings:
1. Нет CSRF-защиты (Medium) — `SameSite=Lax` частично защищает
2. Session cookie без флага `Secure` (Medium) — `https_only=True` не передан в SessionMiddleware
3. Default fallback секреты в config.py (Low) — `"change-me-before-production"`, `"change-me"`
4. ~~Owner password в markdown docs (Low)~~ — закрыто 2026-06-02 (замаскировано в handoff docs)
5. Нет Content-Security-Policy (Low)
6. Устаревшие пакеты (Info) — fastapi, uvicorn, starlette, и др.
7. SSH PasswordAuthentication/PermitRootLogin (Low, осознанное решение)

## Security backlog (после Stage 8.10.0 diagnostics)

### 8.10.1 — Session cookie Secure flag (план)
- Добавить `https_only=True` в `SessionMiddleware` kwargs.
- `webapp/main.py:87-89`.
- 1 строка, маленький безопасный этап.
- Нужен restart после fix.

### 8.10.2 — Mask owner password in docs (план)
- ✅ Выполнено 2026-06-02: owner password PDF замаскирован в handoff docs (полное значение → `DEKORCRM_ESTIMATE_PDF_OWNER_***`).
- Markdown-only этап. Restart не нужен.

### 8.10.3 — CSP nginx diagnostics/header (план)
- Добавить `Content-Security-Policy` header на nginx уровне.
- Начать с мягкой политики: `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'`.
- Сначала диагностика nginx config, потом добавление header.
- Нужен nginx reload.

### 8.10.4 — CSRF diagnostics/fix (план)
- Добавить CSRF-защиту для POST/delete/generate routes.
- Middleware + hidden `_csrf_token` field во всех формах.
- Более крупный этап, аккуратно покрыть тестами.
- `SameSite=Lax` частично защищает от cross-site POST, но не от поддомена/GET→POST цепочек.
- Нужен restart после fix.

### 8.10.5 — Default secrets hardening (план)
- Убрать/запретить production fallback `"change-me-before-production"` и `"change-me"`.
- Приложение не должно стартовать в production без реальных secret/admin password.
- Либо crash при отсутствии env var, либо WARNING log.
- `webapp/config.py:68-72`.
- Нужен restart после fix.

### 8.10.6 — SSH hardening (план, только после настройки SSH-key)
- Отключить `PasswordAuthentication no`.
- Отключить `PermitRootLogin no`.
- Только после подтверждения пользователя, что SSH-key доступ работает.

### 8.10.7 — Dependencies update (план)
- Отдельный этап — сначала диагностика совместимости каждого major/minor bump.
- Starlette 0.48→1.2 — major bump, нужна особая аккуратность.
- Не обновлять массово без тестов.

## Перед UI/UX visual polish и адаптивной переработкой

### Критерии готовности к визуальному этапу

1. **Базовые security hardening задачи закрыты:**
   - Минимум: Session Secure flag (8.10.1), mask owner password (8.10.2), CSP минимальный header (8.10.3).
   - CSRF (8.10.4) хотя бы запланировать отдельным этапом, лучше выполнить до публичной активной эксплуатации.

2. **Ключевые бизнес-сценарии проверены end-to-end:**
   - Создание standalone сметы → импорт Excel → согласование → создание проекта → договор (DOCX + PDF) → PDF сметы → прайс-лист → скачивание документов.

3. **Оставшиеся функциональные модули зафиксированы:**
   - Акты / приложения / финальный акт — если пользователь решит делать до визуального этапа.
   - Финансы/платежи — если пользователь решит.

4. **Нет срочных багов данных:**
   - Сохранение прайс-листа, документы, контрагенты, статусы смет/проектов.

5. **Backup/checkpoint перед визуальной переработкой:**
   - Git clean, все pushed.
   - Service active.
   - База/storage не трогать без backup.
   - Желательно отдельная ветка или tag перед UI refactor.

### Принципы визуальной переработки

1. **Не переписывать весь сайт сразу.** Только по разделам: проекты, сметы, договор, прайс-лист, документы, финансы.

2. **Не смешивать визуальный refactor с бизнес-логикой.** Сначала visual/layout — отдельные commits, без изменения DB, расчётов, маршрутов (если не требуется).

3. **Сохранить расширяемость кода:**
   - Выносить повторяющиеся UI блоки в шаблонные partials/components.
   - Не дублировать разметку.
   - Сохранять понятные `class`/`data-*` attributes для JS.
   - Не завязывать бизнес-логику на визуальные классы.
   - Использовать `data-*` attributes для JS hook points.
   - Не ломать тесты.

4. **Адаптивность делать системно:** Desktop → tablet → mobile. Проверка основных страниц. Не делать «латки» только под один экран.

5. **Перед visual stage составить UI inventory:**
   - Список страниц, форм, таблиц, кнопок/статусов.
   - Что должно быть удобно на телефоне.
   - Что можно оставить только desktop-first.

6. **Единый визуальный стиль:** Сетка, кнопки, карточки, таблицы, сообщения success/error, формы, типографика.

7. **После каждого visual этапа:** User live browser verification. Не push без отдельного подтверждения. Не переходить к следующему разделу без проверки пользователя.

## Предлагаемый порядок работ после Stage 8.10.0

1. Stage 8.10.1 — Session cookie Secure flag
2. Stage 8.10.2 — Mask owner password in docs
3. Stage 8.10.3 — CSP nginx diagnostics/header
4. Stage 8.10.4 — CSRF diagnostics/fix
5. Stage 8.11 — Full functional smoke test checklist
6. Stage 8.12 — UI inventory before redesign
7. Stage 9.0 — Visual/UI polish по разделам
8. Stage 9.x — Responsive/mobile/tablet adaptation

Не начинать эти этапы без отдельного подтверждения пользователя.

## Test suite fixes ✅ ЗАКРЫТЫ
- `test_estimate_repository.py`: 13/13 pass.
- `test_standalone_estimate_routes.py`: 27/27 pass.
- Коммит: `9069b9d`.

## Функциональные блоки Stage 8.5–8.8.1 — все закрыты

### Будущий этап: UI-audit / UI-polish (после подтверждения пользователя)
- Привести import_excel.html и другие страницы к единому визуальному стилю CRM.
- Визуальная полировка страниц импорта, списков, редактора.
- Делать отдельными маленькими этапами, не одним большим рефакторингом.
- Начинать только после подтверждения пользователя и выполнения критериев готовности (см. «Перед UI/UX visual polish»).
- Не смешивать visual refactor с бизнес-логикой.

### Будущий этап: Mobile/adaptive layout
- Не начат. Отдельный этап (Stage 9.x) после завершения desktop visual polish.
- Делать системно: desktop → tablet → mobile.
- Не делать «латки» только под один экран.

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
