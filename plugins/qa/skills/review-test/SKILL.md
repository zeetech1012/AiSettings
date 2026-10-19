---
name: review-test
description: >
  Используй этот навык, когда просят проревьюить, проверить, проаудитить или улучшить тестовый файл или тестовый код.
  Triggers on: "review my test", "check this test", "is this test ok", "audit test file",
  "what's wrong with this test", "improve this test". НЕ запускай для общего code review
  вне тестовых файлов.
---

# Test Code Review

Run every check below in order. For each violation: state the line/block, explain the risk,
provide the fix inline. Do not summarize at the end — fix as you go.

---

## Check 1 — Flakiness Risks (BLOCKER)

- [ ] `time.sleep()` anywhere → **FLAKY**. Replace with polling loop or Playwright `expect()` with timeout
- [ ] Hardcoded waits disguised as `timeout=5000` with no retry → flag it
- [ ] Test depends on execution order (uses data created by a previous test) → **FLAKY**
- [ ] Shared mutable state between tests (module-level variables mutated in tests) → **FLAKY**
- [ ] Playwright: raw `assert locator.text_content() == "x"` → replace with `expect(locator).to_have_text("x")`

## Check 2 — Hardcoded Values (BLOCKER)

- [ ] URL string literal (`"https://..."`, `"http://..."`) → use `base_url` fixture or `os.environ`
- [ ] Credentials in test body (`"admin"`, `"password123"`) → use fixture or ENV var
- [ ] Hardcoded IDs of real DB records → use factory fixture that creates and cleans up

## Check 3 — Allure Annotations (REQUIRED)

- [ ] Missing `@allure.title(...)` → add descriptive title: "Action Entity — expected result"
- [ ] Missing `@allure.severity(...)` → add: BLOCKER / CRITICAL / NORMAL / MINOR
- [ ] No `allure.step()` inside test body → wrap Arrange / Act / Assert blocks
- [ ] No `allure.attach()` for API response or screenshot → add after Act step

**If any Allure violation is found:** load the `allure-annotate` skill for correct
patterns, severity selection guide, and full annotated examples before applying fixes.

## Check 4 — Pytest Markers (REQUIRED)

- [ ] Missing marker entirely → add at least one: `smoke`, `api`, `ui`, `mobile`, `kafka`
- [ ] Wrong marker for test type (e.g. `@pytest.mark.api` on a Playwright test) → fix

## Check 5 — Fixture Scope

- [ ] Session-scoped fixture creating test-specific data → change to `function` scope
- [ ] Function-scoped fixture doing expensive setup (auth, DB connection) → change to `session`
- [ ] Missing teardown in fixtures that create resources → add `yield` + cleanup

## Check 6 — Locator Quality (UI / Mobile only)

- [ ] Playwright: XPath locator → replace with `get_by_test_id()` or `get_by_role()`
- [ ] Playwright: CSS class selector (`.btn-primary`) → request `data-testid` from devs
- [ ] Appium Android: XPath → replace with `resource-id` or `accessibility id`
- [ ] Appium iOS: XPath → replace with `accessibility id` or predicate string
- [ ] Locator defined inline in test function → move to Page Object class

## Check 7 — Assertion Quality

- [ ] `assert response.json()["field"] == value` → validate with Pydantic model instead
- [ ] Single `assert` with multiple conditions joined by `and` → split into separate asserts
- [ ] No assertion at all (test passes vacuously) → add meaningful assert
- [ ] `assert True` or `assert result is not None` only → add content validation

## Check 8 — Test Independence & Scope

- [ ] Test name doesn't describe what is being verified → rename to `test_<action>_<entity>_<condition>`
- [ ] One test file testing unrelated features → split by feature area
- [ ] Test marked `smoke` but takes >30s or has DB setup → remove smoke marker

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
