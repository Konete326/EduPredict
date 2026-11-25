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
last_updated_by_agent: "Phase 80B Student & Teacher Panel Audit Swarm"
active_branch_merged_to_main: "main (verified release push)"
project_phase: "Phase 80B Complete: Student Prediction/Context/Overflow Fixes & Teacher Course/Alert Scoping Fixes"

completed_modules:
  - "Phase 1-80A: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline, Admin Logs & Portal Settings, Theme Studio, My Profile, Cloudinary Avatars, Real-Time Notifications, Feedback Reply CRUD, Stepper Signup, Teacher Approval/Reject Guard, Official PDF & HTML Branding, Cgroup Health, Rate Limits, Encrypted Backups, Enterprise Visual Polish (60-63), Live Stream/KPI/PDF/Card-ID Sync (64-72), Hirael Login-03 (73), Glassmorphism Profile/Tabbed Settings/Drawer Blur/Zero-Glow Academic Widgets (74), Multi-Agent AI Dock/Real-Data Honesty/Monochrome A4 PDFs (75), AI Specialist DPs/sessionStorage Continuity/RBAC-DOM Polls/Zero-UI A4 Print/Progress Watchdog (76), Vercel Auto-Deploy (77), Live Dynamic Gemini AI & Full-App Software Control (78), Theme Polish, Universal Theme Studio & Analyst UX/Backend (80A)."
  - "Phase 80B: Student & Teacher Panel Audit Fixes:"
      - "panels/student_services.py (339/350) & panels/views_student.py (244/250): fixed _fetch_student_docs() prediction sorting (.sort('generated_at', DESCENDING).limit(1) + fallback GPA/risk calculation when marks exist without a prediction), added real academic context (Program/Level, Department, Batch/Class, Enrolled Courses with Assigned Teachers, Portal Admin contact) to Student Dashboard & Report."
      - "templates/panels/student_dashboard.html (194/350), student_report.html (144/350) & student_notifications.html (169/350): added 3-step 'How EduPredict Works' strip, fixed horizontal overflow on /student-panel/notifications/ (table-fixed proportional widths so Mark Read is visible) and /student-panel/report/ (removed truncate clipping on Portal/Term & Student Name, compacted Course-wise Result table)."
      - "panels/teacher_services.py (335/350), panels/teacher_alert_services.py (221/350) & panels/views_teacher.py (243/250): added Assigned Courses & Classes (matched from courses_col() by instructor_id/instructor/instructor_email with My/All Courses scope filter), Portal Admin contact, and scoped 'Alerts I Sent' on /teacher-panel/alerts/ to the logged-in teacher."
      - "templates/panels/teacher_dashboard.html (226/350), teacher_alerts.html (93/350), teacher_ingest.html (181/350) & teacher_students.html (161/350): added 3-step Teacher Workflow strip, Overwrite & Auto-ML behavior notice, Date column nowrap/min-width fitting, removed duplicate Course/Batch subtitle repetition & duplicate export buttons (sm:grid-cols-2 xl:grid-cols-4), and set ingest roster page_size=5."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all 13 JS scripts in static/js/*.js exited 0."
  - "Zero-comment & line-cap audit: all 12 modified files passed with issues=[] (views_student.py 244/250, views_teacher.py 243/250, all others <= 350)."
  - "manage.py test --verbosity=2: Ran 136 tests in 94.210s (OK)."
  - "manage.py verify_uat: UAT Results: 7/7 passed in 11.82s - System 100% Operational (Step 1 status=healthy, latency=651.99ms, Steps 2-7 PASS)."

active_routes_and_files:
  - "panels/student_services.py, panels/views_student.py, templates/panels/student_dashboard.html, templates/panels/student_report.html, templates/panels/student_notifications.html, panels/teacher_services.py, panels/teacher_alert_services.py, panels/views_teacher.py, templates/panels/teacher_dashboard.html, templates/panels/teacher_students.html, templates/panels/teacher_ingest.html, templates/panels/teacher_alerts.html, .agents/git-sync.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables (local Windows fallback reads HKCU\\Environment)."
```