---
name: git-guardrails-claude-code
description: Настраивает хуки Claude Code, блокирующие опасные git-команды (отправка в remote, reset --hard, clean, branch -D, git add по секретным путям) и коммит с секретами в staged до их выполнения. Используй, когда пользователь хочет предотвратить деструктивные git-операции, утечку секретов в индекс или добавить хуки безопасности для git в Claude Code.
---

# Setup Git Guardrails

Sets up PreToolUse hooks that intercept and block dangerous git commands before Claude executes them.

Два независимых хука, оба на матчере `Bash`:

| Хук | Что перехватывает |
|---|---|
| `block-dangerous-git.sh` | деструктивные git-команды и `git add` по секретным путям |
| `gitleaks-staged-guard.sh` | `git commit`, если gitleaks нашёл секреты в staged-изменениях |

## What Gets Blocked

`block-dangerous-git.sh`:

- `git push` (all variants including `--force`)
- `git reset --hard`
- `git clean -f` / `git clean -fd`
- `git branch -D`
- `git checkout .` / `git restore .`
- `git add` по путям, похожим на секреты (`secrets/…`, `.env`, `*.pem`, `*.key`, `*.token`);
  `*.example` / `*.sample` / `*.template` пропускаются

When blocked, Claude sees a message telling it that it does not have authority to access these commands.

`gitleaks-staged-guard.sh` — прогоняет `gitleaks git --staged --redact` перед любым `git commit`
и блокирует его при находках, печатая `файл:строка — RuleID`. Ловит и `git commit --no-verify`,
которым нативный pre-commit обходится. Требует установленного `gitleaks`; если бинаря нет —
коммит блокируется (проверять секреты нечем), а не пропускается молча.

## Steps

### 1. Ask scope

Ask the user: install for **this project only** (`.claude/settings.json`) or **all projects** (`~/.claude/settings.json`)?

### 2. Copy the hook scripts

Bundled scripts: [scripts/block-dangerous-git.sh](scripts/block-dangerous-git.sh) и
[scripts/gitleaks-staged-guard.sh](scripts/gitleaks-staged-guard.sh).

Copy them to the target location based on scope:

- **Project**: `.claude/hooks/<script>.sh`
- **Global**: `~/.claude/hooks/<script>.sh`

Make them executable with `chmod +x`. Второй хук требует `gitleaks` в PATH
(`brew install gitleaks`) — иначе он будет блокировать все коммиты.

### 3. Add hook to settings

Add to the appropriate settings file:

**Project** (`.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/block-dangerous-git.sh"
          },
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/gitleaks-staged-guard.sh"
          }
        ]
      }
    ]
  }
}
```

**Global** (`~/.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/block-dangerous-git.sh"
          },
          {
            "type": "command",
            "command": "~/.claude/hooks/gitleaks-staged-guard.sh"
          }
        ]
      }
    ]
  }
}
```

If the settings file already exists, merge the hook into existing `hooks.PreToolUse` array — don't overwrite other settings.

### 4. Ask about customization

Ask if user wants to add or remove any patterns from the blocked list. Edit the copied script accordingly.

### 5. Verify

Run a quick test:

```bash
echo '{"tool_input":{"command":"git push origin main"}}' | <path-to>/block-dangerous-git.sh
echo '{"tool_input":{"command":"git add .env"}}'          | <path-to>/block-dangerous-git.sh
```

Should exit with code 2 and print a BLOCKED message to stderr. Хук gitleaks проверяется на
реальном репозитории: `git add` файла с тестовым секретом, затем
`echo '{"tool_input":{"command":"git commit -m x"}}' | <path-to>/gitleaks-staged-guard.sh`.
