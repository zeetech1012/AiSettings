---
name: compose-testtag-injector
description: >
  Инъекция `Modifier.testTag("...")` в ПРОДАКШЕН Compose-код (energy-app-native) в местах
  вызова по naming-конвенции (input_/btn_/screen_/switch_/list_/item_<entity>_<id>), без правки
  shared-компонентов. Делает экраны локируемыми для Kaspresso до написания тестов. Triggers on:
  "add testtag", "повесь testTag", "сделай экран локируемым", "inject testtag",
  "добавь теги на экран", "testtag for this screen", "нет локаторов на экране",
  "screen_ tag on root", "item_device testtag".
---

# SKILL: COMPOSE_TESTTAG_INJECTOR

## Цель
Сделать Compose-экран **локируемым** для Kaspresso: повесить `Modifier.testTag("...")` на
интерактивные элементы и корень экрана **в продакшен-коде** (`composeApp/src/commonMain`),
строго по naming-конвенции репо. Это вход в цепочку покрытия экрана — БЕЗ тегов
`new-page-object` и `write-test` не на что опереться (`hasTestTag(...)` не найдёт элемент).

Применять, когда:
- на целевом экране нет/мало `testTag`, а нужен UI-тест;
- `qa-architect` выявил экран без локаторов;
- e2e падает на `screen_*`-ассерте, потому что на корне экрана нет тега.

НЕ применять для: написания самих тестов (→ `write-test`/`kaspresso-compose-qa-guru`),
создания Screen-объектов (→ `new-page-object`), отладки падений (→
`kaspresso-single-test-diagnostician`).

---

## Naming-конвенция (обязательна, из `CLAUDE.md` + `docs/mobile_test_guidelines.md`)

| Префикс | Для чего | Пример (реальный в репо) |
|---|---|---|
| `screen_` | корень экрана (контейнер-ассерт навигации) | `screen_user_info`, `screen_notifications` |
| `btn_` | кнопка / кликабельный action | `btn_logout`, `btn_open_add_device` |
| `input_` | текстовое поле ввода | `input_email`, `input_device_id` |
| `switch_` | тоггл/свитч | `switch_notifications_permission`, `switch_notif_${item.type}` |
| `item_` | элемент списка/меню (`item_<entity>_<id>`) | `item_settings_user_info`, `item_device_${id}` |
| `list_` | контейнер списка | `list_devices` |
| `text_` | значимый текст/ошибка для ассерта | `text_error` |

**Динамические теги** — интерполяция по стабильному идентификатору сущности:
`item_device_${device.id}`, `switch_notif_${item.type}`. НИКОГДА не по индексу/позиции.

---

## Алгоритм

### 1. Найти точки инъекции
- Корень экрана (внешний `Column`/`Box`/`Scaffold` content) → `screen_<name>`.
- Каждый интерактивный composable (`EComplexButton`, `ESwitch`, `OutlinedTextField`, clickable
  `Row`/`Card`) → соответствующий префикс.

### 2. Вешать тег в МЕСТЕ ВЫЗОВА, не в компоненте
Shared-компоненты (`EComplexButton`, `ESwitch`, …) **уже принимают `modifier`** — передавай
`Modifier.testTag(...)` в вызов. **НЕ редактируй сам компонент** (сломаешь все остальные вызовы).

```kotlin
// ✅ правильно — в месте вызова на экране:
ESwitch(
    checked = state.permission,
    onCheckedChange = { vm.setPermission(it) },
    modifier = Modifier.testTag("switch_notifications_permission"),
)

// корень экрана:
Column(modifier = Modifier.testTag("screen_notifications")) { ... }
```
Если у composable уже есть `modifier` от вызова — цепляй: `modifier.testTag("...")`
(сохрани существующие модификаторы, не затирай).

### 3. import
`import androidx.compose.ui.platform.testTag` — добавить, если отсутствует.

### 4. Валидация (executor обязан прогнать)
```bash
./gradlew :composeApp:compileCommonMainKotlinMetadata    # прод-код компилируется
./gradlew :composeApp:compileDebugAndroidTestKotlin       # тесты против тегов компилируются
```

---

## ⚠️ Подводные камни (из реальной отладки)

- **`text_error` / supportingText OutlinedTextField** живёт в merged semantics tree → Screen-объект
  должен искать его с `useUnmergedTree=true`, иначе «found but not displayed». Сам тег вешается
  как обычно, но предупреди автора Screen-объекта.
- **`screen_*` на корень — обязателен для e2e-навигации.** Если экран грузится по навигации
  (RootRoutes), без тега на корне ассерт «экран открылся» невозможен. Проверь, что тег на
  внешнем контейнере, а не на вложенном элементе (иначе он `isPlaced=false` при пустом контенте).
- **Не плодить теги на не-интерактиве.** Тег только там, где тест будет взаимодействовать или
  ассертить. Лишние теги = шум в semantics tree.

## ⛔ Запрещено
- Менять сигнатуру/тело shared-компонента ради тега (→ только место вызова).
- Тег по индексу/позиции элемента (`item_0`) → только по стабильному id сущности.
- `R.id` / `contentDescription`-хаки вместо `testTag` (в Compose приоритет `hasTestTag`).

---

## Формат итогового вывода
- **Экран**: путь к `*.kt` в `commonMain`.
- **Добавленные теги**: таблица `тег → элемент → строка`.
- **Предупреждения**: где нужен `useUnmergedTree` в будущем Screen-объекте.
- **Валидация**: результат `compileDebugAndroidTestKotlin` (compiled ✅).
- **Next**: `new-page-object` для этого экрана → `write-test`.
