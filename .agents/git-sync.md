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
last_updated_by_agent: "EduPredict Production Observability & Telemetry Team"
active_branch_merged_to_main: "feature/sentry-env-and-uat-latency -> main"
project_phase: "Phase 48 Complete: Sentry Environment Tagging & UAT Latency Telemetry"

completed_modules:
  - "Phase 1-35: Core Shell, Auth/RBAC, 4 Role Panels, Leakage-Free ML, Admin Logs & Settings, Live Theme Studio, My Profile, Password Toggles, 1.2s Auto-Upload, ReportLab PDF Report Cards, UAT Suite, Real-Time Health, CI/CD Pipeline, WhiteNoise Static Serving, Docker Containers, Atlas Connection Pooling, Theme-Aware 500 Error Page, Operations Runbook, Automated Backup CLI with Sentry, Backup Retention Purging, Endpoint Rate Limiting, WhiteNoise Immutable Cache, Robots.txt Policy, Reverse Proxy SSL Transparency, Favicon SVG Route, and Auth Timing Defense."
  - "Phase 36: Strict Referrer Policy & Cross-Origin Opener Hardening (SECURE_REFERRER_POLICY & SECURE_CROSS_ORIGIN_OPENER_POLICY)."
  - "Phase 37: Upload Memory Caps & Form Field Protection (DATA_UPLOAD_MAX_MEMORY_SIZE = 5MB, FILE_UPLOAD_MAX_MEMORY_SIZE = 5MB, DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000)."
  - "Phase 38: Sensitive Post Parameters Masking & Cookie HttpOnly Hardening (SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SAMESITE, CSRF_COOKIE_SAMESITE, @sensitive_post_parameters)."
  - "Phase 39: Health Check Process Memory Monitoring (RSS Memory in /health/ via Windows psapi and Linux /proc/self/status)."
  - "Phase 40: Favicon Browser Caching & Health Check Ping Timeout (maxTimeMS=2000, Cache-Control: public, max-age=86400)."
  - "Phase 41: Production Content-Security-Policy (CSP) Headers Hardening (SecurityHeadersMiddleware, SECURE_CONTENT_SECURITY_POLICY)."
  - "Phase 42: Permissions-Policy Security Headers Hardening (camera=(), microphone=(), geolocation=(), payment=(), usb=())."
  - "Phase 43: Health Check No-Cache Header & Diagnostics Hardening (_json_no_cache on /health/)."
  - "Phase 44: Rate Limiter Retry-After Header & 429 Telemetry (Retry-After header, retry_after_seconds)."
  - "Phase 45: Backup CLI Partial Failure Cleanup & Disk Safety Hardening (atomic replace, unlink on error)."
  - "Phase 46: Production Sentry Before-Send Sanitization & Error Tagging (sentry_before_send masking & mongodb tagging)."
  - "Phase 47: WhiteNoise Manifest Strict Setting & Static Fault-Tolerance Hardening (WHITENOISE_MANIFEST_STRICT = False)."
  - "Phase 48: Sentry Environment Tagging & UAT Latency Telemetry:"
      - "Updated config/settings.py (160 lines, 0 comments): Configured environment=os.getenv('ENVIRONMENT', 'production') on Sentry initialization to properly isolate staging vs production alert telemetry."
      - "Updated core/management/commands/verify_uat.py (227 lines, 0 comments): Enhanced Step 1 health diagnostics to flag [HIGH LATENCY] whenever database ping latency exceeds 1500ms."
      - "Updated panels/test_uat.py (387 lines, 0 comments): Verified Sentry environment parameter in test suite (80/80 tests PASS)."

verification_results:
  - "manage.py check: 0 issues reported."
  - "manage.py verify_uat: 7/7 UAT steps PASSED in 10.27s."
  - "manage.py test: 80/80 tests PASSED in 22.77s."
  - "node --check: all 5 JS scripts passed with 0 errors."
  - "Zero comments audit: 0 comments across all modified and newly created files."
  - "Line caps: All files strictly within limits (settings.py 160, verify_uat.py 227, test_uat.py 387 <= 350-400)."

active_routes_and_files:
  - "config/settings.py (160 lines) -> Sentry environment configuration"
  - "core/management/commands/verify_uat.py (227 lines) -> UAT health latency threshold"
  - "panels/test_uat.py (387 lines) -> 28 UAT/ops/doc tests (80 unit tests in test suite)"

pending_modules_in_order:
  - "EduPredict Core Architecture, 4 Role Panels, Evaluation Engine, PDF Reports, and Production Operations/Packaging are 100% complete, hardened, and verified."

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Docker build command: docker compose up --build (or docker build -t edupredict:latest .)."
  - "Automated backup cron: python manage.py export_backup --format json --output-dir backups/ --retention-days 30 --quiet."
  - "Health endpoint is active at /health/ with live MongoDB Atlas ping, IP rate-limiting, and RSS memory telemetry."
  - "Always track .env and .agents/* in Git."
```