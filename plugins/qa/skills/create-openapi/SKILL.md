---
name: create-openapi
description: Задаёт spec-first контракт API-документации для ЛЮБОГО сервиса компании независимо от языка (Go, PHP, C++, Python, Node). Создаёт артефакт openapi.json (OpenAPI 3.0) И определяет единственный эндпоинт, который его отдаёт (GET <prefix>/openapi.json), БЕЗ аннотаций в коде. Это «тонкий контракт», потребляемый центральным порталом документации (api.example.com/docs). Triggers on "create openapi", "сделай спеку", "добавь openapi.json", "ручку для спеки", "openapi endpoint", "тонкий контракт документации", "expose openapi spec", "serve openapi.json", "документация сервиса".
---
# Create OpenAPI (spec-first) — language-agnostic doc contract

## Objective
Give a service the **thin documentation contract** so it can plug into the central docs portal (`api.example.com/docs`). The contract is **the same in every language**; only the way the file is served differs. Two parts:

1. **Artifact** — a hand/AI-maintained `openapi.json` (OpenAPI 3.0) describing the API.
2. **Endpoint** — `GET <prefix>/openapi.json` that returns that file at runtime.

No UI is built into the service (Swagger UI / Redoc live in the portal). No in-code annotation generators (swaggo, springdoc, drf-spectacular, etc.) — the spec is a reviewable artifact, the source of truth.

Reference implementation: `auth_http` (Go). Use it as the shape to mirror in any stack.

## The contract (language-independent — this is the heart)

### A. The spec artifact `openapi.json`
- OpenAPI **3.0**, valid (must pass `redocly lint`).
- `info.title` — filled; becomes the service's **dropdown label** in the portal.
- `info.version` — filled; the contract version.
- `servers: [{ "url": "/<prefix>" }]` — **relative**, never a hardcoded host, so one artifact works on any stand.
- `paths` + `components.schemas` derived from the real API (see Workflow step 1).
- Lives in the repo next to the code, reviewed in PRs like any source file.

### B. The serving endpoint
- Path: `GET <prefix>/openapi.json` (e.g. `/auth/openapi.json`).
- Response: the spec bytes, `Content-Type: application/json`, `200`.
- Reachable **same-origin** through the `api.example.com` gateway (the portal references it relatively).
- **Gated** by a config flag `DOCS_ENABLED` (or equivalent), **default OFF** — prod does not expose the spec unless explicitly enabled (and then only behind VPN). When off, the route is not registered / returns 404.
- Served from a bundled/embedded copy of the artifact (no runtime dependency on a file path that may be absent in the container), OR a static file the web server serves directly.

### C. What must NOT be in the service
- No bundled Swagger UI / Redoc HTML or JS/CSS assets.
- No annotation-based spec generation in handler code.
- No absolute host in `servers`.
- No always-on exposure (gate defaults off).

## Workflow

1. **Derive the contract from source** (spec-first). Read routes/methods, path & query params, request/response shapes, status codes, auth/RBAC. Translate data models → `components.schemas` (reuse `$ref`). For Go, lean on the `go-service-explorer` skill; for a frontend-driven contract use `frontend-contract-miner`.

2. **Write `openapi.json`** using this skeleton; fill `paths` and `components.schemas`:
   ```json
   {
     "openapi": "3.0.3",
     "info": { "title": "<Company> <service> API", "version": "<contract-version>", "description": "<one-line purpose>" },
     "servers": [ { "url": "/<prefix>", "description": "<service> (relative to current host)" } ],
     "paths": {},
     "components": {
       "schemas": {},
       "securitySchemes": { "bearerAuth": { "type": "http", "scheme": "bearer", "bearerFormat": "JWT" } }
     }
   }
   ```

3. **Expose the endpoint** per the service's stack (see Recipes). The behavior is fixed by the contract; the code is whatever idiom the project uses.

4. **Add the gate** — a `DOCS_ENABLED`-style flag defaulting to off; enable on dev/test stands, leave off on prod (unless behind VPN).

5. **Validate** — `redocly lint openapi.json` green; build passes; smoke: with the flag on, `curl -s -o /dev/null -w "%{http_code} %{content_type}" .../<prefix>/openapi.json` → `200 application/json`. Wire `redocly lint` into the service CI.

## Serving recipes by language (examples, not the contract)
The contract is identical; pick the idiom matching the repo.

- **Go** — embed the file and register one handler (reference `auth_http/docs/docs.go`):
  ```go
  //go:embed openapi.json
  var specJSON []byte
  // if DOCS_ENABLED: GET <prefix>/openapi.json -> write specJSON, Content-Type application/json
  ```
- **Python (FastAPI/Flask)** — serve the bundled file behind the flag:
  ```python
  if DOCS_ENABLED:
      @app.get("/<prefix>/openapi.json")
      def spec(): return Response(SPEC_PATH.read_bytes(), media_type="application/json")
  ```
  (FastAPI auto-generates a spec, but the contract here is spec-first: serve the reviewed `openapi.json`, disable the built-in `/docs` UI.)
- **PHP** — a route/controller that `readfile()`s the artifact with `Content-Type: application/json`, guarded by the config flag.
- **C++** — register a route in the embedded HTTP server returning the file contents (compile-in as a resource or read once at startup), gated by config.
- **Node (Express)** — `if (DOCS_ENABLED) app.get('/<prefix>/openapi.json', (_, res) => res.type('application/json').send(spec))`.

In every case: one route, returns the JSON, `application/json`, gated, relative `servers`, no UI.

## Hard constraints (do NOT violate, any language)
- Spec-first — no in-code annotation generators.
- No UI / vendored assets in the service.
- Relative `servers` (`/<prefix>`), never a hardcoded host.
- Exactly one doc route: `<prefix>/openapi.json`.
- Gate defaults to **off**.

## Output
- `openapi.json` (new or regenerated) in the repo.
- The single serving endpoint wired in the project's stack, behind the `DOCS_ENABLED` gate.
- Short diff summary: endpoints/schemas covered + what to review in the spec.

## Related
- `go-service-explorer` — extract routes/payloads from Go source (feed step 1).
- `frontend-contract-miner` — derive the contract from a React/Next consumer.
- `swagger-to-pydantic` — generate QA Pydantic models from the produced spec.
- Central portal design: Obsidian `Company/Projects/<service>/Централизованный портал API-документации.md`, Huly `AUTH-2`.
