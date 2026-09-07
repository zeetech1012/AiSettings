# MCP — общий состав, личные учётные данные

Состав серверов общий для команды, **секреты у каждого свои** и в git не попадают никогда.

| Сервер | Зачем | Что подставить лично |
|---|---|---|
| `codegraph` | граф кода: кто-вызывает / impact до правки | — (поставить бинарь: https://github.com/colbymchenry/codegraph) |
| `context7` | актуальная документация библиотек | — |
| `playwright` | браузерные сценарии / E2E | — |
| `learn-go-with-tests` | справочник Go-тестирования | — |
| `huly` | трекер/доки: issue, синхронизация документации | `HULY_URL`, личный `HULY_TOKEN`, `HULY_WORKSPACE`; путь к сборке huly-mcp. Доступ и токен выдаёт администратор Huly. |
| `jira` (опц., если развёрнут) | трекер: issue/задачи из сессии | `JIRA_URL`, личный `JIRA_PERSONAL_TOKEN` (PAT). Self-hosted → `sooperset/mcp-atlassian`; Cloud → официальный remote MCP. |
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
- **jira** (если развёрнут) — self-hosted Jira (Data Center/Server v8.14+): community-сервер
  `sooperset/mcp-atlassian` через `uvx mcp-atlassian` (или Docker `ghcr.io/sooperset/mcp-atlassian`),
  авторизация по **Personal Access Token** (`JIRA_URL` + `JIRA_PERSONAL_TOKEN`). Для Jira **Cloud**
  вместо него — официальный remote MCP Atlassian (`https://mcp.atlassian.com/v1/mcp`, OAuth, Node 18+).
- **obsidian** — community-плагин «Local REST API with MCP» (id `obsidian-local-rest-api`, v4+):
  включить HTTPS-сервер (:27124), ключ API из настроек плагина → заголовок `Authorization: Bearer`.
  Endpoint MCP — `https://127.0.0.1:27124/mcp/`.

## Куда класть

`mcp.json` — общий исходник в формате `mcpServers` с явным `type: stdio|http`.
Не копируй его без преобразования в другой клиент: поля HTTP и формат stdio различаются.
Exporter `scripts/aisettings.py` создаёт нативные конфиги для Claude, Codex, agy, Qwen и
OpenCode. Пути, установка и ссылки на спецификации — в корневом `README.md`.

По умолчанию экспортируется весь шаблон; `--servers context7 playwright` выбирает подмножество.
`--mcp-source /путь/вне/репозитория/mcp.local.json` подставляет личный файл той же структуры.
Exporter не читает ENV, не подставляет секреты и не преобразует синтаксис ENV-подстановок:
такие строки остаются литералами, а поддержку подстановки определяет конкретный клиент.
Для переносимого файла передавай уже настроенные значения из личного источника. Файлы
экспорта и установки имеют права `0600` (исполняемые ресурсы — `0700`); приватный bundle не публикуй.

`install --components mcp` — preview, запись только с `--apply`. Неразрешённые `<...>` и
`example.com` блокируют установку MCP. Существующий личный конфиг объединяется вручную;
экспорт не заменяет model/provider/preferences активного клиента.

Поддерживаемые поля исходника: `type`, `command`, `args`, `env`, `cwd` для stdio;
`type`, `url`, `headers` для Streamable HTTP. Другие поля и транспорты отклоняются до записи,
чтобы конвертация не теряла настройки молча. CLI не проверяет доступность endpoint или наличие бинаря.

Для Claude остаётся и прямой путь: содержимое `mcp.json` → `~/.claude.json`
(ключ `mcpServers`) или `claude mcp add`.

Значения `<HULY_HOST_URL>` и `<WORKSPACE_UUID>` получает каждый пользователь у администратора
Huly. После настройки проверь личный доступ на чтение — попроси агента показать список проектов
(`mcp__huly__list_projects`) — и только потом создавай тикеты через скилл `service-issue`.
Живые токены и примеры в репозиторий не добавляй.

Ссылки на upstream каждого сервера (что скачать) — в корневом `README.md`, раздел
«Open-source стек».
