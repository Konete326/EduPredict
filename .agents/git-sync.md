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
last_updated_by_agent: "Phase 4 Verification Agent (@verifier)"
active_branch_merged_to_main: "feature/admin-panel -> main"
project_phase: "Phase 4 Complete - Admin Panel, Global Components, Collapsible Shell & 404 Verified"

completed_modules:
  - "Phase 1: Django Project Init, Core MongoDB Layer & App-Shell-3 Layout (core/, templates/components/, static/)"
  - "Phase 2: Authentication, Default Admin Sync & Role-Based Routing (accounts/services.py, accounts/views.py, templates/accounts/auth.html)"
  - "Phase 3 & Polish: Analyst Panel, ML Engine, chunked CSV + 25MB limit in analytics/data_pipeline.py, compact viewport-fit in analyst_dashboard.html"
  - "Phase 4 Admin Backend: panels/admin_seed.py (seeding, overview metrics, JSON/CSV backup), panels/admin_services.py (Users/Courses/Tickets CRUD, mark_notifications_read, table formatters), panels/views_admin.py, core/db.py (courses_col + unique index)"
  - "Phase 4 Global UI & UX: Collapsible desktop/mobile sidebar (Rule 14), 5-row pagination + mobile card sync (Rules 12-13), Coming Soon modal/panel (Rule 15), sortable tables, custom 404 (templates/404.html + accounts.views.error_404), Modern Web Guidance polish (static/css/global.css, static/js/app.js)"
  - "Phase 4 Admin Templates: templates/panels/admin_{dashboard,users,courses,tickets}.html & coming_soon_panel.html"

active_routes_and_files:
  - "/, /auth/, /auth/logout/, catch-all 404 -> accounts/views.py & config/urls.py"
  - "/admin-panel/ -> panels:admin_dashboard (KPIs, Dept Enrollment vs Capacity bar chart, Risk doughnut, Recent Tickets)"
  - "/admin-panel/users/, /admin-panel/courses/, /admin-panel/tickets/ -> Full MongoDB Atlas CRUD + filters + 5-row pagination"
  - "/admin-panel/backup/?format=json|csv -> panels:admin_backup_export"
  - "/support/submit/ -> panels:submit_support_ticket (global sidebar Support modal endpoint)"
  - "/notifications/mark-read/ -> panels:mark_notifications_read (CSRF POST JSON endpoint)"
  - "/analyst-panel/* -> panels/views_analyst.py & analytics/views.py"
  - "/teacher-panel/*, /student-panel/* -> Coming Soon roadmap views (panels/views_teacher.py, panels/views_student.py)"

pending_modules_in_order:
  - "Phase 5: Teacher Panel (Class Overview, Attendance/Marks Ingestion, Alerts)"
  - "Phase 6: Student Panel (Personal Dashboard, AI Risk Card, Report Download)"

important_notes_for_next_agent:
  - "Next Phase: Phase 5 — Teacher Panel (Class Overview, Attendance/Marks Ingestion, Alerts) in panels/views_teacher.py and templates/panels/teacher_*.html ONLY."
  - "Preserve all global contracts: templates/base.html, templates/components/* (5-row pagination, mobile cards, Coming Soon & confirm/form modals), static/css/global.css, static/js/app.js, core/db.py."
  - "Keep .env and .agents/* (including .agents/rules/* and .agents/skills/*) tracked and pushed; maintain zero comments across all .py/.html/.css/.js files, panels/views_*.py <= 250 lines, and other files <= 350 lines."
```