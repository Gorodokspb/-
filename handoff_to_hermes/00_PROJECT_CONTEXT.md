# 00 — Project context

## Проект
DekorCRM / CRM_OLD_BAD — CRM и workflow смет/документов для Dekorartstroy.

## Серверный путь
```text
/opt/dekorcrm/app/CRM_OLD_BAD
```

## Основная веб-часть
```text
run_web.py
webapp/
webapp/main.py
webapp/db.py
webapp/templates/
webapp/static/
```

## Сервис
Из прошлой проверки проекта:
```text
/etc/systemd/system/dekorcrm-web.service
```

Ключевая идея: веб-версия CRM работает как серверное приложение, а desktop-реализация остаётся важным референсом бизнес-логики и UX смет.

## Важные рабочие БД/файлы проекта
- `dekorart_base.db` — историческая SQLite база CRM.
- `dekorart_prices.db` — историческая SQLite база прайса.
- PostgreSQL используется для серверной веб-версии через `.env.web`.
- `.env.web` содержит реальные секреты и не должен попадать в Git.

## Старый/локальный handoff
В памяти есть указание на локальный Windows/Yandex Disk handoff:
```text
C:/Users/Aleks/YandexDisk-Gorodok198/СМЕТЫ НА ПРОВЕРКУ/CRM_OLD_BAD/handoff_to_hermes
```
На сервере папка была создана заново в текущем репозитории.
