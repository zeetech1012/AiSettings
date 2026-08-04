#!/bin/bash
# PreToolUse(Bash) — блокирует деструктивные git-команды до исполнения.
# Установлен скиллом git-guardrails-claude-code.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

DANGEROUS_PATTERNS=(
  "git push"
  "git reset --hard"
  "git clean -fd"
  "git clean -f"
  "git branch -D"
  "git checkout \."
  "git restore \."
  "push --force"
  "reset --hard"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qE "$pattern"; then
    echo "BLOCKED: '$COMMAND' matches dangerous pattern '$pattern'. The user has prevented you from doing this." >&2
    exit 2
  fi
done

# git add по секретным путям — не даём секрету попасть в индекс в принципе.
if echo "$COMMAND" | grep -qE '\bgit[[:space:]]+add\b'; then
  for token in $COMMAND; do
    # снять окружающие кавычки: иначе whitelist ниже не сработает на "path.example"
    token="${token%\"}"; token="${token#\"}"
    token="${token%\'}"; token="${token#\'}"
    case "$token" in
      *.example|*.sample|*.template) continue ;;
      secrets/*|*/secrets/*|.env|*/.env|*.env|*.env.*|*.pem|*.key|*.token)
        echo "BLOCKED: '$token' выглядит как секретный путь — git add по нему запрещён. The user has prevented you from doing this." >&2
        exit 2
        ;;
    esac
  done
fi

exit 0
