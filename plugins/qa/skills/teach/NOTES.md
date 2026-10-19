# Teaching Notes — Kotlin Mobile Testing

## Учебный воркспейс
- Файлы воркспейса живут **здесь** (`~/.claude/skills/teach/`), НЕ в репозитории `energy-app-native` — там строгий запрет на `.md`/новые файлы в рабочем каталоге. Уроки — `lessons/NNNN-*.html`, reference — `reference/*.html`.
- Открывать урок: `open ~/.claude/skills/teach/lessons/<file>.html`.

## Кто учится
- Senior QA, Kotlin — основной язык. Сильная практика: `energy-app-native` (KMP+Compose Multiplatform, Kaspresso+Allure-Kotlin, iOS XCUITest, `runComposeUiTest` в iosTest, real-device прогоны). Floor — высокий: НЕ объяснять азы (что такое тест, что такое KMP). См. learning-record 0001.

## Предпочтения
- Объяснения по-русски; код, термины, API — English.
- Уроки короткие, один тезис, быстрый ощутимый результат; ZPD — для продвинутого (углублять/обобщать, не повторять).
- Миссия — **широта/карьера**: обобщать на любой KMP-проект, давать актуальные изменения API (v2 ComposeUiTest и т.п.), цитировать первоисточники. Опыт из `energy-app-native` использовать как якорь-пример, но не замыкаться на нём.
- Прямой стиль, без воды (как просит глобальный CLAUDE.md роли).

## Идеи следующих уроков (бэклог)
- `runComposeUiTest` v2 vs Kaspresso vs XCUITest — какой слой UI для чего (мост testTag→accessibility на iOS).
- Синхронизация/flakiness: idling, `awaitIdle()`/suspend-lambda, почему `pressBack` флейкает на живых WS/Lottie.
- expect/actual в тестах (fakes, fakeXModule), test doubles в commonTest.
- Allure across layers (Epic/Feature/Story, scoped-storage гочи Android, xcresult-конвертер iOS).
- Глоссарий KMP-тестирования (завести после 2-3 уроков, когда термины устаканятся).
