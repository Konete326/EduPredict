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

## 4. Active Handover State (Agents: Replace This Block on Every Push)
```yaml
last_updated_by_agent: "QA Verifier & Release Engineer (@qa-v2)"
active_branch_merged_to_main: "feature/admin-panel -> main"
project_phase: "Admin Panel & System Performance Optimization Complete - Zero-Lag Caching, SPA Smooth Nav, Desktop Sidebar Collapse, Role Guards & Basic English 100% Verified"

completed_modules:
  - "Phase 1: Django Project Init, Core MongoDB Layer & App-Shell-3 Layout (core/, templates/components/, static/)"
  - "Phase 2: Authentication, Default Admin Sync & Role-Based Routing (accounts/services.py, accounts/views.py, templates/accounts/auth.html)"
  - "Phase 3: Analyst Panel, ML Engine, chunked CSV ingestion, anomaly detection & full-width dashboard"
  - "Phase 4 & 5: Admin Panel (CRUD, 5-row pagination, mobile cards, backups), Teacher Panel, Zero-Lag Caching & SPA Navigation"
  - "Phase 5 Performance & Stability Polish (Rules 16-19):"
      - "Zero-Lag In-Memory TTL Caching: Added get_cached/invalidate_cache in core/db.py with process-once thread locks for ensure_admin_seed_data & ensure_default_admin. Cached read queries across admin overview, users, courses, tickets, analyst context, and teacher/student KPIs. All cached GET endpoints respond in < 15ms."
      - "Strict Role Logic & Self-Action Guards: Blocked Admin from submitting self-tickets on /support/submit/; hidden New Ticket / feedback buttons for Admin in admin_tickets.html and sidebar.html footer; enforced dual user_id and email guards preventing Admin self-deletion, deactivation, or role modification."
      - "Desktop Sidebar Collapse & Nav Groups: Ensured html.sidebar-collapsed and body.sidebar-collapsed use !important transforms; added collapsible section toggles (data-nav-group-toggle) with localStorage persistence (edupredict_nav_groups) and desktop sidebar close action."
      - "SPA Smooth Navigation: static/js/nav.js with 45s prefetch cache, smooth page swapping with #page-extra-js script re-execution, form submit cache invalidation, and ?v=5 static asset cache-busting."
      - "Everyday Basic English: Replaced technical jargon across all headings, sidebar links, toast alerts, modals, and table headers with plain everyday English."
      - "Coming Soon Modals: All unbuilt routes across Teacher and Student panels display theme-aware Coming Soon modals with HTTP 200 Admin preview support."

verification_results:
  - "manage.py check: 0 issues reported."
  - "JS syntax check: node --check static/js/app.js & static/js/nav.js exit 0."
  - "File limits & zero comments: All .py, .html, .css, .js files <= 350 lines (views <= 250 lines) with 0 comments."
  - "Rule file size: .agents/rules/edupredict-rules.md is 10,364 bytes (< 24,000 bytes)."
  - "GET benchmarks: /admin-panel/ (8.2ms), /admin-panel/users/ (12.8ms), /admin-panel/courses/ (17.1ms), /admin-panel/tickets/ (10.3ms), /analyst-panel/ (1.3ms) all < 50ms."
  - "Functional checks: Admin self-action guards, CRUD on temporary user/course/ticket with identical initial/final MongoDB counts, JSON/CSV backups, and student coming-soon routes passed 100%."

active_routes_and_files:
  - "/, /auth/, /auth/logout/, catch-all 404 -> accounts/views.py & config/urls.py"
  - "/admin-panel/ -> panels:admin_dashboard"
  - "/admin-panel/users/ -> panels:admin_users"
  - "/admin-panel/courses/ -> panels:admin_courses"
  - "/admin-panel/tickets/ -> panels:admin_tickets"
  - "/admin-panel/backup/?format=json|csv -> panels:admin_backup_export"
  - "/support/submit/ -> panels:submit_support_ticket (Admin self-submission blocked)"
  - "/notifications/mark-read/ -> panels:mark_notifications_read"
  - "/analyst-panel/ -> panels:analyst_dashboard"
  - "/teacher-panel/* -> panels:views_teacher.py"
  - "/student-panel/* -> panels:views_student.py"

pending_modules_in_order:
  - "Phase 6: Student Panel Full Implementation (Personal Dashboard, AI Risk Card, Report Download, Study Recommendations)"

important_notes_for_next_agent:
  - "Next Phase: Build the dedicated Student Panel in panels/views_student.py and templates/panels/student_*.html."
  - "Preserve zero-lag caching (core/db.py get_cached/invalidate_cache), SPA transitions (#page-extra-js), 5-row pagination, mobile cards, and zero comments policy."
  - "Keep .env and .agents/* tracked in Git."
```