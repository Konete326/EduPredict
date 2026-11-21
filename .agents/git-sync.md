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
last_updated_by_agent: "Phase 65 Global Branding Context & Live Stream Charts Team"
active_branch_merged_to_main: "feature/phase65-stream-charts-global-branding -> main"
project_phase: "Phase 65 Complete: Global Cached Portal Branding Context & Live LMS Stream Chart Auto-Refresh"

completed_modules:
  - "Phase 1-64: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline & Leakage-Free Evaluation, Admin Activity Logs & Portal Settings, Theme Studio, My Profile, Cloudinary Avatars, Real-Time Notifications Feed, Admin Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval/Reject Guard, Official PDF & HTML Branding Sync, Cgroup Health Telemetry, Rate-Limit Headers, Encrypted/Verified Backups, Visual Polish (60/26A), Image Cropper & Lightbox (61/26B), Table-First Directories & Student 360° Drawer (62/26C), Hyper-Automation, Live LMS Stream Simulator & Aptech Pack (63/26D), Student Report HTML Branding Sync & PEP 8 PDF Imports (64)."
  - "Phase 65: Global Cached Portal Branding Context & Live Stream Chart Auto-Refresh:"
      - "core/context_processors.py (92 lines, 0 comments): added _resolve_global_branding(db_connected) returning ('EduPredict Academic Portal', 'Fall 2026') when disconnected or on error and calling _resolve_pdf_branding({}) (backed by get_cached admin:settings TTL=30s) inside try/except when connected; global_context(request) now exposes portal_institution_name and portal_current_term across all routes."
      - "analytics/stream_services.py (118 lines, 0 comments): simulate_lms_stream_tick(uploaded_by='Analyst') now returns low_risk_count, medium_risk_count, dropout_counts (LOW, MEDIUM, HIGH), and course_demand alongside events and predictions_generated."
      - "templates/panels/analyst_dashboard.html (326 lines, 0 comments): initLiveStreamSimulator() -> render(data) updates Chart.getChart(document.getElementById('chart-dropout-doughnut')) and Chart.getChart(document.getElementById('chart-course-demand')) live with chart.update() on every stream tick."
      - "panels/test_phase25.py (394 lines, 0 comments): added test_phase65_global_branding_and_live_stream_charts verifying disconnected fallback defaults, custom system_settings branding via RequestFactory + global_context and live GETs on teacher_dashboard & student_dashboard, live Chart.getChart wiring in analyst_dashboard HTML, and dropout_counts + course_demand JSON payload from analytics:stream_tick."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all 11 JS scripts (analyst_evaluation.js, app.js, auth_wizard.js, charts.js, directory_ui.js, dot_kpi.js, image_cropper.js, nav.js, page_guides.js, theme_studio.js, ui_widgets.js) exited 0."
  - "manage.py test: Ran 111 tests in 54.085s (OK)."
  - "manage.py verify_uat: UAT Results: 7/7 passed in 10.38s - System 100% Operational."
  - "Static audit: core/context_processors.py (92 lines, 0 comments), analytics/stream_services.py (118 lines, 0 comments), templates/panels/analyst_dashboard.html (326 lines, 0 comments), panels/test_phase25.py (394 lines, 0 comments); .agents/rules/edupredict-rules.md 15,978 bytes (< 24,000); .env tracked."

active_routes_and_files:
  - "core/context_processors.py (92 lines), analytics/stream_services.py (118 lines), templates/panels/analyst_dashboard.html (326 lines), panels/test_phase25.py (394 lines)"

pending_modules_in_order:
  - "All Planned Phases (Phases 1-65) Complete — Ready for Final Aptech Viva & Production Deployment."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env, .agents/*, and docs/aptech_submission/* in Git."
```