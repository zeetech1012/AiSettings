---
name: project-tree-documenter
description: Поддержка и автогенерация аннотированных деревьев структуры каталогов проекта внутри Markdown-документации. Учитывает .gitignore и подсвечивает новые или изменённые пути.
---
# Project Tree Documenter

## Objective
Automatically scan the project's directory structure, respect `.gitignore` settings, and inject a formatted file/directory tree with descriptions into Markdown documentation between `<!-- TREE:START -->` and `<!-- TREE:END -->` tags.

## Workflow

When tasked with generating or checking the project directory structure in documentation:

1. **Read Configuration:** Load configuration files (e.g., `readme_tree/config.yaml`) that declare path pruning (directories not to descend into), ignore patterns, custom path orders, and path-to-description annotations.
2. **Scan Filesystem:** Traverse the workspace up to the specified `max_depth` (using `pathlib` or native directory walkers).
3. **Respect Ignored Paths:** If enabled, use `git check-ignore` or parse `.gitignore` to skip build, cache, and dependency files for a clean documentation output.
4. **Generate Tree Markdown:** Format the scanned structure into an ASCII/Unicode hierarchy tree with aligned descriptions:
   ```markdown
   └── scripts/                  # Automation scripts
       ├── readme/               # README generation pipeline
       └── validation/           # Link and URL checks
   ```
5. **Inject into Document:** Open the target Markdown file (e.g., `docs/README-GENERATION.md`), locate the comment blocks (`<!-- TREE:START -->` and `<!-- TREE:END -->`), and overwrite only that section with the newly generated tree.
6. **Drift Detection (CI Mode):** If triggered in check mode, verify if the current tree on disk matches the one in the documentation. Fail if out of sync, ensuring no documentation drift occurs.
