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
last_updated_by_agent: "Phase 20 Theme Studio & Smart Workflow Automation Team"
active_branch_merged_to_main: "feature/theme-studio-automation -> main"
project_phase: "Phase 20 Complete: Live Theme & Appearance Studio, Per-Panel Theme Isolation & Smart Workflow Automation"

completed_modules:
  - "Phase 1-19: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Actor Audit & Dynamic Thresholds, Analytics/Panel Test Splits & Coverage, Student _batch_rank Marks-Scale Fix, Admin Guard/CRUD Tests, Student Alert Extraction, Single-Query Alerts + Dynamic Excellent Threshold, Single-Query Batch Stats + Alert Target Cleanup, Scoped Batch Query & Unread Alert Targets, and Notification Student ID & Empty Batch Guard"
  - "Phase 20: Live Theme & Appearance Studio, Per-Panel Isolation & Smart Automation:"
      - "Added core/theme_services.py (204 lines, 0 comments) with 2 appearance modes, 6 header/sidebar shell themes, 13 brand accent swatches, 6 surface presets, density & sync_shell preferences, per-role/per-user scoping, merge/reset normalization, and MongoDB users.theme_prefs.<ROLE> persistence + invalidate_cache."
      - "Added panels/views_theme.py (46 lines, 0 comments) and panels:theme_preferences route at /theme/preferences/ (GET JSON, POST JSON/form + EduPredict-Theme header + safe referer redirect), wired theme_prefs & theme_catalog in core/context_processors.py (77 lines), and preserved theme_prefs in accounts/services.py (190 lines)."
      - "Added templates/components/theme_studio_modal.html (221 lines, 0 comments) and static/js/theme_studio.js (275 lines, 0 comments) with live preview, scoped localStorage ep_theme_prefs:<user_id>:<role>, debounced /theme/preferences/ persistence, Chart.js themeChanged sync, auto-submit uploads, auto-filter selects, and teacher_ingest student ID auto-fill."
      - "Updated templates/base.html (176 lines), templates/components/topbar.html (83 lines), templates/components/sidebar.html (171 lines), confirm_modal.html (61 lines), form_modal.html (21 lines), static/css/global.css (171 lines), and static/js/app.js (341 lines) for pre-paint theme hydration, dark shell chrome, drag-safe backdrop dismissal, IME guards, field-sizing, :user-invalid, and ?v=7 cache-busting."
      - "Upgraded smart defaults & automation in admin_settings.html (170 lines), admin_users.html (162 lines), admin_courses.html (154 lines), teacher_ingest.html (175 lines), teacher_dashboard.html (166 lines), teacher_students.html (140 lines), teacher_alerts.html (64 lines), and analyst_dashboard.html (273 lines); expanded panels/tests.py (281 lines) with ThemePreferencesTests."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py test analytics panels --verbosity=2: 35/35 tests PASSED (15.605s); full manage.py test --verbosity=2: 35/35 PASSED (14.851s)."
  - "node --check static/js/app.js, static/js/nav.js, static/js/charts.js, static/js/theme_studio.js: PASSED."
  - "Static audit (23 changed files): 0 comments, 0 native alert/confirm/prompt, all files within line caps (views <= 250, others <= 350); .agents/rules/edupredict-rules.md (11899 bytes); .env and 8 .agents/* files tracked."
  - "E2E Client() smoke & isolation check: HTTP 200 across /admin-panel/, /admin-panel/settings/, /admin-panel/users/, /admin-panel/courses/, /teacher-panel/, /teacher-panel/ingest/, /teacher-panel/students/, /teacher-panel/alerts/, /student-panel/, /analyst-panel/, /auth/ (and 404 check), verified Rule 20 sidebar isolation and per-role /theme/preferences/ persistence/reset."

active_routes_and_files:
  - "core/theme_services.py (204 lines), panels/views_theme.py (46 lines), static/js/theme_studio.js (275 lines), templates/components/theme_studio_modal.html (221 lines)"
  - "/theme/preferences/ -> panels:theme_preferences"
  - "/admin-panel/ -> panels:admin_dashboard, /admin-panel/users/ -> panels:admin_users, /admin-panel/courses/ -> panels:admin_courses, /admin-panel/tickets/ -> panels:admin_tickets, /admin-panel/backup/ -> panels:admin_backup_export, /admin-panel/logs/ -> panels:admin_logs, /admin-panel/settings/ -> panels:admin_settings"
  - "/support/submit/ -> panels:submit_support_ticket, /notifications/mark-read/ -> panels:mark_notifications_read"
  - "/teacher-panel/ -> panels:teacher_dashboard, /teacher-panel/students/ -> panels:teacher_students, /teacher-panel/alerts/ -> panels:teacher_alerts, /teacher-panel/ingest/ -> panels:teacher_ingest"
  - "/student-panel/ -> panels:student_dashboard, /student-panel/report/ -> panels:student_report, /student-panel/tips/ -> panels:student_tips, /student-panel/notifications/ -> panels:student_notifications"
  - "/analyst-panel/ -> panels:analyst_dashboard, /analyst-panel/accuracy/ -> panels:analyst_accuracy"

pending_modules_in_order:
  - "All Phase 1-20 features, Live Theme & Appearance Studio, per-panel isolation, and smart automation complete; ready for full-stack UAT or next user-requested feature."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```