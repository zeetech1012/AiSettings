# Doc-sync → Docmost

> Адресатная часть скилла. Общие правила — в `SKILL.md` уровнем выше.
> Реестр — `registry.json`, хелпер — `scripts/docmost_api.py` рядом с этим файлом.


> Официальный MCP Docmost — enterprise-фича (на нашем инстансе «API ключи» закрыты платной
> лицензией, проверено 2026-07-07). Поэтому запись идёт через **internal REST API** (те же
> эндпоинты, что использует фронтенд) детерминированным хелпером `scripts/docmost_api.py`.
> Для чтения/поиска в сессии есть отдельный read-only MCP `docmost-local` (wisflux).

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
- Markdown-совместимость с рендером Docmost — правила ниже (перенесены из упразднённого
  `docmost-qa-strategy`, 2026-08-03); прогонять контент по ним.

### Правила разметки под рендер Docmost

- **Collapsible** — длинные технические блоки оборачивать, оставляя пустую строку после `summary`,
  иначе markdown внутри не отрендерится:

  ```html
  <details>
  <summary><b>Заголовок раздела</b></summary>

  Контент.
  </details>
  ```
- **Callouts** — GitHub-стиль (`> [!info]`, `> [!tip]`, `> [!warning]`, `> [!caution]`) при
  API-импорте не конвертируется, поэтому в выгружаемом тексте — `> <emoji> **…**`.
- **Иерархия заголовков** (`##`/`###`) — и внутри `<details>`, и снаружи: Docmost строит из них
  оглавление страницы. Уровни не пропускать.
- **Таблицы** — стандартный markdown для сравнений и соответствий «экран → файл».
- **Мета-блок аудитории** — статью начинать с `> **Аудитория:** …`, чтобы читатель сразу понимал,
  его это раздел или нет.
- Факты помечать как проверенные, только если они верифицированы по исходникам; архитектурные
  ограничения отражать (например, краш iOS на enum-аргументах навигации требует своего `navType()`).
- Image-эмбеды `![...](...)` на vault-пути — убрать (ассеты не переносятся v1).

## Ограничения v1

- Attachments/картинки не переносятся.
- `update` меняет `pageId` (re-import) → внешние ссылки на страницу протухают; для стабильных
  «входных точек» держать parent-страницу-оглавление и обновлять только детей.
- Registry-формат: `{"documents": [{"obsidian": "<vault path>", "pageId": "...", "spaceId": "...", "title": "..."}]}`.
