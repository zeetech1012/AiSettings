---
name: review-test
description: >
  Используй этот навык, когда просят проревьюить, проверить, проаудитить или улучшить тестовый файл или тестовый код.
  Triggers on: "review my test", "check this test", "is this test ok", "audit test file",
  "what's wrong with this test", "improve this test". НЕ запускай для общего code review
  вне тестовых файлов.
---

# Test Code Review

Прогоняй проверки по порядку. На каждое нарушение: укажи строку/блок, объясни риск, дай фикс
inline. Не суммируй в конце — чини по ходу.

Канон-правила стека не дублируем — ссылайся на них:
- mobile — `Company/Projects/energy-app-native/mobile_test_guidelines.md` (раздел Anti-Patterns);
- общий чеклист — `~/.claude/CLAUDE.md` («Code Review Checklist — Flag These Automatically»).

Ниже — что проверять, в терминах нужного стека (Kotlin/Kaspresso или Go).

---

## Check 1 — Flakiness (BLOCKER)

- [ ] Kotlin: `Thread.sleep()` / coroutine `delay` → `flakySafely { ... }`. Go: `time.Sleep()` → polling-цикл с таймаутом
- [ ] Тест зависит от порядка выполнения (использует данные, созданные другим тестом) → FLAKY
- [ ] Shared mutable state между тестами → FLAKY
- [ ] Скрытое ожидание (`timeoutMs` без условия, голый таймаут) → polling по условию

## Check 2 — Hardcoded Values (BLOCKER)

- [ ] URL-литерал (`"https://..."`) → `BuildConfig` / ENV / `TestConfig`. Go — из config / ENV
- [ ] Креды в теле теста → `BuildConfig` / `QA_TEST_*` instrumentation args / фикстура
- [ ] Хардкод ID реальных записей БД → фикстура, которая создаёт и чистит данные

## Check 3 — Allure (REQUIRED)

- [ ] Нет `@Epic/@Feature/@Story/@Severity/@Tag` (Kotlin) или меток allure-go (Go) → добавить
- [ ] Нет `step(...)` / `Allure.step` вокруг блоков Arrange / Act / Assert → обернуть
- [ ] Нет attach ответа API или скрина → добавить после Act

## Check 4 — Locators (UI / mobile)

- [ ] Compose: основной локатор не `testTag` (используется `hasText`, попытка `R.id`) → `hasTestTag`. Priority: `testTag` > `contentDescription` > `text`
- [ ] Локатор объявлен inline в тесте → вынести в `ComposeScreen` (Page Object)

## Check 5 — Изоляция и фикстуры

- [ ] Фикстура создаёт ресурс без teardown → добавить очистку (в этом проекте — `logout()` в Rule, не `@Before`, не `pm clear`)
- [ ] Состояние протекает между тестами → изолировать

## Check 6 — Assertions

- [ ] Голый `assert` → Kaspresso DSL (`assertIsDisplayed`, `assertTextEquals`) / `testify`
- [ ] Один assert с несколькими условиями через `&&` → разбить на отдельные
- [ ] Тест без ассерта (проходит вхолостую) или только `assertNotNull` → добавить осмысленную проверку содержимого

## Check 7 — Независимость и scope теста

- [ ] Имя теста не описывает проверяемое → `<action><Entity><Condition>` (Kotlin) / `test_<action>_<entity>_<condition>` (Go)
- [ ] Один файл тестирует несвязанные фичи → разбить по фиче
- [ ] `@Tag("smoke")` на тесте дольше 30s или с тяжёлым setup → убрать smoke

## Check 8 — Кросс-платформенный паритет (mobile, iOS ↔ Android)

- [ ] Один сценарий на Android (Kaspresso) и iOS (XCUITest / `runComposeUiTest`) проверяет **одно и то же** (та же логика ассертов, те же экраны). Расхождения — только где вынуждает платформа: нативная клавиатура, secure-field, системные диалоги, реальный OTP
- [ ] **Allure-наименования едины**: один сценарий = один `epic` / `feature` / `story` на обеих платформах (Android — `@Epic/@Feature/@Story`; iOS — через `xcresult_to_allure` по map'ам `SUITE_EPIC_RU` / `STORY_RU`)
- [ ] Fake-фикстуры **не дублируются** между source-set'ами (`commonTest/testdoubles` против `androidInstrumentedTest/fakes`) → общий source-set, иначе версии расходятся
- [ ] Шаги воспроизведения — действия пользователя (GWT: Given/When/Then), не отсылки к коду; повторяющийся E2E-каркас вынесен в общий базовый класс

---

## Output Format

For each violation found:
```
❌ Check N — <Check name>
   Line/Block: <what exactly>
   Risk: <why this is a problem>
   Fix:
   <corrected code>
```

If the test passes all checks:
```
✅ Test looks solid. No violations found.
   Suggestions (optional): <non-blocking improvements if any>
```
