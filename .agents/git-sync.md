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
last_updated_by_agent: "Phase 77 Vercel Live Deployment & GitHub Auto-Sync Team"
active_branch_merged_to_main: "feature/phase77-hf-deploy-cicd-docs -> main"
project_phase: "Phase 77 Complete: Vercel Production Hosting Connected to GitHub main Auto-Deploy + Multi-Cloud Django Config"

completed_modules:
  - "Phase 1-76: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline & Leakage-Free Evaluation, Admin Activity Logs & Portal Settings, Theme Studio, My Profile, Cloudinary Avatars, Real-Time Notifications Feed & History (/notifications/), Admin Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval/Reject Guard, Official PDF & HTML Branding Sync, Cgroup Health Telemetry, Rate-Limit Headers, Encrypted/Verified Backups, Visual Polish (60/26A), Image Cropper & Lightbox (61/26B), Table-First Directories & Student 360° Drawer (62/26C), Hyper-Automation, Live LMS Stream Simulator & Aptech Pack (63/26D), Live Stream/KPI/PDF/Card-ID Sync (64-72), Hirael Login-03 Showcase (73), Glassmorphism Profile/Tabbed Settings/Drawer Blur/Zero-Glow Academic Widgets (74), Multi-Agent AI Dock/Real-Data Honesty/Monochrome A4 PDFs (75), and AI Specialist DPs/sessionStorage Continuity/RBAC-DOM Polls/Zero-UI A4 Print/Progress Watchdog (76)."
  - "Phase 77: Vercel Production Hosting & GitHub Continuous Auto-Deploy:"
      - "vercel.json, config/settings.py (175/350 lines), Dockerfile: configured Vercel WSGI entrypoint (config/wsgi.py, maxDuration: 60), default cloud ALLOWED_HOSTS & CSRF_TRUSTED_ORIGINS (.vercel.app, .onrender.com, .hf.space, etc.), SECURE_PROXY_SSL_HEADER, USE_X_FORWARDED_HOST, and updated container healthcheck port (7860) in Dockerfile + panels/test_uat.py."
      - ".env, .env.example, panels/test_phase75.py (373/380 lines): scrubbed raw GEMINI_BACKEND_KEY_3 secret from tracked .env to pass GitHub GH013 Push Protection cleanly (runtime secrets supplied via Vercel Project Environment Variables)."
      - ".github/workflows/django.yml, README.md, .agents/prd.md, .agents/trd.md, .agents/rules/edupredict-rules.md (19,091 bytes < 24,000): documented GitHub Konete326/EduPredict -> Vercel automatic live deployment on every main push (replacing Hugging Face Spaces), updated Admin credentials (admin@gmail.com / admin123), and audited all 13 static/js/*.js files in CI."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all 13 JS scripts in static/js/*.js exited 0 (NODE_CHECK_OK)."
  - "manage.py collectstatic --noinput --dry-run: 144 static files copied."
  - "manage.py test --verbosity=2: Ran 136 tests in 78.939s (OK)."
  - "manage.py verify_uat: UAT Results: 7/7 passed in 8.03s - System 100% Operational (Step 1 status=healthy, latency=661.82ms, Steps 2-7 PASS)."
  - "Static audit: PY_AUDIT_ISSUES: [], USER_PROFILE_DIFF_EMPTY: True, .agents/rules/edupredict-rules.md 19,091 bytes (< 24,000), ENV_HAS_RAW_GEMINI False."

active_routes_and_files:
  - "vercel.json, config/settings.py, config/wsgi.py, Dockerfile, README.md, .github/workflows/django.yml, .env, .env.example, panels/test_phase75.py, panels/test_uat.py, .agents/prd.md, .agents/trd.md, .agents/rules/edupredict-rules.md, .agents/git-sync.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables."
```