# MCP — общий состав, личные учётные данные

Состав серверов общий для команды, **секреты у каждого свои** и в git не попадают никогда.

| Сервер | Зачем | Что подставить лично |
|---|---|---|
| `codegraph` | граф кода: кто-вызывает / impact до правки | — (поставить бинарь: https://github.com/colbymchenry/codegraph) |
| `context7` | актуальная документация библиотек | — |
| `playwright` | браузерные сценарии / E2E | — |
| `learn-go-with-tests` | справочник Go-тестирования | — |
| `huly` | трекер/доки: issue, синхронизация документации | `HULY_URL`, личный `HULY_TOKEN`, `HULY_WORKSPACE`; путь к сборке huly-mcp. Доступ и токен выдаёт администратор Huly. |
| `obsidian` (опц.) | личная база знаний из сессии | ключ плагина «Local REST API with MCP» |
| `gradle` (опц.) | сборка/тесты KMP без ручного `./gradlew` | локальные пути |
| `allure` (опц.) | чтение Allure-отчётов | локальный путь |

## Первичная установка (нестандартные серверы)

- **codegraph** — бинаря недостаточно, граф строится индексацией в каждом рабочем репозитории:
  `codegraph init && codegraph index` в корне репо; обновление после больших правок —
  `codegraph sync`, проверка — `codegraph status`. Без индекса сервер отвечает пустотой.
- **huly-mcp** — собрать форк:
  `git clone https://github.com/zeetech1012/huly-mcp && cd huly-mcp && pnpm install && pnpm build:mcp`;
  путь к `dist/index.cjs` подставить в конфиг.
- **obsidian** — community-плагин «Local REST API with MCP» (id `obsidian-local-rest-api`, v4+):
  включить HTTPS-сервер (:27124), ключ API из настроек плагина → заголовок `Authorization: Bearer`.
  Endpoint MCP — `https://127.0.0.1:27124/mcp/`.

## Куда класть

- **Claude Code**: содержимое `mcp.json` → `~/.claude.json` (ключ `mcpServers`) или через `claude mcp add`.
- **Codex CLI**: `codex.toml` → секции в `~/.codex/config.toml` (или `codex mcp add <name> -- <cmd>`).
- **Gemini CLI**: `gemini.settings.json` → слить с `~/.gemini/settings.json`.
- **Cursor**: блок `mcpServers` из `gemini.settings.json` → `~/.cursor/mcp.json`.

Значения `<HULY_HOST_URL>` и `<WORKSPACE_UUID>` получает каждый пользователь у администратора
Huly. После настройки проверь личный доступ через `huly-team-work`: назови доступный проект и
попроси показать preview нового тикета. Живые токены и примеры в репозиторий не добавляй.

Ссылки на upstream каждого сервера (что скачать) — в корневом `README.md`, раздел
«Open-source стек».
