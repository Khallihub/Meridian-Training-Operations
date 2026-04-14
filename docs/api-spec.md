# Meridian Training Operations API Spec

## Table Of Contents
1. API Overview
2. Global Conventions
3. Authentication And Authorization
4. System And Documentation Endpoints
5. Auth APIs
6. User APIs
7. Location And Room APIs
8. Course APIs
9. Instructor APIs
10. Session APIs
11. Attendance APIs
12. Booking APIs
13. Replay APIs
14. Promotion APIs
15. Checkout And Order APIs
16. Payment, Refund, Reconciliation APIs
17. Search APIs
18. Ingestion APIs
19. Job APIs
20. Monitoring APIs
21. Audit APIs
22. Admin Policy APIs
23. WebSocket API
24. Common Schema Reference
25. Assumptions

## API Overview
- Service: Meridian Training Operations API
- Framework: FastAPI
- Base REST prefix: /api/v1
- WebSocket path family: /api/ws
- REST endpoint count (application routers): 118
- WebSocket endpoint count: 1
- Additional framework endpoints: 3 (docs, redoc, openapi)
- API styles detected: REST, WebSocket (no GraphQL, no gRPC/RPC transport)

## Global Conventions
- Content type: application/json for most REST endpoints.
- Response envelope for JSON APIs under /api/v1:
  - Success: { data, meta, error: null }
  - Error: { data: null, meta, error: { code, message, details[] } }
- meta object fields:
  - request_id: string UUID
  - timestamp: ISO-8601 UTC
  - version: v1
- Common error codes mapped by middleware:
  - 400 BAD_REQUEST
  - 401 UNAUTHORIZED
  - 403 FORBIDDEN
  - 404 NOT_FOUND
  - 409 CONFLICT
  - 410 GONE
  - 422 VALIDATION_ERROR
  - 423 ACCOUNT_LOCKED
  - 500 INTERNAL_SERVER_ERROR
- Pagination shape where used:
  - data.items: array
  - data.meta: { total_count, page, page_size, has_next }

## Authentication And Authorization
- Bearer JWT (OAuth2PasswordBearer tokenUrl=/api/v1/auth/login)
  - Header: Authorization: Bearer <access_token>
- Role guard dependency
  - require_roles(admin|instructor|learner|finance|dataops)
- WebSocket auth
  - Query token: ?token=<access_token>
- Special auth headers
  - X-Api-Key for ingestion webhook
  - Authorization: Bearer <PROMETHEUS_SCRAPE_TOKEN> for monitoring scrape endpoint
- Public endpoints
  - POST /api/v1/auth/login
  - POST /api/v1/auth/refresh
  - POST /api/v1/payments/callback (signature verified)
  - GET /api/v1/monitoring/health

## System And Documentation Endpoints

| Method | Path | Description | Auth | Request | Response |
|---|---|---|---|---|---|
| GET | /api/v1/docs | Swagger UI | Public | None | HTML page |
| GET | /api/v1/redoc | ReDoc UI | Public | None | HTML page |
| GET | /api/v1/openapi.json | OpenAPI schema | Public | None | JSON OpenAPI document |

Examples:

    GET /api/v1/openapi.json

    200 OK
    {
      "openapi": "3.x",
      "paths": { "...": {} }
    }

## Auth APIs
Body schemas:
- LoginRequest { username, password }
- RefreshRequest { refresh_token }
- ChangePasswordRequest { current_password, new_password }
  - Validation: new_password must pass password complexity checks.

Response schemas:
- TokenResponse { access_token, refresh_token, token_type }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| POST | /api/v1/auth/login | Sign in user and issue access/refresh tokens. | Public | None | None | Content-Type | LoginRequest | 200 TokenResponse | 401 invalid credentials, 423 lockout, 422 validation |
| POST | /api/v1/auth/refresh | Rotate refresh token and issue new pair. | Public | None | None | Content-Type | RefreshRequest | 200 TokenResponse | 401 invalid/used token, inactivity expiry |
| POST | /api/v1/auth/logout | Revoke refresh tokens and blocklist access token. | Bearer | None | None | Authorization | None | 204 No Content | 401 unauthenticated |
| POST | /api/v1/auth/change-password | Update password and revoke refresh tokens. | Bearer | None | None | Authorization, Content-Type | ChangePasswordRequest | 204 No Content | 401 current password invalid, 422 password complexity |

Examples:

    POST /api/v1/auth/login
    Content-Type: application/json

    {
      "username": "admin",
      "password": "StrongPass1!"
    }

    200 OK
    {
      "data": {
        "access_token": "...",
        "refresh_token": "...",
        "token_type": "bearer"
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## User APIs
Body schemas:
- UserCreate { username, password, role, email?, phone? }
  - Validation: password complexity enforced.
- UserUpdate { email?, phone?, is_active?, role? }

Response schemas:
- UserResponse { id, username, role, email(masked), phone(masked), is_active, last_login, created_at }
- UserDetailResponse (same shape as masked UserResponse)
- UserUnmaskResponse { id, username, email_unmasked?, phone_unmasked?, reason }
- Page<UserDetailResponse>

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/users | List users (admin only, paginated). | Bearer + role admin | None | page>=1, page_size 1..200, role?, is_active? | Authorization | None | 200 Page<UserDetailResponse> | 403 role denied, 422 query validation |
| POST | /api/v1/users | Create user. | Bearer + role admin | None | None | Authorization, Content-Type | UserCreate | 201 UserDetailResponse | 409 username exists, 422 validation |
| GET | /api/v1/users/me | Current user profile. | Bearer | None | None | Authorization | None | 200 UserResponse | 401 |
| GET | /api/v1/users/{user_id} | Get one user (admin or self). | Bearer | user_id UUID | None | Authorization | None | 200 UserDetailResponse | 403 not self/admin, 404 |
| PATCH | /api/v1/users/{user_id} | Update user. | Bearer + role admin | user_id UUID | None | Authorization, Content-Type | UserUpdate | 200 UserDetailResponse | 404, 422 |
| DELETE | /api/v1/users/{user_id} | Soft delete user. | Bearer + role admin | user_id UUID | None | Authorization | None | 204 No Content | 404 |
| POST | /api/v1/users/{user_id}/unmask | Return unmasked PII and audit reason. | Bearer + role admin | user_id UUID | reason (min length 5) | Authorization | None | 200 UserUnmaskResponse | 404, 422 reason |

Examples:

    GET /api/v1/users?page=1&page_size=50&role=learner
    Authorization: Bearer <token>

    200 OK
    {
      "data": {
        "items": [
          {
            "id": "...",
            "username": "learner1",
            "role": "learner",
            "email": "l*****@mail.com",
            "phone": "***-***-1234",
            "is_active": true,
            "last_login": "...",
            "created_at": "..."
          }
        ],
        "meta": { "total_count": 1, "page": 1, "page_size": 50, "has_next": false }
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Location And Room APIs
Body schemas:
- LocationCreate { name, address?, timezone(default UTC) }
- LocationUpdate { name?, address?, timezone?, is_active? }
- RoomCreate { name, capacity(default 20) }
- RoomUpdate { name?, capacity?, is_active? }

Response schemas:
- LocationResponse { id, name, address?, timezone, is_active, created_at }
- RoomResponse { id, location_id, name, capacity, is_active }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/locations | List locations. | Bearer | None | is_active? | Authorization | None | 200 LocationResponse[] | 401 |
| POST | /api/v1/locations | Create location. | Bearer + role admin | None | None | Authorization, Content-Type | LocationCreate | 201 LocationResponse | 422 |
| GET | /api/v1/locations/{location_id} | Get location by id. | Bearer | location_id UUID | None | Authorization | None | 200 LocationResponse | 404 |
| PATCH | /api/v1/locations/{location_id} | Update location. | Bearer + role admin | location_id UUID | None | Authorization, Content-Type | LocationUpdate | 200 LocationResponse | 404 |
| DELETE | /api/v1/locations/{location_id} | Soft delete location (is_active=false). | Bearer + role admin | location_id UUID | None | Authorization | None | 204 No Content | 404 |
| GET | /api/v1/locations/{location_id}/rooms | List rooms for location. | Bearer | location_id UUID | None | Authorization | None | 200 RoomResponse[] | 404 location dependent |
| POST | /api/v1/locations/{location_id}/rooms | Create room in location. | Bearer + role admin | location_id UUID | None | Authorization, Content-Type | RoomCreate | 201 RoomResponse | 404 location |
| GET | /api/v1/rooms/{room_id} | Get room by id. | Bearer | room_id UUID | None | Authorization | None | 200 RoomResponse | 404 |
| PATCH | /api/v1/rooms/{room_id} | Update room. | Bearer + role admin | room_id UUID | None | Authorization, Content-Type | RoomUpdate | 200 RoomResponse | 404 |
| DELETE | /api/v1/rooms/{room_id} | Soft delete room. | Bearer + role admin | room_id UUID | None | Authorization | None | 204 No Content | 404 |

Examples:

    POST /api/v1/locations
    Authorization: Bearer <admin_token>
    Content-Type: application/json

    {
      "name": "HQ",
      "address": "101 Main St",
      "timezone": "UTC"
    }

    201 Created
    {
      "data": {
        "id": "...",
        "name": "HQ",
        "address": "101 Main St",
        "timezone": "UTC",
        "is_active": true,
        "created_at": "..."
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Course APIs
Body schemas:
- CourseCreate { title, description?, duration_minutes(default 60), category?, price(default 0) }
- CourseUpdate { title?, description?, duration_minutes?, category?, price?, is_active? }

Response schema:
- CourseResponse { id, title, description?, duration_minutes, category?, price, is_active, created_at }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/courses | List courses. | Bearer | None | is_active? | Authorization | None | 200 CourseResponse[] | 401 |
| POST | /api/v1/courses | Create course. | Bearer + role admin | None | None | Authorization, Content-Type | CourseCreate | 201 CourseResponse | 422 |
| GET | /api/v1/courses/{course_id} | Get course. | Bearer | course_id UUID | None | Authorization | None | 200 CourseResponse | 404 |
| PATCH | /api/v1/courses/{course_id} | Update course. | Bearer + role admin | course_id UUID | None | Authorization, Content-Type | CourseUpdate | 200 CourseResponse | 404 |
| DELETE | /api/v1/courses/{course_id} | Soft delete course. | Bearer + role admin | course_id UUID | None | Authorization | None | 204 No Content | 404 |

Examples:

    GET /api/v1/courses?is_active=true
    Authorization: Bearer <token>

    200 OK
    {
      "data": [
        {
          "id": "...",
          "title": "CPR Basics",
          "description": "...",
          "duration_minutes": 90,
          "category": "safety",
          "price": 25.0,
          "is_active": true,
          "created_at": "..."
        }
      ],
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Instructor APIs
Body schemas:
- InstructorCreate { user_id, bio? }
- InstructorUpdate { bio?, is_active? }

Response schema:
- InstructorResponse { id, user_id, username, bio?, is_active, created_at }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/instructors | List instructors. | Bearer | None | is_active? | Authorization | None | 200 InstructorResponse[] | 401 |
| POST | /api/v1/instructors | Create instructor profile. | Bearer + role admin | None | None | Authorization, Content-Type | InstructorCreate | 201 InstructorResponse | 422 |
| GET | /api/v1/instructors/{instructor_id} | Get instructor by id. | Bearer | instructor_id UUID | None | Authorization | None | 200 InstructorResponse | 404 |
| PATCH | /api/v1/instructors/{instructor_id} | Update instructor profile. | Bearer + role admin | instructor_id UUID | None | Authorization, Content-Type | InstructorUpdate | 200 InstructorResponse | 404 |
| DELETE | /api/v1/instructors/{instructor_id} | Soft delete instructor. | Bearer + role admin | instructor_id UUID | None | Authorization | None | 204 No Content | 404 |

Examples:

    PATCH /api/v1/instructors/{instructor_id}
    Authorization: Bearer <admin_token>
    Content-Type: application/json

    { "bio": "Updated bio" }

    200 OK
    {
      "data": {
        "id": "...",
        "user_id": "...",
        "username": "trainer-a",
        "bio": "Updated bio",
        "is_active": true,
        "created_at": "..."
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Session APIs
Body schemas:
- SessionCreate { title, course_id, instructor_id, room_id, start_time, end_time, capacity>=1, buffer_minutes>=0 }
  - Validation: end_time must be after start_time.
- RecurringSessionCreate { title, course_id, instructor_id, room_id, capacity>=1, buffer_minutes>=0, recurrence{rrule_string,start_date,end_date?} }
- SessionUpdate { title?, course_id?, instructor_id?, room_id?, start_time?, end_time?, capacity>=1?, buffer_minutes>=0? }
  - Validation: if start_time and end_time are both present, end_time > start_time.

Response schema:
- SessionResponse { id, title, course_id, instructor_id, room_id, start_time, end_time, capacity, enrolled_count, buffer_minutes, status, recurrence_rule_id?, created_by, created_at, course_title?, instructor_name?, room_name?, location_name?, location_id? }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/sessions | Weekly listing by ISO week. | Bearer | None | week(required, ex 2026-W14), tz(default UTC), location_id?, instructor_id? | Authorization | None | 200 SessionResponse[] | 422 bad week/tz |
| GET | /api/v1/sessions/monthly | Monthly listing by YYYY-MM. | Bearer | None | month(required, ex 2026-04), tz(default UTC), location_id?, instructor_id? | Authorization | None | 200 SessionResponse[] | 422 |
| POST | /api/v1/sessions | Create session. | Bearer + role admin/instructor | None | None | Authorization, Content-Type | SessionCreate | 201 SessionResponse | 409 room/instructor conflict, 422 |
| POST | /api/v1/sessions/recurring | Create recurring sessions from RRULE. | Bearer + role admin/instructor | None | None | Authorization, Content-Type | RecurringSessionCreate | 201 SessionResponse[] | 409 conflicts, 422 invalid RRULE |
| GET | /api/v1/sessions/{session_id} | Get session. | Bearer | session_id UUID | None | Authorization | None | 200 SessionResponse | 404 |
| PATCH | /api/v1/sessions/{session_id} | Update session. | Bearer + role admin/instructor | session_id UUID | None | Authorization, Content-Type | SessionUpdate | 200 SessionResponse | 403 instructor ownership, 404, 409 |
| DELETE | /api/v1/sessions/{session_id} | Cancel session (admin only). | Bearer + role admin | session_id UUID | None | Authorization | None | 204 No Content | 404 |
| PATCH | /api/v1/sessions/{session_id}/cancel | Transition session to canceled. | Bearer + role admin/instructor | session_id UUID | None | Authorization | None | 200 SessionResponse | 403 ownership, 409 invalid state |
| POST | /api/v1/sessions/{session_id}/go-live | Transition scheduled -> live. | Bearer + role admin/instructor | session_id UUID | None | Authorization | None | 200 SessionResponse | 403, 409 invalid state |
| POST | /api/v1/sessions/{session_id}/end | Transition live -> ended. | Bearer + role admin/instructor | session_id UUID | None | Authorization | None | 200 SessionResponse | 403, 409 must be live |
| POST | /api/v1/sessions/{session_id}/complete | Alias to end endpoint. | Bearer + role admin/instructor | session_id UUID | None | Authorization | None | 200 SessionResponse | Same as /end |
| GET | /api/v1/sessions/{session_id}/roster | Learner roster list. | Bearer + role admin/instructor | session_id UUID | None | Authorization | None | 200 list<object> | 403 ownership, 404 |

Examples:

    POST /api/v1/sessions
    Authorization: Bearer <instructor_or_admin_token>
    Content-Type: application/json

    {
      "title": "Morning CPR",
      "course_id": "...",
      "instructor_id": "...",
      "room_id": "...",
      "start_time": "2026-04-15T09:00:00Z",
      "end_time": "2026-04-15T10:30:00Z",
      "capacity": 20,
      "buffer_minutes": 10
    }

    201 Created
    {
      "data": {
        "id": "...",
        "title": "Morning CPR",
        "status": "scheduled",
        "capacity": 20,
        "enrolled_count": 0,
        "start_time": "...",
        "end_time": "..."
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Attendance APIs
Body schemas:
- CheckInRequest { learner_id }
- CheckOutRequest { learner_id }

Response schemas:
- AttendanceRecordResponse { id, session_id, learner_id, joined_at?, left_at?, minutes_attended, was_late }
- AttendanceStats { session_id, total_enrolled, checked_in, late_joins, avg_minutes_attended, replay_completion_rate }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| POST | /api/v1/sessions/{session_id}/attendance/checkin | Check learner into session. | Bearer + role admin/instructor | session_id UUID | None | Authorization, Content-Type | CheckInRequest | 200 AttendanceRecordResponse | 403 no confirmed booking/ownership, 404 session, 409 already checked in |
| POST | /api/v1/sessions/{session_id}/attendance/checkout | Check learner out of session. | Bearer + role admin/instructor | session_id UUID | None | Authorization, Content-Type | CheckOutRequest | 200 AttendanceRecordResponse | 403 ownership, 404 attendance record |
| GET | /api/v1/sessions/{session_id}/attendance/stats | Attendance and replay completion stats. | Bearer + role admin/instructor | session_id UUID | None | Authorization | None | 200 AttendanceStats | 403 ownership, 404 |

Examples:

    POST /api/v1/sessions/{session_id}/attendance/checkin
    Authorization: Bearer <token>
    Content-Type: application/json

    { "learner_id": "..." }

    200 OK
    {
      "data": {
        "id": "...",
        "session_id": "...",
        "learner_id": "...",
        "joined_at": "...",
        "left_at": null,
        "minutes_attended": 0,
        "was_late": false
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Booking APIs
Body schemas:
- BookingCreate { session_id }
- RescheduleRequest { new_session_id }
- CancelRequest { reason? }

Response schema:
- BookingResponse { id, session_id, learner_id, status, rescheduled_from_id?, policy_fee_flagged, cancellation_reason?, confirmed_at?, cancelled_at?, created_at, session_title?, session_start_time?, learner_username? }
- Page<BookingResponse>

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| POST | /api/v1/bookings | Create booking request. | Bearer + role learner/admin | None | None | Authorization, Content-Type | BookingCreate | 201 BookingResponse | 404 session, 409 non-bookable/full/duplicate |
| GET | /api/v1/bookings | List bookings with role-scoped visibility. | Bearer | None | page>=1, page_size 1..200, session_id?, status? | Authorization | None | 200 Page<BookingResponse> | 403 finance requires session_id |
| GET | /api/v1/bookings/{booking_id}/history | Audit history for booking. | Bearer | booking_id UUID | None | Authorization | None | 200 list<object> | 403 scoped access denied |
| GET | /api/v1/bookings/{booking_id} | Get one booking with role checks. | Bearer | booking_id UUID | None | Authorization | None | 200 BookingResponse | 403, 404 |
| PATCH | /api/v1/bookings/{booking_id}/confirm | Confirm requested booking. | Bearer + role admin/instructor | booking_id UUID | None | Authorization | None | 200 BookingResponse | 403 instructor ownership, 404, 409 status/capacity |
| POST | /api/v1/bookings/{booking_id}/reschedule | Reschedule booking to new session. | Bearer | booking_id UUID | None | Authorization, Content-Type | RescheduleRequest | 200 BookingResponse | 403 not owner, 404, 409 full, 422 cutoff policy |
| POST | /api/v1/bookings/{booking_id}/cancel | Cancel booking. | Bearer | booking_id UUID | None | Authorization, Content-Type | CancelRequest | 200 BookingResponse | 403 not owner, 404, 409 terminal state |

Examples:

    POST /api/v1/bookings
    Authorization: Bearer <learner_token>
    Content-Type: application/json

    { "session_id": "..." }

    201 Created
    {
      "data": {
        "id": "...",
        "session_id": "...",
        "learner_id": "...",
        "status": "requested",
        "policy_fee_flagged": false,
        "created_at": "..."
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Replay APIs
Body schemas:
- ReplayAccessRuleCreate { rule_type(enrolled_only|public|custom), available_from?, available_until? }
- ReplayViewCreate { watched_seconds(default 0), completed(default false) }
- Upload endpoint uses multipart: file plus duration_seconds form field.

Response schemas:
- RecordingResponse { id, session_id, file_size_bytes?, duration_seconds?, mime_type, upload_status, created_at }
- ReplayAccessRuleResponse { id, session_id, rule_type, available_from?, available_until?, is_active }
- ReplayStats { session_id, total_views, unique_viewers, completion_rate_pct }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/sessions/{session_id}/recordings | List ready recordings for session. | Bearer | session_id UUID | None | Authorization | None | 200 RecordingResponse[] | 403 access rule |
| GET | /api/v1/sessions/{session_id}/recordings/{recording_id}/stream | Stream recording with byte-range support. | Query token auth | session_id UUID, recording_id UUID | token(required JWT) | Range(optional), Accept | None | 200 or 206 stream | 401 invalid token, 403 access, 404 recording |
| GET | /api/v1/sessions/{session_id}/replay | Get most recent ready replay. | Bearer | session_id UUID | None | Authorization | None | 200 RecordingResponse | 403, 404 |
| POST | /api/v1/sessions/{session_id}/replay/upload | Create/refresh recording metadata and return presigned PUT URL. | Bearer + role admin/instructor | session_id UUID | None | Authorization | None | 200 object with presigned_url/object_key/bucket | 403 instructor ownership, 404 session |
| PATCH | /api/v1/sessions/{session_id}/replay/recording | Confirm upload and set metadata. | Bearer + role admin/instructor | session_id UUID | file_size_bytes?, duration_seconds? | Authorization | None | 200 RecordingResponse | 403, 404 |
| POST | /api/v1/sessions/{session_id}/replay/recording/data | Direct multipart upload to backend then MinIO. | Bearer + role admin/instructor | session_id UUID | None | Authorization, multipart/form-data | file(binary), duration_seconds(form int) | 200 RecordingResponse | 403, 404 |
| POST | /api/v1/sessions/{session_id}/replay/access-rule | Set replay access rule. | Bearer + role admin | session_id UUID | None | Authorization, Content-Type | ReplayAccessRuleCreate | 200 ReplayAccessRuleResponse | 422 |
| POST | /api/v1/replays/{session_id}/view | Record replay view analytics. | Bearer + role learner/admin | session_id UUID | None | Authorization, Content-Type | ReplayViewCreate | 204 No Content | 403 no access |
| GET | /api/v1/replays/{session_id}/stats | Replay analytics for session. | Bearer + role admin/instructor | session_id UUID | None | Authorization | None | 200 ReplayStats | 403 instructor ownership |

Examples:

    GET /api/v1/sessions/{session_id}/recordings/{recording_id}/stream?token=<jwt>
    Range: bytes=0-1048575

    206 Partial Content
    Content-Range: bytes 0-1048575/98765432
    Accept-Ranges: bytes
    Content-Type: video/webm

    <binary stream>

## Promotion APIs
Body schemas:
- PromotionCreate { name, type, value, min_order_amount?, applies_to, stack_group?, is_exclusive, valid_from, valid_until }
- PromotionUpdate { name?, value?, min_order_amount?, applies_to?, stack_group?, is_exclusive?, is_active?, valid_from?, valid_until? }

Response schema:
- PromotionResponse { id, name, type, value, min_order_amount?, applies_to, stack_group?, is_exclusive, is_active, valid_from, valid_until }
- BestOfferResponse { subtotal, discount_total, total, applied_promotions[] }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| POST | /api/v1/promotions/preview | Dry-run offer evaluation for cart. | Bearer + role admin/finance | None | None | Authorization, Content-Type | CartCreate | 200 BestOfferResponse | 422 |
| GET | /api/v1/promotions | List promotions. | Bearer | None | is_active? | Authorization | None | 200 PromotionResponse[] | 401 |
| POST | /api/v1/promotions | Create promotion. | Bearer + role admin/finance | None | None | Authorization, Content-Type | PromotionCreate | 201 PromotionResponse | 422 |
| GET | /api/v1/promotions/{promo_id} | Get promotion. | Bearer | promo_id UUID | None | Authorization | None | 200 PromotionResponse | 404 |
| PATCH | /api/v1/promotions/{promo_id} | Update promotion. | Bearer + role admin/finance | promo_id UUID | None | Authorization, Content-Type | PromotionUpdate | 200 PromotionResponse | 404 |
| DELETE | /api/v1/promotions/{promo_id} | Soft delete promotion. | Bearer + role admin/finance | promo_id UUID | None | Authorization | None | 204 No Content | 404 |

Examples:

    POST /api/v1/promotions/preview
    Authorization: Bearer <finance_token>
    Content-Type: application/json

    {
      "items": [
        { "session_id": "...", "quantity": 2 }
      ]
    }

    200 OK
    {
      "data": {
        "subtotal": 100.0,
        "discount_total": 20.0,
        "total": 80.0,
        "applied_promotions": [
          {
            "promotion_id": "...",
            "promotion_name": "SPRING20",
            "discount_amount": 20.0,
            "explanation": "20% off"
          }
        ]
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Checkout And Order APIs
Body schemas:
- CartItemInput { session_id, quantity 1..100 }
- CartCreate { items: CartItemInput[] }

Response schemas:
- BestOfferResponse { subtotal, discount_total, total, applied_promotions[] }
- OrderResponse { id, learner_id, status, subtotal, discount_total, total, currency, created_at, paid_at?, expires_at?, items[], applied_promotions[] }
- Page<OrderResponse>

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| POST | /api/v1/checkout/cart | Create order cart and pending payment. | Bearer + role learner/admin | None | None | Authorization, Content-Type | CartCreate | 201 OrderResponse | 404 session, 409 non-bookable |
| POST | /api/v1/checkout/best-offer | Compute best offer without persistence. | Bearer | None | None | Authorization, Content-Type | CartCreate | 200 BestOfferResponse | 404/409 session state |
| GET | /api/v1/orders | List orders with role scope. | Bearer + role admin/finance/learner | None | page>=1, page_size 1..200 | Authorization | None | 200 Page<OrderResponse> | 403 scope |
| GET | /api/v1/orders/{order_id} | Get one order. | Bearer + role admin/finance/learner | order_id UUID | None | Authorization | None | 200 OrderResponse | 403 not owner, 404 |
| PATCH | /api/v1/orders/{order_id}/cancel | Cancel unpaid order. | Bearer + role admin/finance/learner | order_id UUID | None | Authorization | None | 200 OrderResponse | 403, 404, 409 paid order |

Examples:

    POST /api/v1/checkout/cart
    Authorization: Bearer <learner_token>
    Content-Type: application/json

    {
      "items": [
        { "session_id": "...", "quantity": 1 }
      ]
    }

    201 Created
    {
      "data": {
        "id": "...",
        "status": "awaiting_payment",
        "subtotal": 25.0,
        "discount_total": 0.0,
        "total": 25.0,
        "currency": "USD",
        "items": [ { "id": "...", "session_id": "...", "unit_price": 25.0, "quantity": 1 } ],
        "applied_promotions": []
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Payment, Refund, Reconciliation APIs
Body schemas:
- PaymentCallbackPayload { order_id, terminal_ref, amount, timestamp, signature, external_event_id? }
- RefundCreate { order_id, amount, reason? }

Response schemas:
- PaymentResponse { id, order_id, terminal_ref?, amount, status, callback_received_at?, signature_verified, created_at }
- RefundResponse { id, payment_id, requested_by, amount, reason?, status, created_at, processed_at? }
- ReconciliationExportResponse { id, export_date, file_path, generated_at, row_count }
- Page<PaymentResponse>

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/payments | List payments (paginated). | Bearer + role admin/finance | None | page>=1, page_size 1..200 | Authorization | None | 200 Page<PaymentResponse> | 403 |
| POST | /api/v1/payments/callback | Terminal callback; verifies signature/timestamp/idempotency. | Public (signature-based) | None | None | Content-Type | PaymentCallbackPayload | 200 PaymentResponse | 404 payment not found, 422 timestamp format/window |
| POST | /api/v1/payments/{order_id}/simulate | Simulate callback for order. | Bearer + role admin/finance/learner | order_id UUID | None | Authorization | None | 200 PaymentResponse | 404 order |
| GET | /api/v1/payments/{order_id} | Get payment by order id. | Bearer + role admin/finance | order_id UUID | None | Authorization | None | 200 PaymentResponse | 404 |
| GET | /api/v1/refunds | List refunds. | Bearer + role admin/finance | None | status? | Authorization | None | 200 RefundResponse[] | 403 |
| POST | /api/v1/refunds | Create refund request. | Bearer + role admin/finance/learner | None | None | Authorization, Content-Type | RefundCreate | 201 RefundResponse | 404 payment, 422 amount exceeds payment |
| GET | /api/v1/refunds/{refund_id} | Get refund by id. | Bearer + role admin/finance | refund_id UUID | None | Authorization | None | 200 RefundResponse | 404 |
| PATCH | /api/v1/refunds/{refund_id}/review | requested -> pending_review. | Bearer + role admin/finance | refund_id UUID | None | Authorization | None | 200 RefundResponse | 404, 409 invalid transition |
| PATCH | /api/v1/refunds/{refund_id}/approve | pending_review -> approved. | Bearer + role admin/finance | refund_id UUID | None | Authorization | None | 200 RefundResponse | 404, 409 |
| PATCH | /api/v1/refunds/{refund_id}/reject | pending_review -> rejected. | Bearer + role admin/finance | refund_id UUID | None | Authorization | None | 200 RefundResponse | 404, 409 |
| PATCH | /api/v1/refunds/{refund_id}/process | approved -> processing. | Bearer + role admin/finance | refund_id UUID | None | Authorization | None | 200 RefundResponse | 404, 409 |
| PATCH | /api/v1/refunds/{refund_id}/complete | processing -> completed and updates order refund status. | Bearer + role admin/finance | refund_id UUID | None | Authorization | None | 200 RefundResponse | 404, 409 |
| POST | /api/v1/reconciliation/export | Generate reconciliation export. | Bearer + role admin/finance | None | export_date? (ISO date) | Authorization | None | 200 ReconciliationExportResponse | 422 bad date |
| GET | /api/v1/reconciliation/export | GET alias for export generation. | Bearer + role admin/finance | None | export_date? (ISO date) | Authorization | None | 200 ReconciliationExportResponse | 422 bad date |
| GET | /api/v1/reconciliation/exports | List latest exports. | Bearer + role admin/finance | None | None | Authorization | None | 200 ReconciliationExportResponse[] | 403 |
| GET | /api/v1/reconciliation/exports/{export_id}/download | Download CSV export file or redirect to object storage URL. | Bearer + role admin/finance | export_id UUID | None | Authorization | None | 200 file/redirect | 404 export |

Examples:

    POST /api/v1/payments/callback
    Content-Type: application/json

    {
      "order_id": "...",
      "terminal_ref": "TERM-01",
      "amount": 25.0,
      "timestamp": "2026-04-14T10:30:00Z",
      "signature": "<hmac_sha256_hex>",
      "external_event_id": "evt-123"
    }

    200 OK
    {
      "data": {
        "id": "...",
        "order_id": "...",
        "terminal_ref": "TERM-01",
        "amount": 25.0,
        "status": "completed",
        "callback_received_at": "...",
        "signature_verified": true,
        "created_at": "..."
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Search APIs
Body schemas:
- SearchFilters {
  invoice_number?, learner_phone?, enrollment_status?, date_range?, date_from?, date_to?,
  site_id?, instructor_id?, learner_id?, page(default 1), page_size(default 50), include_facets(default false)
}
- SavedSearchCreate { name, filters }
- ExportRequest { filters: SearchFilters, format: csv|excel }

Response schemas:
- SearchResponse { results[], total_count, page, page_size, has_next, query_time_ms, facets? }
- SavedSearchResponse { id, name, filters_json, created_at }
- SearchExportJobResponse { id, status, format, row_count?, error_detail?, created_at, completed_at? }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| POST | /api/v1/search | Search bookings with role-scoped filtering. | Bearer + role admin/instructor/finance | None | None | Authorization, Content-Type | SearchFilters | 200 SearchResponse | 422 |
| GET | /api/v1/search/saved | List current user saved searches. | Bearer | None | None | Authorization | None | 200 SavedSearchResponse[] | 401 |
| POST | /api/v1/search/saved | Save named filters. | Bearer | None | None | Authorization, Content-Type | SavedSearchCreate | 201 SavedSearchResponse | 400 max 20 saved searches |
| DELETE | /api/v1/search/saved/{search_id} | Delete user saved search. | Bearer | search_id UUID | None | Authorization | None | 204 No Content | 404 |
| POST | /api/v1/search/export/jobs | Queue async export job. | Bearer + role admin/instructor/finance | None | None | Authorization, Content-Type | ExportRequest | 202 SearchExportJobResponse(status=queued) | 422 |
| GET | /api/v1/search/export/jobs/{job_id} | Poll export job status. | Bearer + role admin/instructor/finance | job_id UUID | None | Authorization | None | 200 SearchExportJobResponse | 403 ownership, 404 |
| GET | /api/v1/search/export/jobs/{job_id}/download | Download completed export file (csv/xlsx). | Bearer + role admin/instructor/finance | job_id UUID | None | Authorization | None | 200 file | 403, 404, 409 not completed |

Examples:

    POST /api/v1/search/export/jobs
    Authorization: Bearer <token>
    Content-Type: application/json

    {
      "filters": {
        "enrollment_status": "confirmed",
        "page": 1,
        "page_size": 50,
        "include_facets": true
      },
      "format": "csv"
    }

    202 Accepted
    {
      "data": {
        "id": "...",
        "status": "queued",
        "format": "csv",
        "row_count": null,
        "error_detail": null,
        "created_at": "...",
        "completed_at": null
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Ingestion APIs
Body schemas:
- IngestionSourceCreate { name, type(kafka|flume|logstash|file|mysql_cdc|postgres_cdc), config, collection_frequency_seconds(default 300), concurrency_cap(default 10) }
- IngestionSourceUpdate { name?, config?, collection_frequency_seconds?, concurrency_cap?, is_active? }
- Webhook payload: array of objects (list[dict])

Response schemas:
- IngestionSourceResponse { id, name, type, collection_frequency_seconds, concurrency_cap, is_active, last_run_at?, last_status?, created_at }
- IngestionRunResponse { id, source_id, started_at, finished_at?, rows_ingested, status, error_detail? }
- ConnectivityResult { success, latency_ms?, error? }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/ingestion/sources | List ingestion sources. | Bearer + role admin/dataops | None | None | Authorization | None | 200 IngestionSourceResponse[] | 403 |
| POST | /api/v1/ingestion/sources | Create source (config encrypted at rest). | Bearer + role admin/dataops | None | None | Authorization, Content-Type | IngestionSourceCreate | 201 IngestionSourceResponse | 422 |
| GET | /api/v1/ingestion/sources/{source_id} | Get source. | Bearer + role admin/dataops | source_id UUID | None | Authorization | None | 200 IngestionSourceResponse | 404 |
| PATCH | /api/v1/ingestion/sources/{source_id} | Update source. | Bearer + role admin/dataops | source_id UUID | None | Authorization, Content-Type | IngestionSourceUpdate | 200 IngestionSourceResponse | 404 |
| DELETE | /api/v1/ingestion/sources/{source_id} | Soft delete source. | Bearer + role admin/dataops | source_id UUID | None | Authorization | None | 204 No Content | 404 |
| POST | /api/v1/ingestion/sources/{source_id}/test-connection | Test source connectivity. | Bearer + role admin/dataops | source_id UUID | None | Authorization | None | 200 ConnectivityResult | 404 |
| POST | /api/v1/ingestion/sources/{source_id}/trigger | Trigger ingestion run now. | Bearer + role admin/dataops | source_id UUID | None | Authorization | None | 200 IngestionRunResponse | 404 |
| GET | /api/v1/ingestion/sources/{source_id}/runs | List source runs. | Bearer + role admin/dataops | source_id UUID | limit 1..500 (default 50) | Authorization | None | 200 IngestionRunResponse[] | 404, 422 |
| GET | /api/v1/ingestion/runs/{run_id} | Get one run. | Bearer + role admin/dataops | run_id UUID | None | Authorization | None | 200 IngestionRunResponse | 404 |
| POST | /api/v1/ingestion/webhook/{source_id} | Push-based ingest (Logstash/Flume style). | X-Api-Key header | source_id UUID | None | X-Api-Key, Content-Type | list[dict] | 200 IngestionRunResponse | 403 invalid api key, 404 source |

Examples:

    POST /api/v1/ingestion/webhook/{source_id}
    X-Api-Key: <source_api_key>
    Content-Type: application/json

    [
      { "event": "a", "ts": "..." },
      { "event": "b", "ts": "..." }
    ]

    200 OK
    {
      "data": {
        "id": "...",
        "source_id": "...",
        "started_at": "...",
        "finished_at": "...",
        "rows_ingested": 2,
        "status": "succeeded",
        "error_detail": null
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Job APIs
Response schemas:
- JobStatsAggregate { window_minutes, jobs: JobStatRow[] }
- JobStatRow { job_name, total_executions, success_count, failure_count, success_rate_pct, avg_duration_ms, p95_duration_ms, last_run_at?, last_status? }
- JobExecutionResponse { id, job_name, started_at, finished_at?, status, error_detail? }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/jobs | List configured beat schedule job keys. | Bearer + role admin/dataops | None | None | Authorization | None | 200 string[] | 403 |
| GET | /api/v1/jobs/stats/aggregate | Aggregate execution performance for window. | Bearer + role admin/dataops | None | window_minutes 1..1440 (default 60) | Authorization | None | 200 JobStatsAggregate | 422 |
| POST | /api/v1/jobs/{job_name}/trigger | Trigger a scheduled job by key/full/short name. | Bearer + role admin/dataops | job_name string | None | Authorization | None | 202 { queued: task_name } | 404 unknown job |
| GET | /api/v1/jobs/{job_name}/executions | Recent executions for job. | Bearer + role admin/dataops | job_name string | limit 1..500 (default 50) | Authorization | None | 200 JobExecutionResponse[] | 422 |

Examples:

    POST /api/v1/jobs/close-expired-orders/trigger
    Authorization: Bearer <dataops_token>

    202 Accepted
    {
      "data": { "queued": "app.modules.jobs.tasks.close_expired_orders" },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Monitoring APIs
Response schemas:
- Health response: { status, timestamp }
- AlertResponse { id, alert_type, message, job_name?, is_resolved, created_at }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/monitoring/health | Liveness check. | Public | None | None | None | None | 200 {status,timestamp} | None |
| GET | /api/v1/monitoring/metrics | Prometheus metrics (JWT protected). | Bearer + role admin/dataops | None | None | Authorization | None | 200 text/plain metrics | 403 |
| GET | /api/v1/monitoring/metrics/scrape | Prometheus scrape endpoint with static bearer token. | Static token | None | None | Authorization: Bearer <scrape_token> | None | 200 text/plain metrics | 401 invalid/missing token |
| GET | /api/v1/monitoring/alerts | List alerts by resolved state. | Bearer + role admin/dataops | None | resolved bool (default false) | Authorization | None | 200 AlertResponse[] | 403 |
| PATCH | /api/v1/monitoring/alerts/{alert_id}/resolve | Mark alert resolved. | Bearer + role admin/dataops | alert_id UUID string | None | Authorization | None | 204 No Content | 422 invalid UUID format |

Examples:

    GET /api/v1/monitoring/metrics/scrape
    Authorization: Bearer <PROMETHEUS_SCRAPE_TOKEN>

    200 OK
    # HELP ...
    # TYPE ...
    metric_name 123

## Audit APIs
Response schemas:
- AuditLogOut { id, actor_id?, actor_username?, entity_type, entity_id, action, old_value?, new_value?, ip_address?, created_at }
- Page<AuditLogOut>

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/audit-logs | Paginated audit log search. | Bearer + role admin | None | page>=1, page_size 1..200, entity_type?, entity_id?, actor_id?, action?, from_date?, to_date? | Authorization | None | 200 Page<AuditLogOut> | 403, 422 |

Examples:

    GET /api/v1/audit-logs?page=1&page_size=50&entity_type=booking
    Authorization: Bearer <admin_token>

    200 OK
    {
      "data": {
        "items": [
          {
            "id": "...",
            "actor_id": "...",
            "actor_username": "admin",
            "entity_type": "booking",
            "entity_id": "...",
            "action": "confirm",
            "old_value": null,
            "new_value": null,
            "ip_address": null,
            "created_at": "..."
          }
        ],
        "meta": { "total_count": 1, "page": 1, "page_size": 50, "has_next": false }
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## Admin Policy APIs
Body schemas:
- AdminPolicyUpdate { reschedule_cutoff_hours? 0..168, cancellation_fee_hours? 0..168 }

Response schema:
- AdminPolicyResponse { id?, reschedule_cutoff_hours, cancellation_fee_hours, updated_at?, updated_by? }

| Method | Path | Description | Auth | Path Params | Query | Headers | Body | Success | Error/Validation |
|---|---|---|---|---|---|---|---|---|---|
| GET | /api/v1/admin/policy | Read active policy values. | Bearer + role admin | None | None | Authorization | None | 200 AdminPolicyResponse | 403 |
| PATCH | /api/v1/admin/policy | Update policy values. | Bearer + role admin | None | None | Authorization, Content-Type | AdminPolicyUpdate | 200 AdminPolicyResponse | 422 bounds validation |

Examples:

    PATCH /api/v1/admin/policy
    Authorization: Bearer <admin_token>
    Content-Type: application/json

    {
      "reschedule_cutoff_hours": 4,
      "cancellation_fee_hours": 12
    }

    200 OK
    {
      "data": {
        "id": "...",
        "reschedule_cutoff_hours": 4,
        "cancellation_fee_hours": 12,
        "updated_at": "...",
        "updated_by": "..."
      },
      "meta": { "request_id": "...", "timestamp": "...", "version": "v1" },
      "error": null
    }

## WebSocket API

| Type | Path | Description | Auth | Path Params | Query | Messages In | Messages Out | Errors |
|---|---|---|---|---|---|---|---|---|
| WS | /api/ws/sessions/{session_id}/room | Live room signaling and presence channel, multi-worker broadcast via Redis pub/sub. | Query token JWT; plus session membership authorization | session_id string/UUID | token required | webrtc_offer, webrtc_answer, webrtc_ice, webrtc_request | room_state, room_peers, peer_joined, peer_left, session_status_changed, attendee_joined, attendee_left, relayed webrtc_* | close 4001 auth failure, close 4003 access denied |

Access rules:
- Admin: full room access.
- Instructor: must match session.instructor_id through instructor profile mapping.
- Learner and other non-admin roles: must have confirmed booking for session.

Example:

    WS /api/ws/sessions/{session_id}/room?token=<access_jwt>

    Client sends:
    {
      "type": "webrtc_offer",
      "target_user_id": "<peer_user_id>",
      "sdp": "..."
    }

    Server relays:
    {
      "type": "webrtc_offer",
      "from_user_id": "<sender_user_id>",
      "target_user_id": "<peer_user_id>",
      "sdp": "..."
    }

## Common Schema Reference
### Roles
- admin
- instructor
- learner
- finance
- dataops

### Core Status Enums
- SessionStatus:
  - draft, scheduled, live, ended, recording_processing, recording_published, closed_no_recording, canceled, archived
- BookingStatus:
  - requested, confirmed, rescheduled_out, canceled, completed, no_show
- OrderStatus:
  - awaiting_payment, paid, closed_unpaid, canceled, refund_pending, refunded_partial, refunded_full
- PaymentStatus:
  - pending, completed, failed
- RefundStatus:
  - requested, pending_review, approved, processing, completed, rejected, failed, canceled
- PromotionType:
  - percent_off, fixed_off, threshold_fixed_off, bogo_selected_workshops
- IngestionSourceType:
  - kafka, flume, logstash, file, mysql_cdc, postgres_cdc
- IngestionRunStatus:
  - queued, running, succeeded, partial_failed, failed, canceled, resolved
- ReplayRuleType:
  - enrolled_only, public, custom
- RecordingUploadStatus:
  - pending, processing, ready, failed
- SearchExportJobStatus:
  - queued, processing, completed, failed

### Common Headers
- Authorization: Bearer <token>
- Content-Type: application/json
- X-Api-Key: <api_key> (ingestion webhook only)
- Range: bytes=start-end (recording streaming optional)

### Common Query Validation
- page: integer >= 1
- page_size: integer 1..200 for user/order/booking/payment/audit lists
- limit: integer 1..500 for ingestion runs and job executions
- policy fields: integer 0..168

## Assumptions
- Assumption: Framework endpoints /api/v1/docs, /api/v1/redoc, /api/v1/openapi.json are included as available APIs because they are explicitly configured in app initialization.
- Assumption: All JSON responses under /api/v1 are wrapped by envelope middleware, except non-JSON and streaming/file responses.
- Assumption: Some file download endpoints may return either direct file response or redirect URL depending on storage backend and file location.
- Assumption: GET /api/v1/sessions/{session_id}/roster returns a list of learner objects from repository without a dedicated Pydantic schema.
- Assumption: GET /api/v1/bookings/{booking_id}/history returns untyped audit objects (list of dict) by design.

## Endpoint Quick Examples (Every Endpoint)

  GET /api/v1/docs -> 200 HTML
  GET /api/v1/redoc -> 200 HTML
  GET /api/v1/openapi.json -> 200 OpenAPI JSON

  POST /api/v1/auth/login -> 200 TokenResponse
  POST /api/v1/auth/refresh -> 200 TokenResponse
  POST /api/v1/auth/logout -> 204
  POST /api/v1/auth/change-password -> 204

  GET /api/v1/users?page=1&page_size=50 -> 200 Page<UserDetailResponse>
  POST /api/v1/users -> 201 UserDetailResponse
  GET /api/v1/users/me -> 200 UserResponse
  GET /api/v1/users/{user_id} -> 200 UserDetailResponse
  PATCH /api/v1/users/{user_id} -> 200 UserDetailResponse
  DELETE /api/v1/users/{user_id} -> 204
  POST /api/v1/users/{user_id}/unmask?reason=AuditNeed -> 200 UserUnmaskResponse

  GET /api/v1/locations -> 200 LocationResponse[]
  POST /api/v1/locations -> 201 LocationResponse
  GET /api/v1/locations/{location_id} -> 200 LocationResponse
  PATCH /api/v1/locations/{location_id} -> 200 LocationResponse
  DELETE /api/v1/locations/{location_id} -> 204
  GET /api/v1/locations/{location_id}/rooms -> 200 RoomResponse[]
  POST /api/v1/locations/{location_id}/rooms -> 201 RoomResponse
  GET /api/v1/rooms/{room_id} -> 200 RoomResponse
  PATCH /api/v1/rooms/{room_id} -> 200 RoomResponse
  DELETE /api/v1/rooms/{room_id} -> 204

  GET /api/v1/courses -> 200 CourseResponse[]
  POST /api/v1/courses -> 201 CourseResponse
  GET /api/v1/courses/{course_id} -> 200 CourseResponse
  PATCH /api/v1/courses/{course_id} -> 200 CourseResponse
  DELETE /api/v1/courses/{course_id} -> 204

  GET /api/v1/instructors -> 200 InstructorResponse[]
  POST /api/v1/instructors -> 201 InstructorResponse
  GET /api/v1/instructors/{instructor_id} -> 200 InstructorResponse
  PATCH /api/v1/instructors/{instructor_id} -> 200 InstructorResponse
  DELETE /api/v1/instructors/{instructor_id} -> 204

  GET /api/v1/sessions?week=2026-W14&tz=UTC -> 200 SessionResponse[]
  GET /api/v1/sessions/monthly?month=2026-04&tz=UTC -> 200 SessionResponse[]
  POST /api/v1/sessions -> 201 SessionResponse
  POST /api/v1/sessions/recurring -> 201 SessionResponse[]
  GET /api/v1/sessions/{session_id} -> 200 SessionResponse
  PATCH /api/v1/sessions/{session_id} -> 200 SessionResponse
  DELETE /api/v1/sessions/{session_id} -> 204
  PATCH /api/v1/sessions/{session_id}/cancel -> 200 SessionResponse
  POST /api/v1/sessions/{session_id}/go-live -> 200 SessionResponse
  POST /api/v1/sessions/{session_id}/end -> 200 SessionResponse
  POST /api/v1/sessions/{session_id}/complete -> 200 SessionResponse
  GET /api/v1/sessions/{session_id}/roster -> 200 list<object>

  POST /api/v1/sessions/{session_id}/attendance/checkin -> 200 AttendanceRecordResponse
  POST /api/v1/sessions/{session_id}/attendance/checkout -> 200 AttendanceRecordResponse
  GET /api/v1/sessions/{session_id}/attendance/stats -> 200 AttendanceStats

  POST /api/v1/bookings -> 201 BookingResponse
  GET /api/v1/bookings?page=1&page_size=50 -> 200 Page<BookingResponse>
  GET /api/v1/bookings/{booking_id}/history -> 200 list<object>
  GET /api/v1/bookings/{booking_id} -> 200 BookingResponse
  PATCH /api/v1/bookings/{booking_id}/confirm -> 200 BookingResponse
  POST /api/v1/bookings/{booking_id}/reschedule -> 200 BookingResponse
  POST /api/v1/bookings/{booking_id}/cancel -> 200 BookingResponse

  GET /api/v1/sessions/{session_id}/recordings -> 200 RecordingResponse[]
  GET /api/v1/sessions/{session_id}/recordings/{recording_id}/stream?token=<jwt> -> 200/206 stream
  GET /api/v1/sessions/{session_id}/replay -> 200 RecordingResponse
  POST /api/v1/sessions/{session_id}/replay/upload -> 200 {presigned_url,object_key,bucket}
  PATCH /api/v1/sessions/{session_id}/replay/recording -> 200 RecordingResponse
  POST /api/v1/sessions/{session_id}/replay/recording/data -> 200 RecordingResponse
  POST /api/v1/sessions/{session_id}/replay/access-rule -> 200 ReplayAccessRuleResponse
  POST /api/v1/replays/{session_id}/view -> 204
  GET /api/v1/replays/{session_id}/stats -> 200 ReplayStats

  POST /api/v1/promotions/preview -> 200 BestOfferResponse
  GET /api/v1/promotions -> 200 PromotionResponse[]
  POST /api/v1/promotions -> 201 PromotionResponse
  GET /api/v1/promotions/{promo_id} -> 200 PromotionResponse
  PATCH /api/v1/promotions/{promo_id} -> 200 PromotionResponse
  DELETE /api/v1/promotions/{promo_id} -> 204

  POST /api/v1/checkout/cart -> 201 OrderResponse
  POST /api/v1/checkout/best-offer -> 200 BestOfferResponse
  GET /api/v1/orders?page=1&page_size=50 -> 200 Page<OrderResponse>
  GET /api/v1/orders/{order_id} -> 200 OrderResponse
  PATCH /api/v1/orders/{order_id}/cancel -> 200 OrderResponse

  GET /api/v1/payments?page=1&page_size=50 -> 200 Page<PaymentResponse>
  POST /api/v1/payments/callback -> 200 PaymentResponse
  POST /api/v1/payments/{order_id}/simulate -> 200 PaymentResponse
  GET /api/v1/payments/{order_id} -> 200 PaymentResponse
  GET /api/v1/refunds -> 200 RefundResponse[]
  POST /api/v1/refunds -> 201 RefundResponse
  GET /api/v1/refunds/{refund_id} -> 200 RefundResponse
  PATCH /api/v1/refunds/{refund_id}/review -> 200 RefundResponse
  PATCH /api/v1/refunds/{refund_id}/approve -> 200 RefundResponse
  PATCH /api/v1/refunds/{refund_id}/reject -> 200 RefundResponse
  PATCH /api/v1/refunds/{refund_id}/process -> 200 RefundResponse
  PATCH /api/v1/refunds/{refund_id}/complete -> 200 RefundResponse
  POST /api/v1/reconciliation/export -> 200 ReconciliationExportResponse
  GET /api/v1/reconciliation/export -> 200 ReconciliationExportResponse
  GET /api/v1/reconciliation/exports -> 200 ReconciliationExportResponse[]
  GET /api/v1/reconciliation/exports/{export_id}/download -> 200 file/redirect

  POST /api/v1/search -> 200 SearchResponse
  GET /api/v1/search/saved -> 200 SavedSearchResponse[]
  POST /api/v1/search/saved -> 201 SavedSearchResponse
  DELETE /api/v1/search/saved/{search_id} -> 204
  POST /api/v1/search/export/jobs -> 202 SearchExportJobResponse
  GET /api/v1/search/export/jobs/{job_id} -> 200 SearchExportJobResponse
  GET /api/v1/search/export/jobs/{job_id}/download -> 200 file or 409 while processing

  GET /api/v1/ingestion/sources -> 200 IngestionSourceResponse[]
  POST /api/v1/ingestion/sources -> 201 IngestionSourceResponse
  GET /api/v1/ingestion/sources/{source_id} -> 200 IngestionSourceResponse
  PATCH /api/v1/ingestion/sources/{source_id} -> 200 IngestionSourceResponse
  DELETE /api/v1/ingestion/sources/{source_id} -> 204
  POST /api/v1/ingestion/sources/{source_id}/test-connection -> 200 ConnectivityResult
  POST /api/v1/ingestion/sources/{source_id}/trigger -> 200 IngestionRunResponse
  GET /api/v1/ingestion/sources/{source_id}/runs?limit=50 -> 200 IngestionRunResponse[]
  GET /api/v1/ingestion/runs/{run_id} -> 200 IngestionRunResponse
  POST /api/v1/ingestion/webhook/{source_id} -> 200 IngestionRunResponse

  GET /api/v1/jobs -> 200 string[]
  GET /api/v1/jobs/stats/aggregate?window_minutes=60 -> 200 JobStatsAggregate
  POST /api/v1/jobs/{job_name}/trigger -> 202 {queued}
  GET /api/v1/jobs/{job_name}/executions?limit=50 -> 200 JobExecutionResponse[]

  GET /api/v1/monitoring/health -> 200 {status,timestamp}
  GET /api/v1/monitoring/metrics -> 200 text/plain metrics
  GET /api/v1/monitoring/metrics/scrape -> 200 text/plain metrics
  GET /api/v1/monitoring/alerts?resolved=false -> 200 AlertResponse[]
  PATCH /api/v1/monitoring/alerts/{alert_id}/resolve -> 204

  GET /api/v1/audit-logs?page=1&page_size=50 -> 200 Page<AuditLogOut>

  GET /api/v1/admin/policy -> 200 AdminPolicyResponse
  PATCH /api/v1/admin/policy -> 200 AdminPolicyResponse

  WS /api/ws/sessions/{session_id}/room?token=<jwt> -> 101 switch protocol, then bidirectional events