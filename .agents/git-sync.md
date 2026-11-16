# Automated GitHub Sync & Multi-Agent Handover (`git-sync.md`)

> **CRITICAL NOTICE FOR AI AGENTS:**
> The human users giving you tasks **DO NOT know Git or GitHub commands**. You (the AI Agent) are 100% responsible for managing branches, pulling updates, resolving conflicts, updating this handover log, committing, and pushing to GitHub automatically before and after every single task.

---

## 1. Mandatory Pre-Task Git Routine (Run BEFORE Touching Any Code)
Whenever a user asks you to build or fix anything, execute these exact steps silently in the terminal first:

1. **Read `.agents/git-sync.md` (Section 4 below)** to see what the previous agent completed and which files were modified.
2. **Fetch & Pull Latest Main:**
   ```bash
   git checkout main
   git pull origin main
   ```
3. **Create or Switch to Role/Feature Dedicated Branch:**
   Work in a dedicated branch for the specific module being built so team members never clash (e.g., `feature/core-shell`, `feature/auth-rbac`, `feature/analyst-ml`, `feature/admin-panel`, `feature/teacher-panel`, `feature/student-panel`).
   ```bash
   git checkout -B feature/<module-name>
   git merge main
   ```

## 2. Mandatory Post-Task Git Routine & `.env` Auto-Sync Rule (Run AFTER Testing the Feature)
- **`.env` & Full Project Auto-Sync Rule (MANDATORY):** `.env` and ALL project files (code, `templates/`, `static/`, `requirements.txt`, `.env.example`, `.gitignore`, `.agents/*`) MUST always be tracked, committed, and auto-synced/pushed to GitHub whenever any change occurs.
- **`.gitignore` Scope Lock:** ONLY installed library/venv folders and local caches (`.venv/`, `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`, `db.sqlite3`) remain ignored in `.gitignore`. Never ignore `.env`.

Once you finish implementing the single requested feature:

1. **Verify Zero Errors:**
   ```bash
   python manage.py check
   ```
2. **Rewrite Section 4 (Active Handover State) of this file (`.agents/git-sync.md`):**
   - REMOVE/CLEAR the outdated handover notes from the previous agent so this file stays short, clean, and current.
   - Write a crisp summary of what is now completed, what routes/collections were updated, and what the next agent should know.
3. **Commit, Merge to `main`, and Push Both Branches (including `.env` and `.agents/*`):**
   ```bash
   git add .
   git commit -m "feat(<module>): implement and verify <feature-name>"
   git push -u origin feature/<module-name>
   git checkout main
   git pull origin main
   git merge feature/<module-name>
   git push origin main
   ```
4. Inform the user in Roman Urdu that their feature is live and synced on GitHub.

3. Multi-Developer Isolation Rules
Never Break Global Contracts: templates/base.html, templates/components/*, static/css/global.css, and core/db.py are shared across all panels. Only add backwards-compatible keys; never rename existing template block names ({% block content %}, {% block extra_js %}).

Panel Isolation:

Person working on Student Panel edits panels/views_student.py and templates/panels/student_*.html.

Person working on Teacher Panel edits panels/views_teacher.py and templates/panels/teacher_*.html.

Person working on Admin Panel edits panels/views_admin.py and templates/panels/admin_*.html.

Person working on Analyst & ML edits panels/views_analyst.py, analytics/*, and templates/panels/analyst_*.html.

4. Active Handover State (Agents: Replace This Block on Every Push)
```yaml
last_updated_by_agent: "Phase 5 Lead Implementation & Verification Agent"
active_branch_merged_to_main: "feature/teacher-panel -> main"
project_phase: "Phase 5 Complete - Teacher Panel, Zero-Lag Caching, SPA Navigation & Basic English Nav Verified"

completed_modules:
  - "Phase 1: Django Project Init, Core MongoDB Layer & App-Shell-3 Layout (core/, templates/components/, static/)"
  - "Phase 2: Authentication, Default Admin Sync & Role-Based Routing (accounts/services.py, accounts/views.py, templates/accounts/auth.html)"
  - "Phase 3 & Polish: Analyst Panel, ML Engine, chunked CSV + 25MB limit in analytics/data_pipeline.py, compact viewport-fit in analyst_dashboard.html"
  - "Phase 4 Admin Backend & Global Shell: panels/admin_seed.py, panels/admin_services.py, panels/views_admin.py, core/db.py (courses_col + unique index), 5-row pagination, mobile card sync, Coming Soon modals, 404 handler"
  - "Phase 5 Zero-Lag Caching & SPA Navigation (Rule 19): In-memory TTL cache (core/db.py get_cached/invalidate_cache), run-once guards on ensure_admin_seed_data & ensure_default_admin (saving 2.5-3.5s per request, warm GETs < 100ms), and static/js/nav.js (smooth client-side navigation + sessionStorage GET cache + hover prefetch + re-executing page scripts)"
  - "Phase 5 Global UX Polish: Collapsible sidebar on desktop (body.sidebar-collapsed with !important override) & mobile, basic everyday English across all sidebar links & panel headers (Rule 16), collapsible nav groups with localStorage persistence, removed duplicate '+' symbols from action buttons (Rule 17), blocked Admin self-tickets on /support/submit/ and guarded USR-1000 from deletion/deactivation (Rule 18)"
  - "Phase 5 Teacher Backend & Services: panels/teacher_services.py (333 lines, 0 comments) with student status badges (Excellent, Stable, Needs Help, High Risk), get_teacher_dashboard_context, get_teacher_students_context, get_teacher_ingest_context, update_student_record_inline, send_student_alert (notifications_col), delete_student_record"
  - "Phase 5 Teacher Views & Routes: panels/views_teacher.py (171 lines, 0 comments) with /teacher-panel/ (Class Home), /teacher-panel/students/ (Student List + filters + CSV export), /teacher-panel/ingest/ (Upload Marks + 1-click sample class sheet + manual entry form + roster editor)"
  - "Phase 5 Teacher Templates: templates/panels/teacher_dashboard.html (KPIs, Course Attendance & Marks bar chart, Student Status doughnut, At-Risk table), templates/panels/teacher_students.html (filters, 5-row table + mobile cards, Update Marks modal, Send Alert modal, Delete confirm modal), templates/panels/teacher_ingest.html (upload sheet, manual form, class roster editor, upload logs)"

active_routes_and_files:
  - "/, /auth/, /auth/logout/, catch-all 404 -> accounts/views.py & config/urls.py"
  - "/admin-panel/ -> panels:admin_dashboard (KPIs, Dept Enrollment vs Capacity bar chart, Risk doughnut, Recent Tickets)"
  - "/admin-panel/users/, /admin-panel/courses/, /admin-panel/tickets/ -> Full MongoDB Atlas CRUD + filters + 5-row pagination"
  - "/admin-panel/backup/?format=json|csv -> panels:admin_backup_export"
  - "/support/submit/ -> panels:submit_support_ticket (global sidebar Support modal endpoint, blocks Admin self-submission)"
  - "/notifications/mark-read/ -> panels:mark_notifications_read (CSRF POST JSON endpoint)"
  - "/analyst-panel/* -> panels/views_analyst.py & analytics/views.py"
  - "/teacher-panel/ -> panels:teacher_dashboard (Class Home)"
  - "/teacher-panel/students/ -> panels:teacher_students (Student List, CSV export, Update Marks, Send Alert)"
  - "/teacher-panel/ingest/ -> panels:teacher_ingest (Upload spreadsheet, 1-click sample class sheet, manual entry form)"
  - "/student-panel/* -> Coming Soon roadmap views (panels/views_student.py)"

pending_modules_in_order:
  - "Phase 6: Student Panel (Personal Dashboard, AI Risk Card, Report Download)"

important_notes_for_next_agent:
  - "Next Phase: Phase 6 — Student Panel (Personal Dashboard, AI Risk Card, Report Download) in panels/views_student.py and templates/panels/student_*.html ONLY."
  - "Zero-lag caching is active: wrap heavy read queries in get_cached('student:...', fn, ttl=30.0) and call invalidate_cache() after student updates/mutations."
  - "Preserve all global contracts: templates/base.html, templates/components/* (5-row pagination, mobile cards, Coming Soon & confirm/form modals), static/css/global.css, static/js/app.js, static/js/nav.js, core/db.py."
  - "Keep .env and .agents/* (including .agents/rules/* and .agents/skills/*) tracked and pushed; maintain zero comments across all .py/.html/.css/.js files, panels/views_*.py <= 250 lines, and other files <= 350 lines."
```