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
last_updated_by_agent: "EduPredict Production Security & Static Assets Team"
active_branch_merged_to_main: "feature/favicon-route-and-auth-timing-defense -> main"
project_phase: "Phase 35 Complete: Favicon Static SVG Route & Auth Timing Attack Defense"

completed_modules:
  - "Phase 1-33: Core Shell, Auth/RBAC, 4 Role Panels, Leakage-Free ML, Admin Logs & Settings, Live Theme Studio, My Profile, Password Toggles, 1.2s Auto-Upload, ReportLab PDF Report Cards, UAT Suite, Real-Time Health, CI/CD Pipeline, WhiteNoise Static Serving, Docker Containers, Atlas Connection Pooling, Theme-Aware 500 Error Page, Operations Runbook, Automated Backup CLI with Sentry, Backup Retention Purging, Endpoint Rate Limiting, WhiteNoise Immutable Cache, and Robots.txt Policy."
  - "Phase 34: Reverse Proxy SSL Headers & Docker Bytecode Precompilation:"
      - "Updated config/settings.py (139 lines, 0 comments): Configured SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') and USE_X_FORWARDED_HOST = True under DEBUG=False."
      - "Updated Dockerfile (44 lines, 0 comments): Added RUN python -m compileall -q . in runner stage before ownership handover."
  - "Phase 35: Favicon Static SVG Route & Auth Timing Attack Defense:"
      - "Updated core/views_health.py (111 lines, 0 comments): Added favicon_view returning inline SVG graduation cap icon (image/svg+xml) with zero disk I/O to cleanly fulfill browser favicon requests without 404s."
      - "Updated config/urls.py (18 lines, 0 comments): Registered /favicon.ico route before catch-all 404 handler."
      - "Updated accounts/views.py (182 lines, 0 comments): Added 50ms constant-time delay on failed login authentication attempts to equalize response times between nonexistent users and incorrect passwords, preventing timing attacks."
      - "Updated README.md (226 lines): Updated test suite count to 77 tests."
      - "Updated panels/test_uat.py (327 lines, 0 comments): Added unit tests for /favicon.ico SVG response and auth login failure handling (77/77 tests PASS)."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py verify_uat: 7/7 UAT steps PASSED in 10.02s."
  - "manage.py test: 77/77 tests PASSED in 20.43s."
  - "node --check: all 5 JS scripts passed with 0 errors."
  - "Zero comments audit: 0 comments across all modified and newly created files."
  - "Line caps: All files strictly within limits (accounts/views.py 182, urls.py 18, views_health.py 111, test_uat.py 327 <= 350)."

active_routes_and_files:
  - "/favicon.ico -> core.views_health.favicon_view"
  - "accounts/views.py (182 lines) -> Auth timing defense"
  - "panels/test_uat.py (327 lines) -> 25 UAT/ops/doc tests"

pending_modules_in_order:
  - "EduPredict Core Architecture, 4 Role Panels, Evaluation Engine, PDF Reports, and Production Operations/Packaging are 100% complete, hardened, and verified."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Docker build command: docker compose up --build (or docker build -t edupredict:latest .)."
  - "Automated backup cron: python manage.py export_backup --format json --output-dir backups/ --retention-days 30 --quiet."
  - "Health endpoint is active at /health/ with live MongoDB Atlas ping and IP rate-limiting."
  - "Always track .env and .agents/* in Git."
```

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Docker build command: docker compose up --build (or docker build -t edupredict:latest .)."
  - "Automated backup cron: python manage.py export_backup --format json --output-dir backups/ --retention-days 30 --quiet."
  - "Health endpoint is active at /health/ with live MongoDB Atlas ping and IP rate-limiting."
  - "Always track .env and .agents/* in Git."
```