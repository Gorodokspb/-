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
3808997 feat: tighten estimate table workspace
```

## Deploy caution
Не деплоить вслепую. Перед деплоем:
1. Проверить `git status`.
2. Проверить последние коммиты.
3. Запустить минимум `python -m py_compile webapp/main.py webapp/db.py`.
4. Запустить локальный web smoke check `/login`, `/projects`, `/projects/<id>/estimate`.
5. Только затем принимать решение о deploy/systemd restart.
