# Technical Requirements Document (TRD) — EduPredict

## 1. Technology Stack (MERN Rejected — Pure Django Only)
- **Backend Framework:** Python 3.11+ & Django (Latest Stable, Standard MVT Architecture)
- **Database:** MongoDB Atlas (`pymongo` + clean helper layer in `core/db.py` alongside Django Auth, or `mongoengine`)
- **Data Science & ML:** `pandas`, `numpy`, `scikit-learn`, `openpyxl`
- **Package Version Policy (Always Install Latest Packages Rule):** Whenever any Python package, library, or dependency is installed or updated, the **latest stable version** MUST be installed (`pip install --upgrade <package>`) and frozen into `requirements.txt`.
- **Frontend Templating:** Pure Django HTML5 Templates (`{% extends %}`, `{% include %}`)
- **Styling:** Tailwind CSS (Global config in `base.html` + `static/css/global.css`)
- **Icons:** FontAwesome (`@fortawesome/fontawesome-free`)
- **Charts:** Chart.js (v4+ via CDN in `base.html` with global theme adapter)
- **Interactivity:** Clean Vanilla JavaScript (`static/js/app.js`) — Zero React, Zero TypeScript, Zero JSX.

## 2. Strict Modular Folder Architecture
Every agent MUST follow this exact directory structure. Creating random folders or massive 1000-line files is strictly prohibited (Max file length: **300–450 lines**; split views/services if larger).

```text
edupredict/
├── .agents/                        # MANDATORY AI Agent Docs (Read First)
│   ├── PRD.md
│   ├── SRD.md
│   ├── TRD.md
│   ├── design.md
│   ├── project-rules.md
│   └── git-sync.md
├── config/                         # Django Project Configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                           # Global Shared Utilities & DB Connection
│   ├── db.py                       # MongoDB Atlas Singleton Connection & Helpers
│   ├── decorators.py               # @role_required & auth guards
│   └── context_processors.py       # Global notifications & user role context
├── accounts/                       # Auth & User Management App
│   ├── views.py
│   └── urls.py
├── panels/                         # Role-Based Dashboards App (Modular Views)
│   ├── views_admin.py              # Admin Panel Views (< 250 lines)
│   ├── views_teacher.py            # Teacher Panel Views (< 250 lines)
│   ├── views_student.py            # Student Panel Views (< 250 lines)
│   ├── views_analyst.py            # Analyst Panel Views (< 250 lines)
│   └── urls.py                     # Connected routes for all 4 panels
├── analytics/                      # Big Data Ingestion & ML Engine App
│   ├── data_pipeline.py            # CSV/Excel ingestion & missing data cleaning
│   ├── ml_engine.py                # Dropout, Grade, Anomaly & Course Demand ML
│   └── views.py                    # Endpoints for triggering upload/predictions
├── templates/                      # Global & Panel HTML Templates
│   ├── base.html                   # Master App-Shell-3 Layout (Sidebar + Header)
│   ├── components/                 # MANDATORY Reusable Global UI Components
│   │   ├── sidebar.html            # Role-aware App-Shell-3 Sidebar
│   │   ├── topbar.html             # Header with Theme Toggle, Search & Bell
│   │   ├── metric_card.html        # Global KPI Stat Card
│   │   ├── confirm_modal.html      # Global Custom Confirm/Alert Modal
│   │   ├── form_modal.html         # Global Reusable Add/Edit Modal
│   │   ├── data_table.html         # Global Responsive Table Wrapper
│   │   └── toast.html              # Global Non-Intrusive Toast Notification
│   ├── accounts/
│   │   └── auth.html               # Unified Sign-In / Sign-Up Page
│   └── panels/
│       ├── admin_dashboard.html
│       ├── teacher_dashboard.html
│       ├── student_dashboard.html
│       └── analyst_dashboard.html
├── static/
│   ├── css/
│   │   └── global.css              # Design tokens (Light/Dark CSS Variables)
│   └── js/
│       ├── app.js                  # Sidebar toggle, Dark mode, Custom Modals
│       └── charts.js               # Theme-aware Chart.js helper functions
├── .env.example                    # Template for MONGODB_URI & SECRET_KEY
├── requirements.txt                # Pinned latest stable packages
└── manage.py
3. MongoDB Atlas Collections Schema (core/db.py)
All collections reside in the edupredict_db database on MongoDB Atlas:

users:{ "_id": ObjectId, "user_id": "USR-1001", "full_name": str, "email": str, "password_hash": str, "role": "ADMIN|TEACHER|STUDENT|ANALYST", "department": str, "batch": str, "is_active": bool, "created_at": datetime }

student_records (Partitioned/Indexed by student_id and batch):{ "_id": ObjectId, "student_id": "STD-2026-01", "full_name": str, "batch": str, "course_code": str, "attendance_pct": float, "internal_marks": float, "assignment_score": float, "lms_hours_weekly": float, "previous_gpa": float, "updated_at": datetime }

predictions:{ "_id": ObjectId, "student_id": "STD-2026-01", "predicted_gpa": float, "dropout_risk_score": float, "risk_level": "LOW|MEDIUM|HIGH", "is_anomaly": bool, "anomaly_reason": str, "recommendation": str, "model_version": str, "generated_at": datetime }

datasets_log:{ "_id": ObjectId, "filename": str, "uploaded_by": str, "rows_processed": int, "missing_values_fixed": int, "status": "COMPLETED|FAILED", "uploaded_at": datetime }

notifications:{ "_id": ObjectId, "target_role": str, "target_user_id": str, "title": str, "message": str, "severity": "INFO|WARNING|DANGER", "is_read": bool, "created_at": datetime }

support_tickets:{ "_id": ObjectId, "user_id": str, "user_name": str, "role": str, "subject": str, "message": str, "status": "OPEN|RESOLVED", "created_at": datetime }

4. URL Routing Map (panels/urls.py & config/urls.py)
Every route must be cleanly named so templates only use {% url 'route_name' %} (never hardcode URLs):

/ -> Redirects to /auth/ or active role dashboard

/auth/ -> accounts:auth_view (Login / Register)

/auth/logout/ -> accounts:logout_view (Triggered via Global Confirm Modal)

/admin-panel/ -> panels:admin_dashboard

/admin-panel/users/ -> panels:admin_users

/admin-panel/courses/ -> panels:admin_courses

/admin-panel/tickets/ -> panels:admin_tickets

/teacher-panel/ -> panels:teacher_dashboard

/teacher-panel/students/ -> panels:teacher_students

/teacher-panel/ingest/ -> panels:teacher_ingest

/student-panel/ -> panels:student_dashboard

/student-panel/report/ -> panels:student_report

/analyst-panel/ -> panels:analyst_dashboard

/analyst-panel/upload/ -> analytics:upload_dataset

/analyst-panel/run-ml/ -> analytics:run_predictions

5. Global Component Connectivity Contract
No Duplicate UI Code: If an agent needs a KPI card on the Student Panel, it MUST use {% include 'components/metric_card.html' with title="Attendance" value="91%" badge="+3% this month" status="success" icon="fa-solid fa-calendar-check" %}.

No Native Browser Popups: window.alert(), window.confirm(), and window.prompt() are strictly banned. Every confirmation (Delete User, Logout, Reset Data) MUST call openConfirmModal({ title, message, onConfirmUrl }) defined in templates/components/confirm_modal.html.