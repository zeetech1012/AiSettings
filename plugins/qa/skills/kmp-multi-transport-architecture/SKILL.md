---
name: kmp-multi-transport-architecture
description: Архитектурный skill для проектирования Clean Architecture + MVVM в Kotlin Multiplatform проектах с динамически переключаемыми стратегиями подключения (BLE, MQTT, Cloud HTTP API).
version: 1.0.0
---

# KMP Multi-Transport Architecture

This skill provides design patterns, rules, and best practices for implementing Clean Architecture + MVVM in Kotlin Multiplatform (KMP) mobile projects that support dynamic data sources (such as BLE, MQTT, and Cloud API) for IoT or smart energy applications.

## 1. Modular & Package Layout (KMP)
Maintain a **flat package structure** directly under `composeApp/src/commonMain/kotlin/` rather than deeply nested package trees (e.g. avoid starting everything with standard Java-like package domains like `com/company/project/`). This maximizes readability and simplifies imports in shared modules.

### Recommended Layout:
- `data/` — Repository implementations, network API clients, database models, DTOs, and mapping layers.
- `domain/` — Use cases, domain models, business validation rules, managers, and connection controllers.
- `ui/` — Compose screens, ViewModels, navigation setups, and UI-specific state definitions.

## 2. Dynamic Strategy Pattern for Multi-Transport Data
When an application must interact with physical hardware devices (like EV chargers or smart meters) over various communication channels depending on environment constraints, use the **Strategy Pattern** managed via a unified router.

### Code Pattern Example (Strategy Router)
```kotlin
// 1. Declare the Transport Enum
enum class DataSourceType {
    BLE, MQTT, API
}

// 2. Interface defining common interactions
interface DeviceSettingsRepository {
    suspend fun getSettings(deviceId: String): Result<DeviceSettings>
    suspend fun updateSettings(deviceId: String, settings: DeviceSettings): Result<Unit>
}

// 3. Main implementation routing requests to specialized transport repositories
class DeviceSettingsRepositoryImpl(
    private val bleRepository: DeviceSettingsBleRepositoryImpl,
    private val mqttRepository: DeviceSettingsMqttRepositoryImpl,
    private val apiRepository: DeviceSettingsApiRepositoryImpl,
    private val dataSourceManager: DataSourceManager
) : DeviceSettingsRepository {

    override suspend fun getSettings(deviceId: String): Result<DeviceSettings> {
        return when (dataSourceManager.getActiveSource(deviceId)) {
            DataSourceType.BLE -> bleRepository.getSettings(deviceId)
            DataSourceType.MQTT -> mqttRepository.getSettings(deviceId)
            DataSourceType.API -> apiRepository.getSettings(deviceId)
        }
    }
    
    override suspend fun updateSettings(deviceId: String, settings: DeviceSettings): Result<Unit> {
        return when (dataSourceManager.getActiveSource(deviceId)) {
            DataSourceType.BLE -> bleRepository.updateSettings(deviceId, settings)
            DataSourceType.MQTT -> mqttRepository.updateSettings(deviceId, settings)
            DataSourceType.API -> apiRepository.updateSettings(deviceId, settings)
        }
    }
}
```

## 3. Dependency Injection Rules (Koin)
Organize Koin DI declarations into highly-focused modules defined in a shared app module (`AppModule.kt`):

```kotlin
val coreModule = module {
    single<HttpClient> { createKtorHttpClient() }
    single<SqlDriver> { createDatabaseDriver() }
}

val authModule = module {
    singleOf(::AuthRepositoryImpl) { bind<AuthRepository>() }
    viewModelOf(::LoginByPhoneViewModel)
}

val deviceModule = module {
    singleOf(::DeviceSettingsRepositoryImpl) { bind<DeviceSettingsRepository>() }
}
```

By decoupling interface declarations in `domain/` and implementations in `data/`, you easily support fake mock repositories for instrumented tests (e.g. `fakeAuthModule()` overridden via `KoinOverrideRule`).
```

