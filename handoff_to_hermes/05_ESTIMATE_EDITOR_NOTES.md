# 05 — Estimate editor notes

## Последний UX-проход по таблице
Файлы:
```text
webapp/templates/estimate_editor.html
webapp/static/estimate_editor.js
webapp/static/app.css
```

Сделано:
- добавлены классы колонок таблицы: type/name/unit/number/actions;
- числовые ячейки создаются через JS helper `createNumberCell()`;
- числовые значения выровнены вправо;
- включён `font-variant-numeric: tabular-nums`;
- таблица получила sticky header;
- правая колонка действий стала sticky;
- toolbar над таблицей стал compact/sticky;
- подсказки заменены на компактные pill-like элементы;
- уменьшены отступы, бейджи и кнопки меню строк;
- table-wrap получил bounded height: `max-height: calc(100vh - 220px)`.

## Проверенные маршруты
```text
/login
/projects
/projects/7/estimate
```

## Особенности UX
- Двойной клик по строке — редактирование.
- Ctrl+S — сохранить.
- Alt+↑ / Alt+↓ — двигать строки.
- Inline composer добавляет новую строку после выбранной строки или в конец.

## Что не делать без отдельного решения
- Не менять payload сметы без проверки backend save/fetch.
- Не удалять бизнес-поля из данных, даже если они скрыты из UI.
- Не ломать desktop fallback/референс.
