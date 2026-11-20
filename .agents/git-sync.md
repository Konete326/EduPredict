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
last_updated_by_agent: "EduPredict Production Operations & Safety Team"
active_branch_merged_to_main: "feature/backup-disk-space-check -> main"
project_phase: "Phase 50 Complete: Backup CLI Disk Space Pre-Flight Safety Check"

completed_modules:
  - "Phase 1-25: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Live Theme & Appearance Studio, Per-Panel Theme Isolation, /profile/, Ocean Blue Default, Cloudinary Avatars, Change Password Modal, Global Loading Lock, Real-Time Notifications Feed, Admin Feedback Reply CRUD, Typewriter Page Guide Wizard Modal, Card-Grid User/Student/Teacher Directories, Modalized Upload/Quick Entry, Dot-Graph KPI Cards, Stepper Signup Wizard, Teacher Approval Guard & Official Student PDF Transcript."
  - "Phase 26-49: Production Operations Runbook, Docker Containers, WhiteNoise Static Serving, Atlas Connection Pooling, Automated Backup CLI with Atomic Write & Retention Purging, Endpoint Rate Limiting with Retry-After, Production CSP & Permissions-Policy Headers, Sentry Before-Send Sanitization & Environment Tagging, Health Check Process Memory & O(1) Estimated Document Counts with 30s TTL Cache."
  - "Phase 50: Backup CLI Disk Space Pre-Flight Safety Check:"
      - "Updated core/management/commands/export_backup.py (118 lines, 0 comments): Added _check_disk_space() using shutil.disk_usage() to enforce a 50MB minimum free disk space threshold before backup payload generation and verify payload_bytes + 5MB safety margin before atomic disk write."
      - "Updated panels/test_uat.py (399 lines, 0 comments): Added test_export_backup_insufficient_disk_space_raises_error mocking shutil.disk_usage to verify CommandError on low disk space, and removed redundant inner Path imports (94/94 tests PASS)."

verification_results:
  - "manage.py check: 0 issues reported (exit 0)."
  - "manage.py test: 94/94 tests PASSED (46.642s)."
  - "manage.py verify_uat: 7/7 UAT steps PASSED (11.92s)."
  - "node --check: all 9 JS scripts exited 0."
  - "Zero comments audit: 0 comments across all modified files."
  - "Line caps: export_backup.py (118 <= 350), test_uat.py (399 <= 400)."

active_routes_and_files:
  - "core/management/commands/export_backup.py (118 lines) -> Pre-flight & post-payload disk space safety guard"
  - "panels/test_uat.py (399 lines) -> 30 UAT/ops/doc tests (94 unit tests total)"

pending_modules_in_order:
  - "All planned Phases 1-25 Complete."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```