"""Перелинковка после массового переименования: ri:page ri:content-title="СТАРЫЙ" -> "НОВЫЙ".

    python3 relink.py <registry.json.bak-…> [--apply]

Карта old->new: бэкап реестра (старые заголовки) против текущего registry.json (новые) по pageId,
плюс EXTRA — разовые соответствия для страниц вне реестра (после прогона очищать). Проверяются
пространства SPACES: у каждой страницы все ri:page; ссылка, чей заголовок не существует в целевом
пространстве, заменяется по карте, остальное попадает в «НЕ РАЗРЕШЕНО». Без --apply только отчёт.
Заменяет второй прогон upload.py после переименований: один PUT на страницу с битой ссылкой вместо
перевыгрузки всех проектов (2026-09-04: 53 страницы, 164 ссылки, ноль перевыгрузок).
"""
import json, os, re, sys, urllib.request, urllib.parse, html
HERE = os.path.dirname(os.path.abspath(__file__))
PAT = open(os.path.expanduser("~/confluence_pat"), encoding="utf-8").read().strip()
C = "https://confluence.example.com"
REG = os.path.join(HERE, "registry.json")
BAK = next(a for a in sys.argv[1:] if not a.startswith("--"))  # путь к бэкапу реестра
SPACES = sorted({p["space"] for p in json.load(open(REG, encoding="utf-8"))["projects"].values()
                 if p.get("space")})   # пространства берутся из реестра
EXTRA = {}  # {"старый заголовок": "новый"} для страниц вне реестра; после прогона очистить
APPLY = "--apply" in sys.argv

def api(method, path, payload=None):
    req = urllib.request.Request(C + path, method=method, headers={"Authorization": "Bearer " + PAT, "Content-Type": "application/json"},
                                 data=json.dumps(payload).encode() if payload is not None else None)
    with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)

def titles_by_id(reg):
    out = {}
    for p in reg["projects"].values():
        for m in p.get("map", []):
            if m.get("pageId") and m.get("title"): out[str(m["pageId"])] = m["title"]
    return out
old, new = titles_by_id(json.load(open(BAK))), titles_by_id(json.load(open(REG)))
MAP = {old[i]: new[i] for i in old if i in new and old[i] != new[i]}
MAP.update(EXTRA)
print(f"карта переименований: {len(MAP)}")

live = {}   # space -> set(titles)
pages = []  # (space, page)
for sp in SPACES:
    start = 0; live[sp] = set()
    while True:
        d = api("GET", f"/rest/api/content?spaceKey={sp}&type=page&limit=100&start={start}&expand=version")
        for p in d["results"]:
            live[sp].add(p["title"]); pages.append((sp, p))
        if "next" not in d.get("_links", {}): break
        start += 100
print("страниц:", {sp: len(live[sp]) for sp in SPACES})

LINK = re.compile(r'<ri:page\b([^>]*?)ri:content-title="([^"]*)"([^>]*)/?>')
changed, unresolved = [], []
for sp, p in pages:
    body = api("GET", f"/rest/api/content/{p['id']}?expand=body.storage,version")
    st = body["body"]["storage"]["value"]
    def fix(m):
        pre, t, post = m.group(1), html.unescape(m.group(2)), m.group(3)
        sk = re.search(r'ri:space-key="([^"]*)"', pre + post)
        target_space = sk.group(1) if sk else sp
        if t in live.get(target_space, set()): return m.group(0)
        if t in MAP and MAP[t] in live.get(target_space, set()):
            # CHANGED: у самозакрывающегося тега group(3) захватывает « /» — срезаем, иначе выйдет «//>»
            tail = post.rstrip().rstrip("/").rstrip()
            close = " />" if m.group(0).rstrip().endswith("/>") else ">"
            return f'<ri:page{pre}ri:content-title="{html.escape(MAP[t], quote=True)}"{tail}{close}'
        unresolved.append((sp, p["id"], p["title"], target_space, t)); return m.group(0)
    new_st = LINK.sub(fix, st)
    if new_st != st:
        n = sum(1 for a, b in zip(LINK.findall(st), LINK.findall(new_st)) if a != b)
        changed.append((sp, p["id"], p["title"], n))
        if APPLY:
            try:
                api("PUT", f"/rest/api/content/{p['id']}", {"id": p["id"], "type": "page", "title": p["title"], "space": {"key": sp},
                     "version": {"number": body["version"]["number"] + 1, "minorEdit": True},
                     "body": {"storage": {"value": new_st, "representation": "storage"}}})
            except urllib.error.HTTPError as e:
                print("  PUT FAILED", sp, p["id"], p["title"], e.code, e.read().decode(errors="replace")[:400])
print(("ПРИМЕНЕНО" if APPLY else "К ПРАВКЕ") + f": страниц {len(changed)}, ссылок {sum(c[3] for c in changed)}")
for c in changed: print("  ", *c)
print(f"НЕ РАЗРЕШЕНО: {len(unresolved)}")
for u in sorted(set(unresolved)): print("  ", *u)
