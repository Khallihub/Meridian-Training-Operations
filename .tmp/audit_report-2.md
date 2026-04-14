# Meridian Training Operations — Static Delivery Acceptance & Architecture Audit

Date: 2026-04-13  
Method: Static repository analysis only (no runtime execution, no Docker/test execution, no source-code modifications)

## 1) Verdict

**Overall Verdict: Partial Pass (Not Production-Acceptable Yet)**

The codebase is broadly implemented and many previously known blockers are fixed (Argon2id, doc, async export backend, audit hash-chain, scope-aware search query core). However, there are still material defects affecting core acceptance areas.

Top material findings:
- **Blocker**: Search export UX is still wired to a removed synchronous endpoint, so CSV/XLSX export from the search UI is effectively broken.
- **Blocker**: Promotions admin/finance UI sends legacy promotion enums and an invalid preview payload, breaking promotion lifecycle operations from the web app.
- **High**: Search export job polling/download has no object-level ownership check (IDOR risk across eligible roles).
- **High**: Booking endpoints still allow overbroad staff access patterns inconsistent with scoped ABAC boundaries.
- **Medium**: Calendar day-bucketing logic does not consistently honor the provided timezone in weekly/monthly grouping.

## 2) Scope and Static Verification Boundary

- Review type: static-only inspection of backend, frontend, migrations, tests, and docs.
- Explicitly not performed: service startup, API calling, browser validation, Docker execution, or test execution.
- Any behavior requiring runtime is marked as **Cannot Confirm Statistically** or **Manual Verification Required**.

Boundary notes:
- Queue execution timing, retry timing, and file-availability race behavior: **Manual Verification Required**.
- True user-observed UX under deployed reverse-proxy routes: **Manual Verification Required**.

## 3) Repository / Requirement Mapping Summary

Major PRD domains are implemented in architecture:
- FastAPI route composition and module registration in `repo/backend/app/main.py`.
- Role-based Vue route structure in `repo/frontend/src/router/index.ts`.
- Scheduler/worker flows for monitoring, reconciliation, ingestion, and search export jobs in `repo/backend/app/modules/jobs/tasks.py` and `repo/backend/app/modules/jobs/celery_app.py`.

Current acceptance risk is not missing modules; it is contract drift between frontend and backend in key workflows plus object-level authorization gaps.

## 4) Section-by-section Review

### Section A — Scheduling, Booking, Attendance, Replay

Status: **Partial Pass**

Implemented:
- Weekly/monthly session APIs with timezone query parameter in `repo/backend/app/modules/sessions/controller.py:18` and `repo/backend/app/modules/sessions/controller.py:29`.
- Instructor ownership checks for session state and attendance in `repo/backend/app/modules/sessions/service.py:32` and `repo/backend/app/modules/attendance/service.py:24`.
- Replay access checks in replay service path (controller delegates with role/user context) in `repo/backend/app/modules/replays/controller.py:55` and `repo/backend/app/modules/replays/controller.py:72`.

Material gap:
- Frontend calendar grouping does not consistently use provided timezone for day assignment:
  - Month view buckets by raw string prefix (`start_time.startsWith(...)`) in `repo/frontend/src/components/calendar/MonthCalendar.vue:38` and `repo/frontend/src/components/calendar/MonthCalendar.vue:40`.
  - Week view compares parsed/local dates for grouping while only label formatting uses timezone in `repo/frontend/src/components/calendar/WeekCalendar.vue:47`, `repo/frontend/src/components/calendar/WeekCalendar.vue:49`, and `repo/frontend/src/components/calendar/WeekCalendar.vue:71`.

### Section B — Checkout, Promotions, Payments, Refunds

Status: **Fail (UI contract drift blocks core promotion operations)**

Implemented on backend:
- Canonical promotion enum and best-offer engine support PRD-aligned values in `repo/backend/app/modules/promotions/models.py:12` and `repo/backend/app/modules/checkout/best_offer.py:45`.
- Promotion enum migration from legacy values documented in `repo/backend/alembic/versions/0005_prd_enum_alignment.py:18` and `repo/backend/alembic/versions/0005_prd_enum_alignment.py:167`.

Blocker gaps in frontend contract:
- Frontend still types promotion as legacy values (`pct_off`, `fixed_off`, `bogo`) in `repo/frontend/src/api/endpoints/admin.ts:51`.
- Promotion form submits legacy values in `repo/frontend/src/pages/promotions/PromotionFormPage.vue:17` and `repo/frontend/src/pages/promotions/PromotionFormPage.vue:73`.
- Promotion list formatter interprets only legacy values in `repo/frontend/src/pages/promotions/PromotionListPage.vue:26`.
- Promotion preview payload is incompatible with backend endpoint contract:
  - Frontend sends `{ promotion, sample_order_total }` in `repo/frontend/src/pages/promotions/PromotionFormPage.vue:55`.
  - Backend preview expects `CartCreate` with `items` in `repo/backend/app/modules/promotions/controller.py:20` and `repo/backend/app/modules/checkout/schemas.py:16`.

### Section C — Search, Saved Searches, Exports, Reporting

Status: **Fail**

Implemented on backend:
- Async export-job API contract exists (`POST/GET/download`) in `repo/backend/app/modules/search/controller.py:46`, `repo/backend/app/modules/search/controller.py:72`, and `repo/backend/app/modules/search/controller.py:82`.

Blocker gap:
- Frontend export still calls removed synchronous endpoint `/api/v1/search/export`:
  - `repo/frontend/src/composables/useExport.ts:19`
  - `repo/frontend/src/api/endpoints/search.ts:24`
  - Search page invokes this path via composable in `repo/frontend/src/pages/search/AdvancedSearchPage.vue:84`.
- No frontend usage of `/api/v1/search/export/jobs` was found in `repo/frontend/src/**` (static search result), so poll/download workflow is not integrated.

High gap:
- Export job polling/download does not enforce owner-level authorization (see Section 5, Finding 3).

### Section D — Jobs, Retry, Alerts, Monitoring

Status: **Pass (Static)**

- Job scheduler and monitoring surfaces are implemented and wired:
  - Task scheduling and Celery config in `repo/backend/app/modules/jobs/celery_app.py`.
  - Operational job endpoints and monitoring pages in `repo/backend/app/modules/jobs/controller.py`, `repo/frontend/src/pages/jobs/JobMonitorPage.vue`, and `repo/frontend/src/pages/jobs/MonitoringPage.vue`.
- Runtime SLA/alert correctness remains **Manual Verification Required**.

### Section E — Ingestion and Deterministic Dedup/Reprocessing

Status: **Pass (Static)**

- Ingestion source CRUD, test connection, and run triggers are implemented in backend/frontend paths:
  - Backend service/controller under `repo/backend/app/modules/ingestion/`.
  - Frontend pages `repo/frontend/src/pages/dataops/IngestionSourceListPage.vue`, `repo/frontend/src/pages/dataops/IngestionSourceFormPage.vue`, `repo/frontend/src/pages/dataops/IngestionSourceDetailPage.vue`.
- Operational behavior under restarts remains **Manual Verification Required**.

### Section F — Security, Authorization, Audit, Data Governance

Status: **Partial Pass (High-risk authz gaps remain)**

Implemented:
- PRD-aligned auth hardening and audit chain were previously addressed (Argon2id, tamper-evidence migration, explicit assumptions).

Remaining High findings:
- Booking authorization scope is too broad for several staff actions (details in Section 5, Finding 4).
- Search export job endpoint allows cross-user job access by UUID without ownership validation (details in Section 5, Finding 3).

## 5) Issues / Suggestions (Blocker/High first)

### Finding 1 — Blocker
**Search export is broken in frontend due endpoint contract drift**

Evidence:
- Backend exposes async export jobs only: `repo/backend/app/modules/search/controller.py:46`, `repo/backend/app/modules/search/controller.py:72`, `repo/backend/app/modules/search/controller.py:82`.
- Frontend still posts to removed sync endpoint: `repo/frontend/src/composables/useExport.ts:19` and `repo/frontend/src/api/endpoints/search.ts:24`.
- Search page uses this export call: `repo/frontend/src/pages/search/AdvancedSearchPage.vue:84`.
- Intended async contract is documented in `docs/ASSUMPTIONS.md:153`.

Impact:
- Core requirement "export to CSV/Excel with row cap" is not met from primary UI.

Minimum fix:
- Replace frontend export flow with async job lifecycle:
  1. `POST /api/v1/search/export/jobs`
  2. Poll `GET /api/v1/search/export/jobs/{id}`
  3. Download via `GET /api/v1/search/export/jobs/{id}/download`
- Remove stale sync export paths to avoid future drift.

### Finding 2 — Blocker
**Promotions UI/backend contract mismatch breaks create/edit/preview semantics**

Evidence:
- Backend canonical values: `percent_off`, `fixed_off`, `threshold_fixed_off`, `bogo_selected_workshops` in `repo/backend/app/modules/promotions/models.py:12` and migration mapping in `repo/backend/alembic/versions/0005_prd_enum_alignment.py:18`.
- Frontend still sends legacy values (`pct_off`, `fixed_off`, `bogo`) in:
  - `repo/frontend/src/api/endpoints/admin.ts:51`
  - `repo/frontend/src/pages/promotions/PromotionFormPage.vue:17`
  - `repo/frontend/src/pages/promotions/PromotionFormPage.vue:73`
- Preview contract mismatch:
  - Frontend sends `previewPromotion({ promotion, sample_order_total })` in `repo/frontend/src/pages/promotions/PromotionFormPage.vue:55`.
  - Backend preview expects `CartCreate` items payload in `repo/backend/app/modules/promotions/controller.py:20` and `repo/backend/app/modules/checkout/schemas.py:16`.

Impact:
- Promotion setup and preview, a core checkout capability, is unreliable/broken from admin/finance UI.

Minimum fix:
- Normalize frontend promotion enum to backend canonical values.
- Either redesign preview API to accept promotion draft payload, or redesign UI preview call to use cart-based preview inputs.
- Add explicit frontend mapping tests to prevent enum regressions.

### Finding 3 — High
**Search export job object-level authorization missing (IDOR risk)**

Evidence:
- Model stores ownership/scope fields: `created_by`, `caller_id`, `caller_role` in `repo/backend/app/modules/search/models.py:33` and `repo/backend/app/modules/search/models.py:38`.
- Job creation persists those fields in `repo/backend/app/modules/search/service.py:416`.
- Job read path fetches by `id` only, no owner check in `repo/backend/app/modules/search/service.py:429` and `repo/backend/app/modules/search/service.py:431`.
- Controller poll/download pass authenticated user but service ignores it in `repo/backend/app/modules/search/controller.py:72`, `repo/backend/app/modules/search/controller.py:79`, and `repo/backend/app/modules/search/controller.py:90`.

Impact:
- Any authorized role user with a known job UUID can read status/download another user's export artifact.

Minimum fix:
- Enforce `(created_by == current_user.id)` for non-admins in both poll and download paths.
- Add tests for cross-user access denial on export jobs.

### Finding 4 — High
**Booking endpoints have overbroad staff access and missing scoped ownership checks**

Evidence:
- List endpoint grants unscoped listing for admin/instructor/finance by setting `learner_id = None` in `repo/backend/app/modules/bookings/controller.py:37`.
- Repository list applies no role-scope logic beyond optional learner filter in `repo/backend/app/modules/bookings/repository.py:42`.
- Confirm booking route allows instructors, but confirm service does not verify instructor owns the session in `repo/backend/app/modules/bookings/controller.py:85` and `repo/backend/app/modules/bookings/service.py:46`.
- Booking history endpoint enforces ownership only for learners; all other roles can query arbitrary booking history in `repo/backend/app/modules/bookings/controller.py:52`.
- Booking get endpoint bypasses ownership for finance and dataops in `repo/backend/app/modules/bookings/service.py:168`.
- PRD explicitly requires scoped ABAC and role boundaries in `docs/prd.md:301`, `docs/prd.md:303`, and role matrix in `docs/prd.md:307`.

Impact:
- Potential overexposure of enrollment/booking data and cross-scope staff actions.

Minimum fix:
- Add role-aware scope checks mirroring sessions/attendance patterns:
  - Instructor: only bookings for sessions they own.
  - Finance/DataOps: narrow to explicitly authorized booking/payment contexts.
- Add API tests for cross-role/cross-owner denial on list/get/history/confirm.

### Finding 5 — Medium
**Calendar day-grouping logic is not timezone-consistent with selected tz contract**

Evidence:
- Monthly grouping uses raw `start_time` prefix matching in `repo/frontend/src/components/calendar/MonthCalendar.vue:40`.
- Weekly grouping day-buckets by local parsed date in `repo/frontend/src/components/calendar/WeekCalendar.vue:47` and `repo/frontend/src/components/calendar/WeekCalendar.vue:49`.
- Time label formatting uses timezone separately in `repo/frontend/src/components/calendar/WeekCalendar.vue:71`, creating split semantics.
- PRD requires timezone-aware calendar behavior in `docs/prd.md:371` and `docs/prd.md:185`.

Impact:
- Sessions near midnight boundaries can appear under the wrong day for non-local/selected timezone contexts.

Minimum fix:
- Normalize both grouping and display through the same timezone conversion helper before day comparisons.

## 6) Security Review Summary

### Auth entry points
- Auth/session hardening appears implemented (Argon2id, lockout/inactivity, token checks) in current backend core/auth modules.
- **Residual risk**: object-level auth gaps in booking/export-job endpoints (Findings 3 and 4).

### Route-level authorization
- `require_roles` usage is broad and generally present.
- **Residual risk**: route-level checks without object-level predicates still permit cross-scope access in specific endpoints.

### Object-level authorization
- Good patterns exist in sessions/attendance/replay services.
- Missing object-level checks in booking confirm/history/list/get and search export job retrieval create high-severity drift from ABAC expectations.

### Data governance
- Sensitive data controls were improved previously, but overbroad data retrieval paths can still undermine least-privilege intent.

## 7) Tests and Logging Review

Backend tests present across many domains, but critical gaps remain for current defects:
- No dedicated backend API suites for search export endpoints or promotions endpoints were found under `repo/backend/tests/api/` (directory contains auth/attendance/checkout/etc only).
- Authorization tests cover learner isolation for booking by ID (`repo/backend/tests/api/test_authorization.py:214`) but do not cover instructor/finance/dataops overreach on booking list/history/confirm.

Frontend tests exist but miss broken contract paths:
- Search store tests focus on result count/export-disable flags and mocked API calls in `repo/frontend/src/tests/unit/stores/search.spec.ts:23`.
- No frontend tests found for async export-job polling/download integration in `repo/frontend/src/tests/**`.
- Promotion-related test fixtures still use legacy enums (`bogo`, `fixed_off`) in `repo/frontend/src/tests/components/checkout/DiscountTraceability.spec.ts:9`.

Logging/observability code exists, but these findings are contract/auth defects rather than logging defects.

## 8) Test Coverage Assessment

| Requirement Area | Static Test Evidence | Coverage Judgment | Gap |
|---|---|---|---|
| Search export async job flow | Backend routes exist (`search/controller.py`), frontend call path present | Partial Pass | No backend API tests for cross-user export job auth, no frontend integration tests for queue/poll/download |
| Promotions CRUD + preview contract | Backend promotion model/controller exists; frontend form/list implemented | Partial Pass | No contract tests ensuring frontend enum values and preview payload match backend schemas |
| Booking object-level ABAC | Learner isolation test exists (`test_authorization.py:214`) | Partial Pass | No tests for instructor ownership enforcement on confirm/list/history; no finance/dataops scope tests |
| Calendar timezone fidelity | Components and tz props exist | Partial Pass | No tests around timezone boundary bucketing/day assignment |

Final static coverage judgment: **Partial Pass**. Major flows are represented, but tests do not currently protect the highest-severity contract/auth regressions identified above.

## 9) Final Notes

- This report is strictly static; no runtime checks were performed.
- Compared to earlier audit iterations, foundational security hardening work is present, but **frontend-backend contract parity and object-level authorization** still block production acceptance.
- Recommended remediation order:
  1. Fix search export frontend contract to async jobs and add end-to-end tests.
  2. Fix promotions frontend enum/payload contracts and add API/UI contract tests.
  3. Enforce booking/export-job object-level authorization with role-scoped predicates and negative-access tests.
  4. Normalize calendar day-grouping timezone semantics and add boundary tests.
