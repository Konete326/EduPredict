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
last_updated_by_agent: "Phase 97 Targo Sticky Navbar, Sign-In, EduPredict Copy, Posters & Full Responsiveness"
active_branch_merged_to_main: "feature/p97-targo-responsive-signin -> main"
project_phase: "Phase 97: Targo Visible Sticky Navbar, Sign-In Links, EduPredict Branding, Video Posters & Responsive Breakpoints"

completed_modules:
  - "Phase 1-96: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline, Emerald Green Default Theme, Multi-Format Training, Targo Public Pages + Local Videos, Vercel Auto-Deploy."
  - "Phase 97 (Navbar Visibility, Sign-In, EduPredict Copy, Video Posters & Responsiveness):"
      - "accounts/views.py, templates/public/{_base,landing,about,contact}.html: removed 'Academic Portal' phrasing, unified EduPredict branding, added SIGN IN & GET STARTED links in sticky translucent navbar, mobile menu, and hero CTAs."
      - "static/css/landing_provably.css, static/js/landing_provably.js: made .targo-nav sticky high-contrast (always visible over hero video), added 1024px/768px/520px responsive rules (clean mobile video banner, zero-indent mobile stack, full-width <=520px CTAs)."
      - "static/video/{targo_hero,targo_about}.jpg: added lightweight poster frames on landing.html and about.html."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check static/js/landing_provably.js: exited 0."
  - "Zero-comment & line-cap audit: CAPS: [] COMMENTS: []."
  - "manage.py test: Ran 138 tests (OK) & verify_uat: 7/7 passed."
  - "MongoDB Atlas cleaned back to 1 Admin user (admin@gmail.com) only."

active_routes_and_files:
  - "accounts/views.py, templates/public/{_base,landing,about,contact}.html, static/css/landing_provably.css, static/js/landing_provably.js, static/video/*.jpg, .agents/git-sync.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables (local Windows fallback reads HKCU\\Environment)."
```