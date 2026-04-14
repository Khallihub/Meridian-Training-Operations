This file captures implementation assumptions derived from docs/prompt.md in a
Question / My Understanding / Solution format.

---

## 1) Time zone behavior for schedule display and storage

Question: The prompt says users browse the calendar in their chosen time zone,
but it does not define a canonical storage zone.
My Understanding: All session datetimes should be stored in UTC and converted
to each user profile time zone at read time.
Solution: Store all timestamps in UTC, persist an IANA time zone per user, and
apply server-side conversion for API responses and recurrence calculations.

## 2) Recurring session generation horizon

Question: The prompt provides recurring examples but does not state how far into
the future sessions should be generated when no explicit end date is provided.
My Understanding: A bounded generation window is required to avoid unbounded
writes and slow calendar queries.
Solution: Use a default 180-day recurrence horizon unless an explicit end date
is supplied.

## 3) Capacity hold policy during checkout

Question: Capacity limits are defined, but the prompt does not specify whether a
seat is held while payment is pending.
My Understanding: A temporary hold is needed to prevent overselling during
offline payment flow.
Solution: Reserve seats at booking confirmation with a payment window; release
the hold automatically on timeout or failed payment.

## 4) Cancellation fee application logic

Question: The prompt says learner cancellations within 24 hours can be flagged
for a policy fee, but it does not define auto-charge vs manual review.
My Understanding: Fee application should be policy-driven and reviewable.
Solution: Mark eligible cancellations with a fee_pending flag and let Finance
confirm or waive based on policy rules.

## 5) Replay availability and access revocation timing

Question: Replay access is described as "only enrolled learners" and time-bound,
but revocation behavior after cancellation or refund is not explicit.
My Understanding: Replay access should reflect active entitlement in near
real-time.
Solution: Recompute replay entitlement from booking/payment status on each
access request and enforce expiry at session_end + replay_window_days.

## 6) Promotion stacking conflict resolution

Question: The prompt states mutual exclusion by default but does not define tie
breaking when multiple valid promotions produce the same discount.
My Understanding: Deterministic selection is required for receipts and auditing.
Solution: Apply sorting by discount DESC, priority ASC, promotion_id ASC and
persist the applied promotion trace on the order.

## 7) Offline payment callback idempotency

Question: Payment callbacks are required, but duplicate callback handling is not
fully specified.
My Understanding: Callback processing must be idempotent to avoid duplicate
order transitions.
Solution: Enforce idempotency with external_event_id unique constraints and a
fallback Redis dedup key for simulator or legacy payloads.

## 8) Search export consistency at high row counts

Question: Export up to 50,000 rows is required, but the prompt does not define
synchronous vs asynchronous behavior.
My Understanding: Large exports should be asynchronous to keep API latency
predictable.
Solution: Use an export job model (queue, poll status, download when complete)
with server-side file generation and retry handling.

## 9) Saved search lifecycle limits

Question: The prompt limits saved searches to 20 per user, but replacement
behavior at limit is not specified.
My Understanding: The system should prevent silent replacement.
Solution: Return a validation error when creating the 21st saved search unless
the user explicitly deletes one or updates an existing saved search.

## 10) PII masking and controlled unmask flow

Question: The prompt requires masked phone numbers and encryption at rest, but
does not define an operational unmask path for support workflows.
My Understanding: Unmask must be explicit, justified, and auditable.
Solution: Keep masked values in standard responses; provide an admin-only unmask
endpoint requiring a reason and always writing an audit log event.

## 11) Account lockout reset semantics

Question: The prompt defines lockout after 5 failed attempts for 15 minutes but
does not define how failed-attempt counters reset.
My Understanding: Counter reset should happen on successful login and after
lockout expiry.
Solution: Track failed_attempt_count and locked_until; reset counters on
successful authentication or once locked_until has elapsed.

## 12) Job alert thresholds and evaluation window

Question: The prompt specifies alerts for failure rate above 2% in one hour and
lateness above 10 minutes, but does not define the evaluation cadence.
My Understanding: Alert evaluation should run on a fixed short interval and use
rolling windows.
Solution: Evaluate every minute using a rolling 60-minute failure window and a
per-job expected_run_time comparison for lateness.
