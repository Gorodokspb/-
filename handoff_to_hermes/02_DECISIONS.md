# 02 — Decisions and user preferences

## Общий подход
- Разработкой CRM занимается Hermes.
- Не коммитить/деплоить вслепую.
- Сначала проверять текущее состояние репозитория и важные инструкции.
- Сохранять проектную память в `handoff_to_hermes/` на сервере.
- Не сохранять логины, пароли, токены и реальные секреты в handoff или Git.

## Предпочтения по UI сметы
Пользователь предпочитает плотный рабочий интерфейс, а не декоративную страницу:
- максимум места под таблицу;
- минимум вторичных блоков;
- без дублей названия объекта;
- без лишнего `Project ID`;
- меньше маркетингового текста;
- таблица должна быть удобной для ежедневной работы;
- desktop-версия сметы — важный UX-референс.

## Приоритеты CRM/сметы
- Смета и редактор сметы — один из главных рабочих экранов.
- Справочник расценок должен показывать реальные серверные данные, а не искусственно ограниченный список.
- Калькулятор объёмов из desktop-версии нужно переносить в web, если пользователь ожидает тот же workflow.

## Stage 8.4 — Companies / Company assets (архитектурное решение)

Принято: отдельная таблица `companies` для хранения реквизитов, печати и подписи подрядчиков.

### Цели
- Поддержка минимум двух компаний: ООО «Декорартстрой» и ИП Гордеев А.Н.
- Хранение stamp/signature в защищённом storage (`{storage_root}/company-assets/{company_id}/`), не в static
- Отдача stamp/signature только через auth-only routes
- Печать и подпись добавляются только в final approved PDF
- Draft/sent PDF не содержат печать/подпись

### Таблица companies (план)
- `id`, `legal_name`, `short_name`, `inn`, `kpp`, `ogrn`, `ogrnip`
- `legal_address`, `phone`, `email`, `website`
- `stamp_path`, `signature_path`, `watermark_text`
- `is_active`, `created_at`, `updated_at`

### Связь с estimates
- `estimates.company_id` → `companies.id` (FK ON DELETE SET NULL)
- Миграция данных: `company_name` → `company_id` lookup по `short_name`

### Этапы 8.4.x
1. `8.4.1` — Таблица `companies` + миграция; `company_id` в `estimates`
2. `8.4.2` — Repository/service для companies
3. `8.4.3` — Storage для company assets + upload/serve routes
4. `8.4.4` — Template: настройки / компании / карточка
5. `8.4.5` — PDF: `drawImage()` stamp/signature в final approved PDF
6. `8.4.6` — Replace hardcoded `_get_company_details()` → DB lookup (legacy `estimate_pdf.py`)
7. `8.4.7` — Миграция данных: `company_name` → `company_id`
8. `8.4.8` — Тесты

### Ограничения
- Legacy `estimate_pdf.py` не трогать до этапа 8.4.6
- Для старых смет без `company_id` — fallback по `company_name`
- Stamp/signature PNG только через auth, не из `static/`
