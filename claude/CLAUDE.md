@AGENTS.md

## Claude Code — специфика поверх общих правил

- Повторяемые процедуры — через skills (`/write-test`, `/service-doc`, `/review`, `/diagnose`,
  `/handoff` и т.д.): если задача совпадает с описанием skill'а — вызывай его, не изобретай флоу.
- Исследование незнакомого репозитория — sub-agents `project-researcher` / `go-service-explorer` /
  `frontend-contract-miner`; перед правкой — impact-анализ через MCP `codegraph`.
- Актуальная документация библиотек — MCP `context7` (не отвечай по памяти о версиях API).
