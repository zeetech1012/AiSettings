#!/usr/bin/env python3
"""Односторонняя синхронизация Jira IOT → vault: шапки постановок `tasks/*.md` и индекс `tasks/README.md`.

Карта coverage-queue, тикет 05. Только stdlib. Jira читается по REST (PAT из `~/jira_pat` или
`JIRA_PERSONAL_TOKEN`), vault читается и пишется через `obsidian eval` — прямой записи в файлы vault нет.

Что пишет скрипт (машинная часть шапки, тикет 01): `jira`, `summary`, `jira_status`, `epic`, `labels`,
`component`, `conditions`, `synced`. Что не трогает: тело постановки и человеческую часть шапки
(`type`, `project`, `status`, `executor`, `needs`, любые другие ключи). Постановка для закрытой в Jira
задачи не удаляется: обновляется `jira_status`, поле `status` заметки остаётся человеческим.

Режимы:
  jira_vault_sync.py --dry      дельта на экран, ничего не пишется
  jira_vault_sync.py            запись + проверка чтением, итог `ok=N fail=0`
  jira_vault_sync.py --verify   только сверка текущего состояния с ожидаемым, без записи
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
MACHINE_KEYS = ["jira", "summary", "jira_status", "epic", "labels", "component", "conditions", "synced"]
BEGIN, END = "<!-- queue:begin -->", "<!-- queue:end -->"
TABLE_HEAD = "| Ключ | Заголовок | Статус Jira | Условия | Тело | needs |\n|---|---|---|---|---|---|"
KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")


# ----------------------------------------------------------------------------- конфигурация и Jira

def load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["_root"] = path.parent.parent
    return cfg


def token() -> str:
    value = os.environ.get("JIRA_PERSONAL_TOKEN")
    if value:
        return value.strip()
    path = Path.home() / "jira_pat"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    sys.exit("нет токена: задайте JIRA_PERSONAL_TOKEN либо положите ~/jira_pat")


def call(base: str, path: str, attempts: int = 4):
    """GET с повтором при сетевом сбое (инстанс временами отвечает по 20 с и рвёт соединение).
    Ответ сервера, включая 4xx/5xx, повтора не вызывает — это состояние Jira, а не доставки."""
    for attempt in range(attempts):
        request = urllib.request.Request(base + path)
        request.add_header("Authorization", f"Bearer {token()}")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8", "replace")
                return response.status, json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8", "replace")[:300]
        except OSError as error:
            if attempt == attempts - 1:
                return 0, f"сеть после {attempts} попыток: {error}"
            time.sleep(2 ** attempt)
    return 0, "недостижимо"


def issue_record(issue: dict, epic_field: str) -> dict:
    fields = issue["fields"]
    return {
        "key": issue["key"],
        "summary": fields["summary"].strip(),
        "status": fields["status"]["name"],
        "done": fields["status"]["statusCategory"]["key"] == "done",
        "epic": fields.get(epic_field) or "none",
        "labels": sorted(fields.get("labels") or []),
        "component": ", ".join(c["name"] for c in fields.get("components") or []) or "none",
    }


def jira_fields(cfg: dict) -> str:
    return ",".join(["summary", "status", "labels", "components", "issuetype", cfg["epic_link_field"]])


def build_jql(cfg: dict) -> str:
    types = ", ".join(f'"{t}"' for t in cfg["issue_types"])
    epics = ", ".join(cfg["epics"])
    return (f'project = {cfg["project"]} AND issuetype in ({types}) AND statusCategory != Done '
            f'AND (labels = {cfg["label"]} OR "Epic Link" in ({epics})) ORDER BY key')


def jira_selection(cfg: dict) -> list[dict]:
    base, jql, out, start = cfg["jira_url"].rstrip("/"), build_jql(cfg), [], 0
    while True:
        query = urllib.parse.urlencode({"jql": jql, "startAt": start, "maxResults": 100, "fields": jira_fields(cfg)})
        code, body = call(base, "/rest/api/2/search?" + query)
        if code != 200:
            sys.exit(f"Jira search → {code}: {body}")
        out.extend(issue_record(i, cfg["epic_link_field"]) for i in body["issues"])
        start += len(body["issues"])
        if not body["issues"] or start >= body["total"]:
            return out


def jira_issue(cfg: dict, key: str) -> dict | None:
    """Поштучный GET: пакетный `key in (…)` с набором полей на этом инстансе уходит в таймаут."""
    code, body = call(cfg["jira_url"].rstrip("/"), f"/rest/api/2/issue/{key}?fields={jira_fields(cfg)}")
    if code == 404:
        return None
    if code != 200:
        sys.exit(f"Jira {key} → {code}: {body}")
    return issue_record(body, cfg["epic_link_field"])


# ----------------------------------------------------------------------------- реестр условий и соответствие

def load_registry(path: Path, plans: dict) -> dict[str, dict]:
    """`<план>-<id>` → запись реестра, только планы из конфига (границы IOT)."""
    by_source = {v: k for k, v in plans.items()}
    out = {}
    for row in json.loads(path.read_text(encoding="utf-8")):
        prefix = by_source.get(row["source"])
        if prefix:
            out[f"{prefix}-{row['id']}"] = row
    return out


def load_conditions_map(path: Path, registry: dict, plans: dict) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Возвращает соответствие задача → условия и отдельно задачи, сознательно оставленные без условий."""
    result, deliberate, errors = {}, {}, []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) not in (2, 3) or not KEY_RE.match(parts[0].strip()):
            errors.append(f"строка {lineno}: ожидалось <ключ>\\t<условия> либо <ключ>\\tnone\\t<причина>")
            continue
        key = parts[0].strip()
        if key in result:
            errors.append(f"строка {lineno}: ключ {key} встречается второй раз")
            continue
        if parts[1].strip() == "none":
            reason = parts[2].strip() if len(parts) == 3 else ""
            if not reason:
                errors.append(f"{key}: селектор none без причины — причина обязательна")
            deliberate[key] = reason
            result[key] = []
            continue
        if len(parts) == 3:
            errors.append(f"строка {lineno}: третья колонка допустима только вместе с селектором none")
            continue
        conditions = []
        for item in parts[1].split():
            if item.startswith("area:"):
                _, prefix, area = item.split(":", 2)
                source = plans.get(prefix)
                hits = [cid for cid, row in registry.items()
                        if row["source"] == source and row["area"].startswith(area)]
                if not hits:
                    errors.append(f"{key}: селектор {item} не нашёл условий в реестре")
                conditions.extend(hits)
            elif item in registry:
                conditions.append(item)
            else:
                errors.append(f"{key}: условие {item} не найдено в реестре (формат <план>-<id>, планы {', '.join(plans)})")
        result[key] = sorted(dict.fromkeys(conditions), key=condition_sort_key)
    if errors:
        sys.exit("соответствие задача → условия:\n  " + "\n  ".join(errors))
    return result, deliberate


def condition_sort_key(cid: str):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", cid)]


# ----------------------------------------------------------------------------- Obsidian: чтение и запись через eval

def obsidian_ready() -> None:
    try:
        done = subprocess.run(["obsidian", "vault", "list"], capture_output=True, text=True, timeout=15)
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        sys.exit(f"CLI obsidian недоступен ({error}); приложение должно быть запущено: open -a Obsidian")
    if done.returncode != 0:
        sys.exit(f"Obsidian не отвечает: {done.stderr.strip() or done.stdout.strip()}; запустите open -a Obsidian")


def obsidian_eval(js: str, result: Path, timeout: int = 60):
    """Запускает async-код в приложении; итог приходит файлом (верхнеуровневый await в eval не работает)."""
    if result.exists():
        result.unlink()
    try:
        subprocess.run(["obsidian", "eval", "code=" + js], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        pass  # приложение продолжает выполнять код; итог придёт файлом
    deadline = time.time() + timeout
    while time.time() < deadline:
        if result.exists():
            data = json.loads(result.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "error" in data:
                sys.exit(f"obsidian eval: {data['error']}")
            return data
        time.sleep(0.3)
    sys.exit(f"obsidian eval: нет результата за {timeout} с ({result})")


def js_wrap(body: str, result: Path) -> str:
    return ("(async () => { const fs = require('fs'); const R = " + json.dumps(str(result)) + ";\n"
            "  const finish = (v) => { fs.writeFileSync(R + '.tmp', JSON.stringify(v)); fs.renameSync(R + '.tmp', R); };\n"
            "  try {\n" + body + "\n  } catch (e) { finish({error: String(e && e.stack || e)}); }\n"
            "})(); 'started'")


def read_folder(folder: str, workdir: Path) -> list[dict]:
    body = (
        "    const folder = app.vault.getFolderByPath(" + json.dumps(folder) + ");\n"
        "    if (!folder) throw new Error('нет папки ' + " + json.dumps(folder) + ");\n"
        "    const out = [];\n"
        "    for (const f of folder.children) { if (f.extension !== 'md') continue;\n"
        "      out.push({path: f.path, content: await app.vault.read(f)}); }\n"
        "    finish(out);"
    )
    return obsidian_eval(js_wrap(body, workdir / "read.json"), workdir / "read.json")


def apply_plan(plan: dict, workdir: Path) -> list[str]:
    plan_path = workdir / "plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    body = (
        "    const plan = JSON.parse(fs.readFileSync(" + json.dumps(str(plan_path)) + ", 'utf8'));\n"
        "    const log = [];\n"
        "    for (const c of plan.creates) {\n"
        "      if (app.vault.getFileByPath(c.path)) throw new Error('файл уже есть: ' + c.path);\n"
        "      await app.vault.create(c.path, c.content); log.push('created ' + c.path); }\n"
        "    for (const u of plan.updates) {\n"
        "      const f = app.vault.getFileByPath(u.path); if (!f) throw new Error('нет файла: ' + u.path);\n"
        "      let n = 0;\n"
        "      await app.vault.process(f, t => { n = t.split(u.old).length - 1; return n === 1 ? t.replace(u.old, () => u.new) : t; });\n"
        "      if (n !== 1) throw new Error('якорь совпал ' + n + ' раз: ' + u.path);\n"
        "      log.push('updated ' + u.path); }\n"
        "    finish(log);"
    )
    return obsidian_eval(js_wrap(body, workdir / "apply.json"), workdir / "apply.json", timeout=120)


# ----------------------------------------------------------------------------- frontmatter: разбор и сборка

def split_frontmatter(text: str):
    """→ (полный блок с ограждениями, внутренние строки, тело) либо (None, None, text)."""
    if not text.startswith("---\n"):
        return None, None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, None, text
    block = text[: end + 5]
    return block, text[4: end + 1].split("\n"), text[end + 5:]


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\") if value[0] == '"' else inner.replace("''", "'")
    return value


def parse_scalar(rest: str):
    rest = rest.strip()
    if rest.startswith("["):
        close = rest.find("]")
        inner = rest[1: close if close >= 0 else None]
        return [unquote(x) for x in split_flow(inner)]
    if rest.startswith(("\"", "'")):
        quote, i = rest[0], 1
        while i < len(rest):
            if rest[i] == "\\" and quote == '"':
                i += 2
                continue
            if rest[i] == quote:
                return unquote(rest[: i + 1])
            i += 1
        return unquote(rest)
    return rest.split(" #", 1)[0].strip()


def split_flow(inner: str) -> list[str]:
    items, buf, quote = [], "", None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote, buf = ch, buf + ch
        elif ch == ",":
            items.append(buf)
            buf = ""
        else:
            buf += ch
    items.append(buf)
    return [x for x in (i.strip() for i in items) if x]


def parse_items(lines: list[str]) -> list[tuple]:
    """[(key | None, value, raw_lines)] — порядок и комментарии сохраняются для обратной сборки."""
    items, i = [], 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^([A-Za-z_][\w-]*):(.*)$", line)
        if not match:
            items.append((None, None, [line]))
            i += 1
            continue
        key, rest, raw = match.group(1), match.group(2), [line]
        if rest.split(" #", 1)[0].strip() == "":
            values, j = [], i + 1
            while j < len(lines) and re.match(r"^\s*-\s", lines[j]):
                values.append(unquote(lines[j].split("-", 1)[1]))
                raw.append(lines[j])
                j += 1
            items.append((key, values if values else "", raw))
            i = j
        else:
            items.append((key, parse_scalar(rest), raw))
            i += 1
    return items


def needs_quote(value: str) -> bool:
    return (value == "" or value != value.strip() or value.lower() in ("true", "false", "null", "yes", "no", "~")
            or value[0] in "-?*&!|>'\"%@`[]{},#" or bool(re.search(r"(: |\s#|[\[\]{},])", value)))


def yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False) if needs_quote(value) else value


def yaml_list(values: list[str]) -> str:
    return "[" + ", ".join(yaml_scalar(v) for v in values) + "]"


def machine_lines(desired: dict) -> list[str]:
    return [
        f"jira: {desired['jira']}",
        f"summary: {json.dumps(desired['summary'], ensure_ascii=False)}",
        f"jira_status: {yaml_scalar(desired['jira_status'])}",
        f"epic: {desired['epic']}",
        f"labels: {yaml_list(desired['labels'])}",
        f"component: {yaml_scalar(desired['component'])}",
        f"conditions: {yaml_list(desired['conditions'])}",
        f"synced: {desired['synced']}",
    ]


def rebuild_frontmatter(lines: list[str], desired: dict) -> str:
    """Человеческие строки в прежнем порядке, машинные — одним блоком после `project` (или `type`, или сверху)."""
    items = parse_items(lines)
    human = [it for it in items if it[0] not in MACHINE_KEYS]
    anchor = -1
    for idx, (key, _, _) in enumerate(human):
        if key in ("type", "project"):
            anchor = idx
    out = []
    if anchor < 0:
        out.extend(machine_lines(desired))
    for idx, (_, _, raw) in enumerate(human):
        out.extend(raw)
        if idx == anchor:
            out.extend(machine_lines(desired))
    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    return "---\n" + text + "---\n"


def current_machine(items: list[tuple]) -> dict:
    values = {}
    for key, value, _ in items:
        if key in MACHINE_KEYS:
            values[key] = [str(v) for v in value] if isinstance(value, list) else str(value)
    return values


def differs(current: dict, desired: dict) -> list[str]:
    changed = []
    for key in MACHINE_KEYS:
        if key == "synced":
            continue
        if current.get(key) != desired[key]:
            changed.append(f"{key}: {current.get(key)!r} → {desired[key]!r}")
    return changed


def new_spec(desired: dict, cfg: dict) -> str:
    head = ["type: task-spec", f"project: {cfg['project_note']}", *machine_lines(desired),
            "status: active", f"executor: {yaml_scalar(cfg['executor_default'])}", "needs: none"]
    body = (
        f"\n# {desired['summary']}\n\n"
        "## Цель\n\n<!-- одна фраза: что изменится в наборе -->\n\n"
        "## Контекст\n\n<!-- ссылки вместо пересказа: условия плана (Confluence), код file:line, эпик, смежные постановки -->\n\n"
        "## Что сделать\n\n<!-- только работа, каждый пункт с глагола -->\n\n"
        "## Критерии приёмки\n\n<!-- нумерованные АС-n, каждый проверяем -->\n\n"
        "## Как проверить\n\n<!-- команды прогона, ожидаемые пропуски и маркеры configure без стенда -->\n\n"
        "## Не входит в задачу\n\n<!-- со ссылкой на смежную постановку или тикет -->\n"
    )
    return "---\n" + "\n".join(head) + "\n---\n" + body


# ----------------------------------------------------------------------------- индекс очереди

def has_body(body: str) -> bool:
    return re.search(r"АС-\d", body) is not None


def compact(conditions: list[str]) -> str:
    if not conditions:
        return "—"
    if len(conditions) <= 4:
        return ", ".join(conditions)
    return f"{conditions[0]}, …, {conditions[-1]} ({len(conditions)})"


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def key_order(key: str):
    match = re.match(r"^([A-Z]+)-(\d+)$", key)
    return (match.group(1), int(match.group(2))) if match else (key, 0)


def render_table(rows: list[dict], folder: str) -> str:
    open_tasks = sorted((r for r in rows if r["kind"] == "task" and not r["done"]), key=lambda r: key_order(r["key"]))
    done_tasks = sorted((r for r in rows if r["kind"] == "task" and r["done"]), key=lambda r: key_order(r["key"]))
    conds = sorted((r for r in rows if r["kind"] == "cond"), key=lambda r: condition_sort_key(r["key"]))
    lines = [BEGIN,
             f"Задач: {len(open_tasks) + len(done_tasks)} (открытых {len(open_tasks)}, закрытых в Jira {len(done_tasks)}) · "
             f"постановок без задачи Jira: {len(conds)} · с телом: {sum(1 for r in rows if r['body'])}",
             "", TABLE_HEAD]
    for row in open_tasks + done_tasks + conds:
        link = f"[[{folder}/{row['key']}\\|{row['key']}]]"  # внутри таблицы `|` вики-ссылки экранируется
        lines.append(f"| {link} | {cell(row['summary'])} | {cell(row['jira_status'])} | {cell(compact(row['conditions']))} | "
                     f"{'да' if row['body'] else 'нет'} | {cell(row['needs'])} |")
    lines.append(END)
    return "\n".join(lines)


def replace_region(text: str, new_region: str) -> tuple[str, str]:
    start, stop = text.find(BEGIN), text.find(END)
    if start < 0 or stop < 0 or stop < start:
        sys.exit(f"в README нет маркеров {BEGIN} … {END}: добавьте их вокруг таблицы очереди")
    return text[start: stop + len(END)], new_region


# ----------------------------------------------------------------------------- основной проход

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry", action="store_true", help="показать дельту, ничего не писать")
    parser.add_argument("--verify", action="store_true", help="только сверить vault с ожидаемым состоянием")
    parser.add_argument("--config", default=str(SKILL_ROOT / "config" / "queue.json"))
    parser.add_argument("--registry", help="путь к реестру условий (по умолчанию из конфига)")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    today = date.today().isoformat()
    registry_path = Path(args.registry or cfg["registry"]).expanduser()
    if not registry_path.is_file():
        sys.exit(f"реестр условий не найден: {registry_path}")
    registry = load_registry(registry_path, cfg["plans"])
    conditions_map, no_conditions = load_conditions_map(cfg["_root"] / cfg["conditions_map"], registry, cfg["plans"])
    folder = cfg["vault_tasks_folder"]
    workdir = Path(tempfile.mkdtemp(prefix="jira-vault-sync-"))

    obsidian_ready()
    files = {f["path"]: f["content"] for f in read_folder(folder, workdir)}
    readme = files.pop(cfg["readme_path"], None)
    if readme is None:
        sys.exit(f"нет {cfg['readme_path']}")

    # существующие постановки: IOT-<n>.md и cond-<план>-<id>.md; прочие заметки папки не трогаются
    specs, cond_specs, skipped = {}, {}, []
    for path, content in files.items():
        name = Path(path).stem
        block, lines, body = split_frontmatter(content)
        if lines is None:
            skipped.append(f"{name}: без frontmatter")
            continue
        items = parse_items(lines)
        fm = {k: v for k, v, _ in items if k}
        if KEY_RE.match(name):
            if str(fm.get("jira", "")) != name:
                skipped.append(f"{name}: jira в шапке = {fm.get('jira')!r}, не совпадает с имени файла")
                continue
            specs[name] = {"path": path, "block": block, "lines": lines, "items": items, "body": body, "fm": fm}
        elif name.startswith("cond-"):
            cond_specs[name] = {"path": path, "fm": fm, "body": body}
        elif fm.get("type") == "task-spec":
            skipped.append(f"{name}: task-spec прежнего формата, в очередь не входит")

    # выборка Jira: открытые по JQL, плюс ключи существующих постановок вне выборки (закрытые, переразмеченные)
    selection = {r["key"]: r for r in jira_selection(cfg)}
    excluded = {k: cfg["exclude"][k] for k in list(selection) if k in cfg["exclude"] and k not in specs}
    for key in excluded:
        selection.pop(key)
    missing = []
    for key in sorted(set(specs) - set(selection), key=key_order):
        record = jira_issue(cfg, key)
        if record is None:
            missing.append(key)
        else:
            selection[key] = record
    orphan_map = sorted(set(conditions_map) - set(selection) - set(specs), key=key_order)

    # желаемая шапка и дельта
    creates, updates, same, closed, rows = [], [], [], [], []
    for key in sorted(selection, key=key_order):
        record = selection[key]
        desired = {
            "jira": key, "summary": record["summary"], "jira_status": record["status"], "epic": record["epic"],
            "labels": record["labels"], "component": record["component"],
            "conditions": conditions_map.get(key, []), "synced": today,
        }
        if record["done"]:
            closed.append(key)
        spec = specs.get(key)
        if spec is None:
            creates.append((key, desired))
            needs, body = "none", False
        else:
            current = current_machine(spec["items"])
            changed = differs(current, desired)
            if changed:
                updates.append((key, desired, changed, spec))
            else:
                same.append(key)
            needs = str(spec["fm"].get("needs", "none")) or "none"
            body = has_body(spec["body"])
        rows.append({"kind": "task", "key": key, "summary": record["summary"], "jira_status": record["status"],
                     "done": record["done"], "conditions": desired["conditions"], "body": body, "needs": needs})
    for name, spec in cond_specs.items():
        conds = spec["fm"].get("conditions")
        conds = [str(c) for c in conds] if isinstance(conds, list) else [name[len("cond-"):]]
        rows.append({"kind": "cond", "key": name, "summary": str(spec["fm"].get("summary") or name), "jira_status": "—",
                     "done": False, "conditions": conds, "body": has_body(spec["body"]),
                     "needs": str(spec["fm"].get("needs", "none")) or "none"})

    new_region = render_table(rows, folder)
    old_region, _ = replace_region(readme, new_region)
    readme_changed = old_region != new_region

    # отчёт
    print(f"JQL: {build_jql(cfg)}")
    print(f"выборка Jira: {len(selection)} задач; исключено по конфигу: {len(excluded)}"
          + (" — " + ", ".join(f"{k} ({v})" for k, v in excluded.items()) if excluded else ""))
    print(f"постановок в vault: задач {len(specs)}, без задачи Jira (cond-*) {len(cond_specs)}"
          + (f"; пропущено: {'; '.join(skipped)}" if skipped else ""))
    if missing:
        print(f"ключи постановок, которых нет в Jira: {', '.join(missing)} — файлы не тронуты")
    if orphan_map:
        print(f"в соответствии условий есть, а в выборке нет: {', '.join(orphan_map)}")
    deliberate = [k for k in sorted(selection, key=key_order) if k in no_conditions]
    unmapped = [k for k in sorted(selection, key=key_order) if not conditions_map.get(k) and k not in no_conditions]
    print(f"без условий: сознательно {len(deliberate)}, не сопоставлено {len(unmapped)}"
          + (" — " + ", ".join(unmapped) if unmapped else ""))
    print(f"создать: {len(creates)}")
    for key, desired in creates:
        print(f"  + {key} «{desired['summary']}» [{desired['jira_status']}] условий {len(desired['conditions'])}")
    print(f"обновить: {len(updates)}")
    for key, _, changed, _ in updates:
        print(f"  ~ {key}: " + "; ".join(changed))
    print(f"без изменений: {len(same)}")
    print(f"закрыто в Jira (постановка сохранена, status заметки не трогается): {len(closed)}"
          + (" — " + ", ".join(closed) if closed else ""))
    print(f"README: {'таблица изменится' if readme_changed else 'без изменений'} (строк {len(rows)})")

    if args.verify:
        failures = len(creates) + len(updates) + (1 if readme_changed else 0)
        print(f"verify: ok={len(same) + (0 if readme_changed else 1)} fail={failures}")
        return 1 if failures else 0
    if args.dry:
        print("--dry: ничего не записано")
        return 0
    if not creates and not updates and not readme_changed:
        print("изменений нет, запись не требуется")
        return 0

    # запись
    plan = {"creates": [], "updates": []}
    for key, desired in creates:
        plan["creates"].append({"path": f"{folder}/{key}.md", "content": new_spec(desired, cfg)})
    for key, desired, _, spec in updates:
        plan["updates"].append({"path": spec["path"], "old": spec["block"], "new": rebuild_frontmatter(spec["lines"], desired)})
    if readme_changed:
        plan["updates"].append({"path": cfg["readme_path"], "old": old_region, "new": new_region})
        match = re.search(r"^updated: .*$", readme, flags=re.M)
        if match and match.group(0) != f"updated: {today}":
            plan["updates"].append({"path": cfg["readme_path"], "old": match.group(0), "new": f"updated: {today}"})
    for line in apply_plan(plan, workdir):
        print("  " + line)

    # проверка чтением
    after = {f["path"]: f["content"] for f in read_folder(folder, workdir)}
    ok = fail = 0
    expected = {f"{folder}/{key}.md": desired for key, desired in creates}
    expected.update({spec["path"]: desired for _, desired, _, spec in updates})
    for path, desired in expected.items():
        _, lines, body = split_frontmatter(after.get(path, ""))
        got = current_machine(parse_items(lines)) if lines else {}
        problems = differs(got, desired)
        if got.get("synced") != today:
            problems.append(f"synced: {got.get('synced')!r} → {today!r}")
        if path in {s["path"] for s in specs.values()} and body != specs[Path(path).stem]["body"]:
            problems.append("тело изменилось")
        if problems:
            fail += 1
            print(f"  FAIL {path}: " + "; ".join(problems))
        else:
            ok += 1
    if readme_changed:
        region, _ = replace_region(after.get(cfg["readme_path"], BEGIN + END), new_region)
        if region == new_region:
            ok += 1
        else:
            fail += 1
            print("  FAIL README: таблица не совпала с ожидаемой")
    print(f"ok={ok} fail={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
