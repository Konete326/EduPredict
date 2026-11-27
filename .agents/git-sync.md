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
last_updated_by_agent: "Phase 101-102 University Semesters, Searchable Dropdowns, Auto-Codes, 500-Row Dataset & Plain English Admin UI"
active_branch_merged_to_main: "feature/p101-university-semesters-searchable -> main"
project_phase: "Phase 102: University Semesters, Searchable Modals, 500-Row Dataset, Delete Modal & Everyday English"

completed_modules:
  - "Phase 1-100: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline, Targo Public/Auth/404 Pages, Admin Academic CRUD."
  - "Phase 101 (University Semesters, Searchable Dropdowns, Auto-Codes & No Credits):"
      - "templates/components/form_modal.html, static/js/app.js: added searchable_select with live suggestions and headerBadge auto-code display at modal top."
      - "panels/{admin_services,admin_academic_services,views_admin_academic,urls}.py, core/ai_dom_actions.py, templates/components/sidebar.html, templates/panels/admin_{semesters,courses,students}.html: replaced Classes with University Semesters (/admin-panel/semesters/), removed School/College levels and Course Credits, and auto-generated hidden Course/Semester codes."
  - "Phase 102 (500-Row Training Dataset, Persistence, Delete Modal & Plain English):"
      - "static/samples/university_training_dataset_500.csv: added 500-row detailed university dataset."
      - "panels/{admin_services,admin_directory_services,views_admin}.py, templates/panels/admin_training.html: fixed dataset persistence across refresh with dataset_id, added 1-click 500-row training and Delete Dataset with openConfirmModal."
      - "templates/components/{sidebar,topbar}.html, templates/panels/admin_*.html: cleaned Theme & Colors button and converted Admin Panel copy to simple everyday English."
      - "panels/{test_admin_academic,test_admin}.py: added 8 academic/training tests and updated dashboard title check."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check static/js/app.js: exited 0."
  - "Zero-comment & line-cap (<= 400) audit on 23 modified/new files: 0 comments, max 373 lines."
  - "manage.py test: Ran 136 tests (136/136 OK)."
  - "manage.py verify_uat: UAT Results 7/7 passed in 9.78s - System 100% Operational."

active_routes_and_files:
  - "static/samples/university_training_dataset_500.csv, static/js/app.js, core/ai_dom_actions.py, panels/{urls,admin_services,admin_directory_services,admin_academic_services,views_admin,views_admin_academic,test_admin,test_admin_academic}.py, templates/{components/form_modal,components/sidebar,components/topbar,panels/admin_*}.html, .agents/git-sync.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables (local Windows fallback reads HKCU\\Environment)."
```