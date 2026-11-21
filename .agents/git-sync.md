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
last_updated_by_agent: "Phase 60 (26A) Enterprise Visual Polish & Clean Shell Team"
active_branch_merged_to_main: "feature/phase60-visual-polish-shell -> main"
project_phase: "Phase 60 (26A) Complete: Visual Polish, Clean Clickable KPIs, Chart.js Defaults & Scroll-Aware Shell"

completed_modules:
  - "Phase 1-59: Core Shell, Auth/RBAC, 4 Role Panels, Leakage-Free ML, Theme Studio, My Profile, Cloudinary Avatars, Notifications Feed, Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval Guard, Official PDF Transcript, Cgroup Health, Rate-Limit Headers, and Encrypted/Verified Backups."
  - "Phase 60 (26A): Visual Polish & Clean Shell:"
      - "CSS Depth & Tokens: Updated static/css/global.css (282 lines, 0 comments) with accent-color theming, translucent dark hairline borders (--border-subtle: rgba(255,255,255,0.08)), scroll-aware topbar backdrop blur (header.ep-topbar.is-scrolled), and .ep-nav-link.is-active 3px Ocean Blue left bar; removed synthetic dot-matrix CSS rules."
      - "Clean Clickable KPIs: Simplified templates/components/metric_card.html (22 lines) to 3 clean rows (label + 14px muted icon, tabular-nums value, 6px status dot badge); updated static/js/dot_kpi.js (79 lines) with clickable/keyboard table filtering via input[data-table-search]."
      - "Chart.js 6 Global Defaults: Updated static/js/charts.js (297 lines) with vertical grid hiding + light dashed horizontal grids, rounded bars (borderRadius: 6, maxBarThickness: 36), 72% cutout doughnuts + center total plugin, dark slate tooltips, top-right circle legends, and live themeChanged sync."
      - "Scroll-Aware 4-Item Topbar, Ctrl+K Search, Instant Help & Slim Sidebar: Updated templates/components/topbar.html (104 lines) with Breadcrumb, Search Ctrl+K trigger, instant 0ms #instant-help-popover (3 bullets + 2 FAQs), Notification Bell, and Light/Dark + Profile pill; updated templates/components/page_guide_modal.html (55 lines) & static/js/page_guides.js (262 lines) with #command-search-modal (Ctrl+K) and 0ms guide text; updated templates/components/sidebar.html (195 lines) & static/js/nav.js (249 lines) with 3px .is-active highlight and Admin-only Theme Studio; bumped ?v=13 in base.html & auth.html."

verification_results:
  - "manage.py check: 0 issues reported (exit 0)."
  - "manage.py test: 103/103 tests PASSED (41.861s)."
  - "manage.py verify_uat: 7/7 UAT steps PASSED (10.00s)."
  - "node --check: all 9 JS scripts (analyst_evaluation.js, app.js, auth_wizard.js, charts.js, dot_kpi.js, nav.js, page_guides.js, theme_studio.js, ui_widgets.js) exited 0."
  - "Static audit (14 modified files): 0 comments, all files <= 345 lines; .agents/rules/edupredict-rules.md 15,978 bytes (< 24,000)."

active_routes_and_files:
  - "static/css/global.css (282 lines), static/js/charts.js (297 lines), static/js/dot_kpi.js (79 lines), static/js/page_guides.js (262 lines), static/js/nav.js (249 lines), static/js/app.js (345 lines)"
  - "templates/components/metric_card.html (22 lines), templates/components/topbar.html (104 lines), templates/components/sidebar.html (195 lines), templates/components/page_guide_modal.html (55 lines), templates/base.html (182 lines), templates/accounts/auth.html (313 lines)"
  - "panels/test_phase24.py (181 lines), panels/test_phase25.py (142 lines)"

pending_modules_in_order:
  - "Phase 61 (26B): Global Image Cropper (Cropper.js CDN + Ctrl+V Screenshot Paste + Avatar 1:1 Crop & Old Cloudinary Delete + Attachment Chips) & Admin Ticket Detail Drawer + Full-Screen Lightbox"
  - "Phase 62 (26C): Table-First Directories + [Table | Cards] Toggle + 1-Click Copy ID + Student 360 Slide-Over Drawer + Teacher Reject-with-Reason Workflow"
  - "Phase 63 (26D): Hyper-Automation (Zero-Click Auto-ML + Auto-Alert Escalation, Smart CSV Auto-Mapper + Preview, 1-Click Notify All High-Risk Students, visibilitychange Sync, Dynamic Institution/Term PDF Branding, Live LMS Stream Simulator) & Aptech Final Submission Pack"

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```