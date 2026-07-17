---
name: service-doc
description: >
  Используй этот навык, когда просят изучить репозиторий сервиса и сгенерировать документацию
  для целей QA, либо при подготовке контекста для написания тестов в другом репозитории.
  Triggers on: "изучи сервис", "создай документацию для тестов", "сгенерируй контекст",
  "prepare service context", "document this service for QA", "create swagger",
  "что покрыть тестами", "какие эндпоинты у сервиса".
  Запускай этот навык В РЕПОЗИТОРИИ СЕРВИСА, затем скопируй результат в <qa-repo>/docs/.
---

# Generating QA Context Document from a Service Repository

## Purpose

This skill produces a single markdown file that a QA agent in another repo
will use as the source of truth when writing automated tests.
The output file replaces the need for cross-session context sharing.

## Step 0 — Switch to Verbose Mode

Before starting, set Transcript view to **Verbose**.
This lets you see every file the agent reads and catch mistakes early.

---

## Step 1 — Explore the Repository

Read in this order:

1. `README.md` or `docs/` — general service description
2. `main.go` / `cmd/` — entry point, what ports/routes are registered
3. Router file — `router.go`, `routes.go`, or any file with `r.GET` / `r.POST`
4. Handler files — actual business logic per endpoint
5. Model/DTO files — request and response structs
6. Middleware — auth checks, rate limiting, logging
7. `swagger.yaml` / `swagger.json` or `docs/swagger.json` — if exists, use as primary source
8. `.env.example` or `config/` — required environment variables

If Swagger exists → use it as primary source, verify against handlers.
If Swagger does not exist → generate it from code (see Step 2b).

---

## Step 2a — If Swagger Exists

Read `docs/swagger.json` or `/swagger/index.html`.
Extract all endpoints, models, and auth requirements.
Skip to Step 3.

---

## Step 2b — If Swagger Does NOT Exist

Generate a Swagger spec from code:

```
Прочитай все handler-файлы и struct-модели.
Создай файл docs/swagger.yaml в формате OpenAPI 3.0:

openapi: 3.0.0
info:
  title: <ServiceName> API
  version: "1.0"
paths:
  /endpoint:
    post:
      summary: ...
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RequestModel'
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResponseModel'
components:
  schemas:
    RequestModel:
      type: object
      required: [field1]
      properties:
        field1:
          type: string
```

Commit the generated swagger.yaml to the service repo.
```

---

## Step 3 — Generate QA Context Document

Create file `<SERVICE_NAME>_CONTEXT.md` in the service repo root.
Use exactly this structure — QA agent depends on it:

```markdown
# <ServiceName> — QA Context

> Generated: <date>
> Base URL pattern: `https://<service>.api.example.com`
> Auth: Bearer JWT from auth-gateway required on all endpoints (unless marked Public)

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /api/v1/login | Public | Get JWT token |
| GET | /api/v1/users | Required | List users |
| ... | | | |

---

## Request / Response Models (Pydantic format)

Ready to paste into `core/models/<service>_models.py`:

\```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class LoginRequest(BaseModel):
    login: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int

# ... all other models
\```

---

## Auth Flow

Step-by-step how authentication works in this service:

1. Client sends POST /api/v1/auth/login with {login, password}
2. Service validates credentials against user_db_service
3. Returns JWT access_token (TTL: Xmin) + refresh_token (TTL: Xdays)
4. All subsequent requests: Authorization: Bearer <access_token>
5. Token refresh: POST /api/v1/auth/refresh with {refresh_token}

---

## Edge Cases for Testing

Grouped by priority:

### BLOCKER — must cover
- [ ] Valid login returns 200 + valid JWT
- [ ] Invalid credentials return 401
- [ ] Expired token returns 401 (not 403)
- [ ] <core business flow> happy path

### CRITICAL
- [ ] Missing required fields return 422
- [ ] Malformed JWT returns 401
- [ ] <list specific business validations>

### NORMAL
- [ ] Rate limiting (if configured)
- [ ] Field length limits
- [ ] Concurrent requests

### MINOR
- [ ] Response time < 500ms under normal load
- [ ] Error messages are in expected format

---

## Environment Variables Required

| Variable | Description | Example |
|---|---|---|
| BASE_URL | Service base URL | https://auth.api.example.com |
| AUTH_LOGIN | Test user login | test@example.com |
| AUTH_PASSWORD | Test user password | testpass |

---

## Example Requests (curl)

\```bash
# Login
curl -X POST https://auth.api.example.com/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"login": "user@example.com", "password": "secret"}'

# Authenticated request
curl -X GET https://auth.api.example.com/api/v1/users \
  -H "Authorization: Bearer <token>"
\```

---

## Known Limitations / Notes for QA

- <any service-specific quirks, timeouts, known bugs to avoid>
- <data cleanup requirements after tests>
- <dependencies on other services>
```

---

## Step 4 — Copy to QA Repository

After generating the document:

```bash
cp <SERVICE_NAME>_CONTEXT.md ../<qa-repo>/docs/<service-name>.md
```

Or instruct the developer / devops to add it to the QA repo.

---

## Step 5 — Verify the Document

Before finishing, check:

- [ ] Every endpoint from the router is documented
- [ ] All request models have required fields marked
- [ ] Auth requirements are correct (public vs protected)
- [ ] Pydantic models are syntactically valid Python
- [ ] At least 5 edge cases listed per service
- [ ] curl examples work against staging URL
