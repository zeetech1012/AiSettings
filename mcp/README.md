# MCP — общий состав, личные учётные данные

Состав серверов общий для команды, **секреты у каждого свои** и в git не попадают никогда.

| Сервер | Зачем | Что подставить лично |
|---|---|---|
| `codegraph` | граф кода: кто-вызывает / impact до правки | — (поставить бинарь: https://github.com/colbymchenry/codegraph) |
| `context7` | актуальная документация библиотек | — |
| `playwright` | браузерные сценарии / E2E | — |
| `learn-go-with-tests` | справочник Go-тестирования | — |
| `jira` | трекер и вики из сессии: Jira DC (тикеты, JQL, переходы статусов) и Confluence DC (страницы, поиск) | `JIRA_URL`, `JIRA_PERSONAL_TOKEN`, `CONFLUENCE_URL`, `CONFLUENCE_PERSONAL_TOKEN` — личные PAT из профиля пользователя. Нет Confluence — убрать его пару переменных. |
| `obsidian` (опц.) | личная база знаний из сессии | ключ плагина «Local REST API with MCP» |
| `gradle` (опц.) | сборка/тесты KMP без ручного `./gradlew` | локальные пути |
| `allure` (опц.) | чтение Allure-отчётов | локальный путь |
| `idea` (опц.) | встроенный MCP-сервер JetBrains IDE: файлы, инспекции, запуск конфигураций | — (порт по умолчанию 64342; другой порт из настроек IDE подставить в URL) |

| `pycharm` (опц.) | MCP-сервер PyCharm: Python-проекты, инспекции, запуск тестов | `<PYCHARM_MCP_PORT>` из Settings → Tools → MCP Server; отдельный endpoint IDE |

## Первичная установка (нестандартные серверы)

- **codegraph** — бинаря недостаточно, граф строится индексацией в каждом рабочем репозитории:
  `codegraph init && codegraph index` в корне репо; обновление после больших правок —
  `codegraph sync`, проверка — `codegraph status`. Без индекса сервер отвечает пустотой.
- **jira** — self-hosted Jira (Data Center/Server v8.14+) и Confluence DC: community-сервер
  `sooperset/mcp-atlassian` через `uvx mcp-atlassian` (или Docker `ghcr.io/sooperset/mcp-atlassian`),
  авторизация по **Personal Access Token**: `JIRA_URL` + `JIRA_PERSONAL_TOKEN`,
  `CONFLUENCE_URL` + `CONFLUENCE_PERSONAL_TOKEN`. Один процесс отдаёт оба набора инструментов:
  `mcp__jira__jira_*` и `mcp__jira__confluence_*`. Для Jira **Cloud** вместо него — официальный
  remote MCP Atlassian (`https://mcp.atlassian.com/v1/mcp`, OAuth, Node 18+).
- **obsidian** — community-плагин «Local REST API with MCP» (id `obsidian-local-rest-api`, v4+):
  включить HTTPS-сервер (:27124), ключ API из настроек плагина → заголовок `Authorization: Bearer`.
  Endpoint MCP — `https://127.0.0.1:27124/mcp/`.
- **idea** — включить в IDE: Settings → Tools → MCP Server. Сервер работает, пока открыта IDE.

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

После настройки проверь личный доступ на чтение: попроси агента показать твой профиль
(`mcp__jira__jira_get_user_profile`) или выполнить JQL-поиск по своему проекту, и только потом
создавай тикеты через скилл `service-issue`. Живые токены и примеры в репозиторий не добавляй.

Ссылки на upstream каждого сервера (что скачать) — в корневом `README.md`, раздел
«Open-source стек».
