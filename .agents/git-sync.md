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
last_updated_by_agent: "EduPredict Production Operations & Automation Team"
active_branch_merged_to_main: "feature/backup-automation-and-sentry -> main"
project_phase: "Phase 30 Complete: Automated Database Backup CLI & Sentry Exception Tracking"

completed_modules:
  - "Phase 1-28: Core Shell, Auth/RBAC, 4 Role Panels, Leakage-Free ML, Admin Logs & Settings, Live Theme Studio, My Profile, Password Toggles, 1.2s Auto-Upload, ReportLab PDF Report Cards, UAT Suite, Real-Time Health, CI/CD Pipeline, WhiteNoise Static Serving, Docker Containers, and Atlas Connection Pooling."
  - "Phase 29: Production Theme-Aware 500 Error Page & README Operations Runbook:"
      - "Added templates/500.html (99 lines, 0 comments): Resilient standalone server error template matching EduPredict design tokens, dark mode, FontAwesome icons, with Reload, Portal Home, and /health/ diagnostic status links."
      - "Updated README.md: Comprehensive production operations runbook, architecture overview, Docker container commands, 4-role credentials matrix, and test verification guide."
  - "Phase 30: Automated Database Backup CLI & Sentry Exception Tracking Integration:"
      - "Added core/management/commands/export_backup.py (61 lines, 0 comments): CLI management command supporting --format (json/csv), --output-dir, --filename, and --quiet flags to cleanly extract all 6 MongoDB collections for cron/automated backups."
      - "Updated config/settings.py (132 lines, 0 comments): Added conditional sentry_sdk initialization with DjangoIntegration and SENTRY_TRACES_SAMPLE_RATE when SENTRY_DSN environment variable is provided."
      - "Updated requirements.txt (26 lines): Added sentry-sdk==2.75.0, certifi==2026.10.23, and urllib3==2.8.0."
      - "Updated .env.example (10 lines, 0 comments): Documented optional SENTRY_DSN and SENTRY_TRACES_SAMPLE_RATE."
      - "Updated README.md (164 lines): Added export_backup CLI usage documentation and updated test suite count to 67 tests."
      - "Updated panels/test_uat.py (213 lines, 0 comments): Added unit tests verifying export_backup CLI execution for JSON and CSV, invalid format error handling, and conditional Sentry SDK initialization."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py verify_uat: 7/7 UAT steps PASSED in 9.69s."
  - "manage.py test: 67/67 tests PASSED in 18.63s."
  - "node --check: all 5 JS scripts passed with 0 errors."
  - "Zero comments audit: 0 comments across all modified and newly created files."
  - "Line caps: All files strictly within limits (export_backup.py 61 lines, settings.py 132 lines, test_uat.py 213 lines)."

active_routes_and_files:
  - "core/management/commands/export_backup.py (61 lines)"
  - "config/settings.py (132 lines)"
  - "panels/test_uat.py (213 lines)"
  - "python manage.py export_backup --format [json|csv] --output-dir [dir]"

pending_modules_in_order:
  - "EduPredict Core Architecture, 4 Role Panels, Evaluation Engine, PDF Reports, and Production Operations/Packaging are 100% complete and verified."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Automated backup cron: python manage.py export_backup --format json --output-dir backups/ --quiet."
  - "Health endpoint is active at /health/ with live MongoDB Atlas ping."
  - "Always track .env and .agents/* in Git."
```