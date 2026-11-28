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
last_updated_by_agent: "Phase 111/112 Tear-Off Calendar + Student Scope + Chat Upgrades + File Preview"
active_branch_merged_to_main: "feature/p111-tearoff-calendar-modal -> main (commit 998b214)"
project_phase: "Phase 112: Theme-Aware Calendar Modal, Student ID Auto-Resolution, Chat Real-Time/Media/Reply, Attendance Filters, In-App File Preview"

completed_modules:
  - "Phase 1-110: Core Shell, Auth/RBAC, Admin Academic CRUD, 9 Shell Themes, Classroom Tests, Real-Time Chat, Student Attendance Page."
  - "Phase 111 (Tear-Off Calendar Modal): static/css/calendar_modal.css (288 lines), static/js/calendar_modal.js (397 lines), templates/components/calendar_modal.html (111 lines). All input[type=date] globally intercepted. window.openTearOffCalendarModal exposed. Included in templates/base.html at ?v=22."
  - "Phase 112a (student-scope): panels/student_services.py - resolve_student_identity() auto-resolves student_id from user_id/email, syncs semester+courses+teachers. panels/views_student.py - _student_identity() auto-syncs session. panels/admin_services.py - create/update user syncs student_records_col()."
  - "Phase 112b (attendance-profile): templates/panels/student_attendance.html rebuilt with compact filters, 5-row pagination, View modal per row. templates/panels/user_profile.html - Theme & Colors button removed. panels/student_test_services.py - attendance context uses _resolve_student_courses() shared helper."
  - "Phase 112c (class-chat): panels/chat_services.py - multipart RequestDataTooBig fix. panels/views_chat.py - CSRF/toast. static/js/classroom_chat.js - cache:no-store, mobile drawer, Teacher/Admin DP crop, group rename, PDF/CSV/TXT/DOC/DOCX docs (5MB limit), 24-emoji popover, 3-dot Reply, quoted preview. templates/panels/classroom_chat.html updated."
  - "Phase 112d (preview-modal): templates/components/file_preview_modal.html (307 lines) - in-app preview for image/PDF/CSV/text files, New Tab & Download actions. templates/panels/student_tests.html and teacher_test_grade.html updated to open preview modal instead of download."

verification_results:
  - "manage.py check: 0 issues."
  - "manage.py test: Ran 150 tests in 101.731s (150/150 OK)."
  - "manage.py verify_uat: UAT Results 7/7 passed in 11.02s - System 100% Operational."
  - "node --check: calendar_modal.js OK, classroom_chat.js OK."
  - "Line cap audit: all 18 modified files <= 400 lines."

active_routes_and_files:
  - "panels/student_services.py (399), panels/views_student.py (163), panels/admin_services.py (296)"
  - "panels/student_test_services.py (367), panels/chat_services.py (396), panels/views_chat.py (179)"
  - "panels/test_p109_student_chat.py (293)"
  - "static/css/calendar_modal.css (288), static/js/calendar_modal.js (397), static/js/classroom_chat.js (396)"
  - "templates/base.html (195)"
  - "templates/components/calendar_modal.html (111), templates/components/file_preview_modal.html (307)"
  - "templates/panels/classroom_chat.html (185), templates/panels/student_attendance.html (150)"
  - "templates/panels/student_tests.html (176), templates/panels/teacher_test_grade.html (233)"
  - "templates/panels/user_profile.html (229)"

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