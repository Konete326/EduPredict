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
last_updated_by_agent: "Phase 25 Stepper Signup Wizard, Teacher Approval Guard & Official PDF Transcript QA Team"
active_branch_merged_to_main: "feature/phase25-stepper-approval-pdf -> main"
project_phase: "Phase 25 Complete: Stepper Signup Wizard, Teacher Approval Guard & Student PDF Transcript (Phases 1-25 Complete)"

completed_modules:
  - "Phase 1-24: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Live Theme & Appearance Studio, Per-Panel Theme Isolation, /profile/, Ocean Blue Default, Cloudinary Avatars, Change Password Modal, Global Loading Lock, Real-Time Notifications Feed, Admin Feedback Reply CRUD, Typewriter Page Guide Wizard Modal, Card-Grid User/Student/Teacher Directories, Modalized Upload/Quick Entry & Dot-Graph KPI Cards."
  - "Phase 25: Stepper Signup Wizard + Teacher Approval Guard + Student PDF Transcript:"
      - "Stepper Signup Backend & Teacher Approval Guard: Updated accounts/services.py (220 lines) with SELF_REGISTER_ROLES, approval_status in serialize_session_user, PENDING check before is_active in authenticate_user, and register_user(phone, bio) storing PENDING/is_active=False + unread ADMIN notification ('Teacher Approval Needed') for TEACHER while blocking ADMIN self-signup; updated accounts/views.py (198 lines) to read phone/bio, enforce SELF_REGISTER_ROLES, and keep PENDING teachers signed out with warning flash."
      - "Admin Approval Queue & Cards: Updated panels/admin_services.py (348 lines) with PENDING count/filter, phone/bio/approval_status, and APPROVE_USER + 'Account Approved' notification in toggle_user_status; updated panels/directory_card_services.py (172 lines) with Pending Approval warning badge, Approve primary action, and data-approval-status; updated templates/panels/admin_users.html (176 lines) with Pending Approval filter pill and openToggleUserModal() approval wording."
      - "3-Step Auth Stepper UI: Updated templates/accounts/auth.html (313 lines) with [data-auth-stepper] 3-step wizard (Account, Profile, Security), #teacher-approval-notice, optional phone/bio, #wizard-review-summary, and ?v=12 assets; created static/js/auth_wizard.js (162 lines) with linear step validation, teacher notice/batch autofill, IME-guarded Enter navigation, and Caps Lock/password toggles; updated static/css/global.css (275 lines) with .ep-step-indicator and .ep-step-line styles."
      - "Official Student PDF Transcript & Cache-Bust: Updated panels/pdf_services.py (243 lines) with _letter_grade(), EARNED CREDITS, CLASS STANDING, OFFICIAL ACADEMIC TRANSCRIPT & REPORT CARD heading, and 7-col GRADE table; updated templates/panels/student_dashboard.html (175 lines) and templates/panels/student_report.html (80 lines) with primary Download PDF Transcript + data-no-loading='true'; bumped ?v=12 in templates/base.html (182 lines); created panels/test_phase25.py (142 lines)."

verification_results:
  - "manage.py check: 0 issues reported (exit 0)."
  - "manage.py test analytics panels --verbosity=2: 93/93 tests PASSED (106.643s)."
  - "node --check static/js/auth_wizard.js, dot_kpi.js, ui_widgets.js, page_guides.js, app.js, nav.js, charts.js, theme_studio.js, analyst_evaluation.js: all 9 exited 0."
  - "Static audit (13 modified/created Phase 25 files): 0 comments, 0 triple-quotes, all files within line caps (views_*.py <= 250, others <= 350); .agents/rules/edupredict-rules.md (14,509 bytes < 24,000); .env and 8 .agents/* files tracked in Git."
  - "Live Django Client() smoke checks: /auth/ (200), /admin-panel/users/?role=PENDING (200), /student-panel/ (200), /student-panel/report/ (200), and /student-panel/report/download-pdf/ (200, application/pdf, %PDF-) verified."

active_routes_and_files:
  - "accounts/services.py (220 lines), accounts/views.py (198 lines), panels/admin_services.py (348 lines), panels/directory_card_services.py (172 lines), panels/pdf_services.py (243 lines), panels/test_phase25.py (142 lines)"
  - "templates/accounts/auth.html (313 lines), templates/base.html (182 lines), templates/panels/admin_users.html (176 lines), templates/panels/student_dashboard.html (175 lines), templates/panels/student_report.html (80 lines)"
  - "static/js/auth_wizard.js (162 lines), static/css/global.css (275 lines)"

pending_modules_in_order:
  - "All planned Phases 1-25 Complete."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```