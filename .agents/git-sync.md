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
last_updated_by_agent: "Phase 78 Live Dynamic Gemini AI & Full-App Software-Control Action Planner Swarm"
active_branch_merged_to_main: "main (direct verified release push)"
project_phase: "Phase 78 Complete: Live Dynamic Gemini AI Dock + RBAC-Validated Full-App Software Control"

completed_modules:
  - "Phase 1-77: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline, Admin Activity Logs & Portal Settings, Theme Studio, My Profile, Cloudinary Avatars, Real-Time Notifications, Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval/Reject Guard, Official PDF & HTML Branding Sync, Cgroup Health, Rate Limits, Encrypted Backups, Enterprise Visual Polish (60-63), Live Stream/KPI/PDF/Card-ID Sync (64-72), Hirael Login-03 (73), Glassmorphism Profile/Tabbed Settings/Drawer Blur/Zero-Glow Academic Widgets (74), Multi-Agent AI Dock/Real-Data Honesty/Monochrome A4 PDFs (75), AI Specialist DPs/sessionStorage Continuity/RBAC-DOM Polls/Zero-UI A4 Print/Progress Watchdog (76), and Vercel Production Auto-Deploy on GitHub main (77)."
  - "Phase 78: Live Dynamic Gemini AI & Full-App RBAC Software-Control Action Planner:"
      - "core/ai_agent_services.py (345/350 lines, 0 comments/docstrings): added _resolve_gemini_api_key() (env + Windows HKCU Environment fallback while keeping tracked .env GH013-safe), fixed Gemini model chain (primary -> gemini-flash-lite-latest -> gemini-3.5-flash-lite, dropping failing gemini-flash-latest), increased timeout to 10.0s (GEMINI_TIMEOUT_SECS), enabled structured JSON mode (responseMimeType: application/json, maxOutputTokens: 650), and upgraded handle_agent_dock_message() to plan dynamic {reply, dom_actions, poll, handoff_to} matching user language (Roman Urdu or English)."
      - "core/ai_dom_actions.py (331/350 lines, 0 comments/docstrings): added CLICK_ACTION_SPECS (print_a4_report, download_pdf, open_change_password, open_theme_studio, notify_high_risk, run_ml, simulate_stream, export_backup), toggle_theme, toggle_sidebar, describe_role_action_schema(), sanitize_llm_dom_actions(), and sanitize_llm_poll() with strict ROLE_ROUTES and RBAC privacy guard validation."
      - "panels/views_notifications.py (112/250 lines, 0 comments/docstrings): wired optional current_path into handle_agent_dock_message()."
      - "static/js/ai_agent_dock.js (339/350 lines, 0 comments) & templates/components/ai_message_dock.html (77/350 lines, 0 comments): added dynamic software-control executor for all 6 action types (redirect, filter_table, open_and_fill_form with 2.2s prefill highlight, click_element with cross-route pending queue, toggle_theme, toggle_sidebar), current_path POST payload, live #ep-dock-engine-badge (Live AI / Policy Guard / Offline Mode), and non-repetitive offline Retry control."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all 13 JS scripts in static/js/*.js exited 0 (ALL_JS_OK)."
  - "Zero-comment & line-cap audit: core/ai_agent_services.py (345/350), core/ai_dom_actions.py (331/350), panels/views_notifications.py (112/250), static/js/ai_agent_dock.js (339/350), templates/components/ai_message_dock.html (77/350), panels/test_phase75.py (373/380), panels/test_phase76.py (365/380) — all 0 comments/docstrings; .env keeps GEMINI_BACKEND_KEY_3= blank."
  - "Live Gemini dynamic test: Test 1 (STUDENT GPA advice -> engine=gemini-flash-lite-latest, live MongoDB GPA 3.41); Test 2 (ADMIN dark mode + prefilled create_course CS-405 Machine Learning -> engine=gemini-3.5-flash-lite, 2 validated dom_actions); Test 3 (STUDENT requesting admin create_user/export_backup -> engine=rbac_guard, blocked=True, dom_actions=[])."
  - "manage.py test: Ran 136 tests in 100.347s (OK)."
  - "manage.py verify_uat: UAT Results: 7/7 passed in 9.85s - System 100% Operational (Step 1 status=healthy, latency=616.11ms, Steps 2-7 PASS)."

active_routes_and_files:
  - "core/ai_agent_services.py, core/ai_dom_actions.py, panels/views_notifications.py, static/js/ai_agent_dock.js, templates/components/ai_message_dock.html, .agents/git-sync.md"

pending_modules_in_order:
  - "Live on Vercel (auto-deployed from GitHub Konete326/EduPredict main branch)."

important_notes_for_next_agent:
  - "Project is connected from GitHub Konete326/EduPredict (main branch) to Vercel: every push to main automatically builds and deploys live on Vercel."
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Never commit raw GEMINI_BACKEND_KEY_3 or API secrets into tracked .env; manage production secrets in Vercel Environment Variables (local Windows fallback reads HKCU\\Environment)."
```