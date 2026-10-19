# Service-issue → Xray в Jira DC

> Адресатная часть скилла. Общие правила — в `SKILL.md` уровнем выше, ловушки самой Jira — в `jira/notes.md`.
> Всё ниже снято с живого инстанса `jira.example.com` (Jira **11.3.8 Server**, Xray как плагин) 2026-08-06 и 2026-08-07.

## Почему не MCP

Готовые MCP-серверы под Xray проверены и отклонены 2026-08-07:

- `madhawar/xray-mcp-azure` — работает **только с Xray Cloud** через GraphQL `xray.cloud.getxray.app` и пару `client_id`/`client_secret`. На Server/DC не запускается в принципе.
- `jithinjosejacob/xray-mcp-server` — Server/DC поддерживает, но все восемь инструментов относятся к прогонам: импорт результатов, создание и обновление Test Execution, список Test Plan. Ни Test Repository, ни Test Set, ни удаления тестов. Плюс требует передать ему PAT администратора Jira при трёх коммитах в репозитории.

Прямой REST покрывает больше и не выносит токен наружу.

## Модель: четыре разные сущности

| Что | Чем является | Ключевое свойство |
|---|---|---|
| **Test Repository** | дерево папок, принадлежит проекту | тест лежит ровно в одной папке; хранится на стороне Xray, обычным JQL не ищется |
| **Test Set** | задача типа `Test Set` | пересекающаяся группировка, тест входит в сколько угодно наборов |
| **Test Run** | **не задача** | результат прогона внутри Test Execution, в JQL не виден |
| Вкладки `Плагины → Tests / Test Sets / …` | плоские списки задач по типу | эквивалент `project = X AND issuetype = Test`, структуры не несут |

Папка отвечает на вопрос «где тест живёт», набор — «что запускаем вместе». Одно другое не заменяет.

Следствие для досок: типы Xray составляют большую часть проекта (в `WH` 124 из 191, в `API` 183 из 210), поэтому фильтр доски обязан их исключать по типу.

## Test Repository — REST

Базовый путь: `/rest/raven/1.0/api/testrepository/{projectKey}/folders`

| Операция | Вызов |
|---|---|
| Прочитать дерево | `GET {base}` → `{allTestsCount, allOrphanTestsCount, folders[]}` |
| Создать папку | `POST {base}/{parentId}` тело `{"name": "…"}`; корень — `parentId` = `-1` |
| Положить тесты | `PUT {base}/{folderId}/tests` тело `{"add": ["DEMO-51", "DEMO-54"]}` |
| Удалить папку | `DELETE {base}/{folderId}` |

> ⚠️ **Ловушка формы.** `POST {base}/{parentId}/folders` отвечает **404**. Хвостовой сегмент `/folders` нужен только при чтении дерева; при создании его нет.

Ответ на создание: `{"rank": N, "id": N, "testCount": 0, "totalTestCount": 0, "name": "…"}`. `id` понадобится для вложения и для укладки тестов.

Счётчики в интерфейсе читаются как `прямо_в_папке (во_всём_поддереве)`.

## Test Set и окружения — через обычный issue update

Наполнение набора и простановка окружения выполняются обычным `PUT /rest/api/2/issue/{key}`:

```
{"fields": {"customfield_10310": ["DEMO-55"]}}   тесты в Test Set
{"fields": {"customfield_10323": ["device"]}}   Test Environments
```

## Идентификаторы полей этого инстанса

| id | Поле |
|---|---|
| `customfield_10300` | Test Type |
| `customfield_10302` | **Generic Test Definition** — по нему Xray сопоставляет повторные прогоны |
| `customfield_10303` | Manual Test Steps |
| `customfield_10305` | Test Sets association with a Test |
| `customfield_10309` | Test Repository Path |
| `customfield_10310` | Tests association with a Test Set |
| `customfield_10311` | Test Count |
| `customfield_10313` | Tests association with a Test Execution |
| `customfield_10323` | **Test Environments** |
| `customfield_10324` | Tests associated with a Test Plan |

Типы задач Xray: `Test` 10200, `Test Set` 10201, `Test Execution` 10202, `Pre-Condition` 10203, `Test Plan` 10204, `Sub Test Execution` 10205 (подзадачный). Схема одна у `WH` и `API`.

## Ловушки, пойманные в бою

**Обратная связь набора не читается поиском.** `customfield_10305` в ответе `/rest/api/2/search` приходит пустым, хотя связь существует; счётчик на стороне набора (`customfield_10311`) при этом показывает верное число. Проверять принадлежность к набору через поиск нельзя, только со стороны Test Set.

**JQL по длинным именам полей Xray падает.** Запросы вида `"Test Sets association with a Test" is EMPTY` возвращают ошибку. Обращаться по id поля либо через Xray API.

**Заголовок `null` у теста — не тест.** Определение вида `<полное.имя.Класса>.null` означает отказ класса до первого метода: инструментальный прогон отдал в JUnit XML элемент `testcase` с заполненным `classname` и пустым `name`. Такие задачи не описывают проверку, портят счёт покрытия и подлежат удалению, а причина заводится дефектом. Пока класс падает на подготовке, следующий импорт создаст их заново.

**Импорт сопоставляет по `Generic Test Definition`.** Переименование теста в коде порождает новую задачу `Test`, старая остаётся сиротой.

**Окружение — свободная строка.** Разнобой написаний раскалывает историю прогонов. Значение держать равным контуру прогона; когда контуров несколько, брать его из той же переменной, что и тесты (`prod` · `staging` · `test`).

## Порядок наведения порядка в наборе

1. Прочитать дерево, посмотреть `allOrphanTestsCount`.
2. Снять `Generic Test Definition` всех тестов, разложить по пакетам.
3. Завести папки по платформе и каноническому уровню (System, System integration, Acceptance), не по именам классов.
4. Уложить тесты пакетно, по одному `PUT` на папку.
5. Проверить, что сирот не осталось.
6. Тесты с заголовком `null` удалить, предварительно сохранив запись, и завести дефект на причину.

## Ловушка — создание шагов теста через v2 (2026-09-15)

`POST /rest/raven/2.0/api/test/{key}/steps` с телом `{"fields": {"Action": …, "Data": …, "Expected Result": …}}` отвечает
`{"step": {"id": N, "attachmentIds": []}, "warnings": []}`: идентификатор вложен в `step`. Проверка `"id" in ответ` ложно
считает вызов неудачным, а запасной `PUT /rest/raven/1.0/api/test/{key}/step` создаёт шаг второй раз (так задвоились
шаги 32 тестов 15.09). Удаление шага: `DELETE /rest/raven/2.0/api/test/{key}/steps/{stepId}`. Результаты шагов прогона
читать из `GET /rest/raven/1.0/api/testrun/{runId}` (поле `steps`), статус шага ставить `PUT /rest/raven/2.0/api/testrun/{runId}/step/{stepId}`
с телом `{"status": "FAIL", "actualResult": …}`; `GET …/2.0/api/testrun/{id}/step` возвращает пустой список. Управление
Test Repository требует членства учётной записи в роли проекта, права applicationRole недостаточно.

## Создание Manual Test и Test Set через REST (проверено 2026-09-18, HW)

Ручные тесты железа заводятся REST без импорта (канон «Generic Test только импортом» относится к автотестам):

- `POST /rest/api/2/issue` с `issuetype 10200`, `customfield_10300: {"id": "10000"}` (Manual) и
  `customfield_10309: "/Испытания изделий/<изделие>/<вид>"` для **существующей** папки принимается и кладёт тест в папку;
  отказ `Invalid Test Repository Path` только на несуществующий путь. Для надёжности после создания
  `PUT /rest/raven/1.0/api/testrepository/HW/folders/{id}/tests {"add": [...]}` (идемпотентно, тест переезжает).
- Шаги: `POST /rest/raven/2.0/api/test/{key}/steps` с `{"fields": {"Action", "Data", "Expected Result"}}`, ответ `step.id`;
  писать только в тест с нулём шагов (`GET …/2.0/api/test/{key}/steps` → `steps`).
- Test Set: `issuetype 10201`; состав `GET/POST /rest/raven/1.0/api/testset/{key}/test`, `POST {"add": [...]}`
  (OPTIONS разрешает POST); добавлять только отсутствующие.
- Готовый скрипт с сухим прогоном, защитой от повтора и сверкой чтением: рабочий каталог
  `qa-infra/xray/xray_create_tests.py` + `hw_fobos_tests.json` (67 тестов, 5 наборов за один проход, ~350 запросов, 0 ошибок).
- Задачи релиза с `fixVersions`, компонентом и связью Relates: `qa-infra/jira/hw_release_tasks.py` + JSON;
  тип связи на инстансе называется `Relates`, тип «Задача» 10101, `PUT …/issue/{key}?notifyUsers=false`
  с `{"update": {"fixVersions": [{"add": {"id": …}}]}}` добавляет версию без письма.

## Pre-Condition через REST (проверено 2026-09-18, HW)

- Создание: `POST /rest/api/2/issue` с `issuetype 10203`, `customfield_10319: {"id": "10003"}` (тип Manual; Cucumber 10004,
  Generic 10005), текст условий в `customfield_10320` (Conditions), компонент изделия, метка `hardware`.
- Привязка к тестам: `POST /rest/raven/1.0/api/precondition/{key}/test {"add": [...]}` (OPTIONS даёт HEAD,POST,GET,OPTIONS);
  состав читается `GET` там же; со стороны теста `GET /rest/raven/1.0/api/test/{key}/preconditions` (только чтение).
  Добавлять только отсутствующие: повторный POST не проверялся на дубли.
- Библиотека предусловий на изделие (3–6 штук) вместо предусловия первым шагом; скрипт с предусловиями, компонентами на тест
  и папками по имени: `qa-infra/xray/xray_create_tests2.py` (134 объекта за проход, ok=118 fail=0).
- Папка репозитория создаётся тем же скриптом: `POST …/folders/{parentId} {"name"}` затем шесть видов проверок; путь
  `customfield_10309` принимается на создании теста только для уже существующей папки, поэтому создание папки идёт до тестов.

## Импорт прогонов задним числом (Xray JSON `import/execution`), проверено 2026-09-21 на DEMO-56

```text
POST /rest/raven/1.0/import/execution   Content-Type: application/json, Bearer PAT
{"info": {"project": "HW", "summary": …, "description": …, "revision": …, "testEnvironments": ["lab"], "testPlanKey": "DEMO-57",
          "startDate": "2025-05-06T10:00:00+03:00", "finishDate": "2025-05-06T12:30:00+03:00"},
 "tests": [{"testKey": "DEMO-58", "status": "FAIL", "start": "2025-05-06T10:05:00+03:00", "finish": "2025-05-06T10:40:00+03:00",
            "comment": …, "executedBy": "example-user", "steps": [{"status": "PASS", "actualResult": …}, …]}]}
→ 200 {"testExecIssue": {"key": "DEMO-56"}, "testIssues": {"success": [...]}}   # отказы тестов лежат в теле, сверять чтением
```

- Ложатся задним числом: Begin Date 10315, End Date 10316 (из info.startDate/finishDate), Revision 10317, Test Environments 10323,
  Test Plan 10325; у Test Run startedOn/finishedOn, executedBy (и assignee), comment, статусы и Actual Result шагов.
- Не ложится: Created задачи (= дата импорта). `info.version` только существующая версия Jira.
- Последний статус тестов в плане берётся из последнего СОЗДАННОГО прогона, даты не участвуют: история задним числом перекрывает
  текущие результаты (на DEMO-57 статусы сменились через ~5 минут после импорта, первое чтение отдаёт кеш). Исторические прогоны
  в отдельный план, в хронологическом порядке, только для тестов без актуальных прогонов.
- Шаги и комментарий читать `GET /rest/raven/1.0/api/testrun?testExecIssueKey=<exec>&testIssueKey=<test>`;
  `testexec/<key>/test?detailed=true` шагов не отдаёт.
- Скрипт: `qa-infra/xray/xray_import_runs.py` (--dry, защита от повтора по теме, ok=N fail=M).
