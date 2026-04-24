# 06 — Secrets and security

## Абсолютное правило
В эту папку и в Git нельзя сохранять:
- GitHub tokens / PAT;
- Telegram API hash/session strings;
- пароли пользователей;
- реальные `.env.web` значения;
- приватные SSH-ключи;
- API keys;
- сырые диалоги, где есть секреты.

## Как фиксировать секреты безопасно
Плохо: записывать конкретное значение серверного пароля или токена в markdown-файл.

Хорошо:
```text
Пароль веб-CRM задаётся в .env.web на сервере, значение не коммитить.
```

## GitHub token
Если пользователь присылает GitHub token в чат:
- использовать только для нужной операции;
- не записывать в remote URL;
- не записывать в handoff;
- по возможности не сохранять в `~/.git-credentials`;
- после работы рекомендовать перевыпустить/отозвать токен, если он был раскрыт в чате.

## .env.web
Файл `.env.web` должен оставаться вне Git. В репозитории допустим только безопасный пример вроде `.env.web.example`.

Текущее безопасное состояние на сервере после hardening:
```text
.env.web: 600 crmadmin:crmadmin
```

## Server hardening status — 2026-04-24
Сделано без изменения root/SSH password login:
- установлен и включён `fail2ban`;
- включён jail `sshd`;
- nginx получил базовые security headers: HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy;
- `.env.web` ужат до прав `600`.

Осознанно НЕ трогали без отдельной команды пользователя:
- `PermitRootLogin yes`;
- `PasswordAuthentication yes`.

Причина: нельзя рисковать потерей SSH-доступа. Сначала нужно подтвердить вход по SSH-ключу для нужного пользователя.
