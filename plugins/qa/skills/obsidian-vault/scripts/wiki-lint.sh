#!/usr/bin/env bash
# wiki-lint.sh — механизированный lint для two-tree LLM-Wiki (op: lint).
# Read-only: ничего не пишет ни в vault, ни в registry.
#
# Секции:
#   1. Obsidian CLI: unresolved / orphans / deadends (нужно запущенное приложение)
#   2. Структура vault: файлы вне деревьев, папки с ведущими/хвостовыми пробелами
#   3. index.md ↔ файлы проекта (drift: файл есть, в index не упомянут)
#   4. registry.json (huly-doc-sync) ↔ vault: stale-маппинги (файл удалён, запись осталась)
#      + export-доки Company/Projects/** без записи в registry (не синканы)
#   5. Напоминание: Huly-сторона (живость docId) проверяется агентом через MCP huly
#
# Exit code: 1 если найдены ERROR, иначе 0 (WARN/INFO не влияют).

set -u
VAULT="${VAULT:-$HOME/Documents/Obsidian Vault}"
REGISTRY="${REGISTRY:-$HOME/.claude/skills/huly-doc-sync/registry.json}"

echo "=== wiki-lint | vault: $VAULT ==="

# --- 1. Obsidian CLI (битые ссылки / сироты / тупики) -----------------------
if command -v obsidian >/dev/null 2>&1; then
  echo ""
  echo "--- [1] obsidian CLI: unresolved wikilinks ---"
  if ! obsidian unresolved 2>&1 | head -40; then
    echo "WARN: obsidian CLI недоступен (приложение закрыто?) — секция пропущена"
  fi
  echo ""
  echo "--- [1] obsidian CLI: orphans (нет входящих ссылок — нет в index?) ---"
  obsidian orphans 2>/dev/null | head -40 || true
  echo ""
  echo "--- [1] obsidian CLI: deadends (нет исходящих ссылок) — INFO ---"
  obsidian deadends 2>/dev/null | head -20 || true
else
  echo "WARN: obsidian CLI не установлен — секция [1] пропущена"
fi

# --- 2-4. Структура, index-drift, registry ----------------------------------
python3 - "$VAULT" "$REGISTRY" <<'PYEOF'
import json, os, re, sys

vault, registry_path = sys.argv[1], sys.argv[2]
errors, warns = [], []

ALLOWED_ROOT_DIRS = {"Company", "Clippings"}   # Clippings = raw-слой (web clipper)
DAILY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
ALLOWED_ROOT_FILES = {"HANDOFF.md", ".gitignore"}

def rel(p): return os.path.relpath(p, vault)

# --- [2] структура: корень vault и имена папок
print("\n--- [2] структура vault ---")
for name in sorted(os.listdir(vault)):
    if name.startswith(".") or name in ALLOWED_ROOT_FILES:
        continue
    full = os.path.join(vault, name)
    if os.path.isfile(full):
        if not DAILY_RE.match(name):
            warns.append(f"[2] файл в корне vault вне деревьев: {name}")
    elif name not in ALLOWED_ROOT_DIRS:
        warns.append(f"[2] каталог в корне vault вне деревьев (raw без конвенции?): {name}/")

for root, dirs, files in os.walk(vault):
    if "/." in root or root.endswith("/.git"):
        dirs[:] = []
        continue
    for d in list(dirs):
        if d.startswith("."):
            dirs.remove(d)
        elif d != d.strip():
            errors.append(f"[2] имя папки с ведущими/хвостовыми пробелами: '{rel(os.path.join(root,d))}/'")

# --- [3] index.md ↔ файлы проекта (оба дерева)
print("--- [3] index.md ↔ файлы проектов ---")
wiki_root = os.path.join(vault, "Company", "_wiki")
proj_root = os.path.join(vault, "Company", "Projects")

def index_text(project):
    idx = os.path.join(wiki_root, project, "index.md")
    if not os.path.isfile(idx):
        return None
    with open(idx, encoding="utf-8") as f:
        return f.read()

if os.path.isdir(wiki_root):
    for project in sorted(os.listdir(wiki_root)):
        pdir = os.path.join(wiki_root, project)
        if not os.path.isdir(pdir):
            continue
        idx = index_text(project)
        if idx is None:
            errors.append(f"[3] нет index.md: Company/_wiki/{project}/")
            continue
        for root, dirs, files in os.walk(pdir):
            for f in files:
                if not f.endswith(".md") or f in ("index.md", "log.md"):
                    continue
                base = f[:-3]
                if base not in idx:
                    errors.append(f"[3] не упомянут в index Company/_wiki/{project}/index.md: {rel(os.path.join(root,f))}")

if os.path.isdir(proj_root):
    for project in sorted(os.listdir(proj_root)):
        pdir = os.path.join(proj_root, project)
        if not os.path.isdir(pdir):
            continue
        idx = index_text(project)
        if idx is None:
            warns.append(f"[3] export-проект без working-index: Company/Projects/{project}/ (нет Company/_wiki/{project}/index.md)")

# --- [4] registry.json ↔ vault
print("--- [4] registry.json (huly-doc-sync) ↔ vault ---")
try:
    with open(registry_path, encoding="utf-8") as f:
        reg = json.load(f)
except Exception as e:
    errors.append(f"[4] registry.json не читается: {e}")
    reg = {"projects": {}}

registered = set()
for pname, proj in reg.get("projects", {}).items():
    vroot = proj.get("vaultRoot", "")
    for entry in proj.get("documents", {}).get("map", []):
        path = os.path.normpath(os.path.join(vault, vroot, entry["obsidian"]))
        registered.add(path)
        if not os.path.isfile(path):
            errors.append(f"[4] stale-маппинг в registry ({pname}): файла нет — {entry['obsidian']} (docId {entry['docId']})")

if os.path.isdir(proj_root):
    for root, dirs, files in os.walk(proj_root):
        for f in files:
            if f.endswith(".md") and os.path.normpath(os.path.join(root, f)) not in registered:
                warns.append(f"[4] INFO: export-док без записи в registry (не синкан в Huly): {rel(os.path.join(root,f))}")

# --- итог
print("\n=== ИТОГ ===")
for e in errors: print(f"ERROR {e}")
for w in warns:  print(f"WARN  {w}")
print(f"\nERROR: {len(errors)} | WARN/INFO: {len(warns)}")
print("[5] Huly-сторона (живость docId / parent, лишние доки в teamspace) — агентом через MCP huly:")
print("    list_documents по каждому teamspace из registry ↔ map (дрейф в обе стороны).")
sys.exit(1 if errors else 0)
PYEOF
rc=$?
echo ""
echo "=== wiki-lint: $([ $rc -eq 0 ] && echo OK || echo 'FAIL (есть ERROR)') ==="
exit $rc
