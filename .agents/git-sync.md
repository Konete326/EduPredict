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
last_updated_by_agent: "Phase 117 Borderless 3D Zig-Zag Home, Chat Fixes, Default Targo Theme & Animated AI Dock"
active_branch_merged_to_main: "feature/p117-home-zigzag-chat-theme-ai -> main"
project_phase: "Phase 117: Borderless 3D Zig-Zag Home, Chat No-Scroll/Group Info/Polling, Default Targo Theme & Animated AI Avatars/Mic"

completed_modules:
  - "Phase 1-116: Core Shell, Auth/RBAC, Admin Academic CRUD, Classroom Tests, WhatsApp Class Chat, Staff Chat, AI Voice/Avatars, Split Analyst Pages + Teacher Alerts, Expanded Home + Unified Logo + Contact."
  - "Phase 117a (home-zigzag): templates/public/landing.html (168), templates/public/_zz_row.html (25), static/css/landing_provably.css (169) - borderless alternating zig-zag rows with looping muted videos & 3D CSS cyan scenes."
  - "Phase 117b (chat-fixes): templates/panels/classroom_chat.html (237), static/js/classroom_chat.js (389), static/js/chat_media.js (229) - 100dvh no-page-scroll chat, #chat-group-info-modal, pencil edit button, reliable 3s polling, compact bubbles."
  - "Phase 117c (theme-default): core/theme_services.py (389), static/js/theme_studio.js (312), templates/components/theme_studio_modal.html (85), templates/base.html (204), panels/tests.py (383), panels/test_p105_workflow.py (399) - Default (Targo Cyan) shell + THEME_VERSION=2 migration."
  - "Phase 117d (ai-avatars-mic): core/ai_agent_services.py (397), templates/components/ai_message_dock.html (121), static/js/ai_agent_dock.js (342), static/js/ai_dock_avatars.js (36), static/js/ai_dock_voice.js (89), panels/test_phase76.py (347) - animated SVG mascots & SpeechRecognition mic error handling."

verification_results:
  - "manage.py check: 0 issues."
  - "manage.py test: Ran 167 tests in 106.080s (167/167 OK)."
  - "manage.py verify_uat: UAT Results 7/7 passed in 12.70s - System 100% Operational."
  - "node --check: classroom_chat.js, chat_media.js, theme_studio.js, ai_agent_dock.js, ai_dock_avatars.js, ai_dock_voice.js all OK."
  - "Line cap & zero-comment audit: all 18 modified/created files <= 400 lines with 0 comments."

active_routes_and_files:
  - "templates/public/landing.html (168), _zz_row.html (25), static/css/landing_provably.css (169)"
  - "templates/panels/classroom_chat.html (237), static/js/classroom_chat.js (389), static/js/chat_media.js (229)"
  - "core/theme_services.py (389), static/js/theme_studio.js (312), templates/components/theme_studio_modal.html (85), templates/base.html (204)"
  - "core/ai_agent_services.py (397), templates/components/ai_message_dock.html (121), static/js/ai_agent_dock.js (342), ai_dock_avatars.js (36), ai_dock_voice.js (89)"
  - "panels/tests.py (383), panels/test_p105_workflow.py (399), panels/test_phase76.py (347)"

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