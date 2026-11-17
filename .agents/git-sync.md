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
active_branch_merged_to_main: "feature/student-panel -> main"
project_phase: "Phase 6: Student Panel Full Implementation (Dashboard, Report Card, Study Tips, Alerts & Support)"

completed_modules:
  - "Phase 1: Django Project Init, Core MongoDB Layer & App-Shell-3 Layout (core/, templates/components/, static/)"
  - "Phase 2: Authentication, Default Admin Sync & Role-Based Routing (accounts/services.py, accounts/views.py, templates/accounts/auth.html)"
  - "Phase 3: Analyst Panel, ML Engine, chunked CSV ingestion, anomaly detection & full-width dashboard"
  - "Phase 4 & 5: Admin Panel (CRUD, 5-row pagination, mobile cards, backups), Teacher Panel, Zero-Lag Caching & SPA Navigation"
  - "Rule 20 Verified: strict role sidebar isolation across all panels (sidebar.html)"
  - "Phase 6: Student Panel built on live MongoDB data (panels/student_services.py, panels/views_student.py):"
      - "student_dashboard: attendance/GPA/class-standing/credits KPI cards, AI Learning Insight card (risk-aware plain-language summary), My-vs-Class-Average bar chart, subject-wise 5-row paginated table + mobile cards, recent reminders, quick actions"
      - "student_report: course-wise result table (5-row pagination + mobile cards), report summary (GPA, batch, credits, prediction timestamp, teacher advice), Print + CSV download (student_report_download)"
      - "student_tips: weekly study tips generated from attendance/marks/study hours + insight points"
      - "student_notifications: teacher/system alerts (severity badges, mark one/all read POST with CSRF), my help-request tickets table, Need Help modal"
      - "sidebar.html student group rewired to real routes (My Dashboard, My Report Card, Study Tips, Alerts & Support) - zero Coming Soon placeholders left in Student nav"
  - "TTL caching via get_cached (student:overview / student:alerts keys), invalidate_cache on mark-read mutations"

verification_results:
  - "manage.py check: 0 issues reported."
  - "Live integration test: all 4 student pages + CSV download return 200 with real MongoDB Atlas data."
  - "POST mark_all redirects to /student-panel/notifications/ and renders success toast."
  - "Role guards: ANALYST -> /analyst-panel/, TEACHER -> /teacher-panel/, guest -> /auth/ (302); ADMIN can view student panel (200)."
  - "Custom 404 page active for unknown URLs."
  - "Zero comments verified in all new/modified files; node --check app.js + nav.js passed."
  - "File caps: student_services.py 386 (<400), views_student.py 214 (<250)."

active_routes_and_files:
  - "/student-panel/ -> panels:student_dashboard"
  - "/student-panel/report/ -> panels:student_report"
  - "/student-panel/report/download/ -> panels:student_report_download (CSV)"
  - "/student-panel/tips/ -> panels:student_tips"
  - "/student-panel/notifications/ -> panels:student_notifications (GET + POST mark_read/mark_all)"
  - "New: panels/student_services.py, templates/panels/student_dashboard.html, student_report.html, student_tips.html, student_notifications.html"
  - "Modified: panels/urls.py, panels/views_student.py, templates/components/sidebar.html (student group)"

pending_modules_in_order:
  - "Phase 7 (optional hardening): teacher Risk Alerts page (currently Coming Soon), analyst AI Accuracy page, admin Activity Logs & Settings pages"

important_notes_for_next_agent:
  - "Student identity: session user carries student_id (accounts/services.py); teacher alerts target target_user_id = student_id, so student alert queries must match BOTH user_id and student_id."
  - "Keep role navigation strictly isolated across all panels per Rule 20."
  - "Preserve zero-lag caching (core/db.py get_cached/invalidate_cache), 5-row pagination, mobile cards, and zero comments policy."
  - "Requirements installed latest-stable on Python 3.12 per requirements.txt (Django 6.1.3, pandas 3.1.1, pymongo 4.20.0)."
  - "Always track .env and .agents/* in Git."
```