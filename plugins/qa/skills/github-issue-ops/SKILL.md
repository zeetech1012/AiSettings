---
name: github-issue-ops
description: Обработка структурированных GitHub Issue Forms (через Markdown/YAML templates), валидация полей, парсинг данных в JSON и автоматизация создания git branches и Pull Requests.
---
# GitHub Issue Ops Manager

## Objective
Automate administrative repository chores by parsing user submissions via structured GitHub Issues, executing static validation, and dynamically issuing Pull Requests using native Git and GitHub CLI (`gh`).

## Workflow

When triggered to process a GitHub Issue or automate a Pull Request:

1. **Parse Issue Form:** Read the structured Markdown of a GitHub Issue. Match and parse sections (e.g., "Resource Name", "URL", "Category") defined in `.github/ISSUE_TEMPLATE/` into a structured JSON payload.
2. **Execute Resource Validation:** Run targeted checks on the parsed fields (e.g., link reachable, category exists, title matches standards). Provide real-time feedback.
3. **Automate Branching:**
   - Detect repository root.
   - Resolve branch names dynamically (e.g., `add-resource-<id>`).
   - Create a clean git branch from the upstream main/master.
4. **Modify Database:** Append or update the resource database file (e.g., `THE_RESOURCES_TABLE.csv`) ensuring correct column alignment and formatting.
5. **Issue Pull Request:**
   - Commit changes with standardized prefix messages (e.g., `feat(resource): add <name>`).
   - Push to origin or upstream fork.
   - Use GitHub CLI (`gh pr create`) to open a Pull Request linking back to the original issue.

## CLI Usage Guidelines
Utilize the following commands where needed:
- `gh issue view <issue_number> --json body`
- `git checkout -b <branch_name>`
- `git commit -am "<message>"`
- `gh pr create --title "<title>" --body "Closes #<issue_number>"`
