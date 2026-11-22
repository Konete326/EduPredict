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
last_updated_by_agent: "Phase 73 Hirael Login-03 Auth Showcase, Floating SVG Paths & Password Strength Meter Team"
active_branch_merged_to_main: "feature/phase73-login03-auth-showcase -> main"
project_phase: "Phase 73 Complete: Hirael Login-03 Split-Screen Auth Showcase, Floating SVG Paths & Password Strength Meter"

completed_modules:
  - "Phase 1-72: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline & Leakage-Free Evaluation, Admin Activity Logs & Portal Settings, Theme Studio, My Profile, Cloudinary Avatars, Real-Time Notifications Feed, Admin Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval/Reject Guard, Official PDF & HTML Branding Sync, Cgroup Health Telemetry, Rate-Limit Headers, Encrypted/Verified Backups, Visual Polish (60/26A), Image Cropper & Lightbox (61/26B), Table-First Directories & Student 360° Drawer (62/26C), Hyper-Automation, Live LMS Stream Simulator & Aptech Pack (63/26D), Student Report HTML Branding Sync & PEP 8 PDF Imports (64), Global Cached Portal Branding Context & Live Stream Chart Auto-Refresh (65), Live Stream Scatter/KPI Sync & Core Branding Helper Refactor (66), Live KPI data-kpi-value Sync, SPA Init Hook & PDF Branding Delegation (67), SPA reinitEduPredictUI Stream Hook & Live Predictions Table Refresh (68), Mobile Stream Cards Sync, Pagination Search Refresh & v17 Cache-Bust (69), Mobile Card ID-Matching & Unified v17 Static Asset Sync (70), Central STATIC_ASSET_VERSION & Mobile data-card-id Attribute (71), Desktop Table Row data-row-id & Mobile Card Student 360° Trigger (72)."
  - "Phase 73: Hirael Login-03 Split-Screen Auth Showcase, Floating SVG Paths & Password Strength Meter:"
      - "templates/accounts/auth.html (340 lines, 0 comments): upgraded to Login-03 split-screen showcase (data-slot='login', 'login-aside', 'login-main', 'login-panel', 'login-header'), animated #ep-floating-paths container, 3-bullet restraint cards, editorial blockquote, 4-bar #reg-password-strength meter, calm data-pending-approval-card, and ?v=17 asset query strings."
      - "static/js/auth_wizard.js (235 lines, 0 comments): added initFloatingPaths() generating 72 animated SVG <path> elements inside #ep-floating-paths and window.evaluatePasswordStrength() driving the 4 [data-strength-bar] segments + #reg-password-strength-label across empty/short/weak/fair/good/strong states."
      - "static/css/global.css (339 lines, 0 comments): added CSS variable-backed auth showcase animations and floating-path styling."
      - "accounts/views.py (199 lines, 0 comments): added pending_teacher_approval=False to _render_auth() context and passed pending_teacher_approval=True on PENDING teacher registration in _handle_register()."
      - "panels/test_phase73.py (136 lines, 0 comments): added Phase73AuthShowcaseTests verifying Login-03 slots, pending teacher approval status card, and Node VM execution of initFloatingPaths() (72 SVG paths) + evaluatePasswordStrength()."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all 11 JS scripts (analyst_evaluation.js, app.js, auth_wizard.js, charts.js, directory_ui.js, dot_kpi.js, image_cropper.js, nav.js, page_guides.js, theme_studio.js, ui_widgets.js) exited 0."
  - "manage.py test --verbosity=2: Ran 122 tests in 85.669s (OK)."
  - "manage.py verify_uat: UAT Results: 7/7 passed in 9.82s - System 100% Operational."
  - "Static audit: templates/accounts/auth.html (340/350), static/js/auth_wizard.js (235/350), static/css/global.css (339/350), accounts/views.py (199/250), panels/test_phase73.py (136/350), 0 comments/docstrings; .agents/rules/edupredict-rules.md 15,978 bytes (< 24,000); .env and .agents/* tracked in Git."

active_routes_and_files:
  - "templates/accounts/auth.html (340 lines), static/js/auth_wizard.js (235 lines), static/css/global.css (339 lines), accounts/views.py (199 lines), panels/test_phase73.py (136 lines), .agents/git-sync.md"

pending_modules_in_order:
  - "All Planned Phases (Phases 1-73) Complete — Ready for Final Aptech Viva & Production Deployment."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env, .agents/*, and docs/aptech_submission/* in Git."
```