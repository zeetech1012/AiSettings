#!/usr/bin/env python3
"""Публикует README.md проекта на существующую страницу-индекс раздела.

Зачем отдельный скрипт: `upload.py` с флагом `--parent` файл `README.md` не публикует вовсе —
он исключён из общего списка файлов и одновременно не используется как родитель (тот задан
флагом). А индекс раздела нужен: без него читатель не знает, из чего состоит раздел.

Ссылки вида [[Company/Projects/<проект>/<файл>|подпись]] разрешаются в заголовки страниц
по реестру — иначе в Confluence они ведут в никуда.

    publish_index.py <префикс-реестра> <vault-путь-README> <pageId-индекса>
"""
import json
import os
import subprocess
import sys
import urllib.parse

BASE = "https://confluence.example.com"
TOKEN = open(os.path.expanduser("~/confluence_pat"), encoding="utf-8").read().strip()
VAULT = os.path.expanduser("~/Documents/Obsidian Vault")
HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "registry.json")
FOOTER = ("\n----\n{{info}}\nИсточник: {{{{{path}}}}} в Obsidian-vault. "
          "Страница выгружена автоматически, правки вносить в источник.\n{{info}}\n")


def api(method, path, payload=None):
    args = ["curl", "-sS", "-m", "60", "-X", method, BASE + path,
            "-H", "Authorization: Bearer " + TOKEN]
    if payload is not None:
        args += ["-H", "Content-Type: application/json",
                 "-d", json.dumps(payload, ensure_ascii=False)]
    return json.loads(subprocess.run(args, capture_output=True, text=True).stdout or "{}")


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    prefix, rel, page_id = sys.argv[1], sys.argv[2], sys.argv[3]
    abs_path = os.path.join(VAULT, rel)
    if not os.path.exists(abs_path):
        sys.exit(f"нет файла: {abs_path}")

    wiki = subprocess.run([sys.executable, os.path.join(HERE, "md2wiki.py"), abs_path],
                          capture_output=True, text=True, check=True).stdout
    reg = json.load(open(REGISTRY, encoding="utf-8"))
    entry = reg["projects"][prefix]
    space = None  # определяется ниже по странице-индексу

    # Карта «vault-путь -> (заголовок, пространство)» по ВСЕМ проектам, а не только текущему:
    # индекс ссылается и на соседние сервисы, а неразрешённый путь Confluence превращает
    # в ссылку на несуществующую страницу (проверено: auth → auth_http дал createlink).
    targets = []
    for pname, pentry in reg.get("projects", {}).items():
        if not isinstance(pentry, dict):
            continue
        proot = (pentry.get("vaultRoot") or "").rstrip("/")
        for m in pentry.get("map", []):
            obs = m.get("obsidian")
            if not obs:
                continue
            full = f"{proot}/{obs}".rstrip("/")
            targets.append((full, m["title"], pentry.get("space")))
    cur_space = api("GET", f"/rest/api/content/{page_id}?expand=space").get("space", {}).get("key")
    # длинные пути первыми: иначе короткий съест префикс более длинного
    for full, title, tspace in sorted(targets, key=lambda x: -len(x[0])):
        # чужое пространство и заголовок с двоеточием требуют явного префикса «SPACE:»,
        # иначе ссылка ищется в пространстве текущей страницы и бьётся
        label = f"{tspace}:{title}" if tspace and (tspace != cur_space or ":" in title) else title
        for form in (full, full[:-3] if full.endswith(".md") else full):
            wiki = wiki.replace(form, label)

    cur = api("GET", f"/rest/api/content/{page_id}?expand=version,space,ancestors")
    if "title" not in cur:
        sys.exit(f"страница {page_id} недоступна: {str(cur)[:200]}")
    payload = {"id": page_id, "type": "page", "title": cur["title"],
               "space": {"key": cur["space"]["key"]},
               "body": {"storage": {"value": wiki + FOOTER.format(path=rel),
                                    "representation": "wiki"}},
               "version": {"number": cur["version"]["number"] + 1}}
    anc = cur.get("ancestors", [])
    if anc:
        payload["ancestors"] = [{"id": anc[-1]["id"]}]
    res = api("PUT", f"/rest/api/content/{page_id}", payload)
    if "id" not in res:
        sys.exit(f"не обновлено: {str(res)[:250]}")
    print(f"индекс обновлён: {res['id']} «{res['title']}» в {cur['space']['key']}")

    view = api("GET", f"/rest/api/content/{page_id}?expand=body.view")["body"]["view"]["value"]
    bad = [s for s in ("unknown macro", "unmigrated-wiki-markup") if s in view.lower()]
    print("рендер:", bad or "чисто")

    entry["map"] = [m for m in entry.get("map", []) if m.get("obsidian") != "README.md"]
    entry["map"].append({"obsidian": "README.md", "pageId": page_id,
                         "title": cur["title"], "role": "section-index"})
    json.dump(reg, open(REGISTRY, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"реестр {prefix}: {len(entry['map'])} записей")


if __name__ == "__main__":
    main()
