---
name: docmost-doc-sync
description: >-
  Синхронизация документации из Obsidian-vault в Docmost (docmost.example.com) БЕЗ создания дублей —
  через internal REST API (официальный MCP закрыт EE-лицензией). Ведёт registry.json
  (Obsidian path → Docmost pageId). Triggers: "выгрузи в docmost", "синкани в docmost",
  "обнови страницу в docmost", "docmost-doc-sync", "залей доку в docmost".
---

# SKILL: DOCMOST_DOC_SYNC

> Официальный MCP Docmost — enterprise-фича (на нашем инстансе «API ключи» закрыты платной
> лицензией, проверено 2026-07-07). Поэтому запись идёт через **internal REST API** (те же
> эндпоинты, что использует фронтенд) детерминированным хелпером `scripts/docmost_api.py`.
> Для чтения/поиска в сессии есть отдельный read-only MCP `docmost-local` (wisflux).

## Цель и инварианты (как у huly-doc-sync)

Источник истины — **Obsidian-vault**. Docmost — выгрузка. Один Obsidian-файл = одна страница Docmost.

1. **Никогда не создавать вторую страницу** для файла, у которого есть запись в `registry.json`.
2. Новая страница → сразу запись в registry (`obsidian` → `pageId` + `spaceId` + `title`).
3. Перед любой записью — свериться с `registry.json` (лежит рядом с этим SKILL.md).
4. Секреты — только ENV (`DOCMOST_URL` / `DOCMOST_EMAIL` / `DOCMOST_PASSWORD`,
   задаются в `~/.claude/settings.local.json` → `env`). В файлы skill'а не писать.

## Хелпер

```bash
python3 scripts/docmost_api.py spaces                     # список пространств (id | name | slug)
python3 scripts/docmost_api.py search "запрос" [spaceId]
python3 scripts/docmost_api.py info <pageId>
python3 scripts/docmost_api.py export <pageId>            # markdown страницы
python3 scripts/docmost_api.py import <file.md> <spaceId> [parentPageId]  # md → страница
python3 scripts/docmost_api.py create <spaceId> <title> [parentPageId]
python3 scripts/docmost_api.py update-title <pageId> <title>
python3 scripts/docmost_api.py delete <pageId>            # в корзину пространства
```

## Алгоритм sync

1. Прочитать vault-файл через MCP `obsidian` (`vault_read`) → transform (см. ниже) → временный
   `.md` в scratchpad.
2. Registry lookup по vault-пути:
   - **Нет записи** → `import <tmp.md> <spaceId> [parent]` → записать `pageId` в registry.
   - **Есть запись** → **`update <pageId> <tmp.md>`** — replace контента markdown'ом
     (`/api/pages/update` c `operation=replace, format=markdown`, проверено на v0.90).
     `pageId` стабилен, внешние ссылки живут, registry не меняется.
   - Заголовок без смены контента → `update-title`.
   - **Перед update чужих/общих страниц** — `info <pageId>`: если `lastUpdatedBy` — не ты,
     сверить контент на правки коллег (см. случай user_guide 2026-07-07) и согласовать.
   - Fallback для старых инстансов без markdown-update: re-import + delete старой + swap
     `pageId` в registry.
3. Отчёт: `<vault-файл> → <Docmost title> [created|updated] + pageId`.

## Transform Obsidian → Docmost (перед import)

- Frontmatter (`---...---`) — убрать.
- H1 статьи — убрать (у страницы Docmost собственный title; иначе заголовок задвоится).
- Callouts `> [!info]` / `> [!warning]` и т.п. — **API-импорт markdown их НЕ конвертирует**
  (остаются литеральным `[!info]` в цитате; проверено на «Таск трекер» 2026-07-08).
  Заменять на `> <emoji> **...**` (ℹ️/⚠️/❗/💡). `<details><summary>` при этом рендерится корректно.
- Wikilinks `[[...]]` — заменить на читаемый текст (или URL страницы Docmost, если цель уже в registry).
- Экранирование `\|` в таблицах — снять (это Obsidian-специфика).
- Markdown-совместимость с рендером Docmost — правила в skill `docmost-qa-strategy`
  (collapsible, callouts); прогонять контент по ним.
- Image-эмбеды `![...](...)` на vault-пути — убрать (ассеты не переносятся v1).

## Ограничения v1

- Attachments/картинки не переносятся.
- `update` меняет `pageId` (re-import) → внешние ссылки на страницу протухают; для стабильных
  «входных точек» держать parent-страницу-оглавление и обновлять только детей.
- Registry-формат: `{"documents": [{"obsidian": "<vault path>", "pageId": "...", "spaceId": "...", "title": "..."}]}`.

## Wiki-дисциплина

После sync: запись в `log.md` проекта (op `ingest`), как у huly-doc-sync. Личный skill
(🔴 красная корзина — registry и учётка локальные), в командный baseline не раздавать.
