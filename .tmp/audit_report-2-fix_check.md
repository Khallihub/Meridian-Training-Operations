# Meridian Inspection Recheck (Static)

Date: 2026-04-13  
Method: Static code re-inspection only (no runtime execution, no test execution)
Source issues reviewed: repo/.tmp/audit_report-2.md

## Recheck Summary

- Fixed: 5
- Partially Fixed: 0
- Not Fixed: 0

## Issue-by-Issue Status

### 1) Search export UX still wired to removed synchronous endpoint
Status: Fixed

Current evidence:
- Frontend export now creates async job via /api/v1/search/export/jobs in repo/frontend/src/composables/useExport.ts:24.
- Frontend polls /api/v1/search/export/jobs/{id} in repo/frontend/src/composables/useExport.ts:47.
- Frontend downloads from /api/v1/search/export/jobs/{id}/download in repo/frontend/src/composables/useExport.ts:57.
- API client also uses async job contract in repo/frontend/src/api/endpoints/search.ts:21 and repo/frontend/src/api/endpoints/search.ts:31.

Conclusion:
- The previously reported sync-export contract drift is resolved.

### 2) Promotions UI/backend contract mismatch (legacy enums + invalid preview payload)
Status: Fixed

Current evidence:
- Frontend promotion type now uses canonical enum values in repo/frontend/src/api/endpoints/admin.ts:51.
- Promotion form defaults and options now use canonical values in repo/frontend/src/pages/promotions/PromotionFormPage.vue:17 and repo/frontend/src/pages/promotions/PromotionFormPage.vue:81.
- Promotion list formatter now handles canonical enum values in repo/frontend/src/pages/promotions/PromotionListPage.vue:27 and repo/frontend/src/pages/promotions/PromotionListPage.vue:30.
- Preview payload now sends cart-style items in repo/frontend/src/pages/promotions/PromotionFormPage.vue:61.
- Backend preview endpoint still expects CartCreate (items) in repo/backend/app/modules/promotions/controller.py:21 and repo/backend/app/modules/checkout/schemas.py:16.

Conclusion:
- Enum/value and preview payload mismatches are resolved.

### 3) Search export job object-level authorization missing (IDOR risk)
Status: Fixed

Current evidence:
- Controller passes caller context into export-job reads in repo/backend/app/modules/search/controller.py:79 and repo/backend/app/modules/search/controller.py:92.
- Service signature includes caller context in repo/backend/app/modules/search/service.py:429.
- Service enforces non-admin ownership check against created_by in repo/backend/app/modules/search/service.py:442 and repo/backend/app/modules/search/service.py:444.
- Ownership field exists in model in repo/backend/app/modules/search/models.py:38.

Conclusion:
- The previously reported export-job ownership gap is resolved.

### 4) Booking endpoints overbroad for staff (ABAC scope gap)
Status: Fixed

Current evidence:
- Instructor list scope is constrained by instructor ownership in repo/backend/app/modules/bookings/controller.py:48 and repo/backend/app/modules/bookings/controller.py:61, with repository support in repo/backend/app/modules/bookings/repository.py:56.
- Finance list now requires session_id and passes a dedicated finance payment-scope flag in repo/backend/app/modules/bookings/controller.py:39, repo/backend/app/modules/bookings/controller.py:44, and repo/backend/app/modules/bookings/controller.py:65.
- Repository now enforces row-level payment-context filtering for finance list requests via EXISTS on session+learner order linkage in repo/backend/app/modules/bookings/repository.py:61 and repo/backend/app/modules/bookings/repository.py:67.
- Instructor confirm enforces session ownership in repo/backend/app/modules/bookings/service.py:55 and repo/backend/app/modules/bookings/service.py:64.
- Booking history applies role-specific checks and denies non-authorized roles in repo/backend/app/modules/bookings/controller.py:81 and repo/backend/app/modules/bookings/controller.py:118.
- Booking get enforces instructor/finance object-level checks in repo/backend/app/modules/bookings/service.py:187 and repo/backend/app/modules/bookings/service.py:199.

Conclusion:
- The previously reported booking ABAC gap is resolved in current static code.

### 5) Calendar day grouping not consistently honoring selected timezone
Status: Fixed

Current evidence:
- Month calendar now groups sessions by timezone-normalized yyyy-MM-dd using formatInTimeZone in repo/frontend/src/components/calendar/MonthCalendar.vue:42 and repo/frontend/src/components/calendar/MonthCalendar.vue:45.
- Week calendar day bucketing now compares session day and column day in selected timezone in repo/frontend/src/components/calendar/WeekCalendar.vue:47 and repo/frontend/src/components/calendar/WeekCalendar.vue:49.
- Week vertical placement now derives time from selected timezone in repo/frontend/src/components/calendar/WeekCalendar.vue:60.

Conclusion:
- The timezone bucketing inconsistency reported previously is resolved.

## Testing Follow-up (Static Observation)

No new dedicated tests were found for the newly tightened booking ABAC logic or async export job ownership checks in the currently visible test suite. Static fix verification is positive, but runtime/test validation is still recommended.
