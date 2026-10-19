---
name: service-doc
description: >
  Используй этот навык, когда просят изучить репозиторий сервиса и сгенерировать документацию
  для целей QA, либо при подготовке контекста для написания тестов в другом репозитории.
  Triggers on: "изучи сервис", "создай документацию для тестов", "сгенерируй контекст",
  "prepare service context", "document this service for QA", "create swagger",
  "что покрыть тестами", "какие эндпоинты у сервиса".
  Запускай этот навык В РЕПОЗИТОРИИ СЕРВИСА, затем передай результат в согласованное место
  хранения QA-контекста.
---

# Service documentation for QA

Read the existing service description, approved API contract and requirements in the knowledge base.
Expected test results come from owner-approved requirements, never from implementation.

1. Read the service README, existing specifications and entry points. Use source only to extract
   interface shape (routes, request/response fields, auth transport) and state changed by checks
   so cleanup is safe. Do not inspect implementation to hunt defects.
2. Record each extracted fact with `file:line` and 🟡. An extracted contract is `status: draft`;
   behavioral claims need the owner's confirmation before becoming test expectations.
3. Write service overview, interface inventory, environment requirements and open questions in the
   export tree of the configured knowledge base. For Obsidian use its CLI/API, not raw file writes.
   Do not create `<SERVICE>_CONTEXT.md` or `docs/<service>.md` in the repository.
4. If no OpenAPI/AsyncAPI exists, record the draft specification in the knowledge base. The service
   owner maintains a canonical CI file; record its agreed repository path in the note header.
5. Verify routes and model fields against the cited source. Do not invent status codes, constraints,
   time limits, endpoints or expected behavior. Unspecified behavior is a question to the owner.
6. A failure observed in a run against approved requirements becomes one defect via `service-issue`.
   A draft that disagrees with source is corrected as a draft; QA does not fix production code.

## Reconcile an existing description

Inspired by `nacl-tl-reconcile` (ITSalt/NaCl, MIT). Prepare minimal changes with evidence for each
`file:line`, show the owner the proposed edits, then write on approval. Do not change implementation.
Approved requirements remain authoritative. Stop after three review rounds if questions remain;
source-derived behavioral statements remain draft until approved.
