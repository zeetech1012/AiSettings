#!/usr/bin/env bash
# install.sh — раскладка AI baseline по установленным агентам.
# Идемпотентен, существующие файлы НЕ перезаписывает (сообщает и пропускает).
set -u
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$REPO_DIR/plugins/qa/skills"

say()  { printf '%s\n' "$*"; }
sync_rules_copy() { # $1 = файл в репо, $2 = целевая копия
  if [ -e "$2" ]; then
    if cmp -s "$1" "$2"; then say "  = $2 совпадает с baseline"
    else
      say "  ! $2 отличается от baseline (личные правки или отставание) — сравни:"
      say "      diff \"$2\" \"$1\""
    fi
  else cp "$1" "$2" && say "  + $2"; fi
}
link_skills_into() { # $1 = целевая директория skills
  mkdir -p "$1"
  for d in "$SKILLS_SRC"/*/; do
    name="$(basename "$d")"
    if [ -e "$1/$name" ]; then say "  = $name уже есть в $1 — пропущен"
    else ln -s "$d" "$1/$name" && say "  + $name → $1/$name"; fi
  done
}

# --- Claude Code -------------------------------------------------------------
if command -v claude >/dev/null 2>&1 || [ -d "$HOME/.claude" ]; then
  say "[claude] найден"
  mkdir -p "$HOME/.claude"
  sync_rules_copy "$REPO_DIR/AGENTS.md" "$HOME/.claude/AGENTS.md"
  if [ -e "$HOME/.claude/CLAUDE.md" ]; then
    say "  = ~/.claude/CLAUDE.md уже есть — проверь, что в нём есть строка '@AGENTS.md'"
  else
    cp "$REPO_DIR/claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md" && say "  + ~/.claude/CLAUDE.md (@AGENTS.md)"
    say "    → роль агента заполни в нём НАД строкой @AGENTS.md (образец: claude/CLAUDE.example.md)"
  fi
  if [ -e "$HOME/.claude/settings.json" ]; then
    say "  = ~/.claude/settings.json уже есть — слей вручную с claude/settings.json (marketplaces/plugins)"
  else cp "$REPO_DIR/claude/settings.json" "$HOME/.claude/settings.json" && say "  + ~/.claude/settings.json"; fi
  say "  → skills/agents приедут плагином: /plugin marketplace add https://github.com/zeetech1012/AiSettings.git"
  say "    затем: /plugin install qa@ai-settings (или enabledPlugins из settings.json)"
else
  say "[claude] не найден — пропуск"
fi

# --- Codex CLI + Gemini CLI: общая директория ~/.agents/skills ----------------
if command -v codex >/dev/null 2>&1 || [ -d "$HOME/.codex" ] || \
   command -v gemini >/dev/null 2>&1 || [ -d "$HOME/.gemini" ]; then
  say "[codex/gemini] найден хотя бы один — линкую skills в ~/.agents/skills"
  link_skills_into "$HOME/.agents/skills"
fi

if command -v codex >/dev/null 2>&1 || [ -d "$HOME/.codex" ]; then
  mkdir -p "$HOME/.codex"
  say "[codex]"
  sync_rules_copy "$REPO_DIR/AGENTS.md" "$HOME/.codex/AGENTS.md"
  say "[codex] роль агента — в начало личной копии ~/.codex/AGENTS.md"
  say "[codex] MCP: перенеси секции из mcp/codex.toml в ~/.codex/config.toml (см. mcp/README.md)"
fi

if command -v gemini >/dev/null 2>&1 || [ -d "$HOME/.gemini" ]; then
  say "[gemini] в ~/.gemini/settings.json добавь: \"context\": {\"fileName\": [\"AGENTS.md\", \"GEMINI.md\"]}"
  say "[gemini] MCP: слей mcp/gemini.settings.json с ~/.gemini/settings.json"
fi

# --- Cursor -------------------------------------------------------------------
if [ -d "$HOME/.cursor" ]; then
  say "[cursor] глобальных правил нет — AGENTS.md копируй в корень каждого рабочего репозитория; MCP: блок mcpServers → ~/.cursor/mcp.json"
fi

say ""
say "Готово. Секреты (HULY_TOKEN и т.п.) подставь по mcp/README.md — в git их не коммитить."
