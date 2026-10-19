---
description: Создаёт минимальный handoff — только самое необходимое
name: handoff-quick
---

<!-- AiSettings: local import, 2026-10-19. -->
> Project instructions take precedence over this imported procedure. Store project documentation
> in the configured knowledge base; do not create repository notes. Handoff uses one local
> gitignored HANDOFF.md. Discover actual tool schemas and runtime support before execution.


Use one local gitignored HANDOFF.md in the project root. Replace the previous handoff; do not create vault copies or update wiki indexes/logs. On resume verify the branch first.


Create a minimal `HANDOFF.md` with only the essentials. Use this for simple tasks or quick context transfers.

Output this exact format (fill in the brackets):

```markdown
# Handoff: [task in 5 words or less]

**Goal**: [one sentence]

**Done**: [comma-separated list of completed items, or "Nothing yet"]

**Next**: [the single most important next step]

**Watch out**: [one key warning, or "Nothing special"]
```

That's it. No extras. Save to `HANDOFF.md` or the path in `$ARGUMENTS`.
