---
name: kaspresso-log-investigator
description: >
  Очистка логов Kaspresso от системного шума Android и поиск причин падения тестов.
  Triggers on: "kaspresso-log-investigator", "очисти логи kaspresso", "debug kaspresso log",
  "kaspresso log debug", "analyze kaspresso log".
---

# SKILL: KASPRESSO_LOG_INVESTIGATOR (Отладка логов)

## Цель
Анализ логов Android-устройства (logcat) при выполнении UI-автоматизации Kaspresso, фильтрация системного шума и локализация шага, на котором упал тест.

## Алгоритм действий

1. **Получение лог-файла**:
   - Примите путь к файлу лога в качестве аргумента или прочитайте последний лог из директории результатов.
   
2. **Очистка от шума (Фильтрация)**:
   - Исключите системный мусор Android: строки от `dalvikvm`, `ActivityManager`, `PackageManager`, `ViewRootImpl`, `OpenGLRenderer`, `Choreographer` и другие фоновые службы.
   - Оставьте только строки, соответствующие паттернам:
     - `Kaspresso: ...` — шаги тестов, хуки, инициализация Kaspresso DSL.
     - `ViewHierarchy: ...` — распечатка иерархии элементов Compose при падении.
     - `Exception` или `Caused by: ...` — трассировка стека ошибок.
     - `I/Allure: ...` или `AllureRunListener` — отчетность Allure.

3. **Локализация ошибки**:
   - Найдите последний успешный шаг теста (например, `step("When: ...") { ... }`).
   - Найдите первое возникновение `Exception` (например, `ComposeInteractionException`, `AssertionError`, `NullPointerException`).
   - Сопоставьте упавший `testTag` из иерархии `ViewHierarchy` с Page Object.

4. **Краткий итоговый вывод**:
   - Сформируйте лаконичное резюме для пользователя в следующем формате:
     - **Тест упал в блоке**: `[Имя шага/блока]` (например, `step("Submit form")`).
     - **Причина падения**: `[Сообщение об ошибке и упавший элемент]` (например, `testTag = 'LoginButton' не найден на экране в течение 10000 мс`).
     - **Стек-трейс (сокращенный)**: `[Первые 3-5 строк стека ошибки]`.
     - **Рекомендация по исправлению**: `[Например, добавить flakySafely в Robot или проверить testTag в Compose коде]`.
