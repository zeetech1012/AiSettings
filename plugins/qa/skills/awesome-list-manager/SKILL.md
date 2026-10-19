---
name: awesome-list-manager
description: Управление, сортировка, рендеринг и валидация awesome-списков на основе структурированных CSV-баз и YAML-схем категорий. Обеспечивает соблюдение ID-префиксов и обновляет оглавления.
---
# Awesome List Manager

## Objective
Automate the lifecycle of an awesome list, including category definitions, hierarchical sorting, unique ID generation with prefix codes, and rendering multiple README.md styles from Jinja2/Markdown templates.

## Workflow

When triggered to manage, generate, or validate an awesome list:

1. **Category Mapping:** Read category configuration (e.g., `templates/categories.yaml`) to load unique prefixes (e.g., `skill`, `cmd`, `tool`), display icons, and order hierarchy.
2. **ID Generation:** When adding a new resource, auto-generate a slug/ID based on the category's prefix (e.g., `skill-allure-triager` for "Agent Skills") to ensure uniformity.
3. **Database Validation:** Read and validate the CSV database (e.g., `THE_RESOURCES_TABLE.csv`):
   - Ensure header column alignment.
   - Verify that all IDs conform to category prefixes.
   - Run URL sanitization and duplication checks.
4. **Hierarchical Sorting:** Sort all entries in the database by Category Order -> Subcategory Name -> Resource Display Name to prevent messy git diffs.
5. **Template Rendering:** Render the README.md files (e.g., Classic, Minimal, Visual/Extra) using defined templates and config keys (e.g., `acc-config.yaml`). Include repository statistics like Stars and Forks using GitHub API or fetch cache.

## Output format
Generate a confirmation report of the operations done:
- **Validations Checked:** Count of items validated, sorted, and matched.
- **Errors Found:** Discrepancies in ID formats, headers, or categories.
- **Git State:** Resulting status of database sorting and README files regenerated.
