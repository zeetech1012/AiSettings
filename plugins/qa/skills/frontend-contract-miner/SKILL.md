---
name: frontend-contract-miner
description: Анализирует frontend-репозиторий на React/Next.js, чтобы извлечь API-контракты, endpoints, формы request/response и «магические» строки ошибок (например, AUTH_ERRORS). Используй, когда документируешь backend-сервис на основе его frontend-потребителя.
---
# Frontend Contract Miner

> **Тонкий делегат.** Источник правды — sub-agent `frontend-contract-miner`
> (`~/.claude/agents/frontend-contract-miner.md`): у него полный workflow
> (+ validation regexes, auth-flow, file:line-маппинг), изоляция и `model: sonnet`.
> Этот skill только маршрутизирует.

## Что делать

Делегируй задачу одноимённому агенту через инструмент **Agent**
(`subagent_type: "frontend-contract-miner"`). Передай в prompt:

- путь к фронтенд-репозиторию (например `uspd-ui`);
- опционально — имя целевого backend-сервиса для сверки контракта.

Не дублируй здесь логику извлечения контракта — она живёт в агенте.
Если меняется методика — правится **агент**, не этот файл.
