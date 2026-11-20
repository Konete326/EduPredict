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
last_updated_by_agent: "Phase 23 Real-Time Notifications, Feedback Reply CRUD & Typewriter Page Guide QA Team"
active_branch_merged_to_main: "feature/phase23-realtime-notifs-guide -> main"
project_phase: "Phase 23 Complete: Real-Time Notifications Feed, Admin Feedback Reply CRUD & Typewriter Page Guide Wizard Modal"

completed_modules:
  - "Phase 1-22: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Live Theme & Appearance Studio, Per-Panel Theme Isolation, /profile/, Ocean Blue Default, Cloudinary Avatars, Change Password Modal, Global Loading Lock, SPA Progress & Responsive Table Wrap."
  - "Phase 23: Real-Time Notifications, Admin Feedback Reply CRUD & Typewriter Page Guide Wizard:"
      - "Real-Time Notification Feed: Created panels/notification_services.py (134 lines) and panels/views_notifications.py (15 lines) exposing GET /notifications/feed/ (panels:notifications_feed) with 10s TTL caching; updated core/context_processors.py (76 lines) and templates/components/topbar.html (89 lines) to surface feedback_text + reply_text; wired idempotent 15s visibility-gated polling + toast alerts in static/js/ui_widgets.js (248 lines)."
      - "Admin Feedback Reply CRUD: Updated panels/admin_services.py (349 lines) and panels/views_admin.py (247 lines) to support reply_ticket (saving admin_reply, optional status resolve, and targeted FEEDBACK_REPLY user notification containing both feedback_text and reply_text) and delete_reply; updated templates/panels/admin_tickets.html (114 lines) with openReplyTicketModal() and openDeleteReplyModal()."
      - "Typewriter Page Guide Wizard Modal: Created templates/components/page_guide_modal.html (59 lines) and static/js/page_guides.js (115 lines) with 3-step Wizard (Overview, How to Use, Quick FAQs), prefers-reduced-motion-aware typewriter + Skip typing button across 17 routes + fallback; wired #open-page-guide-btn in topbar.html, included modal & ?v=10 assets in templates/base.html (181 lines), and registered 'page-guide-modal' in static/js/app.js (342 lines)."
      - "Tests: Created panels/test_notifications.py (168 lines) covering /notifications/feed/, submit_support_ticket admin notifications, and reply_ticket/delete_reply CRUD."

verification_results:
  - "manage.py check: 0 issues reported (exit 0)."
  - "manage.py test analytics panels --verbosity=2: 85/85 tests PASSED (72.717s)."
  - "node --check static/js/ui_widgets.js, page_guides.js, app.js, nav.js, charts.js, theme_studio.js: all exited 0."
  - "Static audit (14 modified/created files): 0 comments, 0 triple-quotes, all files within line caps (views_*.py <= 250, others <= 350); .agents/rules/edupredict-rules.md (14,509 bytes < 24,000)."
  - "Live Django Client() smoke checks: GET /notifications/feed/ -> 200 JSON (ok=True, unread_count, notifications); POST /admin-panel/tickets/ reply_ticket saved admin_reply & created FEEDBACK_REPLY notification with feedback_text + reply_text, delete_reply cleared admin_reply; GET /admin-panel/ & /profile/ -> 200 with openPageGuideModal(), page-guide-modal, page_guides.js?v=10, ui_widgets.js?v=10, and notification-bell-btn."

active_routes_and_files:
  - "panels/notification_services.py (134 lines), panels/views_notifications.py (15 lines), panels/test_notifications.py (168 lines), panels/urls.py (32 lines)"
  - "panels/admin_services.py (349 lines), panels/views_admin.py (247 lines), core/context_processors.py (76 lines)"
  - "templates/components/topbar.html (89 lines), templates/components/page_guide_modal.html (59 lines), templates/base.html (181 lines), templates/panels/admin_tickets.html (114 lines)"
  - "static/js/ui_widgets.js (248 lines), static/js/page_guides.js (115 lines), static/js/app.js (342 lines)"
  - "/notifications/feed/ -> panels:notifications_feed"

pending_modules_in_order:
  - "Phase 24: Card-Grid User/Student/Teacher Directories + Modalized Upload/Quick Entry + Dot-Graph KPI Cards"
  - "Phase 25: Stepper Signup Wizard + Teacher Approval Guard + Student PDF Transcript"

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```