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
last_updated_by_agent: "EduPredict Core Notification & Alert Team"
active_branch_merged_to_main: "feature/topbar-student-notifs-and-clean-alert-targets -> main"
project_phase: "Phase 23 Complete: Topbar Bell Student ID Query & Clean Alert Target Builders"

completed_modules:
  - "Phase 1-22: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Actor Audit & Dynamic Thresholds, Live Theme & Appearance Studio, Per-Panel Theme Isolation, My Profile, Password Toggles, 1.2s Auto-Upload, and PDF Report Cards & Transcripts."
  - "Phase 23: Topbar Bell Student ID Query & Clean Alert Target Builders:"
      - "Updated core/context_processors.py (74 lines, 0 comments) so _build_notification_query and _fetch_unread_notifications accept and include student_id alongside user_id and active_role, partitioning unread cache by notifs:{user_id}:{student_id}:{role_key}."
      - "Updated panels/student_alert_services.py (69 lines, 0 comments) so _alert_targets uses dict.fromkeys to safely omit empty target_user_id entries when student_id or user_id is empty."
      - "Updated panels/test_teacher_student.py (294 lines, 0 comments) with unit tests for clean alert targets without empty-string user IDs, topbar notification query construction with/without student_id, and unread notification retrieval including student_id."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py test: 51/51 tests PASSED in 7.5s."
  - "node --check static/js/app.js, static/js/nav.js, static/js/charts.js, static/js/theme_studio.js: all PASSED."
  - "Zero comments audit: 0 comments across all modified files."
  - "Line caps: All files strictly within limits (context_processors: 74, student_alert_services: 69, test_teacher_student: 294)."
  - ".env tracked in Git: verified via git ls-files .env."

active_routes_and_files:
  - "core/context_processors.py (74 lines), panels/student_alert_services.py (69 lines), panels/test_teacher_student.py (294 lines)"
  - "/student-panel/notifications/ -> panels:student_notifications"
  - "/admin-panel/notifications/mark-read/ -> panels:mark_notifications_read"

pending_modules_in_order:
  - "Phase 24: Live End-to-End Browser UAT & MongoDB Atlas Integration Verification."
  - "Phase 25: Production Deployment & CI/CD Pipeline Polish."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "ReportLab 5.1 is pinned in requirements.txt. Keep PDF generators in panels/pdf_services.py."
  - "Always track .env and .agents/* in Git."
```