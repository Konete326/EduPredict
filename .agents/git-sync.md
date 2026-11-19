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
last_updated_by_agent: "EduPredict Database & Container Health Team"
active_branch_merged_to_main: "feature/mongo-pooling-and-docker-healthcheck -> main"
project_phase: "Phase 28 Complete: MongoDB Atlas Connection Pooling & Docker Healthcheck Integration"

completed_modules:
  - "Phase 1-22: Core Shell, Auth/RBAC, 4 Role Panels, Leakage-Free ML, Admin Logs & Settings, Live Theme Studio, My Profile, Password Toggles, 1.2s Auto-Upload, ReportLab PDF Report Cards & Rosters."
  - "Phase 23: Topbar Bell Student ID Query & Clean Alert Target Builders:"
      - "Updated core/context_processors.py (74 lines, 0 comments) so _build_notification_query and _fetch_unread_notifications accept and include student_id alongside user_id and active_role, partitioning unread cache by notifs:{user_id}:{student_id}:{role_key}."
      - "Updated panels/student_alert_services.py (69 lines, 0 comments) so _alert_targets uses dict.fromkeys to safely omit empty target_user_id entries when student_id or user_id is empty."
      - "Updated panels/test_teacher_student.py (294 lines, 0 comments) with unit tests for clean alert targets without empty-string user IDs, topbar notification query construction with/without student_id, and unread notification retrieval including student_id."
  - "Phase 24: Live End-to-End UAT Automation Suite & /health/ System Monitoring:"
      - "Added core/views_health.py (77 lines): MongoDB Atlas connection ping, sub-second latency tracking, live collection counts, and memory diagnostics returning JSON HTTP 200/503."
      - "Updated config/urls.py (14 lines): Registered /health/ route (system_health)."
      - "Added core/management/commands/verify_uat.py (205 lines): Complete multi-role simulator testing Health, Auth/RBAC, Admin self-lock, Teacher marks & PDF roster, Analyst ML, Student overview & PDF report card, and Support ticket workflow (7/7 checks PASS)."
      - "Added panels/test_uat.py (75 lines): 6 comprehensive unit tests covering /health/ endpoint response and verify_uat command execution."
  - "Phase 25: Real-Time Alert Cache Invalidation & Topbar Bell Live Sync:"
      - "Updated panels/views_admin.py (243 lines, 0 comments): Cleanly unpacked user_payload dictionary containing user_id, student_id, and role in mark_notifications_read_view to ensure student_id-targeted notifications are marked as read when clicked from the topbar bell on any panel."
      - "Updated analytics/ml_engine.py (350 lines, 0 comments): In run_prediction_pipeline, changed invalidate_cache(\"analyst:\") to full invalidate_cache() so generated dropout and anomaly alert notifications immediately invalidate notifs:*, student:*, and teacher:* in-memory cache."
      - "Updated panels/test_admin.py (276 lines, 0 comments): Added test_mark_notifications_read_view_unpacks_payload_and_handles_rbac verifying GET dashboard redirects, POST mark_notifications_read invocation with user_id, student_id, and role, and JSON response."
      - "Updated analytics/test_pipeline.py (110 lines, 0 comments): Added assertion verifying invalidate_cache() is invoked without prefix on pipeline execution with student alerts enabled."
  - "Phase 26: Production CI/CD Pipeline & Static Serving Polish:"
      - "Added .github/workflows/django.yml (53 lines, 0 comments): Complete GitHub Actions CI pipeline executing checkout, Python 3.12, Node 20, manage.py check, 5 JS syntax validations, 60 unit tests, 7/7 UAT multi-role verification, and collectstatic dry-run."
      - "Updated config/settings.py (106 lines, 0 comments): Added WhiteNoiseMiddleware, STATIC_ROOT with automatic directory ensure, and STORAGES configured with CompressedStaticFilesStorage for production static serving."
      - "Updated requirements.txt (23 lines): Pinned gunicorn==27.0.1 and whitenoise==6.12.0."
      - "Updated panels/test_uat.py (101 lines, 0 comments): Added StaticFilesAndProductionConfigTests covering WhiteNoise middleware, STATIC_ROOT presence, STORAGES staticfiles configuration, and collectstatic dry-run execution."
  - "Phase 27: Docker Containerization & Production Security Headers Packaging:"
      - "Added Dockerfile (35 lines, 0 comments): Multi-stage secure build (python:3.12-slim builder + runner) with non-root edupredict user, static collection, port 8000 exposure, and Gunicorn WSGI runtime."
      - "Added docker-compose.yml (10 lines, 0 comments) and .dockerignore (7 lines, 0 comments) for standardized single-command container orchestration."
      - "Updated config/settings.py (118 lines, 0 comments): Configured conditional production security headers when DEBUG=False including SECURE_BROWSER_XSS_FILTER, SECURE_CONTENT_TYPE_NOSNIFF, X_FRAME_OPTIONS=DENY, SECURE_HSTS_SECONDS=31536000, SESSION_COOKIE_SECURE, and CSRF_COOKIE_SECURE."
      - "Updated panels/test_uat.py (132 lines, 0 comments): Added unit tests for production security header activation under DEBUG=False and Dockerfile/compose existence and clean syntax."
  - "Phase 28: MongoDB Atlas Connection Pooling & Docker Healthcheck Integration:"
      - "Updated core/db.py (251 lines, 0 comments): Configured MongoClient connection pooling with MONGODB_MAX_POOL_SIZE (default 50), MONGODB_MIN_POOL_SIZE (default 2), MONGODB_MAX_IDLE_TIME_MS (default 45000), and MONGODB_SOCKET_TIMEOUT_MS (default 10000)."
      - "Updated Dockerfile (42 lines, 0 comments): Added curl in runner stage and registered native HEALTHCHECK directive against http://localhost:8000/health/."
      - "Updated docker-compose.yml (16 lines, 0 comments): Added healthcheck configuration for web service."
      - "Updated panels/test_uat.py (158 lines, 0 comments): Added unit tests for connection pooling option parsing and Docker healthcheck directive validation."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py verify_uat: 7/7 UAT steps PASSED in 10.17s."
  - "manage.py test: 63/63 tests PASSED in 16.88s."
  - "node --check: all JS scripts passed with 0 errors."
  - "Zero comments audit: 0 comments across all modified and newly created files."
  - "Line caps: All files strictly within limits (views <= 250, settings <= 350, tests <= 350)."

active_routes_and_files:
  - "core/db.py (251 lines), Dockerfile (42 lines), docker-compose.yml (16 lines), panels/test_uat.py (158 lines)"
  - "/health/ -> system_health"
  - "python manage.py verify_uat -> End-to-end multi-role UAT verification"

pending_modules_in_order:
  - "Phase 29: Production Readme & Operations Runbook Documentation."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Docker build command: docker compose up --build (or docker build -t edupredict:latest .)."
  - "Health endpoint is active at /health/ with live MongoDB Atlas ping."
  - "Always track .env and .agents/* in Git."
```