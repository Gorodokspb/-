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

### 8.5.4 ✅ UI integration (выполнено)
- Кнопка «Импорт из Excel» в редакторе standalone-сметы (draft only).
- 3 template-теста. Commit: `8c6f2a7`.

### 8.5.5 Финальная полировка UX импорта Excel (следующий этап)
- Предупреждение, что импорт добавляет строки, а не заменяет существующие.
- Подтверждение перед apply.
- Показать количество уже существующих строк в смете.
- После успешного импорта показывать flash/notice.
- Защита от повторного apply одного и того же preview.

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
