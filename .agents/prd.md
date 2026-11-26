# Product Requirements Document (PRD) — EduPredict

## 1. Project Overview
- **Project Name:** EduPredict — Big Data & Predictive Analytics Educational Portal
- **Framework & Database:** Python Django (MVT Architecture) + MongoDB Atlas (Cloud Database)
- **Target Audience:** Educational Institutions (Administrators, Teachers, Students, and Data Analysts)
- **Core Objective:** Provide an automated, ultra-simple, beginner-friendly educational portal that ingests student academic/attendance data, stores and processes it in MongoDB Atlas, runs automated Machine Learning predictions (dropout risk, performance trends, course demand), and displays insights via clean, interactive dashboards with Light/Dark mode support.

## 2. Core Philosophy: Ultra-Simple & Automated UX
- **Zero Technical Friction for Users:** End-users (Students, Teachers, Admins, Analysts) will never configure complex parameters. Uploads are 1-click CSV/Excel drops; predictions run automatically upon data upload or via a single "Run Prediction" button.
- **Unified Global Shell:** Every panel uses the exact same `@efferd/app-shell-3` layout structure (Collapsible Left Sidebar + Top Header + Main Content Area) so all team members' work looks like a single, unified system.
- **Global Reusable Components:** Modals, Cards, Tables, Badges, Toast Notifications, and Forms are created once inside `templates/components/` and included everywhere via Django `{% include %}`.

## 3. User Roles & Dedicated Panels

### 3.1. Administrator Panel (`/admin-panel/`)
- **Overview Dashboard (`/admin-panel/`):** 4 KPI metric cards (Total Students, Active Teachers, High Dropout Risk Count, System Uptime Status) + 2 Chart.js charts (Department-wise Enrolment & Monthly Attendance Trend).
- **User Management (`/admin-panel/users/`):** View, Add, Edit, Toggle Active Status, and Delete users (`Admin`, `Teacher`, `Student`, `Analyst`) with smart defaults, strict self-protection lock (`data-is-self="true"` preventing self-delete, self-deactivation, and self-role-downgrade), and global searchable/paginated views.
- **Course & Batch Management (`/admin-panel/courses/`):** CRUD for courses, subjects, and academic batches with smart Course Code suggestions and prefix-based Department inference.
- **Support Ticket Resolution (`/admin-panel/tickets/`):** View user feedback/issues and resolve/delete tickets in 1 click (Admins manage incoming tickets and do not submit tickets to themselves).
- **Activity Logs & Backups (`/admin-panel/logs/`, `/admin-panel/backup/`):** Filterable audit trail (`USERS`, `COURSES`, `TICKETS`, `DATA`, `SYSTEM`), manual audit notes, CSV log export, and 1-click MongoDB Backup export (`JSON`/`CSV`).
- **Portal Settings (`/admin-panel/settings/`):** Dynamic institution metadata, passing GPA, attendance minimum, ML risk thresholds, and automated alert toggles + 1-click Theme & Appearance Live Studio launch.

### 3.2. Teacher Panel (`/teacher-panel/`)
- **Class Overview Dashboard (`/teacher-panel/`):** Summary of assigned classes, average class score, and automated list of "At-Risk Students" requiring attention.
- **1-Click Data Ingestion (`/teacher-panel/ingest/`):**
  - Frictionless CSV/Excel upload with a 1.2s cancelable auto-upload toast grace window, automatic validation, missing-value cleaning, and sample CSV template download.
  - Quick Student Entry with smart ID suggestion, datalist autocomplete, and automatic field pre-fill.
- **Student Performance Tracker (`/teacher-panel/students/`):** Auto-filtering dropdowns (batch, course, status), performance badges (`Excellent`, `Stable`, `Needs Help`, `High Dropout Risk`), and quick inline/modal marks editing.
- **Risk Alerts (`/teacher-panel/alerts/`):** Dedicated alert feed and 1-click personalized notification delivery to struggling students.

### 3.3. Student Panel (`/student-panel/`)
- **Personal Learning Dashboard (`/student-panel/`):** Clean summary of current Attendance %, GPA/Grade Prediction, Earned Credits, and class batch rank.
- **Report Card & CSV Download (`/student-panel/report/`, `/student-panel/report/download/`):** Subject-wise progress charts comparing student marks with class average plus downloadable report summary.
- **AI Study Tips (`/student-panel/tips/`):** Plain-language automated recommendations and weekly improvement targets.
- **Notifications & Support Center (`/student-panel/notifications/`):** View alerts from teachers/system and submit quick support tickets.

### 3.4. Data Analyst Panel (`/analyst-panel/`)
- **Big Data & ML Hub (`/analyst-panel/`, `/analyst-panel/upload/`, `/analyst-panel/run-ml/`, `/analyst-panel/evaluation/`):** Upload historical or real-time datasets with 1.2s cancelable auto-upload, automatic missing-data imputation, auto-filterable predictions explorer, CSV export, and leakage-free ML evaluation (`RandomForestClassifier`, `Ridge`, `IsolationForest`).
- **Model Health & Thresholds (`/analyst-panel/accuracy/`):** Dataset health diagnostics, label coverage status, and live portal threshold visibility.

## 4. Global Features (Shared Across All Panels)
1. **Authentication & Role Routing (`/auth/`, `/auth/logout/`):** Unified Sign-In / Sign-Up page with Show/Hide password eye toggles on every password field, Caps Lock warnings, guest `PORTAL` theme persistence synced on login, and automatic role routing.
2. **My Profile & Settings (`/profile/`):** Shared across all logged-in roles (`Admin`, `Teacher`, `Student`, `Analyst`) to update full name, email, optional department/batch/phone/bio, and optional password (with Show/Hide eye toggles), while keeping account `role` read-only and protected.
3. **Theme & Appearance Live Studio (`/theme/preferences/`):** Per-user & per-panel customizable Light/OLED Dark mode, 6 Header/Sidebar Chrome Themes, 13 Brand Accent Swatches, 6 Surface Presets, Comfortable/Compact density (sidebar fixed on the left — no LTR/RTL flip), Accent Auto-Sync, and instant scoped persistence (`localStorage` + MongoDB).
4. **Organized Sidebar & Deduplicated Topbar:** Strict Role Sidebar Isolation (`Admin Core` + `Support & Logs` for Admin; dedicated single group for Teacher/Student/Analyst) plus a unified `Settings & Theme` dropdown for every logged-in role; topbar holds a single Light/Dark button, Notification Bell, Quick Search, and `My Profile` pill without duplicate Theme buttons.
5. **Password Toggles, Mobile Cards & Smart Automation:** Global `[data-password-toggle]` eye buttons in `form_modal.html`, `/profile/`, and `/auth/`; crisp mobile stacked cards (`md:hidden`) and Confusion Matrix cards (`sm:hidden`); 1.2s cancelable auto-upload grace window.

## 5. Strict Scope & Anti-Bloat Rules
- **Reject MERN/React Completely:** No React, Vite, Next.js, or JSX files. Everything is Pure Django + HTML5 Templates + Tailwind CSS + Vanilla JS.
- **One Feature Per Execution:** Coding agents must implement only the single feature/module requested by the user, test it, sync with Git, and ask before starting the next feature.

## 6. Current Status & Production Readiness
- **Built & Verified Core & Ops Scope (Phases 1–59):** All 4 Role Panels, ML Pipeline & Leakage-Free Evaluation, Admin Activity Logs & Portal Settings, Theme Studio, My Profile (`/profile/`), Cloudinary Avatars, Real-Time Notifications Feed, Admin Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval Guard, ReportLab PDF Report Cards & Class Rosters, Live `/health/` System Monitoring (with cgroup memory telemetry), End-to-End Multi-Role UAT (`python manage.py verify_uat`), Encrypted/Checksummed Backups (`export_backup`, `verify_backup`, `decrypt_backup`), Rate Limiting, WhiteNoise, Docker, and CI Pipeline are complete.

## 7. Enterprise UI/UX Masterplan, Zero-Click Automation & Aptech Standard Roadmap (Phases 60–63)
To match live enterprise educational platforms (Civitas Learning, EAB Navigate, PowerSchool) and Aptech submission standards ("Less Clutter, Higher Quality" — see `.agents/design.md` Section 14 for full blueprint):
- **Phase 60 (26A — Visual Polish & Shell Cleanup):** Apply 90/8/2 color discipline & 3-layer hairline depth, ultra-clean clickable KPI cards (no synthetic dot-matrix noise), Chart.js 6 global defaults, scroll-aware 4-item Topbar (Breadcrumb, `Ctrl+K` Command Search, Notification Bell, Light/Dark toggle), slim sidebar `3px` active bar, Admin-Only Theme Studio inside Portal Settings, and Instant 3-Bullet Help Popover.
- **Phase 61 (26B — Global Image Cropper & Ticket Lightbox):** Add reusable `image_cropper_modal.html` (`Cropper.js` CDN) for Profile Avatars (1:1 circle crop + Cloudinary old-avatar cleanup) and Feedback Screenshots (`Ctrl+V` clipboard paste + Free/16:9/4:3 crop + Attachment Chips), plus Admin Ticket Detail Drawer & Full-Screen Image Lightbox.
- **Phase 62 (26C — Table-First Directories, Student 360° & Teacher Reject):** Default User & Student directories to a clean 5–6 column Compact Table with `[Table | Cards]` toggle, 1-click Copy ID, right-side **Student 360° Slide-Over Drawer** (Attendance Ring, Predicted GPA, AI Risk Reasons, Marks, Alerts), and Admin **Reject with Reason** workflow for pending Teachers.
- **Phase 63 (26D — Hyper-Automation, Live LMS Stream & Aptech Submission Pack):** Auto-run fast ML (`Ridge`, `RandomForest(n_estimators=50, n_jobs=-1)`, `IsolationForest`) + zero-click High-Risk Student/Teacher auto-alerts on marks/CSV upload, Smart CSV Column Auto-Mapper + preview, 1-click `"Notify All High-Risk Students"`, `visibilitychange` instant notification sync, dynamic live `institution_name`/`current_term` PDF branding, Analyst `"Simulate Live LMS Stream"` (5s interval), and Aptech Final Submission Pack (`docs/aptech_submission/`: Project Report with Flowcharts/DFDs, Test CSV, Installation ReadMe, Demo Walkthrough).

## 8. Phase 75 — Multi-Agent AI Message Dock, Real-Data Honesty, A4 Print PDFs & 17" Viewport-Fit
- **Multi-Agent AI Message Dock (`Dr. Amina`, `Prof. Zain`, `Sara`, `Bilal`):** Floating WhatsApp-style Zig-Zag chat dock (`templates/components/ai_message_dock.html`, `static/js/ai_agent_dock.js`, `/ai-agents/chat/`) powered by `GEMINI_BACKEND_KEY_3` (`gemini-flash-lite-latest`) + live MongoDB context, automatic specialist handoff with concise task preview, strictly ephemeral memory-only sessions (zero saved chat history), and zero sparkle icons (`fa-wand-magic-sparkles` banned).
- **Zero Dummy Data & Real-Data-Only Charts:** Student self-signup and Admin user creation never insert fake `CS-101` `student_records`; charts, Contour Strata (`chart_data.contour_series` / `chart_data`), and Orbit Goals render real MongoDB numbers or honest empty states.
- **Authentic A4 Printable PDFs:** Student transcripts and teacher class rosters render as formal black-on-white `A4` Registrar/Examination documents (`panels/pdf_services.py` + `@media print`), never copying web UI cards.
- **Single Desktop Sidebar Toggle & 17" Viewport-Fit UX:** Desktop displays a single collapse toggle in the topbar (`#mobile-sidebar-close` carries `lg:hidden` for mobile drawers only), `/profile/` (`user_profile.html`) stays untouched, and `/notifications/`, `/student-panel/`, `/student-panel/tips/`, and `/analyst-panel/accuracy/` fit 17" desktop screens cleanly via compact spacing and 2-tab layouts.

## 9. Phase 76 — Purpose-Built AI Agents, DOM Control & Polls, Clean A4 Printing & Alert Modal
- **Purpose-Built AI Specialists & Active `sessionStorage` Continuity:** Upgrades the AI Message Dock to `EduCoach AI`, `PulseML AI`, `CourseOps AI`, and `HelpDesk AI` with circular inline SVG Data-URI DPs and active-chat `sessionStorage` persistence across page navigation until explicitly Reset or Closed/Ended.
- **Strict RBAC/Password Guardrails, DOM Automation & Interactive Polls:** Blocks cross-role data leakage and password/credential queries deterministically, executes real PRD-aware DOM actions (Redirect, Table Filter, Element Click, Modal Form Open + Auto-Fill), and renders interactive Poll cards inside the chat dock.
- **Zero-UI Single-Page A4 Report Card Printing:** Adds `?inline=1` PDF disposition support and `printOfficialA4Report()` + monochrome `#ep-a4-print-sheet` + `@page { size: A4 portrait; margin: 0; }` print rules so printed report cards never include web UI controls, Download CSV buttons, graphs, or browser URL headers.
- **Alert History Detail Modal, Clean Orbit Ring & Progress Bar Fix:** Adds `#notification-detail-modal` on `/notifications/` (working identically before and after Mark Read while preserving active tabs), removes overlapping `"Goal Score"` text inside `student_tips.html` Orbit SVG rings, and prevents stuck `#ep-top-progress` bars via `data-no-loading`/download SPA bypass and a `4s` watchdog + print/focus/popstate reset guards.

## 10. Phase 77 — Vercel Production Deployment & GitHub Continuous Sync
- **Vercel WSGI & Reverse-Proxy Readiness (`vercel.json`, `config/settings.py`):** Configures `config/wsgi.py` with `maxDuration: 60` in `vercel.json`, cloud `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST`, and CSP headers for production hosting on Vercel (not Hugging Face Spaces).
- **GitHub Source-of-Truth & Automatic Live Deployment (`.github/workflows/django.yml`, `README.md`):** Connected to `https://github.com/Konete326/EduPredict` (`main` branch); every push to `main` runs Django CI checks + all 13 `static/js/*.js` audits + tests + `verify_uat`, and triggers automatic live deployment on Vercel while keeping raw runtime secrets (`GEMINI_BACKEND_KEY_3`) out of Git history (`GH013` safe).

## 11. Phases 81–86 — Public 21st.dev Showcase, Curated Theme Studio & Single-Institute Provisioning
- **21st.dev Public Landing & Live MongoDB Showcase (`accounts/public_data.py`):** Upgrades the public homepage (`/`) with the **Provably Hero** live credential showcase, interactive walkthrough preview, and **Live Testimonial Globe** hydrated directly from MongoDB (`users`, `courses`, `student_records`, `predictions`, `support_tickets`) with a 60s TTL cache.
- **21st.dev Curated Theme Studio:** Adds curated 21st.dev theme presets and WCAG-checked per-theme text contrast tokens across Light & Dark modes inside the Admin-governed Theme Studio.
- **Single-Institute Training vs. Live Roster Separation (`is_training_dataset`):** Admin's one-time Master Training CSV (`sample_datasets/admin_master_training_dataset.csv`) is ingested with `is_training_dataset=True` so ML models train on historical data while live Teacher and Admin class rosters strictly exclude training rows.
- **Teacher Approval, Class CSV Auto-Provisioning & Credentials Export:** Approved Teachers upload isolated class CSVs (`student_id, full_name, birth_date, course_code, marks, attendance`) that automatically provision/update Student accounts (`student_id` username + `<first_name>@<birth_date>` password), run live ML predictions, and expose a 1-click **Download Credentials CSV** action (`/teacher-panel/credentials/download/`, `panels:teacher_credentials_csv`).
- **Read-Only Student Panel & Dual Feedback:** Students sign in with `student_id` + `<first_name>@<birth_date>` into a strictly read-only academic dashboard displaying their assigned teacher and can route **Dual Feedback** either to their **Teacher** (Teacher Alerts inbox) or to **Admin** (Admin Tickets).
- **Sample Datasets Pack & Live Stream Hydration (`sample_datasets/`):** Bundles `admin_master_training_dataset.csv` (200 rows) + 6 teacher class CSVs (18 rows each) for end-to-end demos, alongside real-time Analyst LMS stream log/table hydration and background-tab pause guards.