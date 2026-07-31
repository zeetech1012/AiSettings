---
name: docmost-qa-strategy
description: >
  Используй этот навык, когда генерируешь или исправляешь Markdown-документацию, которая должна
  корректно рендериться в Docmost, либо когда формируешь QA-стратегию для мобильного приложения на Kotlin Multiplatform + Compose.
  Triggers on: "докумен под docmost", "docmost", "вики-статья", "оформи для вики",
  "collapsible", "callout", "qa стратегия kmp", "qa strategy", "тест-стратегия mobile",
  "пирамида тестов compose". Работает в паре с [code-to-wiki-docs] для процесса генерации.
---

# Docmost Documentation & KMP QA Strategy

Гайдлайн из двух частей: (1) как форматировать Markdown, чтобы он корректно рендерился в
**Docmost**; (2) как раскладывать QA-стратегию для **KMP + Compose Multiplatform** приложения.

## 1. Docmost-совместимый Markdown

- **Collapsible** — длинные технические блоки оборачивать:
  ```html
  <details>
  <summary><b>Section Title</b></summary>

  Контент (оставить пустую строку после summary, иначе Markdown внутри не отрендерится).
  </details>
  ```
- **Callouts** — GitHub-style: `> [!info]`, `> [!tip]`, `> [!warning]`, `> [!caution]`.
- **Иерархия заголовков** (`##`/`###`) — и внутри, и снаружи `<details>`: Docmost строит из
  них оглавление страницы. Не пропускать уровни.
- **Таблицы** — стандартный Markdown для структурированных данных (сравнения, «экран → файл»).
- **Мета-блок аудитории** — каждую статью начинать с `> **Аудитория:** …`, чтобы читатель
  сразу понимал, его это раздел или нет.

## 2. QA-стратегия для KMP + Compose

Покрытие тремя слоями, маппить на реальную структуру (`composeApp/src/...`):

### 2.1 Unit (commonTest, JVM-хост)
- Стек: `kotlin-test` + `kotlinx-coroutines-test` + Turbine.
- Цель: ViewModels (MVI/state-машины), UseCases, мапперы, validation rules.
- Правило: проверять эмиссии состояний и edge-cases (обрыв связи, таймаут, ошибка репозитория).
  `Dispatchers.setMain(StandardTestDispatcher())` до конструирования VM; виртуальное время.

### 2.2 Integration
- Стек: in-memory SQLite driver (SQLDelight), Ktor `MockEngine`.
- Цель: запросы к БД, сетевая логика репозиториев.
- Правило: проверять обработку 401/500/timeout и кэширование.

### 2.3 UI / Functional (androidInstrumentedTest)
- Стек: Kaspresso (`kaspresso-compose-support`) + Allure-Kotlin.
- Цель: E2E-флоу (онбординг, авторизация, pairing устройства).
- Правила (жёстко): локаторы **только `testTag`** через `ComposeScreen` + `KNode` (не `R.id`,
  не `KScreen`); **нет `Thread.sleep`** (→ `flakySafely`); изоляция Screens (локаторы) /
  Robots (взаимодействия) / Scenarios (GWT+AAA-логика).
- Реальный граф поверх фейка через Koin override — а не фейк-UseCase.

## 3. Общие требования
- Факты в доке помечать «проверено», если верифицированы по исходникам; не выдумывать.
- Отражать архитектурные ограничения (напр. iOS SIGABRT на enum-аргументах навигации → нужен
  кастомный `typeMap`/`navType()`).
- Держать доку в синхроне с кодом: при изменении архитектуры — обновить статью.
