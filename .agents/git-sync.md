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
last_updated_by_agent: "Phase 21 Profile, Organized Sidebar & UX Automation QA Team"
active_branch_merged_to_main: "feature/profile-ux-automation -> main"
project_phase: "Phase 21 Complete: My Profile (/profile/), Organized Sidebar, Topbar Deduplication, Universal Password Toggles, Admin Self-Lock & 1.2s Cancelable Auto-Upload"

completed_modules:
  - "Phase 1-20: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Actor Audit & Dynamic Thresholds, Live Theme & Appearance Studio, Per-Panel Theme Isolation & Smart Defaults."
  - "Phase 21: Profile, Organized Sidebar, Password Toggles & Cancelable Auto-Upload:"
      - "Added /profile/ (panels:user_profile) across all 4 roles: update_user_profile_data in core/theme_services.py (275 lines), user_profile_view in panels/views_theme.py (97 lines), panels/urls.py (29 lines), and templates/panels/user_profile.html (160 lines) with protected read-only role, optional Department/Batch/Phone/Bio, optional password update, and student_records full_name sync."
      - "Added sync_theme_prefs_on_login in core/theme_services.py and wired in accounts/views.py (179 lines) + accounts/services.py (192 lines) to hydrate saved DB theme_prefs and merge guest PORTAL customization on login/register."
      - "Organized templates/components/sidebar.html (196 lines) with Admin Core (admin) + Support & Logs (admin_ops), preserved teacher/student/analyst isolation, added collapsible Settings & Theme dropdown (My Profile, ADMIN-only Portal Settings, Theme & Colors) for every active role, and removed duplicate footer Theme Studio button."
      - "Deduplicated templates/components/topbar.html (83 lines) by removing #theme-studio-open-btn and adding a My Profile pill; upgraded mobile card-lists in templates/components/data_table.html (134 lines) and sm:hidden Confusion Matrix cards in templates/panels/analyst_evaluation_section.html (201 lines); bumped ?v=8 in templates/base.html (176 lines) and templates/accounts/auth.html (330 lines)."
      - "Added universal [data-password-toggle] Show/Hide eye buttons in static/js/app.js (341 lines), user_profile.html, and auth.html (#reg-confirm-password + guest PORTAL pre-paint hydration); enforced 1.2s cancelable auto-upload toast grace window in static/js/theme_studio.js (300 lines); added data-is-self='true' self-edit role lock in panels/admin_services.py (342 lines) and templates/panels/admin_users.html (169 lines)."
      - "Updated .agents/prd.md, .agents/trd.md, .agents/design.md, .agents/project-rules.md, and .agents/rules/edupredict-rules.md (13,016 bytes < 24,000); expanded panels/tests.py (334 lines)."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py test analytics panels --verbosity=2: 37/37 tests PASSED (19.112s); full manage.py test --verbosity=2: 37/37 PASSED (19.955s)."
  - "node --check static/js/app.js, static/js/nav.js, static/js/charts.js, static/js/theme_studio.js: all exited 0."
  - "Static audit (20 files): 0 comments, 0 triple-quotes, all files within line caps (views <= 250, others <= 350); .agents/rules/edupredict-rules.md (13,016 bytes < 24,000); .env and 8 .agents/* files tracked."
  - "Live MongoDB Atlas Django Client() smoke checks: HTTP 200 on /auth/, /profile/ (GET & POST with role/is_active preservation + password hash check), /admin-panel/users/ (with data-is-self='true' & mobile cards), /teacher-panel/ingest/, /student-panel/, /analyst-panel/, and /theme/preferences/ (GET/POST/reset); verified Rule 20 sidebar isolation & zero duplicate theme buttons across all 4 roles."

active_routes_and_files:
  - "core/theme_services.py (275 lines), panels/views_theme.py (97 lines), templates/panels/user_profile.html (160 lines), static/js/theme_studio.js (300 lines), static/js/app.js (341 lines)"
  - "/profile/ -> panels:user_profile, /theme/preferences/ -> panels:theme_preferences"
  - "/auth/ -> accounts:auth_view, /auth/logout/ -> accounts:logout_view"
  - "/admin-panel/ -> panels:admin_dashboard, /admin-panel/users/ -> panels:admin_users, /admin-panel/courses/ -> panels:admin_courses, /admin-panel/tickets/ -> panels:admin_tickets, /admin-panel/logs/ -> panels:admin_logs, /admin-panel/settings/ -> panels:admin_settings, /admin-panel/backup/ -> panels:admin_backup_export"
  - "/support/submit/ -> panels:submit_support_ticket, /notifications/mark-read/ -> panels:mark_notifications_read"
  - "/teacher-panel/ -> panels:teacher_dashboard, /teacher-panel/students/ -> panels:teacher_students, /teacher-panel/ingest/ -> panels:teacher_ingest, /teacher-panel/alerts/ -> panels:teacher_alerts"
  - "/student-panel/ -> panels:student_dashboard, /student-panel/report/ -> panels:student_report, /student-panel/report/download/ -> panels:student_report_download, /student-panel/tips/ -> panels:student_tips, /student-panel/notifications/ -> panels:student_notifications"
  - "/analyst-panel/ -> panels:analyst_dashboard, /analyst-panel/accuracy/ -> panels:analyst_accuracy, /analyst-panel/upload/ -> analytics:upload_dataset, /analyst-panel/run-ml/ -> analytics:run_predictions, /analyst-panel/evaluation/ -> analytics:model_evaluation"

pending_modules_in_order:
  - "Core Phases 1-21 complete; optional next phases: Live End-to-End Browser UAT, PDF Report Cards/Transcripts, and Production Deployment & CI/CD Polish."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```