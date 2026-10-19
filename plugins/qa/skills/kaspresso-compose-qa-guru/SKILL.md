---
name: kaspresso-compose-qa-guru
description: Экспертный skill для написания Kaspresso + Compose Multiplatform UI-automation тестов для Android и iOS мобильных приложений без XML layouts или R.id.
version: 1.0.0
---

# Kaspresso Compose QA Guru

Expert guide and reference for writing UI automation tests targeting **Compose Multiplatform** using **Kaspresso** (`kaspresso-compose-support`) and **Allure-Kotlin**.

## 1. Locate Strategy: Strictly testTag
In Compose Multiplatform, there are no XML layouts or `R.id` matching. You MUST use `testTag` as the primary locator strategy.

### Page Object Pattern (`ComposeScreen`)
Always separate locator declaration into screen classes extending `ComposeScreen` (from Kakao-Compose).

```kotlin
import androidx.compose.ui.test.SemanticsNodeInteractionsProvider
import io.github.kakaocup.compose.node.element.ComposeScreen
import io.github.kakaocup.compose.node.element.KNode

class LoginScreen(semanticsProvider: SemanticsNodeInteractionsProvider) :
    ComposeScreen<LoginScreen>(
        semanticsProvider = semanticsProvider,
        viewBuilderAction = { hasTestTag("LoginScreenTag") }
    ) {

    // Locator priority: hasTestTag -> hasContentDescription -> hasText
    val phoneField       = KNode(semanticsProvider) { hasTestTag("input_phone") }
    val sendCodeBtn      = KNode(semanticsProvider) { hasTestTag("btn_verify_continue") }
    val registerBtn      = KNode(semanticsProvider) { hasTestTag("btn_registration") }
}
```

### Naming Conventions for testTags
Every interactive Compose element must be tagged using `Modifier.testTag("...")`:
- Inputs: `input_<name>` (e.g. `input_phone`, `input_email`)
- Buttons: `btn_<action>` (e.g. `btn_verify_continue`, `btn_login`)
- Screens/Views: `screen_<name>` (e.g. `screen_login`, `screen_dashboard`)
- Lists: `list_<name>` (e.g. `list_devices`)
- List Items: `item_<entity>_<id>` (e.g. `item_device_NB-12345`)

## 2. Eliminate Flakiness: No Thread.sleep()
Absolute ban on `Thread.sleep()` in test execution. Always use Kaspresso's `flakySafely` blocks for polling and implicit waiting.

```kotlin
// CORRECT — robust and fast polling
flakySafely(timeoutMs = 15000) {
    onComposeScreen<LoginScreen>(composeTestRule) {
        phoneField.assertIsDisplayed()
        sendCodeBtn.performClick()
    }
}

// WRONG — extremely fragile and slow
Thread.sleep(5000)
phoneField.performClick()
```

## 3. Architecture Pattern: Robots & Scenarios
Keep test files clean and focused on AAA (Arrange-Act-Assert) inside GWT (Given-When-Then) steps. Logic goes to Robots, reusable flows to Scenarios.

### Robot DSL implementation
```kotlin
class LoginRobot(private val rule: ComposeTestRule) {
    fun enterPhone(phone: String) = apply {
        LoginScreen(rule) { phoneField.performTextInput(phone) }
    }
    fun tapSendCode() = apply {
        LoginScreen(rule) { sendCodeBtn.performClick() }
    }
}
```

### Scenario DSL implementation
```kotlin
class LoginScenario(
    private val phone: String = "9991234567"
) : BaseScenario<Unit>() {
    override val steps: TestContext<Unit>.() -> Unit = {
        step("Open login screen and authenticate") {
            LoginRobot(composeRule).enterPhone(phone).tapSendCode()
        }
    }
}
```

## 4. Reporting & Allure
Every test class and method must have mandatory Allure annotations to generate reports properly.

```kotlin
@RunWith(AllureAndroidJUnit4::class)
class LoginSmokeTest : TestCase() {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    @Epic("Auth")
    @Feature("Authorization")
    @Story("Login by phone number")
    @Severity(SeverityLevel.BLOCKER)
    @Description("Verifies login screen displays phone fields and buttons correctly")
    @Tag("smoke")
    fun loginScreenShowsPhoneInputAndButtons() = run {
        step("Given: user launches app and opens login screen") {
            // Setup / Navigation
        }
        step("Then: screen UI elements are correctly displayed") {
            flakySafely {
                onComposeScreen<LoginScreen>(composeTestRule) {
                    phoneField.assertIsDisplayed()
                    sendCodeBtn.assertIsDisplayed()
                }
            }
        }
    }
}
```
