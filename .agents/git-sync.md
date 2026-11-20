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
last_updated_by_agent: "Phase 24 Card-Grid Directories, Modalized Upload/Quick Entry & Dot-Graph KPI Cards QA Team"
active_branch_merged_to_main: "feature/phase24-cards-modals-dotkpi -> main"
project_phase: "Phase 24 Complete: Card-Grid Directories, Modalized Upload/Quick Entry & Dot-Graph KPI Cards"

completed_modules:
  - "Phase 1-23: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Live Theme & Appearance Studio, Per-Panel Theme Isolation, /profile/, Ocean Blue Default, Cloudinary Avatars, Change Password Modal, Global Loading Lock, Real-Time Notifications Feed, Admin Feedback Reply CRUD, Typewriter Page Guide Wizard Modal."
  - "Phase 24: Card-Grid User/Student/Teacher Directories + Modalized Upload/Quick Entry + Dot-Graph KPI Cards:"
      - "Directory Card Services & Views: Created panels/directory_card_services.py (162 lines) with build_admin_user_cards (self-protection guard, avatar_url, role_badge, actions) and build_teacher_student_cards (single users_col() avatar lookup + 9-col/8-col fallback_rows parser); updated panels/teacher_services.py (334 lines), panels/views_admin.py (249 lines), and panels/views_teacher.py (238 lines) to inject user_cards, student_cards, and roster_cards."
      - "Card-Grid & Modalized Upload/Quick Entry UI: Created templates/components/directory_cards.html (99 lines) supporting [data-paginated-container], [data-table-search], avatar_url/initials, status badge, 2-col meta grid, and [data-pagination-bar]; updated templates/panels/admin_users.html (169 lines), templates/panels/teacher_students.html (169 lines), templates/panels/teacher_ingest.html (176 lines, #teacher-upload-modal + openQuickEntryModal), and templates/panels/analyst_dashboard.html (264 lines, #analyst-upload-modal)."
      - "Dot-Graph KPI Cards & Modal Shell JS: Updated templates/components/metric_card.html (31 lines) with [data-dot-kpi], [data-kpi-counter], [data-dot-tooltip], and [data-dot-matrix]; updated static/css/global.css (235 lines) with .ep-dot-matrix, .ep-dot-col, .ep-dot, status color variants, @keyframes epDotPop, and prefers-reduced-motion; created static/js/dot_kpi.js (98 lines) exposing window.initDotKpiCards(); updated static/js/app.js (345 lines) with generic [data-ep-modal] handling and window.openCustomModal/closeCustomModal; bumped static assets to ?v=11 in templates/base.html (182 lines) and templates/accounts/auth.html (331 lines)."
      - "Tests: Created panels/test_phase24.py (156 lines) covering DirectoryCardServicesUnitTests and Phase24IntegrationTests."

verification_results:
  - "manage.py check: 0 issues reported (exit 0)."
  - "manage.py test analytics panels --verbosity=2: 88/88 tests PASSED (54.944s)."
  - "node --check static/js/dot_kpi.js, ui_widgets.js, page_guides.js, app.js, nav.js, charts.js, theme_studio.js, analyst_evaluation.js: all exited 0."
  - "Static audit (16 modified/created Phase 24 files): 0 comments, 0 triple-quotes, all files within line caps (views_*.py <= 250, others <= 350); .agents/rules/edupredict-rules.md (14,509 bytes < 24,000); .env and 8 .agents/* files tracked in Git."
  - "Live Django Client() smoke checks: /admin-panel/, /admin-panel/users/, /teacher-panel/, /teacher-panel/students/, /teacher-panel/ingest/, /student-panel/, and /analyst-panel/ verified."

active_routes_and_files:
  - "panels/directory_card_services.py (162 lines), panels/teacher_services.py (334 lines), panels/views_admin.py (249 lines), panels/views_teacher.py (238 lines), panels/test_phase24.py (156 lines)"
  - "templates/components/directory_cards.html (99 lines), templates/components/metric_card.html (31 lines), templates/base.html (182 lines), templates/accounts/auth.html (331 lines)"
  - "templates/panels/admin_users.html (169 lines), templates/panels/teacher_students.html (169 lines), templates/panels/teacher_ingest.html (176 lines), templates/panels/analyst_dashboard.html (264 lines)"
  - "static/css/global.css (235 lines), static/js/dot_kpi.js (98 lines), static/js/app.js (345 lines)"

pending_modules_in_order:
  - "Phase 25: Stepper Signup Wizard + Teacher Approval Guard + Student PDF Transcript"

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```