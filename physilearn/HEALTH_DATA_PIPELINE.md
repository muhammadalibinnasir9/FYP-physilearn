# PhysiLearn Health Data Pipeline — System Overview

PhysiLearn operates as an **integrated health data pipeline** from infrastructure setup through to stakeholder dashboards. This document describes the end-to-end flow and where it is implemented in the codebase. **All requirements below exist in both backend and frontend;** the AI module uses safe dummy/placeholder responses when needed so the pipeline never fails.

---

## 1. Digital Infrastructure (Admin)

The pipeline begins with the **Admin** establishing the digital infrastructure:

| Activity | Description | Implementation |
|----------|-------------|-----------------|
| **Upload student profiles** | Create and manage student records (name, roll number, section). | Admin Dashboard → Students; `StudentAdminViewSet` (CRUD), POST/GET/PATCH `/api/admin/students/`. Student model: `api/models.py`. |
| **Create staff accounts** | Create Teacher and Parent accounts (email, name, temporary password) with role-based permissions. | User Management; POST `/api/admin/create-user/` (or `/api/admin/teachers/`, `/api/admin/parents/`). See `USER_MANAGEMENT_CHECKIN_FLOW.md`, `ADMIN_CHECKLIST.md`. |
| **Link Parents to children** | Assign one or more Student IDs to each Parent for strict data isolation. | Parent creation/relink: `student_ids` in create-user or PATCH `/api/admin/parents/<id>/relink-students/`. `Student.parent` FK enforces linkage. |
| **Data isolation** | Teachers see only their assigned sections; Parents see only their linked children. | Backend filters all student/health/attendance data by `TeacherSection` (teachers) and `Student.parent_id` (parents). |

**References:** `USER_MANAGEMENT_CHECKIN_FLOW.md`, `ADMIN_CHECKLIST.md`, `api/views.py` (create_user_view, students_list_view, my_children_view), `api/permissions.py` (IsAdmin, role/is_staff).

---

## 2. Primary Data-Entry Flow (Teacher)

Once infrastructure is in place, the **Teacher** executes the primary data-entry flow during PE sessions:

| Activity | Description | Implementation |
|----------|-------------|-----------------|
| **PE sessions** | Create and manage PE sessions (date, section, time, description). | `PESessionViewSet`, `/api/pe-sessions/`. Filtered by teacher’s assigned sections. |
| **Real-time physical metrics** | Log height and weight (and related metrics) per student. | Health record create/update: `HealthRecordViewSet`, `/api/health-records/`. Teacher access scoped by `TeacherSection`. |
| **Fitness test scores** | Record fitness test scores (e.g. stamina, strength, flexibility). | `FitnessPerformanceViewSet`, `/api/fitness-performances/`. Same section-based access. |
| **Attendance** | Mark attendance (Present, Absent, Excused, Late) for students in a session. | `AttendanceViewSet`, bulk `/api/attendance/bulk/`. Linked to `PESession` and teacher. |
| **Validation & storage** | Data validated and stored in a centralized database. | Django models: `HealthRecord`, `FitnessPerformance`, `Attendance`, `PESession`, `Student`. Validation in serializers and model `save()`. |

**References:** `api/views.py` (HealthRecordViewSet, FitnessPerformanceViewSet, PESessionViewSet, AttendanceViewSet), `api/models.py`, `api/serializers.py`. Frontend: teacher dashboard, add record, add attendance screens.

---

## 3. AI Module (Automatic Processing)

When height/weight are saved, the system automatically:

| Activity | Description | Implementation |
|----------|-------------|-----------------|
| **Calculate BMI** | Compute BMI from height (m) and weight (kg). | `HealthRecord.save()`: `bmi = weight / (height_m ** 2)`; stored (encrypted) on `HealthRecord`. |
| **Classify health status** | Classify according to WHO-aligned BMI thresholds. | `api/ai_logic.py`: `classify_bmi(bmi)` → Underweight (&lt;18.5), Normal (18.5–25), Overweight (25–30), Obese (≥30). Stored in `HealthRecord.fitness_status`. |
| **Generate personalized recommendations** | AI-driven advice based on fitness status and performance data. | `api/ai_logic.py`: `generate_recommendations(status, student_profile)`. Uses fitness status, test scores, recent performances. Stored in `HealthRecord.ai_recommendations`. On any error, returns a dummy placeholder so the pipeline never fails. |
| **Health history** | Longitudinal snapshots for trend analysis. | On `HealthRecord.save()`, `HealthHistory` record created (height, weight, bmi, fitness_status) for history endpoints. |

**References:** `api/models.py` (HealthRecord.save), `api/ai_logic.py` (classify_bmi, generate_recommendations), `HealthHistory` model.

---

## 4. Stakeholder Dashboards

The flow concludes at role-specific dashboards:

| Role | View | Implementation |
|------|------|-----------------|
| **Parents** | Read-only view of their **child’s** longitudinal growth trends and AI-driven advice. | GET `/api/students/my-children`; `/api/students/<id>/health-history/`, `.../fitness-progress/`, `.../comprehensive-history/`, `.../report/`. All filtered by `Student.parent_id == request.user`. Frontend: parent dashboard, select child, student history. |
| **Admin** | School-wide health analytics: interactive charts, automated reports, institutional health management. | GET `/api/admin/analytics/` (BMI distribution, by grade, at-risk students, activity trends, performance metrics). GET `/api/students/<id>/report/` (PDF). Frontend: admin dashboard, admin analytics screen. |
| **Teachers** | Class/section-scoped data for their assigned sections (students, health records, attendance). | GET `/api/students/` (filtered by TeacherSection), health/attendance viewsets, teacher dashboard. |

**References:** `api/views.py` (my_children_view, student_health_history_view, admin_analytics_view, generate_student_report_view, students_list_view), frontend `admin_dashboard.dart`, `admin_analytics_screen.dart`, `parent_dashboard.dart`, `teacher_dashboard.dart`.

---

## Pipeline Summary

```
Admin (setup)     →  Student profiles, staff accounts, parent–child links, data isolation
        ↓
Teacher (PE)      →  Height/weight, fitness scores, attendance → validated, stored in DB
        ↓
AI module         →  BMI calculation, WHO classification, personalized recommendations
        ↓
Dashboards        →  Parents: read-only child trends + AI advice
                     Admin: school-wide analytics, charts, reports
                     Teachers: section-scoped data entry and views
```

Together, the **User Management Check-in Flow** and **Admin Checklist** cover infrastructure and access control; this document describes how the same pipeline feeds **health data** from data entry through AI processing to stakeholder dashboards.
