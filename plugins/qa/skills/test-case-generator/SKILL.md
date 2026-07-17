---
name: test-case-generator
description: >
  Генерация тест-кейсов на основе изменений кода (git diff).
  Выявляет изменения в Go эндпоинтах и UI-компонентах Kotlin/KMP и пишет тесты на Gherkin/Kaspresso DSL.
  Triggers on: "test-case-generator", "генератор тест-кейсов", "сгенерируй тесты по диффу",
  "git diff test cases", "test ideas from diff".
---

# SKILL: TEST_CASE_GENERATOR (Генератор)

## Цель
Автоматическое создание тест-кейсов и заготовок автотестов на основе изменений в исходном коде проекта (Kotlin/KMP и Go) с использованием Git.

## Алгоритм действий

1. **Анализ изменений (Git Diff)**:
   - Выполните команду `git diff` (например, `git diff HEAD~1` или сравнение с основной веткой `git diff origin/main`) для получения списка измененных строк.
   - Отберите измененные файлы Go (`*.go`) и Kotlin (`*.kt`).

2. **Идентификация затронутых компонентов**:
   - В **Go**: ищите измененные роуты, HTTP-обработчики (например, `httpHandler/authHandler.go`), SQL-запросы в `dbHelper`, изменения структуры JWT или Rate Limit.
   - В **Kotlin/KMP**: ищите новые Compose-экраны, изменения `Modifier.testTag(...)`, новые события в ViewModel или изменения BLE/MQTT транспортов.

3. **Проектирование тест-кейсов**:
   - Для **Go API**: Сформулируйте интеграционный тест-кейс на Go с проверкой статус-кода, схемы JSON и изменений в БД.
   - Для **Kotlin/KMP**: Сформулируйте UI-тест на Kaspresso DSL с использованием Page Object.
   - Также составьте сценарий в формате **Gherkin (Given-When-Then)** для наглядности.

4. **Сохранение результатов (вывод — только в Obsidian-vault)**:
   - **СТРОГО:** не создавать `.md` в рабочем каталоге проекта (правило `~/.claude/CLAUDE.md`).
     Черновики тест-кейсов пишутся **только** через MCP-сервер `obsidian`
     (`vault_write`/`vault_append`) по пути `Company/Projects/<название_проекта>/QA/test_ideas.md`.
     Если папка/проект не очевидны — уточните у пользователя.
   - Разделите документ на секции:
     - ### Затронутые модули и логика
     - ### Сценарии тестирования (Gherkin)
     - ### Шаблон автотеста (Go / Kaspresso DSL)

## Пример шаблона для вывода (Go / Kaspresso)

### Шаблон Go API теста:
```go
func TestAuth_NewFlow(t *testing.T) {
    // Arrange: подготовка payload
    reqBody := `{"new_field": "value"}`
    req, _ := http.NewRequest("POST", "/auth/new-endpoint", bytes.NewBufferString(reqBody))
    
    // Act: выполнение запроса
    w := httptest.NewRecorder()
    handler := http.HandlerFunc(httpHandler.AuthHandler)
    handler.ServeHTTP(w, req)
    
    // Assert: проверка статуса и ответа
    if w.Code != http.StatusOK {
        t.Errorf("Expected 200, got %d", w.Code)
    }
}
```

### Шаблон Kaspresso Compose тестов:
```kotlin
@Test
fun testNewScreenFlow() = run {
    step("Given: Open new screen") {
        MainScreen {
            newScreenButton.click()
        }
    }
    step("When: Input new value and submit") {
        NewScreen {
            inputField.typeText("Value")
            submitButton.click()
        }
    }
    step("Then: Value should be saved successfully") {
        NewScreen {
            successMessage.isDisplayed()
        }
    }
}
```
