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
last_updated_by_agent: "Phase 23 Swarm Coordinator & UAT Automation Team"
active_branch_merged_to_main: "feature/e2e-uat-health -> main"
project_phase: "Phase 23 Complete: Live End-to-End UAT Automation Suite & /health/ System Monitoring"

completed_modules:
  - "Phase 1-22: Core Shell, Auth/RBAC, 4 Role Panels, Leakage-Free ML, Admin Logs & Settings, Live Theme Studio, My Profile, Password Toggles, 1.2s Auto-Upload, ReportLab PDF Report Cards & Rosters."
  - "Phase 23: Live End-to-End UAT Automation Suite & /health/ Monitoring:"
      - "Added core/views_health.py (77 lines): MongoDB Atlas connection ping, sub-second latency tracking, live collection counts, and memory diagnostics returning JSON HTTP 200/503."
      - "Updated config/urls.py (14 lines): Registered /health/ route (system_health)."
      - "Added core/management/commands/verify_uat.py (205 lines): Complete multi-role simulator testing Health, Auth/RBAC, Admin self-lock, Teacher marks & PDF roster, Analyst ML, Student overview & PDF report card, and Support ticket workflow (7/7 checks PASS)."
      - "Added panels/test_uat.py (75 lines): 6 comprehensive unit tests covering /health/ endpoint response and verify_uat command execution."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py verify_uat: 7/7 UAT steps PASSED in 12.31s."
  - "manage.py test: 57/57 tests PASSED in 19.48s."
  - "node --check: all JS scripts passed with 0 errors."
  - "Zero comments audit: 0 comments across all modified and newly created files."
  - "Line caps: All files strictly within limits (views <= 250, commands <= 350)."

active_routes_and_files:
  - "core/views_health.py (77 lines), core/management/commands/verify_uat.py (205 lines), panels/test_uat.py (75 lines)"
  - "/health/ -> system_health"
  - "python manage.py verify_uat -> End-to-end multi-role UAT verification"

pending_modules_in_order:
  - "Phase 24: Production Deployment & CI/CD Pipeline Polish (.github/workflows/django.yml, Gunicorn WSGI readiness)."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Health endpoint is active at /health/ with live MongoDB Atlas ping."
  - "Always track .env and .agents/* in Git."
```