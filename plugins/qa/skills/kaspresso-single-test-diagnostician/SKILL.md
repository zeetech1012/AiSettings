---
name: kaspresso-single-test-diagnostician
description: >
  Диагностика ОДНОГО падающего Kaspresso/Compose instrumented-теста на живом
  устройстве/эмуляторе без gradle-деинсталляции APK: точечный прогон через
  `adb shell am instrument`, извлечение step-скриншотов и Allure-результатов из
  приватных каталогов приложения через `run-as`, генерация Allure-отчёта,
  разбор причины по дереву решений. Triggers on: "diagnose single test",
  "прогони один тест", "достань скриншоты падения", "почему падает этот ui-тест",
  "single test screenshots", "am instrument", "run-as screenshots",
  "instrumented test fails on device", "нужен allure по одному тесту",
  "пустой allure-отчёт", "allure results с устройства".
---

# SKILL: KASPRESSO_SINGLE_TEST_DIAGNOSTICIAN

## Цель
Локализовать причину падения **одного** instrumented UI-теста (Kaspresso + Compose,
`energy-app-native`) на реальном устройстве/эмуляторе. Главное отличие от gradle —
**APK НЕ деинсталлируется**, поэтому step-скриншоты и `test_failed.png` из `cacheDir`
переживают прогон (gradle `connectedAndroidTest` удаляет приложение и теряет их).

Применять, когда:
- тест красный только на устройстве (не в `testDebugUnitTest`);
- нужны визуальные доказательства состояния экрана на шаге падения;
- gradle-прогон не даёт скриншоты (cacheDir вычищен деинсталляцией);
- надо отличить «логин не прошёл» от «локатор не нашёлся».

НЕ применять для: component-тестов на JVM-хосте (в проекте — `L1`; там нет устройства), массового
прогона сьюта (это `scripts/run_tests.sh` / `connectedDebugAndroidTest`).

---

## Предусловия (проверить до запуска)

```bash
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"

adb devices                          # устройство online?
adb shell getprop sys.boot_completed # == 1 (эмулятор догрузился)
adb shell pm list packages | grep example   # test+app APK уже установлены?
```

`APP_PKG` берётся из `applicationId` в `composeApp/build.gradle.kts`, тестовый пакет —
`$APP_PKG.test`. В ветках релиза 1.4.0 это `com.example.home`; в старых ветках был
`com.legacy.examplehome`. **Сверять по gradle-файлу, не подставлять по памяти** — неверный
пакет даёт `run-as: unknown package`, а с подавленным stderr это читается как «файлов нет».

Если APK не установлены — сначала **один раз** поставить их gradle'ом
(`./gradlew :composeApp:installDebug :composeApp:installDebugAndroidTest`),
дальше гонять точечно через `am instrument` (он не переустанавливает → cacheDir цел).

---

## Алгоритм

### 1. Точечный прогон теста + проброс кредов
e2e-тесты требуют `QA_TEST_*` как instrumentation args (в коде их НЕТ, fallback `""`).
**Пустые креды → «wrong code/email» — это by design, не баг.**

Креды брать из `~/.qa_creds`, **не хардкодить в команде** (файл под `chmod 600`,
значения в вывод не печатать):

```bash
set -a; . ~/.qa_creds; set +a
APP_PKG=com.example.home            # сверить с applicationId

adb shell am instrument -w \
  -e class "$APP_PKG.tests.smoke.LoginByEmailSubmitTest#failedLoginShowsError" \
  -e QA_TEST_EMAIL "$QA_TEST_EMAIL" \
  -e QA_TEST_PASSWORD "$QA_TEST_PASSWORD" \
  "$APP_PKG.test/com.kaspersky.kaspresso.runner.KaspressoRunner"
```
- `-e class '<FQN>#<method>'` — один тест; без `#method` — весь класс.
- Креды прокидывать всегда для login-зависимых тестов, иначе диагностируешь ложное падение.
- FQN теста не обязан совпадать с `applicationId` (в 1.4.0 совпадает); брать из `package`
  тестового файла.

### 2. Извлечь step-скриншоты из cacheDir
`BaseTestCase` (screenshot step rule + watcher) сохраняет `step_*.png` и `test_failed.png`
в `cacheDir` приложения. Тащить через `run-as` (приложение debuggable):

```bash
adb shell run-as "$APP_PKG" ls cache/
# забрать конкретный скрин (exec-out — без CRLF-порчи бинарных данных):
adb exec-out run-as "$APP_PKG" cat cache/test_failed.png > /tmp/test_failed.png
```
Затем прочитать `/tmp/*.png` инструментом Read — он покажет картинку визуально
(виден ли элемент, есть ли клавиатура, на каком экране остановились).

### 3. Снять иерархию Compose (если скрина мало)
Падение `ComposeInteractionException` печатает `ViewHierarchy` в logcat — сопоставить
упавший `testTag` с Page Object. При «found but not displayed» смотреть `isPlaced`.

### 4. Собрать Allure-результаты и сгенерировать отчёт

`allure-kotlin-android` пишет результаты в **приватный каталог приложения**:
`AllureAndroidLifecycleKt.obtainResultsDirectory()` = `File(targetContext.filesDir, "allure-results")`,
то есть `/data/data/$APP_PKG/files/allure-results`. Имя каталога задаётся ключом
`allure.results.directory` в `allure.properties` на classpath, по умолчанию `allure-results`.
**На `/sdcard` библиотека не пишет ничего.**

**Чистить прежние результаты до каждого прогона** — иначе отчёт смешает прогоны и покажет
чужие падения как текущие:

```bash
adb shell run-as "$APP_PKG" rm -rf files/allure-results   # на устройстве
rm -rf allure-results allure-report                        # локально
```

После прогона (APK ещё установлен) забрать результаты по файлам:

```bash
mkdir -p allure-results
while IFS= read -r f; do
  [ -n "$f" ] || continue
  adb exec-out run-as "$APP_PKG" cat "files/allure-results/$f" > "allure-results/$f"
done < <(adb shell run-as "$APP_PKG" ls files/allure-results | tr -d '\r')
allure generate allure-results -o allure-report --clean
```

Две ловушки цикла:
- `tr -d '\r'` обязателен: `adb shell` отдаёт имена с CRLF, без чистки `cat` не найдёт файл.
- Именно `while read`, а не `for f in $VAR`. Разбиение по IFS у расширения переменной работает
  в bash, но **не в zsh** (там делится только подстановка команд), и одно имя с переводом строки
  создаёт локально один файл-мусор вместо всех результатов. Проверять размеры выгруженных файлов
  против `run-as ls -l` — расхождение означает, что цикл отработал неверно.
Отчёт целиком — каталог, поэтому в тикет он идёт архивом
(`zip -qr report.zip .` из `allure-report`, затем `add_issue_attachment`). Выгрузка на центральный
`allure-docker-service` вместо архива — процедура в вики:
`Company/_wiki/qa-infra/allure-publish-procedure.md` (login → CSRF → send-results → generate-report,
готовый скрипт и джоба CI).

---

## Чистка логов прогона

Logcat приходит с системным шумом Android, в котором шаги теста теряются. Отфильтровать до значимого:

- **выбросить** строки `dalvikvm`, `ActivityManager`, `PackageManager`, `ViewRootImpl`,
  `OpenGLRenderer`, `Choreographer` и прочие фоновые службы;
- **оставить** `Kaspresso:` (шаги, хуки, инициализация DSL), `ViewHierarchy:` (дерево Compose на
  момент падения), `Exception` и `Caused by:`, `I/Allure:` и `AllureRunListener`.

Дальше локализация: найти последний успешный `step("…")`, затем первое исключение
(`ComposeInteractionException`, `AssertionError`, `NullPointerException`) и сопоставить `testTag` из
`ViewHierarchy` со Screen-объектом. В итог писать: в каком шаге наблюдался отказ · что именно
разошлось с ожиданием (какой `testTag` не найден и за какое время) · 3–5 строк стека · предполагаемый
фикс. Формулировка «тест упал» итогом не является — описывается наблюдаемый отказ.

---

## Дерево решений (типовые падения)

| Симптом на скрине / в стеке | Корень | Фикс |
|---|---|---|
| Элемент **виден** на скрине, но `... found but not displayed` / `isPlaced=false` | merged semantics tree (напр. `text_error` внутри `supportingText` OutlinedTextField) | `useUnmergedTree=true` в Screen-объекте (см. `LoginByEmailScreen.errorText`) |
| На скрине экран логина с «wrong code/email», тест ждёт `tab_*Route` | логин не прошёл — пустые/неверные `QA_TEST_*` | пробросить корректные креды в `-e QA_TEST_*` |
| Нужный экран не открылся после тапа на `item_settings_*` | нет `screen_*`-тега на корне / экран не навигируется | проверить `RootRoutes`, повесить `testTag` на корень экрана |
| Тест флакает на ожидании элемента | гонка рендера Compose | `flakySafely { ... }` в Robot (НЕ `Thread.sleep`) |

---

## ⛔ Запрещённые / доказанно ложные гипотезы

- **НЕ возвращать keyboard-фиксы.** `hideKeyboard()` (UiDevice) и `Espresso.closeSoftKeyboard()`
  проверены и **не чинят** `text_error`/`tab_*Route`. Скриншоты доказали: элемент виден,
  клавиатуры нет → причина merged-tree, а не клавиатура.
- **`Espresso.closeSoftKeyboard()` / `device.exploit.pressBack()` в чистом Compose ненадёжны**
  (нет focused Android View; `Exploit.pressBack` = тот же Espresso по байткоду Kaspresso 1.5.5).
  Надёжно только OS-level `device.uiDevice` — но в известных падениях клавиатура ни при чём.
- **НЕ полагаться на agy/executor для вывода результата** — он зависает после gradle (~30 мин,
  0-байтный буфер). Читать JUnit XML напрямую
  (`composeApp/build/outputs/androidTest-results/.../*.xml`); при зависании `pkill -f "agy -p"`.
- **НЕ гонять диагностику через `connectedAndroidTest`** — деинсталляция APK после прогона
  стирает cacheDir и `files/allure-results` → скриншоты падения и Allure-результаты теряются.
- **Пустой Allure-отчёт ≠ библиотека не пишет на Android 11+.** Проверено на Pixel 10 /
  Android 17: `allure-kotlin-android` 2.4.0 результаты пишет исправно, в `filesDir` приложения.
  Пустой отчёт из `scripts/run_tests.sh` объясняется двумя вещами: скрипт забирает результаты
  из `/sdcard/allure-results` (`DEVICE_RESULTS`), куда библиотека не пишет, и gradle сносит APK
  вместе с каталогом. Не откатывать версию allure и не искать обходов scoped storage —
  чинится путём выгрузки через `run-as`.
- **НЕ подавлять stderr в проверках `run-as` / `adb`** (`2>/dev/null`). При неверном пакете
  `run-as` печатает `unknown package`, а с подавленным stderr `| wc -l` вернёт 0 и «нет файлов»
  будет принято за факт. То же с `adb` вне PATH: `command not found` уйдёт в никуда.

---

## Формат итогового вывода

- **Тест**: `<FQN>#<method>` (прогон: `am instrument`, креды: да/нет).
- **Где упал**: шаг `step("...")` / Robot-взаимодействие.
- **Что на скрине**: `test_failed.png` — какой экран, виден ли целевой элемент, есть ли клавиатура.
- **Корень** (по дереву решений выше): merged-tree / пустые креды / нет тега / гонка рендера.
- **Фикс**: конкретное изменение (`useUnmergedTree=true` в `<Screen>`, проброс `QA_TEST_*`,
  `testTag` на корень, `flakySafely`). **Без keyboard-фиксов.**
- **Скриншоты**: пути в `/tmp/*.png` (приложить к отчёту). Если падение — **реальный прод-баг** (не пустые креды, не merged-tree локатора): эти же скрин + видео идут вложением в баг-тикет (`add_issue_attachment`), а repro собирается из GWT-шагов теста как действия пользователя.
