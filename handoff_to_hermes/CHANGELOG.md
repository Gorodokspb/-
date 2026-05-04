# Changelog — handoff_to_hermes

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
