---
name: new-page-object
description: >
  Создание, добавление или генерация Compose Screen Page Object или Robot-класса для Kotlin Multiplatform (только Compose).
  Triggers on: "create page object", "add page class", "new page object for",
  "create screen class", "add POM for", "page object for this screen".
---

# Creating Compose Screen Page Objects & Robots (Kotlin/KMP)

This skill describes how to design page objects (Screens) and action classes (Robots) for Compose Multiplatform mobile UI-automation tests. Python/Pytest is deprecated and NOT used.

---

## Architecture Flow
We use the **Screen + Robot + Test** architecture pattern:
1. **Screen**: Contains locators (`testTag`) using Kakao Compose (`ComposeScreen` and `KNode`).
2. **Robot**: Contains actions (DSL) such as typing text, tapping buttons, and performing assertions.
3. **Test**: Calls the Robot to build the Arrange/Act/Assert test flow.

---

## 1. Screen (Locators) Template

### Rules
- Inherit from `ComposeScreen<TScreen>(semanticsProvider, viewBuilderAction)`.
- Strictly use **only `testTag`** via `hasTestTag("...")`. Do NOT match by text or resource ID.
- Do not add action methods to the Screen class.

```kotlin
package com.example.energy.screens

import androidx.compose.ui.test.SemanticsNodeInteractionsProvider
import io.github.kakaocup.compose.node.element.KNode
import io.github.kakaocup.compose.screen.ComposeScreen

class MainScreen(semanticsProvider: SemanticsNodeInteractionsProvider) :
    ComposeScreen<MainScreen>(
        semanticsProvider = semanticsProvider,
        viewBuilderAction = { hasTestTag("MainScreenView") }
    ) {

    val titleText = KNode(semanticsProvider) { hasTestTag("MainScreenTitleText") }
    val logoutButton = KNode(semanticsProvider) { hasTestTag("LogoutActionButton") }
    val energyMeterItem = KNode(semanticsProvider) { hasTestTag("EnergyMeterItemPrefix_SN-100") }
}
```

---

## 2. Robot (Actions DSL) Template

### Rules
- Accept `SemanticsNodeInteractionsProvider` in the constructor.
- Initialize the corresponding Screen.
- Implement clear action methods (e.g. `clickLogout()`, `verifyTitleVisible()`).
- Use Kaspresso's `flakySafely` for potential flaky actions.

```kotlin
package com.example.energy.robots

import androidx.compose.ui.test.SemanticsNodeInteractionsProvider
import com.example.energy.screens.MainScreen
import io.github.kakaocup.compose.node.element.KNode

class MainRobot(semanticsProvider: SemanticsNodeInteractionsProvider) {
    private val screen = MainScreen(semanticsProvider)

    fun clickLogout() {
        screen.logoutButton.performClick()
    }

    fun verifyTitle(expectedText: String) {
        screen.titleText.assertTextEquals(expectedText)
    }

    fun selectMeter() {
        screen.energyMeterItem.performClick()
    }
}
```

---

## Checklist Before Finishing
- [ ] Strictly used `testTag` locators only.
- [ ] No `Thread.sleep()` or unsafe calls (`!!`).
- [ ] Screen class represents a single screen and inherits from `ComposeScreen`.
- [ ] Robot class exposes actions and assertions, separating logic from elements.
