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
last_updated_by_agent: "Phase 62 (26C) Table-First Directories, Student 360° Drawer & Teacher Reject Team"
active_branch_merged_to_main: "feature/phase62-table-first-360-reject -> main"
project_phase: "Phase 62 (26C) Complete: Table-First Directories, [Table | Cards] Toggle, 1-Click Copy ID, Student 360° Drawer & Teacher Reject-with-Reason"

completed_modules:
  - "Phase 1-61: Core Shell, Auth/RBAC, 4 Role Panels, Leakage-Free ML, Theme Studio, My Profile, Cloudinary Avatars, Notifications Feed, Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval Guard, Official PDF Transcript, Cgroup Health, Rate-Limit Headers, Encrypted/Verified Backups, Visual Polish (Phase 60 / 26A), and Global Image Cropper & Ticket Lightbox (Phase 61 / 26B)."
  - "Phase 62 (26C): Table-First Directories, Student 360° Drawer & Teacher Reject-with-Reason:"
      - "Backend Reject & Student 360° API: Created panels/phase62_services.py (155 lines) with reject_teacher_account (reason validation, self-action guard, approval_status=REJECTED, is_active=False, REJECT_USER audit log, DANGER APPROVAL notification, cache invalidation) and get_student_360_summary (records, prediction, user, last 5 alerts, risk_status, 2-4 risk_reasons, courses, recent_alerts, edit_attrs). Updated accounts/services.py (224 lines) to block REJECTED logins with the Admin reason; updated panels/admin_services.py (374 lines) & panels/views_admin.py (244 lines) for action='reject' and REJECTED filter/counts; updated panels/directory_card_services.py (187 lines) with Rejected badge, Reject action on pending teachers, and student_360_id/attendance/marks/GPA metadata; added student_360_summary_view at GET /students/<student_id>/summary/ (panels:student_360_summary) in panels/views_notifications.py (29 lines) & panels/urls.py (33 lines)."
      - "Table-First Directories, 360° Drawer & Reject UI: Updated templates/components/directory_cards.html (184 lines) with default 6-column compact table ([data-directory-table-view]), [Table | Cards] toggle ([data-directory-view-toggle]), 1-click Copy ID/email ([data-copy-text]), inline attendance bars, and synced cards grid ([data-directory-cards-view]); created templates/components/student_360_drawer.html (96 lines) & static/js/directory_ui.js (253 lines) with SVG attendance ring, risk reasons, courses, alerts, footer modals, localStorage view persistence (ep_dir_view:<id>), and #analyst-predictions-table Student ID links; updated static/css/global.css (313 lines), templates/panels/admin_users.html (196 lines, Rejected pill + openRejectUserModal), templates/panels/teacher_students.html (169 lines), templates/base.html (188 lines), and templates/accounts/auth.html (313 lines, ?v=15)."

verification_results:
  - "manage.py check: 0 issues reported (exit 0)."
  - "manage.py test: 108/108 tests PASSED (63.624s)."
  - "manage.py verify_uat: 7/7 UAT steps PASSED (18.47s)."
  - "node --check: all 11 JS scripts (analyst_evaluation.js, app.js, auth_wizard.js, charts.js, directory_ui.js, dot_kpi.js, image_cropper.js, nav.js, page_guides.js, theme_studio.js, ui_widgets.js) exited 0."
  - "Static audit (16 modified/created files): 0 comments, views <= 244 lines, all other files <= 374 lines; .agents/rules/edupredict-rules.md 15,978 bytes (< 24,000)."

active_routes_and_files:
  - "panels/phase62_services.py (155 lines), accounts/services.py (224 lines), panels/admin_services.py (374 lines), panels/views_admin.py (244 lines)"
  - "panels/directory_card_services.py (187 lines), panels/views_notifications.py (29 lines), panels/urls.py (33 lines)"
  - "templates/components/directory_cards.html (184 lines), templates/components/student_360_drawer.html (96 lines), static/js/directory_ui.js (253 lines)"
  - "static/css/global.css (313 lines), templates/panels/admin_users.html (196 lines), templates/panels/teacher_students.html (169 lines)"
  - "templates/base.html (188 lines), templates/accounts/auth.html (313 lines), panels/test_phase25.py (259 lines)"

pending_modules_in_order:
  - "Phase 63 (26D): Hyper-Automation (Zero-Click Auto-ML + Auto-Alert Escalation, Smart CSV Auto-Mapper + Preview, 1-Click Notify All High-Risk Students, visibilitychange Sync, Dynamic Institution/Term PDF Branding, Live LMS Stream Simulator) & Aptech Final Submission Pack"

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```