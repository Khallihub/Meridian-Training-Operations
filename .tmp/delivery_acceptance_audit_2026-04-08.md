# Meridian Training Operations - Static Delivery Acceptance & Architecture Audit (Re-review)
Date: 2026-04-08

## 1. Verdict
- Overall conclusion: **Fail**

## 2. Scope and Static Verification Boundary
- What was reviewed:
  - Documentation/config: `README.md`, `docker-compose.yml`, `backend/.env.example`, `backend/pyproject.toml`, `frontend/package.json`, `frontend/vite.config.ts`.
  - Backend entrypoints/routing/security: `backend/app/main.py`, `backend/app/core/*`, auth, sessions, bookings, attendance, replays, checkout, promotions, payments, search, ingestion, jobs, monitoring, policy, audit modules.
  - Frontend role routes/pages/components/stores/APIs for admin/instructor/learner/finance/dataops.
  - Backend and frontend test suites (read-only static coverage audit).
- What was not reviewed:
  - Runtime behavior under real infrastructure load, real browser rendering, websocket media transport quality, real Kafka/Flume/Logstash/MySQL/PostgreSQL connectivity, LAN terminal callback networking.
- What was intentionally not executed:
  - No project startup, no Docker run, no tests executed, no external services.
- Claims requiring manual verification:
  - Real-time websocket media quality and reconnection under network faults.
  - Scheduler timing correctness in deployed environment.
  - External adapter connectivity and throughput under production-like volumes.
  - Prometheus/Grafana actual scrape health in a running stack.

## 3. Repository / Requirement Mapping Summary
- Prompt core goal mapped: offline FastAPI + Vue platform for scheduling, booking/live/replay, checkout/promotions/payments/refunds/reconciliation, operational search/export, and local ingestion/jobs/monitoring across five roles.
- Main implementation areas mapped:
  - Role/auth/session security and routing (`backend/app/core/deps.py:17`, `frontend/src/router/index.ts:77`).
  - Scheduling/booking/attendance/replay (`backend/app/modules/sessions/service.py:57`, `backend/app/modules/bookings/service.py:25`, `backend/app/modules/attendance/service.py:24`, `backend/app/modules/replays/service.py:30`).
  - Checkout/promotions/payments/reconciliation (`backend/app/modules/checkout/service.py:37`, `backend/app/modules/checkout/best_offer.py:80`, `backend/app/modules/payments/service.py:42`, `backend/app/modules/jobs/celery_app.py:39`).
  - Search/export/saved-search (`backend/app/modules/search/service.py:151`, `backend/app/modules/search/service.py:268`).
  - Ingestion/jobs/alerts (`backend/app/modules/ingestion/service.py:113`, `backend/app/modules/jobs/tasks.py:201`, `backend/app/modules/monitoring/controller.py:27`).

## 4. Section-by-section Review

### 4.1 Hard Gates
#### 1.1 Documentation and static verifiability
- Conclusion: **Fail**
- Rationale:
  - Delivery docs and bootstrap path are statically inconsistent: README states default admin login and "No manual setup required", but compose sets production mode that skips admin seeding.
  - Service URL docs also mismatch exposed ports for monitoring/MinIO.
- Evidence:
  - `README.md:5`, `README.md:11`, `README.md:31`, `README.md:41`
  - `docker-compose.yml:17`
  - `backend/docker-entrypoint.sh:14`, `backend/docker-entrypoint.sh:15`, `backend/docker-entrypoint.sh:42`
  - `README.md:20`, `README.md:21`, `docker-compose.yml:97`, `docker-compose.yml:98`, `docker-compose.yml:210`, `docker-compose.yml:211`
- Manual verification note:
  - Manual check required only if a separate undocumented admin bootstrap path exists.

#### 1.2 Material deviation from Prompt
- Conclusion: **Partial Pass**
- Rationale:
  - Most domains exist, but several core semantics materially deviate (reschedule access behavior, buffer enforcement, timezone fidelity, ingestion failure visibility).
- Evidence:
  - `backend/app/modules/bookings/service.py:106`, `backend/app/modules/replays/service.py:57`, `backend/app/modules/attendance/service.py:37`
  - `backend/app/modules/sessions/service.py:41`, `backend/app/modules/sessions/service.py:46`
  - `frontend/src/components/calendar/MonthCalendar.vue:40`
  - `backend/app/modules/ingestion/service.py:161`, `backend/app/modules/ingestion/adapters/cdc_adapter.py:80`, `backend/app/modules/ingestion/adapters/cdc_adapter.py:111`

### 4.2 Delivery Completeness
#### 2.1 Coverage of explicit core requirements
- Conclusion: **Partial Pass**
- Rationale:
  - Core feature areas are implemented, but key requirement-critical behavior has gaps:
    - Reschedule flow can remove effective learner access.
    - Buffer-time enforcement is incomplete.
    - Booking validation allows non-scheduled/ended session booking.
- Evidence:
  - `backend/app/modules/bookings/service.py:81`, `backend/app/modules/bookings/service.py:106`
  - `backend/app/modules/replays/service.py:57`, `backend/app/modules/sessions/websocket.py:186`, `backend/app/modules/sessions/repository.py:80`
  - `backend/app/modules/sessions/service.py:41`, `backend/app/modules/sessions/service.py:46`
  - `backend/app/modules/bookings/service.py:26`, `backend/app/modules/bookings/service.py:31`

#### 2.2 End-to-end 0-to-1 deliverable vs partial demo
- Conclusion: **Partial Pass**
- Rationale:
  - Repo has full-stack structure and broad module set, but default static bootstrap is blocked by admin-account inconsistency.
- Evidence:
  - `backend/app/main.py:52`, `frontend/src/router/index.ts:64`
  - `README.md:8`, `README.md:31`, `docker-compose.yml:17`, `backend/docker-entrypoint.sh:42`
- Manual verification note:
  - Manual user bootstrap could unblock runtime use, but this is not documented as the default acceptance path.

### 4.3 Engineering and Architecture Quality
#### 3.1 Engineering structure and module decomposition
- Conclusion: **Pass**
- Rationale:
  - Backend modules are decomposed by bounded context; frontend is role/page/store segmented.
- Evidence:
  - `backend/app/main.py:53`, `backend/app/main.py:93`
  - `frontend/src/router/index.ts:77`, `frontend/src/router/index.ts:131`

#### 3.2 Maintainability and extensibility
- Conclusion: **Partial Pass**
- Rationale:
  - Overall maintainable structure exists, but there are maintainability regressions from cross-module semantic mismatch (booking status vs access checks) and missing ownership checks.
- Evidence:
  - `backend/app/modules/bookings/service.py:106`, `backend/app/modules/replays/service.py:57`, `backend/app/modules/attendance/service.py:37`
  - `backend/app/modules/sessions/controller.py:68`, `backend/app/modules/sessions/service.py:148`

### 4.4 Engineering Details and Professionalism
#### 4.1 Error handling/logging/validation/API professionalism
- Conclusion: **Fail**
- Rationale:
  - High-impact validation and error-state handling gaps remain:
    - Ingestion CDC adapter failures are swallowed and can be marked successful.
    - Session creation/update lacks explicit boundary validation for start/end and numeric constraints.
    - Monitoring stack config/auth mismatch likely prevents documented scrape behavior.
- Evidence:
  - `backend/app/modules/ingestion/adapters/cdc_adapter.py:80`, `backend/app/modules/ingestion/adapters/cdc_adapter.py:111`, `backend/app/modules/ingestion/service.py:161`
  - `backend/app/modules/sessions/schemas.py:20`, `backend/app/modules/sessions/schemas.py:43`, `backend/app/modules/sessions/service.py:57`, `backend/app/modules/sessions/service.py:148`
  - `backend/app/modules/monitoring/controller.py:21`, `monitoring/prometheus.yml:6`, `monitoring/prometheus.yml:9`

#### 4.2 Product/service shape vs demo
- Conclusion: **Partial Pass**
- Rationale:
  - Product-like layout and role flows exist, but blocker/high defects prevent acceptance as robust delivery.
- Evidence:
  - `backend/app/main.py:52`, `frontend/src/layouts/AppLayout.vue:27`

### 4.5 Prompt Understanding and Requirement Fit
#### 5.1 Business goal/semantics/constraints fit
- Conclusion: **Partial Pass**
- Rationale:
  - Intended domains align, but multiple semantics conflict with prompt constraints (buffer gap semantics, reschedule access continuity, timezone-specific calendar fidelity).
- Evidence:
  - `backend/app/modules/sessions/service.py:41`, `backend/app/modules/sessions/service.py:46`
  - `backend/app/modules/bookings/service.py:106`, `backend/app/modules/replays/service.py:57`
  - `frontend/src/components/calendar/MonthCalendar.vue:40`, `frontend/src/components/calendar/WeekCalendar.vue:47`

### 4.6 Aesthetics (frontend/full-stack)
#### 6.1 Visual and interaction design quality
- Conclusion: **Cannot Confirm Statistically**
- Rationale:
  - Static code indicates structured UI, but rendering quality and interaction feel require manual run.
  - Static text artifacts indicate likely visible UX defects in some views.
- Evidence:
  - `frontend/src/pages/search/AdvancedSearchPage.vue:236`
  - `frontend/src/pages/sessions/SessionDetailPage.vue:178`, `frontend/src/pages/sessions/SessionDetailPage.vue:351`
  - `frontend/src/components/live/LiveRoomModal.vue:383`, `frontend/src/components/live/LiveRoomModal.vue:385`
- Manual verification note:
  - Browser verification required for spacing/alignment/interactive state feedback and character rendering.

## 5. Issues / Suggestions (Severity-Rated)

### Blocker
1. Severity: **Blocker**
- Title: Default documented bootstrap path cannot produce an initial admin account
- Conclusion: **Fail**
- Evidence: `README.md:11`, `README.md:31`, `docker-compose.yml:17`, `backend/docker-entrypoint.sh:14`, `backend/docker-entrypoint.sh:42`
- Impact:
  - Static default startup path is non-verifiable for core role-based flows because login bootstrap contradicts docs.
- Minimum actionable fix:
  - Align docs and bootstrap behavior: either set non-production bootstrap mode for local compose, or document a mandatory first-admin creation path and remove default credential claims.

### High
2. Severity: **High**
- Title: Rescheduled learners lose effective access to live room, replay, attendance, and roster
- Conclusion: **Fail**
- Evidence:
  - Status transition: `backend/app/modules/bookings/service.py:106`
  - Confirmed-only access checks: `backend/app/modules/sessions/websocket.py:186`, `backend/app/modules/replays/service.py:57`, `backend/app/modules/attendance/service.py:37`, `backend/app/modules/sessions/repository.py:80`
- Impact:
  - Core booking semantics break after reschedule; learners can be moved but denied downstream participation and visibility.
- Minimum actionable fix:
  - Treat `rescheduled` as enrolled-for-target-session (or set status back to `confirmed` after successful move), and update all access/roster checks consistently.

3. Severity: **High**
- Title: Room buffer-time rule is incompletely enforced
- Conclusion: **Fail**
- Evidence: `backend/app/modules/sessions/service.py:41`, `backend/app/modules/sessions/service.py:46`
- Impact:
  - Sessions can be scheduled without the required post-session buffer from an already scheduled session.
- Minimum actionable fix:
  - Conflict condition must account for both sessions’ effective blocked window (e.g., existing session end + existing buffer).

4. Severity: **High**
- Title: Missing object-level authorization for instructor session/attendance operations
- Conclusion: **Fail**
- Evidence:
  - Instructor can mutate any session by role: `backend/app/modules/sessions/controller.py:68`, `backend/app/modules/sessions/controller.py:86`, `backend/app/modules/sessions/controller.py:95`, `backend/app/modules/sessions/controller.py:104`
  - Service methods do not check ownership: `backend/app/modules/sessions/service.py:148`, `backend/app/modules/sessions/service.py:166`, `backend/app/modules/sessions/service.py:178`, `backend/app/modules/sessions/service.py:189`
  - Attendance endpoints similarly role-only: `backend/app/modules/attendance/controller.py:20`, `backend/app/modules/attendance/controller.py:30`
- Impact:
  - Instructors can act on sessions/attendance outside their own assignment boundary.
- Minimum actionable fix:
  - Enforce instructor ownership on session-scoped mutations and attendance actions (session.instructor ownership check + 403).

5. Severity: **High**
- Title: Ingestion CDC failures can be silently marked successful
- Conclusion: **Fail**
- Evidence:
  - CDC adapters swallow exceptions and return empty success-like payloads: `backend/app/modules/ingestion/adapters/cdc_adapter.py:80`, `backend/app/modules/ingestion/adapters/cdc_adapter.py:111`
  - Run status is set to success when no exception reaches service: `backend/app/modules/ingestion/service.py:161`
- Impact:
  - Data-health monitoring can report false success, hiding ingestion outages and corrupting operational trust.
- Minimum actionable fix:
  - Propagate adapter errors to service layer (or return structured error state) and mark run failed when adapter connectivity/CDC pull fails.

6. Severity: **High**
- Title: Search export ignores learner phone filter
- Conclusion: **Fail**
- Evidence:
  - Phone filter exists in model: `backend/app/modules/search/schemas.py:17`
  - Phone filtering logic is only in `search()` branch: `backend/app/modules/search/service.py:156`, `backend/app/modules/search/service.py:167`
  - `export()` path uses base/count queries without phone post-filter: `backend/app/modules/search/service.py:268`, `backend/app/modules/search/service.py:274`
- Impact:
  - Export output can include records outside requested phone filter, causing incorrect reporting and possible over-disclosure.
- Minimum actionable fix:
  - Apply equivalent phone-filter post-processing in export path before row-limit check and file generation.

7. Severity: **High**
- Title: Booking creation lacks session-status/time gating
- Conclusion: **Fail**
- Evidence:
  - Booking create only checks existence/capacity/duplicate: `backend/app/modules/bookings/service.py:26`, `backend/app/modules/bookings/service.py:31`, `backend/app/modules/bookings/service.py:35`
  - Session lifecycle statuses defined but not enforced in booking create: `backend/app/modules/sessions/models.py:12`
- Impact:
  - Learners can request bookings against cancelled/completed/live/past sessions if capacity allows.
- Minimum actionable fix:
  - Enforce schedule-state/time validation (book only eligible upcoming scheduled sessions).

8. Severity: **High**
- Title: Prometheus scrape config conflicts with authenticated metrics endpoint
- Conclusion: **Fail**
- Evidence:
  - Metrics endpoint requires admin/dataops auth: `backend/app/modules/monitoring/controller.py:21`
  - Monitoring test confirms unauthenticated metrics is 401: `backend/tests/api/test_monitoring.py:16`
  - Prometheus scrape config has no auth config: `monitoring/prometheus.yml:6`, `monitoring/prometheus.yml:9`
- Impact:
  - Observability stack can fail to ingest backend metrics as documented.
- Minimum actionable fix:
  - Either expose a scrape-safe internal metrics endpoint or configure authenticated scraping.

### Medium
9. Severity: **Medium**
- Title: Timezone handling in calendar/list rendering is inconsistent with “chosen timezone” requirement
- Conclusion: **Partial Pass**
- Evidence:
  - Monthly day matching uses string prefix (no timezone conversion): `frontend/src/components/calendar/MonthCalendar.vue:40`
  - Weekly grouping/position uses local parse/getHours instead of selected tz: `frontend/src/components/calendar/WeekCalendar.vue:47`, `frontend/src/components/calendar/WeekCalendar.vue:59`
  - Learner month/list displays raw ISO slices: `frontend/src/pages/learner/SessionBrowsePage.vue:87`, `frontend/src/pages/learner/SessionBrowsePage.vue:110`
- Impact:
  - Date/day and time placement can drift for non-local or cross-offset scenarios.
- Minimum actionable fix:
  - Normalize all display/grouping logic through timezone-aware conversion (`formatInTimeZone`) and avoid raw string slicing.

10. Severity: **Medium**
- Title: Documentation service URLs mismatch compose-exposed ports
- Conclusion: **Fail**
- Evidence: `README.md:20`, `README.md:21`, `docker-compose.yml:97`, `docker-compose.yml:98`, `docker-compose.yml:210`, `docker-compose.yml:211`
- Impact:
  - Verification attempts are misdirected; review confidence and onboarding quality drop.
- Minimum actionable fix:
  - Correct README URL table to actual mapped ports.

11. Severity: **Medium**
- Title: Session input boundary validation is incomplete
- Conclusion: **Fail**
- Evidence:
  - No schema constraints for start/end ordering, capacity bounds, or buffer bounds: `backend/app/modules/sessions/schemas.py:20`, `backend/app/modules/sessions/schemas.py:43`
  - Service create/update lacks explicit boundary guards: `backend/app/modules/sessions/service.py:57`, `backend/app/modules/sessions/service.py:148`
- Impact:
  - Invalid payloads can propagate to DB-level failures or inconsistent scheduling behavior.
- Minimum actionable fix:
  - Add schema validators (`end_time > start_time`, `capacity >= 1`, `buffer_minutes >= 0`) and service-level guards.

12. Severity: **Medium**
- Title: High-risk authorization and integration paths are under-tested
- Conclusion: **Fail**
- Evidence:
  - Existing tests focus on auth basics and selected flows: `backend/tests/api/test_auth.py:12`, `backend/tests/api/test_payments.py:16`, `backend/tests/api/test_sessions.py:39`
  - Missing direct tests for 403 object-level ownership on session mutations, replay/live-room access after reschedule, ingestion failure states, and scheduler critical paths.
- Impact:
  - Severe defects can remain undetected while test suite still passes.
- Minimum actionable fix:
  - Add focused API tests for ownership enforcement, reschedule-access semantics, ingestion failure-to-alert chain, and order auto-close/reconciliation schedule outcomes.

### Low
13. Severity: **Low**
- Title: Multiple UI strings contain encoding artifacts
- Conclusion: **Fail**
- Evidence: `frontend/src/pages/search/AdvancedSearchPage.vue:236`, `frontend/src/pages/sessions/SessionDetailPage.vue:178`, `frontend/src/components/live/LiveRoomModal.vue:385`
- Impact:
  - Degrades professionalism/readability of user-facing views.
- Minimum actionable fix:
  - Normalize source file encoding and replace corrupted glyphs with intended characters.

## 6. Security Review Summary

- Authentication entry points: **Partial Pass**
  - Evidence: `backend/app/modules/auth/controller.py:12`, `backend/app/modules/auth/service.py:35`, `backend/app/core/security.py:32`, `backend/app/core/deps.py:38`
  - Reasoning: password complexity/lockout/inactivity controls exist; bootstrap inconsistency blocks default access path.

- Route-level authorization: **Partial Pass**
  - Evidence: `backend/app/core/deps.py:50`, `backend/app/modules/sessions/controller.py:68`, `backend/app/modules/payments/controller.py:22`, `backend/app/modules/ingestion/controller.py:20`
  - Reasoning: broad role guards are present on most routes; some sensitive paths rely on coarse role checks only.

- Object-level authorization: **Fail**
  - Evidence: `backend/app/modules/sessions/controller.py:68`, `backend/app/modules/sessions/service.py:148`, `backend/app/modules/attendance/controller.py:20`
  - Reasoning: instructor ownership of target session is not enforced for mutation/attendance operations.

- Function-level authorization: **Partial Pass**
  - Evidence: `backend/app/modules/checkout/service.py:134`, `backend/app/modules/bookings/service.py:163`, `backend/app/modules/users/controller.py:53`
  - Reasoning: several function-level checks exist for own-resource access; gaps remain on session-scoped instructor actions.

- Tenant / user data isolation: **Partial Pass**
  - Evidence: `backend/app/modules/checkout/service.py:134`, `backend/app/modules/bookings/service.py:163`, `backend/app/modules/users/controller.py:53`
  - Reasoning: learner self-scope exists on key entities; instructor cross-session scope remains over-broad.

- Admin / internal / debug protection: **Partial Pass**
  - Evidence: `backend/app/modules/monitoring/controller.py:21`, `backend/app/modules/payments/controller.py:29`, `backend/app/modules/ingestion/controller.py:71`
  - Reasoning: admin/internal endpoints mostly protected; callback/webhook endpoints are intentionally open but rely on signature/api-key controls.

## 7. Tests and Logging Review

- Unit tests: **Partial Pass**
  - Evidence: `backend/tests/unit/test_security.py:13`, `backend/tests/unit/test_booking_state.py:35`, `backend/tests/unit/test_best_offer.py:35`, `frontend/src/tests/unit/stores/search.spec.ts:17`
  - Reasoning: core utility and selected state rules are covered; major authorization/integration semantics are not.

- API / integration tests: **Partial Pass**
  - Evidence: `backend/tests/api/test_auth.py:42`, `backend/tests/api/test_payments.py:16`, `backend/tests/api/test_sessions.py:39`
  - Reasoning: positive auth/payment/session basics are tested; insufficient negative-path and ownership/security coverage.

- Logging categories / observability: **Partial Pass**
  - Evidence: `backend/app/modules/jobs/tasks.py:35`, `backend/app/core/audit.py:15`, `backend/app/modules/sessions/websocket.py:157`
  - Reasoning: structured logger use exists for jobs/audit/websocket, but ingestion adapters can hide failures before observability pipeline detects them.

- Sensitive-data leakage risk in logs / responses: **Partial Pass**
  - Evidence: `backend/app/modules/users/service.py:24`, `backend/app/modules/search/service.py:183`, `backend/app/modules/payments/models.py:35`
  - Reasoning: phone/email are masked in common responses; callback payloads are stored in DB (`raw_callback`) and should be access-controlled and retention-reviewed manually.

## 8. Test Coverage Assessment (Static Audit)

### 8.1 Test Overview
- Unit tests exist:
  - Backend pytest unit tests (`backend/tests/unit/*`), frontend vitest unit/component tests (`frontend/src/tests/*`).
- API/integration tests exist:
  - Backend async API tests (`backend/tests/api/*`) via HTTPX ASGI transport.
- Frameworks:
  - Pytest/pytest-asyncio (`backend/pyproject.toml:37`, `backend/pyproject.toml:48`), Vitest (`frontend/package.json:10`, `frontend/vite.config.ts:21`).
- Test entry points:
  - Backend `tests` path (`backend/pyproject.toml:49`).
  - Frontend script commands (`frontend/package.json:10`, `frontend/package.json:12`) and setup file (`frontend/vite.config.ts:24`).
- Documentation test commands:
  - README documents backend test command only (`README.md:55`, `README.md:59`); frontend test command is not documented there.

### 8.2 Coverage Mapping Table
| Requirement / Risk Point | Mapped Test Case(s) | Key Assertion / Fixture / Mock | Coverage Assessment | Gap | Minimum Test Addition |
|---|---|---|---|---|---|
| Password policy + lockout | `backend/tests/unit/test_security.py:13`, `backend/tests/api/test_auth.py:29` | Complexity regex pass/fail; 423 + `locked_until` assertion (`backend/tests/api/test_auth.py:34`) | basically covered | No inactivity-expiry test | Add API test for inactivity timeout rejection and refresh behavior post-idle |
| Unauthenticated 401 on protected endpoint | `backend/tests/api/test_auth.py:42` | `/api/users/me` returns 401 | sufficient | Only one endpoint class validated | Add matrix tests across sessions/bookings/search/payments protected routes |
| Unauthorized 403 role/object checks | None found | N/A | missing | 403 paths are largely untested | Add tests for learner/instructor forbidden access to admin endpoints and non-owned objects |
| Booking policy cutoffs (2h reschedule / 24h cancellation fee) | `backend/tests/unit/test_booking_state.py:37`, `backend/tests/unit/test_booking_state.py:78` | Raises `UnprocessableError`; fee flag true/false | basically covered | Unit-only mocks, no API auth/object checks | Add API tests for learner/admin cutoff behavior and ownership constraints |
| Rescheduled learner access to live/replay/attendance | None found | N/A | missing | Critical semantic regression undetected by tests | Add integration tests: reschedule then verify live-room/replay/attendance access remains valid |
| Promotions best-offer correctness | `backend/tests/unit/test_best_offer.py:47`, `backend/tests/api/test_checkout.py:42` | Mutual exclusion/stacking assertions; cart discount totals | basically covered | No edge tests for mixed-rule conflicts in persisted order data | Add API tests covering stack_group+exclusive combinations with multiple line items |
| Payment callback signature handling | `backend/tests/api/test_payments.py:16`, `backend/tests/api/test_payments.py:48` | Valid signature -> completed; invalid -> failed | sufficient | Missing idempotency/timestamp-window tests | Add tests for replayed callback fingerprint and stale timestamp rejection |
| Search 50k export guard + saved search cap | `frontend/src/tests/unit/stores/search.spec.ts:30`, `frontend/src/tests/unit/stores/search.spec.ts:37` | `exportDisabled` state and max-20 store behavior | insufficient | Backend export API semantics (incl. phone filter) untested | Add backend API tests for `/api/search/export` with phone filter and row-limit enforcement |
| Ingestion failure classification + alerting chain | None found | N/A | missing | Silent-failure high risk in CDC not covered | Add adapter/service tests ensuring exceptions mark run failed and generate monitorable signals |
| Scheduler order auto-close + reconciliation at 2AM | None found | N/A | missing | Core scheduled business outcomes untested | Add Celery task/unit tests for expiry close and reconciliation export date window |
| Object-level instructor authorization on session ops | None found | N/A | missing | Severe privilege boundary defect can pass test suite | Add API tests ensuring instructor cannot mutate non-owned sessions/attendance |
| Timezone-correct calendar rendering | None found | N/A | missing | Chosen-timezone requirement not guarded by tests | Add frontend component tests for day bucketing/time labels across timezone offsets |

### 8.3 Security Coverage Audit
- Authentication: **Basically covered**
  - Covered: login success/failure and lockout (`backend/tests/api/test_auth.py:12`, `backend/tests/api/test_auth.py:29`), password/JWT utilities (`backend/tests/unit/test_security.py:48`).
  - Not covered: inactivity timeout, token blocklist behavior, refresh replay edge cases.
- Route authorization: **Insufficient**
  - Covered: one unauthenticated 401 check (`backend/tests/api/test_auth.py:42`), monitoring metrics auth check (`backend/tests/api/test_monitoring.py:16`).
  - Not covered: broad role matrix and endpoint families.
- Object-level authorization: **Missing**
  - No meaningful tests for cross-resource ownership constraints (session ownership, booking ownership edge paths, attendance ownership).
- Tenant / data isolation: **Insufficient**
  - Some own-resource checks exist in code, but no dedicated isolation tests to detect cross-user leakage/regression.
- Admin / internal protection: **Insufficient**
  - No tests for misuse/abuse of open callback/webhook endpoints beyond basic payment signature validity.

### 8.4 Final Coverage Judgment
- **Fail**
- Boundary explanation:
  - Covered: basic auth, selected booking policy units, best-offer unit/API basics, payment callback happy/invalid signature, limited monitoring auth check.
  - Uncovered major risks: object-level authorization, reschedule-access continuity, scheduler-critical business jobs, ingestion failure semantics, timezone correctness, and backend search export edge semantics. Existing tests could still pass while severe defects remain in production-critical flows.

## 9. Final Notes
- The codebase is broad and close to the requested domain shape, but acceptance is blocked by bootstrap inconsistency and several high-severity semantic/security defects.
- All conclusions above are static and evidence-linked; runtime behavior claims are intentionally avoided unless directly inferable from code/tests.
