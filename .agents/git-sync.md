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
last_updated_by_agent: "Phase 8 Admin Activity Logs & Portal Settings Swarm"
active_branch_merged_to_main: "feature/admin-logs-settings -> main"
project_phase: "Phase 8 Complete: Admin Activity Logs & Portal Settings"

completed_modules:
  - "Phase 1-5: Core Shell, Auth/RBAC, Admin/Teacher Panels & Rule 20 Sidebar Isolation"
  - "Phase 6 & 7: Student Panel (Dashboard, Report Card, Study Tips, Alerts & Support), Teacher Risk Alerts & Analyst Model Health"
  - "ML Evaluation Tasks 1-3: Leakage-free sklearn Pipelines, analyst_evaluation_section, TTL caching"
  - "Phase 8: Admin Activity Logs & Portal Settings:"
      - "Created panels/admin_audit_services.py (activity_logs & system_settings MongoDB collections, TTL cache admin:logs:<cat> & admin:settings, CSV export, manual log notes, settings update & reset)."
      - "Updated panels/admin_seed.py, panels/views_admin.py (admin_logs & admin_settings), and panels/urls.py (panels:admin_logs, panels:admin_settings)."
      - "Created templates/panels/admin_logs.html & templates/panels/admin_settings.html (CSS tokens, 4 KPI cards, 5-row data_table, mobile cards, modals) and wired live sidebar links in templates/components/sidebar.html."
      - "Added AdminLogsAndSettingsTests in panels/tests.py."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py test analytics panels --verbosity=2: 23/23 tests PASSED."
  - "node --check static/js/app.js & static/js/nav.js: PASSED."
  - "Zero comments and line-count limits verified across all 8 modified/created files."

active_routes_and_files:
  - "/admin-panel/logs/ -> panels:admin_logs (panels/views_admin.py, panels/admin_audit_services.py, templates/panels/admin_logs.html)"
  - "/admin-panel/settings/ -> panels:admin_settings (panels/views_admin.py, panels/admin_audit_services.py, templates/panels/admin_settings.html)"
  - "templates/components/sidebar.html, panels/admin_seed.py, panels/urls.py, panels/tests.py"

pending_modules_in_order:
  - "All Phase 1-8 core and optional Admin modules completed; ready for user acceptance testing or new feature requests."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys and invalidate_cache on mutations."
  - "Always track .env and .agents/* in Git."
```