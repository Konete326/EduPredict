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
active_branch_merged_to_main: "feature/student-panel -> main (Phase 6 & 7)"
project_phase: "Phase 7: Teacher Risk Alerts page & Analyst AI Accuracy page (all Coming Soon panel modules eliminated)"

completed_modules:
  - "Phase 1: Django Project Init, Core MongoDB Layer & App-Shell-3 Layout (core/, templates/components/, static/)"
  - "Phase 2: Authentication, Default Admin Sync & Role-Based Routing (accounts/services.py, accounts/views.py, templates/accounts/auth.html)"
  - "Phase 3: Analyst Panel, ML Engine, chunked CSV ingestion, anomaly detection & full-width dashboard"
  - "Phase 4 & 5: Admin Panel (CRUD, 5-row pagination, mobile cards, backups), Teacher Panel, Zero-Lag Caching & SPA Navigation"
  - "Rule 20 Verified: strict role sidebar isolation across all panels (sidebar.html)"
  - "Phase 6: Student Panel built on live MongoDB data (panels/student_services.py, panels/views_student.py):"
      - "student_dashboard: attendance/GPA/class-standing/credits KPI cards, AI Learning Insight card, My-vs-Class-Average bar chart, subject-wise 5-row paginated table + mobile cards, recent reminders, quick actions"
      - "student_report: course-wise result table, report summary, Print + CSV download (student_report_download)"
      - "student_tips: weekly study tips generated from attendance/marks/study hours + insight points"
      - "student_notifications: teacher/system alerts (severity badges, mark one/all read POST with CSRF), my help-request tickets table, Need Help modal"
      - "sidebar.html student group rewired to real routes - zero Coming Soon placeholders in Student nav"
  - "Phase 7: Teacher Risk Alerts & Analyst AI Accuracy pages built on live MongoDB data:"
      - "panels/teacher_alert_services.py + /teacher-panel/alerts/ (panels:teacher_alerts): students-needing-attention roster with one-click Send Alert modal, 'Alerts I Sent' history table (regex ^Teacher Alert), KPI cards (Need Attention, High Risk, Medium Risk, Alerts Sent + unread)"
      - "analytics/model_health.py + /analyst-panel/accuracy/ (panels:analyst_accuracy): model card (version, last run, training features), GPA MAE & stable-share metrics, low-attendance flag agreement, risk-split doughnut + GPA error bucket bar chart, course demand forecast & training data summary tables"
      - "sidebar.html: Teacher 'Risk Alerts' and Analyst 'AI Accuracy' links now real routes (zero dead links left in Teacher/Analyst nav)"

verification_results:
  - "manage.py check: 0 issues reported."
  - "Live integration test: /teacher-panel/alerts/ and /analyst-panel/accuracy/ return 200 with real MongoDB data; existing dashboards unaffected (200)."
  - "POST send_alert via /teacher-panel/alerts/ stores notification (Teacher Alert (CS-101)) and appears in history table."
  - "Role guards: STUDENT blocked from teacher/analyst pages (302 -> own panel); TEACHER blocked from analyst accuracy; ANALYST blocked from teacher alerts."
  - "Zero comments verified in all new/modified files; file caps respected (views_analyst.py 244 < 250, model_health.py 155, teacher_alert_services.py 81)."

active_routes_and_files:
  - "/teacher-panel/alerts/ -> panels:teacher_alerts (GET + POST send_alert)"
  - "/analyst-panel/accuracy/ -> panels:analyst_accuracy"
  - "New: panels/teacher_alert_services.py, analytics/model_health.py, templates/panels/teacher_alerts.html, templates/panels/analyst_accuracy.html"
  - "Modified: panels/urls.py, panels/views_teacher.py, panels/views_analyst.py, templates/components/sidebar.html"

pending_modules_in_order:
  - "Phase 8 (optional hardening): Admin Activity Logs & Settings pages (still Coming Soon), print-friendly student report CSS, deadline tracking source of truth"

important_notes_for_next_agent:
  - "Teacher alert history query matches target_role=STUDENT with title regex '^Teacher Alert'; auto ML alerts (title 'High Dropout Risk: ...') are excluded on purpose."
  - "Student identity: session user carries student_id; student alert queries must match BOTH user_id and student_id."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys (teacher:alerts, analyst:model_health) and invalidate_cache on mutations."
  - "Git identity for this repo: Fouzan980 <fouzanuddin729@gmail.com>."
  - "Always track .env and .agents/* in Git."
```