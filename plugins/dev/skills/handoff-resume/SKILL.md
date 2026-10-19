---
description: Возобновляет работу по handoff-документу
name: handoff-resume
---

<!-- AiSettings: local import, 2026-10-19. -->
> Project instructions take precedence over this imported procedure. Store project documentation
> in the configured knowledge base; do not create repository notes. Handoff uses one local
> gitignored HANDOFF.md. Discover actual tool schemas and runtime support before execution.


Use one local gitignored HANDOFF.md in the project root. Replace the previous handoff; do not create vault copies or update wiki indexes/logs. On resume verify the branch first.


Resume work from a handoff created by another AI agent.

## 1. Find and Read the Handoff

Look for the handoff document:
- If `$ARGUMENTS` is provided, read that path
- Otherwise, check for `HANDOFF.md` in the current directory
- If not found, ask the user for the path

Read the entire handoff document carefully.

## 2. Verify State Hasn't Drifted

Run `git status` and `git log --oneline -3` to check:
- Is the branch the same as documented?
- Have there been commits since the handoff was created?
- Are there uncommitted changes not mentioned in the handoff?

If state has drifted significantly, warn the user:
> "The repo has changed since this handoff was created. [describe changes]. Should I proceed with the handoff context anyway, or would you like to describe what changed?"

## 3. Summarize to the User

Give a brief summary (not the whole document):

```
Resuming from handoff: [title]

Goal: [1 sentence]
Status: [X of Y tasks complete]
Next: [First item from Resume Instructions]

Ready to continue?
```

## 4. Heed the Warnings

Pay special attention to:
- **Failed Approaches** - Don't repeat these mistakes
- **Warnings** - Respect gotchas from the previous agent
- **Key Decisions** - Follow established patterns unless user asks to change

## 5. Continue the Work

Start with the first item in "Resume Instructions" unless the user redirects.

If the handoff is unclear on something critical, ask the user rather than guessing.
