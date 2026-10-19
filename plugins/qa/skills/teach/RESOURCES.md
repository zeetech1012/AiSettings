# Kotlin Mobile Testing (KMP) Resources

## Knowledge

- [Test your multiplatform app — tutorial (kotlinlang.org)](https://kotlinlang.org/docs/multiplatform/multiplatform-run-tests.html)
  Первоисточник по `commonTest`: компилируется во все таргеты, `kotlin.test` (@Test/assertEquals), как гонять. Use for: основа слоя общих тестов, выбор фреймворка.
- [Testing Compose Multiplatform UI (kotlinlang.org)](https://kotlinlang.org/docs/multiplatform/compose-test.html)
  `runComposeUiTest`, `ComposeUiTest` receiver (НЕ JUnit TestRule), те же finders/matchers, что в Jetpack Compose test. Use for: кросс-платформенные UI-тесты shared Compose.
- [The basics of KMP project structure (kotlinlang.org)](https://kotlinlang.org/docs/multiplatform/multiplatform-discover-project.html)
  Source sets / targets / иерархия common→intermediate→platform. Use for: ментальная модель «где живёт код и тесты».
- [Android source set layout (kotlinlang.org)](https://kotlinlang.org/docs/multiplatform/multiplatform-android-layout.html)
  `androidUnitTest` (host JVM) vs `androidInstrumentedTest` (устройство/эмулятор). Use for: разница host-unit и instrumented.
- [Compose Multiplatform 1.11.0 — JetBrains blog (May 2026)](https://blog.jetbrains.com/kotlin/2026/05/compose-multiplatform-1-11-0/)
  v2 `ComposeUiTest` API на non-Android, `StandardTestDispatcher` по умолчанию (вместо Unconfined), deprecation `runComposeUiTest`/`runSkikoComposeUiTest`. Use for: актуальные изменения API (важно для собеседований/широты).

- [Compose support in Kaspresso (kasperskylab.github.io)](https://kasperskylab.github.io/Kaspresso/Wiki/Jetpack_Compose/)
  Kaspresso = Espresso + UI Automator framework; Compose-support = Kakao-Compose + interceptors, единый DSL для View и Compose. Use for: что такое Kaspresso, чем драйвит Compose, `kaspresso-compose-support`.
- [Kaspresso — GitHub (KasperskyLab)](https://github.com/KasperskyLab/Kaspresso)
  Источник по `flakySafely` (retry-with-timeout, дефолт 10с), robots, interceptors, ускоренный UI Automator. Use for: стабильность, DSL, system-UI.
- [Synchronize your tests — Jetpack Compose (developer.android.com)](https://developer.android.com/develop/ui/compose/testing/synchronization)
  Авто-синхронизация Compose-теста с UI-деревом, `waitForIdle`/`autoAdvance`, idling resources. Use for: почему тест ждёт idle и что делать с never-idle UI.
- [Alternatives to Idling Resources: waitUntil APIs (Android blog)](https://developer.android.com/blog/posts/alternatives-to-idling-resources-in-compose-tests-the-wait-until-ap-is-updated)
  `waitUntil { … }` вместо idling resources. Use for: синхронизация на живых WS/анимациях.

## Wisdom (Communities)

- [Kotlinlang Slack — #multiplatform и #compose](https://slack-chats.kotlinlang.org/)
  Высокосигнальные каналы с участием команды JetBrains. Use for: краевые вопросы по `runComposeUiTest`, синхронизации, source-set конфигурации.
- [r/Kotlin](https://reddit.com/r/Kotlin)
  Use for: обсуждение тест-стратегий, code-review подходов, сравнение инструментов.

## Gaps
- Нет пока курируемого источника по **Kaspresso** (Compose support) и по **iOS XCUITest против Compose-рендеринга через accessibility-мост** — найти official Kaspresso docs + Apple XCUITest docs к соответствующему уроку.
- Нет источника по **Appium для Compose MP** (обсуждали — почему не подходит); найти, если дойдём до сравнения инструментов.
