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
last_updated_by_agent: "Phase 61 (26B) Global Image Cropper, Ctrl+V Screenshots & Ticket Lightbox Team"
active_branch_merged_to_main: "feature/phase61-cropper-ticket-lightbox -> main"
project_phase: "Phase 61 (26B) Complete: Global Image Cropper, Ctrl+V Ticket Screenshots, Detail Drawer & Full-Screen Lightbox"

completed_modules:
  - "Phase 1-60: Core Shell, Auth/RBAC, 4 Role Panels, Leakage-Free ML, Theme Studio, My Profile, Cloudinary Avatars, Notifications Feed, Feedback Reply CRUD, Stepper Signup Wizard, Teacher Approval Guard, Official PDF Transcript, Cgroup Health, Rate-Limit Headers, Encrypted/Verified Backups, and Visual Polish & Clean Shell (Phase 60 / 26A)."
  - "Phase 61 (26B): Global Image Cropper, Ctrl+V Screenshots, Ticket Detail Drawer & Lightbox:"
      - "CSP & Cloudinary Lifecycle: Updated config/settings.py (160 lines) CSP script-src/style-src (cdnjs.cloudflare.com) & img-src (res.cloudinary.com, *.cloudinary.com); added extract_cloudinary_public_id, destroy_cloudinary_asset, upload_ticket_attachment (edupredict/tickets), and encode_image_data_uri in core/cloudinary_services.py (149 lines); updated save_user_avatar & remove_user_avatar in core/theme_services.py (339 lines) to delete previous Cloudinary avatars."
      - "Ticket Attachments & Detail Metadata: Updated create_ticket_record (max 3 URL/data:image/UploadedFile attachments), _load_tickets, and build_ticket_table_data (first View action openTicketDetailDrawer(this), data-attachments, user/role/date/reply metadata, [N img] suffix) in panels/admin_services.py (371 lines) and panels/views_admin.py (241 lines); updated my_tickets & preview in panels/student_alert_services.py (71 lines) & panels/views_student.py (232 lines)."
      - "Global Cropper, Support Modal & Lightbox UI: Created templates/components/image_cropper_modal.html (104 lines) & static/js/image_cropper.js (255 lines) with Cropper.js v1.6.2 CDN + canvas fallback, 1:1 DataTransfer avatar crop on #profile-avatar-file, Ctrl+V/drag-drop/browse screenshot crop + max-3 attachment chips, #ticket-detail-drawer in templates/panels/admin_tickets.html (181 lines), Admin-only Theme Studio + Crop Photo in templates/panels/user_profile.html (170 lines), openSupportTicketModal() in sidebar.html (195 lines) & student_notifications.html (169 lines), and ?v=14 cache-busting in base.html (186 lines) & auth.html (313 lines)."

verification_results:
  - "manage.py check: 0 issues reported (exit 0)."
  - "manage.py test: 106/106 tests PASSED (42.279s)."
  - "manage.py verify_uat: 7/7 UAT steps PASSED (9.64s)."
  - "node --check: all 10 JS scripts (analyst_evaluation.js, app.js, auth_wizard.js, charts.js, dot_kpi.js, image_cropper.js, nav.js, page_guides.js, theme_studio.js, ui_widgets.js) exited 0."
  - "Static audit (17 modified/created files): 0 comments, views <= 241 lines, all other files <= 371 lines; .agents/rules/edupredict-rules.md 15,978 bytes (< 24,000)."

active_routes_and_files:
  - "config/settings.py (160 lines), core/cloudinary_services.py (149 lines), core/theme_services.py (339 lines)"
  - "panels/admin_services.py (371 lines), panels/views_admin.py (241 lines), panels/student_alert_services.py (71 lines), panels/views_student.py (232 lines)"
  - "templates/components/image_cropper_modal.html (104 lines), static/js/image_cropper.js (255 lines), templates/panels/admin_tickets.html (181 lines), templates/panels/user_profile.html (170 lines)"
  - "templates/components/sidebar.html (195 lines), templates/panels/student_notifications.html (169 lines), templates/base.html (186 lines), templates/accounts/auth.html (313 lines)"
  - "panels/test_notifications.py (242 lines), panels/test_phase25.py (142 lines)"

pending_modules_in_order:
  - "Phase 62 (26C): Table-First Directories + [Table | Cards] Toggle + 1-Click Copy ID + Student 360 Slide-Over Drawer + Teacher Reject-with-Reason Workflow"
  - "Phase 63 (26D): Hyper-Automation (Zero-Click Auto-ML + Auto-Alert Escalation, Smart CSV Auto-Mapper + Preview, 1-Click Notify All High-Risk Students, visibilitychange Sync, Dynamic Institution/Term PDF Branding, Live LMS Stream Simulator) & Aptech Final Submission Pack"

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```