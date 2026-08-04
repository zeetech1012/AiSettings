#!/bin/bash
# PreToolUse(Bash) — не даёт закоммитить секрет: gitleaks по staged-изменениям.
# Срабатывает и на `git commit --no-verify` (нативный pre-commit тот обходит, этот — нет).

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

echo "$COMMAND" | grep -qE '\bgit[[:space:]]+([^|;&]*[[:space:]])?commit\b' || exit 0

REPO=$(git -C "${CLAUDE_PROJECT_DIR:-$PWD}" rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$REPO" ] || exit 0

GITLEAKS=$(command -v gitleaks || echo /opt/homebrew/bin/gitleaks)
if [ ! -x "$GITLEAKS" ]; then
  echo "BLOCKED: gitleaks не найден — проверить staged на секреты нечем, коммит остановлен. Установи: brew install gitleaks" >&2
  exit 2
fi

REPORT=$("$GITLEAKS" git --staged --redact --no-banner --log-level error \
  --report-format json --report-path - "$REPO" 2>/dev/null) && exit 0

echo "BLOCKED: gitleaks нашёл секреты в staged-изменениях — коммит остановлен." >&2
SUMMARY=$(echo "$REPORT" | jq -r '.[] | "  \(.File):\(.StartLine) — \(.RuleID)"' 2>/dev/null)
if [ -n "$SUMMARY" ]; then echo "$SUMMARY" >&2; else echo "  (отчёт gitleaks не разобран — запусти вручную: gitleaks git --staged --redact .)" >&2; fi
echo "Что делать: убрать файл из индекса (git restore --staged <file>), значение вынести в secrets/ или ENV, при реальной утечке — ротировать секрет. Обход через --no-verify не поможет." >&2
exit 2
