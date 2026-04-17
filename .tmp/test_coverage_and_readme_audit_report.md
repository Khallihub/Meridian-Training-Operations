# Unified Test Coverage + README Audit (Strict Mode)

Date: 2026-04-17
Method: Static inspection only (no code/test/script/container execution)

## 1) Test Coverage Audit

### Project Type Detection
- Declared project type: fullstack.
- Evidence: `repo/README.md` line 3: `**Project type:** Fullstack (Backend + Frontend)`.

### Backend Endpoint Inventory
- API prefix source: `repo/backend/app/main.py` (`prefix = "/api/v1"` and repeated `app.include_router(..., prefix=prefix)`).
- WebSocket router source: `repo/backend/app/main.py` (`app.include_router(ws_router)`).
- Endpoint totals from static controller scan:
  - HTTP endpoints: 115
  - WebSocket endpoints: 1
  - Total endpoints: 116

#### Inventory (resolved METHOD + PATH)
| Endpoint | Source |
|---|---|
| POST /api/v1/auth/login | repo/backend/app/modules/auth/controller.py:12::login |
| POST /api/v1/auth/refresh | repo/backend/app/modules/auth/controller.py:21::refresh |
| POST /api/v1/auth/logout | repo/backend/app/modules/auth/controller.py:27::logout |
| POST /api/v1/auth/change-password | repo/backend/app/modules/auth/controller.py:37::change_password |
| GET /api/v1/courses | repo/backend/app/modules/courses/controller.py:16::list_courses |
| POST /api/v1/courses | repo/backend/app/modules/courses/controller.py:25::create_course |
| GET /api/v1/courses/{course_id} | repo/backend/app/modules/courses/controller.py:34::get_course |
| PATCH /api/v1/courses/{course_id} | repo/backend/app/modules/courses/controller.py:43::update_course |
| DELETE /api/v1/courses/{course_id} | repo/backend/app/modules/courses/controller.py:55::delete_course |
| GET /api/v1/sessions | repo/backend/app/modules/sessions/controller.py:17::list_weekly |
| GET /api/v1/sessions/monthly | repo/backend/app/modules/sessions/controller.py:29::list_monthly |
| POST /api/v1/sessions | repo/backend/app/modules/sessions/controller.py:41::create_session |
| POST /api/v1/sessions/recurring | repo/backend/app/modules/sessions/controller.py:50::create_recurring |
| GET /api/v1/sessions/{session_id} | repo/backend/app/modules/sessions/controller.py:59::get_session |
| PATCH /api/v1/sessions/{session_id} | repo/backend/app/modules/sessions/controller.py:64::update_session |
| DELETE /api/v1/sessions/{session_id} | repo/backend/app/modules/sessions/controller.py:74::delete_session |
| PATCH /api/v1/sessions/{session_id}/cancel | repo/backend/app/modules/sessions/controller.py:83::cancel_session |
| POST /api/v1/sessions/{session_id}/go-live | repo/backend/app/modules/sessions/controller.py:92::go_live |
| POST /api/v1/sessions/{session_id}/end | repo/backend/app/modules/sessions/controller.py:101::end_session |
| POST /api/v1/sessions/{session_id}/complete | repo/backend/app/modules/sessions/controller.py:110::complete_session |
| GET /api/v1/sessions/{session_id}/roster | repo/backend/app/modules/sessions/controller.py:120::get_roster |
| POST /api/v1/bookings | repo/backend/app/modules/bookings/controller.py:18::create_booking |
| GET /api/v1/bookings | repo/backend/app/modules/bookings/controller.py:28::list_bookings |
| GET /api/v1/bookings/{booking_id}/history | repo/backend/app/modules/bookings/controller.py:70::get_booking_history |
| GET /api/v1/bookings/{booking_id} | repo/backend/app/modules/bookings/controller.py:139::get_booking |
| PATCH /api/v1/bookings/{booking_id}/confirm | repo/backend/app/modules/bookings/controller.py:144::confirm_booking |
| POST /api/v1/bookings/{booking_id}/reschedule | repo/backend/app/modules/bookings/controller.py:153::reschedule_booking |
| POST /api/v1/bookings/{booking_id}/cancel | repo/backend/app/modules/bookings/controller.py:163::cancel_booking |
| POST /api/v1/sessions/{session_id}/attendance/checkin | repo/backend/app/modules/attendance/controller.py:16::checkin |
| POST /api/v1/sessions/{session_id}/attendance/checkout | repo/backend/app/modules/attendance/controller.py:28::checkout |
| GET /api/v1/sessions/{session_id}/attendance/stats | repo/backend/app/modules/attendance/controller.py:40::get_stats |
| POST /api/v1/checkout/cart | repo/backend/app/modules/checkout/controller.py:15::create_cart |
| POST /api/v1/checkout/best-offer | repo/backend/app/modules/checkout/controller.py:24::get_best_offer |
| GET /api/v1/orders | repo/backend/app/modules/checkout/controller.py:33::list_orders |
| GET /api/v1/orders/{order_id} | repo/backend/app/modules/checkout/controller.py:45::get_order |
| PATCH /api/v1/orders/{order_id}/cancel | repo/backend/app/modules/checkout/controller.py:54::cancel_order |
| GET /api/v1/payments | repo/backend/app/modules/payments/controller.py:18::list_payments |
| POST /api/v1/payments/callback | repo/backend/app/modules/payments/controller.py:29::payment_callback |
| POST /api/v1/payments/{order_id}/simulate | repo/backend/app/modules/payments/controller.py:35::simulate_payment |
| GET /api/v1/payments/{order_id} | repo/backend/app/modules/payments/controller.py:41::get_payment |
| GET /api/v1/refunds | repo/backend/app/modules/payments/controller.py:46::list_refunds |
| POST /api/v1/refunds | repo/backend/app/modules/payments/controller.py:55::create_refund |
| GET /api/v1/refunds/{refund_id} | repo/backend/app/modules/payments/controller.py:60::get_refund |
| PATCH /api/v1/refunds/{refund_id}/review | repo/backend/app/modules/payments/controller.py:65::review_refund |
| PATCH /api/v1/refunds/{refund_id}/approve | repo/backend/app/modules/payments/controller.py:71::approve_refund |
| PATCH /api/v1/refunds/{refund_id}/reject | repo/backend/app/modules/payments/controller.py:77::reject_refund |
| PATCH /api/v1/refunds/{refund_id}/process | repo/backend/app/modules/payments/controller.py:83::process_refund |
| PATCH /api/v1/refunds/{refund_id}/complete | repo/backend/app/modules/payments/controller.py:89::complete_refund |
| POST /api/v1/reconciliation/export | repo/backend/app/modules/payments/controller.py:95::trigger_reconciliation |
| GET /api/v1/reconciliation/export | repo/backend/app/modules/payments/controller.py:106::trigger_reconciliation_get |
| GET /api/v1/reconciliation/exports | repo/backend/app/modules/payments/controller.py:118::list_exports |
| GET /api/v1/reconciliation/exports/{export_id}/download | repo/backend/app/modules/payments/controller.py:123::download_export |
| GET /api/v1/audit-logs | repo/backend/app/modules/audit/controller.py:31::list_audit_logs |
| GET /api/v1/sessions/{session_id}/recordings | repo/backend/app/modules/replays/controller.py:48::list_recordings |
| GET /api/v1/sessions/{session_id}/recordings/{recording_id}/stream | repo/backend/app/modules/replays/controller.py:58::stream_recording |
| GET /api/v1/sessions/{session_id}/replay | repo/backend/app/modules/replays/controller.py:122::get_replay |
| POST /api/v1/sessions/{session_id}/replay/upload | repo/backend/app/modules/replays/controller.py:131::initiate_upload |
| PATCH /api/v1/sessions/{session_id}/replay/recording | repo/backend/app/modules/replays/controller.py:141::confirm_upload |
| POST /api/v1/sessions/{session_id}/replay/recording/data | repo/backend/app/modules/replays/controller.py:155::upload_recording_direct |
| POST /api/v1/sessions/{session_id}/replay/access-rule | repo/backend/app/modules/replays/controller.py:172::set_access_rule |
| POST /api/v1/replays/{session_id}/view | repo/backend/app/modules/replays/controller.py:182::record_view |
| GET /api/v1/replays/{session_id}/stats | repo/backend/app/modules/replays/controller.py:192::get_replay_stats |
| GET /api/v1/instructors | repo/backend/app/modules/instructors/controller.py:32::list_instructors |
| POST /api/v1/instructors | repo/backend/app/modules/instructors/controller.py:41::create_instructor |
| GET /api/v1/instructors/{instructor_id} | repo/backend/app/modules/instructors/controller.py:51::get_instructor |
| PATCH /api/v1/instructors/{instructor_id} | repo/backend/app/modules/instructors/controller.py:60::update_instructor |
| DELETE /api/v1/instructors/{instructor_id} | repo/backend/app/modules/instructors/controller.py:72::delete_instructor |
| GET /api/v1/monitoring/health | repo/backend/app/modules/monitoring/controller.py:18::health |
| GET /api/v1/monitoring/metrics | repo/backend/app/modules/monitoring/controller.py:23::metrics |
| GET /api/v1/monitoring/metrics/scrape | repo/backend/app/modules/monitoring/controller.py:30::metrics_scrape |
| GET /api/v1/monitoring/alerts | repo/backend/app/modules/monitoring/controller.py:46::get_alerts |
| PATCH /api/v1/monitoring/alerts/{alert_id}/resolve | repo/backend/app/modules/monitoring/controller.py:61::resolve_alert |
| GET /api/v1/locations | repo/backend/app/modules/locations/controller.py:17::list_locations |
| POST /api/v1/locations | repo/backend/app/modules/locations/controller.py:22::create_location |
| GET /api/v1/locations/{location_id} | repo/backend/app/modules/locations/controller.py:27::get_location |
| PATCH /api/v1/locations/{location_id} | repo/backend/app/modules/locations/controller.py:32::update_location |
| DELETE /api/v1/locations/{location_id} | repo/backend/app/modules/locations/controller.py:37::delete_location |
| GET /api/v1/locations/{location_id}/rooms | repo/backend/app/modules/locations/controller.py:42::list_rooms |
| POST /api/v1/locations/{location_id}/rooms | repo/backend/app/modules/locations/controller.py:47::create_room |
| GET /api/v1/policy | repo/backend/app/modules/policy/controller.py:12::get_policy |
| PATCH /api/v1/policy | repo/backend/app/modules/policy/controller.py:17::update_policy |
| POST /api/v1/promotions/preview | repo/backend/app/modules/promotions/controller.py:20::preview_offer |
| GET /api/v1/promotions | repo/backend/app/modules/promotions/controller.py:26::list_promotions |
| POST /api/v1/promotions | repo/backend/app/modules/promotions/controller.py:35::create_promotion |
| GET /api/v1/promotions/{promo_id} | repo/backend/app/modules/promotions/controller.py:45::get_promotion |
| PATCH /api/v1/promotions/{promo_id} | repo/backend/app/modules/promotions/controller.py:54::update_promotion |
| DELETE /api/v1/promotions/{promo_id} | repo/backend/app/modules/promotions/controller.py:70::delete_promotion |
| GET /api/v1/users | repo/backend/app/modules/users/controller.py:16::list_users |
| POST /api/v1/users | repo/backend/app/modules/users/controller.py:30::create_user |
| GET /api/v1/users/me | repo/backend/app/modules/users/controller.py:39::get_me |
| GET /api/v1/users/{user_id} | repo/backend/app/modules/users/controller.py:44::get_user |
| PATCH /api/v1/users/{user_id} | repo/backend/app/modules/users/controller.py:58::update_user |
| DELETE /api/v1/users/{user_id} | repo/backend/app/modules/users/controller.py:68::delete_user |
| POST /api/v1/users/{user_id}/unmask | repo/backend/app/modules/users/controller.py:77::unmask_user_pii |
| POST /api/v1/search | repo/backend/app/modules/search/controller.py:18::search |
| GET /api/v1/search/saved | repo/backend/app/modules/search/controller.py:31::list_saved_searches |
| POST /api/v1/search/saved | repo/backend/app/modules/search/controller.py:36::save_search |
| DELETE /api/v1/search/saved/{search_id} | repo/backend/app/modules/search/controller.py:41::delete_saved_search |
| POST /api/v1/search/export/jobs | repo/backend/app/modules/search/controller.py:46::trigger_export_job |
| GET /api/v1/search/export/jobs/{job_id} | repo/backend/app/modules/search/controller.py:72::get_export_job |
| GET /api/v1/search/export/jobs/{job_id}/download | repo/backend/app/modules/search/controller.py:84::download_export_file |
| GET /api/v1/jobs | repo/backend/app/modules/jobs/controller.py:20::list_jobs |
| GET /api/v1/jobs/stats/aggregate | repo/backend/app/modules/jobs/controller.py:26::get_aggregate_stats |
| POST /api/v1/jobs/{job_name}/trigger | repo/backend/app/modules/jobs/controller.py:88::trigger_job |
| GET /api/v1/jobs/{job_name}/executions | repo/backend/app/modules/jobs/controller.py:115::list_executions |
| GET /api/v1/ingestion/sources | repo/backend/app/modules/ingestion/controller.py:19::list_sources |
| POST /api/v1/ingestion/sources | repo/backend/app/modules/ingestion/controller.py:24::create_source |
| GET /api/v1/ingestion/sources/{source_id} | repo/backend/app/modules/ingestion/controller.py:29::get_source |
| PATCH /api/v1/ingestion/sources/{source_id} | repo/backend/app/modules/ingestion/controller.py:34::update_source |
| DELETE /api/v1/ingestion/sources/{source_id} | repo/backend/app/modules/ingestion/controller.py:39::delete_source |
| POST /api/v1/ingestion/sources/{source_id}/test-connection | repo/backend/app/modules/ingestion/controller.py:44::test_connection |
| POST /api/v1/ingestion/sources/{source_id}/trigger | repo/backend/app/modules/ingestion/controller.py:49::trigger_ingestion |
| GET /api/v1/ingestion/sources/{source_id}/runs | repo/backend/app/modules/ingestion/controller.py:54::list_runs |
| GET /api/v1/ingestion/runs/{run_id} | repo/backend/app/modules/ingestion/controller.py:59::get_run |
| POST /api/v1/ingestion/webhook/{source_id} | repo/backend/app/modules/ingestion/controller.py:71::ingest_webhook |
| WS /api/ws/sessions/{session_id}/room | repo/backend/app/modules/sessions/websocket.py:185::session_room_ws |

### API Test Mapping Table
- API test files scanned: `repo/backend/tests/api/test_*.py`.
- Static mapping result: all 115 HTTP endpoints have direct HTTP-call evidence in API tests.
- Per-endpoint type: true no-mock HTTP for HTTP endpoints; WebSocket endpoint covered by protocol tests and admission tests.

| Endpoint Set | Covered | Test Type | Test Files | Evidence |
|---|---|---|---|---|
| 115/115 HTTP endpoints | yes | true no-mock HTTP (endpoint-level) | repo/backend/tests/api/*.py | examples: repo/backend/tests/api/test_auth.py::test_login_success, repo/backend/tests/api/test_payments.py::test_valid_callback, repo/backend/tests/api/test_search.py::* |
| WS /api/ws/sessions/{session_id}/room | yes | protocol + handler-admission tests | repo/backend/tests/api/test_websocket_protocol.py; repo/backend/tests/api/test_websocket_admission.py | protocol connect/close assertions + admission checks |

### API Test Classification
- Total API test files inspected: 32.
- Classification counts:
  - True No-Mock HTTP: 24
  - HTTP with Mocking: 8
  - Non-HTTP (unit/integration without HTTP): 0

Mocking detected (WHAT + WHERE):
- `repo/backend/tests/api/test_websocket_admission.py:18` imports `AsyncMock` and `patch`.
- `repo/backend/tests/api/test_websocket_admission.py:113,125,137,152,167,193` patches `app.modules.sessions.websocket.get_ws_user`.
- `repo/backend/tests/api/test_websocket_admission.py:153,154,168,169,194,195` patches `room_manager.broadcast` and `room_manager.send_state_snapshot`.

### Coverage Summary
- Total endpoints: 116
- HTTP endpoints with HTTP tests: 115/115
- HTTP endpoints with TRUE no-mock tests: 115/115
- WebSocket protocol-covered endpoints: 1/1
- HTTP coverage %: 100.0%
- True API coverage %: 100.0%

### Unit Test Summary
#### Backend Unit Tests
- Unit test files: 22 under `repo/backend/tests/unit/`.
- Modules covered (inferred): auth/security, attendance, audit chain, bookings state, checkout/best-offer, courses/instructors, encryption, ingestion models, payments models, policy, promotions, replays models, role guards, search models/scope, sessions service.
- Important backend modules NOT unit-tested (direct service-level isolation): jobs task orchestration, ingestion service/webhook flow, full payments refund service transitions, websocket room manager internals.

#### Frontend Unit Tests (STRICT)
- Frontend test files detected: 34 under `repo/frontend/src/tests/**/*.spec.ts`.
- Framework/tooling evidence:
  - `repo/frontend/package.json` has `"test": "vitest run"`.
  - `repo/frontend/package.json` includes `vitest`, `@vue/test-utils`, `@testing-library/vue`.
  - `repo/frontend/src/tests/setup.ts` initializes Vue test environment and Pinia.
- Tests import/render actual frontend modules evidence:
  - `repo/frontend/src/tests/components/auth/LoginPage.spec.ts:47` mounts login page component.
  - `repo/frontend/src/tests/components/calendar/WeekCalendar.spec.ts:4` imports `@/components/calendar/WeekCalendar.vue`.
  - `repo/frontend/src/tests/components/calendar/MonthCalendar.spec.ts:4` imports `@/components/calendar/MonthCalendar.vue`.
  - `repo/frontend/src/tests/components/search/SavedSearchSidebar.spec.ts:4` imports `@/components/search/SavedSearchSidebar.vue`.
- Important frontend modules/components not directly evidenced in sampled test imports: some page-level operational screens may be covered by shallow group specs rather than deep behavioral tests.
- Frontend unit tests: PRESENT
- CRITICAL GAP: not flagged under strict missing-rule (tests are present with framework + real component imports/mounts).

### Cross-Layer Observation
- Backend API coverage is exhaustive by endpoint count.
- Frontend has substantial unit/component/store tests and dedicated browser E2E files under `repo/frontend/e2e/`.
- Testing posture is backend-strong, but frontend is not missing.

### API Observability Check
- Strong observability in HTTP API tests:
  - Explicit method/path calls (example: `repo/backend/tests/api/test_auth.py`).
  - Explicit request payload/header usage (example: `repo/backend/tests/api/test_payments.py`).
  - Explicit response assertions on status/body fields (examples: `repo/backend/tests/api/test_auth.py`, `repo/backend/tests/api/test_search.py`).
- Weak spots:
  - WebSocket admission tests use targeted mocks to isolate admission paths, reducing full transport-path realism in those specific tests.

### Test Quality & Sufficiency
- Success paths: strong across auth, bookings, sessions, checkout, payments, search, ingestion, monitoring.
- Failure/authz paths: explicit negative tests present in authorization and domain suites.
- Edge-case depth: present in callbacks, refunds, exports, and websocket protocol handling.
- Integration boundaries: HTTP layer is broadly exercised with async client requests.

### Tests Check
- `repo/run_tests.sh` is Docker-based for backend and frontend test execution.
- Evidence:
  - docker compose detection and use: `repo/run_tests.sh:20`, `repo/run_tests.sh:49`.
  - backend pytest in running container: `repo/run_tests.sh:93`.
  - frontend tests via Docker image and containerized npm test: `repo/run_tests.sh:113`, `repo/run_tests.sh:119`.
- No mandatory local `npm install`/`pip install` in script.

### End-to-End Expectations
- Fullstack expectation: FE↔BE browser-level tests should exist.
- Evidence: Playwright specs present in `repo/frontend/e2e/`.
- Result: E2E suite exists (static presence confirmed).

### Test Coverage Score (0-100)
- Score: 93

### Score Rationale
- +40: complete endpoint inventory and HTTP endpoint mapping coverage.
- +25: true no-mock HTTP coverage across HTTP endpoints.
- +15: broad failure/authz path assertions.
- +8: backend + frontend unit/component test presence.
- +5: frontend browser E2E suite present.

### Key Gaps
- Some API test files use mocking for websocket admission internals; transport realism is weaker there.
- Some high-value service internals are validated more by API tests than by dedicated unit-isolated service tests.

### Confidence & Assumptions
- Confidence: high for endpoint counts and route inventory (decorator-level static extraction).
- Confidence: medium-high for endpoint-to-test mapping totals (static request-call mapping in API tests).
- Assumption: all APIRouter HTTP controllers are mounted under `/api/v1` as declared in `backend/app/main.py`.

### Test Audit Verdict
- PASS

---

## 2) README Audit

### README Location
- File exists at required location: `repo/README.md`.

### Hard Gate Checklist
| Gate | Result | Evidence |
|---|---|---|
| README exists at `repo/README.md` | PASS | `repo/README.md` |
| Project type declared | PASS | `repo/README.md:3` |
| Backend/fullstack startup includes docker-compose up | PASS | `repo/README.md:35` (`docker-compose up --build -d`) |
| Access method includes URL + port | PASS | `repo/README.md:50-56` |
| Verification method documented | PASS | `repo/README.md:66-83` |
| Environment rules (no npm/pip/apt/runtime/manual DB setup) | PASS | No `npm install`/`pip install`/`apt-get`/runtime-install/manual DB setup commands found in `repo/README.md`; E2E section explicitly states no local install required |
| Demo credentials include all roles (auth exists) | PASS | `repo/README.md:118-126` (Admin, Instructor, Learner, Finance, DataOps) |

### High Priority Issues
- None.

### Medium Priority Issues
- `chmod +x run_tests.sh` in README testing instructions is Unix-centric and not explicitly paired with Windows-native execution guidance.

### Low Priority Issues
- Frontend verification flow is brief and admin-centric; role-specific flows could be expanded for stronger operational validation.

### Hard Gate Failures
- None.

### README Verdict (PASS / PARTIAL PASS / FAIL)
- PASS

---

## Final Combined Verdicts
- Test Coverage Audit: PASS
- README Audit: PASS
- Overall Combined: PASS
