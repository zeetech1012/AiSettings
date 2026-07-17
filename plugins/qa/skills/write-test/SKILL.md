---
name: write-test
description: >
  Используй этот навык, когда просят написать, создать, сгенерировать или добавить автоматизированный тест.
  Triggers on: "write a test", "create test", "add test for", "cover this endpoint",
  "test this screen", "test this flow".
  Применяется к Go API/Integration тестам и Kotlin/Kaspresso mobile/UI тестам.
---

# How to Write Automated Tests (Go & Kotlin/Kaspresso)

Сначала определи стек проекта — Go (backend: `qa-monorepo` / `auth_http`) или Kotlin
(mobile: `energy-app-native`). Python/Pytest не используется.

Конвенции и шаблоны стека держим в каноне, а не здесь — этот навык только маршрутизирует
и фиксирует дельты, которых в каноне нет.

---

## Kotlin / Kaspresso (mobile, `energy-app-native`)

**Канон — `Company/Projects/energy-app-native/mobile_test_guidelines.md`** (Obsidian-vault).
Читать целиком перед написанием: Compose-маппинг (`KScreen`→`ComposeScreen`, `withId`→`hasTestTag`),
шаблоны Screen / Robot / Test, locator priority (`testTag` > `contentDescription` > `text`),
flakiness (`flakySafely` вместо `Thread.sleep`), naming, Allure-аннотации, GWT + AAA, anti-patterns.
Не дублировать гайдлайн в этом файле.

Дельты, которых в гайдлайне нет — учитывать при написании:

- **Кросс-платформенный паритет.** Тот же сценарий на iOS (XCUITest / `runComposeUiTest`) проверяет
  ту же логику, что Android (Kaspresso). Allure `epic` / `feature` / `story` совпадают на обеих
  платформах: Android — `@Epic/@Feature/@Story`; iOS — через конвертер `scripts/xcresult_to_allure.rb`
  (map'ы `SUITE_EPIC_RU` / `STORY_RU`). Fake-фикстуры — в общем source-set, не дублировать между
  `commonTest` и `androidInstrumentedTest`. Повторяющийся E2E-каркас — в общий базовый класс.
- **Тест вскрыл баг.** QA прод-код не правит — завести один black-box баг-тикет
  (Environment · Severity · Steps to reproduce · Actual/Expected · Attachments). Шаги воспроизведения —
  из GWT-шагов теста как действия пользователя. Скрин/видео — из прогона (Allure / xcresult),
  приложить через `add_issue_attachment`. Repro оставлять красным до фикса.

---

## Go (backend, `qa-monorepo` / `auth_http`)

**Канон — `CLAUDE.md` соответствующего репозитория** (`qa-monorepo`: `resty` + `testify` + `allure-go`;
`auth_http`: `httptest` + `testing` + `tokens`). Ключевое:

- **No sleeps:** никогда `time.Sleep()`; для async (rate limit, ban liftoff) — polling-цикл с таймаутом.
- **Trace to DB:** проверять до уровня БД (`dbHelper`, SQLite / MySQL).
- **Token Management:** JWT / RT через пакет `tokens`.
- **GWT + AAA:** `t.Run("Given/When/Then ...", ...)`, AAA-логика внутри, `allure.step` на блоки.

### Template Go API Test
```go
package httpHandler_test

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"testing"

	"auth_http/httpHandler"
	"auth_http/tokens"
)

func TestAuthHandler_PasswordSuccess(t *testing.T) {
	// Arrange
	payload := []byte(`{"mode":"password","username":"test_user","password":"test_password"}`)
	req, err := http.NewRequest("POST", "/auth", bytes.NewBuffer(payload))
	if err != nil {
		t.Fatalf("Failed to create request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()

	// Act
	handler := http.HandlerFunc(httpHandler.AuthHandler)
	handler.ServeHTTP(rr, req)

	// Assert
	if status := rr.Code; status != http.StatusOK {
		t.Errorf("Handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	respBody := rr.Body.String()
	if !bytes.Contains(rr.Body.Bytes(), []byte("access_token")) {
		t.Errorf("Response body missing access_token: got %s", respBody)
	}
}
```
