---
name: allure-to-obsidian
description: >
  Трансформация сырых отчетов Allure в базу знаний Obsidian.
  Парсит файлы *-result.json и генерирует отчет для Obsidian.
  Triggers on: "allure to obsidian", "allure-to-obsidian", "отчет в obsidian",
  "сгенерируй отчет за", "allure report to vault".
---

# SKILL: ALLURE_TO_OBSIDIAN (Reporting)

## Цель
Парсинг сырых Allure результатов (`*-result.json`) из каталога результатов, классификация ошибок и экспорт сводного отчета в базу знаний Obsidian через MCP-сервер `obsidian` или официальный Obsidian CLI.

## Алгоритм действий

1. **Поиск Allure результатов**:
   - Перейдите в папку с результатами Allure (по умолчанию `./allure-results` или `{{ALLURE_RESULTS_PATH}}`).
   - Используйте встроенные средства чтения файлов для поиска файлов с маской `*-result.json`.

2. **Парсинг результатов**:
   - Прочитайте и распарсите каждый JSON-файл.
   - Отфильтруйте тесты со статусом `failed` или `broken` (имя теста, полный путь, сообщение об ошибке `statusDetails.message`).
   - Выявите flaky тесты (проверьте историю перезапусков, если доступно, или пометки).

3. **Группировка по типам (Root Cause)**:
   - **Network**: Ошибки тайм-аутов, `ConnectException`, `SocketTimeoutException`, `502/503/504 Bad Gateway`.
   - **UI**: Ошибки отсутствия элементов, `TimeoutException` при поиске `testTag` (Compose) или селекторов, несоответствия размеров/позиций.
   - **Logic**: Ассерты, несовпадение ожидаемых и фактических значений (`assertEquals`, `shouldBe`, `assert`).

4. **Генерация и запись отчета (вывод — только в Obsidian-vault)**:
   - **СТРОГО:** не писать `.md` в рабочий каталог (правило `~/.claude/CLAUDE.md`). Отчёт
     отправляется **только в vault** — через MCP-сервер `obsidian` (`vault_write` — создать/
     перезаписать, `vault_append` — дописать) **или** официальный Obsidian CLI
     (`obsidian create path="..." content="..."` / `obsidian append`; требует запущенного
     приложения, переводы строк в `content` — как `\n`; для многострочного отчёта
     предпочтительнее `vault_write`). Путь: `Company/Projects/<название_проекта>/QA/Report_{{DATE}}.md`.
     Если проект/папка не очевидны — уточните у пользователя.
   - (Опц.) Для парсинга HTML-отчёта Allure можно использовать MCP-сервер `allure`
     (`get_allure_report(report_dir)`); сырые `*-result.json` парсятся напрямую через `Bash`.
   - **Шаблон записи**:
     ```markdown
     # Отчет за {{DATE}}

     ## Общая статистика
     - Всего запущено: {{TOTAL_TESTS}}
     - Успешно: {{PASSED_TESTS}}
     - Упало: {{FAILED_TESTS}}

     ## Flaky тесты
     - `testAuthSessionRotation` (Go) — падает при параллельных запросах ротации RT.
     - `testLoginWithEmptyPassword` (Kotlin) — падает из-за долгой анимации UI.

     ## Root Cause
     ### [Network]
     - Не обнаружено сетевых ошибок в данном прогоне.

     ### [UI]
     - `testTag` `LoginButton` не найден в `LoginActivity` в течение 10 секунд (тайм-аут ожидания Kaspresso).

     ### [Logic]
     - `authHandler` вернул статус 401 вместо 200 на валидный запрос пароля.

     ## Action Items
     1. [UI] Добавить `flakySafely` блок в метод `LoginActivityRobot.clickLogin()`.
     2. [Logic] Проверить кэширование RBAC ролей в `authHandler.go:124`.
     ```
