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
last_updated_by_agent: "Phase 93 Exact FlooLandingScroll Port (EduPredict Content + Emerald Green)"
active_branch_merged_to_main: "feature/p93-exact-floo-landing -> main"
project_phase: "Phase 93: Exact 1440x1036 FlooLandingScroll Architecture with EduPredict Content"

completed_modules:
  - "Phase 1-92: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline, Emerald Green Default Theme, Multi-Format Training (.csv/.xlsx/.json/.jsonl/.ndjson/.tsv/.txt), Astryx UI, Vercel Auto-Deploy."
  - "Phase 93 (Exact FlooLandingScroll Port):"
      - "templates/public/_base.html: wrapped header and footer in {% block public_header %} and {% block public_footer %} so landing.html renders the full-bleed 100vh Floo stage without a duplicate top navbar."
      - "templates/public/landing.html, static/css/landing_provably.css, static/js/landing_provably.js: ported exact 1440x1036 ResizeObserver-zoomed FlooLandingScroll (.fld / .fld-body 3636px / .stage / .hero collapsing into 364px header / .sky + .grass + .crm rising card + .cur EduCoach AI cursor + .panel 4 tabs with .bar i progress + .pic rock/rockfg + .glass + #intg 6-card grid + .wire + .ai) with EduPredict content, live metrics, Emerald Green (#10b981) tokens, and prefers-reduced-motion static fallback."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check static/js/landing_provably.js: exited 0."
  - "manage.py test: Ran 138 tests in 113.099s (138/138 OK)."
  - "manage.py verify_uat: UAT Results 7/7 passed in 10.50s - System 100% Operational."
  - "MongoDB Atlas cleaned back to 1 Admin user (admin@gmail.com) only."

active_routes_and_files:
  - "templates/public/{_base,landing}.html, static/{css,js}/landing_provably.{css,js}, .agents/git-sync.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables (local Windows fallback reads HKCU\\Environment)."
```