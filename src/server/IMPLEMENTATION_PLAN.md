# 📋 Server Implementation Plan

**Date**: April 22, 2026  
**Scope**: Server-side improvements only (`src/server/`)  
**Status**: Planning → Execution

---

## 0. Error Handling Strategy

**No Mock Data in Production**
- When data is missing → Return HTTP error with clear message
- UI displays error message to user
- User knows what to do next (e.g., "Please log in" or "Complete your profile")

| Scenario | HTTP Code | Message | UI Behavior |
|----------|-----------|---------|------------|
| User not in DB | 404 | `"User SV001 not found"` | Show login prompt |
| Incomplete profile | 400 | `"Cannot generate roadmap: target_cpa not set"` | Show setup wizard |
| Transcript not found | 404 | `"No transcript records found"` | Show upload prompt |
| Database error | 500 | `"Database connection failed"` | Show retry button |

---

## 1. Current State Analysis

### 🎯 Architecture (Hybrid Model)

The server uses a **dual-flow architecture**:

1. **Chat Route** (`chat.py`): 
   - Agent-first (LLM calls)
   - Flexible, conversational
   - Falls back to mock response if agent fails

2. **Panel Routes** (`panels.py`):
   - Deterministic (direct tools calls, **no LLM**)
   - Fast and reliable for structured data
   - Calls `AcademicTools` directly (bypasses agent)

### ✅ What's Working (Real/OK)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| **Chat API** | `app/routes/chat.py` | ✅ OK | Connects to Agent (with mock fallback) |
| **Roadmap Endpoint** | `app/routes/academic.py` | ✅ OK | Calls `tools.recommend_graduation_path()` |
| **User Status Endpoint** | `app/routes/user.py` | ✅ OK | Returns user persona from DB |
| **Open Courses** | `app/routes/academic.py` | ✅ OK | Queries `Classes` table |
| **File Upload** | `app/routes/chat.py` + `transcript.py` | ✅ OK | Saves to `data/uploads/` |
| **Dependencies** | `app/dependencies.py` | ✅ OK | Singleton pattern for tools |
| **CORS & Health Check** | `main.py` | ✅ OK | Basic config in place |

### ⚠️ What's Using Mock Data (To Fix)

| Component | File | Issue | Fix Strategy | Priority |
|-----------|------|-------|--------------|----------|
| **User Status** | `panels.py:32-50` | Falls back to `USER_STATUS_MOCK` | Return 404 error with "User not found" message | HIGH |
| **Roadmap** | `panels.py:62-83` | Falls back to `ROADMAP_MOCK` | Return 400 error with reason (e.g., "Target CPA not set") | HIGH |
| **Preference Save** | `panels.py:51-60` | Only prints, doesn't save | Implement actual DB save; return 200 with saved values | HIGH |
| **Transcript Confirm** | `panels.py:103-123` | Checks `hasattr()` for missing function | Return 400 error until agent team implements save_transcript_data() | HIGH |

---

## 2. Missing Features (Worker Integration)

### 📊 New Tables in DB (From data.sql)

✅ Already added to `data/data.sql`:
- `course_lecture_frames` – Lecture outline per course per week
- `student_semester_study_schedule` – Study plan + progress tracking
- `review_notifications_history` – Notification audit log
- `student_notification_preferences` – User notification settings

❌ **Need to create endpoints to query these tables:**

### 2.1 New Route: `app/routes/worker_api.py` (NEW FILE)

**Purpose**: Provide endpoints for worker/scheduler to fetch data  
**Error Handling**: Return appropriate HTTP errors when data not found (404, 400)

**Methods needed**:

```python
@router.get("/student/{student_id}/schedule")
def get_student_schedule(student_id: str, semester_id: str, week_no: int):
    """
    Fetch study schedule for a specific week.
    Returns list of courses + current progress.
    """
    # Query: student_semester_study_schedule
    # Needed by: worker.py to know which courses to generate Q's for

@router.get("/course/{course_id}/lecture-frames")
def get_lecture_frames(curriculum_id: str, course_id: str):
    """
    Fetch all lecture frames (weekly outlines) for a course.
    Returns list of week_no + lecture_title + topic_outline.
    """
    # Query: course_lecture_frames
    # Needed by: worker.py to align questions with curriculum

@router.post("/notifications/send")
def send_notification(notification_data: dict):
    """
    Worker calls this to record a sent notification.
    Prevents duplicate questions for same topic/week.
    """
    # Insert into: review_notifications_history
    # Needed by: worker.py to check `has_notification_for_topic()`

@router.get("/student/{student_id}/preferences")
def get_notification_preferences(student_id: str):
    """
    Fetch user's notification settings (frequency, quiet hours, etc).
    """
    # Query: student_notification_preferences
    # Needed by: worker.py scheduler
```

---

## 3. Implementation Tasks

### Phase 1: Fix Mock Data Issues (HIGH PRIORITY)

#### Task 1.1: Remove mock fallback from `panels.py:get_user_status()`
**File**: `src/server/app/routes/panels.py`  
**Current (L32-50)**:
```python
if "error" in history:
    return UserStatus(**USER_STATUS_MOCK)  # ← REMOVE THIS
```

**Action**: Replace mock with HTTP error response
```python
if "error" in history:
    raise HTTPException(
        status_code=404,
        detail=f"User {student_id} not found. Please log in first."
    )
```

**Rationale**: Return clear error messages that UI can display to user instead of hiding with fake data

---

#### Task 1.2: Remove mock fallback from `panels.py:get_roadmap()`
**File**: `src/server/app/routes/panels.py`  
**Current (L62-83)**:
```python
if "error" in history:
    return RoadmapResponse(**ROADMAP_MOCK)  # ← REMOVE THIS
```

**Action**: Replace mock with HTTP error response
```python
if "error" in history:
    raise HTTPException(
        status_code=404,
        detail=f"Cannot generate roadmap. {history['error']}"
    )
```

**Rationale**: Return clear error messages so UI can guide user to complete profile setup first

---

#### Task 1.3: Implement real preference saving
**File**: `src/server/app/routes/panels.py`  
**Current (L51-60)**:
```python
@router.post("/user/preference")
def set_user_preference(pref: PreferenceRequest, tools=Depends(get_academic_tools)):
    return {"status": "success", "received": pref.dict()}  # ← ONLY LOGS
```

**Action**: 
1. Parse `study_load` and `blackout_slots` from request
2. Call `tools.update_user_history(student_id, {...})` with new fields
3. Return confirmation with saved values

**Rationale**: Users expect preferences to persist

---

#### Task 1.4: Verify `data_api.py` not in active use
**File**: `src/server/app/routes/data_api.py`  
**Status**: Legacy file, not included in `main.py` router registration

**Action**: Confirm it's not mounted, leave as-is or remove later  
**Rationale**: Not part of current architecture (chat + panels only)

---

### Phase 2: Add Worker Support APIs (MEDIUM PRIORITY)

#### Task 2.1: Create new `app/routes/worker_api.py`
**File**: `src/server/app/routes/worker_api.py` (NEW)

**Endpoints**:

```python
# 1. Fetch study schedule for worker
@router.get("/worker/schedule/{student_id}")
def get_study_schedule(student_id: str, semester_id: str, week_no: int):
    """Fetch courses + progress for this student/week."""
    # Uses: WorkerRepository.get_study_schedule_rows()

# 2. Fetch lecture frames for worker
@router.get("/worker/frames/{course_id}")
def get_course_frames(curriculum_id: str, course_id: str):
    """Fetch lecture outline by week."""
    # Uses: WorkerRepository.get_lecture_frame()

# 3. Log sent notification
@router.post("/worker/notifications/record")
def record_notification(notification: dict):
    """Worker POSTs after sending a question."""
    # Uses: WorkerRepository.insert_notification()

# 4. Get notification preferences
@router.get("/worker/preferences/{student_id}")
def get_preferences(student_id: str):
    """Fetch user's notification settings."""
    # Uses: WorkerRepository.get_notification_preference()

# 5. Upsert preferences
@router.post("/worker/preferences/{student_id}")
def set_preferences(student_id: str, pref: dict):
    """Update notification settings."""
    # Uses: WorkerRepository.upsert_notification_preference()
```

**Register in `main.py`**:
```python
from server.app.routes import worker_api
app.include_router(worker_api.router, prefix="/api/worker", tags=["Worker"])
```

---

#### Task 2.2: Add query methods to `AcademicTools`
**File**: `src/agent/tools.py` (Already exists, just add new methods)

⚠️ **NOTE**: This is in `src/agent/`, but need to understand structure for integration.

**Methods needed** (coordination with agent team):
```python
def get_lecture_frames(self, curriculum_id: str, course_id: str) -> list:
    """Query course_lecture_frames."""
    
def get_study_schedule(self, student_id: str, semester_id: str, week_no: int) -> list:
    """Query student_semester_study_schedule."""
    
def record_notification(self, notification_data: dict) -> int:
    """Insert into review_notifications_history."""
```

---

### Phase 3: Schema Alignment (LOW PRIORITY)

#### Task 3.1: Verify `Students` table extensions
**Issue**: `student_notification_preferences` is separate table, but notification settings could be stored directly in `Students` table

**Decision**: Keep separate table (cleaner design, easier to add fields later)

#### Task 3.2: Add `study_load` field to `Students`
**Status**: Currently missing. Needed for preference storage.

**Action**: 
- Option A: Add column to `Students` table
- Option B: Create `student_preferences` table with fields: `study_load`, `blackout_slots`, etc.

**Recommendation**: Option B (create new table for future extensibility)

---

## 4. File Changes Summary

### New Files
- `src/server/app/routes/worker_api.py` – Worker scheduler endpoints
- `src/server/IMPLEMENTATION_PLAN.md` – This file

### Modified Files

#### `src/server/main.py`
```python
# Add after other route includes:
from server.app.routes import worker_api
app.include_router(worker_api.router, prefix="/api/worker", tags=["Worker"])
```

#### `src/server/app/routes/panels.py`
- Remove mock fallback from `get_user_status()` (L32-50)
- Remove mock fallback from `get_roadmap()` (L62-83)
- Implement real preference saving in `set_user_preference()` (L51-60)

#### `src/server/app/models/schemas.py`
- Add `PreferenceResponse` schema (for preference save response)
- Extend `PreferenceRequest` with `notification_frequency`, `quiet_hours`, etc.

---

## 5. Testing Checklist

**Error Responses (UI-friendly messages)**
- [ ] `GET /api/user/status` returns 404 with message: `"User SV001 not found"` (when user doesn't exist)
- [ ] `GET /api/roadmap` returns 400 with message: `"Cannot generate roadmap: target_cpa not set"` (when incomplete)
- [ ] `POST /api/transcript/confirm` returns 400 with message: `"save_transcript_data not implemented yet"` (when agent not ready)

**Success Responses (data saved)**
- [ ] `POST /api/user/preference` returns 200 with saved values persisted in DB
- [ ] `GET /api/user/status` returns 200 with real data when user exists

**Worker API**
- [ ] `GET /api/worker/schedule/{student_id}` returns courses or 404 if not found
- [ ] `GET /api/worker/frames/{course_id}` returns lecture outline or 404 if not found
- [ ] `POST /api/worker/notifications/record` inserts and returns 200 with notification_id
- [ ] Worker scheduler successfully handles all error responses

---

## 6. Integration Points

### With `agent/`
- **worker.py** uses `WorkerRepository` directly (same codebase = direct DB access, **no HTTP calls**)
- **worker_api.py** provides HTTP endpoints for external access (UI, monitoring, external schedulers)
- **tools.py** provides high-level tool methods (agent uses this, not needed by worker directly)

**Architecture:**
```
worker.py (in agent/)
    ↓ (direct DB access)
WorkerRepository → SQL queries

worker_api.py (in server/)
    ↓ (exposes HTTP)
GET /api/worker/* ← Can be called by UI, external services, monitoring
```

### With `data/`
- New tables already in `data.sql` ✅
- Seed data for `course_lecture_frames` needed (curriculum mapping)

### With UI (`src/ui/`)
- Can call `/api/worker/schedule/{student_id}` to display study plan
- Can call `/api/worker/preferences/{student_id}` to show notification settings
- Can POST to `/api/worker/notifications/record` if needed for tracking

---

## 7. Dependency Chain

```
worker.py (scheduler)
    ↓
GET /api/worker/schedule/{student_id}
    ↓
AcademicTools.get_study_schedule()
    ↓
WorkerRepository.get_study_schedule_rows()
    ↓
SQL: SELECT ... FROM student_semester_study_schedule
```

Similar chains for:
- Lecture frames
- Notifications
- Preferences

---

## 8. Success Criteria

✅ **Phase 1 Complete**: No more mock data in `panels.py`  
✅ **Phase 2 Complete**: Worker can fetch all needed data via `/api/worker/*`  
✅ **Phase 3 Complete**: User preferences persist across sessions  
✅ **Integration**: `worker.py` successfully runs and logs notifications

---

## 9. Notes

- Do **NOT** modify `agent/` or `data/` per request
- Focus only on `server/` folder
- **No mock data in any endpoint** - Return HTTP errors with clear messages for UI to display
- Worker integration happens at API boundary (HTTP calls)
- All worker DB queries should go through `WorkerRepository` in `agent/worker.py`
- Keep `panels.py` as the source of truth for UI panel data
- UI should handle 404/400 errors gracefully and show appropriate messages/prompts to user
