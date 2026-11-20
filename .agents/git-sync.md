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
last_updated_by_agent: "EduPredict Data Protection Team"
active_branch_merged_to_main: "feature/decrypt-backup-command -> main"
project_phase: "Phase 59 Complete: decrypt_backup Management Command"

completed_modules:
  - "Phase 1-25: Core Shell, Auth/RBAC, Admin/Teacher/Student/Analyst Panels, Leakage-Free ML Evaluation, Admin Activity Logs & Portal Settings, Live Theme & Appearance Studio, Per-Panel Theme Isolation, /profile/, Ocean Blue Default, Cloudinary Avatars, Change Password Modal, Global Loading Lock, Real-Time Notifications Feed, Admin Feedback Reply CRUD, Typewriter Page Guide Wizard Modal, Card-Grid User/Student/Teacher Directories, Modalized Upload/Quick Entry, Dot-Graph KPI Cards, Stepper Signup Wizard, Teacher Approval Guard & Official Student PDF Transcript."
  - "Phase 26-50: Production Operations Runbook, Docker Containers, WhiteNoise Static Serving, Atlas Connection Pooling, Automated Backup CLI with Atomic Write, Retention Purging & Pre-Flight Disk Space Safety Check, Endpoint Rate Limiting with Retry-After, Production CSP & Permissions-Policy Headers, Sentry Before-Send Sanitization & Environment Tagging, Health Check Process Memory & O(1) Estimated Document Counts with 30s TTL Cache."
  - "Phase 51: Linux Cgroup Container Memory Limit Telemetry:"
      - "Updated core/views_health.py (226 lines, 0 comments): Added _get_cgroup_memory_limit_mb() inspecting cgroups v2 (/sys/fs/cgroup/memory.max) and cgroups v1 (/sys/fs/cgroup/memory/memory.limit_in_bytes) while ignoring unlimited/max thresholds; updated _build_memory_payload() to report container_limit_mb and container_usage_pct alongside rss_mb."
      - "Updated panels/tests.py (359 lines, 0 comments): Added test_health_cgroup_container_memory_telemetry verifying cgroups v2 numeric parsing, container_usage_pct calculation, and 'max' unlimited handling (95/95 tests PASS)."
  - "Phase 52: Backup CLI SHA-256 Integrity Checksum Manifest: export_backup.py (127 lines) writes <backup>.sha256 sidecar (hash + filename) after atomic write and prints digest; panels/tests.py (371 lines) adds test_export_backup_writes_sha256_checksum_manifest (96/96 tests PASS, UAT 7/7)."
  - "Phase 53: Rate Limit Remaining Headers: core/decorators.py (152 lines) adds X-RateLimit-Limit and X-RateLimit-Remaining to success and 429 responses; panels/tests.py (389 lines) adds header test (97/97 tests PASS, UAT 7/7)."
  - "Phase 54: Ops Tests Split: created core/test_ops.py (111 lines) with OperationsToolingTests (backup, rate-limit, cgroup tests moved); panels/tests.py now 345 lines, panels/test_uat.py now 332 lines; still 97/97 tests PASS, UAT 7/7."
  - "Phase 55: verify_backup Command: core/management/commands/verify_backup.py (39 lines) validates a backup against its .sha256 sidecar (match, mismatch, missing file/manifest, malformed manifest raise CommandError); core/test_ops.py (125 lines) adds coverage (98/98 tests PASS, UAT 7/7)."
  - "Phase 56: Rate Limit Docs: README.md (236 lines) adds Rate Limiting (Per-Worker Limits) section with X-RateLimit headers and workers x max_requests caveat, verify_backup usage, test count 98; panels/test_uat.py (339 lines) adds README docs test (99/99 tests PASS, UAT 7/7)."
  - "Phase 57: README Health Sample Sync: README.md /health/ sample now matches live response (collections, cache.entries/status, memory with rss_mb and container fields, 30s count cache and ?fresh=1 note); panels/test_uat.py (350 lines) adds sample-vs-live key test (100/100 tests PASS, UAT 7/7)."
  - "Phase 58: Backup Encryption: core/backup_crypto.py (26 lines, Fernet via BACKUP_ENCRYPTION_KEY); export_backup.py (141 lines) adds --encrypt writing <name>.enc plus sha256 of ciphertext and failing before any file is written if key is missing; verify_backup.py (46 lines) also checks .enc files decrypt; cryptography==50.0.2, cffi, pycparser added to requirements.txt; .env.example and README updated; core/test_ops.py (146 lines) adds roundtrip, missing-key and wrong-key tests (101/101 tests PASS, UAT 7/7)."
  - "Phase 59: decrypt_backup Command: core/management/commands/decrypt_backup.py (55 lines) restores plain backup from .enc via BACKUP_ENCRYPTION_KEY, atomic write, refuses overwrite without --overwrite, guards missing file/non-.enc/wrong key without leaving partial output; README documents usage; core/test_ops.py (170 lines) adds coverage (102/102 tests PASS, UAT 7/7)."

verification_results:
  - "manage.py check: 0 issues reported (exit 0)."
  - "manage.py test: 95/95 tests PASSED (41.595s)."
  - "manage.py verify_uat: 7/7 UAT steps PASSED (11.27s)."
  - "node --check: all 9 JS scripts exited 0."
  - "Zero comments audit: 0 comments across all modified files."
  - "Line caps: views_health.py (226 <= 250), tests.py (359 <= 400)."

active_routes_and_files:
  - "core/views_health.py (226 lines) -> Health check with cgroup v1/v2 container memory limit & usage % telemetry"
  - "panels/tests.py (359 lines) -> Unit tests including cgroup container memory telemetry verification"

pending_modules_in_order:
  - "Phase 60 (26A): Visual Polish & Clean Shell (90/8/2 Depth, Clean Clickable KPIs, Chart.js 6 Global Defaults, Scroll-Aware 4-Item Topbar + Ctrl+K Search, Slim Sidebar 3px Active Bar, Admin-Only Theme Studio in Portal Settings, Instant 3-Bullet Help Popover)"
  - "Phase 61 (26B): Global Image Cropper (Cropper.js CDN + Ctrl+V Screenshot Paste + Avatar 1:1 Crop & Old Cloudinary Delete + Attachment Chips) & Admin Ticket Detail Drawer + Full-Screen Lightbox"
  - "Phase 62 (26C): Table-First Directories + [Table | Cards] Toggle + 1-Click Copy ID + Student 360 Slide-Over Drawer + Teacher Reject-with-Reason Workflow"
  - "Phase 63 (26D): Hyper-Automation (Zero-Click Auto-ML + Auto-Alert Escalation, Smart CSV Auto-Mapper + Preview, 1-Click Notify All High-Risk Students, visibilitychange Sync, Dynamic Institution/Term PDF Branding, Live LMS Stream Simulator) & Aptech Final Submission Pack"

important_notes_for_next_agent:
  - "Always run pre-task git checkout main && git pull origin main && git checkout -B feature/<module> && git merge main and post-task commit/merge/push to main."
  - "Keep role navigation strictly isolated across all panels per Rule 20; preserve get_cached TTL keys, invalidate_cache on mutations, and scoped ep_theme_prefs:<user_id>:<role> isolation."
  - "Always track .env and .agents/* in Git."
```