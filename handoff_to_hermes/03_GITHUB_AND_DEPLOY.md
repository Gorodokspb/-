# 03 — GitHub and deploy notes

## Repository
```text
/opt/dekorcrm/app/CRM_OLD_BAD
```

## Remote
```text
origin https://github.com/Gorodokspb/-.git
```

## Branch used for current work
```text
hermes/integrate-origin-master-20260423
```

## Push/auth notes
- На сервере `gh` CLI не установлен.
- SSH к GitHub ранее не проходил: `Permission denied (publickey)`.
- HTTPS push требует GitHub Personal Access Token.
- Токены нельзя сохранять в репозиторий или handoff.
- Если токен используется для push, предпочтительно использовать временный auth header и не записывать токен в remote URL.

## Recent pushed commit
```text
222230e Document Stage 8.10.9 pytest collection fixes
```

## Deploy caution
Не деплоить вслепую. Перед деплоем:
1. Проверить `git status`.
2. Проверить последние коммиты.
3. Запустить минимум `python -m py_compile webapp/main.py webapp/db.py`.
4. Запустить локальный web smoke check `/login`, `/projects`, `/projects/<id>/estimate`.
5. Только затем принимать решение о deploy/systemd restart.

## Production deploy checklist after push

После каждого `git push` в `origin/hermes/integrate-origin-master-20260423` выполнить на сервере (`Smetaserver`, `crmadmin@130.49.129.245` или root) полный deploy checklist. **Не считать deploy завершённым, пока production HEAD не совпадает с pushed HEAD** (для code changes).

**Правило:** `git push ≠ deploy`. Push в GitHub лишь публикует код. На сервере нужен явный `git pull`, и для большинства изменений — `systemctl restart`. uvicorn держит bytecode в памяти, `templates.env.globals` инициализируется только при импорте модуля — без restart новые декораторы и globals не подхватятся.

### Code / config / template changes (нужен restart)

```bash
# 0. Pre-flight: текущее состояние
cd /opt/dekorcrm/app/CRM_OLD_BAD
git status --short --branch

# 1. Pull с GitHub
git pull origin hermes/integrate-origin-master-20260423

# 2. Проверить, что HEAD совпадает с pushed
git status --short --branch
git log --oneline -5

# 3. Restart systemd-сервиса
sudo systemctl restart dekorcrm-web.service

# 4. Проверить, что сервис живой
sudo systemctl status dekorcrm-web.service --no-pager -l

# 5. Healthcheck: локальные эндпоинты
curl -s -o /dev/null -w "GET /login: %{http_code}\n"   http://127.0.0.1:8000/login
curl -s -o /dev/null -w "GET /projects: %{http_code}\n" http://127.0.0.1:8000/projects

# 6. Проверить логи — нет ли Traceback после restart
sudo journalctl -u dekorcrm-web.service -n 80 --no-pager
```

**Smoke-test вживую** (в браузере): открыть `https://crm198.ru/login`, залогиниться, проверить основной флоу (транзакция / смета / удаление).

**Что считать успехом:**
- `git status` показывает `## branch...origin/branch` без `[ahead N, behind M]`
- `systemctl status` показывает `Active: active (running)`, новый PID
- `GET /login` → `200`, `GET /projects` → `302` (редирект на login для неаутентифицированных)
- В journalctl нет `Traceback`/`RuntimeError`/`Refusing to start`

### Docs-only changes (restart НЕ нужен)

```bash
cd /opt/dekorcrm/app/CRM_OLD_BAD
git pull origin hermes/integrate-origin-master-20260423
git log --oneline -3
```

`systemctl restart` НЕ нужен: markdown не импортируется Python-процессом, поведение приложения не меняется. На сервере в `/opt/dekorcrm/app/CRM_OLD_BAD/handoff_to_hermes/*.md` обновятся — достаточно.

### Nginx changes (нужен reload, не restart web)

```bash
# 0. Проверить синтаксис
sudo nginx -t

# 1. Reload (без разрыва соединений)
sudo systemctl reload nginx

# 2. Проверить, что reload применился
sudo systemctl status nginx --no-pager -l
```

`systemctl restart dekorcrm-web` НЕ нужен (Nginx — внешний слой). `systemctl restart nginx` тоже НЕ нужен — `reload` достаточно.

### Dependency changes (requirements.txt / pyproject.toml)

```bash
cd /opt/dekorcrm/app/CRM_OLD_BAD
git pull origin hermes/integrate-origin-master-20260423

# Обновить зависимости в venv
/opt/dekorcrm/venv/bin/pip install -r requirements.txt

# Restart обязателен — uvicorn держит модули в памяти
sudo systemctl restart dekorcrm-web.service
sudo systemctl status dekorcrm-web.service --no-pager -l
```

Для dev-зависимостей (`requirements-dev.txt` — ruff и т.п.) на production-сервере устанавливать **не нужно**, если они не используются в runtime.

### DB migrations (`migrations/*.sql`)

```bash
# 1. Сначала прочитать SQL — он применяется вручную через psql
cat /opt/dekorcrm/app/CRM_OLD_BAD/migrations/<date>_*.sql

# 2. Применить на production-БД
psql "$DEKORCRM_POSTGRES_DSN" -f /opt/dekorcrm/app/CRM_OLD_BAD/migrations/<date>_*.sql

# 3. Проверить
psql "$DEKORCRM_POSTGRES_DSN" -c "\dt"

# 4. Restart (если миграция меняет схему, с которой работает webapp)
sudo systemctl restart dekorcrm-web.service
```

**Не делать автоматически.** Перед миграцией — backup БД (`pg_dump`) и тест на staging.

## Auto-reload status

**Auto-reload при `git pull` пока НЕ внедрён.** Все deploy-операции выполняются вручную по checklist выше. В бэклоге есть задача «auto-reload systemd unit при изменении кода» (Stage 8.12 кандидат), но до её внедрения — ручной deploy обязателен.

Типичный fail-pattern без auto-reload: push прошёл, `git pull` на сервере не делал → новый код лежит в `/opt/dekorcrm/app/CRM_OLD_BAD`, но uvicorn-процесс по-прежнему держит старый bytecode. Приложение работает на старом коде, новые фиксы и security-патчи не действуют. **После каждого push с code changes — restart обязателен.**
