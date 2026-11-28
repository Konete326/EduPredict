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
last_updated_by_agent: "Phase 114 WhatsApp Class Chat, Student Test View Modal, Clean Filters & Badges"
active_branch_merged_to_main: "feature/p114-whatsapp-chat-clean-filters -> main"
project_phase: "Phase 114: WhatsApp Class Chat (Ticks/Slider/10MB), Student Test View Modal, Clean Filters & Badges"

completed_modules:
  - "Phase 1-113: Core Shell, Auth/RBAC, Admin Academic CRUD, Classroom Tests, Real-Time Chat, Tear-Off Calendar, Student Scope, File Preview, Real Public Data & Landing Cyan Default Theme."
  - "Phase 114a (tests-filters-badges): panels/student_test_services.py (384) & student_tests.html (265) - #student-submission-view-modal with View Submission button; standardized h-9 filter bars across 7 panel templates; cleaned noisy semester/pill badges."
  - "Phase 114b (chat-backend-v2): panels/chat_services.py (398), panels/chat_receipt_services.py (200), panels/views_chat.py (194) - 10 MB limit, max 5 images / 5 files multi-upload, WhatsApp read receipts (tick_state & TEACHER/ADMIN-only read_receipts), Cache-Control: no-store."
  - "Phase 114c (chat-whatsapp-ui): templates/panels/classroom_chat.html (201), static/js/chat_media.js (182), static/js/classroom_chat.js (399) - compact bubbles, + menu, #chat-msg-info-modal, multi-image slider, in-app preview & Download All."

verification_results:
  - "manage.py check: 0 issues."
  - "manage.py test: Ran 158 tests in 120.337s (158/158 OK)."
  - "manage.py verify_uat: UAT Results 7/7 passed in 11.95s - System 100% Operational."
  - "node --check: static/js/classroom_chat.js OK, static/js/chat_media.js OK."
  - "Line cap & zero-comment audit: all 18 modified/created files <= 400 lines with 0 comments."

active_routes_and_files:
  - "panels/student_test_services.py (384), panels/chat_services.py (398), panels/chat_receipt_services.py (200), panels/views_chat.py (194), panels/test_p109_student_chat.py (372)"
  - "static/js/chat_media.js (182), static/js/classroom_chat.js (399)"
  - "templates/panels/classroom_chat.html (201), student_tests.html (265), student_attendance.html (145), teacher_tests.html (204), teacher_students.html (91), teacher_attendance.html (135), teacher_test_grade.html (233), admin_users.html (227), admin_tickets.html (193), admin_dashboard.html (123), admin_settings.html (197)"

pending_modules_in_order:
  - "Password Change Approval Workflow: Teacher/Student requests -> Admin approves -> notification sent (new pending_password_changes_col or notifications_col extension)."
  - "Teacher My Students: Remove Update button from student list row (read-only view only)."
  - "Attendance filter: Course select should use searchable dropdown, not all-courses view."
  - "Grade Test: Simplify student roster, View modal for attachments+downloads, Update marks on separate Update button."

important_notes_for_next_agent:
  - "All input[type='date'] globally intercepted by static/js/calendar_modal.js. Add data-native-date='true' to skip the custom modal."
  - "?v=22 required on ALL static assets in templates/base.html - test_phase66.py explicitly checks this."
  - "student_id auto-resolution in _student_identity() in panels/views_student.py - reads users_col() by user_id/email fallback then student_records_col()."
  - "File preview modal opens via window.openFilePreview(url, name, mime) from templates/components/file_preview_modal.html."
  - "Project connected GitHub Konete326/EduPredict main -> Vercel auto-deploy on every push."
  - "Never commit raw GEMINI_BACKEND_KEY_3; use Vercel Env Vars for production."
```