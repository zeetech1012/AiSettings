# AiSettings — общие настройки AI-клиентов

Один источник командных правил, QA/PM skills и состава MCP для **Claude Code, Codex,
Antigravity CLI (`agy`), Qwen Code и OpenCode**. Exporter готовит нативные конфиги из
общих исходников; установщик показывает изменения и защищает личные файлы от перезаписи.
Claude marketplace остаётся отдельным способом доставки тех же skills и sub-agents.

> Личный проект автора. Публичный контент обезличен плейсхолдерами (`example.com`);
> внутренние адреса (Git-хостинг, Jira DC, Confluence DC) каждый подставляет локально.

## Экспорт и установка

Нужны Python 3.11+ и macOS/Linux. Команды выполняются из клона репозитория:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
aisettings_out="$(mktemp -d)"
.venv/bin/python scripts/aisettings.py export --client all \
  --output "$aisettings_out" --servers context7 playwright
```

Получатся каталоги `claude/`, `codex/`, `agy/`, `qwen/`, `opencode/`: в каждом `home/`
с файлами относительно домашнего каталога и `manifest.json` с контрольными суммами,
составом и ограничениями. Экспорт повторяемый, существующий непустой каталог не затирается.
Артефакты создаются вне репозитория. Для одного клиента укажи, например, `--client qwen`.

Preview и установка rules + skills для Codex:

```bash
.venv/bin/python scripts/aisettings.py install --bundle "$aisettings_out/codex"
.venv/bin/python scripts/aisettings.py install --bundle "$aisettings_out/codex" --apply
```

`install` без `--apply` ничего не записывает. Для другого клиента замени имя каталога.
`--home /tmp/aisettings-test-home` позволяет проверить установку в отдельном каталоге.
Используются стандартные пользовательские пути; нестандартные `CODEX_HOME` и
`XDG_CONFIG_HOME` требуют ручной адаптации расположения файлов.

MCP подключается отдельным выбором компонента, после проверки состава:

```bash
.venv/bin/python scripts/aisettings.py install --bundle "$aisettings_out/codex" --components mcp
.venv/bin/python scripts/aisettings.py install --bundle "$aisettings_out/codex" --components mcp --apply
```

Для Claude доступны также `--components agents commands`. По умолчанию они не устанавливаются.
Установщик не запускает клиенты или MCP-серверы и не устанавливает их зависимости.

При конфликте **весь выбранный набор остаётся без изменений**, exit code — `2`.
Существующий личный `config.toml`, `settings.json` или файл правил нужно объединить
с экспортом вручную; автоматического merge произвольных конфигов здесь нет. Чтобы поставить
только skills, используй `--components skills`. Файлы с локальными изменениями защищены
и при обновлении. Совпадающие чужие файлы не становятся управляемыми автоматически.

Состояние установки хранится в `~/.local/share/aisettings/<client>.json` и содержит
пути, компоненты и хеши, без содержимого файлов. Повторная установка того же пакета — no-op.
Новая версия обновляет неизменённые управляемые файлы и удаляет только устаревшие файлы
выбранных компонентов, если они не редактировались локально. Не удаляй файл состояния
между обновлениями. Запись атомарна для отдельного файла; общей транзакции на случай сбоя диска нет.

## Поддержка клиентов

Пути и форматы сверены 2026-09-07. Машинный перечень: `python3 scripts/aisettings.py clients`.

| Клиент | Глобальные rules | Каталог skills | MCP |
|---|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` | `~/.claude/skills` | `~/.claude.json`: `mcpServers`, `type` |
| Codex | `~/.codex/AGENTS.md` | `~/.agents/skills` | `~/.codex/config.toml`: `mcp_servers` |
| agy | `~/.gemini/GEMINI.md` | `~/.gemini/antigravity-cli/skills` | `~/.gemini/config/mcp_config.json`: `serverUrl` |
| Qwen Code | `~/.qwen/QWEN.md` | `~/.qwen/skills` | `~/.qwen/settings.json`: `httpUrl` |
| OpenCode | `~/.config/opencode/AGENTS.md` | `~/.config/opencode/skills` | `~/.config/opencode/opencode.json`: `mcp`, `local`/`remote` |

Источники форматов: [Claude MCP](https://code.claude.com/docs/en/mcp),
[Codex skills](https://developers.openai.com/codex/skills),
[Codex MCP](https://developers.openai.com/codex/mcp),
[agy CLI skills](https://www.antigravity.google/docs/cli/plugins/),
[agy MCP](https://www.antigravity.google/docs/cli/mcp/),
[Qwen configuration](https://qwenlm.github.io/qwen-code-docs/en/users/configuration/settings/),
[OpenCode skills](https://opencode.ai/docs/skills/),
[OpenCode rules](https://opencode.ai/docs/rules/),
[OpenCode MCP](https://opencode.ai/docs/mcp-servers/).

Пределы поддержки:

- Claude получает 20 skills, Codex/Qwen — 19, agy/OpenCode — 18. Состав пересчитывается при
  экспорте и записывается в manifest. `git-guardrails-claude-code` исключён вне Claude;
  `writing-great-skills` исключён для agy/OpenCode, поскольку там не подтверждено соблюдение
  его запрета на неявный вызов. В Codex этот запрет задан `agents/openai.yaml`.
- У [Antigravity rules](https://antigravity.google/docs/rules-workflows) лимит 12 000 символов.
  Если baseline длиннее, `GEMINI.md` содержит инструкцию прочитать полный файл
  `~/.gemini/antigravity-cli/aisettings/AGENTS.md`. Текст не обрезается, но его загрузка
  требует чтения файла агентом; это отмечено как `bootstrap` в manifest.
- Native sub-agents и команды экспортируются только для Claude. Hooks, runtime settings,
  permissions и сторонние plugins на другие клиенты не переводятся. `claude/settings.json`
  остаётся отдельным шаблоном, exporter его не устанавливает.
- Подтверждены структура пакетов и преобразование MCP. Выполнение всех workflows на каждом
  клиенте не проверено: `context: fork`, названия инструментов и делегирование зависят от
  runtime. Пути `~/.claude/skills` в поставляемых ресурсах заменяются на каталог выбранного клиента.
- Некоторые клиенты дополнительно читают skills из `.claude` и `.agents`. Не устанавливай
  одинаковый каталог несколько раз; при уже доступных skills можно выбрать только `rules mcp`.
  Исключение skill из экспорта не запрещает клиенту обнаружить другую установленную копию.

Новый клиент добавляется записью в `config/clients.json`; новый MCP-формат — отдельной
веткой адаптера в `scripts/settings_bundle.py` и проверкой транспорта в `tests/test_mcp.py`.

## Claude marketplace

В Claude Code:

```
/plugin marketplace add zeetech1012/AiSettings
/plugin install qa@ai-settings
/plugin install pm@ai-settings
```

Для Claude выбери один способ доставки skills: marketplace или прямую установку exporter'ом.
При marketplace-установке rules и MCP можно взять из экспорта отдельно.

## Как это устроено

Канонические исходники общие для всех клиентов:

| Что | Источник | Адаптация |
|---|---|---|
| Командные правила | `AGENTS.md` | Нативный файл инструкций клиента |
| Skills и ресурсы | `plugins/*/skills` | Поддерживаемое подмножество и нативные пути |
| Состав MCP | `mcp/mcp.json` | JSON/TOML и поля транспорта клиента |
| Сведения о клиенте | `config/clients.json` | Пути, формат, исключения |

Личная роль, секреты и настройки конкретного инстанса остаются на рабочей станции.

## Что внутри

```
AGENTS.md                        ← канонический текст правил (роль — персональная)
config/clients.json              ← нативные пути и ограничения клиентов
scripts/aisettings.py            ← export / install / clients
scripts/settings_bundle.py       ← преобразование rules, skills и MCP
tests/                          ← проверки переносимости и сохранности личных файлов
claude/CLAUDE.md                 ← @AGENTS.md + Claude-специфика
claude/CLAUDE.example.md         ← образец детализации (секция роли заполняется под себя)
claude/settings.json             ← шаблон: effortLevel, allowlist, hooks-гардрейлы, marketplaces, плагины
.claude-plugin/marketplace.json  ← этот репозиторий = Claude-marketplace `ai-settings`
plugins/qa/                      ← плагин: skills + sub-agents
  skills/    Процедуры с состоянием: doc-sync (confluence, реестр страниц)
             service-issue (jira · xray, модель типов и ловушки инстанса)
             Контекст и диагностика: service-doc · occams-razor · code-to-wiki-docs
             kaspresso-single-test-diagnostician · obsidian-vault
             Utils: git-guardrails-claude-code · write-a-skill · writing-great-skills
  agents/    project-researcher · go-service-explorer · frontend-contract-miner ·
             swagger-to-pydantic · repo-security-auditor · link-integrity-validator · scrum-master
plugins/pm/                      ← плагин: PM-линия (добавлена 2026-08-21, обезличена 2026-08-31)
  skills/    Atlassian: jira-expert · confluence-expert · atlassian-admin · atlassian-templates
             Delivery: pm-skills (router) · scrum-master · senior-pm · agent-harness
             Comms: team-communications · meeting-analyzer
  commands/  /cs:pm · /cs:pm-loop · /cs:grill-pm · /cs:harness
  agents/    cs-pm-orchestrator · harness-runner
mcp/                             ← шаблон состава MCP (mcp.json) + что подставить лично (README.md)
```

## Три корзины (что здесь, чего здесь нет)

| Корзина | Где живёт |
|---|---|
| 🟢 Общее (правила, skills, состав MCP) | **этот репозиторий** → экспорт для клиента |
| 🟡 Стек-специфичное (проектные `CLAUDE.md`, узкие skills) | в репозитории проекта |
| 🔴 Личное (токены, ключи, пути, личная база знаний) | `settings.local.json` / ENV — **не сюда** |

## Open-source стек (что скачать)

Весь набор стоит на open-source. Ссылки на upstream (секретов нет — подставляется локально):

### MCP-серверы (состав — `mcp/`)

| Сервер | Пакет / бинарь | Источник |
|---|---|---|
| `codegraph` | бинарь `codegraph` | https://github.com/colbymchenry/codegraph |
| `context7` | `@upstash/context7-mcp` (npx) | https://github.com/upstash/context7 |
| `playwright` | `@playwright/mcp` (npx) | https://github.com/microsoft/playwright-mcp |
| `learn-go-with-tests` | HTTP (GitBook) | https://github.com/quii/learn-go-with-tests |
| `jira` | `mcp-atlassian` (uvx): Jira DC + Confluence DC по PAT | https://github.com/sooperset/mcp-atlassian |
| `obsidian` | плагин Obsidian «Local REST API with MCP» (v4+, HTTPS :27124, endpoint `/mcp/`) | https://github.com/coddingtonbear/obsidian-local-rest-api |
| `gradle` (опц.) | `gradle-mcp` (uv) | локальный сервер — путь в `mcp/README.md` |
| `allure` (опц.) | `mcp-allure` (uv) | локальный сервер — путь в `mcp/README.md` |
| `idea` (опц.) | встроенный MCP-сервер JetBrains IDE (HTTP `127.0.0.1`) | https://www.jetbrains.com/help/idea/mcp-server.html |

### Инструменты рабочей станции

| Инструмент | Назначение | Источник |
|---|---|---|
| gitleaks | секреты в git-истории/дереве | https://github.com/gitleaks/gitleaks |
| semgrep (CE) | SAST (Go/Kotlin/Swift) | https://github.com/semgrep/semgrep |
| OWASP ZAP | DAST (baseline / api-scan) | https://github.com/zaproxy/zaproxy |
| garak (NVIDIA) | red-teaming LLM: prompt injection, jailbreak, утечки | https://github.com/NVIDIA/garak |
| Docker Engine | контейнеры | https://github.com/moby/moby |
| Obsidian | личная база знаний | https://obsidian.md (проприетарный, free) |
| Meetily | локальный AI-протокол встреч (Whisper.cpp + суммаризация, данные не уходят в облако) | https://github.com/Zackriya-Solutions/meetily |

### Self-hosted инфраструктура

| Сервис | Роль | Источник |
|---|---|---|
| Allure | отчёты | https://github.com/allure-framework/allure2 · docker: https://github.com/fescobar/allure-docker-service |

### Skills — открытый стандарт

- **Этот репозиторий** = общие каталоги `qa` и `pm`; доставка через exporter или Claude marketplace.
- Открытый стандарт **Agent Skills** — папка-скилл с `SKILL.md`; свои skills клади в `plugins/qa/skills/` и отправляй push.
- Сторонние Claude-плагины (handoff, understand-anything и т.п.) — через `/plugin marketplace add <repo-url>`.

Проверенные сторонние наборы:

| Набор | Что это | Источник |
|---|---|---|
| mattpocock/skills | каталог инженерных workflow-skills (`tdd`, `grill-me`, `prototype`, `to-issues`, `writing-*`…) | https://github.com/mattpocock/skills |
| stop-slop | вычищает из прозы AI-клише — для доков, статей, баг-репортов | https://github.com/hardikpandya/stop-slop |
| Anthropic-Cybersecurity-Skills | security-skills с привязкой к MITRE ATT&CK / NIST; Apache-2.0 | https://github.com/mukul975/Anthropic-Cybersecurity-Skills |
| claude-handoff | `/handoff:create` · `/handoff:resume` — передача контекста между сессиями через `HANDOFF.md` | https://github.com/willseltzer/claude-handoff |

Паттерн **LLM-Wiki** (двухдеревная база знаний: ingest/query/lint поверх markdown вместо RAG) —
первоисточник: gist Карпаты https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## Обновления

- Обнови клон, создай новый каталог экспорта, повтори preview и `install --apply` с прежними
  `--components`. Правь источник: сгенерированные файлы перезаписывает следующий экспорт.
- Для Claude marketplace сохраняется штатное обновление плагинов; rules и MCP обновляются отдельно.
- Новый skill = папка в `plugins/qa/skills/` или `plugins/pm/skills/`; exporter обнаружит её сам.

## Проверка изменений

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q --alluredir=allure-results
```

Это component-тесты инструмента настройки: эквивалентные разбиения по транспортам/клиентам,
негативные входные данные и переходы состояний установки. Проверяются TOML/JSON round trip,
повторяемость, preview, обновление, конфликты, целостность bundle и границы записи.
GitHub Actions запускает набор и сохраняет Allure results. Живые MCP endpoints и LLM не вызываются.

## Лицензия

MIT — см. [LICENSE](LICENSE). Производные сторонние skills (набор
[mattpocock/skills](https://github.com/mattpocock/skills), тоже MIT) и их происхождение —
в [NOTICE](NOTICE).
