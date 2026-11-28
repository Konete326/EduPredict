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
last_updated_by_agent: "Phase 119 Real-Time Chat Fixes & Landing Studio Shadow / Edge-Dissolve Polish"
active_branch_merged_to_main: "feature/p119-chat-realtime-fix-shadow -> main"
project_phase: "Phase 119: WhatsApp Class & Staff Chat Real-Time Sync + Landing Studio Shadow & Video Edge-Dissolve"

completed_modules:
  - "Phase 1-118: Core Shell, Auth/RBAC, Admin Academic CRUD, Classroom Tests, WhatsApp Class Chat, Staff Chat, AI Voice/Avatars, Split Analyst Pages + Teacher Alerts, Perimeter Preloader & 4 Studio Looping Videos."
  - "Phase 119a (chat-fixes): static/js/nav.js (251), panels/views_chat.py (248), panels/chat_receipt_services.py (204), static/js/classroom_chat.js (391), templates/panels/classroom_chat.html (240), templates/base.html (204, nav.js?v=22&r=119) - SPA cache bypass for /chat & /staff-chat, s.async=false & no-store guard, json_script double-encoding fix, upward 3-dot menu flip, AI dock bottom offset, 1200ms polling + BroadcastChannel sync, edit/delete/vote returning updated messages+groups, mark_messages_read updating updated_at + cache invalidation."
  - "Phase 119b (home-preloader-frames): static/css/landing_provably.css (161), templates/public/_base.html (113, ?v=18&r=124), landing.html (169), _zz_row.html (46) - restored targo_hero.mp4 + targo_about.mp4 with seamless radial outer-edge feathering, localized edu_*.mp4 pure #F7F6F8 edges, removed edu_hero.*, and enlarged multi-layered card/CTA shadows."
  - "Phase 119 QA: panels/test_p119_chat_shadow.py (133) - multi-user real-time class/staff chat send/edit/delete/vote/read-receipt tests & frontend contract assertions."

verification_results:
  - "manage.py check: 0 issues."
  - "manage.py test: Ran 171 tests in 113.189s (171/171 OK)."
  - "manage.py verify_uat: UAT Results 7/7 passed in 11.81s - System 100% Operational."
  - "node --check: nav.js, chat_media.js, classroom_chat.js all OK."
  - "Line cap, zero-comment & .env audit: all 12 touched files <= 400 lines (views_chat.py 248 <= 250) with 0 comments; GEMINI_BACKEND_KEY_3= blank; no edu_hero.* leftovers."

active_routes_and_files:
  - "panels/views_chat.py (248), panels/chat_receipt_services.py (204), panels/test_p119_chat_shadow.py (133)"
  - "static/js/nav.js (251), static/js/classroom_chat.js (391), static/js/chat_media.js (229)"
  - "templates/base.html (204), templates/panels/classroom_chat.html (240)"
  - "static/css/landing_provably.css (161), templates/public/_base.html (113), landing.html (169), _zz_row.html (46)"

pending_modules_in_order:
  - "Password Change Approval Workflow: Teacher/Student requests -> Admin approves -> notification sent (new pending_password_changes_col or notifications_col extension)."
  - "Teacher My Students: Remove Update button from student list row (read-only view only)."
  - "Attendance filter: Course select should use searchable dropdown, not all-courses view."
  - "Grade Test: Simplify student roster, View modal for attachments+downloads, Update marks on separate Update button."

important_notes_for_next_agent:
  - "All input[type='date'] globally intercepted by static/js/calendar_modal.js. Add data-native-date='true' to skip the custom modal."
  - "?v=22 required on ALL static assets in templates/base.html; ?v=18 required on templates/public/_base.html - test_phase66.py explicitly checks both."
  - "student_id auto-resolution in _student_identity() in panels/views_student.py - reads users_col() by user_id/email fallback then student_records_col()."
  - "File preview modal opens via window.openFilePreview(url, name, mime) from templates/components/file_preview_modal.html."
  - "Project connected GitHub Konete326/EduPredict main -> Vercel auto-deploy on every push."
  - "Never commit raw GEMINI_BACKEND_KEY_3; use Vercel Env Vars for production."
```