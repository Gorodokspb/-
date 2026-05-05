# 07 — Next steps

## Stage 8.4: Модуль компаний, реквизитов, печати и подписи

### 8.4.1 ✅ Schema + repository (выполнено)
- Таблица `companies`, seed-данные ООО «Декорартстрой» и ИП Гордеев А.Н.
- `CompanyRepository`, `CompanyService`, 16 тестов.

### 8.4.2 ✅ Repository/service (выполнено, вместе с 8.4.1)

### 8.4.3 ✅ UI settings companies (выполнено)
### 8.4.4 ✅ Asset upload protected storage (выполнено)

### 8.4.5 ✅ estimates.company_id FK (выполнено)

### 8.4.6a ✅ Company details in final PDF (выполнено)
### 8.4.6b ✅ Final PDF stamp/signature checkboxes (выполнено)
### 8.4.6c ✅ Real PNG stamp/signature in final PDF (выполнено, live-verified)
- Проверочная смета: estimate_id=881, status=approved, company_id=2 (ИП Гордеев А.Н.).
- approved_version_id=743, snapshot содержит company_id=2.
- stamp_path=company-assets/2/stamp.png, signature_path=company-assets/2/signature.png — оба файла существуют.
- Final PDF успешно отображает реквизиты ИП, реальную PNG-печать, реальную PNG-подпись.
- Draft/sent PDF не затронуты. Legacy estimate_pdf.py не тронут. Project-based PDF/JSON не тронуты.

### 8.4.6d Watermark from company.watermark_text (не начат)
- Заменить hardcoded watermark ('ДЕКОРАРТСТРОЙ' / 'ИП ГОРДЕЕВ А.Н.') на `company.watermark_text` из БД.
- Fallback: если company нет — старый hardcoded.

### 8.4.7 Legacy fallback/refactor (не начат, очень осторожно)

## Stage 8.5: Импорт Excel-смет в standalone-редактор
1. Добавить кнопку «Импорт из Excel» в standalone-редакторе сметы.
2. Загрузка `.xlsx` файла, парсинг через `openpyxl`.
3. Распознавание разделов и позиций работ из Excel.
4. Распознавание единиц измерения, количества, цены и суммы.
5. Перенос распознанных строк в текущую standalone-смету.
6. После импорта пользователь проверяет строки и сохраняет черновик.
7. Импорт разрешён только для статуса `draft` (редактируемой сметы).
8. Старые Excel-файлы не должны менять утверждённые/final-сметы.
9. Перед реализацией проанализировать 2–3 реальных Excel-сметы с сервера (`/opt/dekorcrm/storage/Сметы/` или из архива).

## Ближайшие задачи по CRM/сметам (после 8.5)
1. Продолжить доводить редактор сметы до плотного desktop-подобного рабочего вида.
2. Проверить визуально таблицу после sticky header/actions: нет ли перекрытий и неудобной горизонтальной прокрутки.
3. Решить, нужно ли полностью убрать колонку/поле кода/артикула из основного UI или оставить только в диалоге/данных.
4. Продолжить перенос/доработку калькулятора объёмов из desktop-версии в web.
5. Проверить правую панель расценок на реальных данных: количество, поиск, вставка в quick-add.
6. Подготовить безопасный deploy workflow для crm198.ru после локальной проверки.

## Handoff maintenance
После каждого значимого этапа:
1. Обновить relevant `.md` файлы в `handoff_to_hermes/`.
2. Проверить, что нет секретов.
3. Закоммитить изменения.
4. По возможности отправить на GitHub.

## Инфраструктура
- GitHub push настроен через SSH.
- Рабочая ветка: `hermes/integrate-origin-master-20260423`.
- Сервис: `dekorcrm-web.service` на `127.0.0.1:8000`.
- БД: PostgreSQL `dekorcrm`, резервные копии в `/opt/dekorcrm/backups/`.
