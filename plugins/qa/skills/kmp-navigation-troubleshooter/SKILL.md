---
name: kmp-navigation-troubleshooter
description: Справочный skill для отладки Jetpack Compose Navigation в Kotlin Multiplatform проектах, устранения платформо-специфичных крашей (например, iOS SIGABRT NavType error).
version: 1.0.0
---

# KMP Navigation Troubleshooter

This skill provides comprehensive rules, code patterns, and debugging steps for resolving platform-specific **Jetpack Compose Navigation** issues in **Kotlin Multiplatform (KMP)** projects.

## 1. The iOS Startup SIGABRT Crash (Enum Route Arguments)

### Problem
When executing a Compose Multiplatform app on iOS, passing **enum arguments** or nullable types in routes without custom `NavType` mappings causes an immediate runtime crash:
`SIGABRT` / `IllegalArgumentException: could not find any NavType for argument ...`
This happens because Kotlin/Native and iOS build pipelines do not automatically generate or map enum arguments to standard `NavType` objects in Jetpack Navigation.

### The Fix
To prevent this, you MUST explicitly provide a `typeMap` utilizing `typeOf<T>()` and register a custom `NavType` mapper for every enum or custom type argument used in route classes:

```kotlin
// 1. Define custom NavType mapping for the enum
val ElectricityObisCodesNavType = object : NavType<ElectricityObisCodes>(isNullableAllowed = false) {
    override fun put(bundle: Bundle, key: String, value: ElectricityObisCodes) {
        bundle.putString(key, value.name)
    }
    override fun get(bundle: Bundle, key: String): ElectricityObisCodes? {
        return bundle.getString(key)?.let { ElectricityObisCodes.valueOf(it) }
    }
    override fun parseValue(value: String): ElectricityObisCodes {
        return ElectricityObisCodes.valueOf(value)
    }
}

// 2. Register it in NavHost composable registration
composable<ElectricityNetworkStatisticRoute>(
    typeMap = mapOf(typeOf<ElectricityObisCodes>() to ElectricityObisCodesNavType)
) { backStackEntry ->
    val route: ElectricityNetworkStatisticRoute = backStackEntry.toRoute()
    ElectricityNetworkStatisticScreen(obisCode = route.obisCode)
}
```

For **nullable enums**, allow nullable values in your custom mapper and declare it identically:
```kotlin
composable<ChargerConnectionConfigRoute>(
    typeMap = mapOf(typeOf<ConnectionConfigType?>() to ConnectionConfigTypeNavType)
) { /* ... */ }
```

## 2. Capturing iOS Navigation Logs
To diagnose runtime crashes on the iOS simulator or device when the Gradle pipeline fails to capture native stack traces, execute the following commands in the terminal:

```bash
# Get name of booted simulator
xcrun simctl list devices | grep Booted

# Launch the app package
xcrun simctl launch booted com.legacy.examplehome

# Capture real-time log streams filtering for the app process
xcrun simctl spawn booted log stream --level debug --predicate 'process == "ExampleHome"'
```

## 3. General Navigation Rules
- **Decoupled Actions**: ViewModels should never contain direct references to Navigation Controllers or NavHost. Route actions must be delegated via simple lambda lambdas (`onBackClick: () -> Unit`, `onNavigateToDetails: (id: String) -> Unit`).
- **Flat Route Layout**: Group sub-graphs into isolated extension functions (e.g. `fun NavGraphBuilder.authGraph(...)`, `fun NavGraphBuilder.chargerGraph(...)`).
