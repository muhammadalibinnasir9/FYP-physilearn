# Administrative Actions Checklist — Backend & Frontend

This document verifies backend logic and frontend UI against the administrative checklist.

---

## [x] Account Creation

### Backend
- **POST /api/admin/create-user/** (unified) handles both **Teacher** and **Parent** registration.
  - Body: `username`, `email`, `password`, `first_name`, `last_name`, `role` (`TEACHER` | `PARENT`).
  - For `role=TEACHER`: `sections` (list or comma-separated) required.
  - For `role=PARENT`: `student_ids` (list or comma-separated) required.
  - **Password hashing**: Django `User.objects.create_user(..., password=...)` uses `set_password()` internally (default Django hashing). No plain-text storage.
- **Alternative endpoints** (still available):  
  - POST `/api/admin/teachers/` — create Teacher + assign sections.  
  - POST `/api/admin/parents/` — create Parent + link student IDs.

### Frontend
- **Admin Users** screen: “Add User” opens a dialog with role selector (Admin, Teacher, Parent, Student).
- For **Teacher**: form includes “Sections (comma-separated)”;
- For **Parent**: form includes “Student IDs (comma-separated)”.
- Create flow calls **AdminService.createUserAdmin** → **POST /api/admin/create-user/** for Teacher and Parent. Generic roles use POST `/api/users/`.

---

## [x] Teacher-to-Section Mapping

### Backend
- **Join table**: `TeacherSection` (`api/models.py`): `teacher_id` (FK to User), `section` (CharField, e.g. "10-A"), `assigned_by` (FK to User, admin).
  - Sections are identified by string (e.g. "7-A", "Grade 10-A"); there is no separate `Section` model with `section_id`.
- **Logic**: When a **Teacher** calls **GET /api/students/** (or `students_list_view`), the backend filters by this mapping:
  - `assigned_sections = TeacherSection.objects.filter(teacher=request.user).values_list('section', flat=True)`
  - `students = Student.objects.filter(section__in=assigned_sections, is_active=True)`
- Teachers without assigned sections receive an empty list.

### Frontend
- When creating a Teacher, admin enters sections in the Add User dialog; the same payload is sent to POST `/api/admin/create-user/` with `sections`. No separate “mapping” screen; mapping is done at creation time.

---

## [x] Parent-to-Student Linking

### Backend
- **Student model** has **parent_id** foreign key: `Student.parent` → `User` (limit_choices_to role=PARENT).
- **Create Parent**: POST `/api/admin/create-user/` or POST `/api/admin/parents/` with `student_ids` → sets `Student.parent` for those IDs.
- **Re-link**: PATCH `/api/admin/parents/<parent_id>/relink-students/` with `student_ids` → clears previous links for that parent and sets the new ones.

### Frontend
- **Search-and-link UI**: In **Admin Users**, when adding or editing a **Parent**:
  - **Add**: “Student IDs (comma-separated)” field to assign one or more Student IDs.
  - **Edit**: “Linked Student IDs (comma-separated)” and **Update** triggers PATCH `.../relink-students/` via `AdminProvider.updateParentStudentLinks`.
- Admin selects the Parent (when editing) and assigns one or more Student IDs; backend enforces `Student.parent_id` and data isolation for parents.

---

## [x] Role Verification (Middleware)

### Backend
- **Permission class**: `IsAdmin` (`api/permissions.py`) allows access only if:
  - User is authenticated, **and**
  - `user.role == 'ADMIN'` **or** `user.is_staff is True`.
- All admin management endpoints use `@permission_classes([IsAdmin])`:
  - POST `/api/admin/create-user/`
  - POST `/api/admin/teachers/`
  - POST `/api/admin/parents/`
  - PATCH `/api/admin/parents/<id>/relink-students/`
  - UserViewSet (list/create/update/delete users)
  - StudentAdminViewSet, AcademicTermViewSet, FitnessTestParameterViewSet, admin_analytics_view, etc.
- Unauthorized users receive **403 Forbidden**.

### Frontend
- Admin dashboard and User Management are shown only to users with admin role (routing/auth state). API calls send JWT; backend enforces `IsAdmin` (role or is_staff).

---

## Summary

| Item                         | Backend | Frontend |
|-----------------------------|--------|----------|
| POST /api/admin/create-user | Yes    | Yes (via createUserAdmin) |
| Password hashing            | Django default (set_password) | N/A (handled on server) |
| Teacher–Section mapping    | TeacherSection + GET /api/students filter | Sections at create time |
| Parent–Student linking      | Student.parent_id + create/relink endpoints | Add/Edit Parent with student IDs |
| Role verification           | IsAdmin (role ADMIN or is_staff) | Admin-only routes + JWT |

All four checklist items are implemented in both backend and frontend.
