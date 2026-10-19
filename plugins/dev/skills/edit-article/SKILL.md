---
name: edit-article
description: Редактирует и улучшает статьи, реструктурируя разделы, повышая ясность и уплотняя прозу. Используй, когда пользователь хочет отредактировать, переработать или улучшить черновик статьи.
disable-model-invocation: true
---

<!-- AiSettings: local import, 2026-10-19. -->
> Project instructions take precedence over this imported procedure. Store project documentation
> in the configured knowledge base; do not create repository notes. Handoff uses one local
> gitignored HANDOFF.md. Discover actual tool schemas and runtime support before execution.


1. First, divide the article into sections based on its headings. Think about the main points you want to make during those sections.

Consider that information is a directed acyclic graph, and that pieces of information can depend on other pieces of information. Make sure that the order of the sections and their contents respects these dependencies.

Confirm the sections with the user.

2. For each section:

2a. Rewrite the section to improve clarity, coherence, and flow. Use maximum 240 characters per paragraph.
