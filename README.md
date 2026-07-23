# AiSettings — Claude Code marketplace

Плагин-маркетплейс для **Claude Code**: QA/dev skills и исследовательские sub-agents одним
пакетом. Правила работы и рекомендуемый состав MCP команда получает отдельно — через
онбординг-гайд Claude Code (см. «Как это устроено»). Секретов здесь нет и не будет.

> Личный проект автора. Публичный контент обезличен плейсхолдерами (`example.com`) —
> внутренние адреса (Git-хостинг, трекер Huly, вики Docmost) каждый подставляет локально.

## Установка плагина

В Claude Code:

```
/plugin marketplace add zeetech1012/AiSettings
/plugin install qa@ai-settings
```

Skills и sub-agents подхватываются сразу; обновления приезжают через `autoUpdate` маркетплейса.

## Как это устроено

Сетап разнесён на два слоя с разными каналами доставки:

| Слой | Что | Канал | Обновление |
|---|---|---|---|
| Артефакты | 12 skills + 7 sub-agents (плагин `qa`) | **этот marketplace** | автоматически (`autoUpdate`) |
| Правила + MCP | глобальный `CLAUDE.md`, состав MCP, инструменты | **онбординг-гайд Claude Code** (`/team-onboarding`, ссылка внутри команды) | вручную: перезалив гайда → сверка |

Плагин не умеет нести always-on правила, поэтому они живут в онбординг-гайде и копируются
в `~/.claude/CLAUDE.md` один раз. Канонический текст правил — `AGENTS.md` в этом репозитории.

## Что внутри

```
AGENTS.md                        ← канонический текст правил (роль — персональная, в личном CLAUDE.md)
claude/CLAUDE.md                 ← @AGENTS.md + Claude-специфика
claude/CLAUDE.example.md         ← образец детализации (секция роли заполняется под себя)
claude/settings.json             ← шаблон: effortLevel, allowlist, marketplaces, плагины
.claude-plugin/marketplace.json  ← этот репозиторий = Claude-marketplace `ai-settings`
plugins/qa/                      ← плагин: skills + sub-agents
  skills/    write-test · test-case-generator · service-doc · review · review-test · diagnose ·
             debug-test · occams-razor · code-to-wiki-docs · kaspresso-compose-qa-guru ·
             huly-team-work · huly-service-issue
  agents/    project-researcher · go-service-explorer · frontend-contract-miner ·
             swagger-to-pydantic · repo-security-auditor · link-integrity-validator · scrum-master
mcp/                             ← шаблон состава MCP (mcp.json) + что подставить лично (README.md)
```

## Три корзины (что здесь, чего здесь нет)

| Корзина | Где живёт |
|---|---|
| 🟢 Общее (правила, skills, состав MCP) | **этот репозиторий** + онбординг-гайд |
| 🟡 Стек-специфичное (проектные `CLAUDE.md`, узкие skills) | в репозитории проекта |
| 🔴 Личное (токены, ключи, пути, личная база знаний) | `settings.local.json` / ENV — **не сюда** |

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
| garak (NVIDIA) | red-teaming LLM: prompt injection, jailbreak, утечки | https://github.com/NVIDIA/garak |
| Docker Engine | контейнеры | https://github.com/moby/moby |
| Obsidian | личная база знаний | https://obsidian.md (проприетарный, free) |
| Meetily | локальный AI-протокол встреч (Whisper.cpp + суммаризация, данные не уходят в облако) | https://github.com/Zackriya-Solutions/meetily |

### Self-hosted инфраструктура

| Сервис | Роль | Источник |
|---|---|---|
| Huly | трекер + TMS + доки | https://github.com/hcengineering/huly-selfhost (ядро: `hcengineering/platform`) |
| Docmost | командная вики | https://github.com/docmost/docmost |
| Allure | отчёты | https://github.com/allure-framework/allure2 · docker: https://github.com/fescobar/allure-docker-service |

### Skills — открытый стандарт

- **Этот репозиторий** = плагин `qa` (skills + sub-agents), ставится через marketplace (см. «Установка»).
- Открытый стандарт **Agent Skills** — папка-скилл с `SKILL.md`; свои skills кладите в `plugins/qa/skills/` + push.
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

- **Skills / sub-agents** — плагином, `autoUpdate` маркетплейса; при желании `git pull` в клоне.
- **Правила** (`~/.claude/CLAUDE.md`) сами не обновляются: при изменении перезаливается
  онбординг-гайд, копию сверяешь по diff с `AGENTS.md`.
- Новый skill = папка в `plugins/qa/skills/` + push.

## Лицензия

MIT — см. [LICENSE](LICENSE).
