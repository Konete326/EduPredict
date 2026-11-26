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
last_updated_by_agent: "Phase 91-92 Floo Public Pages, Green Default Theme & Multi-Format Training"
active_branch_merged_to_main: "feature/p91-auth-training-ui -> main"
project_phase: "Phase 92: Floo Scroll-Story Landing Page, Emerald Green Default Theme, Multi-Format ML Training & Strict Auth/UI Polish"

completed_modules:
  - "Phase 1-90: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline, Theme Studio & 21st.dev Curated Presets, Cloudinary Avatars, Real-Time Notifications, Feedback Reply CRUD, Stepper Signup, Teacher Approval/Reject Guard, Official Monochrome A4 PDFs, Cgroup Health, Rate Limits, Encrypted Backups, Multi-Agent AI Dock (stationary quadrant-aware popover), Vercel Auto-Deploy, Single-Institute Datasets, Student-ID Auth, Teacher CSV Isolation & Credentials Export, Training vs Live Separation, Bento Grid Modals, 4-Col Minimal Lists + View Details Modal, Dedicated /admin-panel/training/ Page, Astryx Design System Alignment."
  - "Phase 91 (Auth, Training View Modal & UI Polish):"
      - "templates/components/sidebar.html: removed Portal Settings link from Settings nav group."
      - "templates/components/metric_card.html: added truncate max-w-full and full-value title tooltip on [data-kpi-counter]."
      - "templates/components/ai_message_dock.html: simplified #ep-agent-dock-toggle to clean icon-only h-11 w-11 rounded-full button."
      - "accounts/{services,views}.py, templates/accounts/auth.html, static/js/auth_wizard.js, panels/teacher_services.py: restricted self-registration to Teacher & Analyst (Admin approval required), enabled Email/Student ID/Name login with last_login_at tracking, auto-provisioned Students on CSV upload."
      - "panels/{admin_services,admin_directory_services}.py, templates/panels/{admin_users,admin_training}.html: added preview_rows/columns on datasets_log + View modal on /admin-panel/training/ + Student ID/Last Login in user View modal."
  - "Phase 92 (Green Default Theme, Theme Studio Polish, Multi-Format Training & Floo Public Pages):"
      - "core/theme_services.py, static/css/global.css, static/js/theme_studio.js, templates/{base.html,accounts/auth.html,components/theme_studio_modal.html}: switched default theme from Blue/Ocean (#2563eb) to Emerald Green (shell_theme='green', accent='emerald', #10b981); added hover title tooltips on Theme Studio labels and mobile-first Live Preview (order-first lg:order-last)."
      - "analytics/data_pipeline.py, templates/panels/{admin_training,analyst_dashboard,teacher_ingest}.html: added multi-format dataset ingestion & ML training (.csv, .xlsx, .json, .jsonl, .ndjson, .tsv, .txt)."
      - "templates/public/{_base,landing,about,contact}.html, static/{css,js}/landing_provably.{css,js}: ported Floo 1440x1036 ResizeObserver-scaled scroll-story (STORY=2600) to Pure Django MVT + Vanilla JS/CSS in Emerald Green with Newsreader/Inter typography, live EduPredict metrics, and prefers-reduced-motion support."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all static/js/*.js files exited 0."
  - "Zero-comment & line-cap audit: LINE_CAP_FAILS: [], COMMENT_FAILS: []."
  - "manage.py test: Ran 138 tests in 84.264s (138/138 OK)."
  - "manage.py verify_uat: UAT Results 7/7 passed in 10.21s - System 100% Operational."
  - "MongoDB Atlas cleaned back to 1 Admin user (admin@gmail.com) only."

active_routes_and_files:
  - "core/theme_services.py, analytics/data_pipeline.py, static/css/{global,landing_provably}.css, static/js/{theme_studio,landing_provably}.js, templates/public/{_base,landing,about,contact}.html, templates/components/{sidebar,metric_card,ai_message_dock,theme_studio_modal}.html, .agents/git-sync.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."
  - "Optional: Re-run live browser visual QA once browser subagent quota resets."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables (local Windows fallback reads HKCU\\Environment)."
```