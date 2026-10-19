"""Убирает с уже выгруженных страниц Confluence плашки о локальном источнике (решение владельца 2026-09-24).

Что снимается:
- футер статьи: <hr/> и макрос info «Источник: <путь> в Obsidian-vault. Страница выгружена автоматически…»;
- заглушка раздела: макрос info «Раздел соответствует каталогу … в Obsidian-vault» → макрос {children}.
Остальное тело страницы не меняется. Правка незначительная (minorEdit), уведомления не рассылаются.

    python3 strip_vault_footer.py --dry      # что будет изменено, без записи
    python3 strip_vault_footer.py            # запись и сверка чтением, итог ok=N fail=0
Повторный запуск находит 0 страниц: защита от повтора — сам поиск по тексту плашки.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BASE = "https://confluence.example.com"
TOKEN = open(os.path.expanduser("~/confluence_pat")).read().strip()
MACRO = r'<ac:structured-macro ac:name="info"[^>]*>(?:(?!</ac:structured-macro>).)*?{text}(?:(?!</ac:structured-macro>).)*?</ac:structured-macro>'
FOOTER = re.compile(r"(?:\s*<hr\s*/>)?\s*" + MACRO.format(text="в Obsidian-vault. Страница выгружена автоматически"), re.S)
SECTION = re.compile(MACRO.format(text="Раздел соответствует каталогу"), re.S)
CHILDREN = '<ac:structured-macro ac:name="children" ac:schema-version="2" />'


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def find():
    ids, start = [], 0
    while True:
        q = urllib.parse.urlencode({"cql": 'type=page AND text ~ "Obsidian-vault"', "limit": 100, "start": start})
        d = call("GET", f"/rest/api/content/search?{q}")
        ids += [r["id"] for r in d["results"]]
        if len(d["results"]) < 100:
            return ids
        start += 100


def clean(body):
    new = FOOTER.sub("", body)
    new = SECTION.sub(CHILDREN, new)
    return new


def main():
    dry = "--dry" in sys.argv
    ids = find()
    changed, ok, fail = [], 0, []
    for pid in ids:
        p = call("GET", f"/rest/api/content/{pid}?expand=body.storage,version,space")
        old = p["body"]["storage"]["value"]
        new = clean(old)
        if new == old:
            print(f"  skip {pid} {p['title'][:60]} — плашка не найдена в теле")
            continue
        changed.append(pid)
        if dry:
            print(f"  DRY  {pid} [{p['space']['key']}] {p['title'][:70]}  −{len(old) - len(new)} симв.")
            continue
        call("PUT", f"/rest/api/content/{pid}", {
            "id": pid, "type": "page", "title": p["title"], "space": {"key": p["space"]["key"]},
            "version": {"number": p["version"]["number"] + 1, "minorEdit": True,
                        "message": "Убрана плашка о локальном источнике"},
            "body": {"storage": {"value": new, "representation": "storage"}}})
        back = call("GET", f"/rest/api/content/{pid}?expand=body.storage")["body"]["storage"]["value"]
        if "Obsidian-vault" in back:
            fail.append(pid)
            print(f"  FAIL {pid} {p['title'][:60]}")
        else:
            ok += 1
            print(f"  ok   {pid} [{p['space']['key']}] {p['title'][:70]}")
    print(f"найдено {len(ids)}, к правке {len(changed)}" + ("" if dry else f"; ok={ok} fail={len(fail)}"))


if __name__ == "__main__":
    main()
