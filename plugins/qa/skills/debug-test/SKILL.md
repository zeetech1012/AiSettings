---
name: debug-test
description: >
  Используй этот навык, когда тест падает, нестабилен (flaky) или выдаёт неожиданный результат в Kotlin (Kaspresso/Compose) или Go и нужна помощь
  в поиске первопричины.
  Triggers on: "test is failing", "this test fails", "why does this test fail",
  "test is flaky", "debug this test", "test passes locally but fails in CI",
  "intermittent failure", "what's wrong with this test run".
---

# Debugging a Failing Test (Go & Kotlin/Kaspresso)

Work through the layers below to find the root cause of a failing test in Go or Kotlin. Python/Pytest is deprecated and NOT used.

---

## Layer 1 — Read the Error & Stack Trace

Identify:
1. **Error type**: AssertionError, ComposeInteractionException, NullPointerException, TimeoutException, ConnectionError, status mismatches (e.g. expected 200, got 401).
2. **Where it fails**: Go test line, Kotlin step name, or UI Robot interaction.
3. **What was expected vs actual**: Exact strings, HTTP statuses, or DB records.

---

## Layer 2 — Environment & Configuration Check

- **Go Database Driver**: Check the driver configuration in `config/auth_http.ini`. Is it set to `mysql` (QA/production) or `sqlite3` (local development)?
- **Base URLs and Gateways**: Are all target URLs (Unisender, SSO endpoints) mapped to local test servers or mock endpoints?
- **Android Emulator / Device**: Is the target Android emulator active and responsive? Is `adb devices` showing the device?

---

## Layer 3 — Go API Test Debugging

Common causes:
- **Rate limiting / Ban**: The test hit the ban threshold (`TIME_CTRL`, `TIMES`, `TIME_BAN` from `auth_http.ini`). Check the `users.bannedToTS` field in the database. Fix: clear the ban or use a different test user.
- **Token expiration**: The access token or refresh token has expired or is invalid. Validate signature keys.
- **Race conditions**: Tests accessing the same DB user in parallel. Fix: parameterize tests to use distinct test users.

---

## Layer 4 — Kotlin / Kaspresso UI Test Debugging

Common causes:
- **Element not found (Compose)**: `testTag` missing or changed in the Compose code. Check `Modifier.testTag()` in the actual Compose screen.
- **Keyboard overlap**: The Android software keyboard is covering the submit button. Use `closeSoftKeyboard()` or similar robot actions.
- **Slow UI animations**: Compose transitions causing element search timeout. Use Kaspresso's `flakySafely` block to wrap actions.
- **Unsafe calls (`!!`)**: NullPointerException due to unsafe casting or access. Avoid `!!` at all costs.

---

## Layer 5 — Isolation & Suite Run

Run the failing test in isolation:
- **Go**: `go test -v -run TestName ./package/...`
- **Kotlin**: Run a single instrumental test target using Android Studio or `./gradlew` command with filters.

- If it **passes alone but fails in suite** → test order dependency, shared DB state.
- If it **always fails** → genuine bug in the system under test or the test code itself.

---

## Layer 6 — Медиа падения (скрин/видео)

Часто причина видна на кадре падения — смотреть его первым (бритва Оккама: проверять простейшее объяснение, бьющееся с фактами).
- **iOS:** `xcrun xcresulttool export attachments --path <bundle.xcresult> --output-path <dir>` → скрин момента падения (`.png`) + запись экрана (`.mp4`); сопоставление с тестом — по `manifest.json`.
- **Android:** Allure screenshot-on-fail (`BaseTestCase`) + видео (`ScreenRecordRule`). На Android 11+ Allure может не персистить результаты — читать JUnit XML напрямую, кадр доставать через `adb` / `run-as` из cacheDir.
- Если падение — реальный прод-баг: эти скрин+видео приложить к баг-тикету (`add_issue_attachment`), а repro собрать из GWT-шагов теста.

---

## Output Format

```
🔍 Root Cause: <one sentence explanation of the failure>

Layer where found: <1–5>

Evidence:
<specific log snippet, error message, or code line>

Fix:
<corrected Kotlin or Go code / config>

Prevention:
<actions to prevent future occurrences, e.g. adding flakySafely, DB cleanup, or distinct test users>
```
