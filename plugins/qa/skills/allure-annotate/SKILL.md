---
name: allure-annotate
description: >
  Используй этот навык, когда нужно добавить, исправить или улучшить Allure-аннотации в тестовых файлах Kotlin (Kaspresso) или Go.
  Triggers on: "add allure", "fix allure annotations", "add reporting", "add allure title",
  "annotate this test", "add steps to test", "allure is missing", "add severity".
---

# Working with Allure Annotations (Kotlin & Go)

This skill provides rules and templates for annotating Kotlin (Kaspresso) and Go tests for Allure report generation. Python/Pytest is deprecated and NOT used.

---

## 1. Kotlin / Kaspresso Annotations

### Required Annotations
Every Kaspresso test class or method should have Allure annotations to categorize and describe the test.

```kotlin
@Epic("Authentication")            // Grouping: Major epic
@Feature("OTP Login")              // Grouping: Specific feature
@Story("SMS OTP Verification")      // Grouping: Detailed user story
class OtpLoginTest {

    @Test
    @Severity(SeverityLevel.BLOCKER) // CRITICAL, BLOCKER, NORMAL, MINOR
    @Tag("smoke")                    // Tag for filtering
    fun testOtp_Success() {
        ...
    }
}
```

### Steps inside Kaspresso
Use Kaspresso's native `step` block or `Allure.step` for wrapping test phases (Arrange, Act, Assert).

```kotlin
step("Given: Prepare valid OTP payload") {
    // Arrange
}

step("When: Submit OTP code") {
    // Act
}

step("Then: Assert login success") {
    // Assert
}
```

---

## 2. Go API Test Annotations

Go tests are integrated into Allure via `gotestsum` with JUnit XML generation. Use standard Go comments and structured subtests to represent steps.

```go
func TestAuth_Success(t *testing.T) {
	t.Run("Given: Prepare valid credentials", func(t *testing.T) {
		// Arrange
	})

	t.Run("When: Send POST /auth request", func(t *testing.T) {
		// Act
	})

	t.Run("Then: Response status is 200 OK and token is issued", func(t *testing.T) {
		// Assert
	})
}
```

---

## Annotation Checklist
- [ ] Kotlin: `@Epic`, `@Feature`, `@Story` present on the test class.
- [ ] Kotlin: `@Severity` and `@Tag` present on the test method.
- [ ] Kotlin: Body steps wrapped in `step("...") { ... }`.
- [ ] Go: Test body structured with descriptive subtests `t.Run("...")`.
