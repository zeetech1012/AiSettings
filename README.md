# AiSettings — baseline для AI-агентов

Один репозиторий = общий сетап для **Claude Code, OpenAI Codex CLI, Gemini CLI, Cursor**:
правила (`AGENTS.md`), skills (открытый стандарт Agent Skills), sub-agents, состав MCP.
Секретов здесь нет и не будет — учётные данные каждый подставляет локально.

> Публичная версия командного baseline. Внутренние адреса заменены плейсхолдерами
> (`example.com`) — подставьте свои: Git-хостинг, трекер (Huly), вики (Docmost).

## Prerequisites

- **Git**: для клона этого репо достаточно HTTPS; свой Git-хостинг — по SSH-ключу.
- **Huly** (если используете): личный token для MCP `huly`.
- **Node.js** (npx) — MCP `context7` / `playwright`; **pnpm** — сборка huly-mcp; **uv** —
  только опциональные `gradle` / `allure`.

## Быстрый старт

Первый шаг общий для всех агентов:

```bash
git clone https://github.com/zeetech1012/AiSettings.git
cd AiSettings && ./install.sh
```

`install.sh` идемпотентен: раскладывает правила и шаблоны по установленным агентам, существующие
файлы не перезаписывает; повторный запуск показывает, какие копии правил отстали от baseline.

### Claude Code (основной сценарий)

```
/plugin marketplace add zeetech1012/AiSettings
/plugin install qa@ai-settings
```

Роль агента (кем он выступает) заполни в `~/.claude/CLAUDE.md` над строкой `@AGENTS.md`;
образец детализации — `claude/CLAUDE.example.md`. MCP — по `mcp/README.md`.

### Codex CLI / Gemini CLI / Cursor

- Skills симлинкаются в `~/.agents/skills` — Codex и Gemini читают их нативно.
- Codex читает `AGENTS.md` сам (роль — в начало личной копии `~/.codex/AGENTS.md`);
  Gemini — после `"context": {"fileName": ["AGENTS.md", "GEMINI.md"]}`.
- Cursor: глобальных правил у него нет — `AGENTS.md` кладётся в корень каждого рабочего
  репозитория; из baseline он получает только правила и MCP (см. «Почему CLI-агент» ниже).
- MCP-конфиги per-client: `mcp/codex.toml`, `mcp/gemini.settings.json`, `mcp/README.md`.

## Что внутри

```
AGENTS.md                     ← командные правила (agent-agnostic)
claude/CLAUDE.md              ← @AGENTS.md + Claude-специфика
claude/CLAUDE.example.md      ← полный CLAUDE.md автора в оригинале — образец детализации;
                                секция роли персональная, заполняется под себя
claude/settings.json          ← шаблон: effortLevel, allowlist, marketplaces, плагины
.claude-plugin/marketplace.json  ← этот репо = Claude-marketplace
plugins/qa/                   ← плагин: 10 skills + 6 sub-agents
  skills/    write-test · test-case-generator · service-doc · review · review-test ·
             diagnose · debug-test · occams-razor · code-to-wiki-docs · kaspresso-compose-qa-guru
  agents/    project-researcher · go-service-explorer · frontend-contract-miner ·
             swagger-to-pydantic · repo-security-auditor · link-integrity-validator
mcp/                          ← состав MCP в трёх форматах + что подставить лично
install.sh                    ← раскладка по установленным агентам (идемпотентен)
```

## Три корзины (что здесь, чего здесь нет)

| Корзина | Где живёт |
|---|---|
| 🟢 Общее (правила, skills, состав MCP) | **этот репозиторий** |
| 🟡 Стек-специфичное (проектные `CLAUDE.md`/`AGENTS.md`, узкие skills) | в репозитории проекта |
| 🔴 Личное (токены, ключи, пути, личная база знаний) | `settings.local.json` / ENV — **не сюда** |

## Почему CLI-агент (Claude Code / Codex), а не IDE-форк (Cursor / Windsurf)

Baseline рассчитан на CLI-агенты как основной инструмент. Причины конкретные:

- **Полнота baseline.** Skills, sub-agents, hooks и плагин `qa` исполняются в Claude Code
  (Codex / Gemini — skills + `AGENTS.md`). IDE-форки берут из этого репозитория только `AGENTS.md`
  из корня проекта и состав MCP: командные процедуры (`/write-test`, `/service-doc`, `/review`)
  там недоступны.
- **IDE-независимость.** Стеки живут в Android Studio (Kotlin/KMP), Xcode (Swift/XCUITest)
  и GoLand / VS Code (Go). Cursor и Windsurf — форки VS Code, мобильные IDE они не заменяют;
  CLI-агент запускается в терминале любой из этих сред, рядом с реальной сборкой и отладкой.
- **Headless и автоматизация.** `claude -p` / `codex exec` работают без интерфейса: CI,
  cron-прогоны, удалённые машины по SSH. IDE-форку нужно открытое окно редактора.
- **Прямой контракт с провайдером.** CLI ходит к Anthropic / OpenAI напрямую под корпоративной
  подпиской; у IDE-форков код и промпты проходят через инфраструктуру третьей стороны, а лимиты
  и версии моделей определяет посредник.
- **Обновляемость.** Правила и состав MCP приезжают через `git pull` + marketplace `autoUpdate`;
  в IDE-форках конфигурация правится руками в GUI на каждой машине.

Cursor остаётся поддерживаемым вторичным клиентом: правила + MCP, без skills / sub-agents /
плагинов и headless-режима.

## Open-source стек (что скачать)

Весь сетап стоит на open-source. Ссылки на upstream (секретов нет — подставляется локально):

### MCP-серверы (состав — `mcp/`)

| Сервер | Пакет / бинарь | Источник |
|---|---|---|
| `codegraph` | бинарь `codegraph` | https://github.com/colbymchenry/codegraph |
| `context7` | `@upstash/context7-mcp` (npx) | https://github.com/upstash/context7 |
| `playwright` | `@playwright/mcp` (npx) | https://github.com/microsoft/playwright-mcp |
| `learn-go-with-tests` | HTTP (GitBook) | https://github.com/quii/learn-go-with-tests |
| `huly` | пропатченная сборка `huly-mcp` (node) | https://github.com/zeetech1012/huly-mcp — форк; upstream npm `@firfi/huly-mcp` |
| `obsidian` | плагин Obsidian «Local REST API with MCP» (v4+, HTTPS :27124, endpoint `/mcp/`) | https://github.com/coddingtonbear/obsidian-local-rest-api |
| `gradle` (опц.) | `gradle-mcp` (uv) | путь/источник — в `mcp/README.md` |
| `allure` (опц.) | `mcp-allure` (uv) | локальный сервер — путь в `mcp/README.md` |

### Инструменты рабочей станции

| Инструмент | Назначение | Источник |
|---|---|---|
| gitleaks | секреты в git-истории/дереве | https://github.com/gitleaks/gitleaks |
| semgrep (CE) | SAST (Go/Kotlin/Swift) | https://github.com/semgrep/semgrep |
| OWASP ZAP | DAST (baseline / api-scan) | https://github.com/zaproxy/zaproxy |
| garak (NVIDIA) | red-teaming LLM: prompt injection, jailbreak, утечки — гонять против своих LLM-фич и ботов | https://github.com/NVIDIA/garak |
| Docker Engine | контейнеры | https://github.com/moby/moby |
| Obsidian | личная база знаний | https://obsidian.md (проприетарный, free) |
| Meetily | локальный AI-протокол встреч: Whisper.cpp-транскрипция + суммаризация (Ollama/Claude), данные не уходят в облако | https://github.com/Zackriya-Solutions/meetily |

### Self-hosted инфраструктура

| Сервис | Роль | Источник |
|---|---|---|
| Huly | трекер + TMS + доки | https://github.com/hcengineering/huly-selfhost (ядро: `hcengineering/platform`) |
| Docmost | командная вики | https://github.com/docmost/docmost |
| GitLab CE | VCS + CI | https://gitlab.com/gitlab-org/gitlab |
| Allure | отчёты | https://github.com/allure-framework/allure2 · docker: https://github.com/fescobar/allure-docker-service |

### Skills и sub-agents

- **Этот репозиторий** = плагин `qa` (skills + sub-agents), ставится через marketplace (см. «Быстрый старт»).
- Открытый стандарт **Agent Skills** — папка-скилл с `SKILL.md`; свои skills кладите в `plugins/qa/skills/` + push.
- Сторонние Claude-плагины (handoff, understand-anything и т.п.) — ставятся через `/plugin marketplace add <repo-url>`.

Проверенные сторонние наборы (Agent Skills — работают в Claude Code / Codex / Cursor / Gemini CLI):

| Набор | Что это и зачем агенту | Источник |
|---|---|---|
| mattpocock/skills | каталог инженерных workflow-skills (`tdd`, `grill-me`, `prototype`, `to-issues`, `writing-*`…) — готовые процессы разработки/планирования/письма; `npx skills add mattpocock/skills` или Claude-плагин | https://github.com/mattpocock/skills |
| stop-slop | один skill: вычищает из прозы AI-клише («вода», штампы, бинарные контрасты) — подключать при написании доков, статей, баг-репортов | https://github.com/hardikpandya/stop-slop |
| Anthropic-Cybersecurity-Skills | 817 security-skills по 29 областям (threat hunting, malware analysis, forensics, red team) с привязкой к MITRE ATT&CK / NIST — для security-аудитов силами агента; Apache-2.0 | https://github.com/mukul975/Anthropic-Cybersecurity-Skills |
| claude-handoff | плагин `/handoff:create` · `/handoff:quick` · `/handoff:resume` — передача контекста между сессиями/агентами через `HANDOFF.md` (поверх него — двухуровневая схема ephemeral + vault, см. `AGENTS.md`) | https://github.com/willseltzer/claude-handoff |

Паттерн **LLM-Wiki** (двухдеревная база знаний в Obsidian: ingest/query/lint поверх
markdown-вики вместо RAG) — первоисточник: gist Карпаты
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## Обновления

- `git pull` в клоне: skills подхватываются сразу (symlink), плагин Claude — через `autoUpdate`
  маркетплейса.
- Копии правил (`~/.claude/AGENTS.md`, `~/.codex/AGENTS.md`) сами не обновляются: повторный
  `./install.sh` покажет, какие отстали от baseline; слить — вручную по diff.
- Новый skill = папка в `plugins/qa/skills/` + push.

## Лицензия

MIT — см. [LICENSE](LICENSE).
