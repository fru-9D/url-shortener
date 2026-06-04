# Architecture Review — 2026-06-01 (v3)

**PRD:** `docs/prd.md`
**ERD:** `docs/erd.md` (Draft v4)
**Architecture:** `docs/architecture.md`
**Verdict:** FAIL_BLOCKER
**Gate 1:** 0  **Gate 2:** 7  **Gate 3:** 7

---

## Lookup

| Location | Finding | Rule ID | Gate | Severity |
|---|---|---|---|---|
| `docs/architecture.md` | No declaration of CORS allowlist policy, allowed methods, or `Access-Control-Allow-Credentials` posture | ARCH-019 | 2 | blocker |
| `docs/architecture.md` | No declaration of HTTP security headers (CSP, HSTS, X-Frame-Options, etc.), where they are emitted, or their canonical values | ARCH-020 | 2 | blocker |
| `docs/architecture.md` | No declaration of API versioning scheme or deprecation policy | ARCH-022 | 2 | blocker |
| `docs/architecture.md` | No declaration of health check endpoints (names, what each checks, which orchestrator consumes them) | ARCH-023 | 2 | blocker |
| `docs/architecture.md` | No declaration of request body / payload size limits or where limits are enforced | ARCH-024 | 2 | blocker |
| `docs/architecture.md` | No declaration of input validation / DTO boundary policy for FastAPI endpoints | ARCH-025 | 2 | blocker |
| `docs/architecture.md:151` | Error envelope shape declared but global exception handler, stack-trace policy, and exception-to-status-code mapping are absent | ARCH-026 | 2 | blocker |
| `docs/architecture.md` | No declaration of database connection pool size, max overflow, or sizing math against DB `max_connections` | ARCH-028 | 3 | warning |
| `docs/architecture.md` | SQS async retries covered; no idempotency policy declared for mutating API endpoints (link create, invite accept, member removal) | ARCH-029 | 3 | warning |
| `docs/architecture.md` | Link list is 50 items/page per PRD; no pagination scheme declared (cursor vs offset, default/max page size, cursor parameter name) | ARCH-030 | 3 | warning |
| `docs/architecture.md` | Multi-step writes described but no transaction boundary / unit-of-work pattern declared | ARCH-031 | 3 | warning |
| `docs/architecture.md` | No graceful shutdown / draining strategy declared for ECS Fargate services | ARCH-033 | 3 | warning |
| `docs/architecture.md` | No payload compression strategy declared despite growing link-list and analytics responses | ARCH-034 | 3 | warning |

---

## Findings

### ARCH-019 · Gate 2 · blocker · effort: low

**Message:** The architecture does not declare a CORS allowlist policy. The system has a Next.js dashboard origin making fetch requests with `credentials: 'include'` to the FastAPI Link API. Without an explicit allowed-origins list, the CORS configuration — whether the API rejects cross-origin requests by default, which methods are exposed, and whether `Access-Control-Allow-Credentials: true` is required — is left to the implementer to decide ad hoc. Wildcard CORS with credentials is an XSS/CSRF vector and would contradict the CSRF double-submit scheme declared in the frontend/backend contract section.

**Fix:** Add a CORS policy subsection declaring: (1) the production allowed-origins list (e.g. `https://app.snip.io` plus any branded-domain origins); (2) the allowed HTTP methods; (3) that `Access-Control-Allow-Credentials: true` is required; (4) where the policy is enforced (FastAPI CORSMiddleware or ALB/edge layer).

---

### ARCH-020 · Gate 2 · blocker · effort: low

**Message:** The architecture declares no HTTP security headers strategy. The PRD NFR explicitly requires CSRF protection on all mutating endpoints and an OWASP Top-10 baseline, but the architecture does not name where headers such as `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, and `Permissions-Policy` are emitted (Cloudflare edge, ALB, FastAPI middleware, Next.js headers config), their canonical values, or any environment-specific overrides.

**Fix:** Add an HTTP security headers section declaring: which headers are emitted, their production values, where each is applied (Cloudflare Transform Rules / Workers, ALB response headers policy, or Next.js `headers()` config), and any dev-environment overrides.

---

### ARCH-022 · Gate 2 · blocker · effort: low

**Message:** The architecture does not declare an API versioning scheme or deprecation policy. The architecture states FastAPI generates OpenAPI docs consumed by `openapi-typescript` on the Next.js side, but there is no statement of whether the API is versioned (e.g. `/v1/` URI prefix), whether every change is guaranteed backward-compatible, or what the deprecation window and sunset mechanism are. The internal dashboard client is already a consumer that will break on unversioned breaking changes.

**Fix:** Add an API versioning subsection declaring the scheme (e.g. `/v1/` URI prefix, or explicit "every change is backward-compatible with a documented change-log gate") and the deprecation policy (overlap window duration, `Deprecation` / `Sunset` header usage). Even a "no versioning — breaking changes require coordinated dashboard deploy" statement is acceptable if explicit.

---

### ARCH-023 · Gate 2 · blocker · effort: low

**Message:** The architecture does not declare health check endpoints. ECS Fargate services and the ALB require health checks to route traffic and replace unhealthy tasks, but neither the endpoint paths (`/health`, `/healthz`, `/readiness`, `/liveness`), what each checks (process alive vs. DB + Redis reachable), the dependency-check timeout, nor which orchestrator consumes each endpoint is stated anywhere in the document.

**Fix:** Add a health check section declaring the endpoint names, what each signals (liveness = process responds; readiness = process + DB primary + Redis reachable), the per-dependency timeout within the readiness check, and the ALB / ECS health check configuration (path, interval, healthy/unhealthy threshold).

---

### ARCH-024 · Gate 2 · blocker · effort: low

**Message:** The architecture declares no request body or payload size limits. The PRD caps destination URLs at 2048 characters, but there is no architectural statement of the default JSON body size limit, where it is enforced (ALB, Cloudflare, FastAPI), or the per-endpoint exceptions. An unbounded body limit is a denial-of-service primitive against the Link API.

**Fix:** Add a payload size limits statement in the Link API or security section: declare the default JSON body limit (e.g. 1 MB), where it is enforced (ALB request size limit, FastAPI middleware), and whether Cloudflare WAF has a request-size rule on the redirect Worker.

---

### ARCH-025 · Gate 2 · blocker · effort: low

**Message:** The architecture does not declare an input validation or DTO boundary policy. FastAPI is chosen as the API layer, but there is no statement that all request bodies are validated via Pydantic schemas before reaching handlers, that response bodies use explicit `response_model` projections (preventing accidental field leakage from ORM models), or the policy for partial-update schemas. The absence of this policy leaves the door open for mass-assignment vulnerabilities and raw-body parsing patterns.

**Fix:** Add an input validation policy statement (one or two sentences in the Link API or security section): e.g. "All request bodies are declared as Pydantic `BaseModel` subclasses on every endpoint; ORM objects are never returned directly — all responses use explicit `response_model` schemas; partial updates use dedicated `Update<X>` schemas."

---

### ARCH-026 · Gate 2 · blocker · effort: low

**Snippet:** `Every 4xx/5xx response is JSON: { "error": { "code": "<machine-code>", "message": "<human>" } }.`

**Message:** The error envelope shape is declared in the frontend/backend contract section, but the global exception handler that enforces it, the stack-trace policy, and the exception-to-HTTP-status-code mapping are absent. An unhandled FastAPI exception (e.g. a SQLAlchemy IntegrityError) will by default return a 500 with a framework-generated body that does not match the declared envelope, and may leak a stack trace in non-production environments.

**Fix:** Add a global exception handling subsection declaring: (1) the catch-all middleware / exception handler that wraps every unhandled exception in the declared envelope; (2) the stack-trace policy (never in prod HTTP responses; always forwarded to Sentry and CloudWatch); (3) the mapping from common exception classes to HTTP status codes (e.g. `EntityNotFound` → 404, `PermissionDenied` → 403, `ValidationError` → 422, unhandled → 500).

---

### ARCH-028 · Gate 3 · warning · effort: low

**Message:** The architecture does not declare a connection pool strategy for the FastAPI service. The scaling section notes ECS Fargate autoscales to 200 RPS sustained / 1000 RPS burst; the database section names the instance class but says nothing about per-task pool size, max overflow, or the arithmetic of (task count × pool size) against Postgres `max_connections`. At burst scale, an uncontrolled pool will exhaust connection slots before CPU or memory becomes the bottleneck.

**Fix:** Add a connection pool subsection: state the per-task SQLAlchemy `pool_size` and `max_overflow` values, compute total potential connections as (max ECS task count × (pool_size + max_overflow)), verify this is below the target DB's `max_connections` minus admin reserve, and name the pool-leak detection mechanism (e.g. `idle_in_transaction_session_timeout`).

---

### ARCH-029 · Gate 3 · warning · effort: medium

**Message:** The architecture describes SQS at-least-once delivery with consumer retry and DLQ, but no idempotency policy is declared for mutating API endpoints (link create, invite send, member removal, password reset initiation). If an ALB or client retries a timed-out POST to `/links`, a second link is created with a different short code. The PRD's "no deduplication for same-destination submissions" is a domain rule — not a substitute for an infrastructure-level retry-safety mechanism.

**Fix:** Declare an idempotency policy for write endpoints: either (a) accept an `Idempotency-Key` header on POST/PUT/PATCH, persist the (key, response) tuple for a TTL in Redis, and replay on retry; or (b) explicitly state which endpoints are naturally idempotent (e.g. invite-accept is idempotent on the token hash) and which accept duplicate semantics by PRD definition (link create), so implementers know the boundary.

---

### ARCH-030 · Gate 3 · warning · effort: low

**Message:** The PRD mandates 50-items-per-page link list pagination with forward/back navigation, and the CLICK table is append-only and unbounded (13-month retention). The architecture does not declare the pagination model (cursor vs offset), the default or maximum page size, or how the cursor is expressed as a query parameter. Without an architectural decision, the implementation will likely default to OFFSET-based pagination, which degrades for CLICK analytics queries as the table grows.

**Fix:** Add a pagination policy statement: declare the scheme (e.g. cursor-based on `(created_at DESC, id DESC)` for the link list; offset-based acceptable for bounded workspace-scoped lists), the default page size (50 per PRD), the maximum page size, and the query parameter name (e.g. `cursor`, `page`, `after`).

---

### ARCH-031 · Gate 3 · warning · effort: medium

**Message:** The architecture describes multi-step writes that must succeed atomically — (1) link create + ABUSE_REVIEW row insert + Mixpanel event enqueue; (2) member removal + link `owner_id` reassignment + pending invite cancellation (PRD §Teams: "atomically reassigns owner_id"); (3) invite accept + WORKSPACE_MEMBER row creation + INVITE status update — but does not declare where transactions start and end or whether event emission happens inside or after the transaction. Without this, partial-write states will occur.

**Fix:** Add a transaction boundary section: declare the unit-of-work pattern (e.g. "each API request opens one DB transaction; service layer never calls commit directly; the handler commits at successful return"). For operations that emit to SQS (link create → Mixpanel enqueue), explicitly declare whether the SQS publish is inside the transaction (transactional outbox) or after commit (accepted risk of lost event on crash between commit and publish).

---

### ARCH-033 · Gate 3 · warning · effort: low

**Message:** The architecture deploys Link API, click consumer, Mixpanel forwarder, and mail-events worker as ECS Fargate services but does not declare a graceful shutdown strategy. Without an explicit SIGTERM handler, ECS task replacement on deploys will abruptly terminate in-flight HTTP requests and in-flight SQS message processing. SQS consumers are especially sensitive: a task killed mid-processing will cause the message to become visible again, potentially triggering duplicate processing before the DLQ policy applies.

**Fix:** Add a graceful shutdown subsection: declare the SIGTERM handler sequence for HTTP services (stop accepting new connections, drain in-flight requests within a timeout, e.g. 30s), the consumer draining sequence (finish the current message batch before exiting), and the ECS `stopTimeout` value (must be ≥ the drain timeout plus a safety margin).

---

### ARCH-034 · Gate 3 · warning · effort: low

**Message:** The architecture does not declare a payload compression strategy. The link list API returns paginated JSON that grows with workspace activity; the analytics detail endpoint returns a 30-day time-series plus country-breakdown data. The PRD requires dashboard initial-render p95 < 2s on 4G — uncompressed payloads over a constrained mobile connection are a material contributor to that budget.

**Fix:** Add a payload compression statement: declare where compression is applied (Cloudflare for the edge; ALB or FastAPI GZipMiddleware for the regional API), the minimum response-size threshold, and whether Brotli is preferred over gzip where supported. Alternatively, explicitly state that current response sizes are below the threshold that makes compression worthwhile (with a rough payload size estimate).

---

## Dismissed rules

| Rule ID | Considered? | Dismissal reason |
|---|---|---|
| ARCH-001 | Yes | Auth section fully declares: HTTP-only Secure SameSite=Lax signed-session cookie, Redis-backed session record, session_version revocation, RBAC (admin/editor) enforced via FastAPI dependency middleware. |
| ARCH-002 | Yes | Secrets section declares AWS Secrets Manager, ECS Secrets Manager integration, Workers Secrets binding, 30-day DB rotation, quarterly signing-secret rotation with 7-day overlap window. |
| ARCH-003 | Yes | Backups section declares 5-min RPO via continuous WAL archiving to S3, 1-hour RTO with quarterly restore drills, daily/weekly/quarterly snapshot retention. |
| ARCH-004 | Yes | PRD names no specific compliance regime; GDPR manual handling is noted out-of-scope; architecture's Compliance section acknowledges this. |
| ARCH-005 | Yes | No direct contradiction found between architecture and PRD requirements. Email encryption, cookie flags, redirect at edge all match PRD NFRs. |
| ARCH-006 | Yes | Observability section declares structured JSON logs to CloudWatch, CloudWatch metrics with p50/p95/p99, AWS X-Ray distributed tracing with SQS propagation, and Sentry for error tracking. |
| ARCH-007 | Yes | All async operations (click pipeline, Mixpanel forwarding, mail-events) are behind SQS queues with ECS Fargate consumers. No long-running work in-request. |
| ARCH-008 | Yes | Scaling section declares Cloudflare Workers for redirect, ECS Fargate autoscale for Link API / Dashboard (200 RPS sustained, burst 1000), SQS queue-depth autoscale for click consumer, and DB vertical scale path. |
| ARCH-009 | Yes | All five external integrations addressed: Mixpanel (3× retry + DLQ), Pwned Passwords (500ms timeout, fail-open), SES (3× in-process retry), Google Safe Browsing (800ms timeout, fail-open), MaxMind GeoLite2 (local mmdb, 30-day stale fallback). |
| ARCH-010 | Yes | Multi-tenant isolation declared: base repository class AND's `workspace_id` into every SELECT/UPDATE/DELETE. |
| ARCH-011 | Yes | Migrations section declares Alembic, same-PR migration files, CI runs against fresh DB, production migrations gated on manual approval, forward-compatibility requirement. |
| ARCH-012 | Yes | Tier decision adequately motivated (edge for p95 < 100ms globally; Cloudflare Workers named with latency SLO). Per-technology ADRs within a well-motivated tier not required. |
| ARCH-013 | Yes | Rate-limiting section declares Redis sliding window for link creation (60/min/user), login lockout (5 attempts/15min/email), and Cloudflare WAF per-IP rules (1000 req/s) for redirect. |
| ARCH-014 | Yes | Caching section declares Cloudflare regional cache for `short_code → destination_url` (5-min TTL, purge-on-delete), and explicitly states no application-layer cache in v1 with a stated revisit condition. |
| ARCH-015 | Yes | Environments table lists `dev` (Docker Compose), `staging` (same shape as prod, smaller capacity), and `prod` (us-east-1). |
| ARCH-016 | Yes | CI/CD section declares GitHub Actions, per-PR gates (Mypy, tsc, Ruff, ESLint, unit+integration tests, OpenAPI diff, Alembic check), trunk-based deployment, automatic staging deploy, manual-approval prod promotion. |
| ARCH-017 | Yes | Architecture names explicit failure modes for: SES failure, Pwned Passwords timeout (fail-open), Google Safe Browsing timeout (fail-open), click pipeline unavailability (local durable buffering). Failure-mode scaffolding present. |
| ARCH-018 | Yes | Frontend/backend contract section declares: REST/HTTPS/JSON, FastAPI OpenAPI as schema source-of-truth, `openapi-typescript` type generation, session cookie with `credentials: 'include'`, CSRF double-submit, JSON error envelope shape. |
| ARCH-021 | Yes | Auth section explicitly declares: HTTP-only, Secure, SameSite=Lax cookies, 30-day absolute, 7-day idle. Matches PRD Account section verbatim. |
| ARCH-032 | Yes | Observability section declares `request_id` on every log line, AWS X-Ray distributed tracing, and "Trace context is propagated from edge → SQS → consumer via the `X-Amzn-Trace-Id` message attribute." All three propagation requirements met. |

---

## JSON findings

```json
[
  {
    "domain": "architecture-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ARCH-019",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "The architecture does not declare a CORS allowlist policy. The dashboard origin makes fetch requests with credentials: 'include' to the FastAPI Link API. Without an explicit allowed-origins list, CORS configuration is left ad hoc. Wildcard CORS with credentials contradicts the CSRF double-submit scheme declared in the frontend/backend contract section.",
    "fix": "Add a CORS policy subsection: (1) production allowed-origins list; (2) allowed HTTP methods; (3) Access-Control-Allow-Credentials: true; (4) enforcement layer (FastAPI CORSMiddleware or ALB).",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ARCH-020",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "No HTTP security headers strategy declared. PRD NFR requires CSRF protection and OWASP Top-10 baseline but architecture does not name where CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy are emitted or their canonical values.",
    "fix": "Add an HTTP security headers section: which headers are emitted, production values, where each is applied (Cloudflare Transform Rules, ALB response headers policy, or Next.js headers() config), and dev-environment overrides.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ARCH-022",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "No API versioning scheme or deprecation policy declared. FastAPI generates OpenAPI docs consumed by openapi-typescript but there is no statement of whether the API uses a /v1/ prefix, guarantees backward-compatibility, or has a sunset mechanism. The dashboard client is already a consumer that will break on unversioned breaking changes.",
    "fix": "Add an API versioning subsection declaring the scheme and deprecation policy. Even a 'no versioning — breaking changes require coordinated dashboard deploy' statement is acceptable if explicit.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ARCH-023",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "No health check endpoints declared. ECS Fargate services and the ALB require health checks to route traffic and replace unhealthy tasks, but endpoint paths, what each checks, dependency-check timeout, and orchestrator configuration are all absent.",
    "fix": "Add a health check section: endpoint names, what each signals (liveness = process responds; readiness = process + DB primary + Redis reachable), per-dependency timeout, and ALB / ECS health check configuration.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ARCH-024",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "No request body or payload size limits declared. No default JSON body cap, enforcement layer, or per-endpoint exceptions stated. An unbounded body limit is a denial-of-service primitive against the Link API.",
    "fix": "Declare the default JSON body limit (e.g. 1 MB), where it is enforced (ALB request size limit, FastAPI middleware), and whether Cloudflare WAF has a request-size rule on the redirect Worker.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ARCH-025",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "No input validation or DTO boundary policy declared. No statement that all request bodies use Pydantic schemas, that responses use explicit response_model projections, or the policy for partial-update schemas. Absence leaves the door open for mass-assignment vulnerabilities.",
    "fix": "Add an input validation policy statement: e.g. 'All request bodies are declared as Pydantic BaseModel subclasses; ORM objects are never returned directly; responses use explicit response_model schemas; partial updates use dedicated Update<X> schemas.'",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "gate": 2,
    "severity": "blocker",
    "rule": "ARCH-026",
    "file": "docs/architecture.md",
    "line": 151,
    "snippet": "Every 4xx/5xx response is JSON: { \"error\": { \"code\": \"<machine-code>\", \"message\": \"<human>\" } }.",
    "message": "Error envelope shape declared in frontend/backend contract section, but the global exception handler, stack-trace policy, and exception-to-status-code mapping are absent. An unhandled FastAPI exception will return a 500 with a framework-generated body that does not match the declared envelope.",
    "fix": "Add a global exception handling subsection: (1) catch-all middleware wrapping every unhandled exception in the declared envelope; (2) stack-trace policy (never in prod responses; always forwarded to Sentry and CloudWatch); (3) exception-to-status-code mapping.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ARCH-028",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "No DB connection pool strategy declared. Scaling section notes ECS autoscales to 200 RPS sustained / 1000 RPS burst but no per-task pool_size, max_overflow, or sizing math against Postgres max_connections is stated. At burst scale, an uncontrolled pool will exhaust connection slots.",
    "fix": "Add a connection pool subsection: state per-task pool_size and max_overflow values, compute total potential connections (max ECS task count × (pool_size + max_overflow)) against DB max_connections minus admin reserve, and name the pool-leak detection mechanism.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ARCH-029",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "SQS consumer retry idempotency is addressed but no idempotency policy declared for mutating API endpoints. If an ALB or client retries a timed-out POST to /links, a second link is created with a different short code.",
    "fix": "Declare an idempotency policy: either Idempotency-Key header on POST/PUT/PATCH with Redis-backed replay, or explicitly enumerate which endpoints are naturally idempotent vs. which accept duplicate semantics by PRD definition.",
    "effort": "medium"
  },
  {
    "domain": "architecture-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ARCH-030",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "No pagination scheme declared. PRD mandates 50-items-per-page link list; CLICK table is append-only and unbounded. No cursor vs offset decision, default/max page size, or cursor parameter name stated.",
    "fix": "Add a pagination policy statement: pagination scheme (cursor-based recommended for CLICK analytics), default page size (50 per PRD), maximum page size, and query parameter name.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ARCH-031",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "Multi-step writes described (link create + ABUSE_REVIEW insert + Mixpanel enqueue; member removal + link owner_id reassignment + invite cancellation) but no transaction boundary or unit-of-work pattern declared. Without this, partial-write states will occur.",
    "fix": "Add a transaction boundary section: declare the unit-of-work pattern and explicitly state whether SQS publishes are inside the transaction (transactional outbox) or after commit.",
    "effort": "medium"
  },
  {
    "domain": "architecture-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ARCH-033",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "No graceful shutdown strategy declared for ECS Fargate services and SQS consumers. Without an explicit SIGTERM handler, task replacement on deploys abruptly terminates in-flight requests and in-flight SQS message processing.",
    "fix": "Add a graceful shutdown subsection: SIGTERM handler sequence for HTTP services (drain in-flight requests, e.g. 30s), consumer draining sequence (finish current message batch), and ECS stopTimeout value.",
    "effort": "low"
  },
  {
    "domain": "architecture-review",
    "gate": 3,
    "severity": "warning",
    "rule": "ARCH-034",
    "file": "docs/architecture.md",
    "line": 0,
    "snippet": "",
    "message": "No payload compression strategy declared. Link-list and analytics time-series responses grow with workspace activity. PRD requires dashboard initial-render p95 < 2s on 4G — uncompressed payloads are a material contributor to that budget.",
    "fix": "Declare where compression is applied (Cloudflare, ALB, or FastAPI GZipMiddleware), the minimum response-size threshold, and whether Brotli is preferred over gzip where supported.",
    "effort": "low"
  }
]
```

## Domain summary

```json
{
  "domain": "architecture-review",
  "gate1_count": 0,
  "gate2_count": 7,
  "gate3_count": 7,
  "verdict": "FAIL_BLOCKER"
}
```

---

## Notes

The architecture document is substantively strong at the structural level. Gate 1 is entirely clean: auth/authz, secrets management, backup/recovery, compliance posture, and PRD contradiction checks all pass. The tier decomposition (edge / regional / async), multi-tenant enforcement, external-integration resilience, observability stack, migration strategy, environment topology, CI/CD pipeline, and frontend/backend contract are all adequately declared.

The seven Gate 2 blockers are concentrated in a single theme: **the security-posture and API-contract surface area is declared at the structural level but not at the policy level**. CORS, HTTP security headers, API versioning, health check endpoints, body-size limits, input validation, and the global exception handler are all standard FastAPI/ALB concerns that are absent from the document. None require architectural rework — they are additive policy declarations (`effort: low` for six of seven). Because they are absent at architecture stage, the corresponding be-* code reviewers (`SEC-BE-008`, `SEC-BE-012`, `API-BE-005`, `REL-BE-001`, `RT-BE-011`, `RT-BE-003`, `REL-BE-002`) have no stated policy to verify against.

The seven Gate 3 warnings are similarly additive: connection pool sizing math, idempotency policy for write endpoints, pagination scheme, transaction boundaries for multi-step writes, graceful shutdown draining, and payload compression are all declarable in one to two paragraphs each without changing any service boundary or storage choice.
