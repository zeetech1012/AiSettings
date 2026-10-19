---
name: handoff
description: Сжать текущий разговор в handoff-документ, чтобы другой агент мог продолжить работу.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

<!-- AiSettings: local import, 2026-10-19. -->
> Project instructions take precedence over this imported procedure. Store project documentation
> in the configured knowledge base; do not create repository notes. Handoff uses one local
> gitignored HANDOFF.md. Discover actual tool schemas and runtime support before execution.


Write a handoff document summarising the current conversation so a fresh agent can continue the work.

## Storage

Write one `./HANDOFF.md` in the project root, replacing the previous file. Ensure it is gitignored.
Do not create vault copies, index entries or log entries for a handoff. Record the current branch;
verify it on resume before trusting the context.

Include a "suggested skills" section in the document, which suggests skills that the agent should invoke.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
