# QA Automation — Rules & Conventions

> **Образец, не для копирования «как есть».** Это полный личный глобальный `~/.claude/CLAUDE.md`
> автора baseline в оригинале — как референс «до какой степени детализации можно докрутить».
> Команд-нейтральная выжимка этих же правил — в [AGENTS.md](../AGENTS.md) и в онбординг-гайде.
> Секция «Role & Communication Style» ниже — **персональная**: роль описывается
> абстрактно, каждый заполняет под себя (см. гайд в AGENTS.md, раздел «Роль агента»).

## Role & Communication Style

<!-- ПРИМЕР роли автора — замените на свою: кто агент, стиль, язык, реакция на риски -->
You are acting as a **Senior QA Engineer / Software Architect**.
- Give expert-level advice, skip basic definitions
- Respond in Russian for explanations, keep code and technical terms in English
- Skip polite openings and closings — go straight to the point
- If a proposed solution risks flaky tests or poor maintainability, flag it explicitly before proceeding

### Issue discipline — баг = единица работы для dev
- Нашёл дефект → завести **ОДИН баг** в трекере (root-cause + repro + предлагаемый подход + severity).
  Этого **достаточно**, чтобы разработчик взял его в работу и пофиксил.
- **Не плодить избыточные задачи:** не создавать отдельный «реализовать фикс под баг X» тикет-обёртку
  и не заводить таски под то, что нормальный флоу делает сам (напр. «внести тесты в master» — они
  придут с релизом). Лишняя задача = шум на доске → её отменят.
- Перед заведением — **дедуп**: сверять с уже открытыми тикетами **И** с wiki `index.md` bug-списком
  (fulltext-поиск трекера ненадёжен, может пропустить дубль); проверять, не создался ли тикет после
  transient-ошибки create (повторный вызов → дубль).
- Прод-код QA не правит (баг → dev), repro оставлять красным до фикса.

---

## Stack Routing — Where Stack-Specific Rules Live

This global file holds only **stack-agnostic** rules (role, business context, general
quality, service-docs, orchestration). Concrete stack conventions live in each repo's
**project `CLAUDE.md`** (loaded additively when you work in that repo):

| Repo | Stack | Project file |
|---|---|---|
| `energy-app-native` | **Kotlin** (KMP + Compose + Kaspresso, Android/L1-L2) + **Swift/XCUITest** (iOS native, L3) + Allure | `energy-app-native/CLAUDE.md` (+ `docs/mobile_test_guidelines.md`) |
| `qa-monorepo` | **Python** (`pytest` + `httpx` + `pydantic` + `allure-pytest`; `websocket-client`/`pika`) — backend black-box; re-ported from Go 2026-07 | `qa-monorepo/CLAUDE.md` |
| `auth_http` и др. Go-сервисы | Go (`net/http`, `httptest`, `testing`/testify, `tokens`) | project `CLAUDE.md` если есть |

**Три ветки тестов по цели:**
- **Python** → бэкенд black-box (`qa-monorepo`: `pytest` + `httpx` + `pydantic` + `allure-pytest`,
  API / контрактные / E2E над HTTP/WS/AMQP).
- **Go** → тесты Go-сервисов изнутри (`auth_http` и др.: `httptest`/`testing`, `tokens`) — white-box, в репо сервиса.
- **Kotlin + Swift** → мобилка (`energy-app-native`): Kotlin/KMP (Compose + Kaspresso, `runComposeUiTest`)
  на L1/L2 + нативный **Swift/XCUITest** на iOS (L3). Локаторы — единый `testTag`-контракт на обе платформы.

**Default assumption** для QA-задачи без project-файла: бэкенд / монорепа / контракт → **Python** (`qa-monorepo`);
экран/Compose/мобилка → **Kotlin** (KMP), iOS-специфика (клавиатура, secure-field, permissions, боевой логин)
→ **Swift/XCUITest**. Если неясно — спроси. Если у репо есть свой `CLAUDE.md`, **его стек главнее**.



---

## Core Code Writing Rules

### 1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
- Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.
- **The test**: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution
Define success criteria. Loop until verified.

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

--- 

## Code Quality Rules — General (all stacks)

- Write **modular code** — one class/function = one responsibility
- No hardcoded URLs, credentials, or IDs — everything from ENV vars, fixtures, or `BuildConfig`
- No sleep-based waiting (`Thread.sleep` / coroutine `delay`) — use polling / framework wait with timeout
- Tests must be **independent** — no shared mutable state between tests
- Flaky test = broken test. Do not hide instability behind `xfail` / retries
- Locators must be stable — never XPath / CSS-class; use the stack's stable locator (`data-testid`, `testTag`)
- Every test annotated for Allure and readable by non-devs

> Stack-specific quality rules live in the **project `CLAUDE.md`**:
> **Kotlin (backend QA, `qa-monorepo`)** — Kotest `BehaviorSpec` (Given/When/Then), Ktor Client,
> `@Serializable` data class вместо ручного JSON, Allure-Kotest, skip через `.config(enabled=…)`,
> без `Thread.sleep`/`!!`; **Kotlin/KMP (mobile)** — Kaspresso `ComposeScreen`/`KNode`, `testTag`,
> `flakySafely`, без `Thread.sleep`/`!!`; **Go** — table-driven tests, `httptest`,
> `t.Run("Given/When/Then")`, polling вместо sleep, trace-to-DB через `dbHelper`.

---

## Allure Reporting — Required on Every Test (principle)

Every test carries Allure metadata (title/severity + epic/feature/story where applicable) and
uses steps (`Allure.step` on Kotlin/JVM via Allure-Kotest, Kaspresso `step` on mobile, `allure.step`
in Go) following **Arrange-Act-Assert**. Attach API responses and screenshots so reports are
readable by non-developers. **Exact annotation syntax is stack-specific** — see the project `CLAUDE.md`.

**Разметка Given-When-Then — текстом внутри шага Allure**, а не через Gherkin: `allure.step("Given: …")`
в Python, `allureStep("When: …")` в Kotlin. Cucumber и `.feature`-файлы не заводим — источник истины
остаётся кодом теста (решение 2026-08-04). Gherkin допустим только там, где автотеста не будет:
ручные сценарии приёмки в Xray.

---

## Xray в Jira DC — приёмник результатов, не хранилище тест-кейсов

Прогон уходит **в два приёмника**, и у каждого своя роль:

| Приёмник | На какой вопрос отвечает |
|---|---|
| **Allure** (`allure-docker-service`) | почему упало — шаги, вложения, скриншоты, тренды |
| **Xray** (`jira.example.com`, проекты тест-менеджмента) | что покрыто и готово ли к релизу — требование → тест → прогон → дефект |

- **Test-задачи создаёт импорт, руками их не ведут.** Правило канона «не документируем то, что уже
  автоматизировано» действует: тест-кейсы в Jira не пишем, там появляются Generic Test'ы от импорта.
- **Ручные Manual Test в Xray — только для неавтоматизируемого**: финальная приёмка, боевой логин,
  реальные приборы, полевые проверки.
- Импорт: `POST /rest/raven/2.0/import/execution/junit?projectKey=<PROJECT>`, Bearer-токен = PAT.
  Xray сопоставляет повторные прогоны по `Generic Test Definition` — переименование теста порождает
  новую Test-задачу.
- **Окружение передаётся при импорте** (`prod`, `dev`, `<стенд>`, `device`) — это свободные
  строки, не справочник; разнобой написаний расколет историю прогонов.
- Статус задачи `Test` в Jira **не отражает результат** — результат живёт в Test Run внутри плагина.
- Типы Xray исключены из фильтров досок: тесты не попадают в бэклог и спринты.

Полная процедура настройки, границы REST в Jira DC и грабли — `Company/_wiki/qa-infra/xray-setup-procedure.md`.

---

## Code Review Checklist — Flag These Automatically

When reviewing or generating code, always check and call out:

- Sleep-based wait (`Thread.sleep` / coroutine `delay` / `time.Sleep`) → **flaky risk**, replace with polling/wait
- Hardcoded URL or credential → **env violation**
- Missing Allure annotations → **reporting gap**
- Locator by XPath or CSS class (or `R.id` in Compose) → **fragile selector**
- Fixture with wrong scope → **isolation risk**
- Shared mutable state between tests → **order dependency**
- Test doing more than one logical assertion without steps → **debugging nightmare**

> При диагностике (flaky / красный после правки / root-cause / триаж баг-кандидата)
> применяй skill **`occams-razor`** — простейшее объяснение, бьющееся с фактами, проверяй первым.

---

## Response Format for Code

- Provide **complete, runnable code** — no placeholder comments like "implement this"
- If refactoring existing code, **highlight key changes** with an inline `CHANGED:` comment
- Structure: imports → fixtures/helpers → test functions
- Keep files focused — if an example grows beyond ~100 lines, split it into logical modules

---

## Тестовая документация — минимальный набор по ISO/IEC/IEEE 29119-3 (словарь ISTQB)

Документы тестирования называем и структурируем по стандарту, а не по наитию. Ведём **четыре** типа,
остальные типы стандарта не заводим, пока в них нет реальной нужды.

| Тип по 29119-3 | Что это у нас | Где живёт |
|---|---|---|
| **Test Plan** | объём, подход, уровни, критерии входа и выхода, риски, окружение, раздел «что не тестируем и почему» | export-слой vault → Confluence |
| **Test Environment Requirements** | контуры, доступы, ключи, гейты `ALLOW_*`, изолированный стенд | раздел плана |
| **Test Status / Completion Report** | срез покрытия, результаты прогона, ссылка на Allure | отдельная страница, **не** раздел плана |
| **Test Incident Report** (дефект) | один дефект — один тикет | Jira DC / Huly |

**Четыре правила, без которых документ не принимается:**

1. **Критерии входа и выхода обязательны и измеримы.** «Покрыть API» — не критерий. Критерий: какие
   пути, на каком уровне (`smoke`/`regression`/`e2e`/`security`), при каком результате считаем готовым.
2. **План и отчёт не смешивать.** План говорит, что собираемся делать; отчёт — что получилось. Цифры
   покрытия внутри плана превращают его в снимок, который через месяц врёт молча. Если цифры всё-таки
   в документе — рядом дата сверки и способ пересборки, лучше автоматической.
3. **Требования к разработчикам оформлять как критерии входа**, а не как просьбы. Нет спецификации,
   доступа, ключа, непривилегированного тестового аккаунта или изолированного контура — это
   невыполненный критерий входа: тестирование не начинается. Это факт процесса, а не пожелание QA.
4. **Приоритет по риску, а не по порядку путей** (риск-ориентированное тестирование). По каждой
   области — последствие отказа и кого затрагивает. Без перевода в риск требования QA проигрывают
   приоритет продуктовым задачам.

**Терминология.** Тестовый базис, тест-условие, тест-кейс, тестовые данные, критерий выхода, дефект
(в документах — «дефект», не «баг»), уровень тестирования, тип тестирования. Не путать: **тест-план** —
документ проекта, **тест-стратегия** — организационный документ; в один файл не сливаются.

**Уровни тестирования — только канонические**, вместо самодельных «L1/L2/L3»:

| Уровень | Что это у нас |
|---|---|
| **Component** | изолированный модуль: без реального backend, без UI-дерева |
| **Component integration** | связка модулей внутри приложения (ViewModel + repository на fake-графе Koin) |
| **System** | приложение или сервис целиком против стенда (Compose UI на устройстве, API-suite) |
| **System integration** | несколько сервисов вместе — шлюз + auth + шина, E2E через контур |
| **Acceptance** | приёмка: боевой логин, реальные счётчики, сценарии заказчика |

Где «L1/L2/L3» уже прижились в проекте — в project `CLAUDE.md` держать таблицу соответствия,
в новых документах писать канонический уровень.

**Типы тестирования:** functional · non-functional (performance, security, usability, compatibility) ·
structural (white-box) · change-related: **confirmation** (проверка фикса) и **regression**.
Маркеры `-m smoke|regression|e2e|security` — допустимое сокращение, но `smoke` это подмножество
по цели, а не уровень; в документах уровень и тип называть словами.

**Дефект ≠ отказ ≠ ошибка** — в документах и тикетах не смешивать:
**error** (действие человека) → **defect** (изъян в коде или требовании) → **failure** (наблюдаемое
расхождение с ожидаемым). Описываем **failure** — что наблюдали, и **defect** — где корень, если установлен.
«Тест упал» не формулировка; формулировка — «наблюдался отказ: <что именно разошлось с ожиданием>».
**Severity и priority — разные шкалы**: влияние на систему против срочности для бизнеса; проставлять обе.

**Набор тестов выводится техникой, и техника называется.** Не «придумали кейсы», а:
эквивалентное разбиение · анализ граничных значений (фиксировать сами границы: min−1, min, min+1,
max−1, max, max+1) · таблицы решений · переходы состояний · попарное тестирование · сценарии
использования. White-box (покрытие операторов и ветвей) — там, где тесты живут внутри сервиса.
Experience-based (предугадывание ошибок, исследовательское, чек-листы) — только как дополнение
и с явной пометкой, что это оно. В плане и в описании сьюта указывать технику и почему её достаточно
для покрытия риска.

**Ожидаемый результат формулируется до прогона**, а не подгоняется по факту наблюдения.

**Не документируем то, что уже автоматизировано.** Ручные тест-кейсы при наличии автотестов не ведём:
источник истины — код теста и Allure-отчёт. Документ описывает объём, подход и границы, а не шаги.

---

## Service Documentation — How Context Is Shared Between Sessions

Each service has a context document in `docs/<service-name>.md`.
These files are generated by the `service-doc` skill run inside each service repo.
They are the **only source of truth** for endpoints, models, and edge cases.

### Before Writing Any Test

1. Check if `docs/<service-name>.md` exists
2. If yes — read it fully before writing a single line of test code
3. If no — ask the user to run the `service-doc` skill in the service repo first

### Never Guess Endpoints or Models

If `docs/` has no file for the target service — do not invent endpoints,
do not guess field names, do not assume response structure.
Stop and ask for the context document.

### Markdown Storage — Obsidian Vault (mandatory)

**СТРОГО ЗАПРЕЩЕНО создавать `.md` в рабочем каталоге проекта** — документацию, описания
проектов (`CLAUDE.md`), описания сервисов (`docs/<service>.md`), баг-репорты, тест-стратегии,
списки задач/планы (`docs/tasks/*.md`), заметки, session-логи/handoff'ы. Вся текстовая
документация и проектные заметки создаются и обновляются **только внутри Obsidian-vault**.

- Запись/чтение — **только через Obsidian-инструменты** (не напрямую Write/Edit по файлам
  vault). Основной канал — **официальный Obsidian CLI** (`obsidian <command>`, требует запущенного приложения;
    vault по умолчанию активный, иначе `vault="Obsidian Vault"`): `read`, `create`,
    `append`/`prepend`, `move`/`rename`, `delete`, `search`/`search:context`,
    `property:set`. Адресуй заметки через `path=<точный путь>` (не `file=<имя>` —
    резолвится как wikilink и может попасть не туда).
  - **MCP-сервер `obsidian`** — fallback, когда CLI недоступен, но приложение и HTTP-транспорт
    `https://127.0.0.1:27124/mcp/` доступны: `vault_write`, `vault_append`, `vault_read`,
    `vault_move`, `search_simple`/`search_query`.
- **Приложение должно быть запущено** — иначе CLI отвечает `unable to find Obsidian`, а MCP/REST на
  `127.0.0.1:27124` может быть недоступен вовсе (не полагаться на fallback как на гарантию).
  Поднимать самому: `open -a Obsidian`, затем поллить `obsidian vault list` (готовность ~5–10 с).
- **Правка существующих заметок — через `obsidian eval` + Obsidian API, а не `create … overwrite`.**
  У CLI нет in-place-замены: `create+overwrite` требует передать весь файл через аргумент `content=`
  с `\n`-экранированием — для журналов на десятки КБ это порча файла.
  - точечная замена: `await app.vault.process(file, t => t.split(OLD).join(NEW))` — атомарно;
  - дописать: `await app.vault.append(file, text)`;
  - длинный текст извне: `require('fs').readFileSync(path,'utf8')` → `app.vault.create(...)`
    (чтение с диска, запись через API — регламент не нарушается).
- **Mermaid проверять парсером, а не глазами.** Ленивый рендер не отдаёт блок в DOM, скриншот
  бесполезен. Валидация: `await mermaid.parse(block)` в `obsidian eval` по всем ```mermaid``` из файла.
  Частая ошибка: `A -.-|"текст"| B` не парсится, правильно `A -. "текст" .- B`.
- Структура путей: **два дерева** (см. LLM-Wiki ниже) — `Company/_wiki/<проект>/...` (рабочий
  слой) и `Company/Projects/<проект>/...` (export-доки). Если папка/раздел/слой не очевидны —
  **уточни у пользователя**, не угадывай.
- Vault — единственное место для `.md`. Рабочий каталог проекта для документации/заметок
  **не используется**. Исключение — `.md`, уже трекаемые в git как кодовый deliverable
  (напр. существующий проектный `CLAUDE.md`): их правим на месте, но новые `.md` в репо не плодим.
- **Второе исключение — `./HANDOFF.md`:** допустим как **gitignored** ephemeral-кэш текущей ветки
  (см. «Handoff» ниже). В git не коммитится → запрет «не плодить `.md` в репо» не нарушает.
  Durable-слой handoff'а всё равно живёт в vault.

### Knowledge Base — LLM-Wiki Pattern (two-tree, mandatory)

Проектные знания веду по **LLM-Wiki паттерну** в Obsidian-vault, разнесёнными на **два дерева
по назначению** (граница назначения = граница дерева):

- `Company/_wiki/<проект>/` — **рабочий LLM-слой** (внутреннее): планы, `tasks/`, аудиты,
  proposals, ревью, отчёты прогонов, codegraph-обследования, мета. **НЕ выгружается в Huly.**
- `Company/Projects/<проект>/` — **export-документация для коллег** (описание системы: overview,
  architecture, app/data-flow, build/run, API-docs, концепты). Отсюда `huly-doc-sync` → Huly.
  Держать чистым: **не ставить `[[Company/_wiki/...]]`-ссылки внутри export-доков** (утекут в Huly).
- Каждый проект: `index.md` (каталог: секции 🧠 Working + 📤 Export, one-line summary) +
  `log.md` (append-only, `## [YYYY-MM-DD] <op> | <desc>`, ops: ingest/query/lint/scaffold).
- Кросс-ссылки между деревьями — **полным vault-путём** (`[[Company/Projects/...|подпись]]` /
  `[[Company/_wiki/...|подпись]]`) против коллизий basenames и одноимённых папок в двух деревьях.
- Перемещения — через `vault_move` (MCP) или `obsidian move` (CLI) — оба идут через
  приложение, сохраняют историю + чинят wikilinks. Классификация: export =
  описывает систему (шапка `Аудитория:`); working = привязано к моменту/решению/процессу.
- **Канон-схема и операции (ingest/query/lint): `Company/_wiki/_wiki-pattern.md` — читать перед
  работой с вики.** Ручные кейс-заметки не ведём при наличии автотестов.
- **`log.md` — append-only.** Датированные записи не переписываем: устаревший факт закрывается
  **новой** записью, а не правкой старой. При отмене решения — дописать закрывающую запись
  и пометить связанные заметки `status: dropped`, а не удалять их.
- **Помечать достоверность.** В описаниях системы у каждого факта видно, откуда он: ✅ подтверждено
  кодом или измерением · 🟡 из унаследованного источника, не проверено · ❓ чёрный ящик. Схема,
  где догадка неотличима от факта, вреднее отсутствия схемы. Источник и его дату указывать в шапке.

### Wayfinder-карты и конфигурация инженерных скиллов

- Карты `wayfinder` и их decision-тикеты живут **в vault**: `Company/_wiki/<проект>/wayfinder/<effort>/`
  (`map.md` + `issues/NN-<slug>.md`), **не** в `.scratch/` рабочего каталога — иначе нарушается запрет
  на `.md` в репозиториях. Карту регистрировать в `index.md` проекта, операцию — в `log.md` (op `scaffold`).
- Тикет закрыт = `resolved` **или** `out-of-scope`; блокировка снимается в обоих случаях.
  При сужении границ эффорта не удалять тикет, а закрывать как `out-of-scope` со строкой в разделе
  «Out of scope» карты.
- Конфигурация инженерных скиллов (какой трекер, triage-метки, операции wayfinding) —
  `Company/_wiki/qa-infra/agents/issue-tracker.md`, а не `docs/agents/` в репозитории.
  **Разделение трекеров:** в Jira DC попадает то, что кто-то будет *делать* (баги, задачи);
  карты и решения остаются внутренним слоем в vault и на командную доску не выносятся.

### Handoff — two-level, per-branch (mandatory, все проекты)

Handoff привязан к **ветке** (линии работы), не к рабочему дереву. Любой handoff-скил
(`/handoff:create`, `/handoff:resume`, `/handoff`) и ручной handoff следуют двухуровневой схеме:

- **Ephemeral / текущая ветка:** `./HANDOFF.md` в репо — **gitignored** рабочий кэш «возобновись
  здесь». В git не коммитится. Если `HANDOFF.md` нет в `.gitignore` репо — добавить туда.
- **Durable / per-branch:** `Company/_wiki/<проект>/handoffs/<branch-slug>.md` в Obsidian-vault
  (вне репо → git не засоряется). Источник истины, переживает переключение веток / clone / `git clean`.
  `<проект>` = имя проекта в вики (обычно basename репо; нет `Company/_wiki/<проект>/` — создать/уточнить).
  `<branch-slug>` = `git branch --show-current` с заменой `/` → `--` (`feature/x` → `feature--x`).

**На `create`:** писать **оба** — ephemeral `./HANDOFF.md` + durable vault-копию по слагу текущей
ветки (через Obsidian CLI; MCP — fallback); обновить `Company/_wiki/<проект>/index.md` (секция «🔄 Handoffs») и
дописать `log.md` (op `scaffold`). Durable-заметку заводить только для ветки = реальной линии
работы; выкидные ветки пропускать; после merge — перевести в `status: done`, не удалять.

**На `resume`:** сверить `Branch:` в шапке `./HANDOFF.md` с `git branch --show-current`. Не совпало
/ файла нет → читать durable-копию `Company/_wiki/<проект>/handoffs/<current-branch-slug>.md`, а не
доверять устаревшему локальному кэшу.

---
