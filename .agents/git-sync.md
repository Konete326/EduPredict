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
last_updated_by_agent: "Phase 10 Admin Actor Audit & Analyst Active Thresholds Integrator"
active_branch_merged_to_main: "feature/actor-audit-analyst-thresholds -> main"
project_phase: "Phase 10 Complete: Actor Attribution, Analyst Thresholds Chip & Persist Alert Tests"

completed_modules:
  - "Phase 1-9: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Audit Triggers & Dynamic ML Settings"
  - "Phase 10: Admin Actor Audit Attribution & Analyst Active Thresholds:"
      - "Added actor_name parameter and attribution across all user, course, and ticket service mutations in panels/admin_services.py and wired _actor_name(request) in panels/views_admin.py."
      - "Added active portal_settings threshold summary chip and dynamic High Risk card badge in panels/views_analyst.py and templates/panels/analyst_dashboard.html."
      - "Extended unit tests in panels/tests.py (actor attribution & Analyst threshold chip) and analytics/tests.py (persist=True auto_student_alerts / auto_teacher_alerts notification filter)."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py test analytics panels --verbosity=2: 24/24 tests PASSED."
  - "node --check static/js/app.js & static/js/nav.js: PASSED."
  - "Zero comments and line-count limits verified across all 6 modified files."

active_routes_and_files:
  - "panels/admin_services.py (340 lines), panels/views_admin.py (237 lines), panels/views_analyst.py (239 lines), templates/panels/analyst_dashboard.html (272 lines), panels/tests.py (351 lines), analytics/tests.py (395 lines)"
  - "/admin-panel/logs/ -> panels:admin_logs"
  - "/admin-panel/settings/ -> panels:admin_settings"
  - "/analyst-panel/ -> panels:analyst_dashboard"

pending_modules_in_order:
  - "All Phase 1-10 core and polish items complete; ready for full-stack UAT or next user-requested feature."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys and invalidate_cache on mutations."
  - "Always track .env and .agents/* in Git."
```