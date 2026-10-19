---
name: go-service-explorer
description: Анализ Go backend-репозитория для извлечения routes, middleware, RBAC rules и структур payload. Используется, чтобы держать Markdown API documentation в синхронизации с фактическим Go source code.
---
# Go Service Explorer

> **Тонкий делегат.** Источник правды — sub-agent `go-service-explorer`
> (`~/.claude/agents/go-service-explorer.md`): он содержит полный workflow,
> запускается изолированно и параллелится. Этот skill только маршрутизирует.

## Что делать

Делегируй задачу одноимённому агенту через инструмент **Agent**
(`subagent_type: "go-service-explorer"`). Передай в prompt:

- путь к Go-репозиторию;
- целевой файл `docs/<service>.md`, который нужно создать/обновить.

Не дублируй здесь логику извлечения routes/RBAC/payloads — она живёт в агенте.
Если меняется методика — правится **агент**, не этот файл.
