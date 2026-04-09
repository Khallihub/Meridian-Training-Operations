# Meridian Training Operations System - Static Delivery Acceptance & Architecture Audit
Date: 2026-04-08
Reviewer Mode: Static-only (no runtime execution)

## 1. Verdict
- Overall conclusion: **Fail**
- Primary reason: Material security and delivery defects were found (authorization gaps, schema/migration drift affecting required flows, and core export/data-quality issues), with insufficient test coverage for these high-risk areas.

## 2. Scope and Static Verification Boundary
- What was reviewed:
  - Documentation and manifests: `README.md`, `docker-compose.yml`, `backend/.env.example`, backend/frontend Dockerfiles, Nginx and Prometheus configs.
  - Backend architecture: FastAPI entrypoints, route registration, auth/deps/security, modules for sessions/bookings/replays/checkout/payments/search/ingestion/jobs/monitoring/audit, SQLAlchemy models, Alembic migrations.
  - Frontend architecture: Vue router/guards, stores, API client/endpoints, role pages, key components (calendar/search/checkout/live room).
  - Tests (static): backend unit/API tests and frontend Vitest specs.
- What was not reviewed:
  - Runtime behavior under real environment conditions (network, DB, Redis, Kafka, MinIO, Celery worker/beat, browser interactions, WebSocket runtime behavior, Docker runtime).
- What was intentionally not executed:
  - Project startup, Docker, tests, migrations, external services.
- Claims requiring manual verification:
  - End-to-end runtime flows (terminal callback delivery timing, scheduler timing at 2:00 AM, alert firing under live workload, CDC/Kafka/Logstash/Flume connectivity in real infrastructure).

## 3. Repository / Requirement Mapping Summary
- Prompt core goals mapped:
  - Multi-role training operations platform (admin/instructor/learner/finance/dataops), scheduling/calendar, booking lifecycle, live/replay access, offline checkout/promotions, operational search/export, payments/refunds/reconciliation, scheduler/alerts, ingestion pipelines.
- Main implementation areas matched:
  - Backend modules reflect required domains (`sessions`, `bookings`, `replays`, `checkout`, `payments`, `search`, `ingestion`, `jobs`, `monitoring`, `audit`) and are registered in API entrypoint (`backend/app/main.py:52`).
  - Frontend has role-routed pages and domain stores wired to API endpoints (`frontend/src/router/index.ts:76`, `frontend/src/stores/checkout.ts:34`, `frontend/src/stores/ingestion.ts:26`, `frontend/src/api/endpoints/search.ts:5`).
- Core mismatch summary:
  - Required features are broadly present, but critical defects exist in authorization, migration/schema consistency, and export correctness.

## 4. Section-by-section Review

### 1. Hard Gates
#### 1.1 Documentation and static verifiability
- Conclusion: **Partial Pass**
- Rationale:
  - Startup and verification instructions exist (`README.md:5`, `README.md:24`, `README.md:55`) and project entrypoints/manifests are statically coherent (`backend/app/main.py:14`, `docker-compose.yml:120`).
  - However, docs are backend-centric and include consistency/security concerns: default-admin guidance conflicts with production compose defaults (`README.md:31`, `docker-compose.yml:17`, `backend/docker-entrypoint.sh:14`), and frontend test/run guidance is not explicitly documented.
- Evidence:
  - `README.md:5`, `README.md:31`, `README.md:55`
  - `docker-compose.yml:17`, `docker-compose.yml:120`
  - `backend/docker-entrypoint.sh:14`
- Manual verification note:
  - Manual environment bring-up still required to validate actual operability.

#### 1.2 Material deviation from Prompt
- Conclusion: **Partial Pass**
- Rationale:
  - Implementation is aligned to prompt domains and user roles (`backend/app/main.py:52`, `frontend/src/router/index.ts:76`).
  - Material deviations: explicit Flume support in prompt is compromised by migration enum mismatch (model/UI allow flume, DB migration enum does not), and configurable policy management by administrator is not implemented (critical policy windows are hardcoded).
- Evidence:
  - `backend/app/modules/ingestion/models.py:12`
  - `frontend/src/pages/dataops/IngestionSourceFormPage.vue:65`
  - `backend/alembic/versions/0001_initial_schema.py:324`
  - `backend/app/modules/bookings/service.py:75`
- Manual verification note:
  - None.

### 2. Delivery Completeness
#### 2.1 Coverage of explicit core prompt requirements
- Conclusion: **Partial Pass**
- Rationale:
  - Covered statically: scheduling/week-month endpoints, recurring sessions, capacity/buffer fields, booking transitions, replay rules, promotions, search/export limits, payment/refund/reconciliation/job/ingestion modules.
  - Not fully covered due material defects: flume path broken by schema mismatch; search export column mapping mismatch; several security boundaries are too weak for production-grade acceptance.
- Evidence:
  - Scheduling/recurrence/buffer: `backend/app/modules/sessions/schemas.py:22`, `backend/app/modules/sessions/service.py:71`
  - Booking flow/policy windows: `backend/app/modules/bookings/models.py:12`, `backend/app/modules/bookings/service.py:75`, `backend/app/modules/bookings/service.py:120`
  - Replay rules: `backend/app/modules/replays/service.py:30`
  - Search/export limit: `backend/app/modules/search/service.py:277`
  - Payments/reconciliation: `backend/app/modules/payments/service.py:240`, `backend/app/modules/jobs/celery_app.py:39`
  - Ingestion enum mismatch: `backend/app/modules/ingestion/models.py:15`, `backend/alembic/versions/0001_initial_schema.py:324`
- Manual verification note:
  - Runtime behavior for integrations and scheduled operations remains manual.

#### 2.2 End-to-end deliverable vs partial/demo
- Conclusion: **Pass**
- Rationale:
  - Full multi-module backend + frontend + infra manifests are present, not a single-file/demo scaffold.
  - Both API and UI are structured with role pages and domain modules.
- Evidence:
  - `backend/app/main.py:52`
  - `frontend/src/router/index.ts:63`
  - `docker-compose.yml:25`

### 3. Engineering and Architecture Quality
#### 3.1 Structure and module decomposition
- Conclusion: **Pass**
- Rationale:
  - Domain-based decomposition is clear and appropriately segmented across backend modules and frontend pages/stores.
- Evidence:
  - `backend/app/main.py:52`
  - `backend/app/modules/bookings/service.py:19`
  - `backend/app/modules/payments/service.py:38`
  - `frontend/src/router/index.ts:76`
  - `frontend/src/pages/learner/SessionBrowsePage.vue:57`
  - `frontend/src/stores/search.ts:46`
  - `backend/app/main.py:52`

#### 3.2 Maintainability and extensibility
- Conclusion: **Partial Pass**
- Rationale:
  - Architecture is extensible overall, but maintainability is reduced by model/migration drift and enum drift between backend and frontend.
- Evidence:
  - Order status drift: `backend/app/modules/checkout/models.py:17` vs `backend/alembic/versions/0001_initial_schema.py:228`
  - Ingestion type drift: `backend/app/modules/ingestion/models.py:15` vs `backend/alembic/versions/0001_initial_schema.py:324`
  - Frontend type drift: `frontend/src/stores/ingestion.ts:8`, `frontend/src/stores/ingestion.ts:22`

### 4. Engineering Details and Professionalism
#### 4.1 Error handling, logging, validation, API design
- Conclusion: **Partial Pass**
- Rationale:
  - Positive: centralized exception mapping exists; logging exists in core jobs/audit/ws paths.
  - Negative: critical validation and security controls are incomplete (e.g., order endpoint auth scope, callback idempotency/replay defenses, export field mapping correctness, hardcoded policy rules).
- Evidence:
  - Exceptions: `backend/app/core/exceptions.py:52`
  - Logging: `backend/app/modules/jobs/tasks.py:13`, `backend/app/core/audit.py:49`
  - Auth gap: `backend/app/modules/checkout/controller.py:45`, `backend/app/modules/checkout/service.py:134`
  - Callback replay/idempotency gap: `backend/app/modules/payments/service.py:27`, `backend/app/modules/payments/service.py:42`
  - Export mapping defect: `backend/app/modules/search/service.py:77`, `backend/app/modules/search/service.py:283`

#### 4.2 Real product/service shape vs demo
- Conclusion: **Partial Pass**
- Rationale:
  - Product-like structure is present, but material defects prevent acceptance as professional-grade delivery.
- Evidence:
  - Product shape: `docker-compose.yml:25`, `frontend/src/router/index.ts:76`, `backend/app/main.py:52`
  - Blocking defects (listed in Issues section).

### 5. Prompt Understanding and Requirement Fit
#### 5.1 Business goal and constraint fit
- Conclusion: **Partial Pass**
- Rationale:
  - The solution clearly targets the requested business scenario and role workflows.
  - Key prompt constraints are weakened by defects: missing robust Flume support due schema mismatch, policy configurability absent, and security controls insufficient for sensitive finance/order operations.
- Evidence:
  - Role map: `frontend/src/router/index.ts:55`
  - Flume mismatch: `frontend/src/pages/dataops/IngestionSourceFormPage.vue:65`, `backend/alembic/versions/0001_initial_schema.py:324`
  - Hardcoded policy windows: `backend/app/modules/bookings/service.py:75`, `backend/app/modules/bookings/service.py:120`
  - Finance/order auth issue: `backend/app/modules/checkout/controller.py:45`, `backend/app/modules/checkout/service.py:134`

### 6. Aesthetics (Frontend)
#### 6.1 Visual/interaction quality and consistency
- Conclusion: **Partial Pass**
- Rationale:
  - Layout hierarchy, spacing, and role navigation are generally coherent.
  - Multiple UI text artifacts/encoding glitches and control-character render risks reduce professional finish and can degrade interaction clarity.
- Evidence:
  - Corrupted/garbled text markers: `frontend/src/pages/sessions/SessionDetailPage.vue:53`, `frontend/src/pages/sessions/SessionDetailPage.vue:178`, `frontend/src/pages/sessions/SessionDetailPage.vue:351`
  - Control chars in table sort indicator: `frontend/src/components/tables/DataTable.vue:56`
  - Corrupted symbols in monitor page: `frontend/src/pages/jobs/JobMonitorPage.vue:90`

## 5. Issues / Suggestions (Severity-Rated)

### Blocker
1. **Flume ingestion declared but DB schema cannot store it**
- Severity: **Blocker**
- Conclusion: Prompt-required Flume source type is not deliverable with migration-based schema.
- Evidence:
  - Model/UI accept flume: `backend/app/modules/ingestion/models.py:15`, `frontend/src/pages/dataops/IngestionSourceFormPage.vue:65`
  - Migration enum omits flume: `backend/alembic/versions/0001_initial_schema.py:324`
- Impact:
  - Creating `flume` sources can fail at persistence layer in migration-driven deployments.
- Minimum actionable fix:
  - Add Alembic migration to alter `ingestionsourcetype` enum and include `flume`; add regression test that creates flume source against migrated schema.

### High
2. **Order endpoints expose object access/cancel beyond intended roles**
- Severity: **High**
- Conclusion: `GET /orders/{id}` and `PATCH /orders/{id}/cancel` allow any authenticated non-learner role (e.g., instructor/dataops) to access/cancel arbitrary orders.
- Evidence:
  - Route lacks role guard: `backend/app/modules/checkout/controller.py:45`, `backend/app/modules/checkout/controller.py:50`
  - Service only restricts learner role: `backend/app/modules/checkout/service.py:134`, `backend/app/modules/checkout/service.py:185`
- Impact:
  - Unauthorized financial/order manipulation risk.
- Minimum actionable fix:
  - Enforce `require_roles("admin", "finance", "learner")` on these routes and keep learner ownership checks in service.

3. **Payment callback lacks replay/idempotency protections**
- Severity: **High**
- Conclusion: Callback verifies HMAC but does not enforce timestamp freshness, nonce, or processed-event idempotency.
- Evidence:
  - Signature logic only: `backend/app/modules/payments/service.py:27`
  - Callback processing always re-applies side effects: `backend/app/modules/payments/service.py:42`
- Impact:
  - Replay/duplicate callbacks can repeatedly mutate order/payment state and trigger inconsistent booking/refund review outcomes.
- Minimum actionable fix:
  - Enforce timestamp tolerance + nonce/event-id store; short-circuit if payment/order already terminally processed.

4. **Order status enum drift (`needs_review`) between model and migration**
- Severity: **High**
- Conclusion: Code can assign `OrderStatus.needs_review`, but Alembic enum does not include it.
- Evidence:
  - Model includes value: `backend/app/modules/checkout/models.py:17`
  - Service writes value: `backend/app/modules/payments/service.py:103`
  - Migration enum missing value: `backend/alembic/versions/0001_initial_schema.py:228`
- Impact:
  - Runtime DB errors when conflict path attempts to set `needs_review`.
- Minimum actionable fix:
  - Add migration to alter `orderstatus` enum and align tests to migration schema.

5. **Capacity rule can be violated at confirmation stage**
- Severity: **High**
- Conclusion: Capacity checked at booking request, but confirmation increments enrollment without re-check/locking.
- Evidence:
  - Request-time check: `backend/app/modules/bookings/service.py:30`
  - Confirm path increments without capacity guard: `backend/app/modules/bookings/service.py:55`
- Impact:
  - Overbooking risk under concurrent confirmations.
- Minimum actionable fix:
  - Re-check capacity atomically on confirmation (transactional lock/constraint) and return `409` when full.

6. **Search export schema mapping produces incorrect/blank columns**
- Severity: **High**
- Conclusion: Export headers do not match selected column aliases.
- Evidence:
  - Query labels: `status`, `session_date`, `session_title` in `backend/app/modules/search/service.py:77`, `backend/app/modules/search/service.py:80`, `backend/app/modules/search/service.py:81`
  - Export headers use `enrollment_status`, `session_start`, `course_title`: `backend/app/modules/search/service.py:283`
- Impact:
  - CSV/Excel exports can omit critical values despite available source data.
- Minimum actionable fix:
  - Align header keys with query aliases or map row fields explicitly before writing.

7. **Administrator policy configurability is not implemented (hardcoded policy windows)**
- Severity: **High**
- Conclusion: Prompt requires administrator policy setting, but reschedule/cancel policy windows are hardcoded in service logic.
- Evidence:
  - Hardcoded 2-hour block: `backend/app/modules/bookings/service.py:75`
  - Hardcoded 24-hour fee flag: `backend/app/modules/bookings/service.py:120`
  - No policy route in role navigation: `frontend/src/router/index.ts:76`
- Impact:
  - Core business policy cannot be configured by admins as required.
- Minimum actionable fix:
  - Introduce policy configuration model/API/UI and replace literals with configurable values.

### Medium
8. **Refund amount validation allows non-positive values**
- Severity: **Medium**
- Conclusion: Refund amount has no lower-bound validation.
- Evidence:
  - Schema: `backend/app/modules/payments/schemas.py:31`
  - Service only checks upper bound: `backend/app/modules/payments/service.py:170`
- Impact:
  - Invalid negative/zero refunds can enter ledger workflows.
- Minimum actionable fix:
  - Add `gt=0` validation in schema and enforce service-level guard.

9. **Frontend/backend enum/type drift (status/type strings) increases runtime inconsistency risk**
- Severity: **Medium**
- Conclusion: Frontend types differ from backend enums (`failed` vs `failure`, missing `flume`, missing `needs_review`).
- Evidence:
  - Frontend ingestion type/status unions: `frontend/src/stores/ingestion.ts:8`, `frontend/src/stores/ingestion.ts:22`
  - Backend ingestion/order enums: `backend/app/modules/ingestion/models.py:15`, `backend/app/modules/checkout/models.py:17`
- Impact:
  - Incorrect UI badges/logic and weaker type safety for key states.
- Minimum actionable fix:
  - Generate shared API types from OpenAPI or manually align unions to backend enums.

10. **UI text/encoding artifacts degrade production UX clarity**
- Severity: **Medium**
- Conclusion: Multiple pages/components contain mojibake/control characters in user-facing text.
- Evidence:
  - `frontend/src/pages/sessions/SessionDetailPage.vue:178`
  - `frontend/src/pages/jobs/JobMonitorPage.vue:90`
  - `frontend/src/components/tables/DataTable.vue:56`
- Impact:
  - Reduced readability and perceived quality; potential confusion in critical pages.
- Minimum actionable fix:
  - Normalize file encodings to UTF-8 and replace corrupted glyphs with explicit symbols/text.

11. **Documentation consistency gap on default admin flow**
- Severity: **Medium**
- Conclusion: README suggests default admin login while compose defaults run `APP_ENV=production`, which skips admin seeding.
- Evidence:
  - Default admin instructions: `README.md:31`, `README.md:41`
  - Production env in compose: `docker-compose.yml:17`
  - Seed skip in production: `backend/docker-entrypoint.sh:14`, `backend/docker-entrypoint.sh:42`
- Impact:
  - Reviewer/operator confusion and failed first-login expectation.
- Minimum actionable fix:
  - Align README with entrypoint behavior and provide explicit admin bootstrap steps.

## 6. Security Review Summary

### Authentication Entry Points
- Conclusion: **Pass**
- Evidence & reasoning:
  - Username/password login, refresh, logout, change-password are implemented with complexity and lockout controls (`backend/app/modules/auth/controller.py:12`, `backend/app/core/security.py:27`, `backend/app/modules/auth/service.py:35`).

### Route-level Authorization
- Conclusion: **Partial Pass**
- Evidence & reasoning:
  - Most protected routes use `require_roles` (`backend/app/modules/payments/controller.py:18`, `backend/app/modules/ingestion/controller.py:19`).
  - Material gap on order-by-id and cancel routes (`backend/app/modules/checkout/controller.py:45`, `backend/app/modules/checkout/controller.py:50`).
  - Public callback/webhook endpoints are intentional but require stronger anti-replay and robust key hygiene (`backend/app/modules/payments/controller.py:29`, `backend/app/modules/ingestion/controller.py:71`).

### Object-level Authorization
- Conclusion: **Fail**
- Evidence & reasoning:
  - Learner ownership checks are present in several services (e.g., bookings/orders for learner), but non-learner order access is over-broad (`backend/app/modules/checkout/service.py:134`).
  - Instructor ownership boundaries for session-mutating actions are not enforced in service (role-only gating) (`backend/app/modules/sessions/controller.py:64`, `backend/app/modules/sessions/service.py:148`).

### Function-level Authorization
- Conclusion: **Partial Pass**
- Evidence & reasoning:
  - Business services rely primarily on controller role checks; where controllers are permissive, service-level defenses are insufficient for some operations (`backend/app/modules/checkout/controller.py:45`, `backend/app/modules/checkout/service.py:134`).

### Tenant / User Data Isolation
- Conclusion: **Partial Pass**
- Evidence & reasoning:
  - User-level isolation exists for learner-owned bookings/orders in many flows (`backend/app/modules/bookings/service.py:69`, `backend/app/modules/checkout/service.py:134`).
  - No explicit tenant model/tenant-scoped constraints were found; multi-tenant isolation cannot be confirmed statically because architecture appears single-tenant by design.

### Admin / Internal / Debug Endpoint Protection
- Conclusion: **Partial Pass**
- Evidence & reasoning:
  - Admin/internal endpoints (jobs/alerts/metrics/audit) are role-protected (`backend/app/modules/jobs/controller.py:21`, `backend/app/modules/monitoring/controller.py:21`, `backend/app/modules/audit/controller.py:41`).
  - Public health and callback/webhook endpoints exist by design; callback hardening remains insufficient (`backend/app/modules/monitoring/controller.py:15`, `backend/app/modules/payments/controller.py:29`).

## 7. Tests and Logging Review

### Unit Tests
- Conclusion: **Partial Pass**
- Rationale:
  - Useful unit tests exist for security/encryption/booking state/best-offer.
  - Do not cover migration compatibility, authorization edge cases, or export-field integrity.
- Evidence:
  - `backend/tests/unit/test_security.py:13`
  - `backend/tests/unit/test_booking_state.py:35`
  - `backend/tests/unit/test_best_offer.py:35`

### API / Integration Tests
- Conclusion: **Fail**
- Rationale:
  - Some API coverage exists for auth/sessions/checkout/payment callback/monitoring.
  - High-risk endpoints and scenarios (order auth boundaries, ingestion flows, export correctness, callback replay/idempotency, enum migration drift) are not covered.
- Evidence:
  - Existing scope: `backend/tests/api/test_auth.py:10`, `backend/tests/api/test_checkout.py:40`, `backend/tests/api/test_payments.py:14`
  - Search of tests shows only callback payment endpoint hits for payment module risk area: `backend/tests/api/test_payments.py:37`, `backend/tests/api/test_payments.py:61`

### Logging Categories / Observability
- Conclusion: **Partial Pass**
- Rationale:
  - Meaningful categories exist for job lifecycle, alerts, audit failures, and websocket subscriber failures.
  - Limited domain-level structured logging around critical authorization and export failure paths.
- Evidence:
  - `backend/app/modules/jobs/tasks.py:77`
  - `backend/app/modules/jobs/tasks.py:231`
  - `backend/app/core/audit.py:49`

### Sensitive-data leakage risk in logs / responses
- Conclusion: **Partial Pass**
- Rationale:
  - Phone/email are encrypted at rest and masked in most user/search responses.
  - Admin detail responses intentionally include unmasked values; this should be policy-confirmed and audit-traceable.
- Evidence:
  - Encryption/masking usage: `backend/app/modules/users/service.py:17`, `backend/app/modules/users/service.py:24`
  - Admin response includes unmasked fields: `backend/app/modules/users/service.py:31`

## 8. Test Coverage Assessment (Static Audit)

### 8.1 Test Overview
- Unit tests exist: **Yes** (`backend/tests/unit/test_security.py:1`, `backend/tests/unit/test_booking_state.py:1`, `frontend/src/tests/unit/stores/auth.spec.ts:1`).
- API/integration-like tests exist: **Yes** (`backend/tests/api/test_auth.py:1`, `backend/tests/api/test_checkout.py:1`, `backend/tests/conftest.py:12` via `httpx` ASGI test client).
- Frameworks:
  - Backend: `pytest`, `pytest-asyncio`, `httpx` (`backend/pyproject.toml:37`, `backend/tests/conftest.py:12`).
  - Frontend: `vitest`, `@vue/test-utils` (`frontend/package.json:10`, `frontend/package.json:40`).
- Test entry points:
  - Backend testpaths configured: `backend/pyproject.toml:47`.
  - Frontend test script: `frontend/package.json:10`.
- Documentation provides test commands:
  - Backend command documented in README: `README.md:55`.
  - Frontend test command not documented in README (only in `package.json`).

### 8.2 Coverage Mapping Table
| Requirement / Risk Point | Mapped Test Case(s) | Key Assertion / Fixture / Mock | Coverage Assessment | Gap | Minimum Test Addition |
|---|---|---|---|---|---|
| Auth login + lockout after 5 failures | `backend/tests/api/test_auth.py:29` | Expects `423` and `locked_until` (`backend/tests/api/test_auth.py:34`) | basically covered | No inactivity-timeout assertion | Add API test for inactivity expiry via Redis last_seen expiration path |
| Password complexity rules | `backend/tests/unit/test_security.py:13` | Invalid cases raise `ValueError` (`backend/tests/unit/test_security.py:18`) | sufficient | None major | Keep |
| Unauthenticated 401 on protected route | `backend/tests/api/test_auth.py:42` | `/api/users/me` returns 401 (`backend/tests/api/test_auth.py:44`) | basically covered | Sparse endpoint variety | Add representative 401 tests for finance/dataops endpoints |
| Route authorization (403 for wrong role) | No direct 403 role matrix tests found | N/A | insufficient | Role boundaries (orders/search/payments/jobs) could regress silently | Add parameterized role-matrix tests per critical endpoint |
| Order object-level authorization | No tests found | N/A | missing | Current auth flaw on order get/cancel not caught | Add tests proving instructor/dataops cannot access or cancel other users' orders |
| Booking reschedule 2-hour block | `backend/tests/unit/test_booking_state.py:37` | Expects `UnprocessableError` match "2 hours" (`backend/tests/unit/test_booking_state.py:49`) | sufficient | No API-level integration for role/ownership + boundary times | Add API tests at 1h59m and 2h01m edges |
| Learner cancel within 24h policy fee flag | `backend/tests/unit/test_booking_state.py:78` | `policy_fee_flagged is True` (`backend/tests/unit/test_booking_state.py:97`) | sufficient | Not validated at API response contract level | Add API test asserting flag in cancel response |
| Checkout best-offer + cart creation | `backend/tests/api/test_checkout.py:42` | Subtotal/discount/total assertions (`backend/tests/api/test_checkout.py:69`) | basically covered | No conflict/duplicate/capacity checkout scenarios | Add tests for mixed promotions, BOGO edge quantities, conflicting promos |
| Payment callback signature verification | `backend/tests/api/test_payments.py:16` and `:48` | Valid callback completes, invalid signature fails (`backend/tests/api/test_payments.py:45`, `:69`) | basically covered | No replay/idempotency/timestamp tolerance tests | Add duplicate-callback and stale-timestamp tests |
| Search export correctness + 50k cap | Frontend store test for disable flag: `frontend/src/tests/unit/stores/search.spec.ts:30` | UI flag over 50k (`frontend/src/tests/unit/stores/search.spec.ts:34`) | insufficient | Backend export field mapping bug untested | Add backend API test validating exported headers and row values |
| Ingestion source types incl. Flume | No backend API tests for ingestion | N/A | missing | Flume schema mismatch undetected | Add ingestion API tests for each source type against migrated schema |
| Job alerts/threshold logic | No tests for `check_job_health` thresholds | N/A | missing | >2% failure and lateness behavior unverified | Add unit/integration tests seeding `job_executions` and asserting alert creation |
| Security-sensitive logging leakage | No tests found | N/A | missing | Potential accidental leakage regressions undetected | Add tests asserting masked fields in responses/log payloads |

### 8.3 Security Coverage Audit
- Authentication tests: **Partial Pass**
  - Covered: login success/failure, lockout, protected endpoint 401.
  - Missing: inactivity-timeout behavior and refresh-token misuse edge cases.
- Route authorization tests: **Fail**
  - Missing broad role-matrix tests; severe route-scope defects can remain undetected.
- Object-level authorization tests: **Fail**
  - Missing tests for order ownership/access across roles.
- Tenant/data isolation tests: **Cannot Confirm Statistically**
  - No tenant model and no tenant-specific tests; user-level checks are only partially tested.
- Admin/internal protection tests: **Partial Pass**
  - Monitoring metrics auth tested; jobs/audit/admin surface lacks comprehensive negative-role tests.

### 8.4 Final Coverage Judgment
- **Fail**
- Boundary explanation:
  - Covered: selected auth, checkout best-offer basics, payment signature happy/negative path, some booking policy logic.
  - Uncovered critical risks: authorization boundary failures, callback replay/idempotency, migration/schema drift, ingestion path verification, export correctness. Current tests could pass while severe production defects remain.

## 9. Final Notes
- Audit conclusions are strictly static and evidence-based.
- Runtime assertions were intentionally avoided; all runtime-dependent outcomes are marked for manual verification.
- The highest-value remediation order is:
  1. Fix authorization and callback replay/idempotency.
  2. Resolve model/migration enum drift (`flume`, `needs_review`).
  3. Fix search export mapping and add regression tests.
  4. Implement configurable policy management for admin-defined booking windows.
