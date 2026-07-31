---
name: swagger-to-pydantic
description: Автоматически генерирует или обновляет Pydantic v2 модели из файла спецификации Swagger/OpenAPI. Выявляет breaking changes. Используй, когда обновлена спецификация backend API.
---
# Swagger to Pydantic Generator

> **Тонкий делегат.** Источник правды — sub-agent `swagger-to-pydantic`
> (`~/.claude/agents/swagger-to-pydantic.md`): он реально гоняет
> `datamodel-codegen` и считает diff против предыдущих моделей.
> Этот skill только маршрутизирует.

## Что делать

Делегируй задачу одноимённому агенту через инструмент **Agent**
(`subagent_type: "swagger-to-pydantic"`). Передай в prompt:

- источник спеки (URL или локальный `openapi.json`/`swagger.yaml`);
- целевой `services/<name>/models.py`.

Не дублируй здесь генерацию/диф — они живут в агенте. Жди от агента
сводку обновлённых моделей и секцию breaking changes.
Если меняется методика — правится **агент**, не этот файл.
