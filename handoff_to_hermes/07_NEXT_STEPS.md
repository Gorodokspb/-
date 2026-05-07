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

### Будущий этап: UI-audit / UI-polish (после завершения всех ключевых функций CRM)
- Привести import_excel.html и другие страницы к единому визуальному стилю CRM.
- Визуальная полировка страниц импорта, списков, редактора.
- Делать только после того, как работоспособность всех ключевых функций CRM будет завершена.

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
