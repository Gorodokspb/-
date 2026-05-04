# 01 — Current status

## Текущая серверная ветка
```text
hermes/integrate-origin-master-20260423
```

## Последние важные коммиты
```text
e8d525c Stage 8.3.3 standalone workflow UI
61aca5e Stage 8.3.2b link final PDF documents
de55c72 Stage 8.3.2a allow standalone documents
cc94701 Stage 8.3.1 standalone final PDF from approved snapshot
5f893d2 Stage 8.2 standalone draft PDF
8870e78 Stage 8.1 standalone estimate status snapshots
```

Все отправлены на GitHub: `origin/hermes/integrate-origin-master-20260423`.

## Выполненные этапы standalone-смет

### Stage 6–7: Реестр и редактор standalone-смет
- Создан реестр самостоятельных смет `/standalone-estimates`.
- Работает создание сметы без проекта и без контрагента.
- Работает открытие standalone-сметы в редакторе `/estimates/{id}/edit`.
- Исправлено сохранение шапки, разделов и позиций; повторное открытие сохраняет данные.

### Stage 8.1: JSON / snapshots / statuses
- Исправлен порядок send/approve.
- sent/approved snapshots содержат актуальный status.
- `approved_version_id` и `current_version_id` работают корректно.

### Stage 8.2: Draft PDF
- Standalone draft PDF формируется отдельно от legacy.
- Разделы отображаются как разделы, итоги и скидка выводятся.
- Watermark для черновика добавлен; печать/подпись запрещены в draft.

### Stage 8.3.1–8.3.2b: Final approved PDF
- Final PDF строится из approved snapshot, а не из текущих живых данных.
- Добавлены маршруты final PDF (`POST /final-pdf`, `GET /download/final-pdf`).
- Final PDF привязан к `documents`, `estimate_documents`, `estimate_versions.pdf_document_id`, `estimates.final_document_id`.
- `documents.project_id` допускает NULL для standalone-документов (миграция `20260503_documents_nullable_project_id.sql`).
- Workflow `draft → sent → approved → final PDF → download` проверен на live (estimate 683).

### Stage 8.3.3: UI workflow
- В standalone editor добавлены кнопки: Отправить клиенту, Согласовать, Отклонить, Сформировать final PDF, Скачать final PDF, Скачать JSON.
- JS делает `fetch + reload`; legacy editor не затронут.
- 9 текстовых проверок шаблона, 129 тестов всего — все зелёные.

## Состояние после push
Рабочее дерево чистое, ветка отслеживает `origin/hermes/integrate-origin-master-20260423`.
