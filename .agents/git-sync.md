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
Create or Switch to Role/Feature Dedicated Branch:

Work in a dedicated branch for the specific module being built so team members never clash (e.g., feature/core-shell, feature/admin-panel, feature/teacher-panel, feature/student-panel, feature/analyst-ml).

Bash
git checkout -B feature/<module-name>
git merge main
2. Mandatory Post-Task Git Routine (Run AFTER Testing the Feature)
Once you finish implementing the single requested feature:

Verify Zero Errors:

Bash
python manage.py check
Rewrite Section 4 (Active Handover State) of this file (.agents/git-sync.md):

REMOVE/CLEAR the outdated handover notes from the previous agent so this file stays short, clean, and current.

Write a crisp summary of what is now completed, what routes/collections were updated, and what the next agent should know.

Commit, Merge to main, and Push Both Branches:

Bash
git add .
git commit -m "feat(<module>): implement and verify <feature-name>"
git push -u origin feature/<module-name>
git checkout main
git pull origin main
git merge feature/<module-name>
git push origin main
Inform the user in Roman Urdu that their feature is live and synced on GitHub.

3. Multi-Developer Isolation Rules
Never Break Global Contracts: templates/base.html, templates/components/*, static/css/global.css, and core/db.py are shared across all panels. Only add backwards-compatible keys; never rename existing template block names ({% block content %}, {% block extra_js %}).

Panel Isolation:

Person working on Student Panel edits panels/views_student.py and templates/panels/student_*.html.

Person working on Teacher Panel edits panels/views_teacher.py and templates/panels/teacher_*.html.

Person working on Admin Panel edits panels/views_admin.py and templates/panels/admin_*.html.

Person working on Analyst & ML edits panels/views_analyst.py, analytics/*, and templates/panels/analyst_*.html.

4. Active Handover State (Agents: Replace This Block on Every Push)
```yaml
last_updated_by_agent: "Phase 2 Verification Agent (@verifier)"
active_branch_merged_to_main: "feature/auth-rbac -> main"
project_phase: "Phase 2 Complete - Authentication, Default Admin Sync & Role-Based Routing Verified"

completed_modules:
  - "Phase 1: Django Project Init, Core MongoDB Layer & App-Shell-3 Layout (templates/base.html, components/, static/)"
  - "Phase 2: Authentication & Role-Based Routing (accounts/services.py, accounts/views.py, templates/accounts/auth.html)"
  - "Core DB Caching & Env: 15s health TTL cache in core/db.py, ADMIN_EMAIL/ADMIN_PASSWORD/ADMIN_FULL_NAME in .env/.env.example, .env tracked per user instruction"
  - "RBAC View Guards: @role_required applied to all 12 routes in panels/views_{admin,teacher,student,analyst}.py and analytics/views.py"

active_routes_and_files:
  - "/ -> accounts.views.root_redirect (unauth -> /auth/; authenticated -> role dashboard)"
  - "/auth/ -> accounts:auth_view (GET standalone Sign In / Create Account; POST action=login|register against MongoDB Atlas)"
  - "/auth/logout/ -> accounts:logout_view (session.flush() + toast + redirect /auth/)"
  - "/admin-panel/* -> panels/views_admin.py (@role_required(['ADMIN']))"
  - "/teacher-panel/* -> panels/views_teacher.py (@role_required(['TEACHER']))"
  - "/student-panel/* -> panels/views_student.py (@role_required(['STUDENT']))"
  - "/analyst-panel/ -> panels/views_analyst.py (@role_required(['ANALYST']))"
  - "/analyst-panel/upload/, /analyst-panel/run-ml/ -> analytics/views.py (@role_required(['ANALYST']))"

pending_modules_in_order:
  - "Phase 3: Analyst Panel + CSV Ingestion + Scikit-Learn ML Pipeline (analytics app)"
  - "Phase 4: Admin Panel (User/Course CRUD, Metrics, Support Tickets)"
  - "Phase 5: Teacher Panel (Class Overview, Attendance/Marks Ingestion, Alerts)"
  - "Phase 6: Student Panel (Personal Dashboard, AI Risk Card, Report Download)"

important_notes_for_next_agent:
  - "Next Phase: Phase 3 — Analyst Panel + CSV Ingestion + Scikit-Learn ML Pipeline (panels/views_analyst.py, analytics/*, templates/panels/analyst_*.html) ONLY."
  - "Preserve all global contracts: templates/base.html, templates/components/*, static/css/global.css, core/db.py, core/decorators.py, core/context_processors.py, accounts/*."
  - "Maintain zero comments across all .py/.html/.css/.js files, file length <= 350 lines, and zero native alert/confirm/prompt popups."
```