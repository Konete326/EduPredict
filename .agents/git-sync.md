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
last_updated_by_agent: "Phase 86 Empty-State Recent Uploads & Public Asset Sync Swarm"
active_branch_merged_to_main: "feature/phase86-empty-log-row-v20-sync -> main"
project_phase: "Phase 86 Complete: Empty-State Recent Uploads Live Row Creation & Public Asset Version Sync"

completed_modules:
  - "Phase 1-85: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline & Leakage-Free Evaluation, Admin Activity Logs & Portal Settings, Theme Studio & 21st.dev Curated Presets, Cloudinary Avatars, Real-Time Notifications, Feedback Reply CRUD, Stepper Signup, Teacher Approval/Reject Guard, Official Monochrome A4 PDFs, Cgroup Health, Rate Limits, Encrypted Backups, Enterprise Visual Polish, Multi-Agent AI Dock (Gemini live + RBAC/DOM control), Vercel Auto-Deploy, Public 21st.dev Header/Footer/About/Contact, Provably Hero & Interactive 3D Testimonial Globe, and Live Recent Uploads Stream Log Sync (85)."
  - "Phase 86: Empty-State Recent Uploads Live Row Creation & Public Asset Version Sync:"
      - "static/js/directory_ui.js (347 lines, 0 comments): updated syncStreamDatasetLogsTable(logEntry) so when #dataset-logs-table starts in empty state ([data-empty-row]), it removes [data-empty-row], dynamically builds and appends the 5-cell desktop tr[data-page-item][data-row-id] and 5-row mobile div[data-mobile-card][data-page-item][data-card-id] (with status badge pill), populates all fields, and invokes refreshSearchText()."
      - "static/js/app.js (348 lines, 0 comments): updated refreshSearchText() inside initPaginatedContainers() to rebuild entries when a paginated container originally initialized with 0 [data-page-item] items."
      - "templates/public/landing.html (288 lines, 0 comments): unified static asset query versions (?v=18) with templates/public/_base.html."
      - "panels/test_phase66.py (394 lines, 0 comments): extended test_phase85_live_stream_recent_uploads_log_sync to verify unified public ?v=18 asset versions and Node VM empty-state row/card creation + search index rebuild."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all JS scripts in static/js/*.js exited 0."
  - "Zero-comment & line-cap audit: static/js/directory_ui.js (347 lines), static/js/app.js (348 lines), templates/public/landing.html (288 lines), panels/test_phase66.py (394 lines) — 0 comments."
  - "manage.py test: Ran 137 tests (OK)."
  - "manage.py verify_uat: UAT Results 7/7 passed - System 100% Operational."

active_routes_and_files:
  - "static/js/directory_ui.js (347 lines), static/js/app.js (348 lines), templates/public/landing.html (288 lines), panels/test_phase66.py (394 lines), .agents/git-sync.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables (local Windows fallback reads HKCU\\Environment)."
```