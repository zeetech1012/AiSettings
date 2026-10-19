---
name: write-test
description: >
  Используй этот навык, когда просят написать, создать, сгенерировать или добавить автоматизированный тест.
  Triggers on: "write a test", "create test", "add test for", "cover this endpoint",
  "test this screen", "test this flow".
  Применяется к Go API/Integration тестам и Kotlin/Kaspresso mobile/UI тестам.
---

# How to Write Automated Tests (Go & Kotlin/Kaspresso)

Before writing any code, check the project type to choose either Go or Kotlin. Python/Pytest is deprecated and NOT used.

---

## 1. Go API and Integration Tests

### Rules
- **No sleeps**: Never use `time.Sleep()`. Use polling loops (e.g. `tenacity`-like retry logic) for async operations like rate limits or ban liftoff.
- **Trace to DB**: Trace calls down to the database level (`dbHelper` module, SQLite/MySQL).
- **Token Management**: Use `tokens` package for JWT/RT generation and verification.

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

	// Further response validation
	respBody := rr.Body.String()
	if !bytes.Contains(rr.Body.Bytes(), []byte("access_token")) {
		t.Errorf("Response body missing access_token: got %s", respBody)
	}
}
```

---

## 2. Kotlin / Kaspresso Compose Multiplatform UI Tests

### Rules
- **Locators**: strictly **ONLY `testTag`** via `Modifier.testTag()`. Other matching strategies are prohibited.
- **Page Objects**: Use `ComposeScreen` and `KNode`. Do not use `KScreen` (Kakao).
- **Structure**: Separate into `Screens` (locators), `Robots` (DSL actions), and `Tests` (GWT/AAA logic).
- **No sleeps**: Absolutely no `Thread.sleep()`. Use Kaspresso's `flakySafely`.
- **Safety**: No unsafe calls `!!` in Kotlin. Use safe calls `?.` or explicit checks.
- **Reporting**: Mandatory Allure-kotlin annotations (`@Epic`, `@Feature`, `@Story`, `@Severity`, `@Tag`).

### Page Object (Screen) Template
```kotlin
package com.company.energy.screens

import androidx.compose.ui.test.SemanticsNodeInteractionsProvider
import io.github.kakaocup.compose.node.element.KNode
import io.github.kakaocup.compose.screen.ComposeScreen

class LoginScreen(semanticsProvider: SemanticsNodeInteractionsProvider) :
    ComposeScreen<LoginScreen>(
        semanticsProvider = semanticsProvider,
        viewBuilderAction = { hasTestTag("LoginScreen") }
    ) {

    val usernameField = KNode(semanticsProvider) { hasTestTag("UsernameInputField") }
    val passwordField = KNode(semanticsProvider) { hasTestTag("PasswordInputField") }
    val submitButton = KNode(semanticsProvider) { hasTestTag("SubmitLoginButton") }
}
```

### Robot Template
```kotlin
package com.company.energy.robots

import androidx.compose.ui.test.SemanticsNodeInteractionsProvider
import com.company.energy.screens.LoginScreen

class LoginRobot(semanticsProvider: SemanticsNodeInteractionsProvider) {
    private val screen = LoginScreen(semanticsProvider)

    fun enterUsername(username: String) {
        screen.usernameField.performTextInput(username)
    }

    fun enterPassword(password: String) {
        screen.passwordField.performTextInput(password)
    }

    fun clickLogin() {
        screen.submitButton.performClick()
    }
}
```

### Test Template
```kotlin
package com.company.energy.tests

import androidx.compose.ui.test.junit4.createComposeRule
import com.company.energy.robots.LoginRobot
import io.qameta.allure.kotlin.*
import org.junit.Rule
import org.junit.Test

@Epic("Authentication")
@Feature("Login Flow")
@Story("Success Login")
class LoginTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    @Severity(SeverityLevel.BLOCKER)
    @Tag("smoke")
    fun testLogin_Success() {
        val robot = LoginRobot(composeTestRule)

        Allure.step("Enter valid credentials") {
            robot.enterUsername("test_user")
            robot.enterPassword("password123")
        }

        Allure.step("Click login button") {
            robot.clickLogin()
        }

        Allure.step("Assert user navigated to home screen") {
            // Verify elements on main screen
        }
    }
}
```
