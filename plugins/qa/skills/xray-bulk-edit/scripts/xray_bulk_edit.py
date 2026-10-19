#!/usr/bin/env python3
"""Массовая правка Test-задач Xray и полей Jira DC: сухой прогон, защита от повторов, проверка чтением.

Запись во внешние системы из сессии агента блокирует классификатор харнесса, поэтому скрипт
предназначен для запуска владельцем через `!`. Только стандартная библиотека.

Формат входа (TSV): <ключ задачи>\t<JSON тела>
  fields: тело = содержимое объекта "fields", например {"customfield_10302": "ru.company.qa…"}
  add:    тело = {"<поле-список>": [значения]} — значения ДОПИСЫВАЮТСЯ, существующие не стираются
  steps:  тело = один шаг, {"step": …, "data": …, "result": …}; порядок строк = порядок шагов
  folders: тело = {"folder": "/Продукт/Группа"} — место теста в Test Repository; недостающие папки создаются

Использование:
  python3 xray_bulk_edit.py fields data.tsv --dry
  python3 xray_bulk_edit.py fields data.tsv
  python3 xray_bulk_edit.py add labels.tsv --dry
  python3 xray_bulk_edit.py add labels.tsv
  python3 xray_bulk_edit.py steps steps.tsv --dry
  python3 xray_bulk_edit.py steps steps.tsv
  python3 xray_bulk_edit.py folders folders.tsv --dry
  python3 xray_bulk_edit.py folders folders.tsv
  python3 xray_bulk_edit.py fields data.tsv --verify-only

Окружение: JIRA_URL (по умолчанию https://jira.example.com), JIRA_PERSONAL_TOKEN либо файл ~/jira_pat.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from pathlib import Path

BASE = os.environ.get("JIRA_URL", "https://jira.example.com").rstrip("/")
STEP_PATH = "/rest/raven/1.0/api/test/{key}/step"
ISSUE_PATH = "/rest/api/2/issue/{key}"
FOLDERS_PATH = "/rest/raven/1.0/api/testrepository/{project}/folders"
REPO_PATH_FIELD = "customfield_10309"  # Test Repository Path: «/Продукт/Группа», Xray ведёт его сам


def token() -> str:
    value = os.environ.get("JIRA_PERSONAL_TOKEN")
    if value:
        return value.strip()
    path = Path.home() / "jira_pat"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    sys.exit("нет токена: задайте JIRA_PERSONAL_TOKEN либо положите ~/jira_pat")


def call(method: str, path: str, payload=None, attempts: int = 4):
    """Возвращает (код, тело). Тело — разобранный JSON либо строка.

    Сетевой сбой повторяется с нарастающей паузой. Без этого проход по паре сотен задач — лотерея:
    инстанс временами отвечает по 20 секунд и рвёт соединение по таймауту, а две копии скрипта разом
    исчерпывают локальные порты (`OSError: [Errno 49]`). Оба случая проверены 2026-09-17/18: прогон
    умирал на середине, потеряв десятки минут чтения. Ответ сервера (в том числе 4xx и 5xx) повтора
    не вызывает — это состояние Jira, а не сбой доставки."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    for attempt in range(attempts):
        request = urllib.request.Request(BASE + path, data=data, method=method)
        request.add_header("Authorization", f"Bearer {token()}")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8", "replace")
                try:
                    return response.status, json.loads(raw) if raw.strip() else None
                except json.JSONDecodeError:
                    return response.status, raw
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8", "replace")[:300]
        except OSError as error:  # URLError, TimeoutError и исчерпание портов — все наследуют OSError
            if attempt == attempts - 1:
                return 0, f"сеть после {attempts} попыток: {error}"
            time.sleep(2 ** attempt)
    return 0, "недостижимо"


def load(path: str):
    rows = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        if "\t" not in line:
            sys.exit(f"строка {number}: нет табуляции между ключом и телом")
        key, body = line.split("\t", 1)
        try:
            rows.append((key.strip(), json.loads(body)))
        except json.JSONDecodeError as error:
            sys.exit(f"строка {number} ({key}): тело не разбирается как JSON — {error}")
    if not rows:
        sys.exit("файл данных пуст")
    return rows


def grouped(rows):
    out = OrderedDict()
    for key, body in rows:
        out.setdefault(key, []).append(body)
    return out


def step_count(key: str):
    code, body = call("GET", STEP_PATH.format(key=key))
    if code != 200 or not isinstance(body, list):
        return None
    return len(body)


def run_steps(rows, dry: bool, verify_only: bool) -> int:
    by_key = grouped(rows)
    print(f"== задач: {len(by_key)}, шагов: {len(rows)} ==")

    print("== текущее состояние ==")
    busy = []
    for key, items in by_key.items():
        current = step_count(key)
        if current is None:
            print(f"  {key}: состояние не прочитано")
            busy.append(key)
        elif current:
            print(f"  {key}: уже {current} шагов (ожидалось 0, нужно {len(items)})")
            busy.append(key)
    if not busy:
        print("  все задачи пусты")

    if verify_only:
        return verify_steps(by_key)
    if dry:
        for key, body in rows:
            print(f"would PUT {key}: {str(body.get('step', ''))[:90]}")
        return 0
    if busy:
        print(f"ОТМЕНА: у задач {' '.join(busy)} шаги уже есть либо состояние не прочитано — запись дала бы дубли")
        return 1

    ok = fail = 0
    for key, body in rows:
        code, response = call("PUT", STEP_PATH.format(key=key), body)
        if code in (200, 201, 204):
            ok += 1
        else:
            fail += 1
            print(f"FAIL {key} HTTP {code}: {str(response)[:200]}")
    print(f"PUT ok={ok} fail={fail} (ожидание: ok={len(rows)} fail=0)")
    return verify_steps(by_key) or (1 if fail else 0)


def verify_steps(by_key) -> int:
    print("== проверка чтением ==")
    bad = 0
    for key, items in by_key.items():
        current = step_count(key)
        if current == len(items):
            print(f"  {key}: {current} шагов")
        else:
            bad += 1
            print(f"  {key}: РАСХОЖДЕНИЕ ожидали {len(items)}, получили {current}")
    print(f"расхождений: {bad} (ожидание: 0)")
    return 1 if bad else 0


def same(current, wanted) -> bool:
    """Поле-перечисление Jira отдаёт объектом целиком ({"self":…, "value":…, "id":…}), а правка
    задаёт только {"value": …}: сравниваются те ключи, которые правка назвала, иначе проверка
    чтением объявляет расхождение на успешно применённой правке."""
    if isinstance(wanted, dict) and isinstance(current, dict):
        return all(current.get(name) == value for name, value in wanted.items())
    return current == wanted


def field_values(key: str, names):
    code, body = call("GET", ISSUE_PATH.format(key=key) + "?fields=" + ",".join(sorted(names)))
    if code != 200 or not isinstance(body, dict):
        return None
    return body.get("fields", {})


def run_fields(rows, dry: bool, verify_only: bool) -> int:
    print(f"== объектов: {len(rows)} ==")
    pending = []
    print("== дельта к текущему состоянию ==")
    for key, body in rows:
        current = field_values(key, body.keys())
        if current is None:
            print(f"  {key}: состояние не прочитано — правка пропускается")
            continue
        diff = {name: value for name, value in body.items() if not same(current.get(name), value)}
        if diff:
            pending.append((key, diff))
            for name, value in diff.items():
                print(f"  {key} {name}: {str(current.get(name))[:40]} → {str(value)[:60]}")
    print(f"  требуют правки: {len(pending)} из {len(rows)}")

    if verify_only:
        return 1 if pending else 0
    if dry:
        for key, diff in pending:
            print(f"would PUT {key}: {json.dumps(diff, ensure_ascii=False)[:120]}")
        return 0
    if not pending:
        print("правка уже нанесена, записывать нечего")
        return 0

    ok = fail = 0
    for key, diff in pending:
        code, response = call("PUT", ISSUE_PATH.format(key=key), {"fields": diff})
        if code in (200, 204):
            ok += 1
        else:
            fail += 1
            print(f"FAIL {key} HTTP {code}: {str(response)[:200]}")
    print(f"PUT ok={ok} fail={fail} (ожидание: ok={len(pending)} fail=0)")

    print("== проверка чтением ==")
    bad = 0
    for key, body in rows:
        current = field_values(key, body.keys())
        for name, value in body.items():
            if current is None or not same(current.get(name), value):
                bad += 1
                print(f"  {key} {name}: РАСХОЖДЕНИЕ ожидали {str(value)[:50]}, получили {str((current or {}).get(name))[:50]}")
    print(f"расхождений: {bad} (ожидание: 0)")
    return 1 if (bad or fail) else 0


def run_add(rows, dry: bool, verify_only: bool) -> int:
    """Дописывание значений в поле-список (метки, компоненты) через глагол update: значения
    добавляются, существующие не стираются. Идемпотентно по устройству: уже присутствующее
    значение в дельту не попадает."""
    print(f"== объектов: {len(rows)} ==")
    pending = []
    print("== дельта к текущему состоянию ==")
    for key, body in rows:
        current = field_values(key, body.keys())
        if current is None:
            print(f"  {key}: состояние не прочитано — правка пропускается")
            continue
        missing = {}
        for name, values in body.items():
            have = current.get(name) or []
            absent = [v for v in values if v not in have]
            if absent:
                missing[name] = absent
        if missing:
            pending.append((key, missing))
            for name, values in missing.items():
                print(f"  {key} {name}: +{values}")
    print(f"  требуют правки: {len(pending)} из {len(rows)}")

    if verify_only:
        return 1 if pending else 0
    if dry:
        for key, missing in pending:
            print(f"would PUT {key}: {json.dumps(missing, ensure_ascii=False)[:120]}")
        return 0
    if not pending:
        print("правка уже нанесена, записывать нечего")
        return 0

    ok = fail = 0
    for key, missing in pending:
        update = {name: [{"add": value} for value in values] for name, values in missing.items()}
        code, response = call("PUT", ISSUE_PATH.format(key=key), {"update": update})
        if code in (200, 204):
            ok += 1
        else:
            fail += 1
            print(f"FAIL {key} HTTP {code}: {str(response)[:200]}")
    print(f"PUT ok={ok} fail={fail} (ожидание: ok={len(pending)} fail=0)")

    print("== проверка чтением ==")
    bad = 0
    for key, body in rows:
        current = field_values(key, body.keys())
        for name, values in body.items():
            have = (current or {}).get(name) or []
            for value in values:
                if value not in have:
                    bad += 1
                    print(f"  {key} {name}: РАСХОЖДЕНИЕ нет значения {value}")
    print(f"расхождений: {bad} (ожидание: 0)")
    return 1 if (bad or fail) else 0


def folder_index(project: str):
    """Путь → id для всего дерева репозитория проекта. Путь собирается из имён: «/Корень/Подпапка»."""
    code, body = call("GET", FOLDERS_PATH.format(project=project))
    if code != 200 or not isinstance(body, dict):
        sys.exit(f"{project}: дерево репозитория не прочитано, HTTP {code}: {str(body)[:200]}")
    index = {}

    def walk(folder, prefix):
        path = f"{prefix}/{folder['name']}"
        index[path] = folder["id"]
        for sub in folder.get("folders", []):
            walk(sub, path)

    for root in body.get("folders", []):
        walk(root, "")
    return index


def repo_paths(keys):
    out = {}
    for key in keys:
        current = field_values(key, {REPO_PATH_FIELD})
        out[key] = None if current is None else (current.get(REPO_PATH_FIELD) or "")
    return out


def run_folders(rows, dry: bool, verify_only: bool) -> int:
    """Раскладка тестов по папкам Test Repository. Папка создаётся POST на родителя (корень — id -1),
    тест переносится PUT …/folders/<id>/tests {"add": [...]}. Переноса папки целиком REST не даёт:
    у PUT на папку нет поля родителя, поэтому режим только создаёт папки и двигает тесты."""
    wanted = {}
    for key, body in rows:  # файл проверяется целиком ДО первой записи
        path = body.get("folder") if isinstance(body, dict) else None
        if not isinstance(path, str) or not path.startswith("/") or "//" in path or path.endswith("/"):
            sys.exit(f"{key}: folder должен иметь вид «/Корень/Подпапка», получено {path!r}")
        if key in wanted and wanted[key] != path:
            sys.exit(f"{key}: две разные папки в файле — {wanted[key]} и {path}")
        wanted[key] = path
    projects = sorted({key.split("-")[0] for key in wanted})
    print(f"== тестов: {len(wanted)}, проектов: {' '.join(projects)} ==")

    current = repo_paths(wanted)
    unread = [key for key, path in current.items() if path is None]
    pending = {key: path for key, path in wanted.items() if current.get(key) is not None and current[key] != path}
    print("== дельта к текущему состоянию ==")
    for key, path in pending.items():
        print(f"  {key}: {current[key] or '<вне папок>'} → {path}")
    for key in unread:
        print(f"  {key}: состояние не прочитано — пропускается")
    print(f"  требуют правки: {len(pending)} из {len(wanted)}")
    if verify_only:
        return 1 if pending or unread else 0
    if not pending:
        print("правка уже нанесена, записывать нечего")
        return 1 if unread else 0

    fail = 0
    for project in projects:
        index = folder_index(project)
        targets = sorted({path for key, path in pending.items() if key.startswith(project + "-")})
        for target in targets:  # недостающие папки — по сегментам, от корня вниз
            parts = target.strip("/").split("/")
            for depth in range(1, len(parts) + 1):
                path = "/" + "/".join(parts[:depth])
                if path in index:
                    continue
                parent = index.get("/" + "/".join(parts[:depth - 1])) if depth > 1 else -1
                print(("would " if dry else "") + f"создать папку {path}")
                if dry:
                    index[path] = f"<{path}>"
                    continue
                code, created = call("POST", f"{FOLDERS_PATH.format(project=project)}/{parent}", {"name": parts[depth - 1]})
                if code not in (200, 201) or not isinstance(created, dict) or "id" not in created:
                    sys.exit(f"папка {path} не создана, HTTP {code}: {str(created)[:200]}")
                index[path] = created["id"]
        for target in targets:
            keys = sorted((k for k, p in pending.items() if p == target and k.startswith(project + "-")),
                          key=lambda k: int(k.split("-")[1]))
            print(("would " if dry else "") + f"перенести {len(keys)} → {target}: {' '.join(keys)}")
            if dry:
                continue
            code, response = call("PUT", f"{FOLDERS_PATH.format(project=project)}/{index[target]}/tests", {"add": keys})
            if code not in (200, 204):
                fail += len(keys)
                print(f"FAIL {target} HTTP {code}: {str(response)[:200]}")
    if dry:
        return 0

    print("== проверка чтением ==")
    after = repo_paths(wanted)
    bad = [key for key, path in wanted.items() if after.get(key) != path]
    for key in bad:
        print(f"  {key}: РАСХОЖДЕНИЕ ожидали {wanted[key]}, получили {after.get(key)}")
    print(f"ok={len(wanted) - len(bad)} fail={len(bad)} (ожидание: ok={len(wanted)} fail=0)")
    return 1 if (bad or fail or unread) else 0


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) < 2 or argv[0] not in ("fields", "steps", "add", "folders"):
        print(__doc__)
        return 2
    mode, path = argv[0], argv[1]
    flags = set(argv[2:])
    unknown = flags - {"--dry", "--verify-only"}
    if unknown:
        print(f"неизвестные флаги: {' '.join(sorted(unknown))}")
        return 2
    rows = load(path)
    dry = "--dry" in flags
    verify_only = "--verify-only" in flags
    if mode == "steps":
        return run_steps(rows, dry, verify_only)
    if mode == "add":
        return run_add(rows, dry, verify_only)
    if mode == "folders":
        return run_folders(rows, dry, verify_only)
    return run_fields(rows, dry, verify_only)


if __name__ == "__main__":
    sys.exit(main())
