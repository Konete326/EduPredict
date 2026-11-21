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
last_updated_by_agent: "Phase 63 (26D) Hyper-Automation, Live LMS Stream Simulator & Aptech Submission Team"
active_branch_merged_to_main: "feature/phase63-hyper-automation-aptech -> main"
project_phase: "Phase 63 (26D) Complete: Enterprise UI/UX Masterplan (Phases 60-63) & Aptech Final Submission Pack Finished"

completed_modules:
  - "Phase 1-62: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline & Leakage-Free Evaluation, Admin Activity Logs & Portal Settings, Theme Studio, My Profile, Cloudinary Avatars, Real-Time Notifications Feed, Admin Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval/Reject Guard, Official PDF Transcript, Cgroup Health Telemetry, Rate-Limit Headers, Encrypted/Verified Backups, Visual Polish (Phase 60 / 26A), Image Cropper & Ticket Lightbox (Phase 61 / 26B), and Table-First Directories & Student 360° Drawer (Phase 62 / 26C)."
  - "Phase 63 (26D): Hyper-Automation, Live LMS Stream Simulator & Aptech Submission Pack:"
      - "Zero-Click ML, Smart CSV Auto-Mapper & Live LMS Stream Backend: Updated analytics/preprocessing.py (181 lines) with RandomForestClassifier(n_estimators=50, n_jobs=-1, max_depth=4, min_samples_leaf=2); updated analytics/data_pipeline.py (356 lines) with institutional aliases (Roll_No, Enrollment, Reg_No, Att_%, Test_Score, Prev_GPA, LMS_Hours), column_mappings, and 3-row preview_rows; updated analytics/ml_engine.py (364 lines) with <75% Low Attendance Alert auto-escalation; created analytics/stream_services.py (111 lines) with simulate_lms_stream_tick() pushing live LMS/attendance events, logging STREAM_TICK, and refreshing predictions; added stream_tick endpoint (/analyst-panel/stream-tick/, analytics:stream_tick) in analytics/views.py (132 lines) & analytics/urls.py (11 lines)."
      - "Teacher Bulk Alerts, Auto-Alert Toggle & Dynamic PDF Branding: Updated panels/teacher_alert_services.py (128 lines) & panels/views_teacher.py (247 lines) with notify_all_high_risk_students, toggle_teacher_auto_alerts, auto_alerts_enabled, and 'Read ✓✓' history badges; updated panels/pdf_services.py (255 lines) with _resolve_pdf_branding() syncing live institution_name and current_term from get_portal_settings() into both Student Report Card and Teacher Roster PDFs."
      - "Frontend Hyper-Automation & Aptech Final Submission Pack: Updated templates/panels/teacher_alerts.html (83 lines) with 1-click Bulk Notify & Auto-Alert < 75% toggle; updated templates/panels/analyst_dashboard.html (312 lines) with pulsing Simulate Live LMS Stream button, #live-stream-status-strip, and 5s X-CSRFToken fetch polling; updated static/js/ui_widgets.js (342 lines) with 4 KB FileReader Smart CSV Column Auto-Mapper preview ([data-csv-mapper-preview]) and visibilitychange instant notification sync; updated templates/panels/student_report.html (84 lines), templates/base.html (188 lines, ?v=16), and templates/accounts/auth.html (313 lines, ?v=16); created Aptech pack in docs/aptech_submission/ (PROJECT_REPORT.md 163 lines, INSTALLATION_README.md 128 lines, DEMO_WALKTHROUGH.md 76 lines, sample_aptech_test_dataset.csv 13 lines)."

verification_results:
  - "manage.py check: 0 issues reported (exit 0)."
  - "manage.py test: 109/109 tests PASSED (51.440s), including test_phase63_hyper_automation_live_stream_and_aptech_pack in panels/test_phase25.py (346 lines)."
  - "manage.py verify_uat: 7/7 UAT steps PASSED in 10.38s (System 100% Operational)."
  - "node --check: all 11 JS scripts (analyst_evaluation.js, app.js, auth_wizard.js, charts.js, directory_ui.js, dot_kpi.js, image_cropper.js, nav.js, page_guides.js, theme_studio.js, ui_widgets.js) exited 0."
  - "Static audit (16 modified/created code files + 4 Aptech docs): 0 comments, views <= 247 lines, all other files <= 364 lines; .agents/rules/edupredict-rules.md 15,978 bytes (< 24,000)."

active_routes_and_files:
  - "analytics/preprocessing.py (181 lines), analytics/data_pipeline.py (356 lines), analytics/ml_engine.py (364 lines), analytics/stream_services.py (111 lines)"
  - "analytics/views.py (132 lines), analytics/urls.py (11 lines), panels/teacher_alert_services.py (128 lines), panels/views_teacher.py (247 lines)"
  - "panels/pdf_services.py (255 lines), panels/test_phase25.py (346 lines), static/js/ui_widgets.js (342 lines)"
  - "templates/panels/teacher_alerts.html (83 lines), templates/panels/analyst_dashboard.html (312 lines), templates/panels/student_report.html (84 lines)"
  - "templates/base.html (188 lines), templates/accounts/auth.html (313 lines)"
  - "docs/aptech_submission/: PROJECT_REPORT.md (163 lines), INSTALLATION_README.md (128 lines), DEMO_WALKTHROUGH.md (76 lines), sample_aptech_test_dataset.csv (13 lines)"

pending_modules_in_order:
  - "All Planned Core, Ops, Security & Enterprise Masterplan Phases (Phases 1-63) Complete — Ready for Final Aptech Viva & Production Deployment."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env, .agents/*, and docs/aptech_submission/* in Git."
```