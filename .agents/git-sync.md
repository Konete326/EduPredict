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
last_updated_by_agent: "Phase 88 Astryx Unslop, Bento Modals, 4-Col Lists & Training Page"
active_branch_merged_to_main: "feature/phase88-astryx-bento-clean-ui -> main"
project_phase: "Phase 88: Astryx + Unslop Polish, Bento Grid Modals, 4-Col Lists + View Modal, Dedicated Training Page & Draggable AI Dock"

completed_modules:
  - "Phase 1-87: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline, Theme Studio & 21st.dev Curated Presets, Cloudinary Avatars, Real-Time Notifications, Feedback Reply CRUD, Stepper Signup, Teacher Approval/Reject Guard, Official Monochrome A4 PDFs, Cgroup Health, Rate Limits, Encrypted Backups, Multi-Agent AI Dock, Vercel Auto-Deploy, Provably Hero & Live Testimonial Globe, Single-Institute Datasets, Student-ID Auth, Teacher CSV Isolation & Credentials Export, Training vs Live Separation, Clean-Start DB Reset & Full Docs Sync."
  - "Phase 88 (Astryx + Unslop Polish, Bento Modals, 4-Col Lists + View Modal, Dedicated Training Page & Draggable AI Dock):"
      - "templates/components/{form_modal,ai_message_dock}.html, templates/base.html, static/js/{app,ai_agent_dock}.js: added 2-column Bento Grid modals (>= 5 fields), global openViewDetailsModal() reusing #form-modal, fixed window-bound draggable #ep-agent-dock-toggle with sessionStorage persistence, added Figtree font, and bumped assets to ?v=22."
      - "static/css/global.css, templates/components/{sidebar,metric_card}.html: applied Meta Astryx + unslop polish (Figtree font stack, 175ms cubic-bezier transitions, quiet sentence-case sidebar labels with aria-current='page', clean stat cards without oversized decorative boxes)."
      - "panels/{urls,views_admin,admin_services}.py, templates/panels/{admin_training,admin_dashboard,teacher_dashboard,student_dashboard,analyst_dashboard}.html: added dedicated /admin-panel/training/ page & sidebar route, and simplified all 4 role dashboards to minimal Header + 4 KPIs + 2 Charts + 1 concise card."
      - "panels/{admin_directory_services,teacher_services,student_services}.py, templates/components/data_table.html, templates/panels/{admin_users,admin_courses,admin_tickets,teacher_students,student_notifications}.html: simplified all data tables to 3-4 essential columns with View (fa-eye) detail modals."
      - ".agents/{design,project-rules,prd,git-sync}.md, README.md: documented permanent Phase 88 UI/UX standards."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all static/js/*.js files exited 0."
  - "Zero-comment & line-cap audit: 0 comments across all 31 modified code files; all within caps (views_*.py <= 250, app/template/JS/CSS <= 350, tests <= 400)."
  - "manage.py test: Ran 137 tests in 87.208s (137/137 OK)."
  - "manage.py verify_uat: UAT Results 7/7 passed in 8.80s - System 100% Operational."
  - "Live QA (http://127.0.0.1:8000): verified Admin login, /admin-panel/training/ GET + CSV upload (ML Model Trained), /admin-panel/users/ & /admin-panel/courses/ 4-col tables + View modal + Bento modal, and draggable AI dock JS; cleaned MongoDB Atlas to 1 Admin user and 0 rows across all other collections."

active_routes_and_files:
  - "panels/{admin_directory_services,admin_services,student_services,teacher_services,urls,views_admin}.py, static/css/global.css, static/js/{ai_agent_dock,app}.js, templates/base.html, templates/components/{ai_message_dock,data_table,form_modal,metric_card,sidebar}.html, templates/panels/{admin_courses,admin_dashboard,admin_tickets,admin_training,admin_users,analyst_dashboard,student_dashboard,student_notifications,teacher_dashboard,teacher_students}.html, .agents/{design,git-sync,prd,project-rules}.md, README.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables (local Windows fallback reads HKCU\\Environment)."
```