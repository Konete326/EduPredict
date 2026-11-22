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
last_updated_by_agent: "Phase 74 Notifications History, Glassmorphism Profile, Tabbed Settings, Drawer Blur & Academic Widgets Team"
active_branch_merged_to_main: "feature/phase74-profile-notifs-ux-charts -> main"
project_phase: "Phase 74 Complete: Notifications History, Glassmorphism Portfolio Profile, Tabbed Portal Settings, Full-Viewport Drawer Blur, Compact Table Actions & Zero-Glow Academic Widgets"

completed_modules:
  - "Phase 1-73: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline & Leakage-Free Evaluation, Admin Activity Logs & Portal Settings, Theme Studio, My Profile, Cloudinary Avatars, Real-Time Notifications Feed, Admin Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval/Reject Guard, Official PDF & HTML Branding Sync, Cgroup Health Telemetry, Rate-Limit Headers, Encrypted/Verified Backups, Visual Polish (60/26A), Image Cropper & Lightbox (61/26B), Table-First Directories & Student 360° Drawer (62/26C), Hyper-Automation, Live LMS Stream Simulator & Aptech Pack (63/26D), Live Stream/KPI/PDF/Card-ID Sync (64-72), and Hirael Login-03 Split-Screen Auth Showcase (73)."
  - "Phase 74: Notifications History, Glassmorphism Profile, Tabbed Settings, Drawer Blur & Zero-Glow Academic Widgets:"
      - "panels/notification_services.py (274/350 lines, 0 comments), panels/views_notifications.py (81/250 lines, 0 comments), panels/urls.py (34/350 lines, 0 comments), templates/panels/notifications_history.html (153/350 lines, 0 comments): added /notifications/ (panels:notifications_history) with ALL/UNREAD/READ/REPLIES tabs, normalized support ticket reply merging without duplicate ticket_ids, POST mark_one (ObjectId + ownership check) & mark_all, and _resolve_notification_target() target_url in /notifications/feed/."
      - "templates/components/topbar.html (107/350 lines), templates/components/sidebar.html (199/350 lines), static/js/ui_widgets.js (345/350 lines), static/js/page_guides.js (267/350 lines), static/js/app.js (348/350 lines): clickable <a data-notif-item> dropdown alerts, #view-all-notifications-link, sidebar Alerts History link, #topbar-quick-search + openCommandSearchModal(initialQuery) fallback, inline-flex gap-2 spinner lock wrapper, and syncBodyScrollLock() ep-overlay-blur for modals and drawers."
      - "templates/panels/user_profile.html (234/350 lines), templates/panels/admin_settings.html (202/350 lines), templates/panels/admin_tickets.html (199/350 lines), templates/components/data_table.html (134/350 lines), panels/admin_services.py (349/350 lines): Glassmorphism Portfolio /profile/ with modalized Edit/Avatar/FAQ/Change-Password, 3-tab 17-inch viewport-fit /admin-panel/settings/, flex-nowrap single-row table actions, compact ticket labels, and drawer quick actions."
      - "static/css/global.css (265/350 lines), static/js/image_cropper.js (279/350 lines), static/js/directory_ui.js (336/350 lines), static/js/academic_widgets.js (245/350 lines), templates/base.html (189/350 lines), templates/panels/analyst_accuracy.html (207/350 lines), templates/panels/student_tips.html (149/350 lines), .agents/design.md (203 lines), .agents/rules/edupredict-rules.md (16,713 bytes): removed will-change: opacity, transform from .spa-page-enter, added document.body drawer portaling + ep-overlay-blur, and added zero-glow (shadowBlur = 0) Catmull-Rom Contour Strata, Interactive 3-Ring Orbit Goals, and prefers-reduced-motion Marquee widgets."
      - "panels/test_phase74.py (364/400 lines, 0 comments): added 5 comprehensive Django + Node VM tests covering /notifications/, /profile/, /admin-panel/settings/, /admin-panel/tickets/, drawer blur/portaling, topbar search, spinner gap, and academic_widgets.js / ui_widgets.js."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all 12 JS scripts (academic_widgets.js, analyst_evaluation.js, app.js, auth_wizard.js, charts.js, directory_ui.js, dot_kpi.js, image_cropper.js, nav.js, page_guides.js, theme_studio.js, ui_widgets.js) exited 0."
  - "manage.py test --verbosity=2: Ran 127 tests in 135.521s (OK)."
  - "manage.py verify_uat: UAT Results: 7/7 passed in 17.28s - System 100% Operational."
  - "Static audit: all 22 Phase 74 files within line caps (views_notifications.py 81/250, test_phase74.py 364/400, all others <= 349/350), 0 comments/docstrings; .agents/rules/edupredict-rules.md 16,713 bytes (< 24,000); .env and .agents/* tracked in Git."

active_routes_and_files:
  - "/notifications/ (panels:notifications_history), /notifications/feed/, /profile/, /admin-panel/settings/, /admin-panel/tickets/, /analyst-panel/accuracy/, /student-panel/tips/, panels/test_phase74.py, .agents/git-sync.md"

pending_modules_in_order:
  - "All Planned Phases (Phases 1-74) Complete — Ready for Final Aptech Viva & Production Deployment."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env, .agents/*, and docs/aptech_submission/* in Git."
```