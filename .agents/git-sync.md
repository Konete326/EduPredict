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
last_updated_by_agent: "Phase 16 Student Alert N+1 Fix & Dynamic Excellent Threshold Team"
active_branch_merged_to_main: "feature/alert-n1-fix-and-excellent-threshold -> main"
project_phase: "Phase 16 Complete: Single-Query Student Alerts & Dynamic Excellent Attendance Threshold"

completed_modules:
  - "Phase 1-15: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Actor Audit & Dynamic Thresholds, Analytics/Panel Test Splits & Coverage, Student _batch_rank Marks-Scale Fix, Admin Guard/CRUD Tests, and Student Alert Extraction"
  - "Phase 16: Single-Query Student Alerts & Dynamic Excellent Attendance Threshold:"
      - "Updated panels/student_alert_services.py (76 lines, 0 AST comments) with _format_alert_doc(doc), single-query _load_recent_alerts(student_id, user_id, role, limit=5) eliminating N+1 find_one calls, and _load_alert_detail delegating to _format_alert_doc."
      - "Updated panels/student_services.py (320 lines, 0 AST comments) so _build_tips and _load_student_overview align the 'Excellent' attendance tip/status threshold (min(100.0, max(90.0, float(min_att) + 10.0)) and excellent_att = min(100.0, max(85.0, min_att + 5.0))) strictly above min_attendance_pct."
      - "Updated panels/test_teacher_student.py (252 lines, 0 AST comments) with test_single_query_recent_alerts_and_dynamic_excellent_threshold verifying 1 find() / 0 find_one() calls in _load_recent_alerts and Needs Help vs Excellent classification under min_attendance_pct=90."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py test analytics panels --verbosity=2 (and full manage.py test): 33/33 tests PASSED."
  - "node --check static/js/app.js, static/js/nav.js, static/js/charts.js: PASSED."
  - "Zero comments and line-count limits verified: panels/student_alert_services.py (76/78), panels/student_services.py (320/322), panels/test_teacher_student.py (252/255); .agents/rules/edupredict-rules.md (11899 bytes); .env tracked in Git."

active_routes_and_files:
  - "panels/student_alert_services.py (76 lines), panels/student_services.py (320 lines), panels/test_teacher_student.py (252 lines)"
  - "/admin-panel/ -> panels:admin_dashboard, /admin-panel/users/ -> panels:admin_users, /admin-panel/courses/ -> panels:admin_courses, /admin-panel/tickets/ -> panels:admin_tickets, /admin-panel/backup/ -> panels:admin_backup_export, /admin-panel/logs/ -> panels:admin_logs, /admin-panel/settings/ -> panels:admin_settings"
  - "/support/submit/ -> panels:submit_support_ticket"
  - "/teacher-panel/ -> panels:teacher_dashboard, /teacher-panel/students/ -> panels:teacher_students, /teacher-panel/alerts/ -> panels:teacher_alerts, /teacher-panel/ingest/ -> panels:teacher_ingest"
  - "/student-panel/ -> panels:student_dashboard, /student-panel/report/ -> panels:student_report, /student-panel/tips/ -> panels:student_tips, /student-panel/notifications/ -> panels:student_notifications"
  - "/analyst-panel/ -> panels:analyst_dashboard, /analyst-panel/accuracy/ -> panels:analyst_accuracy"

pending_modules_in_order:
  - "All Phase 1-16 implementation, optimization, modularization, and test coverage suites complete; ready for full-stack UAT or next user-requested feature."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys and invalidate_cache on mutations."
  - "Always track .env and .agents/* in Git."
```