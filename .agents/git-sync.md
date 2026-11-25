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
last_updated_by_agent: "Phase 80A Theme Polish, Universal Theme Studio & Analyst UX/Backend Swarm"
active_branch_merged_to_main: "main (verified release push)"
project_phase: "Phase 80A Complete: Refined Dark Mode, Universal Theme & Colors, Metric Card Polish & Analyst Consistency"

completed_modules:
  - "Phase 1-79: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline, Admin Logs & Portal Settings, Theme Studio, My Profile, Cloudinary Avatars, Real-Time Notifications, Feedback Reply CRUD, Stepper Signup, Teacher Approval/Reject Guard, Official PDF & HTML Branding, Cgroup Health, Rate Limits, Encrypted Backups, Enterprise Visual Polish (60-63), Live Stream/KPI/PDF/Card-ID Sync (64-72), Hirael Login-03 (73), Glassmorphism Profile/Tabbed Settings/Drawer Blur/Zero-Glow Academic Widgets (74), Multi-Agent AI Dock/Real-Data Honesty/Monochrome A4 PDFs (75), AI Specialist DPs/sessionStorage Continuity/RBAC-DOM Polls/Zero-UI A4 Print/Progress Watchdog (76), Vercel Auto-Deploy (77), Live Dynamic Gemini AI & Full-App Software Control (78)."
  - "Phase 80A: Theme Polish, Universal Theme Studio & Analyst Data/UI Consistency:"
      - "core/theme_services.py (339/350) & static/css/global.css (283/350): refined neutral zinc dark tokens (#09090b canvas, #111114 surface, #1b1b20 elevated), dark/blue shell dark chromes (#0d0e12 / #111217), rgba(255,255,255,0.08) hairline borders, and crisp input/table focus & hover parity."
      - "templates/components/sidebar.html (199/350), templates/base.html (191/350) & templates/components/metric_card.html (22/350): enabled Theme & Colors (openThemeStudioModal() + theme_studio_modal.html) for all logged-in roles (ADMIN, TEACHER, STUDENT, ANALYST) while keeping Portal Settings ADMIN-only; polished metric_card.html padding & tablet/desktop typography."
      - "panels/views_analyst.py (249/250) & analytics/model_health.py (220/350): deduplicated student_records & predictions by unique student_id (coverage <= 100.0%), synced Recent Uploads count (removed .limit(6), added total_uploads_count), and clarified genuine GPA labels vs proxy previous_gpa MAE across /analyst-panel/ and /analyst-panel/accuracy/."
      - "templates/panels/analyst_dashboard.html (345/350), templates/panels/analyst_accuracy.html (159/350) & static/js/academic_widgets.js (242/350): simplified Analyst header to 3 primary actions + 3-step 'How Data & ML Work' strip, full-width Recent Uploads, compact Predictions table, stacked Tab 2 Training Data Summary, dynamic ctx.measureText padding (with fallback guard) to prevent x-axis label clipping, and wired gpa_mae_title/gpa_mae_badge."
      - "panels/test_notifications.py (241/380) & panels/test_phase24.py (182/380): updated assertions for universal non-admin Theme & Colors modal while keeping /admin-panel/settings/ ADMIN-only."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all 13 JS scripts in static/js/*.js exited 0 (JS_CHECK_OK: 13 files)."
  - "Zero-comment & line-cap audit: all 12 modified files passed with issues=[] (views_analyst.py 249/250, all others <= 350, test files <= 380)."
  - "manage.py test --verbosity=2: Ran 136 tests in 100.176s (OK)."
  - "manage.py verify_uat: UAT Results: 7/7 passed in 10.48s - System 100% Operational (Step 1 status=healthy, latency=636.4ms, Steps 2-7 PASS)."

active_routes_and_files:
  - "core/theme_services.py, static/css/global.css, templates/base.html, templates/components/sidebar.html, templates/components/metric_card.html, panels/views_analyst.py, analytics/model_health.py, templates/panels/analyst_dashboard.html, templates/panels/analyst_accuracy.html, static/js/academic_widgets.js, panels/test_notifications.py, panels/test_phase24.py, .agents/git-sync.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables (local Windows fallback reads HKCU\\Environment)."
```