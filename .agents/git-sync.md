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
Create or Switch to Role/Feature Dedicated Branch:

Work in a dedicated branch for the specific module being built so team members never clash (e.g., feature/core-shell, feature/admin-panel, feature/teacher-panel, feature/student-panel, feature/analyst-ml).

Bash
git checkout -B feature/<module-name>
git merge main
2. Mandatory Post-Task Git Routine (Run AFTER Testing the Feature)
Once you finish implementing the single requested feature:

Verify Zero Errors:

Bash
python manage.py check
Rewrite Section 4 (Active Handover State) of this file (.agents/git-sync.md):

REMOVE/CLEAR the outdated handover notes from the previous agent so this file stays short, clean, and current.

Write a crisp summary of what is now completed, what routes/collections were updated, and what the next agent should know.

Commit, Merge to main, and Push Both Branches:

Bash
git add .
git commit -m "feat(<module>): implement and verify <feature-name>"
git push -u origin feature/<module-name>
git checkout main
git pull origin main
git merge feature/<module-name>
git push origin main
Inform the user in Roman Urdu that their feature is live and synced on GitHub.

3. Multi-Developer Isolation Rules
Never Break Global Contracts: templates/base.html, templates/components/*, static/css/global.css, and core/db.py are shared across all panels. Only add backwards-compatible keys; never rename existing template block names ({% block content %}, {% block extra_js %}).

Panel Isolation:

Person working on Student Panel edits panels/views_student.py and templates/panels/student_*.html.

Person working on Teacher Panel edits panels/views_teacher.py and templates/panels/teacher_*.html.

Person working on Admin Panel edits panels/views_admin.py and templates/panels/admin_*.html.

Person working on Analyst & ML edits panels/views_analyst.py, analytics/*, and templates/panels/analyst_*.html.

4. Active Handover State (Agents: Replace This Block on Every Push)
```yaml
last_updated_by_agent: "Phase 1 Verification Agent (@verifier)"
active_branch_merged_to_main: "feature/core-shell -> main"
project_phase: "Phase 1 Complete - Core Django Shell, MongoDB Layer & App-Shell-3 Layout Verified"

completed_modules:
  - "Phase 1: Django Project Init (config/, accounts/, panels/, analytics/, manage.py, requirements.txt, .env.example, .gitignore)"
  - "Core Layer: core/db.py (MongoDBClient singleton, 6 collection helpers, ensure_indexes, check_db_health), core/decorators.py (login_required_custom, role_required), core/context_processors.py (global_context)"
  - "App-Shell-3 & Static Assets: templates/base.html, static/css/global.css (Light/Dark tokens), static/js/app.js (modals, toasts, theme toggle, drawer, table search), static/js/charts.js (Chart.js theme adapter)"
  - "Global UI Components: templates/components/{sidebar,topbar,metric_card,confirm_modal,form_modal,data_table,toast}.html"

active_routes:
  - "/ -> accounts.views.root_redirect"
  - "/auth/ -> accounts:auth_view"
  - "/auth/logout/ -> accounts:logout_view"
  - "/admin-panel/, /admin-panel/users/, /admin-panel/courses/, /admin-panel/tickets/ -> panels:admin_*"
  - "/teacher-panel/, /teacher-panel/students/, /teacher-panel/ingest/ -> panels:teacher_*"
  - "/student-panel/, /student-panel/report/ -> panels:student_*"
  - "/analyst-panel/ -> panels:analyst_dashboard"
  - "/analyst-panel/upload/, /analyst-panel/run-ml/ -> analytics:upload_dataset, analytics:run_predictions"

pending_modules_in_order:
  - "Phase 2: Authentication & Role-Based Routing (accounts app)"
  - "Phase 3: Analyst Panel + CSV Ingestion + Scikit-Learn ML Pipeline (analytics app)"
  - "Phase 4: Admin Panel (User/Course CRUD, Metrics, Support Tickets)"
  - "Phase 5: Teacher Panel (Class Overview, Attendance/Marks Ingestion, Alerts)"
  - "Phase 6: Student Panel (Personal Dashboard, AI Risk Card, Report Download)"

important_notes_for_next_agent:
  - "Next Phase: Phase 2 — Authentication & Role-Based Routing (accounts app) ONLY."
  - "Preserve all global contracts: templates/base.html, templates/components/*, static/css/global.css, core/db.py, core/decorators.py, core/context_processors.py."
  - "Wire @role_required and login_required_custom onto protected panel/analytics views as Phase 2 auth is activated; maintain zero comments across all .py/.html/.css/.js files."
```