# Technical Requirements Document (TRD) — EduPredict

## 1. Technology Stack (MERN Rejected — Pure Django Only)
- **Backend Framework:** Python 3.11+ & Django (Latest Stable, Standard MVT Architecture)
- **Database:** MongoDB Atlas (`pymongo` + clean helper layer in `core/db.py` alongside Django Auth, or `mongoengine`)
- **Data Science & ML:** `pandas`, `numpy`, `scikit-learn`, `openpyxl`
- **Media Storage:** `cloudinary` (Avatar uploads via `core/cloudinary_services.py`, URLs persisted in MongoDB `users.avatar_url`)
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
│   ├── prd.md
│   ├── srd.md
│   ├── trd.md
│   ├── design.md
│   ├── project-rules.md
│   ├── git-sync.md
│   └── rules/edupredict-rules.md
├── config/                         # Django Project Configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                           # Global Shared Utilities, DB & Theme Services
│   ├── db.py                       # MongoDB Atlas Singleton, TTL Cache & Helpers
│   ├── decorators.py               # @role_required & @login_required_custom guards
│   ├── context_processors.py       # Global notifications, role & theme context
│   ├── cloudinary_services.py      # Cloudinary avatar validation & 320x320 upload helper
│   └── theme_services.py           # Per-user/per-panel theme, login sync & profile/password updates
├── accounts/                       # Auth & User Session App
│   ├── services.py                 # Auth, registration, session serialization
│   ├── views.py
│   └── urls.py
├── panels/                         # Role-Based Dashboards App (Modular Views & Services)
│   ├── admin_audit_services.py     # Activity logs & portal settings services
│   ├── admin_seed.py               # Process-once admin seed & backup payload
│   ├── admin_services.py           # Admin CRUD, self-action guards & table builders
│   ├── teacher_services.py         # Teacher roster, manual entry & alert services
│   ├── teacher_alert_services.py   # Teacher alert formatting & persistence
│   ├── student_services.py         # Student metrics, report card & tips services
│   ├── student_alert_services.py   # Student alert helpers
│   ├── views_admin.py              # Admin Panel Views (<= 250 lines)
│   ├── views_teacher.py            # Teacher Panel Views (<= 250 lines)
│   ├── views_student.py            # Student Panel Views (<= 250 lines)
│   ├── views_analyst.py            # Analyst Panel Views (<= 250 lines)
│   ├── views_theme.py              # Theme Preferences API & My Profile/Avatar/Password Views (<= 145 lines)
│   ├── tests.py, test_admin.py, test_teacher_student.py
│   └── urls.py                     # Connected routes for all 4 panels + profile/theme
├── analytics/                      # Big Data Ingestion & ML Engine App
│   ├── data_pipeline.py            # CSV/Excel ingestion & missing data cleaning
│   ├── preprocessing.py            # Feature normalization & schema mapping
│   ├── ml_engine.py                # Dropout, Grade, Anomaly & Course Demand ML
│   ├── evaluation.py               # Leakage-free train/test ML evaluation
│   ├── model_health.py             # Model diagnostics & label coverage
│   ├── tests.py, test_pipeline.py
│   ├── views.py                    # Endpoints for upload, ML trigger & evaluation JSON
│   └── urls.py
├── templates/                      # Global & Panel HTML Templates
│   ├── base.html                   # Master App-Shell-3 Layout (Sidebar + Header)
│   ├── 404.html                    # Theme-aware custom 404 page
│   ├── components/                 # MANDATORY Reusable Global UI Components
│   │   ├── sidebar.html            # Role-isolated sidebar + Settings & Theme dropdown
│   │   ├── topbar.html             # Header with Theme Toggle, Bell, Search & Profile/Avatar pill
│   │   ├── metric_card.html        # Global KPI Stat Card
│   │   ├── confirm_modal.html      # Global Custom Confirm & Coming Soon Modals
│   │   ├── form_modal.html         # Global Reusable Add/Edit/Change-Password Modal
│   │   ├── theme_studio_modal.html # Theme & Appearance Live Studio Modal
│   │   ├── gradient_file_uploader.html # Animated drag/drop uploader + preview & progress bar
│   │   ├── faq_pro.html            # Live search & animated accordion FAQ widget
│   │   ├── data_table.html         # Global Wrapped Desktop Table + Mobile Stacked Cards
│   │   └── toast.html              # Global Non-Intrusive Toast Notification
│   ├── accounts/
│   │   └── auth.html               # Unified Sign-In / Sign-Up + Eye Toggles + Theme Hydration
│   └── panels/
│       ├── user_profile.html       # Shared My Profile & Settings Page (All Roles)
│       ├── admin_dashboard.html, admin_users.html, admin_courses.html, admin_tickets.html, admin_logs.html, admin_settings.html
│       ├── teacher_dashboard.html, teacher_students.html, teacher_ingest.html, teacher_alerts.html
│       ├── student_dashboard.html, student_report.html, student_tips.html, student_notifications.html
│       ├── analyst_dashboard.html, analyst_evaluation_section.html, analyst_accuracy.html
│       └── coming_soon_panel.html
├── static/
│   ├── css/
│   │   └── global.css              # Design tokens, dark shell chrome & modern baseline CSS
│   └── js/
│       ├── app.js                  # Sidebar, Modals, Password Toggle, Pagination & Sorting
│       ├── nav.js                  # SPA navigation cache, #ep-top-progress & nav groups
│       ├── theme_studio.js         # Ocean Blue Theme Studio & 1.2s Cancelable Auto-Upload
│       ├── ui_widgets.js           # Top Progress Bar, Submit Lock, FaqPro & Gradient Uploaders
│       ├── charts.js               # Theme-aware Chart.js helper functions
│       └── analyst_evaluation.js   # Evaluation chart & diagnostics renderer
├── .env.example                    # Template for MONGODB_URI, SECRET_KEY & CLOUDINARY_* keys
├── requirements.txt                # Pinned latest stable packages
└── manage.py
```
## 3. MongoDB Atlas Collections Schema (`core/db.py` & `panels/admin_audit_services.py`)
All collections reside in the `edupredict_db` database on MongoDB Atlas:

- `users`: `{ "_id": ObjectId, "user_id": "USR-1001", "student_id": str (optional), "full_name": str, "email": str, "password_hash": str, "role": "ADMIN|TEACHER|STUDENT|ANALYST", "department": str, "batch": str, "phone": str, "bio": str, "avatar_url": str, "theme_prefs": dict (keyed by role), "is_active": bool, "created_at": datetime }`
- `courses`: `{ "_id": ObjectId, "course_code": "CS-101", "title": str, "department": str, "batch": str, "instructor": str, "credits": int, "capacity": int, "status": "ACTIVE|ARCHIVED", "created_at": datetime }`
- `student_records` (Indexed by `student_id` and `batch`): `{ "_id": ObjectId, "student_id": "STD-2026-01", "full_name": str, "batch": str, "course_code": str, "attendance_pct": float, "internal_marks": float, "assignment_score": float, "lms_hours_weekly": float, "previous_gpa": float, "updated_at": datetime }`
- `predictions`: `{ "_id": ObjectId, "student_id": "STD-2026-01", "predicted_gpa": float, "dropout_risk_score": float, "risk_level": "LOW|MEDIUM|HIGH", "is_anomaly": bool, "anomaly_reason": str, "recommendation": str, "model_version": str, "generated_at": datetime }`
- `datasets_log`: `{ "_id": ObjectId, "filename": str, "uploaded_by": str, "rows_processed": int, "missing_values_fixed": int, "status": "COMPLETED|FAILED", "uploaded_at": datetime }`
- `notifications`: `{ "_id": ObjectId, "target_role": str, "target_user_id": str, "title": str, "message": str, "severity": "INFO|WARNING|DANGER", "is_read": bool, "created_at": datetime }`
- `support_tickets`: `{ "_id": ObjectId, "ticket_id": "TKT-1001", "user_id": str, "user_name": str, "role": str, "subject": str, "message": str, "status": "OPEN|RESOLVED", "created_at": datetime }`
- `activity_logs`: `{ "_id": ObjectId, "log_id": str, "actor": str, "role": str, "category": "USERS|COURSES|TICKETS|DATA|SYSTEM", "action": str, "summary": str, "severity": str, "source": str, "created_at": datetime }`
- `system_settings`: `{ "_id": ObjectId, "key": "portal_settings", "institution_name": str, "current_term": str, "default_batch": str, "passing_gpa": float, "min_attendance_pct": int, "high_risk_threshold": int, "medium_risk_threshold": int, "anomaly_drop_pct": int, "auto_student_alerts": bool, "auto_teacher_alerts": bool, "updated_by": str, "updated_at": datetime }`

## 4. Complete Named URL Routing Map (`config/urls.py`, `accounts/urls.py`, `panels/urls.py`, `analytics/urls.py`)
Every route must be cleanly named so templates only use `{% url 'route_name' %}` (never hardcode URLs):

- `/` -> `root` (Redirects to `/auth/` or active role dashboard)
- `/auth/` -> `accounts:auth_view` (Login / Register with guest `PORTAL` theme sync)
- `/auth/logout/` -> `accounts:logout_view` (Triggered via Global Confirm Modal)
- `/profile/` -> `panels:user_profile` (Shared `My Profile & Settings` page for all logged-in roles)
- `/theme/preferences/` -> `panels:theme_preferences` (GET/POST per-user & per-panel Theme Studio persistence + reset)
- `/support/submit/` -> `panels:submit_support_ticket` (Non-Admin support submission)
- `/notifications/mark-read/` -> `panels:mark_notifications_read`
- `/admin-panel/` -> `panels:admin_dashboard`
- `/admin-panel/users/` -> `panels:admin_users`
- `/admin-panel/courses/` -> `panels:admin_courses`
- `/admin-panel/tickets/` -> `panels:admin_tickets`
- `/admin-panel/logs/` -> `panels:admin_logs`
- `/admin-panel/settings/` -> `panels:admin_settings`
- `/admin-panel/backup/` -> `panels:admin_backup_export`
- `/teacher-panel/` -> `panels:teacher_dashboard`
- `/teacher-panel/students/` -> `panels:teacher_students`
- `/teacher-panel/ingest/` -> `panels:teacher_ingest`
- `/teacher-panel/alerts/` -> `panels:teacher_alerts`
- `/student-panel/` -> `panels:student_dashboard`
- `/student-panel/report/` -> `panels:student_report`
- `/student-panel/report/download/` -> `panels:student_report_download`
- `/student-panel/tips/` -> `panels:student_tips`
- `/student-panel/notifications/` -> `panels:student_notifications`
- `/analyst-panel/` -> `panels:analyst_dashboard`
- `/analyst-panel/accuracy/` -> `panels:analyst_accuracy`
- `/analyst-panel/upload/` -> `analytics:upload_dataset`
- `/analyst-panel/run-ml/` -> `analytics:run_predictions`
- `/analyst-panel/evaluation/` -> `analytics:model_evaluation`

## 5. Global Component Connectivity & UX Contracts
- **No Duplicate UI Code:** Always `{% include %}` from `templates/components/` (`metric_card.html`, `data_table.html`, `confirm_modal.html`, `form_modal.html`, `theme_studio_modal.html`, `gradient_file_uploader.html`, `faq_pro.html`, `toast.html`).
- **No Native Browser Popups:** `window.alert()`, `window.confirm()`, and `window.prompt()` are strictly banned. Use `openConfirmModal`, `openFormModal`, `openThemeStudioModal`, `openComingSoonModal`, or `showToast`.
- **Unified Password Toggles & Change Password Modal:** `static/js/app.js` wraps `type="password"` modal fields in `<div class="relative">` + `pr-9` + `[data-password-toggle]` eye buttons and handles delegated click toggling across `form_modal.html` (while `auth.html` uses `togglePasswordVisibility`). `user_profile.html` NEVER displays inline optional password inputs on the Profile Details form — password updates use `openChangePasswordModal()` posting `action="change_password"` (`current_password`, `new_password`, `confirm_password`) verified with `check_password`.
- **Cloudinary Media Policy:** `.env` holds `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` (with empty placeholders in `.env.example`). `core/cloudinary_services.py` validates images (`<= 5 MB`) and uploads `320x320` face-cropped avatars to `edupredict/avatars`; only secure URLs are stored in MongoDB Atlas `users.avatar_url` and session `current_user.avatar_url`.
- **Global Loading Lock, `#ep-top-progress` & UI Widgets (`ui_widgets.js`, `nav.js`):** `#ep-top-progress` (`z-60`) animates via `window.EduPredictProgress = { start, done }` on SPA navigation and form submits; `initGlobalSubmitGuards` prevents duplicate POST submits, locks submit buttons with `<i class="fa-solid fa-spinner fa-spin">` + `"Processing..."` + `aria-busy="true"` (12s fallback + `pageshow` reset via `resetEduPredictSubmitLocks`, skipping `[data-no-lock]`, `[data-no-loading]`, and download forms); `initGradientUploaders()` powers `[data-gradient-uploader]` and `initFaqProWidgets()` powers `[data-faq-pro]` using safe DOM `Text` nodes + `<mark>` (never untrusted `innerHTML`).
- **Zero Horizontal Scrollbar & Ocean Blue Default:** `static/css/global.css` enforces `html, body { overflow-x: clip; }` and `data_table.html` wraps body cells (`break-words max-w-[18rem]`) instead of blanket `whitespace-nowrap`. Default theme is Ocean Blue (`shell_theme="blue"`, `accent="ocean"`, `#2563eb` light / `#3b82f6` dark).
- **1.2s Cancelable Auto-Upload & Theme Contract:** `static/js/theme_studio.js` (`bindSmartFileUploads()`) gives `input[type="file"][data-auto-submit="true"]` a 1200ms cancelable toast grace window (`window.eduPredictCancelUpload` cleared on SPA swaps via `reinitEduPredictUI()`). `get_user_theme_prefs(request)` MUST stay strictly session-only on GET (never query `users_col()`); guest `PORTAL` prefs merge on login via `sync_theme_prefs_on_login`; sidebar stays fixed on the left (no LTR/RTL flip).
- **Phases 23–25 Roadmap:** Phase 23: Real-Time Notifications + Admin Feedback Reply CRUD + Typewriter Page Guide Wizard Modal; Phase 24: Card-Grid User/Student/Teacher Directories + Modalized Upload/Quick Entry + Dot-Graph KPI Cards; Phase 25: Stepper Signup Wizard + Teacher Approval Guard + Student PDF Transcript.