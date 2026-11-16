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
last_updated_by_agent: "Phase 3 Verification Agent (@verifier)"
active_branch_merged_to_main: "feature/analyst-ml -> main"
project_phase: "Phase 3 Complete - Analyst Panel, Big Data Ingestion & Scikit-Learn ML Pipeline Verified"

completed_modules:
  - "Phase 1: Django Project Init, Core MongoDB Layer & App-Shell-3 Layout (core/, templates/components/, static/)"
  - "Phase 2: Authentication, Default Admin Sync & Role-Based Routing (accounts/services.py, accounts/views.py, templates/accounts/auth.html)"
  - "Phase 3: Big Data Ingestion & ML Pipeline (analytics/data_pipeline.py, analytics/ml_engine.py, analytics/views.py)"
  - "Phase 3 UI & Layout: Full-width fluid container in templates/base.html (no centered max-w-7xl box), multi-panel sidebar access for ADMIN in templates/components/sidebar.html, Analyst Hub in panels/views_analyst.py + templates/panels/analyst_dashboard.html"
  - "Phase 3 Docs Rules: Updated .agents/{git-sync,project-rules,design,trd}.md with .env auto-sync rule, latest package rule, and full-width responsive split layout rule"

active_routes_and_files:
  - "/, /auth/, /auth/logout/ -> accounts/views.py"
  - "/analyst-panel/ -> panels/views_analyst.py (@role_required(['ANALYST', 'ADMIN']), filters + ?export=csv + Chart.js data)"
  - "/analyst-panel/upload/ -> analytics/views.py:upload_dataset (@role_required(['ANALYST', 'ADMIN']), mode='sample' or .csv/.xlsx upload + ML trigger)"
  - "/analyst-panel/run-ml/ -> analytics/views.py:run_predictions (@role_required(['ANALYST', 'ADMIN']), RandomForest + Ridge + IsolationForest + TEACHER alerts)"
  - "/admin-panel/*, /teacher-panel/*, /student-panel/* -> Role-guarded placeholder shells ready for Phases 4-6"

pending_modules_in_order:
  - "Phase 4: Admin Panel (User/Course CRUD, Metrics, Support Tickets)"
  - "Phase 5: Teacher Panel (Class Overview, Attendance/Marks Ingestion, Alerts)"
  - "Phase 6: Student Panel (Personal Dashboard, AI Risk Card, Report Download)"

important_notes_for_next_agent:
  - "Next Phase: Phase 4 — Admin Panel (User/Course CRUD, Metrics, Support Tickets) in panels/views_admin.py and templates/panels/admin_*.html ONLY."
  - "Use full-width responsive layout (no centered max-w-7xl mx-auto) and existing global components (metric_card.html, data_table.html, confirm_modal.html, form_modal.html, toast.html)."
  - "Keep .env and .agents/* tracked and pushed to GitHub; maintain zero comments across all .py/.html/.css/.js files and file length <= 350 lines."
```