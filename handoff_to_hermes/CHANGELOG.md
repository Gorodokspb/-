# Changelog — handoff_to_hermes

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
