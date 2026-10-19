#!/usr/bin/env python3
"""Релиз прошивки HW в Jira DC + Xray: версия, план, Test Execution по файлу прошивки, исполнители, связи задача ↔ тест.
Свойства: сухой прогон (--dry), защита от повтора (сделанное пропускается по текущему состоянию), сверка чтением → ok=N fail=M.
Только stdlib. Конфиг — JSON (пример: ../release.example.json).
  python3 hw_release.py release.json --dry
  python3 hw_release.py release.json"""
import hashlib, json, os, sys, urllib.error, urllib.parse, urllib.request

B = os.environ.get("JIRA_URL", "https://jira.example.com").rstrip("/")
T = os.environ.get("JIRA_PERSONAL_TOKEN") or open(os.path.expanduser("~/jira_pat")).read().strip()
CF_REV, CF_ENV = "customfield_10317", "customfield_10323"
TYPE_TEST_EXECUTION = "10202"  # 10200 Test · 10201 Test Set · 10202 Test Execution · 10203 Pre-Condition · 10204 Test Plan
DRY = "--dry" in sys.argv


def call(method, path, body=None):
    req = urllib.request.Request(B + path, method=method, data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + T, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw.strip() else None
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} → {e.code}: {e.read().decode()[:400]}")


def write(msg, method, path, body=None):
    print(("DRY " if DRY else "") + msg)
    return None if DRY else call(method, path, body)


def fields(k, f):
    return call("GET", f"/rest/api/2/issue/{k}?fields={f}")["fields"]


def ensure_fix_version(key, vid, vname):
    if vname not in [v["name"] for v in fields(key, "fixVersions")["fixVersions"]]:
        write(f"{key}: fixVersion += {vname}", "PUT", f"/rest/api/2/issue/{key}?notifyUsers=false",
              {"update": {"fixVersions": [{"add": {"id": vid} if vid else {"name": vname}}]}})


def ensure_assignee(key, user):
    if (fields(key, "assignee")["assignee"] or {}).get("name") != user:
        write(f"{key}: исполнитель → {user}", "PUT", f"/rest/api/2/issue/{key}?notifyUsers=false", {"fields": {"assignee": {"name": user}}})


def tested_by(task):
    return {l["inwardIssue"]["key"] for l in fields(task, "issuelinks")["issuelinks"] if l["type"]["name"] == "Tests" and "inwardIssue" in l}


def main():
    c = json.load(open(sys.argv[1], encoding="utf-8"))
    proj, plan, user, tests = c["project"], c["plan"], c["assignee"], c["tests"]
    # 1. версия
    vers = {v["name"]: v for v in call("GET", f"/rest/api/2/project/{proj}/versions")}
    v = vers.get(c["version"]["name"]) or write(f"версия «{c['version']['name']}»", "POST", "/rest/api/2/version",
                                                 {"project": proj, "name": c["version"]["name"], "description": c["version"].get("description", "")}) or {}
    vid, vname = v.get("id"), c["version"]["name"]
    # 2. план
    ensure_fix_version(plan, vid, vname)
    ensure_assignee(plan, user)
    add = [k for k in tests if k not in {t["key"] for t in call("GET", f"/rest/raven/1.0/api/testplan/{plan}/test")}]
    if add:
        write(f"{plan}: тесты += {add}", "POST", f"/rest/raven/1.0/api/testplan/{plan}/test", {"add": add})
    # 3. прогон по файлу прошивки
    e = c["execution"]
    sha = hashlib.sha256(open(os.path.expanduser(e["firmware_file"]), "rb").read()).hexdigest()
    fname = os.path.basename(e["firmware_file"])
    desc = e["description"].replace("{file}", fname).replace("{sha256}", sha)
    jql = f'project = {proj} AND issuetype = "Test Execution" AND fixVersion = "{vname}"' if vid else None
    found = [i["key"] for i in (call("GET", "/rest/api/2/search?" + urllib.parse.urlencode({"jql": jql, "fields": "summary"}))["issues"] if jql else [])
             if fields(i["key"], "summary")["summary"] == e["summary"]]
    if found:
        ex = found[0]; print(f"прогон уже есть: {ex}")
    else:
        r = write(f"Test Execution «{e['summary']}» (SHA-256 {sha[:12]}…)", "POST", "/rest/api/2/issue?notifyUsers=false", {"fields": {
            "project": {"key": proj}, "issuetype": {"id": TYPE_TEST_EXECUTION}, "summary": e["summary"], "description": desc,
            "assignee": {"name": user}, "fixVersions": [{"id": vid}] if vid else [], "components": [{"name": x} for x in e.get("components", [])],
            CF_REV: e["revision"], CF_ENV: e.get("environments", ["lab"])}})
        ex = (r or {}).get("key")
    if ex:
        have = {t["key"] for t in call("GET", f"/rest/raven/1.0/api/testexec/{ex}/test")}
        add = [k for k in tests if k not in have]
        if add:
            write(f"{ex}: тесты += {len(add)}", "POST", f"/rest/raven/1.0/api/testexec/{ex}/test", {"add": add})
        if ex not in {x["key"] for x in call("GET", f"/rest/raven/1.0/api/testplan/{plan}/testexecution")}:
            write(f"{plan}: прогон += {ex}", "POST", f"/rest/raven/1.0/api/testplan/{plan}/testexecution", {"add": [ex]})
        for t in call("GET", f"/rest/raven/1.0/api/testexec/{ex}/test"):
            if call("GET", f"/rest/raven/1.0/api/testrun/{t['id']}").get("assignee") != user:
                write(f"{ex}/{t['key']}: исполнитель прогона → {user}", "PUT", f"/rest/raven/1.0/api/testrun/{t['id']}/assignee?user={user}")
    else:
        print(f"DRY <новый прогон>: тесты += {len(tests)}; {plan}: прогон += новый; исполнитель Test Run → {user}")
    # 4. задачи релиза ↔ тесты (тест «tests» задачу; у задачи «tested by»)
    links = c.get("links", {})
    for task, ts in links.items():
        ensure_fix_version(task, vid, vname)
        for x in [x for x in ts if x not in tested_by(task)]:
            write(f"{x} tests {task}", "POST", "/rest/api/2/issueLink", {"type": {"name": "Tests"}, "inwardIssue": {"key": x}, "outwardIssue": {"key": task}})
    if DRY:
        return
    # 5. сверка чтением
    ch = [("версия", vname in {x["name"] for x in call("GET", f"/rest/api/2/project/{proj}/versions")})]
    for k in (plan, ex):
        f = fields(k, "fixVersions,assignee")
        ch += [(f"{k} релиз", vname in [x["name"] for x in f["fixVersions"]]), (f"{k} исполнитель", (f["assignee"] or {}).get("name") == user)]
    ch.append((f"{plan} тесты", set(tests) <= {t["key"] for t in call("GET", f"/rest/raven/1.0/api/testplan/{plan}/test")}))
    runs = call("GET", f"/rest/raven/1.0/api/testexec/{ex}/test")
    ch.append((f"{ex} тесты", set(tests) <= {t["key"] for t in runs}))
    ch.append((f"{ex} исполнитель Test Run", all(call("GET", f"/rest/raven/1.0/api/testrun/{t['id']}").get("assignee") == user for t in runs)))
    f = fields(ex, f"{CF_REV},{CF_ENV}")
    ch.append((f"{ex} ревизия и окружение", f[CF_REV] == e["revision"] and f[CF_ENV] == e.get("environments", ["lab"])))
    ch.append((f"{plan} ∋ {ex}", ex in {y["key"] for y in call("GET", f"/rest/raven/1.0/api/testplan/{plan}/testexecution")}))
    for task, ts in links.items():
        ch.append((f"{task} tested by", set(ts) <= tested_by(task)))
    for n, g in ch:
        if not g: print("FAIL", n)
    print(f"прогон {ex}; ok={sum(g for _, g in ch)} fail={sum(not g for _, g in ch)}")


main()
