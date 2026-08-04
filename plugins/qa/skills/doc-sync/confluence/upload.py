#!/usr/bin/env python3
"""Выгрузка документации из Obsidian-vault в Confluence DC.

Идемпотентность: страница ищется по паре «пространство + заголовок». Найдена —
обновляется с инкрементом версии, не найдена — создаётся. Повторный прогон
не плодит копии.

Заголовки страниц в Confluence уникальны В ПРЕДЕЛАХ ПРОСТРАНСТВА, независимо
от вложенности, поэтому к заголовку из H1 добавляется префикс проекта:
в vault имена файлов повторяются (`architecture_context.md`, `product_overview.md`
лежат почти в каждом проекте). При совпадении заголовков внутри проекта к нему
добавляется имя файла.

Дерево vault переносится в дерево страниц: на каждый подкаталог создаётся
страница-раздел, её дети — файлы этого подкаталога.

Использование:
    upload.py <space> <prefix> <vaultRoot> [--parent <id>] [--dry]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://confluence.example.com"
VAULT = os.path.expanduser("~/Documents/Obsidian Vault")
HERE = os.path.dirname(os.path.abspath(__file__))
MD2WIKI = os.path.join(HERE, "md2wiki.py")
REGISTRY = os.path.join(HERE, "registry.json")
TOKEN = open(os.path.expanduser("~/confluence_pat"), encoding="utf-8").read().strip()

FOOTER = ("\n----\n{{info}}\nИсточник: {{{{{path}}}}} в Obsidian-vault. "
          "Страница выгружена автоматически, правки вносить в источник.\n{{info}}\n")

BROKEN = []  # (файл, номер блока, ошибка) — невалидный mermaid в исходниках

SECTION_BODY = ("{{info}}\nРаздел соответствует каталогу {{{{{path}}}}} "
                "в Obsidian-vault. Содержимое — в дочерних страницах.\n{{info}}\n")

TOC = "{toc:maxLevel=2|minLevel=2}"
TOC_MIN_SECTIONS = 6


def api(method, path, payload=None):
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {body[:300]}") from None


def md2wiki(path, title_only=False):
    cmd = [sys.executable, MD2WIKI] + (["--title"] if title_only else []) + [path]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def load_linkmap():
    """Карта «путь в vault» -> «заголовок страницы в Confluence» из registry.

    md2wiki переносит цель wikilink как есть, а целью в vault выступает путь
    (`Company/Projects/uspd-ui/...`). Заголовки же в Confluence другие: к H1
    добавлен префикс проекта. Без подстановки перекрёстные ссылки ведут на
    несуществующие страницы. Карта строится по всем проектам сразу, поэтому
    межпроектные ссылки тоже разрешаются.
    """
    if not os.path.exists(REGISTRY):
        return {}
    reg = json.load(open(REGISTRY, encoding="utf-8"))
    out = {}
    for proj in reg.get("projects", {}).values():
        if not isinstance(proj, dict):
            continue
        vroot = proj.get("vaultRoot")
        for m in proj.get("map", []):
            rel, title = m.get("obsidian"), m.get("title")
            if not (vroot and rel and title):
                continue
            # заголовок с двоеточием («Data Flow: …») в wiki-разметке читается
            # как «пространство:страница»; префикс пространства снимает разбор
            if ":" in title and proj.get("space"):
                title = f"{proj['space']}:{title}"
            full = f"{vroot}/{rel}".rstrip("/")
            for key in {full, full[:-3] if full.endswith(".md") else full}:
                out[key] = title
    return out


LINKMAP = load_linkmap()


def resolve_links(text):
    """Заменяет цели ссылок на заголовки страниц. Неизвестные цели не трогает."""
    def title_of(target):
        return LINKMAP.get(target, target)

    def one(m):
        alias, target = m.group(1), m.group(2)
        return "[" + alias + "|" + title_of(target) + "]"

    text = re.sub(r"\[([^\]\n|]*)\|([^\]\n|]+)\]", one, text)
    # форма [[Путь]] без подписи: md2wiki отдаёт её как [Путь]
    return re.sub(r"\[([^\]\n|]+)\]",
                  lambda m: "[" + title_of(m.group(1)) + "]", text)


def add_toc(body):
    """Ставит оглавление перед первым разделом длинной страницы.

    Макрос добавляется при синхронизации, а не в исходник: в vault оглавление
    рисует сама Obsidian, засорять markdown разметкой Confluence нечем.
    Третий уровень не берём — там отдельные поля и сообщения, будет шум.
    """
    lines = body.split("\n")
    heads = [n for n, ln in enumerate(lines) if ln.startswith("h2. ")]
    if len(heads) < TOC_MIN_SECTIONS:
        return body
    lines[heads[0]:heads[0]] = [TOC, ""]
    return "\n".join(lines)


def find_page(space, title):
    q = urllib.parse.urlencode({"spaceKey": space, "title": title,
                                "expand": "version"})
    res = api("GET", "/rest/api/content?" + q)
    return res["results"][0] if res.get("results") else None


def homepage_id(space):
    return api("GET", f"/rest/api/space/{space}?expand=homepage")["homepage"]["id"]


def upsert(space, title, body, parent_id, dry=False, known_id=None):
    existing = find_page(space, title)
    # CHANGED: заголовок изменился в источнике — страница ищется по id из registry.
    # Без этого PUT не находит её по новому заголовку и создаёт дубль рядом со старой.
    if not existing and known_id:
        try:
            existing = api("GET", f"/rest/api/content/{known_id}?expand=version")
        except RuntimeError:
            existing = None
    if dry:
        act = "переименовать" if existing and existing["title"] != title else (
            "обновить" if existing else "создать")
        return act, (existing or {}).get("id", "-")
    payload = {"type": "page", "title": title, "space": {"key": space},
               "body": {"storage": {"value": body, "representation": "wiki"}}}
    if existing:
        payload["id"] = existing["id"]
        payload["version"] = {"number": existing["version"]["number"] + 1}
        # CHANGED: ancestors и при обновлении — иначе страница остаётся под прежним
        # родителем и дерево vault не переносится в дерево страниц
        if parent_id:
            payload["ancestors"] = [{"id": str(parent_id)}]
        return "обновлена", api("PUT", "/rest/api/content/" + existing["id"],
                                payload)["id"]
    payload["ancestors"] = [{"id": str(parent_id)}]
    return "создана", api("POST", "/rest/api/content", payload)["id"]


def attach_diagrams(md_path, page_id):
    """Рендерит mermaid-блоки документа в SVG и кладёт их вложениями страницы.

    mmdc в пакетном режиме поднимает Chromium один раз на документ и выдаёт
    out-1.svg, out-2.svg... в порядке появления блоков — та же нумерация,
    которую ставит md2wiki.
    """
    src = open(md_path, encoding="utf-8").read()
    blocks = re.findall(r"```mermaid\n(.*?)```", src, flags=re.S)
    if not blocks:
        return 0
    tmp = tempfile.mkdtemp(prefix="mmd-")

    # Поблочно, а не пакетом: в пакетном режиме одна невалидная диаграмма
    # роняет обработку всего документа и остальные тоже не рисуются.
    rendered = {}
    for i, code in enumerate(blocks, start=1):
        mmd = os.path.join(tmp, f"d{i}.mmd")
        out = os.path.join(tmp, f"d{i}.svg")
        open(mmd, "w", encoding="utf-8").write(code)
        r = subprocess.run(["npx", "-y", "@mermaid-js/mermaid-cli",
                            "-i", mmd, "-o", out],
                           cwd=tmp, capture_output=True, text=True)
        if os.path.exists(out):
            rendered[i] = out
        else:
            err = (r.stderr or r.stdout).strip().splitlines()
            msg = next((l for l in err if "error" in l.lower()), err[0] if err else "?")
            print(f"           ! диаграмма {i} не отрисована: {msg[:120]}")
            BROKEN.append((md_path, i, msg[:200]))
    if not rendered:
        shutil.rmtree(tmp, ignore_errors=True)
        return 0

    existing = {a["title"]: a["id"] for a in api(
        "GET", f"/rest/api/content/{page_id}/child/attachment?limit=100"
    ).get("results", [])}

    n = 0
    for i, path in sorted(rendered.items()):
        name = f"diagram-{i}.svg"
        # multipart-загрузка через curl: в stdlib это громоздко
        if name in existing:
            url = (f"{BASE}/rest/api/content/{page_id}/child/attachment/"
                   f"{existing[name]}/data")
        else:
            url = f"{BASE}/rest/api/content/{page_id}/child/attachment"
        cp = subprocess.run([
            "curl", "-sS", "-m", "60", "-X", "POST", url,
            "-H", "Authorization: Bearer " + TOKEN,
            "-H", "X-Atlassian-Token: no-check",
            "-F", f"file=@{path};filename={name};type=image/svg+xml",
            "-F", "comment=Отрисовано из mermaid-исходника документа",
            "-o", "/dev/null", "-w", "%{http_code}"],
            capture_output=True, text=True)
        if cp.stdout.strip() in ("200", "201"):
            n += 1
        else:
            print(f"           ! вложение {name}: HTTP {cp.stdout.strip()}")
    shutil.rmtree(tmp, ignore_errors=True)
    return n


def make_title(prefix, base, used, fname):
    # backticks из H1 в заголовке страницы не нужны: разметки там нет,
    # они остались бы литеральными символами
    base = base.replace("`", "").strip()
    t = base if base.lower().startswith(prefix.lower()) else f"{prefix} — {base}"
    if t in used:                      # коллизия внутри проекта
        t = f"{t} ({os.path.splitext(fname)[0]})"
    used.add(t)
    return t


def walk(space, prefix, root, rel, parent_id, entries, used, dry, indent=1):
    """Обрабатывает каталог rel (относительно root) и его подкаталоги."""
    abs_dir = os.path.join(VAULT, root, rel) if rel else os.path.join(VAULT, root)
    names = sorted(os.listdir(abs_dir))
    files = [n for n in names if n.endswith(".md")]
    subdirs = [n for n in names if os.path.isdir(os.path.join(abs_dir, n))
               and not n.startswith(".")]
    pad = "  " * indent

    # README этого уровня становится страницей-родителем для остальных
    if "README.md" in files and rel:
        p = os.path.join(abs_dir, "README.md")
        base = md2wiki(p, True).strip() or rel
        relpath = os.path.join(rel, "README.md")
        title = make_title(prefix, base, used, "README")
        body = add_toc(resolve_links(md2wiki(p))) + FOOTER.format(
            path=f"{root}/{relpath}")
        act, pid = upsert(space, title, body, parent_id, dry,
                          entries.get(relpath, {}).get("pageId"))
        print(f"{pad}{act:10} [раздел] {title}  id={pid}")
        if not dry:
            d = attach_diagrams(p, pid)
            if d:
                print(f"{pad}           диаграмм вложено: {d}")
        entries[relpath] = {"obsidian": relpath, "pageId": pid, "title": title,
                            "role": "section-index"}
        parent_id = pid
        files.remove("README.md")

    for f in files:
        p = os.path.join(abs_dir, f)
        relpath = os.path.join(rel, f) if rel else f
        base = md2wiki(p, True).strip() or os.path.splitext(f)[0]
        title = make_title(prefix, base, used, f)
        body = add_toc(resolve_links(md2wiki(p))) + FOOTER.format(
            path=f"{root}/{relpath}")
        act, pid = upsert(space, title, body, parent_id, dry,
                          entries.get(relpath, {}).get("pageId"))
        print(f"{pad}{act:10} {title}  id={pid}")
        if not dry:
            d = attach_diagrams(p, pid)
            if d:
                print(f"{pad}           диаграмм вложено: {d}")
        entries[relpath] = {"obsidian": relpath, "pageId": pid, "title": title}

    for d in subdirs:
        sub_rel = os.path.join(rel, d) if rel else d
        has_readme = os.path.exists(os.path.join(abs_dir, d, "README.md"))
        if has_readme:
            sub_parent = parent_id           # README внутри станет разделом сам
        else:
            title = make_title(prefix, d, used, d)
            body = SECTION_BODY.format(path=f"{root}/{sub_rel}")
            act, pid = upsert(space, title, body, parent_id, dry,
                              entries.get(sub_rel + "/", {}).get("pageId"))
            print(f"{pad}{act:10} [раздел] {title}  id={pid}")
            entries[sub_rel + "/"] = {"obsidian": sub_rel + "/", "pageId": pid,
                                      "title": title, "role": "section-stub"}
            sub_parent = pid
        walk(space, prefix, root, sub_rel, sub_parent, entries, used, dry, indent + 1)


def main():
    args = list(sys.argv[1:])
    dry = "--dry" in args
    if dry:
        args.remove("--dry")
    parent = None
    if "--parent" in args:
        k = args.index("--parent")
        parent, args[k:k + 2] = args[k + 1], []
    space, prefix, root = args[0], args[1], args[2]

    abs_root = os.path.join(VAULT, root)
    reg = (json.load(open(REGISTRY, encoding="utf-8")) if os.path.exists(REGISTRY)
           else {"_comment": "Obsidian path -> Confluence pageId. Ведётся upload.py",
                 "confluence_url": BASE, "projects": {}})
    entry = reg["projects"].setdefault(prefix, {})
    entry["space"], entry["vaultRoot"] = space, root
    entries = {m["obsidian"]: m for m in entry.get("map", [])}
    used = set()

    # корневой README проекта — родитель всего дерева
    if parent is None:
        if os.path.exists(os.path.join(abs_root, "README.md")):
            p = os.path.join(abs_root, "README.md")
            title = make_title(prefix, md2wiki(p, True).strip() or prefix, used, "README")
            body = add_toc(resolve_links(md2wiki(p))) + FOOTER.format(
                path=f"{root}/README.md")
            act, parent = upsert(space, title, body, homepage_id(space), dry,
                                 entries.get("README.md", {}).get("pageId"))
            print(f"  {act:10} [родитель] {title}  id={parent}")
            if not dry:
                d = attach_diagrams(p, parent)
                if d:
                    print(f"             диаграмм вложено: {d}")
            entries["README.md"] = {"obsidian": "README.md", "pageId": parent,
                                    "title": title, "role": "parent-index"}
        else:
            parent = homepage_id(space)

    names = sorted(os.listdir(abs_root))
    files = [n for n in names if n.endswith(".md") and n != "README.md"]
    subdirs = [n for n in names if os.path.isdir(os.path.join(abs_root, n))
               and not n.startswith(".")]
    for f in files:
        p = os.path.join(abs_root, f)
        base = md2wiki(p, True).strip() or os.path.splitext(f)[0]
        title = make_title(prefix, base, used, f)
        body = add_toc(resolve_links(md2wiki(p))) + FOOTER.format(path=f"{root}/{f}")
        act, pid = upsert(space, title, body, parent, dry,
                          entries.get(f, {}).get("pageId"))
        print(f"  {act:10} {title}  id={pid}")
        if not dry:
            d = attach_diagrams(p, pid)
            if d:
                print(f"             диаграмм вложено: {d}")
        entries[f] = {"obsidian": f, "pageId": pid, "title": title}
    for d in subdirs:
        if os.path.exists(os.path.join(abs_root, d, "README.md")):
            sub_parent = parent
        else:
            title = make_title(prefix, d, used, d)
            act, pid = upsert(space, title, SECTION_BODY.format(path=f"{root}/{d}"),
                              parent, dry, entries.get(d + "/", {}).get("pageId"))
            print(f"  {act:10} [раздел] {title}  id={pid}")
            entries[d + "/"] = {"obsidian": d + "/", "pageId": pid, "title": title,
                                "role": "section-stub"}
            sub_parent = pid
        walk(space, prefix, root, d, sub_parent, entries, used, dry, 2)

    if not dry:
        entry["map"] = [entries[k] for k in sorted(entries)]
        json.dump(reg, open(REGISTRY, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"  registry: {len(entry['map'])} записей")


if __name__ == "__main__":
    main()
