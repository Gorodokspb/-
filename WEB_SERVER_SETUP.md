# Web CRM: сервер и GitHub

## Что храним где

Живые данные:
- PostgreSQL на сервере
- файлы CRM на сервере в `/opt/dekorcrm/storage`
- резервные копии базы и файлов тоже на сервере

GitHub:
- только код проекта
- история изменений
- резервная публикация исходников

Важно:
- GitHub не должен быть основным хранилищем базы, смет и договоров
- рабочие PDF, JSON-черновики и вложения должны жить на сервере, а не в Яндекс Диске

## Рекомендуемая структура на сервере

```text
/opt/dekorcrm/
  app/CRM_OLD_BAD
  storage/
    Сметы/
    Договоры/
    uploads/
  backups/
  venv/
```

## Что уже подготовлено в коде

- `webapp/` — browser-MVP на FastAPI
- `run_web.py` — запуск web-версии
- `.env.web.example` — шаблон конфигурации
- документы в web-версии читаются из путей, лежащих внутри `DEKORCRM_STORAGE_ROOT`

## Минимальный план переноса

1. Код держать в GitHub и разворачивать на сервере из репозитория.
2. Все рабочие папки `Сметы` и `Договоры` перенести в `/opt/dekorcrm/storage`.
3. В `.env.web` на сервере указать:
   - PostgreSQL DSN
   - логин и пароль web-входа
   - `DEKORCRM_STORAGE_ROOT=/opt/dekorcrm/storage`
4. Запускать web-приложение командой:

```bash
cd /opt/dekorcrm/app/CRM_OLD_BAD
source /opt/dekorcrm/venv/bin/activate
python -m pip install -r requirements.txt
python run_web.py
```

5. После проверки повесить Nginx как reverse proxy на домен или IP.

## Что это дает

- больше не нужен Яндекс Диск как рабочее хранилище
- ты и тестировщик сможете заходить через браузер
- код будет безопасно сохраняться в GitHub
- база и документы останутся централизованно на сервере
