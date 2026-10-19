---
name: kmp-fake-koin-module
description: >
  Генерация тестового дубля репозитория (Fake*Repository) + Koin-override-модуля (fakeXModule)
  для KMP/Compose instrumented-тестов energy-app-native, по образцу fakeAuthModule/FakeAuthRepository.
  Подменяет слой данных поверх живого графа без backend; включает safe-teardown паттерн
  KoinOverrideRule (restore вместо unload). Triggers on: "create fake repository", "сделай фейк",
  "fake koin module", "подмени репозиторий в тесте", "fakeMessengerModule", "fake device module",
  "override koin in test", "тестовый дубль репозитория", "mock repository for ui test".
---

# SKILL: KMP_FAKE_KOIN_MODULE

## Цель
Создать пару **`Fake<X>Repository`** + **`fake<X>Module()`** для подмены слоя данных в
instrumented-тестах (`energy-app-native`), чтобы гонять UI happy-path/error-path **без backend**.
Остальной граф (use-case'ы, ViewModel) остаётся реальным и резолвится поверх фейка.

Применять, когда:
- UI-тесту нужен детерминированный ответ репозитория (успех/ошибка) без сети;
- покрываешь экран с данными (Notifications-свитчи, AddDevice, UserInfo) — отложенные таски
  2b-3b из handoff;
- нужен лог вызовов репозитория для верификации.

НЕ применять для: чистой L1-логики на JVM (там фейки кладутся в `commonTest/testdoubles`, без
Koin — Koin поднимает только приложение), написания самих тестов (→ `write-test`).

---

## Где что лежит (две раскладки — не путать)

| Назначение | Путь | Koin? |
|---|---|---|
| **Instrumented** (UI на устройстве) | `androidInstrumentedTest/.../fakes/Fake*.kt` + `di/FakeModules.kt` | да — override живого графа через `KoinOverrideRule` |
| **commonTest** (L1, JVM-хост) | `commonTest/.../testdoubles/Fake*.kt` | нет — фейк передаётся в VM/use-case конструктором |

Этот скил — про **instrumented**-вариант (с Koin). Для L1 просто инстанцируй фейк в тесте.

---

## Алгоритм

### 1. Найти интерфейс репозитория и его прод-биндинг
```bash
grep -rn "interface <X>Repository" composeApp/src/commonMain/kotlin/domain/repository/
grep -n "single<<X>>" composeApp/src/commonMain/kotlin/koin/AppModule.kt   # какой модуль биндит
```
Запомни **точное имя прод-модуля**, который объявляет `single<X>` — оно понадобится в teardown.
Пример реальных биндингов: `messengerModule` → `MessengerApiRepository`,
`authModule` → `AuthRepository`, `otpTimerProvider` → `OTPTimerProvider`.

⚠️ **Qualified-биндинги:** некоторые репозитории биндятся с `named(...)` —
например `DeviceSettingsDataRepository` имеет `named("api")`, `named("ble")`, `named("mqtt")`
+ дефолтный. Фейк должен переопределить **тот же квалификатор**, иначе override не сработает.

### 2. Создать `Fake<X>Repository` (по образцу `fakes/FakeAuthRepository.kt`)
Паттерн:
- реализует `domain.repository.<X>`;
- настраиваемые поля результата: `var defaultResult: Result<Unit> = Result.success(Unit)` и
  типизированные `var <method>Result` для не-Unit методов (по умолчанию — failure
  «not configured in test», чтобы забывчивость падала явно, а не молча);
- `val calls = mutableListOf<String>()` + `private fun record(name) = calls.add(name)` в каждом
  методе — для верификации «метод вызван».
- состояние сбрасывается per-test: `KoinOverrideRule` ставит новый инстанс на каждый тест.

```kotlin
class FakeMessengerApiRepository : MessengerApiRepository {
    var defaultResult: Result<Unit> = Result.success(Unit)
    var quickSetupResult: Result<QuickSetupModel> =
        Result.failure(IllegalStateException("quickSetupResult not configured in test"))
    val calls = mutableListOf<String>()
    private fun record(name: String) = calls.add(name)

    override suspend fun getQuickSetup(): Result<QuickSetupModel> {
        record("getQuickSetup"); return quickSetupResult
    }
    override suspend fun saveQuickSetup(payload: QuickSetupModel): Result<Unit> {
        record("saveQuickSetup"); return defaultResult
    }
    // ... остальные методы интерфейса — record(...) + return defaultResult
}
```

### 3. Создать `fake<X>Module()` (в `di/FakeModules.kt`, по образцу `fakeAuthModule`)
```kotlin
fun fakeMessengerModule(
    repo: FakeMessengerApiRepository = FakeMessengerApiRepository(),
): Module = module {
    single<MessengerApiRepository> { repo }
    // qualified-кейс: single<DeviceSettingsDataRepository>(named("api")) { repo }
}
```

### 4. Подключить в тесте через `KoinOverrideRule`
```kotlin
private val fakeMessenger = FakeMessengerApiRepository()
@get:Rule val koinOverride = KoinOverrideRule(fakeMessengerModule(fakeMessenger))
// доступ к инстансу: get<MessengerApiRepository>() as FakeMessengerApiRepository
```

### 5. ⚠️ Обновить teardown-restore в `KoinOverrideRule.finished()`
`KoinOverrideRule.finished()` грузит обратно прод-модули, чьи определения подменялись.
**Если добавляешь новый фейк-домен — допиши его прод-модуль в restore-список**, иначе
последующие тесты на реальном графе упадут с `NoDefinitionFoundException`.

```kotlin
override fun finished(description: Description) {
    // restore — перечисли ВСЕ прод-модули, чьи биндинги мог подменить любой fakeXModule:
    loadKoinModules(listOf(authModule, otpTimerProvider, messengerModule /* +новый */))
}
```

### 6. Валидация
```bash
./gradlew :composeApp:compileDebugAndroidTestKotlin
```

---

## ⛔ Запрещено / критично (hard-won)

- **НИКОГДА `unloadKoinModules` в teardown.** Инструментальный прогон поднимает Koin ОДИН раз на
  весь процесс — граф общий. `unloadKoinModules` удаляет определение из общего графа НАВСЕГДА →
  все последующие тесты на реальном графе падают `NoDefinitionFoundException` (это и был
  order-dependence баг, фикс `b6d7964`). Только **restore через повторный `loadKoinModules`**.
- **Не подменять квалификатор по умолчанию, если прод биндит `named(...)`** — override не
  попадёт в нужный слот.
- **Дефолт типизированного результата — failure, не success.** Забытая настройка должна падать
  явным «not configured», а не молча возвращать пустой happy-path.
- **Не класть instrumented-фейк в `commonTest`** (и наоборот) — разные раскладки, Koin есть
  только в instrumented.

---

## Формат итогового вывода
- **Интерфейс**: `domain.repository.<X>` + прод-модуль, который его биндит (+ квалификаторы).
- **Созданные файлы**: `fakes/Fake<X>Repository.kt`, изменения в `di/FakeModules.kt`.
- **Teardown**: добавлен ли прод-модуль в `KoinOverrideRule.finished()` restore-список.
- **Валидация**: `compileDebugAndroidTestKotlin` ✅.
- **Next**: `write-test` с `@get:Rule KoinOverrideRule(fake<X>Module(...))`.
