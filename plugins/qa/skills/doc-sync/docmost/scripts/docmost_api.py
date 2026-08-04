#!/usr/bin/env python3
"""docmost_api.py — детерминированный клиент internal REST API Docmost.

Учётные данные ТОЛЬКО из ENV (задать в ~/.claude/settings.local.json → env):
  DOCMOST_URL      — базовый URL (напр. https://docmost.example.com)
  DOCMOST_EMAIL    — email учётки
  DOCMOST_PASSWORD — пароль
  DOCMOST_INSECURE — "1" = не проверять TLS (self-signed)

Команды (результат — JSON в stdout):
  spaces                                  — список пространств
  search <query> [spaceId]                — полнотекстовый поиск
  info <pageId>                           — метаданные страницы
  export <pageId>                         — markdown-контент страницы
  import <file.md> <spaceId> [parentPageId] — создать страницу из markdown
  create <spaceId> <title> [parentPageId] — пустая страница
  update <pageId> <file.md>               — заменить контент markdown'ом (pageId стабилен)
  update-title <pageId> <title>           — переименовать
  delete <pageId>                         — удалить страницу (в корзину пространства)

Update контента = re-import + delete старой + swap pageId в registry (см. SKILL.md).
"""
import json
import os
import ssl
import sys
import urllib.request

BASE = os.environ.get("DOCMOST_URL", "").rstrip("/")
EMAIL = os.environ.get("DOCMOST_EMAIL", "")
PASSWORD = os.environ.get("DOCMOST_PASSWORD", "")
CTX = ssl._create_unverified_context() if os.environ.get("DOCMOST_INSECURE") == "1" else None

_cookie = None


def die(msg):
    print(json.dumps({"error": msg}, ensure_ascii=False))
    sys.exit(1)


def _request(path, data=None, headers=None, raw_body=None):
    req = urllib.request.Request(BASE + path, method="POST")
    if _cookie:
        req.add_header("Cookie", _cookie)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if raw_body is not None:
        body = raw_body
    else:
        req.add_header("Content-Type", "application/json")
        body = json.dumps(data or {}).encode()
    try:
        resp = urllib.request.urlopen(req, body, timeout=30, context=CTX)
    except urllib.error.HTTPError as e:
        die(f"HTTP {e.code} {path}: {e.read().decode()[:300]}")
    return resp


def login():
    global _cookie
    if not (BASE and EMAIL and PASSWORD):
        die("нет DOCMOST_URL / DOCMOST_EMAIL / DOCMOST_PASSWORD в ENV")
    resp = _request("/api/auth/login", {"email": EMAIL, "password": PASSWORD})
    for h, v in resp.getheaders():
        if h.lower() == "set-cookie" and "authToken=" in v:
            _cookie = v.split(";")[0]
    if not _cookie:
        die("логин прошёл, но authToken-cookie не получен")


def call(path, data=None):
    return json.loads(_request(path, data).read().decode())


def import_md(path, space_id, parent_id=None):
    boundary = "----docmostsync"
    name = os.path.basename(path)
    with open(path, "rb") as f:
        content = f.read()
    parts = [f"--{boundary}\r\nContent-Disposition: form-data; name=\"spaceId\"\r\n\r\n{space_id}\r\n"]
    if parent_id:
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parentPageId\"\r\n\r\n{parent_id}\r\n")
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: text/markdown\r\n\r\n")
    body = "".join(parts).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    resp = _request("/api/pages/import", headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, raw_body=body)
    return json.loads(resp.read().decode())


def main():
    if len(sys.argv) < 2:
        die("нет команды (см. --help в шапке файла)")
    cmd, args = sys.argv[1], sys.argv[2:]
    login()
    if cmd == "spaces":
        out = call("/api/spaces", {"page": 1, "limit": 100})
    elif cmd == "list":
        # корневые страницы пространства; с pageId — дети этой страницы
        payload = {"spaceId": args[0], "page": 1, "limit": 100}
        if len(args) > 1:
            payload["pageId"] = args[1]
        out = call("/api/pages/sidebar-pages", payload)
    elif cmd == "search":
        payload = {"query": args[0]}
        if len(args) > 1:
            payload["spaceId"] = args[1]
        out = call("/api/search", payload)
    elif cmd == "info":
        out = call("/api/pages/info", {"pageId": args[0]})
    elif cmd == "export":
        # endpoint отдаёт сырой markdown-файл, не JSON
        resp = _request("/api/pages/export", {"pageId": args[0], "format": "markdown"})
        sys.stdout.write(resp.read().decode())
        return
    elif cmd == "import":
        out = import_md(args[0], args[1], args[2] if len(args) > 2 else None)
    elif cmd == "create":
        payload = {"spaceId": args[0], "title": args[1]}
        if len(args) > 2:
            payload["parentPageId"] = args[2]
        out = call("/api/pages/create", payload)
    elif cmd == "update":
        # замена контента страницы markdown'ом — pageId стабилен (не re-import)
        md = open(args[1], encoding="utf-8").read()
        out = call("/api/pages/update", {"pageId": args[0], "operation": "replace", "format": "markdown", "content": md})
    elif cmd == "update-title":
        out = call("/api/pages/update", {"pageId": args[0], "title": args[1]})
    elif cmd == "delete":
        out = call("/api/pages/delete", {"pageId": args[0]})
    else:
        die(f"неизвестная команда: {cmd}")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
