---
name: obsidian-vault
description: Поиск, создание и управление заметками в Obsidian vault с wikilinks и index-заметками. Используй, когда пользователь хочет найти, создать или организовать заметки в Obsidian.
---

# Obsidian Vault

## Vault location

`$HOME/Documents/Obsidian Vault/` (vault name: `Obsidian Vault`).

Структура — two-tree LLM-Wiki (канон: `Company/_wiki/_wiki-pattern.md`, правила — `~/.claude/CLAUDE.md`):
- `Company/_wiki/<проект>/` — рабочий LLM-слой (планы, tasks, аудиты, отчёты).
  - `handoffs/<branch-slug>.md` — durable per-branch handoff (зеркало gitignored `./HANDOFF.md` репо;
    слаг ветки `/`→`--`). Создаётся/обновляется handoff-скилами; правило — `~/.claude/CLAUDE.md` › Handoff.
- `Company/Projects/<проект>/` — export-документация для коллег (→ Huly).

## Access — два равноправных канала

Чтение/запись **только через Obsidian-инструменты** (не raw Write/Edit/grep по файлам vault):

- **MCP-сервер `obsidian`**: `vault_read`, `vault_write` (создать/перезаписать),
  `vault_append`, `vault_move`, `vault_list`, `search_simple`/`search_query`.
- **Официальный Obsidian CLI** (`obsidian <command>`, требует запущенного приложения Obsidian):
  `read`, `create`, `append`/`prepend`, `move`/`rename`, `delete`, `search`/`search:context`,
  `backlinks`, `links`, `files`, `property:set`. Адресация — `path=<точный путь>`
  (не `file=<имя>` — резолвится как wikilink и при коллизии имён попадёт не туда).
  Переводы строк в `content` — как `\n`; для многострочного контента удобнее MCP `vault_write`.
- Если один канал недоступен (MCP не поднят / приложение закрыто) — используй другой.

> Полный справочник CLI (130+ команд, все флаги и форматы вывода):
> `references/command-reference.md` — читай при работе с нетипичной командой.

## Naming conventions

- **Index notes**: у каждого проекта `index.md` (секции 🧠 Working + 📤 Export, one-line summary)
- **Title Case** для имён заметок
- Организация — деревья `Company/_wiki` / `Company/Projects` + index-заметки

## Linking

- Obsidian `[[wikilinks]]` syntax: `[[Note Title]]`
- Связанные заметки — внизу заметки
- Кросс-ссылки между деревьями — полным vault-путём: `[[Company/Projects/...|подпись]]`
- В export-доках (`Company/Projects/`) не ставить ссылок на `Company/_wiki/...` (утекут в Huly)

## Workflows

### Search for notes

```bash
obsidian search query="keyword"            # по содержимому
obsidian search:context query="keyword"    # с контекстом совпадений
obsidian files | grep -i "keyword"         # по имени файла
```

Или MCP: `search_simple` / `search_query`, `vault_list`.

### Create a new note

1. **Title Case** для имени; путь — в правильном дереве (`_wiki` vs `Projects`);
   если слой не очевиден — уточни у пользователя
2. `obsidian create path="Company/_wiki/<проект>/Note.md" content="..."` или MCP `vault_write`
3. `[[wikilinks]]` на связанные заметки внизу
4. Допиши строку в `index.md` проекта (`obsidian append` / MCP `vault_append`)

### Find related notes (backlinks)

```bash
obsidian backlinks path="Company/_wiki/<проект>/Note.md"   # кто ссылается на заметку
obsidian links path="Company/_wiki/<проект>/Note.md"       # исходящие ссылки
```

### Move / rename

`obsidian move` / `obsidian rename` или MCP `vault_move` — идут через приложение,
сохраняют историю и чинят wikilinks. Не перемещать файлы через `mv`.

### Wiki lint (op: lint в LLM-Wiki)

```bash
obsidian unresolved                  # битые wikilinks по всему vault
obsidian orphans                     # заметки без входящих ссылок (нет в index?)
obsidian deadends                    # заметки без исходящих ссылок
obsidian backlinks path="..." counts # входящие ссылки конкретной заметки
```

**Полный механизированный прогон** — `scripts/wiki-lint.sh` (read-only, exit 1 при ERROR):
CLI-проверки выше + структура vault (файлы/папки вне деревьев, пробелы в именах) +
drift index.md↔файлы проектов + registry.json (huly-doc-sync) ↔ vault (stale-маппинги,
несинканные export-доки). Huly-сторону (живость docId) скрипт не проверяет — это шаг
агента через MCP `huly` (`list_documents` по teamspace ↔ map). Запускать перед
`huly-doc-sync` и периодически. Vault под git: после lint-фиксов — commit.

### Find index notes

```bash
obsidian files | grep -i "index"
```

## CLI gotchas

- `create` — путь **без** `.md` (добавится сам); `move`/`rename` — полный путь **с** `.md`
- `search query="..." format=json` — JSON-массив путей (удобно для `jq`)
- `property:set` пишет список как строку, не YAML-массив — массивы через
  `read` → правка frontmatter → `create` или через `eval`
- `eval` — только однострочный JS; многострочный: `obsidian eval code="$(cat /tmp/x.js)"`
- `template:insert` работает только с активным файлом в UI; из CLI —
  `obsidian create path="..." template="..."`
