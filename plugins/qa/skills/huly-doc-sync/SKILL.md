---
name: huly-doc-sync
description: >
  Синхронизация документации из Obsidian-vault в Huly БЕЗ создания дублей.
  При обновлении локального .md в Obsidian обновляет тот же документ Huly по сохранённому
  docId (edit_document с full-replace), а не плодит копию статьи. Ведёт registry.json
  (Obsidian path → Huly docId). Новый док создаётся один раз и регистрируется.
  Triggers on: "обнови доки в huly", "синхронизируй документацию", "залей доки в huly",
  "sync docs to huly", "update huly docs", "обнови статью в huly", "выгрузи док в huly",
  "doc sync", "huly-doc-sync".
---

# SKILL: HULY_DOC_SYNC

> **MCP huly работает из локальной пропатченной сборки** (`zeetech1012/huly-mcp`, конфиг `command: node`, `args: [.../dist/index.cjs]`). Синхронизация (`edit_document` / `create_document`) — как раньше. Дополнительно: загрузка вложений (`add_issue_attachment` — скрин/видео к багам) **теперь работает** — стоковый `@firfi/huly-mcp` ломал её на self-hosted инстансе (абсолютный `UPLOAD_URL` + `concatLink`), пропатченная сборка чинит. Если MCP вернётся на сток (`npx @firfi/huly-mcp@latest`) — загрузка вложений снова отвалится (StorageError `Cannot POST /https:/tracker.example.com/files`).

## Цель
Держать документацию в Huly зеркалом Obsidian-vault. **Источник истины — Obsidian.**
Huly — выгрузка для команды. Ключевой инвариант: **один Obsidian-файл = один документ Huly**.
Повторный запуск **обновляет** существующий документ (по `docId`), **не создаёт** новый.

## Инварианты (нарушать нельзя)
1. **Никогда не `create_document` для файла, у которого есть запись в `registry.json`.** Только `edit_document` по `docId`.
2. `create_document` допустим **только** для файла без записи в реестре → сразу после создания добавить запись в `registry.json` (`obsidian` → `docId` + `title`).
3. Перед любой записью свериться с `registry.json` (лежит рядом с этим SKILL.md).
4. Title в Huly меняем через `edit_document(title=...)` — не пересоздаём документ ради переименования.
5. `.md` создаём/правим только в Obsidian (это правило vault'а), Huly правим через MCP. Сам реестр — служебный JSON skill'а, не документация.

## Инструменты
- Чтение Obsidian: `mcp__obsidian__vault_read` (вернёт `content`, `frontmatter`, `stat.mtime`).
- Запись Huly: `mcp__obsidian` для чтения + `mcp__huly__edit_document` (full-replace через `content`, переименование через `title`).
- Создание (только новые): `mcp__huly__create_document` (с `parent` = `parentTitle` из реестра для вложенности).
- Реестр: `Read`/`Edit`/`Write` файла `registry.json` в каталоге skill'а.

## Алгоритм

### 0. Определить scope
- Пользователь назвал конкретные файлы → синхронизируем их.
- «обнови все доки» → пройти по всем записям `map` соответствующего проекта.
- Определить проект по vault-пути (`Company/Projects/<project>/...`) → секция в `registry.json`.

### 1. Прочитать реестр
`Read` `registry.json`. Найти секцию `projects.<project>.documents`. Запомнить `teamspace`, `parentTitle`, `map`.

### 2. Для каждого целевого файла
1. `vault_read` Obsidian-файла (`vaultRoot` + `obsidian`-путь).
2. **Найти запись в `map` по `obsidian`-пути.**
   - **Есть запись** → `edit_document(teamspace, document=<docId>, content=<transformed>)`. Если заголовок документа сменился — добавить `title=<new>` и обновить `title` в реестре.
   - **Нет записи** → `create_document(teamspace, title, parent=<parentTitle>, content=<transformed>)`; взять `id` из ответа; **дописать** в `map` объект `{ "obsidian": "<path>", "docId": "<id>", "title": "<title>" }` (через `Edit` registry.json).
3. Никогда не создавать второй документ для уже сматченного файла.

### 3. Transform Obsidian → Huly (применять к content перед записью)
Привести markdown к тому, что корректно рендерит Huly:
- **Mermaid:** убрать `<br/>` внутри подписей нод (Huly-парсер их не любит) — заменить на пробел. Блоки ` ```mermaid ` оставить как есть.
- **Картинки:** строки-эмбеды `![alt](*.png)` удалить (ассеты в Huly не загружены) — текст статьи не трогать.
- **Внутренние ссылки** `[текст](other.md)` / `[[wikilink]]`: оставить как читаемый текст или заменить на название целевого документа Huly (по реестру). Не оставлять «битые» `.md`-якоря, если легко поправить.
- Frontmatter Obsidian (`---...---`) в тело Huly **не** копировать (служебные поля). Допустимо вынести `Аудитория/Стек` строкой `> **...**` если они уже в теле.
- Кодовые блоки, таблицы — без изменений.

### 4. Отчёт
Вернуть список: `<obsidian-файл> → <Huly title> [updated|created]` + URL из ответа MCP. Явно отметить, что обновлено (не создано).

## Test Management (опционально)
Если просят синхронизировать `test_cases_catalog.md`:
- Кейсы матчатся по имени (`TC-XX: ...`) → `mcp__huly__update_test_case(project, testCase=<name>, ...)`.
- Новые TC → `create_test_case` в нужную сюиту. Сюиты идемпотентны (`create_test_suite` вернёт существующую).
- Это отдельный поток; по умолчанию skill работает с Documents.

## Анти-паттерны
- ❌ Прогнать `create_document` по всем файлам «чтобы обновить» → получите дубли. Всегда edit по docId.
- ❌ Захардкодить docId в промпте вместо реестра.
- ❌ Тащить frontmatter и битые image-эмбеды в Huly.
- ❌ Создавать `.md` в рабочем каталоге репозитория (правило vault'а).

## Расширение на другие проекты
Добавить новую секцию в `projects.<name>` с `vaultRoot`, `documents.teamspace`, `parentDocId/parentTitle`, пустым/заполненным `map`. Первый прогон создаст документы и заполнит `map`; последующие — только обновляют.
