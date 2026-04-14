# Meridian Previous Inspection Recheck (Static)

Date: 2026-04-13
Source baseline: .tmp/static-audit-meridian-2026-04-13.md
Method: Static repository review only (no runtime execution, no tests run in this recheck)

## Overall Result

- Previous Blocker/High items: 6 of 6 are now addressed in code/migrations.
- Additional previously flagged partial gaps reviewed: 5 addressed, 2 remain runtime-verification items.
- Static acceptance posture now: major improvement, with remaining risk concentrated in operational behavior under failure/restart.

## Issue-by-Issue Status

1. Password hashing did not meet Argon2id requirement
- Prior severity: Blocker
- Current status: Fixed
- Evidence:
  - repo/backend/app/core/security.py:15
  - repo/backend/app/core/security.py:45
  - repo/backend/app/modules/auth/service.py:40
  - repo/backend/app/modules/auth/service.py:60
  - repo/backend/requirements.txt:8
  - repo/backend/tests/unit/test_security.py:48

2. Search endpoint lacked role-scope filtering for instructor/finance
- Prior severity: High
- Current status: Fixed
- Evidence:
  - repo/backend/app/modules/search/controller.py:21
  - repo/backend/app/modules/search/controller.py:26
  - repo/backend/app/modules/search/service.py:30
  - repo/backend/app/modules/search/service.py:42
  - repo/backend/app/modules/search/service.py:45
  - repo/backend/tests/unit/test_search_scope.py:44
  - repo/backend/tests/unit/test_search_scope.py:69

3. PII unmask controls (permission + reason + audit) were missing
- Prior severity: High
- Current status: Fixed
- Evidence:
  - repo/backend/app/modules/users/controller.py:77
  - repo/backend/app/modules/users/controller.py:80
  - repo/backend/app/modules/users/service.py:106
  - repo/backend/app/modules/users/service.py:120
  - repo/backend/app/modules/users/service.py:133
  - repo/backend/app/modules/users/schemas.py:45
  - repo/backend/tests/unit/test_unmask_audit.py:61

4. Callback idempotency by external_event_id was missing
- Prior severity: High
- Current status: Fixed
- Evidence:
  - repo/backend/app/modules/payments/schemas.py:18
  - repo/backend/app/modules/payments/models.py:31
  - repo/backend/app/modules/payments/models.py:37
  - repo/backend/app/modules/payments/service.py:52
  - repo/backend/app/modules/payments/service.py:56
  - repo/backend/app/modules/payments/service.py:161
  - repo/backend/alembic/versions/0006_security_hardening.py:1
  - repo/backend/tests/unit/test_external_event_id_dedup.py:87

5. Promotion tie-break determinism was incomplete
- Prior severity: High
- Current status: Fixed
- Evidence:
  - repo/backend/app/modules/checkout/best_offer.py:81
  - repo/backend/app/modules/checkout/best_offer.py:83
  - repo/backend/app/modules/checkout/best_offer.py:132
  - repo/backend/app/modules/checkout/service.py:59
  - repo/backend/alembic/versions/0006_security_hardening.py:1
  - repo/backend/tests/unit/test_best_offer.py:103

6. Audit tamper-evidence chain was not implemented
- Prior severity: High
- Current status: Fixed
- Evidence:
  - repo/backend/app/modules/audit/models.py:26
  - repo/backend/app/modules/audit/models.py:27
  - repo/backend/app/core/audit.py:18
  - repo/backend/app/core/audit.py:83
  - repo/backend/alembic/versions/0006_security_hardening.py:1
  - repo/backend/tests/unit/test_audit_chain.py:1

7. Instructor overlap prevention not explicit
- Prior severity: Medium (section gap)
- Current status: Fixed
- Evidence:
  - repo/backend/app/modules/sessions/service.py:68
  - repo/backend/app/modules/sessions/service.py:100
  - repo/backend/app/modules/sessions/service.py:141

8. Recurrence default horizon diverged from 180-day requirement
- Prior severity: Medium (section gap)
- Current status: Fixed
- Evidence:
  - repo/backend/app/modules/sessions/service.py:127

9. Search export behavior was synchronous instead of async job contract
- Prior severity: High (section gap)
- Current status: Fixed
- Evidence:
  - repo/backend/app/modules/search/controller.py:46
  - repo/backend/app/modules/search/controller.py:72
  - repo/backend/app/modules/search/controller.py:82
  - repo/backend/app/modules/jobs/tasks.py:283
  - repo/backend/app/modules/jobs/tasks.py:316
  - repo/backend/app/modules/search/models.py:19
  - repo/backend/alembic/versions/0007_search_export_jobs.py:1

10. Structured logging with request/job correlation IDs was not evident
- Prior severity: Medium (section gap)
- Current status: Fixed
- Evidence:
  - repo/backend/app/core/logging.py:32
  - repo/backend/app/core/logging.py:46
  - repo/backend/app/main.py:11
  - repo/backend/app/main.py:25
  - repo/backend/app/modules/jobs/tasks.py:290

11. Ingestion dedup fingerprint did not match PRD tuple
- Prior severity: Medium (section gap)
- Current status: Fixed
- Evidence:
  - repo/backend/app/modules/ingestion/adapters/batch_adapter.py:21
  - repo/backend/app/modules/ingestion/adapters/batch_adapter.py:33
  - repo/backend/app/modules/ingestion/adapters/batch_adapter.py:40
  - repo/backend/app/modules/ingestion/adapters/batch_adapter.py:50

12. Restart-safe requeue/resume behavior under worker failure
- Prior severity: Medium (section gap)
- Current status: Partially addressed, still requires runtime verification
- Evidence:
  - repo/backend/app/modules/jobs/celery_app.py:19
  - repo/backend/app/modules/jobs/celery_app.py:20
  - repo/backend/app/modules/jobs/celery_app.py:21
- Note: The Celery reliability knobs are configured, but failure-injection evidence was not executed in this static recheck.

13. Deterministic reprocessing guarantees across restart/state persistence
- Prior severity: Medium (section gap)
- Current status: Improved but still requires runtime verification
- Evidence:
  - repo/backend/app/modules/ingestion/adapters/batch_adapter.py:21
  - repo/backend/app/modules/ingestion/adapters/batch_adapter.py:72
- Note: Fingerprint implementation is aligned, but restart semantics depend on runtime persistence and deployment behavior.

## Delta vs Prior Inspection

- All previously reported Blocker/High findings now have concrete implementation evidence in code and schema.
- Remaining open items are operational validation items that cannot be fully concluded via static review only.

## Suggested Runtime Validation (Optional Next Step)

1. Kill a worker mid-task to validate requeue/resume behavior and idempotent completion.
2. Replay payment callbacks with the same external_event_id under concurrency.
3. Restart Redis/Celery during ingestion and verify duplicate suppression and replay determinism.
4. Exercise search export queue, poll, and download flow end-to-end in a running stack.
