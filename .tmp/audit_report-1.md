# Meridian Training Operations — Static Delivery Acceptance & Architecture Audit

Date: 2026-04-13  
Method: Static repository analysis only (no runtime execution, no tests run, no code changes)

## 1) Verdict

**Overall Verdict: Partial Pass (Not Production-Acceptable Yet)**

The repository implements most core domains and has substantial backend/frontend/test coverage, but there are **Blocker/High** deviations from the PRD/security contract that prevent acceptance as-is.

Top risks (Blocker/High):
- **Blocker**: Password hashing does not meet PRD-required Argon2id (bcrypt is used).
- **High**: Search endpoint lacks role-scope filtering for instructors/finance (potential overexposure).
- **High**: Sensitive unmask controls (permission + reason + audit) are not implemented; admin responses include unmasked PII by default.
- **High**: PRD-mandated callback idempotency by `external_event_id` is not implemented in API/schema/model.
- **High**: Promotion tie-break determinism (`discount DESC`, `priority ASC`, `promotion_id ASC`) is not fully implemented.

## 2) Scope and Static Verification Boundary

- Static-only review of backend, frontend, migrations, tests, and infra config.
- No runtime validation performed (no app startup, Docker, or test execution).
- Any runtime behavior claims are marked as **Cannot Confirm Statistically** or **Manual Verification Required**.

Boundary statements:
- Job execution reliability under restart/failure, scheduler clock behavior, and performance SLOs: **Manual Verification Required**.
- End-to-end user journey success in a running stack: **Cannot Confirm Statistically**.

## 3) Repository / Requirement Mapping Summary

Prompt/PRD domains are materially represented in code:
- API composition and modules wired in `backend/app/main.py:52`.
- Core domains present (auth/users/locations/courses/instructors/sessions/bookings/attendance/replays/promotions/checkout/payments/search/ingestion/jobs/monitoring/audit/policy) via router registration in `backend/app/main.py:53`.
- Frontend role-based route surface present in `frontend/src/router/index.ts:56`.
- Background jobs and scheduler implemented in `backend/app/modules/jobs/tasks.py:52` and `backend/app/modules/jobs/celery_app.py:22`.

Primary PRD/security drift points are concentrated in crypto/auth contract, ABAC scope enforcement depth, and strict deterministic/idempotency requirements.

## 4) Section-by-section Review

### Section A — Scheduling, Booking, Attendance, Replay

Status: **Partial Pass**

What is implemented:
- Recurring session creation exists using RRULE expansion in `backend/app/modules/sessions/service.py:82`.
- Capacity checks and booking non-bookable guard exist in `backend/app/modules/bookings/service.py:35` and `backend/app/modules/bookings/service.py:32`.
- Policy windows (reschedule/cancel) are enforced in `backend/app/modules/bookings/service.py:92` and `backend/app/modules/bookings/service.py:139`.
- Replay access checks (enrollment/time window/instructor ownership) exist in `backend/app/modules/replays/service.py:30`.

Gaps:
- Instructor overlap prevention is not explicit; room overlap is checked in `backend/app/modules/sessions/service.py:43`, but no symmetric instructor-overlap query is present.
- Recurrence horizon defaults to 365 days when no end date is supplied (`backend/app/modules/sessions/service.py:96`), differing from PRD’s 180-day bounded horizon.

### Section B — Checkout, Promotions, Payments, Refunds

Status: **Partial Pass**

What is implemented:
- Best-offer engine and traceability are present in `backend/app/modules/checkout/best_offer.py:89` and persisted to order promotions in `backend/app/modules/checkout/service.py:79`.
- Callback signature verification exists (`backend/app/modules/payments/service.py:27`).
- Refund lifecycle transitions are implemented in `backend/app/modules/payments/service.py:232`.
- Auto-close unpaid orders job exists in `backend/app/modules/jobs/tasks.py:52`.

Gaps:
- PRD/API requirement for callback idempotency keyed by `external_event_id` is absent; payload has no such field in `backend/app/modules/payments/schemas.py:9`, and model has no persistent key column in `backend/app/modules/payments/models.py:29`.
- Current callback dedup uses Redis TTL key (`backend/app/modules/payments/service.py:137`), which is weaker than durable unique event ID semantics.
- Promotion deterministic tie-break ordering is incomplete (no explicit priority/ID tie-break in engine loops, e.g., `backend/app/modules/checkout/best_offer.py:145`).

### Section C — Search, Saved Searches, Exports, Reporting

Status: **Partial Pass**

What is implemented:
- Combined filtering and pagination exist in `backend/app/modules/search/service.py:151`.
- Saved search cap (20/user) enforced in `backend/app/modules/search/service.py:311`.
- Export row cap (50,000) enforced in `backend/app/modules/search/service.py:277`.

Gaps:
- Auth-scope filtering before ranking is not enforced in service; endpoint accepts instructor/finance/admin (`backend/app/modules/search/controller.py:21`) but does not pass caller scope into query construction (`backend/app/modules/search/service.py:151`).
- Export implemented as immediate binary response (`backend/app/modules/search/controller.py:42`) rather than asynchronous export-job contract.

### Section D — Jobs, Retry, Alerts, Monitoring

Status: **Partial Pass**

What is implemented:
- Celery beat schedule covers order closure, rollups, reconciliation, ingestion, health checks in `backend/app/modules/jobs/celery_app.py:22`.
- Exponential retry patterns appear in tasks (`backend/app/modules/jobs/tasks.py:63`).
- Alert creation for failure-rate and lateness exists in `backend/app/modules/jobs/tasks.py:224` and `backend/app/modules/jobs/tasks.py:259`.
- Aggregate job stats endpoint exists in `backend/app/modules/jobs/controller.py:26`.

Gaps:
- Structured logs with correlation/request/job IDs are not implemented; logging is basic config (`backend/app/main.py:10`).
- Restart-safe requeue/resume logic for in-flight jobs is not evident in task/scheduler code: **Cannot Confirm Statistically**.

### Section E — Ingestion and Deterministic Dedup/Reprocessing

Status: **Partial Pass**

What is implemented:
- Source management + connectivity checks exist in `backend/app/modules/ingestion/service.py:71`.
- Source config encryption at rest exists in `backend/app/modules/ingestion/service.py:38`.
- Dedup via Redis `NX` keys exists in `backend/app/modules/ingestion/adapters/batch_adapter.py:34`.

Gaps:
- PRD fingerprint rule (`source_id + source_record_id + event_time + normalized payload signature`) is not explicitly implemented; current row hash is `md5(json.dumps(row, sort_keys=True))` in `backend/app/modules/ingestion/adapters/batch_adapter.py:22`.
- Deterministic reprocessing guarantees across restart/state persistence are **Manual Verification Required**.

### Section F — Security, Authorization, Audit, Data Governance

Status: **Fail**

What is implemented:
- JWT auth + role guards are present in `backend/app/core/deps.py:17` and `backend/app/core/deps.py:50`.
- Inactivity timeout checks exist in `backend/app/core/security.py:127`.
- Lockout policy logic exists in `backend/app/modules/auth/service.py:36`.
- Encryption/masking utilities exist in `backend/app/core/encryption.py:1` and `backend/app/core/masking.py:6`.

Failing criteria:
- Password hashing algorithm is bcrypt (`backend/app/core/security.py:11`) vs PRD-required Argon2id.
- Unmask policy and reasoned/audited access flow are not implemented; admin user responses expose unmasked fields by default (`backend/app/modules/users/controller.py:44`, `backend/app/modules/users/service.py:31`).
- Audit tamper-evidence chain/signed digest is not present (audit model contains no chain/hash fields in `backend/app/modules/audit/models.py:11`; write helper is insert-only without tamper chain in `backend/app/core/audit.py:36`).

## 5) Issues / Suggestions (Blocker/High first)

### Blocker

1. Password hashing non-compliant with PRD (Argon2id required)
- Evidence: bcrypt configured in `backend/app/core/security.py:11`.
- Risk: Fails explicit security baseline and acceptance contract.
- Suggestion: Migrate to Argon2id (`passlib[argon2]`), add migration strategy for existing hashes, and add tests covering hash upgrade path.


### High

2. Search endpoint lacks role-scope authorization filtering (ABAC gap)
- Evidence: endpoint allows instructor/finance/admin in `backend/app/modules/search/controller.py:21`; service query has no caller scope parameter/enforcement in `backend/app/modules/search/service.py:151`.
- Risk: Cross-user/site data exposure for non-admin users.
- Suggestion: Add mandatory server-side scope predicates (instructor-owned sessions, finance-limited domains, etc.) before ranking/filtering.

3. PII unmask control flow missing (permission + reason + audit)
- Evidence: admin user detail includes `email_unmasked`/`phone_unmasked` (`backend/app/modules/users/schemas.py:45`, `backend/app/modules/users/service.py:31`), with no explicit unmask permission/reason endpoint.
- Risk: Overbroad sensitive-data exposure and audit/compliance failure.
- Suggestion: Introduce explicit unmask endpoint requiring permission + reason; log audit event for every unmask attempt.

4. Payment callback idempotency not implemented per `external_event_id`
- Evidence: callback schema has no `external_event_id` in `backend/app/modules/payments/schemas.py:9`; model has no unique external-event field in `backend/app/modules/payments/models.py:29`; dedup uses transient Redis key in `backend/app/modules/payments/service.py:137`.
- Risk: Duplicate callback replay handling is non-durable and weaker than spec.
- Suggestion: Add `external_event_id` to payload + persistent unique index; keep Redis as optimization only.

5. Promotion deterministic tie-break incomplete
- Evidence: selection logic compares only discount amount (`backend/app/modules/checkout/best_offer.py:145`, `backend/app/modules/checkout/best_offer.py:157`), no explicit priority/ID tie-break; promo load query is unsorted in `backend/app/modules/checkout/service.py:56`.
- Risk: Non-deterministic outcomes under equal discounts.
- Suggestion: Apply explicit sort key `(discount DESC, priority ASC, promotion_id ASC)` and add tie-case unit tests.

6. Audit tamper-evidence not implemented
- Evidence: audit table fields in `backend/app/modules/audit/models.py:14` lack chain/signature fields; logger is plain insert in `backend/app/core/audit.py:36`.
- Risk: Fails explicit PRD tamper-evidence requirement.
- Suggestion: Add hash-chain or signed batch digest schema + verification job and tests.

## 6) Security Review Summary

### Auth entry points
- Implemented: `/auth/login`, `/auth/refresh`, `/auth/logout` with JWT and inactivity checks (`backend/app/core/deps.py:17`, `backend/app/modules/auth/service.py:61`).
- Finding: **Partial** due to hashing non-compliance (`backend/app/core/security.py:11`).

### Route-level authorization
- Implemented broadly via `require_roles` (`backend/app/core/deps.py:50`) and applied across controllers (example: `backend/app/modules/payments/controller.py:22`).
- Finding: **Pass (RBAC layer)**.

### Object-level authorization
- Implemented in several domains (booking/order ownership and instructor ownership), e.g., `backend/app/modules/bookings/service.py:168`, `backend/app/modules/checkout/service.py:139`, `backend/app/modules/sessions/service.py:32`.
- Finding: **Partial** (search scope gap remains high risk).

### Function-level authorization
- Sensitive transitions guarded (refund actions finance/admin, session live controls admin/instructor) in `backend/app/modules/payments/controller.py:65` and `backend/app/modules/sessions/controller.py:92`.
- Finding: **Partial Pass**.

### Tenant/user isolation
- Learner isolation tests exist (`backend/tests/api/test_authorization.py:214`).
- Finding: **Partial** due to potential cross-scope search exposure.

### Admin/internal/debug protections
- Monitoring metrics JWT-protected at `/monitoring/metrics` (`backend/app/modules/monitoring/controller.py:24`).
- Prometheus scrape uses static bearer token at `/monitoring/metrics/scrape` (`backend/app/modules/monitoring/controller.py:30`).
- Finding: **Partial** (static token is acceptable for local-first but requires strict secret management and rotation).

## 7) Tests and Logging Review

Tests (static presence):
- Backend auth/authorization/object-level coverage exists (`backend/tests/api/test_auth.py:10`, `backend/tests/api/test_authorization.py:69`, `backend/tests/api/test_websocket_admission.py:102`).
- Backend payments/refunds/ingestion/monitoring tests exist (`backend/tests/api/test_payments.py:14`, `backend/tests/api/test_refund_lifecycle.py:39`, `backend/tests/api/test_ingestion.py:31`, `backend/tests/api/test_monitoring.py:9`).
- Frontend store/component tests exist via Vitest (`frontend/src/tests/unit/stores/auth.spec.ts:23`, `frontend/src/tests/unit/stores/search.spec.ts:17`).

Logging:
- App uses standard Python logging setup (`backend/app/main.py:10`); audit write failures are logged (`backend/app/core/audit.py:49`).
- Structured logging with stable correlation/job IDs is not evident: **Partial / Manual Verification Required**.

## 8) Test Coverage Assessment

### Coverage Mapping Table

| Requirement Area | Evidence of Tests | Coverage Judgment | Gap Notes |
|---|---|---|---|
| Auth, lockout, role guard | `backend/tests/api/test_auth.py:10`, `backend/tests/unit/test_security.py:13` | Partial Pass | No evidence of username-substring password rejection test. |
| Object-level authorization | `backend/tests/api/test_authorization.py:141`, `backend/tests/api/test_websocket_admission.py:102` | Partial Pass | No explicit search-scope leakage test for instructor/finance. |
| Booking policy windows/states | `backend/tests/unit/test_booking_state.py:1`, `backend/tests/api/test_booking_non_bookable_session.py:1` | Partial Pass | No runtime E2E validation across UI + API. |
| Promotions best-offer | `backend/tests/unit/test_best_offer.py:35`, `backend/tests/api/test_checkout.py:1` | Partial Pass | No tie-break determinism tests (priority + ID). |
| Payments/refunds | `backend/tests/api/test_payments.py:14`, `backend/tests/api/test_refund_lifecycle.py:39` | Partial Pass | No `external_event_id` idempotency contract test (field absent). |
| Search/saved/export | `frontend/src/tests/unit/stores/search.spec.ts:17` | Partial Pass | Backend integration tests for search scope/filter correctness not evident. |
| Ingestion/dedup | `backend/tests/api/test_ingestion.py:73` | Partial Pass | Tests do not prove deterministic fingerprint contract/reprocessing invariants. |
| Monitoring/jobs | `backend/tests/api/test_monitoring.py:9` | Partial Pass | No static evidence of restart-resume/failure-injection tests. |
| Frontend role UX routes | `frontend/src/router/index.ts:139`, `frontend/src/tests/unit/stores/auth.spec.ts:23` | Partial Pass | No Playwright/Cypress E2E suite found in `frontend/package.json:32`. |

### Final Coverage Judgment

**Partial Pass**

Rationale:
- Critical domains have meaningful unit/API/component tests present.
- However, PRD-critical acceptance coverage is incomplete for deterministic tie-breaks, scoped search authorization, durable callback idempotency contract, and end-to-end role-critical flows.

## 9) Final Notes

- This audit is static-only; runtime reliability and operability claims remain **Manual Verification Required**.
- The repository is close to functional completeness, but acceptance should be blocked until Blocker/High items are remediated and re-audited.
- Recommended re-audit order: (1) security contract blockers, (2) search scope + callback idempotency, (3) deterministic promotion tests, (4) tamper-evident audit enhancements.
