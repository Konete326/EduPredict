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
last_updated_by_agent: "Phase 64 Portal Branding Sync & PDF Imports Team"
active_branch_merged_to_main: "feature/phase64-portal-branding-sync -> main"
project_phase: "Phase 64 Complete: Student Report HTML Portal Branding Sync & PEP 8 PDF Imports Cleanup"

completed_modules:
  - "Phase 1-63: Core Shell, Auth/RBAC, 4 Role Panels, ML Pipeline & Leakage-Free Evaluation, Admin Activity Logs & Portal Settings, Theme Studio, My Profile, Cloudinary Avatars, Real-Time Notifications Feed, Admin Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval/Reject Guard, Official PDF Transcript, Cgroup Health Telemetry, Rate-Limit Headers, Encrypted/Verified Backups, Visual Polish (60/26A), Image Cropper & Lightbox (61/26B), Table-First Directories & Student 360° Drawer (62/26C), Hyper-Automation, Live LMS Stream Simulator & Aptech Pack (63/26D)."
  - "Phase 64: Portal Branding HTML/PDF Sync & PEP 8 PDF Imports Cleanup:"
      - "panels/pdf_services.py (255 lines, 0 comments): moved all reportlab imports (letter, ParagraphStyle, getSampleStyleSheet, HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle) to the top import block before _ORIG_GET_PORTAL_SETTINGS and _resolve_pdf_branding(data)."
      - "panels/views_student.py (237 lines, 0 comments): imported _resolve_pdf_branding; student_report(request) passes portal_institution_name and portal_current_term to panels/student_report.html ('Portal / Term' summary card); student_report_pdf(request) resolves and injects institution_name and current_term into pdf_data."
      - "panels/test_phase25.py (370 lines, 0 comments): added test_phase64_portal_branding_html_sync_and_pdf_imports verifying custom system_settings branding in student_report HTML & PDF responses and AST-verifying top-only imports in panels/pdf_services.py."

verification_results:
  - "manage.py check: System check identified no issues (0 silenced)."
  - "node --check: all 11 JS scripts (analyst_evaluation.js, app.js, auth_wizard.js, charts.js, directory_ui.js, dot_kpi.js, image_cropper.js, nav.js, page_guides.js, theme_studio.js, ui_widgets.js) exited 0."
  - "manage.py test: Ran 110 tests in 52.738s (OK)."
  - "manage.py verify_uat: 7/7 passed in 10.44s - System 100% Operational."
  - "Static audit: panels/pdf_services.py (255 lines, 0 comments), panels/views_student.py (237 lines, 0 comments), panels/test_phase25.py (370 lines, 0 comments); .agents/rules/edupredict-rules.md 15,978 bytes (< 24,000); .env tracked."

active_routes_and_files:
  - "panels/pdf_services.py (255 lines), panels/views_student.py (237 lines), panels/test_phase25.py (370 lines)"
  - "templates/panels/student_report.html (84 lines, Portal / Term card)"

pending_modules_in_order:
  - "All Planned Phases (Phases 1-64) Complete — Ready for Final Aptech Viva & Production Deployment."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env, .agents/*, and docs/aptech_submission/* in Git."
```