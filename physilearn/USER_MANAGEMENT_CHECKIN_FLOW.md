# User Management Check-in Flow — Spec vs Implementation

This document maps the **User Management Check-in Flow** (Admin creates Teachers/Parents, mapping, data isolation, notifications) to the current PhysiLearn backend.

---

## 1. Admin creates Teacher and Parent accounts

**Spec:** Admin creates accounts by entering basic credentials (email, name, temporary password); stored with role-based permissions (JWT claims).

**Implementation:**

| Aspect | Status | Location |
|--------|--------|----------|
| Create Teacher | ✅ | `POST /api/admin/teachers/` — `create_teacher_and_assign_sections_view` |
| Create Parent | ✅ | `POST /api/admin/parents/` — `create_parent_and_link_students_view` |
| Fields | ✅ | `username`, `email`, `password`, `first_name`, `last_name` (required for both) |
| Role storage | ✅ | `User.role` (ADMIN / TEACHER / PARENT) — `api/models.py` |
| JWT claims | ✅ | `CustomTokenObtainPairSerializer` adds `role` (and role-specific data) to access token — `api/serializers.py` |
| Admin-only | ✅ | Both endpoints use `@permission_classes([IsAdmin])` — `api/views.py` |

**Admin can also** list/create generic users via `UserViewSet` at `/api/users/` (uses `RegisterSerializer` with optional `role`).

---

## 2. Mapping task

**Spec:** Admin assigns Teachers to Classes/Sections (e.g. Grade 10-A) and links Parent accounts to their Student IDs. Backend uses these FKs for data isolation.

**Implementation:**

| Task | Status | How |
|------|--------|-----|
| Teacher → Sections | ✅ | `TeacherSection` model (teacher, section, assigned_by). Teacher creation endpoint accepts `sections` (list or comma-separated), creates `TeacherSection` rows and sets `Student.teacher` for students in those sections. |
| Parent → Students | ✅ | `Student.parent` FK. Parent creation endpoint accepts `student_ids` (list or comma-separated), sets `Student.parent` for those IDs. |
| Re-link Parent | ✅ | `PATCH /api/admin/parents/<parent_id>/relink-students/` — `patch_parent_students_view` updates which students are linked to a parent. |

**Models:** `api/models.py` — `User`, `Student` (parent, teacher, section), `TeacherSection` (teacher, section, assigned_by).

---

## 3. Data isolation

**Spec:** Teacher sees only their assigned class list; Parent sees only health reports of their linked children.

**Implementation:**

| Role | What they see | How |
|------|----------------|-----|
| Teacher | Only students in assigned sections | `students_list_view` and teacher-scoped views filter by `TeacherSection.objects.filter(teacher=request.user).values_list('section', flat=True)` then `Student.objects.filter(section__in=assigned_sections)`. Same pattern in `HealthRecordViewSet`, `FitnessPerformanceViewSet`, `PESessionViewSet`, `AttendanceViewSet`, and student history/report endpoints. |
| Parent | Only their linked children | `students_list_view`: `Student.objects.filter(parent_id=request.user.id)`. `my_children_view`: same. Health record / history / report access: `student.parent == request.user`. |
| Admin | Full access | No section/parent filter; can access all users and students. |

**Permissions:** `IsAdmin`, `IsTeacher`, `IsParent` in `api/permissions.py`; role checks and FK-based filtering in views.

---

## 4. Automated notification / credential brief

**Spec:** System sends an automated notification or credential brief to new users so they can log in and start their role.

**Implementation:**

- **In-app notification:** After creating a Teacher or Parent, the backend creates a **credential-brief notification** for that user (title/message with login instructions, no plain-text password). They see it when they open the app.
- **Email:** Optional; can be added later (e.g. send email with temporary password via your email backend). Not implemented by default.

**Relevant code:** `notifications/models.py` (`Notification`), `notifications/signals.py` (e.g. `create_system_notification`); credential-brief creation is invoked from `create_teacher_and_assign_sections_view` and `create_parent_and_link_students_view` in `api/views.py`.

---

## API quick reference (Admin User Management)

| Action | Method | Endpoint | Body (key fields) |
|--------|--------|----------|-------------------|
| Create Teacher + assign sections | POST | `/api/admin/teachers/` | `username`, `email`, `password`, `first_name`, `last_name`, `sections` (e.g. `["10-A", "10-B"]`) |
| Create Parent + link students | POST | `/api/admin/parents/` | `username`, `email`, `password`, `first_name`, `last_name`, `student_ids` (e.g. `[1, 2]`) |
| Re-link Parent to students | PATCH | `/api/admin/parents/<id>/relink-students/` | `student_ids` (e.g. `[1, 3, 5]`) |
| List/create users (generic) | GET/POST etc. | `/api/users/` | Standard DRF; create uses `RegisterSerializer` (optional `role`) |
| List students (admin) | GET | `/api/admin/students/` | — |
| Teacher’s sections | GET | `/api/teacher/sections/` | (as Teacher) |
| Students (role-filtered) | GET | `/api/students/` | Optional `teacher_id=me` for teachers |
| Parent’s children | GET | `/api/students/my-children` | (as Parent) |

---

## Summary

- **Account creation and mapping** are implemented as specified (Admin creates Teacher/Parent with credentials; Teacher→sections and Parent→student IDs; JWT includes role).
- **Data isolation** is enforced via `TeacherSection` and `Student.parent` (and teacher) in all relevant list and detail endpoints.
- **Credential brief** is implemented as an in-app notification for new Teachers and Parents; optional email can be added later.
