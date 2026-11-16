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
last_updated_by_agent: "Coordinator & Senior Full-Stack Architect (@coordinator)"
active_branch_merged_to_main: "feature/admin-panel -> main"
project_phase: "Strict Role Navigation Isolation & Ultra-Simple Marks Ingestion 100% Implemented & Verified (Rule 20)"

completed_modules:
  - "Phase 1: Django Project Init, Core MongoDB Layer & App-Shell-3 Layout (core/, templates/components/, static/)"
  - "Phase 2: Authentication, Default Admin Sync & Role-Based Routing (accounts/services.py, accounts/views.py, templates/accounts/auth.html)"
  - "Phase 3: Analyst Panel, ML Engine, chunked CSV ingestion, anomaly detection & full-width dashboard"
  - "Phase 4 & 5: Admin Panel (CRUD, 5-row pagination, mobile cards, backups), Teacher Panel, Zero-Lag Caching & SPA Navigation"
  - "Rule 20 Execution (Strict Role Navigation Isolation & Ultra-Simple Marks Ingestion):"
      - "Strict Role Sidebar Isolation: In templates/components/sidebar.html, removed cross-role visibility (e.g. active_role == 'ADMIN' rendering inside Teacher/Student/Analyst sections). Now when active_role is ADMIN, only the Admin group renders. When TEACHER, only Teacher renders. When STUDENT, only Student renders. When ANALYST, only Analyst renders. Zero cross-panel clutter."
      - "Ultra-Simple Marks & Attendance Ingestion: Simplified teacher_ingest.html and analytics/data_pipeline.py. Teachers now have a simple 4-field quick entry widget (Student ID with datalist picker, Name, Course, Marks 0-100, Attendance % 0-100) and an optional collapsed 'More Details' section for secondary attributes. Spreadsheet upload now requires only 3 columns (Student ID, Marks, Attendance) with automatic column synonym normalization (e.g. roll_no, score, att) and sample CSV template download (?template=csv). Existing student names, batch, and courses are preserved when only marks are uploaded."
      - "Rule Documentation: Persisted Rule 20 across .agents/rules/edupredict-rules.md, .agents/project-rules.md, .agents/design.md, and .agents/skills/edupredict-workflow/SKILL.md."

verification_results:
  - "manage.py check: 0 issues reported."
  - "Role isolation verification (verify_role_isolation.py):"
      - "PASS: Admin panel sidebar strictly isolated (contains data-nav-group='admin', excludes teacher/student/analyst)."
      - "PASS: Teacher panel sidebar strictly isolated (contains data-nav-group='teacher', excludes admin/student/analyst)."
      - "PASS: Student panel sidebar strictly isolated (contains data-nav-group='student', excludes admin/teacher/analyst)."
      - "PASS: Analyst panel sidebar strictly isolated (contains data-nav-group='analyst', excludes admin/teacher/student)."
      - "PASS: Teacher sample CSV template download verified (text/csv with student_id, marks, attendance)."
      - "PASS: Simple 3-column CSV upload verified (saved student record with 92.0 marks and 88.0% attendance)."
  - "File limits & zero comments: All touched files <= 350 lines with 0 comments."

active_routes_and_files:
  - "/admin-panel/* -> panels:views_admin.py (Admin only sees Admin sidebar)"
  - "/teacher-panel/* -> panels:views_teacher.py (Teacher only sees Teacher sidebar)"
  - "/teacher-panel/ingest/?template=csv -> panels:teacher_ingest (Sample template download)"
  - "/student-panel/* -> panels:views_student.py (Student only sees Student sidebar)"
  - "/analyst-panel/* -> panels:views_analyst.py (Analyst only sees Analyst sidebar)"

pending_modules_in_order:
  - "Phase 6: Student Panel Full Implementation (Personal Dashboard, AI Risk Card, Report Download, Study Recommendations)"

important_notes_for_next_agent:
  - "Next Phase: Build the dedicated Student Panel in panels/views_student.py and templates/panels/student_*.html."
  - "Keep role navigation strictly isolated across all panels per Rule 20."
  - "Preserve zero-lag caching (core/db.py get_cached/invalidate_cache), 5-row pagination, mobile cards, and zero comments policy."
  - "Always track .env and .agents/* in Git."
```