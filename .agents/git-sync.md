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
last_updated_by_agent: "Phase 22 Ocean Blue Default, Cloudinary Avatars & UX Polish QA Team"
active_branch_merged_to_main: "feature/phase22-ux-cloudinary-blue -> main"
project_phase: "Phase 22 Complete: Ocean Blue Default Theme, Cloudinary Avatars, Change Password Modal, Global Loading Lock, Top SPA Progress Bar, Responsive Table Wrap, Gradient Uploader & FAQ-Pro"

completed_modules:
  - "Phase 1-21: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Actor Audit & Dynamic Thresholds, Live Theme & Appearance Studio, Per-Panel Theme Isolation, /profile/ & Cancelable Auto-Upload."
  - "Phase 22: Ocean Blue Default, Cloudinary Avatars & UX Polish:"
      - "Ocean Blue Default & Clean Shell: Switched default theme to shell_theme='blue' and accent='ocean' (#2563eb / #3b82f6) across core/theme_services.py (333 lines), static/css/global.css (217 lines), static/js/theme_studio.js (300 lines), static/js/charts.js (264 lines), templates/components/theme_studio_modal.html (221 lines), templates/base.html (179 lines), and templates/accounts/auth.html (331 lines); added inline Ocean Blue SVG favicon and removed 'Atlas Ready' pill from templates/components/topbar.html (75 lines)."
      - "Cloudinary Avatar Media Pipeline: Added core/cloudinary_services.py (68 lines) with is_cloudinary_configured() and 320x320 face-cropped upload_user_avatar() (<= 5 MB), tracked CLOUDINARY_* keys in .env / .env.example, froze cloudinary== in requirements.txt, and wired avatar_url into accounts/services.py (193 lines), panels/admin_services.py (342 lines), topbar.html, and sidebar.html (196 lines)."
      - "Change Password Modal & Profile Widgets: Updated panels/views_theme.py (139 lines) and core/theme_services.py for action='change_password', 'upload_avatar', and 'remove_avatar'; updated templates/panels/user_profile.html (165 lines) with openChangePasswordModal() (no inline password inputs), templates/components/gradient_file_uploader.html (32 lines), and templates/components/faq_pro.html (34 lines)."
      - "Global Loading Lock, SPA Progress & Zero Horizontal Scrollbar: Added static/js/ui_widgets.js (163 lines) with window.EduPredictProgress (#ep-top-progress), double-submit guard ('Processing...' + aria-busy + 12s/pageshow reset), FaqPro search highlight, and GradientUploader; wired into static/js/nav.js (249 lines) and static/js/app.js (341 lines); enforced overflow-x: clip in global.css and break-words max-w-[18rem] in templates/components/data_table.html (134 lines)."
      - "Docs & Tests: Updated .agents/trd.md, .agents/design.md, .agents/project-rules.md, and .agents/rules/edupredict-rules.md (14,509 bytes < 24,000); expanded panels/tests.py (345 lines)."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py test analytics panels --verbosity=2: 38/38 tests PASSED (11.602s)."
  - "node --check static/js/ui_widgets.js, app.js, nav.js, charts.js, theme_studio.js: all exited 0."
  - "Static audit (21 files): 0 comments, 0 triple-quotes, all files within line caps (views <= 250, others <= 350); .agents/rules/edupredict-rules.md (14,509 bytes < 24,000); .env and 8 .agents/* files tracked."
  - "Live Django Client() smoke checks: is_cloudinary_configured()=True; GET /theme/preferences/ returns shell_theme='blue', accent='ocean', accent_primary='#2563eb'; /admin-panel/ & /auth/ include SVG favicon; /admin-panel/ excludes 'Atlas Ready' and includes #ep-top-progress; /profile/ includes openChangePasswordModal(), data-gradient-uploader, and data-faq-pro without inline new_password; data_table.html includes break-words."

active_routes_and_files:
  - "core/cloudinary_services.py (68 lines), core/theme_services.py (333 lines), panels/views_theme.py (139 lines), static/js/ui_widgets.js (163 lines), static/css/global.css (217 lines)"
  - "templates/components/gradient_file_uploader.html (32 lines), templates/components/faq_pro.html (34 lines), templates/panels/user_profile.html (165 lines)"
  - "/profile/ -> panels:user_profile, /theme/preferences/ -> panels:theme_preferences"

pending_modules_in_order:
  - "Phase 23: Real-Time Notifications + Admin Feedback Reply CRUD + Typewriter Page Guide Wizard Modal"
  - "Phase 24: Card-Grid User/Student/Teacher Directories + Modalized Upload/Quick Entry + Dot-Graph KPI Cards"
  - "Phase 25: Stepper Signup Wizard + Teacher Approval Guard + Student PDF Transcript"

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```